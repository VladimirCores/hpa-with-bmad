# Story 1.4: Provision Offline Rook-Ceph Persistent Storage on Persistent QEMU Disks

Status: done

## Story

As a Platform Engineer,
I want to install Rook-Ceph 1.20.3 on the persistent QEMU disk images with RBD and CephFS StorageClasses,
so that all stateful platform components have persistent storage that survives cluster recreation.

## Acceptance Criteria

1. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Rook-Ceph manifest from GitOps, then Rook-Ceph 1.20.3 is installed.
2. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Rook-Ceph manifest from GitOps, then if Rook-Ceph is already initialized on the persistent disks, the script detects the existing `CephCluster` and OSDs and preserves the existing data.
3. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Rook-Ceph manifest from GitOps, then if Rook-Ceph is not initialized, the script creates a CephCluster with OSDs on the persistent QEMU disk devices.
4. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Rook-Ceph manifest from GitOps, then RBD and CephFS StorageClasses are provisioned with dynamic provisioning.
5. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Rook-Ceph manifest from GitOps, then dev topology uses single-OSD Ceph with RF=1 on the persistent disks.
6. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Rook-Ceph manifest from GitOps, then stateful data is stored in Ceph, not in hostPath, emptyDir, or local ephemeral volumes.
7. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Rook-Ceph manifest from GitOps, then destructive OSD initialization or wiping only happens when an explicit cleanup flag is provided.
8. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Rook-Ceph manifest from GitOps, then the process completes without internet access.
9. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Rook-Ceph manifest from GitOps, then the script exits with a non-zero status on any failure.

## Tasks / Subtasks

- [x] Task 1: Add Rook-Ceph offline GitOps manifests (AC: 1, 2, 3, 4, 5, 6)
  - [x] Subtask 1.1: Add Rook-Ceph 1.20.3 operator manifest.
  - [x] Subtask 1.2: Add single-OSD CephCluster manifest for persistent QEMU disks.
  - [x] Subtask 1.3: Add RBD and CephFS StorageClasses.
  - [x] Subtask 1.4: Add Rook-Ceph dev Kustomize overlay.
- [x] Task 2: Add Rook-Ceph offline installer script (AC: 2, 7, 8, 9)
  - [x] Subtask 2.1: Add `scripts/install-rook-ceph-dev.py` and `scripts/install_rook_ceph_dev.py`.
  - [x] Subtask 2.2: Add `--offline`, `--dry-run`, `--check`, `--apply`, and `--cleanup` modes.
  - [x] Subtask 2.3: Fail fast when `talosconfig`, Cilium, QEMU disk images, or offline Rook-Ceph image cache is missing.
- [x] Task 3: Add offline Rook-Ceph documentation (AC: 8)
  - [x] Subtask 3.1: Add `docs/rook-ceph-dev-storage.md`.
  - [x] Subtask 3.2: Document persistent disk handoff, cleanup behavior, and StorageClasses.
- [x] Task 4: Add validation coverage (AC: 1, 3, 4, 5, 6, 7, 9)
  - [x] Subtask 4.1: Add `tests/test_install_rook_ceph_dev.py`.
  - [x] Subtask 4.2: Run validation and fix failures.

## Dev Notes

### Requirements

- Continue from Stories 1.1 through 1.3.
- Rook-Ceph version pinned to 1.20.3.
- Cilium networking from Story 1.3 must be installed before real apply.
- Persistent QEMU disk images from Story 1.2 must be available for OSDs.
- Dev topology uses single OSD Ceph with RF=1.
- RBD and CephFS StorageClasses must be provisioned.
- Stateful data must use Ceph, not hostPath, emptyDir, or local ephemeral volumes.
- Destructive OSD initialization or wiping must only happen with explicit `--cleanup`.
- Offline mode must not require internet access.
- Do not SSH into Talos nodes.

### Source Tree Components

- `scripts/install-rook-ceph-dev.py` — Python 3 Rook-Ceph installer wrapper.
- `scripts/install_rook_ceph_dev.py` — Python 3 Rook-Ceph offline installer.
- `gitops/rook-ceph/base/rook-ceph.yaml` — Rook-Ceph operator and CephCluster manifest.
- `gitops/rook-ceph/base/storageclasses.yaml` — RBD and CephFS StorageClasses.
- `gitops/rook-ceph/overlays/dev/kustomization.yaml` — Rook-Ceph dev overlay.
- `docs/rook-ceph-dev-storage.md` — offline Rook-Ceph storage documentation.
- `output/rook-ceph/images/rook-ceph-v1.20.3` — offline image cache marker.
- `tests/test_install_rook_ceph_dev.py` — validation test for manifests and installer behavior.

### Testing Standards

- Use Python 3 for validation.
- Validation must not require a running Kubernetes cluster.
- Validation should assert manifest content for Rook-Ceph 1.20.3, single OSD, RF=1, RBD, CephFS, and cleanup safeguards.
- Do not call `kubectl` during validation unless `--apply` is explicitly provided.
- Do not install external Python dependencies.

### Anti-patterns to Avoid

- Do not use hostPath or emptyDir for Ceph OSD backing storage.
- Do not wipe QEMU disk images unless `--cleanup` is explicitly provided.
- Do not install production RF=3 topology in this dev story.
- Do not use SSH for OSD initialization.
- Do not overwrite Ceph data without preserving existing CephCluster and OSD state.

## Dev Agent Record

### Agent Model Used

nex-agi/nex-n2-mini

### Debug Log References

- Bootstrapped Rook-Ceph offline GitOps manifests and installer.
- Added Rook-Ceph 1.20.3 dry-run validation path.

### Completion Notes List

- Implemented Story 1.4 acceptance criteria.
- Added Rook-Ceph 1.20.3 GitOps manifests for the operator, CephCluster, and StorageClasses.
- Added offline installer entrypoint with `--offline`, `--dry-run`, `--check`, `--apply`, and `--cleanup` modes.
- Added offline documentation and validation tests.
- Validated with `./scripts/install-rook-ceph-dev.py --offline --dry-run`, `python3 scripts/install-rook-ceph-dev.py --check`, `./tests/test_install_rook_ceph_dev.py`, and `python3 -m py_compile scripts/install-rook-ceph-dev.py scripts/install_rook_ceph_dev.py tests/test_install_rook_ceph_dev.py`.

### File List

- `scripts/install-rook-ceph-dev.py`
- `scripts/install_rook_ceph_dev.py`
- `gitops/rook-ceph/base/rook-ceph.yaml`
- `gitops/rook-ceph/base/storageclasses.yaml`
- `gitops/rook-ceph/overlays/dev/kustomization.yaml`
- `docs/rook-ceph-dev-storage.md`
- `output/rook-ceph/images/rook-ceph-v1.20.3`
- `tests/test_install_rook_ceph_dev.py`
