---
baseline_commit: a6b07e03c8c1cfd889f055bc9137187f93a1820e
---

# Story 4.1: Build IoT Device Simulator and Telemetry Acceptance Harness

Status: done

## Story

As a QA Engineer,
I want a tunable IoT device simulator that can generate telemetry across MQTT, HTTP, and gRPC,
so that the telemetry pipeline can be validated at realistic device counts, message rates, regions, and device types.

## Acceptance Criteria

1. Given a simulator configuration exists with device count, message rate, device types, and region IDs, when I run the simulator against the local dev platform, then it emits telemetry through MQTT, HTTP, and gRPC routes.
2. Given a valid telemetry message is generated, then each message includes `device_id`, `device_type`, `event_type`, `timestamp`, `payload`, and `region_id`, matching the CommonEnvelope fields used by Pulsar and Kafka topics.
3. Given the simulator is configured for a high-rate validation run, then it can target up to 100K RPS or a lower configured rate suitable for local validation.
4. Given the simulator is running, then it exposes throughput, error rate, and latency metrics for the validation run.
5. Given the simulator cannot connect to the local dev platform, then it exits with a non-zero status and prints a clear connection error.
6. Given the simulator detects an invalid generated payload, schema mismatch, protocol failure, or generation failure, then it exits with a non-zero status.
7. Given the simulator is run in offline, dry-run, or check mode, then it does not require internet access and does not require a live Kubernetes cluster.
8. Given the simulator is run against a healthy local dev platform, then it can validate MQTT, HTTP, and gRPC telemetry paths as a prerequisite for Stories 4.2 through 4.10.
9. Given the simulator writes a run summary, then the summary includes protocol counts, device counts, region counts, accepted/rejected counts, latency percentiles, error rate, and exit status.
10. Given the simulator supports both hyphenated and underscored Python entrypoints, then both entrypoints invoke the same implementation module.

## Tasks / Subtasks

- [x] Task 1: Define simulator configuration and payload model (AC: 1, 2, 9)
  - [x] Subtask 1.1: Add a YAML or JSON config for device count, message rate, device types, region IDs, protocol targets, API key source, timeout, and output path.
  - [x] Subtask 1.2: Generate deterministic but varied telemetry payloads across device types and regions.
  - [x] Subtask 1.3: Preserve the original payload bytes or JSON object untransformed inside `payload`.
  - [x] Subtask 1.4: Include RFC3339/ISO-8601 timestamps and CommonEnvelope-compatible fields.

- [x] Task 2: Implement telemetry simulator entrypoints (AC: 1, 2, 5, 6, 10)
  - [x] Subtask 2.1: Add `scripts/simulate-telemetry-dev.py` as the human-facing Python 3 entrypoint.
  - [x] Subtask 2.2: Add `scripts/simulate_telemetry_dev.py` as the underscored alias used by tests and startup-style commands.
  - [x] Subtask 2.3: Implement `--offline`, `--dry-run`, `--check`, and `--apply` or `--live` modes as appropriate.
  - [x] Subtask 2.4: Fail fast when required configuration is missing.
  - [x] Subtask 2.5: Fail non-zero on connection, schema, generation, or protocol errors.

- [x] Task 3: Implement protocol emission paths (AC: 1, 2, 5, 6)
  - [x] Subtask 3.1: Emit HTTP telemetry to the configured `/telemetry` endpoint with `X-API-Key`.
  - [x] Subtask 3.2: Emit MQTT telemetry to the configured broker/topic with the same envelope fields.
  - [x] Subtask 3.3: Emit gRPC telemetry to the configured endpoint using the same logical envelope.
  - [x] Subtask 3.4: Track protocol-specific success and failure counts without conflating them.

- [x] Task 4: Add telemetry metrics and run summary output (AC: 4, 9)
  - [x] Subtask 4.1: Track total messages, accepted messages, rejected messages, connection failures, schema failures, and protocol failures.
  - [x] Subtask 4.2: Track throughput in messages per second and target RPS.
  - [x] Subtask 4.3: Track latency percentiles such as p50, p95, and p99.
  - [x] Subtask 4.4: Write a JSON run summary under `output/telemetry-simulator/` for later validation.

- [x] Task 5: Add offline documentation (AC: 7)
  - [x] Subtask 5.1: Add `docs/telemetry-device-simulator-harness.md`.
  - [x] Subtask 5.2: Document configuration fields, protocol targets, dry-run behavior, live validation behavior, metrics, and exit codes.
  - [x] Subtask 5.3: Document how this simulator prepares Stories 4.2 through 4.10 without implementing those stories.

