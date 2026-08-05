#!/usr/bin/env python3
"""Telemetry simulator core for HPDC local validation runs."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT.parent / "output" / "telemetry-simulator" / "config.yaml"
MAX_ENVELOPE_SIZE_BYTES = 64 * 1024
COMMON_ENVELOPE_FIELDS = (
    "device_id",
    "device_type",
    "event_type",
    "timestamp",
    "payload",
    "region_id",
    "origin",
    "idempotency_key",
)
PROTO_COMMON_ENVELOPE_FIELD_NUMBERS = {
    "device_id": 1,
    "device_type": 2,
    "event_type": 3,
    "timestamp": 4,
    "payload": 5,
    "region_id": 6,
    "origin": 7,
    "idempotency_key": 8,
}
_COMMON_ENVELOPE_PROTO_DESCRIPTOR = None
_COMMON_ENVELOPE_PROTO_CLASS = None


class TelemetryConfigError(ValueError):
    """Raised when simulator configuration is invalid."""


class TelemetryGenerationError(RuntimeError):
    """Raised when telemetry cannot be generated safely."""


class TelemetrySchemaError(RuntimeError):
    """Raised when an envelope violates the CommonEnvelope contract."""


class TelemetryProtocolError(RuntimeError):
    """Raised when a live protocol emission fails."""


class TelemetryConnectionError(TelemetryProtocolError):
    """Raised when a live protocol cannot reach its target."""


def build_common_envelope_proto_descriptor():
    from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

    global _COMMON_ENVELOPE_PROTO_DESCRIPTOR, _COMMON_ENVELOPE_PROTO_CLASS
    if _COMMON_ENVELOPE_PROTO_CLASS is not None:
        return _COMMON_ENVELOPE_PROTO_CLASS
    message_descriptor = descriptor_pb2.DescriptorProto(name="CommonEnvelope")
    for field_name, field_number in PROTO_COMMON_ENVELOPE_FIELD_NUMBERS.items():
        field = message_descriptor.field.add()
        field.name = field_name
        field.number = field_number
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
        field.type = (
            descriptor_pb2.FieldDescriptorProto.TYPE_BYTES
            if field_name == "payload"
            else descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        )
    file_descriptor = descriptor_pb2.FileDescriptorProto(
        name="hpdc/telemetry/v1/common_envelope.proto",
        package="hpdc.telemetry.v1",
    )
    file_descriptor.message_type.add().CopyFrom(message_descriptor)
    pool = descriptor_pool.DescriptorPool()
    pool.Add(file_descriptor)
    _COMMON_ENVELOPE_PROTO_DESCRIPTOR = pool.FindMessageTypeByName("hpdc.telemetry.v1.CommonEnvelope")
    _COMMON_ENVELOPE_PROTO_CLASS = message_factory.GetMessageClass(_COMMON_ENVELOPE_PROTO_DESCRIPTOR)
    return _COMMON_ENVELOPE_PROTO_CLASS


def get_common_envelope_proto_class():
    return build_common_envelope_proto_descriptor()


@dataclass(frozen=True)
class ProtocolTarget:
    enabled: bool = True
    url: str | None = None
    broker: str | None = None
    topic: str | None = None
    endpoint: str | None = None
    service: str | None = None
    method: str | None = None
    timeout: float = 2.0


@dataclass(frozen=True)
class SimulatorConfig:
    device_count: int
    message_rate: int
    device_types: tuple[str, ...]
    region_ids: tuple[str, ...]
    protocol_targets: dict[str, ProtocolTarget]
    api_key: str
    api_key_env: str
    timeout: float
    output_path: str
    seed: int
    payload_size_limit_bytes: int = MAX_ENVELOPE_SIZE_BYTES

    @property
    def output_file(self) -> Path:
        return Path(self.output_path)

    def enabled_protocols(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, target in self.protocol_targets.items()
            if target.enabled
        )


@dataclass(frozen=True)
class TelemetryEnvelope:
    device_id: str
    device_type: str
    event_type: str
    timestamp: str
    payload: dict[str, Any]
    region_id: str
    origin: str
    idempotency_key: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "region_id": self.region_id,
            "origin": self.origin,
            "idempotency_key": self.idempotency_key,
        }

    def to_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass
class ProtocolResult:
    protocol: str
    planned: int = 0
    accepted: int = 0
    rejected: int = 0
    connection_failures: int = 0
    schema_failures: int = 0
    protocol_failures: int = 0
    latencies_ms: list[float] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.planned

    @property
    def error_rate(self) -> float:
        total = self.total
        if total == 0:
            return 0.0
        return (self.rejected + self.connection_failures + self.protocol_failures) / total


@dataclass
class RunMetrics:
    mode: str
    target_rps: int
    messages_generated: int
    device_count: int
    region_count: int
    message_rate: int
    elapsed_seconds: float
    protocol_results: dict[str, ProtocolResult]
    generated_at: str
    config_path: str
    summary_path: str

    def to_summary(self) -> dict[str, Any]:
        total_messages = sum(result.planned for result in self.protocol_results.values())
        accepted = sum(result.accepted for result in self.protocol_results.values())
        rejected = sum(result.rejected for result in self.protocol_results.values())
        connection_failures = sum(result.connection_failures for result in self.protocol_results.values())
        schema_failures = sum(result.schema_failures for result in self.protocol_results.values())
        protocol_failures = sum(result.protocol_failures for result in self.protocol_results.values())
        latencies = [latency for result in self.protocol_results.values() for latency in result.latencies_ms]
        elapsed = max(self.elapsed_seconds, 1e-9)
        throughput = total_messages / elapsed if elapsed > 0 else 0.0
        errors = rejected + connection_failures + protocol_failures + schema_failures
        summary = {
            "mode": self.mode,
            "generated_at": self.generated_at,
            "config_path": self.config_path,
            "target_rps": self.target_rps,
            "message_rate": self.message_rate,
            "messages_generated": self.messages_generated,
            "device_count": self.device_count,
            "region_count": self.region_count,
            "protocol_counts": {
                name: {
                    "planned": result.planned,
                    "accepted": result.accepted,
                    "rejected": result.rejected,
                    "connection_failures": result.connection_failures,
                    "schema_failures": result.schema_failures,
                    "protocol_failures": result.protocol_failures,
                }
                for name, result in self.protocol_results.items()
            },
            "total_messages": total_messages,
            "accepted_messages": accepted,
            "rejected_messages": rejected,
            "connection_failures": connection_failures,
            "schema_failures": schema_failures,
            "protocol_failures": protocol_failures,
            "latency_percentiles_ms": percentile_summary(latencies),
            "elapsed_seconds": round(elapsed, 6),
            "throughput_messages_per_second": round(throughput, 3),
            "error_rate": round(errors / total_messages, 6) if total_messages else 0.0,
            "exit_status": 0 if errors == 0 else 1,
        }
        return summary


def parse_simple_yaml(path: Path) -> dict[str, Any]:
    """Parse the simple YAML subset used by HPDC project config files."""
    try:
        import yaml  # type: ignore
    except ImportError:
        return parse_simple_yaml_without_pyyaml(path)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TelemetryConfigError(f"YAML root must be a mapping in {path}")
    return {str(key): value for key, value in loaded.items()}


def parse_simple_yaml_without_pyyaml(path: Path) -> dict[str, Any]:
    """Fallback parser for the simple YAML subset used by HPDC project config files."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any], str, dict[str, Any] | list[Any]]] = [(-1, root, "", root)]
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line_without_comment = remove_yaml_comment(raw_line).strip()
        if not line_without_comment:
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if line_without_comment.startswith("- "):
            while stack and indent <= stack[-1][0]:
                stack.pop()
            for entry_indent, parent, entry_key, child in reversed(stack):
                if isinstance(child, list):
                    child.append(parse_scalar(line_without_comment[2:].strip()))
                    break
                if isinstance(child, dict) and entry_key:
                    new_list = [parse_scalar(line_without_comment[2:].strip())]
                    child.clear()
                    parent[entry_key] = new_list
                    stack[-1] = (entry_indent, parent, entry_key, new_list)
                    break
            else:
                raise TelemetryConfigError(f"invalid YAML list line in {path}: {raw_line!r}")
            continue
        key, separator, value = line_without_comment.partition(":")
        if not separator:
            raise TelemetryConfigError(f"invalid YAML line in {path}: {raw_line!r}")
        key = key.strip()
        value = value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value == "":
            child: dict[str, Any] = {}
            if indent > stack[-1][0]:
                parent = stack[-1][3]
            parent[key] = child
            stack.append((indent, parent, key, child))
        else:
            parent[key] = parse_scalar(value)
    return root


