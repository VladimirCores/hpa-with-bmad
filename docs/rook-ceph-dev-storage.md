# Dev Storage for HPDC

This page documents the storage backend options for the HPDC dev cluster.

## Purpose

Storage provides persistent block and file storage for stateful HPDC workloads on the Talos dev cluster. Two storage backends are supported:

- **local-path**: Lightweight local-path-provisioner for Docker-based dev clusters (recommended)
- **rook-ceph**: Full Ceph storage with RBD and CephFS for bare-metal/VM-based clusters

## Installation

### local-path (default)

From the repository root:

```bash
python3 scripts/startup.dev.py --offline --apply --storage local-path
```

Or install directly:

```bash
python3 scripts/gitops/install_storage_dev.py --storage local-path
```

### rook-ceph

From the repository root:

```bash
python3 scripts/startup.dev.py --offline --apply --storage rook-ceph
```

Or install directly:

```bash
python3 scripts/gitops/install_storage_dev.py --storage rook-ceph
```

**Note**: Rook-Ceph requires dedicated block devices and is more suitable for bare-metal or VM-based clusters. For Docker-based dev clusters, `local-path` is recommended.

## Validation mode

```bash
python3 scripts/gitops/install_storage_dev.py --storage local-path --check
python3 scripts/gitops/install_storage_dev.py --storage rook-ceph --check
```

## Required artifacts

### local-path

- `kubectl` access to the cluster
- No additional offline artifacts required

### rook-ceph

- `kubectl` access to the cluster
- Internet access to download Rook-Ceph manifests (or pre-cached manifests)
- Block devices available for OSDs (not available in Docker-based clusters)

## PodSecurity Configuration

Talos enforces PodSecurity policies. The storage installation scripts automatically set the required PodSecurity labels:

```bash
kubectl label namespace local-path-storage pod-security.kubernetes.io/enforce=privileged --overwrite
kubectl label namespace default pod-security.kubernetes.io/enforce=privileged --overwrite
```

## StorageClasses

### local-path

```yaml
storageClassName: local-path
```

- Provisioner: `rancher.io/local-path`
- Reclaim policy: Delete
- Volume binding mode: WaitForFirstConsumer

### rook-ceph

```yaml
storageClassName: rook-ceph-rbd
```

```yaml
storageClassName: rook-ceph-cephfs
```

- Reclaim policy: Delete
- Volume binding mode: Immediate
- Volume expansion enabled

## Testing storage

After installation, test with a PVC and pod:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: local-path  # or rook-ceph-rbd
---
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  containers:
  - name: test
    image: busybox
    command: ["sh", "-c", "echo 'Hello' > /data/test.txt && sleep 30"]
    volumeMounts:
    - name: test-volume
      mountPath: /data
  volumes:
  - name: test-volume
    persistentVolumeClaim:
      claimName: test-pvc
```

Apply and verify:

```bash
kubectl apply -f test.yaml
kubectl get pvc test-pvc
kubectl get pod test-pod
kubectl exec test-pod -- cat /data/test.txt
```

## Cleanup

To remove the storage installation:

```bash
# Delete test resources
kubectl delete pod test-pod --force
kubectl delete pvc test-pvc

# For local-path: delete the namespace
kubectl delete namespace local-path-storage --force

# For rook-ceph: delete the namespace (this will delete all data)
kubectl delete namespace rook-ceph --force
```

## Constraints

- local-path is recommended for Docker-based dev clusters
- rook-ceph requires dedicated block devices (not available in Docker)
- Do not use hostPath, emptyDir, or local ephemeral volumes for production data
- PodSecurity labels must be set for Talos clusters
