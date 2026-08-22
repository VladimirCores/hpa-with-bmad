# HPDC Bootstrap

## Purpose

Bootstrap scaffolds the High Performance Distributed Cluster repository so the Talos substrate can be provisioned without manual setup or external dependencies.

## Required tooling

- Python 3
- `talosctl`
- Docker

## Project-wide scripting rule

All project automation scripts must be written in Python 3. Shell wrappers are not allowed in the project `scripts/` directory.

## Bootstrap command

Run the scaffold bootstrap once:

```python
python3 scripts/startup.dev.py --offline --check --step 01-bootstrap-dev.py
```

## Dev cluster entry point

Run the ordered HPDC dev setup through the single entry point:

```python
python3 scripts/startup.dev.py --offline --dry-run
```

List the ordered step scripts:

```python
python3 scripts/startup.dev.py --list
```

Each startup run rewrites `output/startup.dev.log` before executing so the selected dry-run, check, or apply flow is reviewable.

## Storage backend selection

The cluster supports two storage backends via the `--storage` flag:

### local-path (default)

Lightweight local-path-provisioner for Docker-based dev clusters:

```bash
python3 scripts/startup.dev.py --offline --apply --storage local-path
```

### rook-ceph

Full Ceph storage with RBD and CephFS (requires block devices):

```bash
python3 scripts/startup.dev.py --offline --apply --storage rook-ceph
```

**Note**: For Docker-based dev clusters, `local-path` is recommended as Rook-Ceph requires dedicated block devices.

## Expected output

```text
01  01-bootstrap-dev.py  Bootstrap the HPDC monorepo scaffold.
02  02-bootstrap-talos-dev.py  Provision the offline Talos dev cluster.
...
15  15-validate-offline-gitops-pipeline.py  Validate offline GitOps pipeline.
```

## Next step

Run `python3 scripts/startup.dev.py --offline --dry-run --step 02-bootstrap-talos-dev.py` to provision the offline Talos dev cluster.
