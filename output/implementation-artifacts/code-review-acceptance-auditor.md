# Acceptance Auditor Prompt

You are an Acceptance Auditor. Review the provided diff against the spec file and any loaded context docs. Check for: violations of acceptance criteria, deviations from spec intent, missing implementation of specified behavior, contradictions between spec constraints and actual code. Output findings as a Markdown list. Each finding: one-line title, which AC/constraint it violates, and evidence from the diff.

Spec file: `output/implementation-artifacts/4-1-build-iot-device-simulator-and-telemetry-acceptance-harness.md`
Review target: `4-1-build-iot-device-simulator-and-telemetry-acceptance-harness`

Diff:

# Diff for Story 4.1 review

--- FILE: scripts/telemetry_simulator.py ---
diff --git a/scripts/telemetry_simulator.py b/scripts/telemetry_simulator.py
new file mode 100644
index 0000000..f3a7719
--- /dev/null
+++ b/scripts/telemetry_simulator.py
@@ -0,0 +1,721 @@
+#!/usr/bin/env python3
+"""Telemetry simulator core for HPDC local validation runs."""
+
+from __future__ import annotations
+
+import argparse
+import json
+import math
+import random
+import sys
+import time
+from dataclasses import dataclass, field
+from datetime import datetime, timezone
+from pathlib import Path
+from statistics import mean
+from typing import Any
+from urllib.error import HTTPError, URLError
+from urllib.request import Request, urlopen
+
+ROOT = Path(__file__).resolve().parent
+DEFAULT_CONFIG_PATH = ROOT.parent / "output" / "telemetry-simulator" / "config.yaml"
+MAX_ENVELOPE_SIZE_BYTES = 64 * 1024
+COMMON_ENVELOPE_FIELDS = (
+    "device_id",
+    "device_type",
+    "event_type",
+    "timestamp",
+    "payload",
+    "region_id",
+    "origin",
+    "idempotency_key",
+)
+
+
+class TelemetryConfigError(ValueError):
+    """Raised when simulator configuration is invalid."""
+
+
+class TelemetryGenerationError(RuntimeError):
+    """Raised when telemetry cannot be generated safely."""
+
+
+class TelemetrySchemaError(RuntimeError):
+    """Raised when an envelope violates the CommonEnvelope contract."""
+
+
+class TelemetryProtocolError(RuntimeError):
+    """Raised when a live protocol emission fails."""
+
+
+@dataclass(frozen=True)
+class ProtocolTarget:
+    enabled: bool = True
+    url: str | None = None
+    broker: str | None = None
+    topic: str | None = None
+    endpoint: str | None = None
+    service: str | None = None
+    method: str | None = None
+    timeout: float = 2.0
+
+
+@dataclass(frozen=True)
+class SimulatorConfig:
+    device_count: int
+    message_rate: int
+    device_types: tuple[str, ...]
+    region_ids: tuple[str, ...]
+    protocol_targets: dict[str, ProtocolTarget]
+    api_key: str
+    timeout: float
+    output_path: str
+    seed: int
+    payload_size_limit_bytes: int = MAX_ENVELOPE_SIZE_BYTES
+
+    @property
+    def output_file(self) -> Path:
+        return Path(self.output_path)
+
+    def enabled_protocols(self) -> tuple[str, ...]:
+        return tuple(
+            name
+            for name, target in self.protocol_targets.items()
+            if target.enabled
+        )
+
+
+@dataclass(frozen=True)
+class TelemetryEnvelope:
+    device_id: str
+    device_type: str
+    event_type: str
+    timestamp: str
+    payload: dict[str, Any]
+    region_id: str
+    origin: str
+    idempotency_key: str
+
+    def to_dict(self) -> dict[str, Any]:
+        return {
+            "device_id": self.device_id,
+            "device_type": self.device_type,
+            "event_type": self.event_type,
+            "timestamp": self.timestamp,
+            "payload": self.payload,
+            "region_id": self.region_id,
+            "origin": self.origin,
+            "idempotency_key": self.idempotency_key,
+        }
+
+    def to_bytes(self) -> bytes:
+        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
+
+
+@dataclass
+class ProtocolResult:
+    protocol: str
+    planned: int = 0
+    accepted: int = 0
+    rejected: int = 0
+    connection_failures: int = 0
+    schema_failures: int = 0
+    protocol_failures: int = 0
+    latencies_ms: list[float] = field(default_factory=list)
+
+    @property
+    def total(self) -> int:
+        return self.planned
+
+    @property
+    def error_rate(self) -> float:
+        total = self.total
+        if total == 0:
+            return 0.0
+        return (self.rejected + self.connection_failures + self.protocol_failures) / total
+
+
+@dataclass
+class RunMetrics:
+    mode: str
+    target_rps: int
+    messages_generated: int
+    protocol_results: dict[str, ProtocolResult]
+    generated_at: str
+    config_path: str
+    summary_path: str
+
+    def to_summary(self) -> dict[str, Any]:
+        total_messages = sum(result.planned for result in self.protocol_results.values())
+        accepted = sum(result.accepted for result in self.protocol_results.values())
+        rejected = sum(result.rejected for result in self.protocol_results.values())
+        connection_failures = sum(result.connection_failures for result in self.protocol_results.values())
+        schema_failures = sum(result.schema_failures for result in self.protocol_results.values())
+        protocol_failures = sum(result.protocol_failures for result in self.protocol_results.values())
+        latencies = [latency for result in self.protocol_results.values() for latency in result.latencies_ms]
+        elapsed = max(total_messages / self.target_rps, 1.0) if self.target_rps else 1.0
+        throughput = total_messages / elapsed if elapsed > 0 else 0.0
+        errors = rejected + connection_failures + protocol_failures + schema_failures
+        summary = {
+            "mode": self.mode,
+            "generated_at": self.generated_at,
+            "config_path": self.config_path,
+            "target_rps": self.target_rps,
+            "messages_generated": self.messages_generated,
+            "protocol_counts": {
+                name: {
+                    "planned": result.planned,
+                    "accepted": result.accepted,
+                    "rejected": result.rejected,
+                    "connection_failures": result.connection_failures,
+                    "schema_failures": result.schema_failures,
+                    "protocol_failures": result.protocol_failures,
+                }
+                for name, result in self.protocol_results.items()
+            },
+            "total_messages": total_messages,
+            "accepted_messages": accepted,
+            "rejected_messages": rejected,
+            "connection_failures": connection_failures,
+            "schema_failures": schema_failures,
+            "protocol_failures": protocol_failures,
+            "latency_percentiles_ms": percentile_summary(latencies),
+            "throughput_messages_per_second": round(throughput, 3),
+            "error_rate": round(errors / total_messages, 6) if total_messages else 0.0,
+            "exit_status": 0 if errors == 0 else 1,
+        }
+        return summary
+
+
+def parse_simple_yaml(path: Path) -> dict[str, Any]:
+    """Parse the simple YAML subset used by HPDC project config files."""
+    try:
+        import yaml  # type: ignore
+    except ImportError:
+        return parse_simple_yaml_without_pyyaml(path)
+    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
+    if not isinstance(loaded, dict):
+        raise TelemetryConfigError(f"YAML root must be a mapping in {path}")
+    return {str(key): value for key, value in loaded.items()}
+
+
+def parse_simple_yaml_without_pyyaml(path: Path) -> dict[str, Any]:
+    """Fallback parser for the simple YAML subset used by HPDC project config files."""
+    root: dict[str, Any] = {}
+    stack: list[tuple[int, dict[str, Any] | list[Any], str, dict[str, Any] | list[Any]]] = [(-1, root, "", root)]
+    for raw_line in path.read_text(encoding="utf-8").splitlines():
+        line_without_comment = remove_yaml_comment(raw_line).strip()
+        if not line_without_comment:
+            continue
+        indent = len(raw_line) - len(raw_line.lstrip(" "))
+        if line_without_comment.startswith("- "):
+            while stack and indent <= stack[-1][0]:
+                stack.pop()
+            for entry_indent, parent, entry_key, child in reversed(stack):
+                if isinstance(child, list):
+                    child.append(parse_scalar(line_without_comment[2:].strip()))
+                    break
+                if isinstance(child, dict) and entry_key:
+                    new_list = [parse_scalar(line_without_comment[2:].strip())]
+                    child.clear()
+                    parent[entry_key] = new_list
+                    stack[-1] = (entry_indent, parent, entry_key, new_list)
+                    break
+            else:
+                raise TelemetryConfigError(f"invalid YAML list line in {path}: {raw_line!r}")
+            continue
+        key, separator, value = line_without_comment.partition(":")
+        if not separator:
+            raise TelemetryConfigError(f"invalid YAML line in {path}: {raw_line!r}")
+        key = key.strip()
+        value = value.strip()
+        while stack and indent <= stack[-1][0]:
+            stack.pop()
+        parent = stack[-1][1]
+        if value == "":
+            child: dict[str, Any] = {}
+            if indent > stack[-1][0]:
+                parent = stack[-1][3]
+            parent[key] = child
+            stack.append((indent, parent, key, child))
+        else:
+            parent[key] = parse_scalar(value)
+    return root
+
+
+def remove_yaml_comment(line: str) -> str:
+    in_single = False
+    in_double = False
+    escaped = False
+    for index, char in enumerate(line):
+        if escaped:
+            escaped = False
+            continue
+        if char == "\\" and in_double:
+            escaped = True
+            continue
+        if char == "'" and not in_double:
+            in_single = not in_single
+            continue
+        if char == '"' and not in_single:
+            in_double = not in_double
+            continue
+        if char == "#" and not in_single and not in_double:
+            if index == 0 or line[index - 1].isspace():
+                return line[:index]
+    return line
+
+
+def parse_scalar(value: str) -> Any:
+    if value.startswith("[") and value.endswith("]"):
+        inner = value[1:-1].strip()
+        if not inner:
+            return []
+        return [parse_scalar(part.strip()) for part in inner.split(",")]
+    if value in {"true", "True"}:
+        return True
+    if value in {"false", "False"}:
+        return False
+    if value in {"null", "None", "~"}:
+        return None
+    try:
+        return int(value)
+    except ValueError:
+        pass
+    try:
+        return float(value)
+    except ValueError:
+        pass
+    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
+        return value[1:-1]
+    return value
+
+
+def default_config() -> SimulatorConfig:
+    return SimulatorConfig(
+        device_count=10,
+        message_rate=100,
+        device_types=("sensor", "actuator", "gateway"),
+        region_ids=("us-east-1", "eu-west-1", "ap-south-1"),
+        protocol_targets={
+            "http": ProtocolTarget(url="http://localhost:8080/telemetry"),
+            "mqtt": ProtocolTarget(broker="localhost:1883", topic="hpdc/telemetry"),
+            "grpc": ProtocolTarget(endpoint="localhost:50051", service="hpdc.telemetry.v1.TelemetryService"),
+        },
+        api_key="local-dev-api-key",
+        timeout=2.0,
+        output_path="output/telemetry-simulator/summary.json",
+        seed=42,
+    )
+
+
+def load_config(config_path: Path) -> SimulatorConfig:
+    if not config_path.exists():
+        raise TelemetryConfigError(f"missing simulator config: {config_path}")
+    parsed = parse_simple_yaml(config_path)
+    defaults = default_config()
+    values = defaults.__dict__.copy()
+    values.update(parsed)
+    protocol_targets = values.get("protocol_targets", {})
+    if not isinstance(protocol_targets, dict):
+        raise TelemetryConfigError("protocol_targets must be a mapping")
+    normalized_targets: dict[str, ProtocolTarget] = {}
+    for name in ("http", "mqtt", "grpc"):
+        raw_target = protocol_targets.get(name, {})
+        if not isinstance(raw_target, dict):
+            raise TelemetryConfigError(f"protocol_targets.{name} must be a mapping")
+        normalized_targets[name] = ProtocolTarget(
+            enabled=bool(raw_target.get("enabled", True)),
+            url=raw_target.get("url"),
+            broker=raw_target.get("broker"),
+            topic=raw_target.get("topic"),
+            endpoint=raw_target.get("endpoint"),
+            service=raw_target.get("service"),
+            method=raw_target.get("method"),
+            timeout=float(raw_target.get("timeout", values.get("timeout", 2.0))),
+        )
+    return SimulatorConfig(
+        device_count=int(values.get("device_count", defaults.device_count)),
+        message_rate=int(values.get("message_rate", defaults.message_rate)),
+        device_types=tuple(str(item) for item in values.get("device_types", defaults.device_types)),
+        region_ids=tuple(str(item) for item in values.get("region_ids", defaults.region_ids)),
+        protocol_targets=normalized_targets,
+        api_key=str(values.get("api_key", defaults.api_key)),
+        timeout=float(values.get("timeout", defaults.timeout)),
+        output_path=str(values.get("output_path", defaults.output_path)),
+        seed=int(values.get("seed", defaults.seed)),
+        payload_size_limit_bytes=int(values.get("payload_size_limit_bytes", defaults.payload_size_limit_bytes)),
+    )
+
+
+def validate_config(config: SimulatorConfig) -> None:
+    if config.device_count < 0:
+        raise TelemetryConfigError("device_count must be >= 0")
+    if config.message_rate < 0:
+        raise TelemetryConfigError("message_rate must be >= 0")
+    if not config.device_types:
+        raise TelemetryConfigError("device_types must contain at least one device type")
+    if not config.region_ids:
+        raise TelemetryConfigError("region_ids must contain at least one region id")
+    if config.payload_size_limit_bytes <= 0:
+        raise TelemetryConfigError("payload_size_limit_bytes must be > 0")
+    if "http" in config.protocol_targets and not config.protocol_targets["http"].url:
+        raise TelemetryConfigError("protocol_targets.http.url is required when HTTP is enabled")
+    if "mqtt" in config.protocol_targets and not config.protocol_targets["mqtt"].broker:
+        raise TelemetryConfigError("protocol_targets.mqtt.broker is required when MQTT is enabled")
+    if "mqtt" in config.protocol_targets and not config.protocol_targets["mqtt"].topic:
+        raise TelemetryConfigError("protocol_targets.mqtt.topic is required when MQTT is enabled")
+    if "grpc" in config.protocol_targets and not config.protocol_targets["grpc"].endpoint:
+        raise TelemetryConfigError("protocol_targets.grpc.endpoint is required when gRPC is enabled")
+
+
+def generate_payload(
+    *,
+    device_index: int,
+    device_type: str,
+    region_id: str,
+    sequence: int,
+    seed: int,
+) -> dict[str, Any]:
+    rng = random.Random(f"{seed}:{device_index}:{sequence}")
+    variants = {
+        "sensor": ("temperature", "humidity", "pressure"),
+        "actuator": ("valve_position", "motor_speed", "command_state"),
+        "gateway": ("uptime", "rx_bytes", "tx_bytes"),
+    }
+    metric = variants.get(device_type, variants["sensor"])[sequence % len(variants.get(device_type, variants["sensor"]))]
+    base_value = rng.uniform(0.0, 100.0)
+    if metric == "rx_bytes":
+        base_value = rng.randint(1024, 65536)
+    elif metric == "tx_bytes":
+        base_value = rng.randint(1024, 65536)
+    elif metric == "uptime":
+        base_value = rng.randint(60, 86400)
+    return {
+        "device_index": device_index,
+        "device_type": device_type,
+        "region_id": region_id,
+        "sequence": sequence,
+        "metric": metric,
+        "value": round(base_value, 3),
+        "unit": unit_for_metric(metric),
+        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
+    }
+
+
+def unit_for_metric(metric: str) -> str:
+    if metric in {"temperature", "humidity", "pressure"}:
+        return "unitless"
+    if metric in {"valve_position", "command_state"}:
+        return "percent"
+    if metric in {"motor_speed"}:
+        return "rpm"
+    if metric in {"uptime"}:
+        return "seconds"
+    return "bytes"
+
+
+def generate_envelope(
+    *,
+    device_id: str,
+    device_type: str,
+    region_id: str,
+    sequence: int,
+    payload: dict[str, Any],
+    seed: int,
+) -> TelemetryEnvelope:
+    envelope = TelemetryEnvelope(
+        device_id=device_id,
+        device_type=device_type,
+        event_type="telemetry.sample",
+        timestamp=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
+        payload=payload,
+        region_id=region_id,
+        origin="iot-device-simulator",
+        idempotency_key=f"{device_id}:{sequence}",
+    )
+    validate_common_envelope(envelope)
+    return envelope
+
+
+def generate_envelopes(config: SimulatorConfig) -> list[TelemetryEnvelope]:
+    envelopes: list[TelemetryEnvelope] = []
+    for device_index in range(config.device_count):
+        device_type = config.device_types[device_index % len(config.device_types)]
+        region_id = config.region_ids[device_index % len(config.region_ids)]
+        device_id = f"{device_type}-{region_id.replace('-', '_')}-{device_index:05d}"
+        payload = generate_payload(
+            device_index=device_index,
+            device_type=device_type,
+            region_id=region_id,
+            sequence=device_index,
+            seed=config.seed,
+        )
+        envelopes.append(
+            generate_envelope(
+                device_id=device_id,
+                device_type=device_type,
+                region_id=region_id,
+                sequence=device_index,
+                payload=payload,
+                seed=config.seed,
+            )
+        )
+    return envelopes
+
+
+def validate_common_envelope(envelope: TelemetryEnvelope | dict[str, Any]) -> None:
+    data = envelope.to_dict() if isinstance(envelope, TelemetryEnvelope) else envelope
+    missing = [field for field in COMMON_ENVELOPE_FIELDS if field not in data]
+    if missing:
+        raise TelemetrySchemaError(f"missing CommonEnvelope field(s): {', '.join(missing)}")
+    for field in ("device_id", "device_type", "event_type", "timestamp", "region_id", "origin", "idempotency_key"):
+        if not isinstance(data[field], str) or not data[field]:
+            raise TelemetrySchemaError(f"{field} must be a non-empty string")
+    if not isinstance(data["payload"], dict):
+        raise TelemetrySchemaError("payload must be a JSON object")
+    encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
+    if len(encoded) > MAX_ENVELOPE_SIZE_BYTES:
+        raise TelemetrySchemaError("CommonEnvelope exceeds 64KB maximum size")
+
+
+def percentile(values: list[float], percentile_value: float) -> float:
+    if not values:
+        return 0.0
+    ordered = sorted(values)
+    if len(ordered) == 1:
+        return round(ordered[0], 3)
+    rank = (len(ordered) - 1) * percentile_value
+    lower = math.floor(rank)
+    upper = math.ceil(rank)
+    if lower == upper:
+        return round(ordered[int(rank)], 3)
+    weight = rank - lower
+    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 3)
+
+
+def percentile_summary(values: list[float]) -> dict[str, float]:
+    return {
+        "p50": percentile(values, 0.50),
+        "p95": percentile(values, 0.95),
+        "p99": percentile(values, 0.99),
+    }
+
+
+def emit_http(envelope: TelemetryEnvelope, target: ProtocolTarget, timeout: float, api_key: str) -> float:
+    if not target.url:
+        raise TelemetryProtocolError("HTTP target URL is not configured")
+    body = envelope.to_bytes()
+    request = Request(
+        target.url,
+        data=body,
+        method="POST",
+        headers={
+            "Content-Type": "application/json",
+            "X-API-Key": api_key,
+            "X-Telemetry-Origin": envelope.origin,
+        },
+    )
+    started = time.perf_counter()
+    try:
+        with urlopen(request, timeout=timeout) as response:
+            if response.status >= 400:
+                raise TelemetryProtocolError(f"HTTP status {response.status}")
+    except HTTPError as error:
+        raise TelemetryProtocolError(f"HTTP protocol failure: HTTPError {error.code}") from error
+    except URLError as error:
+        raise TelemetryProtocolError(f"HTTP connection failure: {error.reason}") from error
+    except OSError as error:
+        raise TelemetryProtocolError(f"HTTP connection failure: {error}") from error
+    return (time.perf_counter() - started) * 1000.0
+
+
+def emit_mqtt(envelope: TelemetryEnvelope, target: ProtocolTarget, timeout: float) -> float:
+    try:
+        from paho.mqtt.client import MQTT_ERR_SUCCESS, Client
+    except ImportError as error:
+        raise TelemetryProtocolError("MQTT live emission requires optional dependency paho-mqtt") from error
+    if not target.broker or not target.topic:
+        raise TelemetryProtocolError("MQTT broker and topic are not configured")
+    host, port_text = target.broker.rsplit(":", 1)
+    port = int(port_text)
+    started = time.perf_counter()
+    try:
+        client = Client()
+        client.connect(host, port, keepalive=10)
+        info = client.publish(target.topic, envelope.to_bytes(), qos=0, retain=False)
+        info.wait_for_publish(timeout=timeout)
+        if info.rc != MQTT_ERR_SUCCESS:
+            raise TelemetryProtocolError(f"MQTT publish failed with rc={info.rc}")
+        client.disconnect()
+    except Exception as error:  # noqa: BLE001 - live protocol failures must be surfaced clearly.
+        try:
+            client.disconnect()
+        except Exception:
+            pass
+        raise TelemetryProtocolError(f"MQTT protocol failure: {error}") from error
+    return (time.perf_counter() - started) * 1000.0
+
+
+def emit_grpc(envelope: TelemetryEnvelope, target: ProtocolTarget, timeout: float) -> float:
+    try:
+        import grpc
+    except ImportError as error:
+        raise TelemetryProtocolError("gRPC live emission requires optional dependency grpcio") from error
+    if not target.endpoint:
+        raise TelemetryProtocolError("gRPC endpoint is not configured")
+    service = target.service or "hpdc.telemetry.v1.TelemetryService"
+    method_name = target.method or f"/{service}/PublishTelemetry"
+    channel = grpc.insecure_channel(target.endpoint)
+    started = time.perf_counter()
+    try:
+        channel.unary_unary(method_name)(
+            envelope.to_bytes(),
+            timeout=timeout,
+        )
+    except grpc.RpcError as error:
+        raise TelemetryProtocolError(f"gRPC protocol failure: {error.details()}") from error
+    except Exception as error:  # noqa: BLE001 - live protocol failures must be surfaced clearly.
+        raise TelemetryProtocolError(f"gRPC protocol failure: {error}") from error
+    finally:
+        channel.close()
+    return (time.perf_counter() - started) * 1000.0
+
+
+def emit_protocol(
+    envelope: TelemetryEnvelope,
+    protocol: str,
+    target: ProtocolTarget,
+    live: bool,
+    api_key: str,
+) -> tuple[float | None, str | None]:
+    if not live:
+        return None, None
+    if protocol == "http":
+        return emit_http(envelope, target, target.timeout, api_key), None
+    if protocol == "mqtt":
+        return emit_mqtt(envelope, target, target.timeout), None
+    if protocol == "grpc":
+        return emit_grpc(envelope, target, target.timeout), None
+    raise TelemetryProtocolError(f"unsupported protocol: {protocol}")
+
+
+def make_protocol_result(protocol: str) -> ProtocolResult:
+    return ProtocolResult(protocol=protocol)
+
+
+def run_simulation(config: SimulatorConfig, mode: str, config_path: str | None = None) -> RunMetrics:
+    validate_config(config)
+    envelopes = generate_envelopes(config)
+    enabled_protocols = config.enabled_protocols()
+    protocol_results: dict[str, ProtocolResult] = {
+        protocol: make_protocol_result(protocol) for protocol in enabled_protocols
+    }
+    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
+    live = mode in {"apply", "live"}
+    try:
+        for envelope in envelopes:
+            try:
+                validate_common_envelope(envelope)
+            except TelemetrySchemaError as error:
+                for protocol in enabled_protocols:
+                    protocol_results[protocol].schema_failures += 1
+                raise TelemetrySchemaError(str(error)) from error
+            for protocol in enabled_protocols:
+                result = protocol_results[protocol]
+                result.planned += 1
+                if not live:
+                    continue
+                try:
+                    latency, _error = emit_protocol(envelope, protocol, config.protocol_targets[protocol], live, config.api_key)
+                except TelemetryProtocolError as error:
+                    result.protocol_failures += 1
+                    raise TelemetryProtocolError(f"{protocol} protocol failure: {error}") from error
+                except OSError as error:
+                    result.connection_failures += 1
+                    raise TelemetryProtocolError(f"{protocol} connection failure: {error}") from error
+                if latency is not None:
+                    result.latencies_ms.append(latency)
+                    result.accepted += 1
+    except (TelemetrySchemaError, TelemetryProtocolError, OSError) as error:
+        write_summary(
+            RunMetrics(
+                mode=mode,
+                target_rps=config.message_rate,
+                messages_generated=len(envelopes),
+                protocol_results=protocol_results,
+                generated_at=generated_at,
+                config_path=config_path or str(config.output_file),
+                summary_path=str(config.output_file),
+            )
+        )
+        raise
+    metrics = RunMetrics(
+        mode=mode,
+        target_rps=config.message_rate,
+        messages_generated=len(envelopes),
+        protocol_results=protocol_results,
+        generated_at=generated_at,
+        config_path=config_path or str(config.output_file),
+        summary_path=str(config.output_file),
+    )
+    write_summary(metrics)
+    return metrics
+
+
+def write_summary(metrics: RunMetrics) -> Path:
+    output_path = Path(metrics.summary_path)
+    output_path.parent.mkdir(parents=True, exist_ok=True)
+    summary = metrics.to_summary()
+    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
+    return output_path
+
+
+def display_path(path: Path) -> str:
+    try:
+        return str(path.resolve().relative_to(Path.cwd()))
+    except ValueError:
+        return str(path)
+
+
+def build_arg_parser() -> argparse.ArgumentParser:
+    parser = argparse.ArgumentParser(description="Generate and optionally emit HPDC telemetry validation payloads.")
+    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to simulator YAML config")
+    parser.add_argument("--offline", action="store_true", default=True, help="Use offline-safe local assumptions")
+    parser.add_argument("--dry-run", action="store_true", default=True, help="Generate and summarize payloads without live protocol emission")
+    parser.add_argument("--check", action="store_true", help="Validate config and write a dry-run summary")
+    parser.add_argument("--apply", action="store_true", help="Emit telemetry through configured live protocols")
+    parser.add_argument("--live", action="store_true", help="Alias for --apply")
+    return parser
+
+
+def main(argv: list[str] | None = None) -> int:
+    parser = build_arg_parser()
+    args = parser.parse_args(argv)
+    mode = "live" if args.live else "apply" if args.apply else "check" if args.check else "dry-run"
+    try:
+        config_path = Path(args.config)
+        if not config_path.exists():
+            print(f"Missing simulator config: {config_path}", file=sys.stderr)
+            return 2
+        config = load_config(config_path)
+        metrics = run_simulation(config, mode, display_path(config_path))
+        summary = metrics.to_summary()
+        print(json.dumps(summary, indent=2, sort_keys=True))
+        return int(summary["exit_status"])
+    except TelemetryConfigError as error:
+        print(f"Configuration error: {error}", file=sys.stderr)
+        return 2
+    except TelemetrySchemaError as error:
+        print(f"Schema error: {error}", file=sys.stderr)
+        return 6
+    except TelemetryProtocolError as error:
+        print(f"Protocol error: {error}", file=sys.stderr)
+        return 5
+    except OSError as error:
+        print(f"System error: {error}", file=sys.stderr)
+        return 1
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())