def remove_yaml_comment(line: str) -> str:
    in_single = False
    in_double = False
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_double:
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if char == "#" and not in_single and not in_double:
            if index == 0 or line[index - 1].isspace():
                return line[:index]
    return line


def parse_scalar(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part.strip()) for part in inner.split(",")]
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def parse_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    try:
        return bool(int(value))
    except (TypeError, ValueError):
        raise TelemetryConfigError(f"{field_name} must be a boolean") from None


def parse_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise TelemetryConfigError(f"{field_name} must be an integer") from None


def parse_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise TelemetryConfigError(f"{field_name} must be a number") from None


def default_config() -> SimulatorConfig:
    return SimulatorConfig(
        device_count=10,
        message_rate=100,
        device_types=("sensor", "actuator", "gateway"),
        region_ids=("us-east-1", "eu-west-1", "ap-south-1"),
        protocol_targets={
            "http": ProtocolTarget(url="http://localhost:8080/telemetry"),
            "mqtt": ProtocolTarget(broker="localhost:1883", topic="hpdc/telemetry"),
            "grpc": ProtocolTarget(endpoint="localhost:50051", service="hpdc.telemetry.v1.TelemetryService"),
        },
        api_key="",
        api_key_env="HPDC_TELEMETRY_API_KEY",
        timeout=2.0,
        output_path="output/telemetry-simulator/summary.json",
        seed=42,
    )


