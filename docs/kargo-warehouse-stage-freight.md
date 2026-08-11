# Kargo Warehouse, Stage, and Freight

Run `python3 scripts/startup.dev.py --offline --dry-run --step 11-install-kargo-dev.py` to validate the Kargo v1.11 Warehouse, Stage, and Freight promotion scaffolding.

Required footprint:

- `output/provisioned.yaml` → `provisioned.kargo.value`
- `output/kargo/images/kargo-v1.11.0` → `ghcr.io/akuity/kargo:v1.11.0` offline image cache marker
