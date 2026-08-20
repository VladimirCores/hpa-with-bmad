# Story 2.9: Configure Argo Events and Workflows

Status: done

## Story

As a Platform Engineer,
I want Argo Events and workflows configured,
so GitOps pipelines can react to events and automate offline delivery.

## Acceptance Criteria

1. Given Argo Events manifests are applied, then EventSource, Sensor, and Workflow resources exist.
2. Given required Argo Events artifacts are present, the installer validates them.
3. Given required artifacts are missing, the script exits non-zero.
4. Offline mode does not require internet access.

## Files

- `scripts/install-argoevents-dev.py`
- `gitops/argo-events/base/argoevents.yaml`
- `gitops/argo-events/overlays/dev/kustomization.yaml`
- `docs/argoevents-workflows.md`
- `tests/test_install_argoevents_dev.py`

## Record Depth

- Shallow record: no Dev Agent Record, review findings, or per-story baseline commit preserved (action item #20).
- Baseline delivery commit: `326b097` ("Add offline GitOps pipeline scaffolding"); subsequent hardening in `9b4626d` (script reorganization) and `d74e7a9` (Argo Events v1.9.11 manifest materialization).
- Behavior asserted via `tests/test_install_argoevents_dev.py` and `docs/argoevents-workflows.md` referenced above.