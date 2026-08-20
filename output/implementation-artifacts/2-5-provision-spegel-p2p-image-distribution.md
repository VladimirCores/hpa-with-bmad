# Story 2.5: Provision Spegel P2P Image Distribution

Status: done

## Story

As a Platform Engineer,
I want Spegel P2P image distribution,
so offline clusters can share cached images without repeatedly pulling from the internet.

## Acceptance Criteria

1. Given Spegel images are pre-cached locally, when the Spegel manifest is applied, then Spegel is installed.
2. Given the Spegel cache is ready, when the installer runs, then it validates offline image cache markers.
3. Given required artifacts are missing, the script exits non-zero.
4. Offline mode does not require internet access.

## Files

- `scripts/install-spegel-dev.py`
- `gitops/spegel/base/spegel.yaml`
- `gitops/spegel/overlays/dev/kustomization.yaml`
- `docs/spegel-p2p-image-distribution.md`
- `tests/test_install_spegel_dev.py`

## Record Depth

- Shallow record: no Dev Agent Record, review findings, or per-story baseline commit preserved (action item #20).
- Baseline delivery commit: `326b097` ("Add offline GitOps pipeline scaffolding"); subsequent hardening in `9b4626d` (script reorganization).
- Behavior asserted via `tests/test_install_spegel_dev.py` and `docs/spegel-p2p-image-distribution.md` referenced above.