# 3.5 Configure Casbin RBAC Policies

Implemented Casbin RBAC enforcement for domain routes.

## Completed

- Installed Casbin RBAC policy config and ext-authz service.
- Configured base roles and role hierarchy.
- Configured DENY-wins policy defaults.
- Exposed Casbin ext-authz for Envoy Gateway JWT policy checks.

## Validation

Run:

```python
python3 scripts/install-casbin-dev.py --offline --dry-run
```
