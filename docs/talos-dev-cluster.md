# Provision the Offline Talos Dev Cluster

## Purpose

This document describes the Talos dev bootstrap path for HPDC. It provisions a local Talos Linux cluster from persistent QEMU disk images using `talosctl cluster create` and prepares the cluster for Cilium and Rook-Ceph installation.

## Required tooling

- Python 3
- `talosctl`
- QEMU or `qemu-img`
- Pre-cached Talos installer image

## Offline artifact

The offline Talos installer image must be present before running bootstrap:

```text
output/qemu/images/talos-v1.13.7.iso
```

If the image is missing, the bootstrap exits with a non-zero status because offline mode cannot download it.

## Persistent disk images

Persistent QEMU disk images are stored under:

```text
output/qemu/talos-v1.img
output/qemu/talos-v2.img
output/qemu/talos-v3.img
```

The default bootstrap provisions one Talos VM. Add `--nodes N` to provision multiple VMs.

Disk images are reused across reruns. Provide `--cleanup` to remove existing disk images before provisioning.

## Bootstrap command

```python
scripts/bootstrap-talos-dev.py --offline
```

## Validation command

```python
python3 scripts/bootstrap-talos-dev.py --check
python3 scripts/bootstrap-talos-dev.py --offline --dry-run
```

## Expected output

```text
$ python3 scripts/bootstrap-talos-dev.py --offline --dry-run
Talos dev cluster bootstrap dry-run passed.
Persistent QEMU disks: ['output/qemu/talos-v1.img']
Talos version: 1.13.7
Node specs: output/talos/node-specs.yaml
talosconfig: output/talos/talosconfig
```

## Talos bootstrap sequence

The real bootstrap sequence is:

1. Create or reuse persistent QEMU disk images.
2. Generate `output/talos/node-specs.yaml` for Talos 1.13.7.
3. Ensure `output/talos/talosconfig` exists.
4. Run `talosctl cluster create --offline --nodes file://output/talos/node-specs.yaml --talos-version 1.13.7`.
5. Run `talosctl kubeconfig --output output/talos/talosconfig`.
6. Run `talosctl health`.
7. Run `talosctl get nodes`.
8. Run `talosctl get disks`.
9. Confirm the cluster is usable without SSH.

## Rook-Ceph handoff

Story 1.4 should use the persistent QEMU disk images under `output/qemu/` as Rook-Ceph OSD backing storage. Do not wipe these disks unless an explicit cleanup operation is requested.