--- FILE: scripts/simulate-telemetry-dev.py ---
diff --git a/scripts/simulate-telemetry-dev.py b/scripts/simulate-telemetry-dev.py
new file mode 100644
index 0000000..4e34cab
--- /dev/null
+++ b/scripts/simulate-telemetry-dev.py
@@ -0,0 +1,9 @@
+#!/usr/bin/env python3
+"""Human-facing HPDC telemetry simulator entrypoint."""
+
+from __future__ import annotations
+
+from telemetry_simulator import main
+
+if __name__ == "__main__":
+    raise SystemExit(main())

--- FILE: scripts/simulate_telemetry_dev.py ---
diff --git a/scripts/simulate_telemetry_dev.py b/scripts/simulate_telemetry_dev.py
new file mode 100644
index 0000000..e308c2f
--- /dev/null
+++ b/scripts/simulate_telemetry_dev.py
@@ -0,0 +1,9 @@
+#!/usr/bin/env python3
+"""Underscored HPDC telemetry simulator alias."""
+
+from __future__ import annotations
+
+from telemetry_simulator import main
+
+if __name__ == "__main__":
+    raise SystemExit(main())

--- FILE: scripts/steps/16-simulate-telemetry-dev.py ---
diff --git a/scripts/steps/16-simulate-telemetry-dev.py b/scripts/steps/16-simulate-telemetry-dev.py
new file mode 100644
index 0000000..909a8d7
--- /dev/null
+++ b/scripts/steps/16-simulate-telemetry-dev.py
@@ -0,0 +1,29 @@
+#!/usr/bin/env python3
+"""Step 16: Validate HPDC telemetry simulator."""
+
+from __future__ import annotations
+
+import subprocess
+import sys
+from pathlib import Path
+
+ROOT = Path(__file__).resolve().parents[2]
+SCRIPT = ROOT / "scripts" / "simulate-telemetry-dev.py"
+
+STEP_NAME = "16-simulate-telemetry-dev.py"
+STEP_DESCRIPTION = "Validate HPDC telemetry simulator and acceptance harness."
+
+
+def main() -> int:
+    args = ["--offline"]
+    if "--check" in sys.argv:
+        args.append("--check")
+    elif "--apply" in sys.argv:
+        args.append("--apply")
+    else:
+        args.append("--dry-run")
+    return int(subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, check=False).returncode)
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())