- [x] Task 6: Add validation coverage (AC: 5, 6, 7, 10)
  - [x] Subtask 6.1: Add `tests/test_simulate_telemetry_dev.py`.
  - [x] Subtask 6.2: Validate config parsing, payload generation, CommonEnvelope fields, summary output, and non-zero failure paths.
  - [x] Subtask 6.3: Validate `--offline --dry-run` or `--check` without requiring a running cluster.
  - [x] Subtask 6.4: Run Python compilation checks for new scripts.

- [x] Task 7: Add startup integration if required by the repo convention (AC: 7)
  - [x] Subtask 7.1: Add `scripts/steps/16-simulate-telemetry-dev.py` only if the dev team expects startup-style orchestration for telemetry validation.
  - [x] Subtask 7.2: Ensure the step forwards `--offline`, `--dry-run`, `--check`, and `--apply` modes consistently.

## Dev Notes

### Requirements

- This story owns the simulator and acceptance harness only. Do not implement Story 4.2 ingestion, Story 4.3 normalization, Story 4.4 topic partitioning, Story 4.5 back-pressure, Story 4.6 Pulsar Functions, Story 4.7 ClickHouse tables, Story 4.8 KeyDB cache, Story 4.9 Spin functions, or Story 4.10 end-to-end validation.
- The simulator must support MQTT, HTTP, and gRPC telemetry emission.
- The simulator must be configurable by device count, message rate, device types, region IDs, protocol targets, API key source, timeout, and output path.
- The simulator must target up to 100K RPS when configured, but must also support lower rates for local validation.
- The simulator must expose throughput, error rate, and latency metrics.
- Offline, dry-run, and check modes must not require internet access or a live Kubernetes cluster.
- The local dev platform must be healthy and reachable before live telemetry validation succeeds.
- The simulator must exit non-zero on connection, schema, generation, or protocol failure.
- All project automation scripts must be Python 3. Do not add shell wrappers in `scripts/`.

### Scope Boundaries

- Do not create MQTT, HTTP, or gRPC protocol adapters for the platform. Those belong to later stories.
- Do not modify Pulsar, Kafka, ClickHouse, KeyDB, Spin, or Pulsar Function code in this story.
- Do not require external package installation in validation. If optional dependencies are needed for gRPC or MQTT, document them clearly and keep dry-run/check paths dependency-free where possible.
- Do not assume internet access. Use local endpoints and local image/cache assumptions only.
- Do not emit raw payloads that are transformed into a different schema before publishing. The CommonEnvelope wraps the original payload.

### Requirements from Epics and PRD

- Epic 4 objective: validate 100K+ RPS telemetry ingestion from IoT devices via MQTT, HTTP, and gRPC at the `/telemetry` route.
- FR-1 requires multi-protocol ingestion through MQTT, HTTP, and gRPC.
- FR-2 requires common envelope normalization with `device_id`, `device_type`, `event_type`, `timestamp`, `payload`, and `region_id`; this story should generate those fields for downstream normalization work.
- NFR1 requires sustained 100K RPS per region with p99 latency under 100ms from edge to topic.
- NFR11 requires payloads larger than 64KB to be rejected with HTTP 413; this story should generate oversized payload cases for validation planning.
- NFR16 requires per-environment retention policies; the simulator should be configurable for dev/staging/prod scenarios.
- NFR18 requires air-gapped operation; dry-run and check modes must not reach external registries or services.
- NFR23 requires normalized telemetry to reach ClickHouse within 2 seconds of ingestion; the simulator should provide load and timing data for this later validation.

### Architecture Compliance

- Envoy Gateway is the exclusive ingress boundary for `/telemetry`; telemetry clients should target the gateway route, not a backend service directly.
- `/telemetry` uses API-Key authentication through Envoy Gateway, not Casdoor or Casbin.
- Telemetry is the primary event-mesh path: IoT devices -> Envoy Gateway -> Pulsar.
- All Pulsar and Kafka messages use the CommonEnvelope Protobuf contract.
- CommonEnvelope fields: `device_id`, `device_type`, `event_type`, `timestamp`, `payload`, `region_id`, `origin`, and `idempotency_key`.
- Max envelope size is 64KB; oversized payloads must be rejected with HTTP 413 by the platform.
- `origin` prevents change-feed mutation loops in later stories.
- `idempotency_key` supports deduplication through KeyDB.
- All stateful platform data must use Ceph-backed persistent storage; this story should not introduce local persistent state outside generated output summaries.
- mTLS is required for inter-service traffic; simulator traffic is external edge traffic through Envoy Gateway.
- GitOps-only delivery means any manifests or configuration generated for the simulator must be Git-owned.