def resolve_configured_api_key(api_key: str, api_key_env: str) -> str:
    if api_key.startswith("${") and api_key.endswith("}"):
        env_name = api_key[2:-1]
        if not env_name:
            raise TelemetryConfigError("api_key_env is required when api_key uses environment interpolation")
        resolved = os.environ.get(env_name)
        if not resolved:
            raise TelemetryConfigError(f"{env_name} is not set; cannot resolve api_key")
        return resolved
    if api_key == "" and api_key_env:
        resolved = os.environ.get(api_key_env)
        if not resolved:
            raise TelemetryConfigError(f"{api_key_env} is not set; cannot resolve api_key")
        return resolved
    return api_key


def load_config(config_path: Path, *, resolve_api_key: bool = False) -> SimulatorConfig:
    if not config_path.exists():
        raise TelemetryConfigError(f"missing simulator config: {config_path}")
    parsed = parse_simple_yaml(config_path)
    defaults = default_config()
    values = defaults.__dict__.copy()
    values.update(parsed)
    unknown_keys = set(parsed) - set(defaults.__dict__)
    if unknown_keys:
        raise TelemetryConfigError(f"unknown simulator config key(s): {', '.join(sorted(unknown_keys))}")
    protocol_targets = values.get("protocol_targets", {})
    if not isinstance(protocol_targets, dict):
        raise TelemetryConfigError("protocol_targets must be a mapping")
    normalized_targets: dict[str, ProtocolTarget] = {}
    for name in ("http", "mqtt", "grpc"):
        raw_target = protocol_targets.get(name, {})
        if not isinstance(raw_target, dict):
            raise TelemetryConfigError(f"protocol_targets.{name} must be a mapping")
        normalized_targets[name] = ProtocolTarget(
            enabled=parse_bool(raw_target.get("enabled", True), f"protocol_targets.{name}.enabled"),
            url=raw_target.get("url"),
            broker=raw_target.get("broker"),
            topic=raw_target.get("topic"),
            endpoint=raw_target.get("endpoint"),
            service=raw_target.get("service"),
            method=raw_target.get("method"),
            timeout=parse_float(raw_target.get("timeout", values.get("timeout", 2.0)), f"protocol_targets.{name}.timeout"),
        )
    return SimulatorConfig(
        device_count=parse_int(values.get("device_count", defaults.device_count), "device_count"),
        message_rate=parse_int(values.get("message_rate", defaults.message_rate), "message_rate"),
        device_types=tuple(str(item) for item in values.get("device_types", defaults.device_types)),
        region_ids=tuple(str(item) for item in values.get("region_ids", defaults.region_ids)),
        protocol_targets=normalized_targets,
        api_key=(
            resolve_configured_api_key(str(values.get("api_key", defaults.api_key)), str(values.get("api_key_env", defaults.api_key_env)))
            if resolve_api_key
            else str(values.get("api_key", defaults.api_key))
        ),

        api_key_env=str(values.get("api_key_env", defaults.api_key_env)),
        timeout=parse_float(values.get("timeout", defaults.timeout), "timeout"),
        output_path=str(values.get("output_path", defaults.output_path)),
        seed=parse_int(values.get("seed", defaults.seed), "seed"),
        payload_size_limit_bytes=parse_int(
            values.get("payload_size_limit_bytes", defaults.payload_size_limit_bytes),
            "payload_size_limit_bytes",
        ),
    )


