# 3.13 Expose Grafana and Hubble UI via Envoy Gateway

Implemented observability UI exposure through Envoy Gateway route scaffolding.

## Completed

- Added Grafana and Hubble UI deployment/service scaffolding.
- Added Envoy Gateway HTTPRoute table for `grafana.hpdc.local` and `hubble.hpdc.local`.
- Configured native tool auth behavior.
- Marked the story as deferred until Epic 7 tools are installed.

## Validation

Run:

```python
python3 scripts/install-observability-ui-routes-dev.py --offline --dry-run
```
