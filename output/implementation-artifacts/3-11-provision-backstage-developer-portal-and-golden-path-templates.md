# 3.11 Provision Backstage Developer Portal and Golden Path Templates

Status: done

Implemented Backstage developer portal scaffolding.

## Completed

- Added Backstage namespace and ConfigMap.
- Added Backstage deployment and service.
- Added Golden Path documentation.
- Configured Casdoor-native auth references.

## Validation

Run:

```python
python3 scripts/install-backstage-dev.py --offline --dry-run
```
