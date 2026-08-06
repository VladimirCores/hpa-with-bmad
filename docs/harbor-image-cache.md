# Record Harbor Offline Image Cache Ingestion Metadata

Use `python3 startup.dev.py --offline --dry-run --step 07-preload-harbor-cache.py` to validate the local Harbor image cache manifest and record Harbor ingestion metadata.

The preload script runs without internet access. It requires:

- `output/harbor/images/harbor-core-v2.11.3`
- `output/harbor/cache-images.txt`
- `gitops/harbor/base/preload-images.yaml`
- `gitops/harbor/base/preload-images-job.yaml`
- `gitops/harbor/overlays/preload/kustomization.yaml`

Dry-run mode lists every cached image with its expected tag and writes `output/harbor/harbor-ingestion-manifest.yaml` for Harbor ingestion planning. This records metadata only; it does not push or load images into Harbor.