--- FILE: output/telemetry-simulator/config.yaml ---
diff --git a/output/telemetry-simulator/config.yaml b/output/telemetry-simulator/config.yaml
new file mode 100644
index 0000000..0602604
--- /dev/null
+++ b/output/telemetry-simulator/config.yaml
@@ -0,0 +1,33 @@
+# Default HPDC telemetry simulator configuration for local validation.
+# Keep secrets local and non-committed in real environments.
+device_count: 10
+message_rate: 100
+device_types:
+  - sensor
+  - actuator
+  - gateway
+region_ids:
+  - us-east-1
+  - eu-west-1
+  - ap-south-1
+protocol_targets:
+  http:
+    url: "http://localhost:8080/telemetry"
+    enabled: true
+    timeout: 2.0
+  mqtt:
+    broker: "localhost:1883"
+    topic: "hpdc/telemetry"
+    enabled: true
+    timeout: 2.0
+  grpc:
+    endpoint: "localhost:50051"
+    service: "hpdc.telemetry.v1.TelemetryService"
+    method: "/hpdc.telemetry.v1.TelemetryService/PublishTelemetry"
+    enabled: true
+    timeout: 2.0
+api_key: "local-dev-api-key"
+timeout: 2.0
+output_path: "output/telemetry-simulator/summary.json"
+seed: 42
+payload_size_limit_bytes: 65536

