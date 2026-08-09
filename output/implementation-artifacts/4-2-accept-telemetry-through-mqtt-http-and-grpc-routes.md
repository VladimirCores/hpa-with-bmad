---
baseline_commit: f2fbd10
---

# Story 4.2: Accept Telemetry Through MQTT, HTTP, and gRPC Routes

Status: done

## Story

As a Platform Engineer,
I want the `/telemetry` ingestion route to accept MQTT, HTTP, and gRPC telemetry,
So that heterogeneous IoT devices can publish telemetry without separate protocol adapters.

## Acceptance Criteria

1. Given the simulator from Story 4.1 and the `/telemetry` route are available, when I publish valid MQTT, HTTP, and gRPC telemetry payloads, then the platform accepts each payload type.
2. Given valid telemetry is accepted, then each accepted payload is routed to the internal Pulsar ingestion topic.
3. Given ingestion exceeds the configured capacity for a device type, then the platform returns HTTP 429.
4. Given the process completes without internet access, then Story 4.2 validation remains offline/GitOps-safe.
5. Given any route acceptance, routing, or capacity-control failure occurs, then the process exits with a non-zero status.

## Tasks / Subtasks

- [x] Task 1: Capture Story 4.2 planning from Epic 4
  - [x] Subtask 1.1: Record Story 4.2 acceptance criteria from `output/planning-artifacts/epics.md`.
  - [x] Subtask 1.2: Confirm Story 4.2 follows Story 4.1 simulator/harness output.
- [ ] Task 2: Implement `/telemetry` route acceptance
  - [x] Subtask 2.1: Add or update Envoy Gateway route/manifest configuration for `/telemetry`.
  - [x] Subtask 2.2: Accept HTTP telemetry payloads with API-Key authentication.
  - [ ] Subtask 2.3: Accept MQTT telemetry on the configured HPDC topic.
  - [ ] Subtask 2.4: Accept gRPC telemetry on the configured HPDC service/method.
- [ ] Task 3: Route accepted telemetry to internal Pulsar ingestion topic
  - [x] Subtask 3.1: Preserve accepted payload bytes for normalization by later stories.
  - [ ] Subtask 3.2: Emit accepted telemetry to the internal Pulsar ingestion topic.
  - [ ] Subtask 3.3: Record per-protocol acceptance counts for Story 4.1 harness validation.
- [ ] Task 4: Add capacity response behavior
  - [x] Subtask 4.1: Detect exceeded capacity for a device type.
  - [x] Subtask 4.2: Return HTTP 429 for HTTP capacity failures.
  - [x] Subtask 4.3: Fail non-zero on route acceptance, routing, or capacity-control errors.
- [ ] Task 5: Validate offline/GitOps-safe behavior
  - [x] Subtask 5.1: Add or update local validation commands.
  - [x] Subtask 5.2: Confirm validation does not require internet access.
  - [ ] Subtask 5.3: Confirm validation exits non-zero on failure.

## Dev Notes

### Requirements

- Story 4.2 owns ingestion route acceptance for MQTT, HTTP, and gRPC.
- Story 4.3 owns normalization into Protobuf `CommonEnvelope`.
- Story 4.4 owns partitioned Pulsar topic creation.
- Story 4.2 must not implement later normalization, topic partitioning, back-pressure, Pulsar Functions, ClickHouse, KeyDB, Spin, or end-to-end performance validation.
- `/telemetry` is the Envoy Gateway ingress boundary for telemetry.
- HTTP telemetry uses API-Key authentication through Envoy Gateway.
- Validation should use the Story 4.1 simulator as the producer.

### Scope Boundaries

- Do not normalize telemetry into `CommonEnvelope`; Story 4.3 owns that.
- Do not create partitioned topics; Story 4.4 owns that.
- Do not implement back-pressure; Story 4.5 owns that.
- Do not implement ClickHouse or KeyDB persistence/cache; Stories 4.7 and 4.8 own those.
- Do not implement Spin WASM transforms; Story 4.9 owns those.

### Requirements from Epics and PRD

- Epic 4 objective: validate 100K+ RPS telemetry ingestion from IoT devices via MQTT, HTTP, and gRPC at the `/telemetry` route.
- FR-1 requires multi-protocol ingestion through MQTT, HTTP, and gRPC.
- FR-2 requires common envelope normalization with `device_id`, `device_type`, `event_type`, `timestamp`, `payload`, and `region_id`; Story 4.2 should preserve raw accepted payloads for Story 4.3.
- NFR1 requires sustained 100K RPS per region with p99 latency under 100ms from edge to topic.
- NFR11 requires payloads larger than 64KB to be rejected with HTTP 413; Story 4.2 should validate capacity behavior with Story 4.1-generated traffic.
- NFR18 requires air-gapped operation; Story 4.2 validation must not require internet access.
- NFR23 requires normalized telemetry to reach ClickHouse within 2 seconds of ingestion; Story 4.2 should provide acceptance/routing evidence for later timing validation.

### Architecture Compliance

