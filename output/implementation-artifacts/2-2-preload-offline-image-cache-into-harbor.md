# Story 2.2: Preload Offline Image Cache into Harbor

Status: review

Baseline commit: 6d71180de70ebe43174094a1b0a8d3b2b311c88b

## Story

As a Platform Engineer,
I want a local image cache preloaded into Harbor,
so that GitOps pipelines can build and deploy without internet access.

## Acceptance Criteria

1. Given Harbor is installed and Harbor images are pre-cached locally, when the preload script runs, then offline images are recorded for Harbor ingestion.
2. Given the image cache manifest is present, when the preload script runs in dry-run mode, then it lists each image and expected tag.
3. Given the preload script fails to find the Harbor cache marker or image list, it exits non-zero.
4. The process completes without internet access.

## Tasks/Subtasks

- [x] Implement `scripts/preload_harbor_cache.py` to validate offline Harbor cache prerequisites and generate an ingestion manifest.
- [x] Update Harbor preload GitOps manifests for the offline image cache job.
- [x] Add tests for dry-run image listing, expected tags, missing marker handling, and missing image list handling.
- [x] Document the preload workflow and generated Harbor ingestion manifest.

## Dev Agent Record

### Implementation Plan

- Use local file validation only; no network calls.
- Parse `output/harbor/cache-images.txt` and derive expected tags.
- Record generated Harbor ingestion metadata in `output/harbor/harbor-ingestion-manifest.yaml`.

### Completion Notes

- Implemented offline Harbor cache preload validation and manifest generation.
- Dry-run output lists each cached image and expected tag.
- Missing Harbor marker or image list now fails with a non-zero exit.

## Files

- `scripts/preload-harbor-cache.py`
- `scripts/preload_harbor_cache.py`
- `gitops/harbor/base/preload-images.yaml`
- `gitops/harbor/base/preload-images-job.yaml`
- `gitops/harbor/overlays/preload/kustomization.yaml`
- `docs/harbor-image-cache.md`
- `tests/test_preload_harbor_cache.py`
- `output/harbor/harbor-ingestion-manifest.yaml`

## Change Log

- Added offline Harbor cache preload validation and ingestion manifest recording.
