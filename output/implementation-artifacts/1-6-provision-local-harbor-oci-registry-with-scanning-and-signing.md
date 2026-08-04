# Story 1.6: Provision Local Harbor OCI Registry with Scanning and Signing

Status: done

## Story

As a Platform Engineer,
I want to install Harbor 2.11.3 as a local OCI registry with Trivy/Clair scanning and Cosign signature verification,
so that GitOps workloads can pull trusted images and charts without internet access.

## Acceptance Criteria

1. Given the offline Talos dev cluster from Story 1.2 is healthy and Harbor images are pre-cached locally, when I apply the Harbor manifest from GitOps, then Harbor 2.11.3 is installed as a local OCI registry.
2. Given the offline Talos dev cluster from Story 1.2 is healthy and Harbor images are pre-cached locally, when I apply the Harbor manifest from GitOps, then Trivy/Clair scanning is enabled on image push.
3. Given the offline Talos dev cluster from Story 1.2 is healthy and Harbor images are pre-cached locally, when I apply the Harbor manifest from GitOps, then Cosign signature verification is enabled for image pulls.
4. Given the offline Talos dev cluster from Story 1.2 is healthy and Harbor images are pre-cached locally, when I apply the Harbor manifest from GitOps, then Harbor is available through a ClusterIP or LoadBalancer service.
5. Given the offline Talos dev cluster from Story 1.2 is healthy and Harbor images are pre-cached locally, when I apply the Harbor manifest from GitOps, then the process completes without internet access.
6. Given the offline Talos dev cluster from Story 1.2 is healthy and Harbor images are pre-cached locally, when I apply the Harbor manifest from GitOps, then the script exits with a non-zero status on any failure.

## Tasks / Subtasks

- [x] Task 1: Add Harbor offline GitOps manifests (AC: 1, 2, 3, 4)
  - [x] Subtask 1.1: Add Harbor 2.11.3 core, registry, jobservice, chart repository, Trivy, Redis, and PostgreSQL resources.
  - [x] Subtask 1.2: Add persistent Rook-Ceph-backed PVCs for Harbor state.
  - [x] Subtask 1.3: Add Harbor values/config for scanning and signature verification.
  - [x] Subtask 1.4: Add Harbor dev Kustomize overlay.
- [x] Task 2: Add Harbor offline installer script (AC: 5, 6)
  - [x] Subtask 2.1: Add `scripts/install-harbor-dev.py` and `scripts/install_harbor_dev.py`.
  - [x] Subtask 2.2: Add `--offline`, `--dry-run`, `--check`, and `--apply` modes.
  - [x] Subtask 2.3: Fail fast when `talosconfig`, Rook-Ceph, or offline Harbor image cache is missing.
- [x] Task 3: Add offline Harbor documentation (AC: 5)
  - [x] Subtask 3.1: Add `docs/harbor-dev-registry.md`.
  - [x] Subtask 3.2: Document image cache, registry service, scanning, signing, and offline constraints.
- [x] Task 4: Add validation coverage (AC: 1, 2, 3, 4, 6)
  - [x] Subtask 4.1: Add `tests/test_install_harbor_dev.py`.
  - [x] Subtask 4.2: Run validation and fix failures.

## Dev Notes

### Requirements

- Continue from Stories 1.1 through 1.5.
- Harbor version pinned to 2.11.3.
- Cilium networking from Story 1.3 must be installed before real apply.
- Rook-Ceph persistent storage from Story 1.4 must be installed before real apply.
- Offline mode must not require internet access.
- Do not SSH into Talos nodes.

### Source Tree Components

- `scripts/install-harbor-dev.py` — Python 3 Harbor offline installer wrapper.
- `scripts/install_harbor_dev.py` — Python 3 Harbor offline installer implementation.
- `gitops/harbor/base/harbor.yaml` — Harbor operator/core deployment manifest.
- `gitops/harbor/base/harbor-values.yaml` — Harbor runtime configuration.
- `gitops/harbor/base/harbor-pvcs.yaml` — Rook-Ceph-backed PVCs.
- `gitops/harbor/overlays/dev/kustomization.yaml` — Harbor dev overlay.
- `docs/harbor-dev-registry.md` — offline Harbor registry documentation.
- `output/harbor/images/harbor-core-v2.11.3` — offline Harbor image cache marker.
- `output/harbor/images/harbor-registry-v2.11.3` — offline Harbor image cache marker.
- `tests/test_install_harbor_dev.py` — validation test for manifests and installer behavior.

### Testing Standards

- Use Python 3 for validation.
- Validation must not require a running Kubernetes cluster.
- Validation should assert manifest content for Harbor 2.11.3, Trivy/Clair scanning, Cosign signature verification, persistent PVCs, and offline cache markers.
- Do not call `kubectl` during validation unless `--apply` is explicitly provided.
- Do not install external Python dependencies.

### Anti-patterns to Avoid

- Do not use internet image sources in offline mode.
- Do not use hostPath or local ephemeral storage for Harbor state.
- Do not SSH into Talos nodes.
- Do not skip offline image cache validation.

## Dev Agent Record

### Agent Model Used

nex-agi/nex-n2-mini

### Debug Log References

- Bootstrapped Harbor offline GitOps manifests and installer.
- Added Harbor 2.11.3 dry-run validation path.

### Completion Notes List

- Implemented Story 1.6 acceptance criteria.
- Added Harbor 2.11.3 GitOps manifests for core, registry, jobservice, Trivy adapter, ChartMuseum, Redis, PostgreSQL, services, values, and PVCs.
- Added offline installer entrypoint with `--offline`, `--dry-run`, `--check`, and `--apply` modes.
- Added offline documentation and validation tests.
- Validated with `./scripts/install-harbor-dev.py --offline --dry-run`, `python3 scripts/install_harbor_dev.py --check`, `./tests/test_install_harbor_dev.py`, and `python3 -m py_compile scripts/install-harbor-dev.py scripts/install_harbor_dev.py tests/test_install_harbor_dev.py`.

### File List

- `scripts/install-harbor-dev.py`
- `scripts/install_harbor_dev.py`
- `gitops/harbor/base/harbor.yaml`
- `gitops/harbor/base/harbor-values.yaml`
- `gitops/harbor/base/harbor-pvcs.yaml`
- `gitops/harbor/overlays/dev/kustomization.yaml`
- `docs/harbor-dev-registry.md`
- `output/harbor/images/harbor-core-v2.11.3`
- `output/harbor/images/harbor-registry-v2.11.3`
- `output/harbor/images/harbor-jobservice-v2.11.3`
- `output/harbor/images/harbor-trivy-adapter-v2.11.3`
- `output/harbor/images/harbor-chartmuseum-v2.11.3`
- `output/harbor/images/harbor-redis-v1.23`
- `output/harbor/images/harbor-postgresql-v15`
- `tests/test_install_harbor_dev.py`
