# Cilium mTLS Service Mesh with SPIRE

This page documents the Story 1.5 offline Cilium mTLS service mesh bootstrap.

## Purpose

Cilium mTLS uses SPIFFE identities and SPIRE to issue workload certificates. In HPDC, the Cilium agent and operator connect to the per-node SPIRE agent socket to validate workload identities and enforce mTLS for pod-to-pod and service traffic.

## Installation

From the repository root:

```python
python3 scripts/startup.dev.py --offline --dry-run --step 04-install-cilium-mtls-dev.py
```

To apply the GitOps overlay to the Talos cluster after Story 1.3 and Story 1.4 are complete:

```python
python3 scripts/startup.dev.py --offline --apply --step 04-install-cilium-mtls-dev.py
```

Validation mode:

```python
python3 scripts/startup.dev.py --offline --check --step 04-install-cilium-mtls-dev.py
```

## Required Offline Artifacts

The offline installer requires these local artifacts:

- `output/talos/talosconfig` from Story 1.2.
- `output/cilium/images/cilium-agent-v1.19.6` from Story 1.3.
- `output/cilium/images/spire-agent-v1.9.6` from this story.
- `output/cilium/images/spire-server-v1.9.6` from this story.
- `output/rook-ceph/images/rook-ceph-v1.20.3` from Story 1.4.

## GitOps Resources

The dev overlay applies:

- `gitops/cilium/base/cilium-mtls.yaml`
  - Cilium 1.19.6 resource with `authentication.enabled:true`.
  - Cilium mutual authentication with `authentication.mutual.spire.enabled:true`.
  - SPIRE server address: `spire-server.cilium-spire.svc:8081`.
  - SPIRE agent socket path: `/run/spire/sockets/agent/agent.sock`.
  - SPIRE server `StatefulSet` with Rook-Ceph RBD backing storage.
  - SPIRE server and agent `ServiceAccount` resources.
  - Per-node SPIRE agent `DaemonSet`.
- `gitops/cilium/base/cilium-mtls-test.yaml`
  - `mtls-server` deployment and service.
  - `mtls-client` deployment that calls `http://mtls-server.hpdc-mtls-test.svc.cluster.local/`.

## Mesh Behavior

After apply, expected state is:

- `cilium-spire` namespace exists.
- `spire-server` is running and exposes `spire-server.cilium-spire.svc:8081`.
- `spire-agent` is running on each Talos node.
- Cilium connects to the SPIRE workload API through `/run/spire/sockets/agent/agent.sock`.
- Workloads receive SPIFFE identities for mTLS.
- Plaintext HTTP between mesh-enabled services is rejected.

## Test Flow

Run the following after the mesh is healthy:

```bash
kubectl -n hpdc-mtls-test rollout status deployment/mtls-server
kubectl -n hpdc-mtls-test rollout status deployment/mtls-client
kubectl -n hpdc-mtls-test exec deploy/mtls-client -- curl -fsS http://mtls-server.hpdc-mtls-test.svc.cluster.local/
```

Expected success:

- The `mtls-client` request to `mtls-server` succeeds with valid SPIFFE identity.

Expected failure:

- A request without a valid SPIFFE identity must fail when Cilium mTLS policy enforces authenticated traffic.

## Offline Constraints

- Offline mode must not require internet access.
- Do not SSH into Talos nodes.
- Do not use plaintext HTTP as the service-to-service path.
- Do not skip SPIRE readiness checks during real apply.

## Constraints

- Offline mode must not require internet access.
- Do not SSH into Talos nodes.
- Do not use hostPath, emptyDir, or local ephemeral volumes for SPIRE server persistent CA/data storage.
- Do not install production mesh policy in this story; Story 3.9 covers enforcement policy refinement.
