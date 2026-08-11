# Argo Rollouts Progressive Delivery

Run `python3 scripts/startup.dev.py --offline --dry-run --step 13-install-argorollouts-dev.py` to validate Argo Rollouts v1.9 progressive delivery scaffolding.

Required footprint:

- `output/provisioned.yaml` → `provisioned.argo-rollouts.value`
- `output/argo-rollouts/images/argo-rollouts-v1.9.1` → `quay.io/argoproj/argo-rollouts:v1.9.1` offline image cache marker
