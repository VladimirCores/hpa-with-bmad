# Offline Harbor Registry for HPDC

This page documents the Story 1.6 offline Harbor registry bootstrap.

## Purpose

Harbor provides a local OCI registry for GitOps images and charts. It is configured for offline use with Trivy/Clair scanning on image push and Cosign/signature verification on image pulls.

## Installation

From the repository root:

```python
python3 startup.dev.py --offline --dry-run --step 06-install-harbor-dev.py
```

To apply the GitOps overlay to the Talos cluster after Cilium and Rook-Ceph are installed:

```python
python3 startup.dev.py --offline --apply --step 06-install-harbor-dev.py
```

Validation mode:

```python
python3 startup.dev.py --offline --check --step 06-install-harbor-dev.py
```

## Required Offline Artifacts

The offline installer requires these local artifacts:

- `output/talos/talosconfig` from Story 1.2.
- `output/rook-ceph/images/rook-ceph-v1.20.3` from Story 1.4.
- `output/harbor/images/harbor-core-v2.11.3` from this story.
- `output/harbor/images/harbor-registry-v2.11.3` from this story.
- `output/harbor/images/harbor-jobservice-v2.11.3` from this story.
- `output/harbor/images/harbor-trivy-adapter-v2.11.3` from this story.
- `output/harbor/images/harbor-chartmuseum-v2.11.3` from this story.
- `output/harbor/images/harbor-redis-v1.23` from this story.
- `output/harbor/images/harbor-postgresql-v15` from this story.

## GitOps Resources

The dev overlay applies:

- `gitops/harbor/base/harbor.yaml`
  - Harbor core, jobservice, registry, Trivy adapter, ChartMuseum, Redis, and PostgreSQL deployments.
  - Harbor service and registry service.
- `gitops/harbor/base/harbor-values.yaml`
  - Harbor external URL.
  - Trivy scanning enabled.
  - Cosign/signature verification settings.
  - Rook-Ceph-backed persistence.
- `gitops/harbor/base/harbor-pvcs.yaml`
  - Rook-Ceph-backed PVCs for Harbor state.

## Persistence

Harbor state is stored in Ceph-backed PVCs using `storageClassName: rook-ceph-rbd`.

Persistent PVCs:

- `harbor-core`
- `harbor-jobservice`
- `harbor-registry`
- `harbor-trivy`
- `harbor-chartmuseum`
- `harbor-redis`
- `harbor-postgresql`

## Image Registry Service

After apply, Harbor is available as:

```text
service/harbor in namespace harbor
```

The registry endpoint is:

```text
service/harbor-registry in namespace harbor
```

## Validation

Run:

```python
python3 startup.dev.py --offline --dry-run --step 06-install-harbor-dev.py
python3 startup.dev.py --offline --check --step 06-install-harbor-dev.py
python3 tests/test_install_harbor_dev.py
python3 -m compileall -q startup.dev.py scripts tests
```

## Constraints

- Offline mode must not require internet access.
- Do not SSH into Talos nodes.
- Do not use hostPath, emptyDir, or local ephemeral storage for Harbor state.
- Do not skip offline image cache validation.