--- FILE: output/telemetry-simulator/sample-payloads.json ---
diff --git a/output/telemetry-simulator/sample-payloads.json b/output/telemetry-simulator/sample-payloads.json
new file mode 100644
index 0000000..20f16e7
--- /dev/null
+++ b/output/telemetry-simulator/sample-payloads.json
@@ -0,0 +1,61 @@
+{
+  "sample_payloads": [
+    {
+      "device_id": "sensor_us_east_1_00000",
+      "device_type": "sensor",
+      "event_type": "telemetry.sample",
+      "timestamp": "2026-08-05T00:00:00Z",
+      "payload": {
+        "device_index": 0,
+        "device_type": "sensor",
+        "region_id": "us-east-1",
+        "sequence": 0,
+        "metric": "temperature",
+        "value": 23.421,
+        "unit": "unitless",
+        "generated_at": "2026-08-05T00:00:00Z"
+      },
+      "region_id": "us-east-1",
+      "origin": "iot-device-simulator",
+      "idempotency_key": "sensor_us_east_1_00000:0"
+    },
+    {
+      "device_id": "actuator_eu_west_1_00001",
+      "device_type": "actuator",
+      "event_type": "telemetry.sample",
+      "timestamp": "2026-08-05T00:00:01Z",
+      "payload": {
+        "device_index": 1,
+        "device_type": "actuator",
+        "region_id": "eu-west-1",
+        "sequence": 1,
+        "metric": "valve_position",
+        "value": 67.123,
+        "unit": "percent",
+        "generated_at": "2026-08-05T00:00:01Z"
+      },
+      "region_id": "eu-west-1",
+      "origin": "iot-device-simulator",
+      "idempotency_key": "actuator_eu_west_1_00001:1"
+    },
+    {
+      "device_id": "gateway_ap_south_1_00002",
+      "device_type": "gateway",
+      "event_type": "telemetry.sample",
+      "timestamp": "2026-08-05T00:00:02Z",
+      "payload": {
+        "device_index": 2,
+        "device_type": "gateway",
+        "region_id": "ap-south-1",
+        "sequence": 2,
+        "metric": "uptime",
+        "value": 12345,
+        "unit": "seconds",
+        "generated_at": "2026-08-05T00:00:02Z"
+      },
+      "region_id": "ap-south-1",
+      "origin": "iot-device-simulator",
+      "idempotency_key": "gateway_ap_south_1_00002:2"
+    }
+  ]
+}

