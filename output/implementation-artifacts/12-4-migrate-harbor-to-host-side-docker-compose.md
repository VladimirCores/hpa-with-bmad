# Story 12.4: Migrate Harbor to Host-Side Docker Compose

Status: pending

## Story

As a Platform Engineer,
I want Harbor running on the host machine (10.6.0.1) via Docker Compose instead of inside the Talos cluster,
So that control plane nodes are freed from Harbor's resource overhead (4-8GB RAM) and Harbor survives cluster rebuilds.

## Acceptance Criteria

1. Given the host machine at 10.6.0.1, when Harbor is deployed via Docker Compose, then Harbor core, registry, jobservice, PostgreSQL, and Redis run as Docker containers on the host.
2. Given Harbor is running on the host, when Talos nodes pull images via containerd mirror at 10.6.0.1:5000, then the pulls succeed against Harbor's registry endpoint.
3. Given Harbor is running on the host, when a user navigates to https://10.6.0.1:8443 (or http://10.6.0.1:8443 for dev), then the Harbor web UI is accessible.
4. Given Harbor is running on the host, when an image is pushed to the registry, then Trivy vulnerability scanning runs on the image.
5. Given Harbor is running on the host, when in-cluster workloads reference Harbor images, then the images are pullable from the host-side Harbor.
6. Given the existing `hpa-local-registry` (registry:2) container, when Harbor replaces it, then the old container is stopped and removed.
7. Given in-cluster Harbor manifests exist (gitops/harbor/), when the migration completes, then those manifests, PVCs, and namespace resources are removed from the GitOps tree.
8. Given the migration completes, when `startup.dev.py` runs, then the pipeline references host-side Harbor instead of in-cluster Harbor.
9. Given the migration completes, when the process runs, then it completes without internet access.
10. Given the migration completes, when any step fails, then the script exits with a non-zero status.

## Tasks / Subtasks

- [ ] Task 1: Create Harbor Docker Compose configuration (AC: 1, 3)
  - [ ] Subtask 1.1: Create `platform/harbor/docker-compose.yml` with Harbor core, registry, jobservice, PostgreSQL, Redis, and nginx reverse proxy.
  - [ ] Subtask 1.2: Create `platform/harbor/harbor.yml` with Harbor configuration (externalURL, storage, Trivy, Cosign, auth).
  - [ ] Subtask 1.3: Create self-signed TLS certificate generation script (`platform/harbor/gen-certs.sh`).
  - [ ] Subtask 1.4: Create `platform/harbor/registry-config.yml` for the registry endpoint.
  - [ ] Subtask 1.5: Expose registry on port 5000 (replacing registry:2) and web UI on port 8443.

- [ ] Task 2: Create host-side Harbor management script (AC: 1, 9, 10)
  - [ ] Subtask 2.1: Create `scripts/services/harbor.py` with `start`, `stop`, `status`, `restart` commands.
  - [ ] Subtask 2.2: Idempotent: detect existing containers, skip recreation if already running.
  - [ ] Subtask 2.3: Health probe: verify Harbor core `/api/v2.0/health` returns healthy.
  - [ ] Subtask 2.4: Load Harbor images from offline cache into Docker before first start.

- [ ] Task 3: Stop and remove old registry:2 container (AC: 6)
  - [ ] Subtask 3.1: Update `scripts/services/image-registry.py` to stop `hpa-local-registry` and print deprecation notice.
  - [ ] Subtask 3.2: Ensure old registry data at `resources/registry/data` is migrated or backed up.

- [ ] Task 4: Remove in-cluster Harbor manifests (AC: 7)
  - [ ] Subtask 4.1: Remove `gitops/harbor/base/harbor.yaml`, `harbor-values.yaml`, `harbor-pvcs.yaml`.
  - [ ] Subtask 4.2: Remove `gitops/harbor/overlays/dev/`, `overlays/preload/`, `overlays/refresh/`.
  - [ ] Subtask 4.3: Remove `gitops/harbor/rendered/dev.yaml`.
  - [ ] Subtask 4.4: Remove `gitops/harbor/base/preload-images.yaml`, `preload-images-job.yaml`, `image-cache-refresh.yaml`.

- [ ] Task 5: Update pipeline scripts (AC: 8, 9, 10)
  - [ ] Subtask 5.1: Rewrite `scripts/gitops/install_harbor_dev.py` to call host-side Harbor script.
  - [ ] Subtask 5.2: Update `scripts/steps/06-install-harbor-dev.py` to call host-side Harbor script.
  - [ ] Subtask 5.3: Remove step 07 (preload-harbor-cache.py) — Harbor now manages its own storage.
  - [ ] Subtask 5.4: Update `scripts/gitops/install_spegel_dev.py` to use Harbor registry endpoint as upstream.

- [ ] Task 6: Update Talos node registry mirrors (AC: 2)
  - [ ] Subtask 6.1: Verify `controlplane.yaml` mirrors (`http://10.6.0.1:5000`) work with Harbor's registry endpoint.
  - [ ] Subtask 6.2: Verify `worker.yaml` mirrors work identically.
  - [ ] Subtask 6.3: If Harbor uses TLS on port 5000, add `caFile` to mirror config or use HTTP.