def validate_config(config: SimulatorConfig) -> None:
    if config.device_count <= 0:
        raise TelemetryConfigError("device_count must be >= 1")
    if config.message_rate <= 0:
        raise TelemetryConfigError("message_rate must be >= 1")
    if not config.device_types:
        raise TelemetryConfigError("device_types must contain at least one device type")
    if not config.region_ids:
        raise TelemetryConfigError("region_ids must contain at least one region id")
    if config.payload_size_limit_bytes <= 0:
        raise TelemetryConfigError("payload_size_limit_bytes must be > 0")
    if config.protocol_targets["http"].enabled and not config.protocol_targets["http"].url:
        raise TelemetryConfigError("protocol_targets.http.url is required when HTTP is enabled")
    if config.protocol_targets["mqtt"].enabled and not config.protocol_targets["mqtt"].broker:
        raise TelemetryConfigError("protocol_targets.mqtt.broker is required when MQTT is enabled")
    if config.protocol_targets["mqtt"].enabled and not config.protocol_targets["mqtt"].topic:
        raise TelemetryConfigError("protocol_targets.mqtt.topic is required when MQTT is enabled")
    if config.protocol_targets["grpc"].enabled and not config.protocol_targets["grpc"].endpoint:
        raise TelemetryConfigError("protocol_targets.grpc.endpoint is required when gRPC is enabled")
    if not config.enabled_protocols():
        raise TelemetryConfigError("at least one protocol must be enabled")


def generate_payload(
    *,
    device_index: int,
    device_type: str,
    region_id: str,
    sequence: int,
    seed: int,
) -> dict[str, Any]:
    rng = random.Random(seed)
    variants = {
        "sensor": ("temperature", "humidity", "pressure"),
        "actuator": ("valve_position", "motor_speed", "command_state"),
        "gateway": ("uptime", "rx_bytes", "tx_bytes"),
    }
    device_variants = variants.get(device_type, variants["sensor"])
    metric = device_variants[device_index % len(device_variants)]
    base_value = rng.uniform(0.0, 100.0)
    if metric == "rx_bytes":
        base_value = rng.randint(1024, 65536)
    elif metric == "tx_bytes":
        base_value = rng.randint(1024, 65536)
    elif metric == "uptime":
        base_value = rng.randint(60, 86400)
    generated_at = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=sequence)
    return {
        "device_index": device_index,
        "device_type": device_type,
        "region_id": region_id,
        "sequence": sequence,
        "metric": metric,
        "value": round(base_value, 3),
        "unit": unit_for_metric(metric),
        "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
    }


