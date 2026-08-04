# Story 2.7: Configure Argo CD ApplicationSet and Sync Waves

Status: done

## Story

As a Platform Engineer,
I want Argo CD ApplicationSet and sync waves configured,
so GitOps resources are synced in the correct order.

## Acceptance Criteria

1. Given Argo CD manifests are applied, then ApplicationSet and sync wave resources exist.
2. Given required Argo artifacts are present, the installer validates them.
3. Given required artifacts are missing, the script exits non-zero.
4. Offline mode does not require internet access.

## Files

- `scripts/install-argocd-dev.py`
- `gitops/argo-cd/base/argocd.yaml`
- `gitops/argo-cd/overlays/dev/kustomization.yaml`
- `docs/argocd-applicationset-sync-waves.md`
- `tests/test_install_argocd_dev.py`