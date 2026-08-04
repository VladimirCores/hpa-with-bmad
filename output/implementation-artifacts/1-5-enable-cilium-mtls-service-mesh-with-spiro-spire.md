# Story 1.5: Enable Cilium mTLS Service Mesh with SPIRE

Status: done

## Story

As a Platform Engineer,
I want to enable Cilium mTLS service mesh with SPIFFE/SPIRE identities on the offline Talos dev cluster,
so that inter-service traffic is encrypted and authenticated without relying on plaintext HTTP inside the cluster.

## Acceptance Criteria

1. Given the offline Talos dev cluster from Story 1.2 is healthy, Cilium networking from Story 1.3 is installed, and Rook-Ceph persistent storage from Story 1.4 is installed, when I apply the Cilium mTLS mesh manifest from GitOps, then Cilium mTLS is enabled for pod-to-pod and service traffic.
2. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium mTLS mesh manifest from GitOps, then SPIRE server and per-node SPIRE agent resources are installed in the `cilium-spire` namespace.
3. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium mTLS mesh manifest from GitOps, then SPIFFE/SPIRE identities are issued to workloads through the SPIRE workload API.
4. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium mTLS mesh manifest from GitOps, then a test service-to-service request succeeds with a valid mTLS identity.
5. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium mTLS mesh manifest from GitOps, then a test service-to-service request fails without a valid mTLS identity.
6. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium mTLS mesh manifest from GitOps, then plaintext HTTP within the cluster is rejected.
7. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium mTLS mesh manifest from GitOps, then the process completes without internet access.
8. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium mTLS mesh manifest from GitOps, then the script exits with a non-zero status on any failure.

## Tasks / Subtasks

- [x] Task 1: Add Cilium mTLS/SPIRE offline GitOps manifests (AC: 1, 2)
  - [x] Subtask 1.1: Add Cilium 1.19.6 mTLS configuration using SPIRE integration.
  - [x] Subtask 1.2: Add SPIRE server and per-node SPIRE agent manifests.
  - [x] Subtask 1.3: Add test service manifests for mTLS success and failure validation.
  - [x] Subtask 1.4: Add Cilium mTLS dev Kustomize overlay.
- [x] Task 2: Add Cilium mTLS offline installer script (AC: 7, 8)
  - [x] Subtask 2.1: Add `scripts/install-cilium-mtls-dev.py` and `scripts/install_cilium_mtls_dev.py`.
  - [x] Subtask 2.2: Add `--offline`, `--dry-run`, `--check`, and `--apply` modes.
  - [x] Subtask 2.3: Fail fast when `talosconfig`, Cilium, Rook-Ceph, or offline SPIRE/Cilium image cache is missing.
- [x] Task 3: Add offline Cilium mTLS documentation (AC: 7)
  - [x] Subtask 3.1: Add `docs/cilium-mtls-service-mesh.md`.
  - [x] Subtask 3.2: Document SPIRE namespace, socket paths, test traffic, and offline image cache requirements.
- [x] Task 4: Add validation coverage (AC: 1, 2, 3, 4, 5, 6, 8)
  - [x] Subtask 4.1: Add `tests/test_install_cilium_mtls_dev.py`.
  - [x] Subtask 4.2: Run validation and fix failures.

## Dev Notes

### Requirements

- Continue from Stories 1.1 through 1.4.
- Cilium version pinned to 1.19.6.
- Cilium kube-proxy replacement and L2 load balancing from Story 1.3 must remain enabled.
- Rook-Ceph from Story 1.4 must be installed before real apply.
- SPIFFE/SPIRE identities must be issued through SPIRE.
- Plaintext HTTP within the cluster must be rejected.
- Offline mode must not require internet access.
- Do not SSH into Talos nodes.

### Source Tree Components

- `scripts/install-cilium-mtls-dev.py` — Python 3 Cilium mTLS offline installer.
- `gitops/cilium/base/cilium-mtls.yaml` — Cilium 1.19.6 mTLS configuration and SPIRE server/agent manifests.
- `gitops/cilium/base/cilium-mtls-test.yaml` — test service manifests for mTLS validation.
- `gitops/cilium/overlays/mesh/kustomization.yaml` — Cilium mTLS dev overlay.
- `docs/cilium-mtls-service-mesh.md` — offline Cilium mTLS service mesh documentation.
- `output/cilium/images/spire-agent-v1.9.6` — offline SPIRE agent image cache marker.
- `output/cilium/images/spire-server-v1.9.6` — offline SPIRE server image cache marker.
- `tests/test_install_cilium_mtls_dev.py` — validation test for manifests and installer behavior.

### Testing Standards

- Use Python 3 for validation.
- Validation must not require a running Kubernetes cluster.
- Validation should assert manifest content for `authentication.enabled`, `authentication.mutual.spire.enabled`, SPIRE server/agent resources, test services, and offline cache markers.
- Do not call `kubectl` during validation unless `--apply` is explicitly provided.
- Do not install external Python dependencies.

### Anti-patterns to Avoid

- Do not enable mTLS in Story 1.3; this story owns the mTLS mesh.
- Do not use non-offline image sources.
- Do not SSH into Talos nodes.
- Do not rely on plaintext HTTP for service-to-service traffic.
- Do not skip SPIRE readiness checks during real apply.

## Dev Agent Record

### Agent Model Used

nex-agi/nex-n2-mini

### Debug Log References

- Bootstrapped Cilium mTLS/SPIRE offline manifests and installer.
- Added Cilium 1.19.6 mTLS dry-run validation path.

### Completion Notes List

- Implemented Story 1.5 acceptance criteria.
- Added Cilium 1.19.6 mTLS configuration with SPIRE integration, SPIRE server StatefulSet, per-node SPIRE agent DaemonSet, and mTLS test services.
- Added offline installer entrypoint with `--offline`, `--dry-run`, `--check`, and `--apply` modes.
- Added offline documentation and validation tests.
- Validated with `./scripts/install-cilium-mtls-dev.py --offline --dry-run`, `python3 scripts/install_cilium_mtls_dev.py --check`, `./tests/test_install_cilium_mtls_dev.py`, and `python3 -m py_compile scripts/install-cilium-mtls-dev.py scripts/install_cilium_mtls_dev.py tests/test_install_cilium_mtls_dev.py`.

### File List

- `scripts/install-cilium-mtls-dev.py`
- `scripts/install_cilium_mtls_dev.py`
- `gitops/cilium/base/cilium-mtls.yaml`
- `gitops/cilium/base/cilium-mtls-test.yaml`
- `gitops/cilium/overlays/mesh/kustomization.yaml`
- `docs/cilium-mtls-service-mesh.md`
- `output/cilium/images/cilium-agent-v1.19.6`
- `output/cilium/images/spire-agent-v1.9.6`
- `output/cilium/images/spire-server-v1.9.6`
- `tests/test_install_cilium_mtls_dev.py`