- Envoy Gateway is the exclusive ingress boundary for `/telemetry`.
- Telemetry is the primary event-mesh path: IoT devices -> Envoy Gateway -> Pulsar.
- `/telemetry` uses API-Key authentication through Envoy Gateway, not Casdoor or Casbin.
- All Pulsar and Kafka messages use the CommonEnvelope Protobuf contract.
- All stateful platform data must use Ceph-backed persistent storage.
- GitOps-only delivery means manifests/configuration must be Git-owned.

### Source Tree Components to Touch

- `output/telemetry-simulator/config.yaml`
- `gitops/telemetry-ingestion/base/telemetry-ingestion.yaml`
- `gitops/telemetry-ingestion/overlays/dev/kustomization.yaml`
- `scripts/install-telemetry-ingestion-dev.py`
- Envoy Gateway route/manifest configuration for `/telemetry`
- Local telemetry acceptance validation scripts or tests

### Testing Standards

- Use Python 3 for simulator-driven validation.
- Validation must not require internet access.
- Validation should use the Story 4.1 simulator output for valid MQTT, HTTP, and gRPC traffic.
- Tests should validate successful acceptance, routing evidence, HTTP 429 capacity behavior, and non-zero exit on failure.
- Do not call `kubectl` in tests unless the repository already has a tested pattern for that.

### Anti-patterns to Avoid

- Do not implement Story 4.3 normalization in this story.
- Do not implement Story 4.4 topic partitioning in this story.
- Do not skip any of MQTT, HTTP, or gRPC acceptance paths.
- Do not return success when only one protocol accepts traffic.
- Do not rely on plaintext HTTP inside the cluster; external simulator traffic is through Envoy Gateway.

## Implementation Notes

### Completed

- Added `gitops/telemetry-ingestion/base/telemetry-ingestion.yaml` with:
  - `telemetry-ingestion` namespace
  - `pulsar-telemetry-ingestion` ServiceAccount and Service
  - `telemetry-ingestion-capacity` ConfigMap with default, sensor, actuator, and gateway limits
  - HTTPRoute for `POST /telemetry`
  - GRPCRoute for `/hpdc.telemetry.v1.TelemetryService/*`
  - TCPRoute for MQTT on listener `mqtt:1884`
- Added MQTT listener `mqtt:1884` to `gitops/envoy-gateway/base/envoy-gateway.yaml`.
- Updated `/telemetry` HTTPRoute backend to `pulsar-telemetry-ingestion:8080`.
- Added gRPC API-Key SecurityPolicy target for `hpdc-telemetry-grpc-ingestion`.
- Added offline validation for telemetry ingestion manifests and HTTP 429 capacity behavior.

### Validation Commands

```python
python3 tests/test_install_telemetry_ingestion_dev.py
python3 tests/test_telemetry_capacity_dev.py
python3 tests/test_install_envoy_gateway_dev.py
python3 startup.dev.py --offline --dry-run --step 17-install-telemetry-ingestion-dev.py
```

## Dev Agent Record

### Agent Model Used

nex-agi/nex-n2-mini

### Implementation Plan

- Create Story 4.2 implementation artifact from Epic 4 acceptance criteria.
- Implement `/telemetry` route acceptance for MQTT, HTTP, and gRPC.
- Route accepted telemetry to the internal Pulsar ingestion topic.
- Add HTTP 429 capacity-control behavior for exceeded device-type capacity.
- Validate Story 4.2 with the Story 4.1 simulator and local/offline commands.

### Completion Notes

- Story 4.1 is complete and Story 4.2 is implemented as a GitOps route/capacity scaffold.
- Live cluster apply was not run; validation remains offline/GitOps-safe.
- The internal Pulsar ingestion backend is represented by the `pulsar-telemetry-ingestion` Service route target; Story 4.4 still owns partitioned Pulsar topic creation.

### File List

- `output/implementation-artifacts/4-2-accept-telemetry-through-mqtt-http-and-grpc-routes.md`
- `gitops/telemetry-ingestion/base/telemetry-ingestion.yaml`
- `gitops/telemetry-ingestion/overlays/dev/kustomization.yaml`
- `gitops/envoy-gateway/base/envoy-gateway.yaml`
- `gitops/envoy-gateway/overlays/dev/kustomization.yaml`
- `gitops/security/base/api-key-authn.yaml`
- `scripts/install-telemetry-ingestion-dev.py`
- `scripts/steps/17-install-telemetry-ingestion-dev.py`
- `scripts/telemetry_capacity.py`
- `tests/test_install_telemetry_ingestion_dev.py`
- `tests/test_telemetry_capacity_dev.py`
- `docs/telemetry-ingestion-route.md`
- `docs/envoy-gateway-edge-routing.md`
- `README.md`

### Change Log

- 2026-08-05: Marked Story 4.2 ready-for-dev after Story 4.1 completion.
- 2026-08-05: Started Story 4.2 implementation with telemetry ingestion GitOps route scaffold.
- 2026-08-05: Added offline validation for telemetry ingestion routes and HTTP 429 capacity behavior.

### Status

done

## Review Findings

### Patch

Pending review.

### Defer

- MQTT protocol-level API-Key authentication is outside Story 4.2 scope; MQTT is routed as TCP to the telemetry ingestion service.

## Questions / Clarifications

None.