--- FILE: output/telemetry-simulator/summary.json ---
diff --git a/output/telemetry-simulator/summary.json b/output/telemetry-simulator/summary.json
new file mode 100644
index 0000000..fd4a592
--- /dev/null
+++ b/output/telemetry-simulator/summary.json
@@ -0,0 +1,47 @@
+{
+  "accepted_messages": 0,
+  "config_path": "output/telemetry-simulator/config.yaml",
+  "connection_failures": 0,
+  "error_rate": 0.0,
+  "exit_status": 0,
+  "generated_at": "2026-08-05T07:35:04Z",
+  "latency_percentiles_ms": {
+    "p50": 0.0,
+    "p95": 0.0,
+    "p99": 0.0
+  },
+  "messages_generated": 10,
+  "mode": "dry-run",
+  "protocol_counts": {
+    "grpc": {
+      "accepted": 0,
+      "connection_failures": 0,
+      "planned": 10,
+      "protocol_failures": 0,
+      "rejected": 0,
+      "schema_failures": 0
+    },
+    "http": {
+      "accepted": 0,
+      "connection_failures": 0,
+      "planned": 10,
+      "protocol_failures": 0,
+      "rejected": 0,
+      "schema_failures": 0
+    },
+    "mqtt": {
+      "accepted": 0,
+      "connection_failures": 0,
+      "planned": 10,
+      "protocol_failures": 0,
+      "rejected": 0,
+      "schema_failures": 0
+    }
+  },
+  "protocol_failures": 0,
+  "rejected_messages": 0,
+  "schema_failures": 0,
+  "target_rps": 100,
+  "throughput_messages_per_second": 30.0,
+  "total_messages": 30
+}

