# IoT Device Simulator and Telemetry Acceptance Harness

This document describes the simulator and acceptance harness for Story 4.1. It prepares local telemetry validation for Stories 4.2 through 4.10 without implementing those later platform stories.

## Purpose

The simulator generates CommonEnvelope-compatible telemetry from configurable IoT device profiles and can optionally emit those messages through HTTP, MQTT, and gRPC targets. It is designed for local, offline-first validation where dry-run and check modes do not require internet access or a live Kubernetes cluster.

## Files

- `scripts/simulate-telemetry-dev.py` — primary Python 3 entrypoint.
- `scripts/simulate_telemetry_dev.py` — underscored alias that delegates to the same implementation.
- `scripts/telemetry_simulator.py` — simulator core with config parsing, payload generation, metrics, and protocol emission.
- `output/telemetry-simulator/config.yaml` — default simulator configuration.
- `output/telemetry-simulator/sample-payloads.json` — sample CommonEnvelope payloads for tests and manual inspection.
- `output/telemetry-simulator/summary.json` — generated run summary.
- `tests/test_simulate_telemetry_dev.py` — validation coverage.

## Run modes

Run a dependency-free dry run:

```python
python3 scripts/simulate-telemetry-dev.py --offline --dry-run
```

Validate configuration and write a summary without live protocol emission:

```python
python3 scripts/simulate-telemetry-dev.py --check
```

Emit telemetry through configured live protocols:

```python
python3 scripts/simulate-telemetry-dev.py --apply
```

Use the underscored alias from tests or startup-style commands:

```python
python3 scripts/simulate_telemetry_dev.py --offline --dry-run
```

All project automation scripts are Python 3.

All protocol targets must be disabled explicitly to fail configuration validation; at least one protocol must be enabled for a live run.

## Configuration

`output/telemetry-simulator/config.yaml` controls the validation run.

| Field | Description |
| --- | --- |
| `device_count` | Number of deterministic simulated devices. |
| `message_rate` | Target messages to generate per validation run; must be at least 1. |
| `device_types` | Device profile names used for varied payload generation. |
| `region_ids` | Region IDs used for device and telemetry partitioning. |
| `protocol_targets.http.url` | Envoy Gateway `/telemetry` endpoint for HTTP live emission. |
| `protocol_targets.http.enabled` | Whether HTTP is included in the run. |
| `protocol_targets.mqtt.broker` | MQTT broker host and port, for example `localhost:1883`. |
| `protocol_targets.mqtt.topic` | MQTT topic for telemetry samples. |
| `protocol_targets.mqtt.enabled` | Whether MQTT is included in the run. |
| `protocol_targets.grpc.endpoint` | gRPC endpoint for live telemetry emission. |
| `protocol_targets.grpc.service` | gRPC service path prefix. |
| `protocol_targets.grpc.method` | Full gRPC method path. |
| `protocol_targets.grpc.enabled` | Whether gRPC is included in the run. |
| `api_key` | HTTP API key source for Envoy Gateway validation. Commit `${HPDC_TELEMETRY_API_KEY}` and provide the actual key from the environment for live runs. |
| `api_key_env` | Environment variable name used to resolve `api_key` during live runs. Defaults to `HPDC_TELEMETRY_API_KEY`. |
| `timeout` | Default protocol timeout in seconds. |
| `output_path` | JSON summary output path. |
| `seed` | Determinism seed for varied but repeatable payloads. |
| `payload_size_limit_bytes` | Maximum CommonEnvelope size; defaults to the 64KB platform limit. |

## Payload model

Every generated message includes CommonEnvelope-compatible fields:

- `device_id`
- `device_type`
- `event_type`
- `timestamp`
- `payload`
- `region_id`
- `origin`
- `idempotency_key`

The original payload object is preserved inside `payload`; the simulator wraps it instead of transforming it into a different schema.

## Protocol behavior

### HTTP

Live HTTP emission posts JSON envelopes to the configured Envoy Gateway `/telemetry` endpoint with `X-API-Key`, `Content-Type: application/json`, and `X-Telemetry-Origin`. The committed config uses `${HPDC_TELEMETRY_API_KEY}`; live runs require that environment variable to be set. HTTP errors, connection failures, and protocol errors cause a non-zero exit.

### MQTT

Live MQTT emission requires the optional `paho-mqtt` dependency. If `paho-mqtt` is unavailable, dry-run and check modes still work, while live MQTT emission exits non-zero with a clear dependency error.

### gRPC

Live gRPC emission requires the optional `grpcio` dependency and serializes each CommonEnvelope into a protobuf-compatible dynamic `CommonEnvelope` message before calling the configured unary method. If `grpcio` or `protobuf` is unavailable, dry-run and check modes still work, while live gRPC emission exits non-zero with a clear dependency error.

## Metrics and summary

Each run writes a JSON summary containing:

- configured device, region, and message-rate counts
- protocol counts for HTTP, MQTT, and gRPC
- total, accepted, rejected, and schema-failed messages
- connection, schema, and protocol failure counts
- target RPS and measured throughput
- p50, p95, and p99 latency percentiles
- error rate
- exit status

## Exit codes

- `0` — simulation completed with no failures.
- `1` — unexpected system error.
- `2` — missing or invalid configuration.
- `5` — live protocol failure.
- `6` — schema or payload generation failure.

## Offline and air-gapped operation

Dry-run and check modes only generate deterministic payloads and write local output. They do not call Kubernetes, reach external registries, or require internet access.

## Relationship to later telemetry stories

This story intentionally does not implement platform ingestion routes, normalization, topic partitioning, back-pressure, Pulsar Functions, ClickHouse tables, KeyDB state, Spin functions, or end-to-end validation. It creates the simulator and acceptance harness so Stories 4.2 through 4.10 can validate ingestion, normalization, routing, and performance behavior against realistic device traffic.
