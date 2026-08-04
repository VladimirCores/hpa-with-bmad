# Story 2.2: Preload Offline Image Cache into Harbor

Status: done

## Story

As a Platform Engineer,
I want a local image cache preloaded into Harbor,
so that GitOps pipelines can build and deploy without internet access.

## Acceptance Criteria

1. Given Harbor is installed and Harbor images are pre-cached locally, when the preload script runs, then offline images are recorded for Harbor ingestion.
2. Given the image cache manifest is present, when the preload script runs in dry-run mode, then it lists each image and expected tag.
3. Given the preload script fails to find the Harbor cache marker or image list, it exits non-zero.
4. The process completes without internet access.

## Files

- `scripts/preload-harbor-cache.py`
- `gitops/harbor/base/preload-images.yaml`
- `gitops/harbor/base/preload-images-job.yaml`
- `gitops/harbor/overlays/preload/kustomization.yaml`
- `docs/harbor-image-cache.md`
- `tests/test_preload_harbor_cache.py`