# Story 1.1: Bootstrap Monorepo Structure & Dev Tooling

---
baseline_commit: 1cd189fc721bc6812df20dda50d03c0fe3a7546b
---

Status: done

## Story

As a Platform Engineer,
I want the HPDC repository scaffolded with Talos machine configs, Kustomize overlays, and a QEMU bootstrap script,
so that I can provision the substrate without manual setup or external dependencies.

## Acceptance Criteria

1. Given the repository is in a clean state, when I run the bootstrap script, then the script creates the standard monorepo directories (`gitops/`, `platform/`, `backend/`, `specs/`, `charts/`, `docs/`).
2. Given the repository is in a clean state, when I run the bootstrap script, then it creates a Talos machine config file under `platform/talos/machine-config.yaml`.
3. Given the repository is in a clean state, when I run the bootstrap script, then it creates a dev bootstrap script under `scripts/bootstrap-dev.sh` using `talosctl cluster create`.
4. Given the repository is in a clean state, when I run the bootstrap script, then it creates a Kustomize base directory under `gitops/platform/base`.
5. Given the repository is in a clean state, when I run the bootstrap script, then it creates a README with the bootstrap command and expected output.
6. Given the repository is in a clean state, when I run the bootstrap script, then the script exits with a non-zero status on any failure.

## Tasks / Subtasks

- [x] Task 1: Create standard monorepo directories and placeholder structure (AC: 1)
  - [x] Subtask 1.1: Create `gitops/`, `platform/`, `backend/`, `specs/`, `charts/`, `docs/`.
  - [x] Subtask 1.2: Create Python 3 bootstrap entrypoint and Python 3 wrapper.
- [x] Task 2: Add Talos substrate scaffolding (AC: 2)
  - [x] Subtask 2.1: Add `platform/talos/machine-config.yaml` for Talos 1.13.7 dev bootstrap.
  - [x] Subtask 2.2: Document Talos bootstrap assumptions and required tooling.
- [x] Task 3: Add Kustomize base scaffolding (AC: 4)
  - [x] Subtask 3.1: Add `gitops/platform/base/kustomization.yaml`.
  - [x] Subtask 3.2: Add placeholder Kustomize overlay files for base/dev/prod.
- [x] Task 4: Add README and bootstrap documentation (AC: 5)
  - [x] Subtask 4.1: Add `docs/bootstrap.md` with bootstrap command and expected output.
  - [x] Subtask 4.2: Add root README bootstrap section if present.
- [x] Task 5: Add validation coverage (AC: 6)
  - [x] Subtask 5.1: Add a test script that verifies required files/directories exist.
  - [x] Subtask 5.2: Run validation and fix failures.

## Dev Notes

### Requirements

- Follow AD-9: monorepo structure uses `gitops/`, `platform/`, `backend/`, `specs/`, `charts/`, `docs/`.
- Follow AD-7: all persistent state uses Ceph RBD; this story only creates scaffolding and does not initialize Ceph.
- Follow AD-8: mTLS is handled later by Cilium SPIFFE/SPIRE; this story does not enable mTLS.
- Follow AD-13: secrets must not be stored in Git, ConfigMaps, or environment variables.
- Follow project-wide scripting rule: bootstrap, cache, verification, and automation scripts must be written in Python 3.
- Talos version pinned to 1.13.7; Cilium 1.19.6; Rook-Ceph 1.20.3.
- Dev bootstrap uses `talosctl cluster create` with QEMU backend.
- This story must not require internet access.
- This story must not implement Story 1.2 cluster provisioning. It only creates the scaffold and wrapper.

### Source Tree Components

- `scripts/bootstrap-dev.py` — Python 3 bootstrap wrapper.
- `scripts/bootstrap_dev.py` — Python 3 bootstrap implementation.
- `platform/talos/machine-config.yaml` — Talos 1.13.7 machine config template.
- `gitops/platform/base/kustomization.yaml` — Kustomize base.
- `gitops/platform/overlays/dev/kustomization.yaml` — dev overlay.
- `gitops/platform/overlays/prod/kustomization.yaml` — prod overlay.
- `docs/bootstrap.md` — bootstrap documentation.
- `tests/test_bootstrap_dev.py` — validation test for required scaffold files.

### Testing Standards

- Use Python 3 for validation.
- Validation must check for required directories and files without requiring `talosctl` to be installed.
- The bootstrap script must be safe to run in a clean repository and must fail fast with a non-zero exit code on missing required environment assumptions.
- Do not run `talosctl` during validation.
- Do not install external Python dependencies.

### Anti-patterns to Avoid

- Do not create all Talos/Cilium/Rook-Ceph manifests required by later stories.
- Do not add secrets, credentials, or real cluster values.
- Do not use `kubectl` or direct cluster commands in bootstrap scripts.
- Do not use non-Python automation for bootstrap or verification.
- Do not overwrite existing files without preserving user changes.

## Dev Agent Record

### Agent Model Used

nex-agi/nex-n2-mini

### Debug Log References

- Bootstrapped scaffold with Python 3 entrypoint and Python 3 wrapper.
- Fixed bootstrap entrypoint syntax before running validation.

### Completion Notes List

- Implemented Story 1.1 acceptance criteria.
- Created standard monorepo directories and bootstrap scaffold.
- Added Python 3 bootstrap implementation plus Python 3 wrapper.
- Added Talos machine config template, Kustomize base/overlays, README, bootstrap documentation, and validation test.
- Validated with `./scripts/bootstrap-dev.py`, `./tests/test_bootstrap_dev.py`, `python3 -m py_compile scripts/bootstrap_dev.py tests/test_bootstrap_dev.py`, and `python3 scripts/bootstrap_dev.py --check`.

### File List

- `scripts/bootstrap-dev.py`
- `scripts/bootstrap_dev.py`
- `platform/talos/machine-config.yaml`
- `gitops/platform/base/kustomization.yaml`
- `gitops/platform/overlays/dev/kustomization.yaml`
- `gitops/platform/overlays/prod/kustomization.yaml`
- `docs/bootstrap.md`
- `README.md`
- `tests/test_bootstrap_dev.py`
