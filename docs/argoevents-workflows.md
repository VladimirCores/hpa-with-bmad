# Argo Events and Workflows

Run `python3 scripts/startup.dev.py --offline --dry-run --step 14-install-argoevents-dev.py` to validate Argo Events v1.9 and workflow scaffolding.

Required footprint:

- `output/provisioned.yaml` → `provisioned.argo-events.value`
- `output/argo-events/images/argo-events-v1.9.11` → `quay.io/argoproj/argo-events:v1.9.11` offline image cache marker