--- FILE: docs/telemetry-device-simulator-harness.md ---
diff --git a/docs/telemetry-device-simulator-harness.md b/docs/telemetry-device-simulator-harness.md
new file mode 100644
index 0000000..bbf64d6
--- /dev/null
+++ b/docs/telemetry-device-simulator-harness.md
@@ -0,0 +1,127 @@
+# IoT Device Simulator and Telemetry Acceptance Harness
+
+This document describes the simulator and acceptance harness for Story 4.1. It prepares local telemetry validation for Stories 4.2 through 4.10 without implementing those later platform stories.
+
+## Purpose
+
+The simulator generates CommonEnvelope-compatible telemetry from configurable IoT device profiles and can optionally emit those messages through HTTP, MQTT, and gRPC targets. It is designed for local, offline-first validation where dry-run and check modes do not require internet access or a live Kubernetes cluster.
+
+## Files
+
+- `scripts/simulate-telemetry-dev.py` — primary Python 3 entrypoint.
+- `scripts/simulate_telemetry_dev.py` — underscored alias that delegates to the same implementation.
+- `scripts/telemetry_simulator.py` — simulator core with config parsing, payload generation, metrics, and protocol emission.
+- `output/telemetry-simulator/config.yaml` — default simulator configuration.
+- `output/telemetry-simulator/sample-payloads.json` — sample CommonEnvelope payloads for tests and manual inspection.
+- `output/telemetry-simulator/summary.json` — generated run summary.
+- `tests/test_simulate_telemetry_dev.py` — validation coverage.
+
+## Run modes
+
+Run a dependency-free dry run:
+
+```python
+python3 scripts/simulate-telemetry-dev.py --offline --dry-run
+```
+
+Validate configuration and write a summary without live protocol emission:
+
+```python
+python3 scripts/simulate-telemetry-dev.py --check
+```
+
+Emit telemetry through configured live protocols:
+
+```python
+python3 scripts/simulate-telemetry-dev.py --apply
+```
+
+Use the underscored alias from tests or startup-style commands:
+
+```python
+python3 scripts/simulate_telemetry_dev.py --offline --dry-run
+```
+
+All project automation scripts are Python 3.
+
+## Configuration
+
+`output/telemetry-simulator/config.yaml` controls the validation run.
+
+| Field | Description |
+| --- | --- |
+| `device_count` | Number of deterministic simulated devices. |
+| `message_rate` | Target messages per second for throughput reporting. |
+| `device_types` | Device profile names used for varied payload generation. |
+| `region_ids` | Region IDs used for device and telemetry partitioning. |
+| `protocol_targets.http.url` | Envoy Gateway `/telemetry` endpoint for HTTP live emission. |
+| `protocol_targets.http.enabled` | Whether HTTP is included in the run. |
+| `protocol_targets.mqtt.broker` | MQTT broker host and port, for example `localhost:1883`. |
+| `protocol_targets.mqtt.topic` | MQTT topic for telemetry samples. |
+| `protocol_targets.mqtt.enabled` | Whether MQTT is included in the run. |
+| `protocol_targets.grpc.endpoint` | gRPC endpoint for live telemetry emission. |
+| `protocol_targets.grpc.service` | gRPC service path prefix. |
+| `protocol_targets.grpc.method` | Full gRPC method path. |
+| `protocol_targets.grpc.enabled` | Whether gRPC is included in the run. |
+| `api_key` | Local API key used for Envoy Gateway HTTP telemetry validation. |
+| `timeout` | Default protocol timeout in seconds. |
+| `output_path` | JSON summary output path. |
+| `seed` | Determinism seed for varied but repeatable payloads. |
+| `payload_size_limit_bytes` | Maximum CommonEnvelope size; defaults to the 64KB platform limit. |
+
+## Payload model
+
+Every generated message includes CommonEnvelope-compatible fields:
+
+- `device_id`
+- `device_type`
+- `event_type`
+- `timestamp`
+- `payload`
+- `region_id`
+- `origin`
+- `idempotency_key`
+
+The original payload object is preserved inside `payload`; the simulator wraps it instead of transforming it into a different schema.
+
+## Protocol behavior
+
+### HTTP
+
+Live HTTP emission posts JSON envelopes to the configured Envoy Gateway `/telemetry` endpoint with `X-API-Key`, `Content-Type: application/json`, and `X-Telemetry-Origin`. HTTP errors, connection failures, and protocol errors cause a non-zero exit.
+
+### MQTT
+
+Live MQTT emission requires the optional `paho-mqtt` dependency. If `paho-mqtt` is unavailable, dry-run and check modes still work, while live MQTT emission exits non-zero with a clear dependency error.
+
+### gRPC
+
+Live gRPC emission requires the optional `grpcio` dependency. If `grpcio` is unavailable, dry-run and check modes still work, while live gRPC emission exits non-zero with a clear dependency error.
+
+## Metrics and summary
+
+Each run writes a JSON summary containing:
+
+- protocol counts for HTTP, MQTT, and gRPC
+- total, accepted, and rejected messages
+- connection, schema, and protocol failure counts
+- target RPS and measured throughput
+- p50, p95, and p99 latency percentiles
+- error rate
+- exit status
+
+## Exit codes
+
+- `0` — simulation completed with no failures.
+- `1` — unexpected system error.
+- `2` — missing or invalid configuration.
+- `5` — live protocol failure.
+- `6` — schema or payload generation failure.
+
+## Offline and air-gapped operation
+
+Dry-run and check modes only generate deterministic payloads and write local output. They do not call Kubernetes, reach external registries, or require internet access.
+
+## Relationship to later telemetry stories
+
+This story intentionally does not implement platform ingestion routes, normalization, topic partitioning, back-pressure, Pulsar Functions, ClickHouse tables, KeyDB state, Spin functions, or end-to-end validation. It creates the simulator and acceptance harness so Stories 4.2 through 4.10 can validate ingestion, normalization, routing, and performance behavior against realistic device traffic.

