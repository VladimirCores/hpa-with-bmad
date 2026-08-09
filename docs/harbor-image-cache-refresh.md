# Refresh Harbor Cached Images

Run `python3 startup.dev.py --offline --dry-run --step 08-refresh-harbor-cache.py` to validate cached Harbor image metadata and detect digest changes.

Required files:

- `output/provisioned.yaml` (`harbor-image-cache` entry records image digests and change state)
- `gitops/harbor/base/image-cache-refresh.yaml`
