# Argo CD ApplicationSet and Sync Waves

Run `python3 scripts/startup.dev.py --offline --dry-run --step 12-install-argocd-dev.py` to validate the Argo CD v3.5 ApplicationSet and sync wave scaffolding.

Required footprint:

- `output/provisioned.yaml` → `provisioned.argocd.value`
- `output/argocd/images/argocd-v3.5.0` → `quay.io/argoproj/argocd:v3.5.0` offline image cache marker
