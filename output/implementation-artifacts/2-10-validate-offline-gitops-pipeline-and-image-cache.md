# Story 2.10: Validate Offline GitOps Pipeline and Image Cache

Status: done

## Story

As a Platform Engineer,
I want the offline GitOps pipeline and image cache validated,
so Epic 2 is production-ready before handoff.

## Acceptance Criteria

1. Given all Epic 2 artifacts exist, when the validation script runs, then all required files and manifests are checked.
2. Given a required artifact is missing, the validation script exits non-zero.
3. Given all checks pass, the script reports the offline GitOps pipeline is ready.
4. Validation must not require internet access.

## Files

- `scripts/validate-offline-gitops-pipeline.py`
- `docs/offline-gitops-validation.md`
- `tests/test_validate_offline_gitops_pipeline.py`

## Record Depth

- Shallow record: no Dev Agent Record, review findings, or per-story baseline commit preserved (action item #20).
- Baseline delivery commit: `326b097` ("Add offline GitOps pipeline scaffolding"); subsequent hardening in `9b4626d` (script reorganization).
- Behavior asserted via `tests/test_validate_offline_gitops_pipeline.py` and `docs/offline-gitops-validation.md` referenced above.