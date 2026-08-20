# Story 2.4: Provision Local Git Mirror for Offline GitOps

Status: done

## Story

As a Platform Engineer,
I want a local Git mirror,
so GitOps manifests and workflows can be accessed without internet access.

## Acceptance Criteria

1. Given the local Git mirror manifest is applied, then a Git server is available in the cluster.
2. Given offline Git artifacts are present, the installer validates required local git mirrors.
3. Given required artifacts are missing, the script exits non-zero.
4. Offline mode does not require internet access.

## Files

- `scripts/provision-local-git-mirror.py`
- `gitops/git/base/git-mirror.yaml`
- `gitops/git/overlays/dev/kustomization.yaml`
- `docs/local-git-mirror.md`
- `tests/test_provision_local_git_mirror.py`

## Record Depth

- Shallow record: no Dev Agent Record, review findings, or per-story baseline commit preserved (action item #20).
- Baseline delivery commit: `326b097` ("Add offline GitOps pipeline scaffolding"); subsequent hardening in `9b4626d` (script reorganization).
- Behavior asserted via `tests/test_provision_local_git_mirror.py` and `docs/local-git-mirror.md` referenced above.