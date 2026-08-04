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