### Source Tree Components to Touch

- `scripts/simulate-telemetry-dev.py` — primary Python 3 simulator entrypoint.
- `scripts/simulate_telemetry_dev.py` — underscored alias entrypoint.
- `output/telemetry-simulator/config.yaml` — default simulator configuration.
- `output/telemetry-simulator/sample-payloads.json` — sample payload corpus for unit tests.
- `output/telemetry-simulator/summary.json` — generated run summary.
- `docs/telemetry-device-simulator-harness.md` — simulator documentation.
- `tests/test_simulate_telemetry_dev.py` — validation tests.
- `scripts/steps/16-simulate-telemetry-dev.py` — optional startup step if the team expects it.

### Testing Standards

- Use Python 3 for the simulator and tests.
- Validation must not require a running Kubernetes cluster.
- Dry-run and check modes must not require internet access.
- Tests should validate:
  - config parsing and validation;
  - CommonEnvelope field generation;
  - HTTP payload generation;
  - MQTT/gRPC planning or dry-run behavior;
  - metrics and summary output;
  - non-zero exit on missing config, connection failure, schema failure, and generation failure.
- Do not call `kubectl` in tests.
- Do not install external Python dependencies unless required and documented.
- Keep simulator output deterministic enough for tests while still varying device count, region, and device type.

### Anti-patterns to Avoid

- Do not implement ingestion routes in this story.
- Do not turn the simulator into a normalization service.
- Do not skip MQTT, HTTP, or gRPC coverage.
- Do not use non-offline dependencies for dry-run/check validation.
- Do not hide failures by returning zero on partial protocol failure.
- Do not rely on plaintext HTTP inside the cluster; external simulator traffic is through Envoy Gateway.
- Do not store secrets in Git. Use environment-backed config references for live telemetry API keys.
- Do not create persistent local state for generated telemetry unless it is an output summary.

## Dev Agent Record

### Agent Model Used

nex-agi/nex-n2-mini

### Implementation Plan

- Added a Python 3 simulator core at `scripts/telemetry_simulator.py` for config parsing, CommonEnvelope generation, protocol planning, metrics collection, and optional live emission.
- Added hyphenated and underscored entrypoints so both invocation styles delegate to the same implementation module.
- Added default dry-run/check configuration and sample payloads under `output/telemetry-simulator/`.
- Implemented HTTP live emission using `urllib.request` and environment-backed API key resolution for `X-API-Key`.
- Implemented JSON summary output with protocol counts, accepted/rejected counts, failure counts, throughput, latency percentiles, error rate, and exit status.
- Added offline documentation and startup integration step.
- Added validation coverage for config parsing, payload generation, CommonEnvelope fields, dry-run summary output, missing config, invalid schema, connection failure, and alias behavior.

### Debug Log References

- Created Story 4.1 context from Epic 4 and PRD telemetry requirements.
- Confirmed no previous Story 4.x implementation files exist in `output/implementation-artifacts`.
- Confirmed no project-level `project-context.md` exists; used epics, PRD, architecture spine, solution design, README, specs, and existing tests as source context.
- Implemented simulator and harness without adding ingestion routes, normalization, Pulsar, Kafka, ClickHouse, KeyDB, Spin, or Pulsar Function changes.

### Completion Notes

