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