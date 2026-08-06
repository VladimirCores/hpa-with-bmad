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

- `scripts/preload_harbor_cache.py`
- `scripts/steps/07-preload-harbor-cache.py`
- `scripts/preload-harbor-cache.py`
- `gitops/harbor/base/preload-images.yaml`
- `gitops/harbor/base/preload-images-job.yaml`
- `gitops/harbor/overlays/preload/kustomization.yaml`
- `docs/harbor-image-cache.md`
- `tests/test_preload_harbor_cache.py`
- `output/harbor/harbor-ingestion-manifest.yaml`
- `output/harbor/images/redis-7.2-alpine`
- `output/harbor/images/postgres-15-alpine`

## Change Log

- Added offline Harbor cache preload validation and ingestion manifest recording.

## Review Findings

- [x] [Review][Patch] GitOps preload YAML is invalid — `preload-images.yaml` and `preload-images-job.yaml` have over-indented `command:` blocks that break YAML parsing.
- [x] [Review][Patch] Preload Job does not mount the offline image ConfigMap — manifests reference `/offline-image-cache/images.yaml` without `volumeMounts` or `volumes`.
- [x] [Review][Patch] `--apply` is misleading and not operationally safe — it only writes the ingestion manifest and does not preload images into Harbor.
- [x] [Review][Patch] Generated ingestion manifest omits targets for non-Harbor dependency images without documenting that they are expected-tag-only planning records.
- [x] [Review][Patch] Redis cache marker is inconsistent with `cache-images.txt` and generated manifest.
- [x] [Review][Patch] Story documentation names the wrong script filename.
- [x] [Review][Patch] Tests mutate repository marker and cache-list files during failure-path tests.
- [x] [Review][Patch] Tests only assert representative dry-run/manifest records instead of every cached image and expected tag.
- [x] [Review][Patch] Docs overstate the implementation as Harbor preload when the current change records ingestion metadata only.
- [x] [Review][Patch] CLI defaults make `--offline` effectively no-op and allow mutually exclusive modes to override each other.
- [x] [Review][Patch] Image parsing accepted missing tags and custom temp roots could fail before missing prerequisite reporting.
- [x] [Review][Patch] Failure-path tests did not cover custom roots, missing per-image markers, missing tags, or manifest source assertions.
- [x] [Review][Patch] Script description still said Harbor preload instead of recording ingestion metadata.
