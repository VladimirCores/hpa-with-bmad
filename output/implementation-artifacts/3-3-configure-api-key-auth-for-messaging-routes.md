# 3.3 Configure API-Key Auth for Messaging Routes

Implemented Envoy Gateway API-key authentication for messaging routes.

## Completed

- Added `Secret/security/messaging-api-keys`.
- Added `SecurityPolicy/hpdc-messaging-api-key-authn`.
- Restricted API-key validation to `/events` and `/telemetry`.
- Confirmed Casdoor/Casbin are excluded from messaging route auth.

## Validation

Run:

```python
python3 scripts/install-api-key-auth-dev.py --offline --dry-run
```
