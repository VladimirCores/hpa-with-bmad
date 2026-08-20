# Story 2.6: Configure Kargo Warehouse, Stage, and Freight Promotion

Status: done

## Story

As a Platform Engineer,
I want Kargo Warehouse, Stage, and Freight promotion configured,
so GitOps can promote trusted artifacts through offline stages.

## Acceptance Criteria

1. Given Kargo manifests are applied, then Warehouse, Stage, and Freight resources exist.
2. Given required Kargo artifacts are present, the installer validates them.
3. Given required artifacts are missing, the script exits non-zero.
4. Offline mode does not require internet access.

## Files

- `scripts/install-kargo-dev.py`
- `gitops/kargo/base/kargo.yaml`
- `gitops/kargo/overlays/dev/kustomization.yaml`
- `docs/kargo-warehouse-stage-freight.md`
- `tests/test_install_kargo_dev.py`

## Record Depth

- Shallow record: no Dev Agent Record, review findings, or per-story baseline commit preserved (action item #20).
- Baseline delivery commit: `326b097` ("Add offline GitOps pipeline scaffolding"); subsequent hardening in `9b4626d` (script reorganization) and `d74e7a9` (Kargo v1.11 manifest materialization).
- Behavior asserted via `tests/test_install_kargo_dev.py` and `docs/kargo-warehouse-stage-freight.md` referenced above.