# 3.10 Configure OpenAPI Specification Governance

Status: done

Implemented OpenAPI governance for HPDC edge APIs.

## Completed

- Added `specs/api/hpdc-edge-api.yaml`.
- Added Swagger UI deployment and service.
- Added OpenAPI governance docs.
- Configured `/docs` route contract for Swagger UI.

## Validation

Run:

```python
python3 scripts/install-openapi-dev.py --offline --dry-run
```
