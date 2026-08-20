# Story 2.8: Configure Argo Rollouts Progressive Delivery

Status: done

## Story

As a Platform Engineer,
I want Argo Rollouts progressive delivery configured,
so workloads can roll out gradually and safely.

## Acceptance Criteria

1. Given Argo Rollouts manifests are applied, then Rollout and progressive delivery resources exist.
2. Given required Argo Rollouts artifacts are present, the installer validates them.
3. Given required artifacts are missing, the script exits non-zero.
4. Offline mode does not require internet access.

## Files

- `scripts/install-argorollouts-dev.py`
- `gitops/argo-rollouts/base/argorollouts.yaml`
- `gitops/argo-rollouts/overlays/dev/kustomization.yaml`
- `docs/argorollouts-progressive-delivery.md`
- `tests/test_install_argorollouts_dev.py`

## Record Depth

- Shallow record: no Dev Agent Record, review findings, or per-story baseline commit preserved (action item #20).
- Baseline delivery commit: `326b097` ("Add offline GitOps pipeline scaffolding"); subsequent hardening in `9b4626d` (script reorganization) and `d74e7a9` (Argo Rollouts v1.9.1 manifest materialization).
- Behavior asserted via `tests/test_install_argorollouts_dev.py` and `docs/argorollouts-progressive-delivery.md` referenced above.