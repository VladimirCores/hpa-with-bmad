# 3.12 Expose Backstage, Argo CD UI, and Kargo UI via Envoy Gateway

Implemented tool UI exposure through Envoy Gateway.

## Completed

- Added HTTPRoute table for Backstage, Argo CD, and Kargo UI.
- Configured native tool auth behavior.
- Confirmed Casdoor/Casbin ext_authz is not enforced on tool UI routes.

## Validation

Run:

```python
python3 scripts/install-tool-ui-routes-dev.py --offline --dry-run
```
