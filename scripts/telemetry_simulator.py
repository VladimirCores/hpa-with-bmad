#!/usr/bin/env python3
"""Telemetry simulator core for HPDC local validation runs."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
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


class TelemetryConfigError(ValueError):
    """Raised when simulator configuration is invalid."""


class TelemetryGenerationError(RuntimeError):
    """Raised when telemetry cannot be generated safely."""


class TelemetrySchemaError(RuntimeError):
    """Raised when an envelope violates the CommonEnvelope contract."""


class TelemetryProtocolError(RuntimeError):
    """Raised when a live protocol emission fails."""


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
        elapsed = max(total_messages / self.target_rps, 1.0) if self.target_rps else 1.0
        throughput = total_messages / elapsed if elapsed > 0 else 0.0
        errors = rejected + connection_failures + protocol_failures + schema_failures
        summary = {
            "mode": self.mode,
            "generated_at": self.generated_at,
            "config_path": self.config_path,
            "target_rps": self.target_rps,
            "messages_generated": self.messages_generated,
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
        api_key="local-dev-api-key",
        timeout=2.0,
        output_path="output/telemetry-simulator/summary.json",
        seed=42,
    )


def load_config(config_path: Path) -> SimulatorConfig:
    if not config_path.exists():
        raise TelemetryConfigError(f"missing simulator config: {config_path}")
    parsed = parse_simple_yaml(config_path)
    defaults = default_config()
    values = defaults.__dict__.copy()
    values.update(parsed)
    protocol_targets = values.get("protocol_targets", {})
    if not isinstance(protocol_targets, dict):
        raise TelemetryConfigError("protocol_targets must be a mapping")
    normalized_targets: dict[str, ProtocolTarget] = {}
    for name in ("http", "mqtt", "grpc"):
        raw_target = protocol_targets.get(name, {})
        if not isinstance(raw_target, dict):
            raise TelemetryConfigError(f"protocol_targets.{name} must be a mapping")
        normalized_targets[name] = ProtocolTarget(
            enabled=bool(raw_target.get("enabled", True)),
            url=raw_target.get("url"),
            broker=raw_target.get("broker"),
            topic=raw_target.get("topic"),
            endpoint=raw_target.get("endpoint"),
            service=raw_target.get("service"),
            method=raw_target.get("method"),
            timeout=float(raw_target.get("timeout", values.get("timeout", 2.0))),
        )
    return SimulatorConfig(
        device_count=int(values.get("device_count", defaults.device_count)),
        message_rate=int(values.get("message_rate", defaults.message_rate)),
        device_types=tuple(str(item) for item in values.get("device_types", defaults.device_types)),
        region_ids=tuple(str(item) for item in values.get("region_ids", defaults.region_ids)),
        protocol_targets=normalized_targets,
        api_key=str(values.get("api_key", defaults.api_key)),
        timeout=float(values.get("timeout", defaults.timeout)),
        output_path=str(values.get("output_path", defaults.output_path)),
        seed=int(values.get("seed", defaults.seed)),
        payload_size_limit_bytes=int(values.get("payload_size_limit_bytes", defaults.payload_size_limit_bytes)),
    )


def validate_config(config: SimulatorConfig) -> None:
    if config.device_count < 0:
        raise TelemetryConfigError("device_count must be >= 0")
    if config.message_rate < 0:
        raise TelemetryConfigError("message_rate must be >= 0")
    if not config.device_types:
        raise TelemetryConfigError("device_types must contain at least one device type")
    if not config.region_ids:
        raise TelemetryConfigError("region_ids must contain at least one region id")
    if config.payload_size_limit_bytes <= 0:
        raise TelemetryConfigError("payload_size_limit_bytes must be > 0")
    if "http" in config.protocol_targets and not config.protocol_targets["http"].url:
        raise TelemetryConfigError("protocol_targets.http.url is required when HTTP is enabled")
    if "mqtt" in config.protocol_targets and not config.protocol_targets["mqtt"].broker:
        raise TelemetryConfigError("protocol_targets.mqtt.broker is required when MQTT is enabled")
    if "mqtt" in config.protocol_targets and not config.protocol_targets["mqtt"].topic:
        raise TelemetryConfigError("protocol_targets.mqtt.topic is required when MQTT is enabled")
    if "grpc" in config.protocol_targets and not config.protocol_targets["grpc"].endpoint:
        raise TelemetryConfigError("protocol_targets.grpc.endpoint is required when gRPC is enabled")


def generate_payload(
    *,
    device_index: int,
    device_type: str,
    region_id: str,
    sequence: int,
    seed: int,
) -> dict[str, Any]:
    rng = random.Random(f"{seed}:{device_index}:{sequence}")
    variants = {
        "sensor": ("temperature", "humidity", "pressure"),
        "actuator": ("valve_position", "motor_speed", "command_state"),
        "gateway": ("uptime", "rx_bytes", "tx_bytes"),
    }
    metric = variants.get(device_type, variants["sensor"])[sequence % len(variants.get(device_type, variants["sensor"]))]
    base_value = rng.uniform(0.0, 100.0)
    if metric == "rx_bytes":
        base_value = rng.randint(1024, 65536)
    elif metric == "tx_bytes":
        base_value = rng.randint(1024, 65536)
    elif metric == "uptime":
        base_value = rng.randint(60, 86400)
    return {
        "device_index": device_index,
        "device_type": device_type,
        "region_id": region_id,
        "sequence": sequence,
        "metric": metric,
        "value": round(base_value, 3),
        "unit": unit_for_metric(metric),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
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
) -> TelemetryEnvelope:
    envelope = TelemetryEnvelope(
        device_id=device_id,
        device_type=device_type,
        event_type="telemetry.sample",
        timestamp=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        payload=payload,
        region_id=region_id,
        origin="iot-device-simulator",
        idempotency_key=f"{device_id}:{sequence}",
    )
    validate_common_envelope(envelope)
    return envelope


def generate_envelopes(config: SimulatorConfig) -> list[TelemetryEnvelope]:
    envelopes: list[TelemetryEnvelope] = []
    for device_index in range(config.device_count):
        device_type = config.device_types[device_index % len(config.device_types)]
        region_id = config.region_ids[device_index % len(config.region_ids)]
        device_id = f"{device_type}-{region_id.replace('-', '_')}-{device_index:05d}"
        payload = generate_payload(
            device_index=device_index,
            device_type=device_type,
            region_id=region_id,
            sequence=device_index,
            seed=config.seed,
        )
        envelopes.append(
            generate_envelope(
                device_id=device_id,
                device_type=device_type,
                region_id=region_id,
                sequence=device_index,
                payload=payload,
                seed=config.seed,
            )
        )
    return envelopes


def validate_common_envelope(envelope: TelemetryEnvelope | dict[str, Any]) -> None:
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
    if len(encoded) > MAX_ENVELOPE_SIZE_BYTES:
        raise TelemetrySchemaError("CommonEnvelope exceeds 64KB maximum size")


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
    except URLError as error:
        raise TelemetryProtocolError(f"HTTP connection failure: {error.reason}") from error
    except OSError as error:
        raise TelemetryProtocolError(f"HTTP connection failure: {error}") from error
    return (time.perf_counter() - started) * 1000.0


def emit_mqtt(envelope: TelemetryEnvelope, target: ProtocolTarget, timeout: float) -> float:
    try:
        from paho.mqtt.client import MQTT_ERR_SUCCESS, Client
    except ImportError as error:
        raise TelemetryProtocolError("MQTT live emission requires optional dependency paho-mqtt") from error
    if not target.broker or not target.topic:
        raise TelemetryProtocolError("MQTT broker and topic are not configured")
    host, port_text = target.broker.rsplit(":", 1)
    port = int(port_text)
    started = time.perf_counter()
    try:
        client = Client()
        client.connect(host, port, keepalive=10)
        info = client.publish(target.topic, envelope.to_bytes(), qos=0, retain=False)
        info.wait_for_publish(timeout=timeout)
        if info.rc != MQTT_ERR_SUCCESS:
            raise TelemetryProtocolError(f"MQTT publish failed with rc={info.rc}")
        client.disconnect()
    except Exception as error:  # noqa: BLE001 - live protocol failures must be surfaced clearly.
        try:
            client.disconnect()
        except Exception:
            pass
        raise TelemetryProtocolError(f"MQTT protocol failure: {error}") from error
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
    channel = grpc.insecure_channel(target.endpoint)
    started = time.perf_counter()
    try:
        channel.unary_unary(method_name)(
            envelope.to_bytes(),
            timeout=timeout,
        )
    except grpc.RpcError as error:
        raise TelemetryProtocolError(f"gRPC protocol failure: {error.details()}") from error
    except Exception as error:  # noqa: BLE001 - live protocol failures must be surfaced clearly.
        raise TelemetryProtocolError(f"gRPC protocol failure: {error}") from error
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
                except TelemetryProtocolError as error:
                    result.protocol_failures += 1
                    raise TelemetryProtocolError(f"{protocol} protocol failure: {error}") from error
                except OSError as error:
                    result.connection_failures += 1
                    raise TelemetryProtocolError(f"{protocol} connection failure: {error}") from error
                if latency is not None:
                    result.latencies_ms.append(latency)
                    result.accepted += 1
    except (TelemetrySchemaError, TelemetryProtocolError, OSError) as error:
        write_summary(
            RunMetrics(
                mode=mode,
                target_rps=config.message_rate,
                messages_generated=len(envelopes),
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
        config = load_config(config_path)
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
