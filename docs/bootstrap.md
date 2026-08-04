# HPDC Bootstrap

## Purpose

Bootstrap scaffolds the High Performance Distributed Cluster repository so the Talos substrate can be provisioned without manual setup or external dependencies.

## Required tooling

- Python 3
- `talosctl`
- QEMU

## Project-wide scripting rule

All project automation scripts must be written in Python 3. Shell wrappers are not allowed in the project `scripts/` directory.

## Bootstrap command

```python
scripts/bootstrap-dev.py
```

## Expected output

```text
HPDC scaffold created.
Required files:
- scripts/bootstrap-dev.py
- scripts/bootstrap_dev.py
- platform/talos/machine-config.yaml
- gitops/platform/base/kustomization.yaml
- gitops/platform/overlays/dev/kustomization.yaml
- gitops/platform/overlays/prod/kustomization.yaml
- docs/bootstrap.md
- tests/test_bootstrap_dev.py
```

## Next step

Run `scripts/bootstrap-dev.py` from Story 1.1, then continue with Story 1.2 to provision the offline Talos dev cluster.
