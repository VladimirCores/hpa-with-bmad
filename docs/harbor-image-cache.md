# Preload Harbor Offline Image Cache

Use `python3 startup.dev.py --offline --dry-run --step 07-preload-harbor-cache.py` to validate the local Harbor image cache manifest.

Required files:

- `output/harbor/images/harbor-core-v2.11.3`
- `output/harbor/cache-images.txt`
- `gitops/harbor/base/preload-images.yaml`
- `gitops/harbor/base/preload-images-job.yaml`
- `gitops/harbor/overlays/preload/kustomization.yaml`
