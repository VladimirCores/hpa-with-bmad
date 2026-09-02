---
title: "Remove Harbor and Use Local Registry"
description: "Replace Harbor OCI registry with lightweight local registry:2, remove Harbor from cluster, shift scanning/signing to CI pipeline while maintaining air-gapped delivery"
tags:-devops, registry, harbor, optimization, security
---

## Acceptance Criteria

**Given** the dev cluster has Harbor installed via Story 2.1 with ~2GB RAM consumption
**And** image push/pull and Helm chart operations work via Harbor
**When** I evaluate resource consumption and implement the replacement
**Then**

1. **Analysis Phase:**
   - Document Harbor's current resource consumption (CPU, RAM, storage)
   - Document Harbor's features: Trivy scanning, Cosign signing, Helm charts, UI, multi-tenancy
   - Document Spegel's role in P2P image distribution

2. **Design Phase:**
   - Design registry:2 deployment (no UI, minimal resources ~50MB RAM)
   - Design CI pipeline integration for Trivy scanning
   - Design CI pipeline integration for Cosign signing
   - Ensure Helm chart OCI support continues

3. **Implementation Phase:**
   - Create `gitops/registry/base/registry.yaml` with registry:2 Deployment and Service
   - Configure registry persistence via CephFS (RF=1 dev)
   - Update Spegel configuration to cache from registry:2
   - Create `scripts/trivy-scan-ci.py` for CI-based vulnerability scanning
   - Create `scripts/cosign-sign-ci.py` for CI-based image signing
   - Update Kargo warehouse to reference images by digest
   - Remove Harbor helm release: `helm uninstall harbor -n harbor`
   - Remove Harbor namespace: `kubectl delete namespace harbor`
   - Remove Harbor storage: `helm uninstall harbor-charts-migrator -n harbor` (if exists)

4. **Validation Phase:**
   - Verify `kubectl get pods -n harbor` returns "Error from server (NotFound)" or empty
   - Verify image push to `localhost:5000/test-image` succeeds
   - Verify image pull from local registry succeeds
   - Verify Spegel caches images: `kubectl logs -l app=spegel -n kube-system` shows cache hits
   - Verify Helm chart push: `helm push ./chartoci oci://localhost:5000/charts`
   - Verify Kargo can pull images by digest from registry:2
   - Verify air-gapped operation: no external registry access needed

**And** the script exits with non-zero status on any failure

## Implementation Steps

### Step 1: Create Minimal Registry Manifests

```yaml
# gitops/registry/base/registry.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: registry
  namespace: registry
spec:
  replicas: 1
  selector:
    matchLabels:
      app: registry
  template:
    metadata:
      labels:
        app: registry
    spec:
      containers:
      - name: registry
        image: registry:2
        ports:
        - containerPort: 5000
        volumeMounts:
        - name: registry-storage
          mountPath: /var/lib/registry
        env:
        - name: REGISTRY_HTTP_TLS_CERTIFICATE
          value: /certs/domain.crt
        - name: REGISTRY_HTTP_TLS_KEY
          value: /certs/domain.key
        readinessProbe:
          httpGet:
            path: /v2/
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: registry-storage
        persistentVolumeClaim:
          claimName: registry-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: registry
  namespace: registry
spec:
  type: ClusterIP
  ports:
  - port: 5000
    targetPort: 5000
    name: registry
  selector:
    app: registry
```

### Step 2: Update Spegel Configuration

Spegel will continue to cache images from the local registry and serve to peers.

### Step 3: CI Pipeline Integration

Update `.github/workflows/image-scan-sign.yaml`:

```yaml
# Trivy scan (in CI, not Harbor webhook)
trivy image --exit-code 1 --severity CRITICAL $IMAGE
cosign sign --key $COSIGN_KEY $IMAGE
```

### Step 4: Remove Harbor

```bash
# Remove Helm release
helm uninstall harbor -n harbor
helm uninstall harbor-postgresql -n harbor
helm uninstall harbor-notary -n harbor

# Delete namespace
kubectl delete namespace harbor --wait --timeout=60s

# Clean up any remaining resources
kubectl get pods -A | grep harbor || echo "Clean"
```

## Related

- Story 2.1: Provision Local Harbor OCI Registry with Scanning and Signing
- Story 2.5: Provision Spegel P2P Image Distribution
- AD-10: Air-gapped delivery
- FR-30: Local Harbor OCI registry
- FR-31: Spegel P2P image distribution