- Added simulator configuration, sample payload corpus, and initial summary output under `output/telemetry-simulator/`.
- Implemented deterministic CommonEnvelope generation with device ID, device type, event type, timestamp, payload, region ID, origin, and idempotency key.
- Preserved generated payload objects untransformed inside `payload`.
- Implemented dry-run, check, apply, and live modes through both `scripts/simulate-telemetry-dev.py` and `scripts/simulate_telemetry_dev.py`.
- Implemented HTTP live emission using `urllib.request` and environment-backed API key resolution for `X-API-Key`.
- Implemented optional live MQTT emission through `paho-mqtt` and optional live gRPC emission through `grpcio`; dry-run/check paths remain dependency-free.
- Implemented summary metrics: protocol counts, total/accepted/rejected messages, connection/schema/protocol failures, target RPS, throughput, p50/p95/p99 latency, error rate, and exit status.
- Added failure handling for missing config, invalid CommonEnvelope schema, HTTP connection failure, and protocol errors.
- Added offline documentation at `docs/telemetry-device-simulator-harness.md`.
- Added startup integration step `scripts/steps/16-simulate-telemetry-dev.py`.
- Added validation coverage in `tests/test_simulate_telemetry_dev.py`.
- Validation passed after patch application: `python3 -m compileall -q startup.dev.py scripts tests`, `python3 tests/test_simulate_telemetry_dev.py`, `python3 scripts/simulate-telemetry-dev.py --offline --dry-run`, `python3 startup.dev.py --offline --dry-run --step 16-simulate-telemetry-dev.py`, and `git diff --check`.
- Default dry-run summary now reports `device_count: 10`, `region_count: 3`, `message_rate: 100`, `messages_generated: 100`, and `total_messages: 300` for HTTP/MQTT/gRPC planning.

### File List

- `scripts/telemetry_simulator.py`
- `scripts/simulate-telemetry-dev.py`
- `scripts/simulate_telemetry_dev.py`
- `scripts/steps/16-simulate-telemetry-dev.py`
- `output/telemetry-simulator/config.yaml`
- `output/telemetry-simulator/sample-payloads.json`
- `output/telemetry-simulator/summary.json`
- `docs/telemetry-device-simulator-harness.md`
- `tests/test_simulate_telemetry_dev.py`

### Change Log

- 2026-08-05: Implemented Story 4.1 telemetry simulator and acceptance harness.

### Status

done

## Review Findings

### Patch

- [x] [Review][Patch] gRPC live emission should be protobuf-compatible — Implemented dynamic CommonEnvelope protobuf serialization for gRPC live emission using configured endpoint/service/method and clear dependency errors when `grpcio`/`protobuf` are unavailable.

- [x] [Review][Patch] Summary omits device and region counts, and throughput is synthetic — Added `device_count`, `region_count`, `message_rate`, and measured `elapsed_seconds`; throughput now uses actual elapsed time and the summary artifact has been regenerated.
- [x] [Review][Patch] message_rate is accepted but not enforced, and all protocols disabled can exit 0 — `message_rate` is now validated as >= 1, generation schedules exactly `message_rate` envelopes, and config validation requires at least one protocol enabled.
- [x] [Review][Patch] Connection failures are misclassified as protocol failures — Added `TelemetryConnectionError`; HTTP/MQTT/gRPC connection failures are now counted under `connection_failures` and summarized separately.
- [x] [Review][Patch] Oversized payload validation is incomplete — CommonEnvelope size validation now uses `payload_size_limit_bytes`; oversized envelopes fail as schema errors before live emission.
- [x] [Review][Patch] Config parsing and validation are too permissive — Config keys are validated against the known schema, booleans are parsed explicitly, and required fields are only enforced for enabled protocols.
- [x] [Review][Patch] Determinism and generation-failure handling are incomplete — Timestamps and idempotency keys are deterministic per sequence; generation/schema errors write a summary and exit non-zero.
- [x] [Review][Patch] MQTT and gRPC live paths have robustness gaps — MQTT uses an explicit client id and disconnect cleanup; gRPC uses protobuf-compatible dynamic messages and closes channels in `finally`.
- [x] [Review][Patch] Startup step drops simulator arguments — `scripts/steps/16-simulate-telemetry-dev.py` now forwards `--config` and other simulator arguments while preserving default offline behavior.
- [x] [Review][Patch] Tests do not cover the reviewed failure paths — Added invalid config, oversized payload, deterministic timestamp, connection-failure classification, and summary-count assertions.
- [x] [Review][Patch] Unused implementation artifacts remain — Removed the obsolete import/use paths from `scripts/telemetry_simulator.py` and kept only the active simulator implementation, startup step, docs, tests, and summary output.

### Defer

- [x] [Review][Defer] Committed local API key placeholder — `output/telemetry-simulator/config.yaml` no longer commits a secret-like value; live HTTP telemetry resolves `api_key` from `${HPDC_TELEMETRY_API_KEY}` using `api_key_env: HPDC_TELEMETRY_API_KEY`.

## Questions / Clarifications

None.
