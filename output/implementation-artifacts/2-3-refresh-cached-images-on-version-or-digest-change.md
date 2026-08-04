# Story 2.3: Refresh Cached Images on Version or Digest Change

Status: done

## Story

As a Platform Engineer,
I want cached images refreshed when versions or digests change,
so the offline GitOps pipeline always uses current trusted artifacts.

## Acceptance Criteria

1. Given a cached image manifest exists, when the refresh script runs, then changed images are listed.
2. Given no digest changes exist, the script reports that no refresh is required.
3. Given required cache metadata is missing, the script exits non-zero.
4. Offline mode does not require internet access.

## Files

- `scripts/refresh-harbor-cache.py`
- `gitops/harbor/base/image-cache-refresh.yaml`
- `gitops/harbor/overlays/refresh/kustomization.yaml`
- `docs/harbor-image-cache-refresh.md`
- `tests/test_refresh_harbor_cache.py`