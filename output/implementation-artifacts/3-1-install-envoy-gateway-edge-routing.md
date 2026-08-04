# 3.1 Install Envoy Gateway Edge Routing

Implemented GitOps manifests for Envoy Gateway edge routing.

## Completed

- Installed Envoy Gateway control plane scaffold.
- Added GatewayClass and Gateway for `*.hpdc.local`.
- Added HTTPRoute table for `/data`, `/api`, `/gql`, `/events`, and `/telemetry`.
- Added per-route rate-limit annotation for future Envoy Gateway enforcement.

## Validation

Run:

```python
python3 scripts/install-envoy-gateway-dev.py --offline --dry-run
```
