# 3.7 Configure Casbin ABAC Policies

Status: done

Implemented Casbin attribute-based access control.

## Completed

- Added ABAC attribute and policy data.
- Added ABAC ext-authz service.
- Configured combined RBAC + ReBAC + ABAC evaluation semantics.
- Preserved DENY-wins behavior.

## Validation

Run:

```python
python3 scripts/install-casbin-abac-dev.py --offline --dry-run
```