--- FILE: tests/test_simulate_telemetry_dev.py ---
diff --git a/tests/test_simulate_telemetry_dev.py b/tests/test_simulate_telemetry_dev.py
new file mode 100644
index 0000000..d683606
--- /dev/null
+++ b/tests/test_simulate_telemetry_dev.py
@@ -0,0 +1,172 @@
+#!/usr/bin/env python3
+"""Validate the HPDC telemetry simulator harness."""
+
+from __future__ import annotations
+
+import json
+import subprocess
+import sys
+import tempfile
+from pathlib import Path
+
+ROOT = Path(__file__).resolve().parents[1]
+SCRIPTS = ROOT / "scripts"
+if str(SCRIPTS) not in sys.path:
+    sys.path.insert(0, str(SCRIPTS))
+
+from telemetry_simulator import (  # noqa: E402
+    TelemetryConfigError,
+    TelemetrySchemaError,
+    generate_envelope,
+    generate_payload,
+    load_config,
+    parse_simple_yaml,
+    run_simulation,
+    validate_common_envelope,
+)
+
+
+def write_config(path: Path, *, output_path: Path) -> None:
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text(
+        "\n".join(
+            [
+                "device_count: 3",
+                "message_rate: 3",
+                "device_types:",
+                "  - sensor",
+                "  - actuator",
+                "region_ids:",
+                "  - us-east-1",
+                "  - eu-west-1",
+                "protocol_targets:",
+                "  http:",
+                "    url: \"http://localhost:9/telemetry\"",
+                "    enabled: true",
+                "  mqtt:",
+                "    broker: \"localhost:1883\"",
+                "    topic: \"hpdc/telemetry\"",
+                "    enabled: false",
+                "  grpc:",
+                "    endpoint: \"localhost:50051\"",
+                "    enabled: false",
+                "api_key: \"test-api-key\"",
+                f"output_path: \"{output_path.as_posix()}\"",
+                "seed: 7",
+                "",
+            ]
+        ),
+        encoding="utf-8",
+    )
+
+
+def test_parse_simple_yaml() -> None:
+    parsed = parse_simple_yaml(ROOT / "output" / "telemetry-simulator" / "config.yaml")
+    assert parsed["device_count"] == 10
+    assert parsed["protocol_targets"]["http"]["url"].endswith("/telemetry")
+
+
+def test_generate_payload_and_envelope() -> None:
+    payload = generate_payload(device_index=0, device_type="sensor", region_id="us-east-1", sequence=0, seed=42)
+    envelope = generate_envelope(
+        device_id="sensor_us_east_1_00000",
+        device_type="sensor",
+        region_id="payload-region",
+        sequence=0,
+        payload=payload,
+        seed=42,
+    )
+    assert envelope.payload == payload
+    assert envelope.device_id == "sensor_us_east_1_00000"
+    assert envelope.region_id == "payload-region"
+    assert envelope.idempotency_key == "sensor_us_east_1_00000:0"
+    validate_common_envelope(envelope)
+
+
+def test_dry_run_writes_summary() -> None:
+    with tempfile.TemporaryDirectory(prefix="hpdc-telemetry-", dir=ROOT / "output") as temp_dir:
+        config_path = Path(temp_dir) / "config.yaml"
+        output_path = Path(temp_dir) / "summary.json"
+        write_config(config_path, output_path=output_path)
+        metrics = run_simulation(load_config(config_path), "dry-run")
+        summary = metrics.to_summary()
+        assert summary["messages_generated"] == 3
+        assert summary["total_messages"] == 3
+        assert summary["protocol_counts"]["http"]["planned"] == 3
+        assert summary["exit_status"] == 0
+        assert json.loads(output_path.read_text(encoding="utf-8"))["total_messages"] == 3
+
+
+def test_missing_config_returns_config_error() -> None:
+    try:
+        load_config(Path("/tmp/does-not-exist-hpdc-config.yaml"))
+    except TelemetryConfigError:
+        return
+    raise AssertionError("missing config should raise TelemetryConfigError")
+
+
+def test_invalid_envelope_rejected() -> None:
+    try:
+        validate_common_envelope({"device_id": "sensor", "payload": {}})
+    except TelemetrySchemaError:
+        return
+    raise AssertionError("invalid envelope should be rejected")
+
+
+def test_live_connection_failure_exits_non_zero() -> None:
+    with tempfile.TemporaryDirectory(prefix="hpdc-telemetry-", dir=ROOT / "output") as temp_dir:
+        config_path = Path(temp_dir) / "config.yaml"
+        output_path = Path(temp_dir) / "summary.json"
+        write_config(config_path, output_path=output_path)
+        result = subprocess.run(
+            [sys.executable, str(SCRIPTS / "simulate-telemetry-dev.py"), "--config", str(config_path), "--apply"],
+            cwd=ROOT,
+            check=False,
+            capture_output=True,
+            text=True,
+        )
+        assert result.returncode != 0
+        assert "Protocol error" in result.stderr
+        assert json.loads(output_path.read_text(encoding="utf-8"))["exit_status"] == 1
+
+
+def test_alias_delegates_to_same_entrypoint() -> None:
+    with tempfile.TemporaryDirectory(prefix="hpdc-telemetry-", dir=ROOT / "output") as temp_dir:
+        config_path = Path(temp_dir) / "config.yaml"
+        output_path = Path(temp_dir) / "alias-summary.json"
+        write_config(config_path, output_path=output_path)
+        result = subprocess.run(
+            [
+                sys.executable,
+                str(SCRIPTS / "simulate_telemetry_dev.py"),
+                "--config",
+                str(config_path),
+                "--offline",
+                "--dry-run",
+            ],
+            cwd=ROOT,
+            check=False,
+            capture_output=True,
+            text=True,
+        )
+        assert result.returncode == 0, result.stderr
+        assert json.loads(output_path.read_text(encoding="utf-8"))["messages_generated"] == 3
+
+
+def main() -> int:
+    test_parse_simple_yaml()
+    test_generate_payload_and_envelope()
+    test_dry_run_writes_summary()
+    test_missing_config_returns_config_error()
+    test_invalid_envelope_rejected()
+    test_live_connection_failure_exits_non_zero()
+    test_alias_delegates_to_same_entrypoint()
+    subprocess.run([sys.executable, "-m", "py_compile", str(SCRIPTS / "telemetry_simulator.py")], check=True)
+    subprocess.run([sys.executable, "-m", "py_compile", str(SCRIPTS / "simulate-telemetry-dev.py")], check=True)
+    subprocess.run([sys.executable, "-m", "py_compile", str(SCRIPTS / "simulate_telemetry_dev.py")], check=True)
+    print("telemetry simulator harness validation passed.")
+    return 0
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())

