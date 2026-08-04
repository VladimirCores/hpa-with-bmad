# Offline Rook-Ceph Storage for HPDC

This page documents the Story 1.4 offline Rook-Ceph dev storage bootstrap.

## Purpose

Rook-Ceph provides persistent block and file storage for stateful HPDC workloads on the offline Talos dev cluster. The dev topology is intentionally small and single-node: one Ceph monitor, one manager, one OSD on the persistent QEMU disk image, and RF=1.

## Installation

From the repository root:

```python
./scripts/install-rook-ceph-dev.py --offline --dry-run
```

To apply the GitOps overlay to the Talos cluster after Cilium is installed:

```python
./scripts/install-rook-ceph-dev.py --offline --apply
```

Validation mode:

```python
python3 scripts/install-rook-ceph-dev.py --check
```

## Required Offline Artifacts

The offline installer requires these local artifacts:

- `output/talos/talosconfig` from Story 1.2.
- `output/cilium/images/cilium-agent-v1.19.6` from Story 1.3.
- `output/qemu/talos-v1.img` from Story 1.2.
- `output/rook-ceph/images/rook-ceph-v1.20.3` from this story.

## GitOps Resources

The dev overlay applies:

- `gitops/rook-ceph/base/rook-ceph.yaml`
  - Rook-Ceph operator.
  - CephCluster named `rook-ceph` in namespace `rook-ceph`.
  - Rook-Ceph image `quay.io/rook/ceph:v1.20.3`.
  - One monitor.
  - One OSD on `/dev/disk/by-id/qemu_talos-v1`.
  - `dataDirHostPath: /var/lib/rook`.
  - `dataEmptyDir: false`.
- `gitops/rook-ceph/base/storageclasses.yaml`
  - `rook-ceph-rbd` StorageClass for RBD block volumes.
  - `rook-ceph-cephfs` StorageClass for CephFS file volumes.
  - Immediate volume binding.
  - Volume expansion enabled.

## Persistent Disk Handoff

The persistent QEMU disk image from Story 1.2 is the backing device for the single Ceph OSD. The manifest pins the OSD device to `/dev/disk/by-id/qemu_talos-v1` so the installer can detect whether the persistent disk is already initialized.

Before real apply, the installer checks for an existing `CephCluster` and OSD resources. If they exist, it applies the GitOps overlay without wiping the disk.

## Cleanup Behavior

Destructive OSD initialization or wiping is never automatic. The installer only accepts cleanup behavior when `--cleanup` is provided with `--apply`. In offline validation mode, no QEMU disk image is modified.

## StorageClasses

Use these StorageClasses from applications:

```yaml
storageClassName: rook-ceph-rbd
```

```yaml
storageClassName: rook-ceph-cephfs
```

## Validation

Run:

```python
./scripts/install-rook-ceph-dev.py --offline --dry-run
python3 scripts/install-rook-ceph-dev.py --check
./tests/test_install_rook_ceph_dev.py
python3 -m py_compile scripts/install-rook-ceph-dev.py scripts/install_rook_ceph_dev.py tests/test_install_rook_ceph_dev.py
```

## Constraints

- Offline mode must not require internet access.
- Do not SSH into Talos nodes.
- Do not use hostPath, emptyDir, or local ephemeral volumes for Ceph OSD data.
- Do not wipe persistent QEMU disks unless cleanup is explicitly requested.
- Do not install production RF=3 topology in this dev story.
