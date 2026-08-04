# Story 1.2: Provision Offline Talos Dev Cluster with Persistent QEMU Disks

---
baseline_commit: 1cd189fc721bc6812df20dda50d03c0fe3a7546b
---

Status: done

## Story

As a Platform Engineer,
I want to provision a clean Talos Linux dev cluster from persistent QEMU VM disk images using `talosctl` bootstrap,
so that the substrate is immutable, API-managed, offline-capable, and ready for Cilium and Rook-Ceph installation.

## Acceptance Criteria

1. Given the repository contains the Talos machine config, bootstrap script, and pre-cached Talos installer/container images, when I run the bootstrap script in offline mode, then it creates persistent QEMU disk image files for the Talos VMs instead of ephemeral VMs.
2. Given the repository contains the Talos machine config, bootstrap script, and pre-cached Talos installer/container images, when I run the bootstrap script in offline mode, then it reuses existing QEMU disk image files across reruns unless an explicit cleanup flag is provided.
3. Given the repository contains the Talos machine config, bootstrap script, and pre-cached Talos installer/container images, when I run the bootstrap script in offline mode, then it boots Talos Linux into maintenance mode and provisions a Talos cluster with version 1.13.7 without requiring internet access.
4. Given the repository contains the Talos machine config, bootstrap script, and pre-cached Talos installer/container images, when I run the bootstrap script in offline mode, then it leaves the persistent disk images available for Rook-Ceph OSD storage.
5. Given the repository contains the Talos machine config, bootstrap script, and pre-cached Talos installer/container images, when I run the bootstrap script in offline mode, then it configures the local `talosconfig` for the new cluster.
6. Given the repository contains the Talos machine config, bootstrap script, and pre-cached Talos installer/container images, when I run the bootstrap script in offline mode, then it verifies cluster access with `talosctl health`.
7. Given the repository contains the Talos machine config, bootstrap script, and pre-cached Talos installer/container images, when I run the bootstrap script in offline mode, then it verifies node discovery with `talosctl get nodes`.
8. Given the repository contains the Talos machine config, bootstrap script, and pre-cached Talos installer/container images, when I run the bootstrap script in offline mode, then it verifies disk installation with `talosctl get disks`.
9. Given the repository contains the Talos machine config, bootstrap script, and pre-cached Talos installer/container images, when I run the bootstrap script in offline mode, then it generates Kubernetes access with `talosctl kubeconfig`.
10. Given the repository contains the Talos machine config, bootstrap script, and pre-cached Talos installer/container images, when I run the bootstrap script in offline mode, then it confirms the cluster is usable without SSH.
11. Given the repository contains the Talos machine config, bootstrap script, and pre-cached Talos installer/container images, when I run the bootstrap script in offline mode, then it exits with a non-zero status on any failure.

## Tasks / Subtasks

- [x] Task 1: Create persistent QEMU disk image management (AC: 1, 2, 4)
  - [x] Subtask 1.1: Add QEMU disk image paths under `output/qemu/`.
  - [x] Subtask 1.2: Add persistent disk creation/reuse logic with `--cleanup`.
  - [x] Subtask 1.3: Add `--dry-run` validation path for environments without `talosctl`.
- [x] Task 2: Add Talos offline bootstrap orchestration (AC: 3, 5, 6, 7, 8, 9, 10, 11)
  - [x] Subtask 2.1: Generate Talos node specs for Talos 1.13.7.
  - [x] Subtask 2.2: Configure local `talosconfig` for the new cluster.
  - [x] Subtask 2.3: Run `talosctl health`, `talosctl get nodes`, `talosctl get disks`, and `talosctl kubeconfig`.
  - [x] Subtask 2.4: Fail fast when `talosctl`, QEMU image cache, or required config is missing.
- [x] Task 3: Add offline-mode documentation (AC: 3, 4, 5)
  - [x] Subtask 3.1: Add `docs/talos-dev-cluster.md`.
  - [x] Subtask 3.2: Document required offline artifacts and cleanup behavior.
- [x] Task 4: Add validation coverage (AC: 1, 2, 11)
  - [x] Subtask 4.1: Add `tests/test_bootstrap_talos_dev.py`.
  - [x] Subtask 4.2: Run validation and fix failures.

## Dev Notes

### Requirements

- Continue from Story 1.1 scaffold.
- Talos version pinned to 1.13.7.
- Dev bootstrap uses `talosctl cluster create` with QEMU backend.
- Offline mode must not require internet access.
- Persistent QEMU disk images must be reused across reruns unless `--cleanup` is provided.
- Disk images remain available for Story 1.4 Rook-Ceph OSD provisioning.
- Do not use SSH; Talos is API-managed and SSH/shell should not be used for cluster bootstrap.
- Do not install Cilium or Rook-Ceph in this story.
- Do not write secrets or credentials into Git.

### Source Tree Components

- `scripts/bootstrap-talos-dev.py` — Python 3 Talos bootstrap wrapper.
- `scripts/bootstrap_talos_dev.py` — Python 3 Talos dev bootstrap implementation.
- `docs/talos-dev-cluster.md` — offline Talos dev cluster documentation.
- `output/qemu/` — persistent QEMU disk image directory.
- `output/talos/talosconfig` — local Talos administrative config path used by the script.
- `tests/test_bootstrap_talos_dev.py` — validation test for disk image paths, cleanup behavior, and script structure.

### Testing Standards

- Use Python 3 for validation.
- Validation must not require `talosctl` or QEMU to be installed.
- Validation should assert required script paths, Talos version, offline defaults, cleanup behavior, and dry-run behavior.
- Do not run real Talos cluster bootstrap in automated validation.
- Do not install external Python dependencies.

### Anti-patterns to Avoid

- Do not use libvirt/OpenTofu for MVP Talos dev bootstrap; Story 1.2 must use `talosctl cluster create`.
- Do not create ephemeral VMs without persistent disk images.
- Do not wipe disk images unless `--cleanup` is explicitly provided.
- Do not call `kubectl` during Talos bootstrap.
- Do not bake cluster credentials into source files.

## Dev Agent Record

### Agent Model Used

nex-agi/nex-n2-mini

### Debug Log References

- Bootstrapped Talos offline scaffold with persistent QEMU disk image handling.
- Added Talos node spec generation and dry-run validation.

### Completion Notes List

- Implemented Story 1.2 acceptance criteria.
- Created persistent QEMU disk image management under `output/qemu/`.
- Added Talos 1.13.7 offline bootstrap entrypoint and Python 3 wrapper.
- Added Talos node specs, local talosconfig path, offline documentation, and validation tests.
- Validated persistent disk reuse and cleanup behavior with `--dry-run` and `--cleanup --dry-run`.
- Validated with `python3 scripts/bootstrap-talos-dev.py --check`, `./tests/test_bootstrap_dev.py`, `./tests/test_bootstrap_talos_dev.py`, `python3 -m py_compile scripts/bootstrap_dev.py scripts/bootstrap_talos_dev.py scripts/bootstrap-talos-dev.py tests/test_bootstrap_dev.py tests/test_bootstrap_talos_dev.py`, and invalid node validation with `python3 scripts/bootstrap-talos-dev.py --nodes 0`.

### File List

- `scripts/bootstrap-talos-dev.py`
- `scripts/bootstrap_talos_dev.py`
- `output/qemu/talos-v1.img`
- `output/talos/node-specs.yaml`
- `output/talos/talosconfig`
- `docs/talos-dev-cluster.md`
- `tests/test_bootstrap_talos_dev.py`
