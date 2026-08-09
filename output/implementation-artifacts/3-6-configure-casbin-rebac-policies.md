# 3.6 Configure Casbin ReBAC Policies

Status: done

Implemented Casbin relationship-based access control.

## Completed

- Added relationship policy data for company admins, clients, devices, and assets.
- Added a ReBAC ext-authz service for hot-reload policy evaluation.
- Configured PostgreSQL-backed relationship storage semantics.

## Validation

Run:

```python
python3 scripts/install-casbin-rebac-dev.py --offline --dry-run
```
