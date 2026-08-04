# 3.4 Configure Casdoor JWT AuthN for Domain Routes

Implemented centralized Casdoor identity configuration for domain routes.

## Completed

- Installed Casdoor control-plane scaffold.
- Configured OIDC and SAML identity providers.
- Configured refresh-token and session expiration defaults.
- Exposed Casdoor internally for Envoy Gateway JWT validation.

## Validation

Run:

```python
python3 scripts/install-casdoor-dev.py --offline --dry-run
```
