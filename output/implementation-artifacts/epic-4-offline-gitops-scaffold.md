# Epic 4 Consolidated Scaffold — Stories 4.3–4.10

Covers Epic 4 stories 4.3 (CommonEnvelope normalization) through 4.10 (E2E pipeline validation) delivered via a single GitOps/offline-safe scaffold. Stories 4.1 and 4.2 have their own records.

## Summary
- Story 4.10 target: Validate End-to-End Telemetry Pipeline Performance
- Implemented a GitOps/offline-safe Epic 4 scaffold that covers the remaining Epic 4 telemetry, alert, entity, observability, regional, and AI-agent stories without requiring internet access.
- Added a reusable validation script for the Epic 4 scaffold.

## Acceptance Coverage
- Telemetry CommonEnvelope schema and 64KB payload policy are declared in `gitops/epic4/base/epic4-offline-scaffold.yaml`.
- Partitioned Pulsar topics are declared for `device_type` + `region_id` with dev/staging/prod retention support.
- Back-pressure controls, drop metrics, memory ceilings, and retry/drop policy are declared.
- Pulsar Function aggregation/windowing, 25,000-record batches, 500ms flush interval, retry count, and JDBC Sink acknowledgment path are declared.
- ClickHouse `device_metrics` table schema, `ORDER BY (device_type, processed_timestamp)`, retention policies, and Ceph-backed storage are declared.
- KeyDB hot-state caching with 5-minute default TTL and fallback to CouchDB/ClickHouse/YugabyteDB is declared.
- Spin WASM function field mapping, Kafka consumer lag scaling, 10ms latency budget, and downstream transform path are declared.
- Alert, entity, observability, regional, and AI-agent stories are represented as GitOps-safe custom resources and services.

## Files Changed
- `gitops/epic4/base/epic4-offline-scaffold.yaml`
- `gitops/epic4/overlays/dev/kustomization.yaml`
- `gitops/epic4/overlays/staging/kustomization.yaml`
- `gitops/epic4/overlays/prod/kustomization.yaml`
- `scripts/validate-epic4-dev.py`
- `scripts/steps/29-install-epic4-dev.py`
- `scripts/steps/30-validate-epic4-dev.py`
- `tests/test_validate_epic4_dev.py`
- `output/telemetry-validation/telemetry-validation-workspaces.txt`

## Validation
- `python3 tests/test_validate_epic4_dev.py`
- `python3 startup.dev.py --offline --dry-run --step 29-install-epic4-dev.py`
- `python3 startup.dev.py --offline --dry-run --step 30-validate-epic4-dev.py`
- `git diff --check`
