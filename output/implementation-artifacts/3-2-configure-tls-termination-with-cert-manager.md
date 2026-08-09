# 3.2 Configure TLS Termination with cert-manager

Status: done

Implemented cert-manager TLS termination for Envoy Gateway.

## Completed

- Installed cert-manager control plane, webhook, and cainjector manifests.
- Added `ClusterIssuer/hpdc-selfsigned`.
- Added `Certificate/hpdc-edge-tls` for `*.hpdc.local`.
- Confirmed Envoy Gateway references `hpdc-edge-tls`.
- Added HTTP-to-HTTPS redirect listener.

## Validation

Run:

```python
python3 scripts/install-cert-manager-dev.py --offline --dry-run
```
