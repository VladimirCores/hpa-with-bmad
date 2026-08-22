# Provision the Offline Talos Dev Cluster

## Purpose

This document describes the Talos dev bootstrap path for HPDC. It provisions a local Talos Linux cluster using Docker containers via `talosctl cluster create docker` and prepares the cluster for storage backend installation.

## Required tooling

- Python 3
- `talosctl`
- Docker

## Cluster Configuration

The dev cluster uses Docker containers for fast provisioning and teardown:

- **Cluster name**: `hpdc-talos`
- **Subnet**: `10.6.0.0/24`
- **Control planes**: 1 (default)
- **Workers**: 3 (default, configurable with `--workers`)
- **CPUs per worker**: 2 (default, configurable with `--cpus-workers`)
- **RAM per worker**: 3072MB (default, configurable with `--memory-workers`)

## Bootstrap command

### Dry-run mode

```bash
python3 scripts/startup.dev.py --offline --dry-run --step 02-bootstrap-talos-dev.py
```

### Apply mode (creates the cluster)

```bash
python3 scripts/startup.dev.py --offline --apply --step 02-bootstrap-talos-dev.py
```

### With custom worker count

```bash
python3 scripts/startup.dev.py --offline --apply --step 02-bootstrap-talos-dev.py
# Or directly:
python3 scripts/gitops/bootstrap_talos_dev.py --workers 5 --cpus-workers 4
```

## Storage Backend Options

The cluster supports two storage backends via the `--storage` flag:

### local-path (default)

Lightweight local-path-provisioner for development:

```bash
python3 scripts/startup.dev.py --offline --apply --storage local-path
```

### rook-ceph

Full Ceph storage with RBD and CephFS (requires block devices):

```bash
python3 scripts/startup.dev.py --offline --apply --storage rook-ceph
```

**Note**: Rook-Ceph requires dedicated block devices and is more suitable for bare-metal or VM-based clusters. For Docker-based dev clusters, `local-path` is recommended.

## Cluster Lifecycle

### Idempotent startup

The startup script automatically tears down any existing cluster before provisioning:

```bash
python3 scripts/startup.dev.py --offline --apply
```

This will:
1. Detect and tear down any existing cluster (kind or Talos)
2. Create a new cluster with the specified configuration
3. Install the selected storage backend

### Manual teardown

```bash
python3 scripts/stop.dev.py --apply
```

### Check cluster status

```bash
python3 scripts/stop.dev.py --check
```

## Validation

After provisioning, verify the cluster:

```bash
# Check nodes
kubectl get nodes -o wide

# Check storage classes
kubectl get storageclass

# Check pods
kubectl get pods -A
```

## PodSecurity Configuration

Talos enforces PodSecurity policies. The storage installation scripts automatically set the required PodSecurity labels:

```bash
kubectl label namespace local-path-storage pod-security.kubernetes.io/enforce=privileged --overwrite
kubectl label namespace default pod-security.kubernetes.io/enforce=privileged --overwrite
```

## Expected output

### Dry-run

```text
Talos dev cluster bootstrap dry-run passed.
Cluster name: hpdc-talos
Control planes: 1 (CPU: 2.0, RAM: 2048MB)
Workers: 3 (CPU: 2.0, RAM: 3072MB)
Storage: local-path
Subnet: 10.6.0.0/24
Talos version: v1.13.7
```

### Apply

```text
Tearing down existing dev cluster before provisioning...
Cluster teardown complete; proceeding with provisioning.
Cluster 'hpdc-talos' provisioned successfully.
Storage backend: local-path
Workers: 3 (CPU: 2.0, RAM: 3072MB)
```

## Storage handoff

After cluster provisioning, install the storage backend:

```bash
# For local-path (recommended for Docker dev clusters)
python3 scripts/gitops/install_storage_dev.py --storage local-path

# For rook-ceph (requires block devices)
python3 scripts/gitops/install_storage_dev.py --storage rook-ceph
```

## Troubleshooting

### Cluster already exists

If you see errors about an existing cluster, the startup script will automatically tear it down. To manually destroy:

```bash
talosctl cluster destroy --name hpdc-talos
docker rm -f hpdc-talos-controlplane-1 hpdc-talos-worker-{1,2,3}
docker network rm hpdc-talos
```

### PodSecurity violations

If pods are rejected due to PodSecurity policies, ensure the namespace labels are set:

```bash
kubectl label namespace <namespace> pod-security.kubernetes.io/enforce=privileged --overwrite
```

### Storage provisioning failures

Check the provisioner logs:

```bash
# For local-path
kubectl logs -n local-path-storage deployment/local-path-provisioner

# For rook-ceph
kubectl logs -n rook-ceph deployment/rook-ceph-operator
```