def unit_for_metric(metric: str) -> str:
    if metric in {"temperature", "humidity", "pressure"}:
        return "unitless"
    if metric in {"valve_position", "command_state"}:
        return "percent"
    if metric in {"motor_speed"}:
        return "rpm"
    if metric in {"uptime"}:
        return "seconds"
    return "bytes"


def generate_envelope(
    *,
    device_id: str,
    device_type: str,
    region_id: str,
    sequence: int,
    payload: dict[str, Any],
    seed: int,
    size_limit: int = MAX_ENVELOPE_SIZE_BYTES,
) -> TelemetryEnvelope:
    envelope = TelemetryEnvelope(
        device_id=device_id,
        device_type=device_type,
        event_type="telemetry.sample",
        timestamp=(datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=sequence)).isoformat().replace("+00:00", "Z"),
        payload=payload,
        region_id=region_id,
        origin="iot-device-simulator",
        idempotency_key=f"{device_id}:{sequence}",
    )
    validate_common_envelope(envelope, limit=size_limit)
    return envelope


def generate_envelopes(config: SimulatorConfig) -> list[TelemetryEnvelope]:
    envelopes: list[TelemetryEnvelope] = []
    for sequence in range(config.message_rate):
        device_index = sequence % config.device_count
        device_type = config.device_types[device_index % len(config.device_types)]
        region_id = config.region_ids[device_index % len(config.region_ids)]
        device_id = f"{device_type}-{region_id.replace('-', '_')}-{device_index:05d}"
        payload = generate_payload(
            device_index=device_index,
            device_type=device_type,
            region_id=region_id,
            sequence=sequence,
            seed=config.seed,
        )
        envelopes.append(
            generate_envelope(
                device_id=device_id,
                device_type=device_type,
                region_id=region_id,
                sequence=sequence,
                payload=payload,
                seed=config.seed,
                size_limit=config.payload_size_limit_bytes,
            )
        )
    return envelopes


def validate_common_envelope(envelope: TelemetryEnvelope | dict[str, Any], *, limit: int = MAX_ENVELOPE_SIZE_BYTES) -> None:
    data = envelope.to_dict() if isinstance(envelope, TelemetryEnvelope) else envelope
    missing = [field for field in COMMON_ENVELOPE_FIELDS if field not in data]
    if missing:
        raise TelemetrySchemaError(f"missing CommonEnvelope field(s): {', '.join(missing)}")
    for field in ("device_id", "device_type", "event_type", "timestamp", "region_id", "origin", "idempotency_key"):
        if not isinstance(data[field], str) or not data[field]:
            raise TelemetrySchemaError(f"{field} must be a non-empty string")
    if not isinstance(data["payload"], dict):
        raise TelemetrySchemaError("payload must be a JSON object")
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > limit:
        raise TelemetrySchemaError(f"CommonEnvelope exceeds {limit} byte maximum size")


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    rank = (len(ordered) - 1) * percentile_value
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return round(ordered[int(rank)], 3)
    weight = rank - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 3)


def percentile_summary(values: list[float]) -> dict[str, float]:
    return {
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
    }


def emit_http(envelope: TelemetryEnvelope, target: ProtocolTarget, timeout: float, api_key: str) -> float:
    if not target.url:
        raise TelemetryProtocolError("HTTP target URL is not configured")
    body = envelope.to_bytes()
    request = Request(
        target.url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "X-Telemetry-Origin": envelope.origin,
        },
    )
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status >= 400:
                raise TelemetryProtocolError(f"HTTP status {response.status}")
    except HTTPError as error:
        raise TelemetryProtocolError(f"HTTP protocol failure: HTTPError {error.code}") from error
    except (URLError, OSError) as error:
        raise TelemetryConnectionError(f"HTTP connection failure: {error}") from error
    return (time.perf_counter() - started) * 1000.0