--- FILE: output/implementation-artifacts/sprint-status.yaml ---
diff --git a/output/implementation-artifacts/sprint-status.yaml b/output/implementation-artifacts/sprint-status.yaml
index d77b887..860af76 100644
--- a/output/implementation-artifacts/sprint-status.yaml
+++ b/output/implementation-artifacts/sprint-status.yaml
@@ -24,7 +24,7 @@
 #   - done: Finished
 
 generated: 2026-08-04T09:46:14Z
-last_updated: 2026-08-04T11:06:05Z
+last_updated: 2026-08-05T07:35:04Z
 project: High Performance Distributed Cluster (HPDC)
 project_key: NOKEY
 tracking_system: file-system
@@ -58,9 +58,9 @@ development_status:
   3-11-provision-backstage-developer-portal-and-golden-path-templates: done
   3-12-expose-backstage-argo-cd-ui-and-kargo-ui-via-envoy-gateway: done
   3-13-expose-grafana-and-hubble-ui-via-envoy-gateway: done
-  epic-4: backlog
+  epic-4: in-progress
   epic-4-retrospective: optional
-  4-1-build-iot-device-simulator-and-telemetry-acceptance-harness: backlog
+  4-1-build-iot-device-simulator-and-telemetry-acceptance-harness: review
   4-2-accept-telemetry-through-mqtt-http-and-grpc-routes: backlog
   4-3-normalize-telemetry-into-protobuf-commonenvelope: backlog
   4-4-create-partitioned-pulsar-topics-for-telemetry: backlog
