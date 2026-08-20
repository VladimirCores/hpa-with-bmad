# 3.13 Expose Grafana and Hubble UI via Envoy Gateway

Status: superseded — resolved 2026-08-11. See `output/planning-artifacts/implementation-readiness-report-2026-08-07.md`.

Implemented observability UI exposure through Envoy Gateway route scaffolding.

## Completed

- Added Grafana and Hubble UI deployment/service scaffolding.
- Added Envoy Gateway HTTPRoute table for `grafana.hpdc.local` and `hubble.hpdc.local`.
- Configured native tool auth behavior.
- Superseded by Epic 7 Story 7.5 (sole owner of observability UI routes); this record is historical predecessor scaffolding.

## Validation

Run:

```python
python3 scripts/install-observability-ui-routes-dev.py --offline --dry-run
```