def emit_mqtt(envelope: TelemetryEnvelope, target: ProtocolTarget, timeout: float) -> float:
    try:
        from paho.mqtt.client import MQTT_ERR_SUCCESS, Client
    except ImportError as error:
        raise TelemetryProtocolError("MQTT live emission requires optional dependency paho-mqtt") from error
    if not target.broker or not target.topic:
        raise TelemetryProtocolError("MQTT broker and topic are not configured")
    try:
        host, port_text = target.broker.rsplit(":", 1)
        port = int(port_text)
    except ValueError as error:
        raise TelemetryProtocolError(f"MQTT broker must be host:port") from error
    client = None
    started = time.perf_counter()
    try:
        client = Client(client_id=f"hpdc-telemetry-simulator-{time.time_ns()}")
        client.connect(host, port, keepalive=10)
        info = client.publish(target.topic, envelope.to_bytes(), qos=0, retain=False)
        info.wait_for_publish(timeout=timeout)
        if info.rc != MQTT_ERR_SUCCESS:
            raise TelemetryProtocolError(f"MQTT publish failed with rc={info.rc}")
        client.disconnect()
    except TelemetryConnectionError:
        raise
    except TelemetryProtocolError:
        raise
    except Exception as error:  # noqa: BLE001 - live protocol failures must be surfaced clearly.
        raise TelemetryConnectionError(f"MQTT connection failure: {error}") from error
    finally:
        if client is not None:
            try:
                client.disconnect()
            except Exception:
                pass
    return (time.perf_counter() - started) * 1000.0


def emit_grpc(envelope: TelemetryEnvelope, target: ProtocolTarget, timeout: float) -> float:
    try:
        import grpc
    except ImportError as error:
        raise TelemetryProtocolError("gRPC live emission requires optional dependency grpcio") from error
    if not target.endpoint:
        raise TelemetryProtocolError("gRPC endpoint is not configured")
    service = target.service or "hpdc.telemetry.v1.TelemetryService"
    method_name = target.method or f"/{service}/PublishTelemetry"
    envelope_proto_class = get_common_envelope_proto_class()
    common_envelope = envelope_proto_class()
    payload_field_type = common_envelope.DESCRIPTOR.fields_by_number[5].type
    for field_name, value in envelope.to_dict().items():
        field_number = PROTO_COMMON_ENVELOPE_FIELD_NUMBERS[field_name]
        field = common_envelope.DESCRIPTOR.fields_by_number[field_number]
        if field.type == payload_field_type:
            setattr(common_envelope, field.name, value.encode("utf-8"))
        else:
            setattr(common_envelope, field.name, str(value))
    channel = grpc.insecure_channel(target.endpoint)
    started = time.perf_counter()
    try:
        channel.unary_unary(method_name)(common_envelope, timeout=timeout)
    except grpc.RpcError as error:
        raise TelemetryProtocolError(f"gRPC protocol failure: {error.details()}") from error
    except grpc.FutureTimeoutError as error:
        raise TelemetryConnectionError(f"gRPC connection failure: {error}") from error
    except Exception as error:  # noqa: BLE001 - live protocol failures must be surfaced clearly.
        raise TelemetryConnectionError(f"gRPC connection failure: {error}") from error
    finally:
        channel.close()
    return (time.perf_counter() - started) * 1000.0


def emit_protocol(
    envelope: TelemetryEnvelope,
    protocol: str,
    target: ProtocolTarget,
    live: bool,
    api_key: str,
) -> tuple[float | None, str | None]:
    if not live:
        return None, None
    if protocol == "http":
        return emit_http(envelope, target, target.timeout, api_key), None
    if protocol == "mqtt":
        return emit_mqtt(envelope, target, target.timeout), None
    if protocol == "grpc":
        return emit_grpc(envelope, target, target.timeout), None
    raise TelemetryProtocolError(f"unsupported protocol: {protocol}")


