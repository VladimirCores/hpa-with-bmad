# Story 1.3: Install Offline Cilium eBPF Networking with kube-proxy Replacement

---
baseline_commit: 1cd189fc721bc6812df20dda50d03c0fe3a7546b
---

Status: done

## Story

As a Platform Engineer,
I want to install Cilium 1.19.6 with `kubeProxyReplacement:true` and L2 load balancing on the offline Talos dev cluster,
so that the cluster has service load balancing without kube-proxy and is ready for secure service networking.

## Acceptance Criteria

1. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium manifest from GitOps, then Cilium is installed as the cluster CNI.
2. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium manifest from GitOps, then kube-proxy is disabled or not present.
3. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium manifest from GitOps, then `kubeProxyReplacement:true` is configured.
4. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium manifest from GitOps, then `CiliumL2AnnouncementPolicy` and `CiliumLoadBalancerIPPool` are applied for L2 load balancing.
5. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium manifest from GitOps, then Cilium agent and operator pods are `Ready`.
6. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium manifest from GitOps, then a test service behind a local LoadBalancer can be reached through the L2 load balancer.
7. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium manifest from GitOps, then the process completes without internet access.
8. Given the offline Talos dev cluster from Story 1.2 is healthy, when I apply the Cilium manifest from GitOps, then the script exits with a non-zero status on any failure.

## Tasks / Subtasks

- [x] Task 1: Add Cilium offline GitOps manifests (AC: 1, 2, 3, 4)
  - [x] Subtask 1.1: Add Cilium base Kustomize manifest for Cilium 1.19.6.
  - [x] Subtask 1.2: Configure `kubeProxyReplacement:true` and disable kube-proxy.
  - [x] Subtask 1.3: Add Cilium L2 mode, `CiliumL2AnnouncementPolicy`, and `CiliumLoadBalancerIPPool`.
- [x] Task 2: Add Cilium offline installer script (AC: 5, 6, 7, 8)
  - [x] Subtask 2.1: Add `scripts/install-cilium-dev.py` and `scripts/install_cilium_dev.py`.
  - [x] Subtask 2.2: Add `--offline`, `--dry-run`, `--check`, and `--apply` modes.
  - [x] Subtask 2.3: Fail fast when `talosconfig` or offline Cilium image cache is missing.
- [x] Task 3: Add offline Cilium documentation (AC: 7)
  - [x] Subtask 3.1: Add `docs/cilium-dev-networking.md`.
  - [x] Subtask 3.2: Document required offline artifacts and expected readiness checks.
- [x] Task 4: Add validation coverage (AC: 1, 2, 3, 4, 8)
  - [x] Subtask 4.1: Add `tests/test_install_cilium_dev.py`.
  - [x] Subtask 4.2: Run validation and fix failures.

## Dev Notes

### Requirements

- Continue from Story 1.1 and Story 1.2.
- Cilium version pinned to 1.19.6.
- Talos dev cluster from Story 1.2 is healthy before real apply.
- Offline mode must not require internet access.
- Cilium must run with `kubeProxyReplacement:true`.
- kube-proxy must be disabled or absent.
- Cilium L2 mode must be enabled.
- Apply `CiliumL2AnnouncementPolicy` and `CiliumLoadBalancerIPPool`.
- Do not install Rook-Ceph in this story.
- Do not enable mTLS in this story; Story 1.5 covers Cilium mTLS/SPIFFE/SPIRE.
- Do not use SSH.

### Source Tree Components

- `scripts/install-cilium-dev.py` — Python 3 Cilium installer wrapper.
- `scripts/install_cilium_dev.py` — Python 3 Cilium offline installer.
- `gitops/cilium/base/cilium.yaml` — Cilium 1.19.6 offline manifest.
- `gitops/cilium/base/cilium-l2-policy.yaml` — Cilium L2 load balancing policy.
- `gitops/cilium/overlays/dev/kustomization.yaml` — Cilium dev overlay.
- `docs/cilium-dev-networking.md` — offline Cilium networking documentation.
- `tests/test_install_cilium_dev.py` — validation test for manifests and installer behavior.

### Testing Standards

- Use Python 3 for validation.
- Validation must not require a running Kubernetes cluster.
- Validation should assert manifest content for `kubeProxyReplacement:true`, L2 mode, `CiliumL2AnnouncementPolicy`, and `CiliumLoadBalancerIPPool`.
- Do not call `kubectl` during validation unless `--apply` is explicitly provided.
- Do not install external Python dependencies.

### Anti-patterns to Avoid

- Do not use kube-proxy for service load balancing.
- Do not apply Cilium from remote internet sources in offline mode.
- Do not skip offline image cache validation.
- Do not enable mTLS/SPIFFE/SPIRE in this story.
- Do not overwrite Cilium state without preserving existing cluster configuration.

## Dev Agent Record

### Agent Model Used

nex-agi/nex-n2-mini

### Debug Log References

- Bootstrapped Cilium offline GitOps manifests and installer.
- Added Cilium 1.19.6 dry-run validation path.

### Completion Notes List

- Implemented Story 1.3 acceptance criteria.
- Added Cilium 1.19.6 GitOps manifests for Cilium, L2 announcement policy, and LoadBalancer IP pool.
- Added offline installer entrypoint with `--offline`, `--dry-run`, `--check`, and `--apply` modes.
- Added offline documentation and validation tests.
- Validated with `./scripts/install-cilium-dev.py --offline --dry-run`, `python3 scripts/install-cilium-dev.py --check`, `./tests/test_install_cilium_dev.py`, and `python3 -m py_compile scripts/install-cilium-dev.py scripts/install_cilium_dev.py tests/test_install_cilium_dev.py`.

### File List

- `scripts/install-cilium-dev.py`
- `scripts/install_cilium_dev.py`
- `gitops/cilium/base/cilium.yaml`
- `gitops/cilium/base/cilium-l2-policy.yaml`
- `gitops/cilium/base/cilium-loadbalancer-ippool.yaml`
- `gitops/cilium/overlays/dev/kustomization.yaml`
- `docs/cilium-dev-networking.md`
- `output/cilium/images/cilium-agent-v1.19.6`
- `tests/test_install_cilium_dev.py`