- [ ] Task 7: Update environment configuration (AC: 8)
  - [ ] Subtask 7.1: Update `.env` — `HPDC_LOCAL_REGISTRY_URL` stays `http://localhost:5000` (unchanged).
  - [ ] Subtask 7.2: Update `.env.components` — `HPDC_HARBOR_ENABLED` becomes informational (always-on host-side).
  - [ ] Subtask 7.3: Add `HPDC_HARBOR_UI_URL=http://10.6.0.1:8443` to `.env`.

- [ ] Task 8: Update documentation (AC: 8)
  - [ ] Subtask 8.1: Rewrite `docs/harbor-dev-registry.md` with host-side Docker Compose instructions.
  - [ ] Subtask 8.2: Update `README.md` Harbor references (remove in-cluster Harbor section).
  - [ ] Subtask 8.3: Update `NEXT.md` Harbor references.

- [ ] Task 9: Add validation tests (AC: 1, 2, 3, 4, 10)
  - [ ] Subtask 9.1: Update `tests/test_install_harbor_dev.py` to validate host-side Harbor config.
  - [ ] Subtask 9.2: Add health check test: Harbor core returns healthy on 10.6.0.1:8443.
  - [ ] Subtask 9.3: Add registry test: `curl http://10.6.0.1:5000/v2/_catalog` returns repo list.

## Dev Notes

### Requirements

- Harbor version: match current (goharbor/harbor-core:v2.15.2 per harbor.yaml).
- Harbor must replace the existing `hpa-local-registry` (registry:2) at port 5000.
- Harbor web UI must be accessible from the cluster network at port 8443.
- Trivy scanning must remain enabled on image push.
- Cosign signature verification must remain enabled for image pulls.
- Storage uses host filesystem (`/opt/harbor/data/`) instead of Rook-Ceph PVCs.
- Self-signed TLS for dev; production requires proper CA.
- All scripts written in Python 3.
- Offline mode must not require internet access.

### Current State

- `hpa-local-registry` (registry:2) runs on host at `10.6.0.1:5000` — simple OCI cache.
- In-cluster Harbor runs in namespace `harbor` with: core, registry, jobservice, trivy-adapter, redis, postgresql.
- In-cluster Harbor uses ClusterIP services, `externalURL: http://harbor.harbor.svc.cluster.local`, Rook-Ceph PVCs.
- Talos nodes pull via containerd mirror at `http://10.6.0.1:5000` with `skipFallback: true`.
- `.env` has `HPDC_LOCAL_REGISTRY_URL=http://localhost:5000`.

### Source Tree Components (new)

- `platform/harbor/docker-compose.yml` — Harbor Docker Compose definition.
- `platform/harbor/harbor.yml` — Harbor runtime configuration.
- `platform/harbor/gen-certs.sh` — Self-signed TLS certificate generation.
- `scripts/services/harbor.py` — Host-side Harbor management (start/stop/status).
- `scripts/services/image-registry.py` — Updated to deprecate old registry:2.

### Source Tree Components (to remove)

- `gitops/harbor/base/harbor.yaml`
- `gitops/harbor/base/harbor-values.yaml`
- `gitops/harbor/base/harbor-pvcs.yaml`
- `gitops/harbor/base/preload-images.yaml`
- `gitops/harbor/base/preload-images-job.yaml`
- `gitops/harbor/base/image-cache-refresh.yaml`
- `gitops/harbor/overlays/dev/kustomization.yaml`
- `gitops/harbor/overlays/preload/kustomization.yaml`
- `gitops/harbor/overlays/refresh/kustomization.yaml`
- `gitops/harbor/rendered/dev.yaml`
- `output/harbor/images/harbor-*` (image cache markers — images now live in Harbor's Docker storage)

### Architecture Implications

- Harbor is no longer a Kubernetes workload — it's a host-level service managed by Docker Compose.
- The in-cluster `harbor` namespace, Services, Deployments, PVCs, and ConfigMaps are all removed.
- Spegel DaemonSet must be reconfigured to use Harbor as its upstream registry instead of the old registry:2.
- Argo CD and Kargo image references may need updating if they referenced in-cluster Harbor services.
- The chart server at `10.6.0.1:8080` is separate from Harbor and remains unchanged.

### Anti-patterns to Avoid

- Do not run Harbor inside the cluster after migration.
- Do not leave the old `hpa-local-registry` container running alongside Harbor.
- Do not use internet image sources in offline mode.
- Do not store Harbor state on ephemeral storage.
- Do not hardcode IPs or ports — use `.env` variables.

## Dev Agent Record

### Agent Model Used

_(pending)_

### Debug Log References

_(pending)_

### Completion Notes List

_(pending)_

### File List

_(pending)_

## Record Depth

_(pending — baseline delivery commit to be assigned)_