def make_protocol_result(protocol: str) -> ProtocolResult:
    return ProtocolResult(protocol=protocol)


def run_simulation(config: SimulatorConfig, mode: str, config_path: str | None = None) -> RunMetrics:
    validate_config(config)
    envelopes = generate_envelopes(config)
    enabled_protocols = config.enabled_protocols()
    protocol_results: dict[str, ProtocolResult] = {
        protocol: make_protocol_result(protocol) for protocol in enabled_protocols
    }
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    started_at = time.perf_counter()
    live = mode in {"apply", "live"}
    try:
        for envelope in envelopes:
            try:
                validate_common_envelope(envelope)
            except TelemetrySchemaError as error:
                for protocol in enabled_protocols:
                    protocol_results[protocol].schema_failures += 1
                raise TelemetrySchemaError(str(error)) from error
            for protocol in enabled_protocols:
                result = protocol_results[protocol]
                result.planned += 1
                if not live:
                    continue
                try:
                    latency, _error = emit_protocol(envelope, protocol, config.protocol_targets[protocol], live, config.api_key)
                except TelemetryConnectionError as error:
                    result.connection_failures += 1
                    raise TelemetryProtocolError(f"{protocol} connection failure: {error}") from error
                except TelemetryProtocolError as error:
                    result.protocol_failures += 1
                    raise TelemetryProtocolError(f"{protocol} protocol failure: {error}") from error
                if latency is not None:
                    result.latencies_ms.append(latency)
                    result.accepted += 1
    except (TelemetrySchemaError, TelemetryProtocolError, OSError) as error:
        write_summary(
            RunMetrics(
                mode=mode,
                target_rps=config.message_rate,
                messages_generated=len(envelopes),
                device_count=config.device_count,
                region_count=len(config.region_ids),
                message_rate=config.message_rate,
                elapsed_seconds=round(time.perf_counter() - started_at, 6),
                protocol_results=protocol_results,
                generated_at=generated_at,
                config_path=config_path or str(config.output_file),
                summary_path=str(config.output_file),
            )
        )
        raise
    metrics = RunMetrics(
        mode=mode,
        target_rps=config.message_rate,
        messages_generated=len(envelopes),
        device_count=config.device_count,
        region_count=len(config.region_ids),
        message_rate=config.message_rate,
        elapsed_seconds=round(time.perf_counter() - started_at, 6),
        protocol_results=protocol_results,
        generated_at=generated_at,
        config_path=config_path or str(config.output_file),
        summary_path=str(config.output_file),
    )
    write_summary(metrics)
    return metrics


def write_summary(metrics: RunMetrics) -> Path:
    output_path = Path(metrics.summary_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = metrics.to_summary()
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and optionally emit HPDC telemetry validation payloads.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to simulator YAML config")
    parser.add_argument("--offline", action="store_true", default=True, help="Use offline-safe local assumptions")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Generate and summarize payloads without live protocol emission")
    parser.add_argument("--check", action="store_true", help="Validate config and write a dry-run summary")
    parser.add_argument("--apply", action="store_true", help="Emit telemetry through configured live protocols")
    parser.add_argument("--live", action="store_true", help="Alias for --apply")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    mode = "live" if args.live else "apply" if args.apply else "check" if args.check else "dry-run"
    try:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Missing simulator config: {config_path}", file=sys.stderr)
            return 2
        config = load_config(config_path, resolve_api_key=mode in {"apply", "live"})
        metrics = run_simulation(config, mode, display_path(config_path))
        summary = metrics.to_summary()
        print(json.dumps(summary, indent=2, sort_keys=True))
        return int(summary["exit_status"])
    except TelemetryConfigError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2
    except TelemetrySchemaError as error:
        print(f"Schema error: {error}", file=sys.stderr)
        return 6
    except TelemetryProtocolError as error:
        print(f"Protocol error: {error}", file=sys.stderr)
        return 5
    except OSError as error:
        print(f"System error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
