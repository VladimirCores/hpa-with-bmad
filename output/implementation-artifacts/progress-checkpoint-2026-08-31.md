# Dev-cluster resume checkpoint — 2026-08-31 (UTC+3)

> Re-runnable at each gate. `KUBECONFIG=/tmp/hpacore.kc` is `sudo -n cat /root/.kube/config`
> (root-owned, mode 600 — regenerate after any reboot). Host has EXTRA RAM/CPU now.
> Driving components manually step-by-step (NOT `startup.dev.py`, which would tear the
> working cluster down via step 02). Each script: prefix `HPDC_KUBERNETES_VERSION=1.36.2`.

## Version target (resolved)
- `.env.versions`/`.example` pinned at `1.37.0` (user directive). Not buildable: Talos 1.13.7
  bundles k8s 1.36.2 (release-notes). Cluster runs **1.36.2** (Talos-native ceiling) via env
  override so the files stay at the 1.37.0 target. 1.37.0 needs Talos ≥1.15 + new ISO/CNI/bundle.

## Cluster state (LIVE)
- **4/4 QEMU nodes `Ready`**, k8s v1.36.2 (1× control-plane 8 GiB/2vCPU, 3× workers 4096 MiB/2vCPU + 40 GiB data disk).
- **Cilium 1.20.1 GREEN**: 4× cilium-agent (1/1), 4× cilium-envoy, 2× cilium-operator; KPR.
- **Hubble GREEN**: `hubble-relay` 1/1 Ready, `hubble-ui` 2/2 Ready; nodes pulled relay/ui/ui-backend
  (digests) from the offline registry. All kube-system pods Running.
- **Controlplane pods**: kube-apiserver / kube-controller-manager / kube-scheduler / coredns Running.
- Local helm chart server: `python3 -m http.server 8080 --bind 0.0.0.0 --directory platform/charts`
  (setsid pid 313831). `platform/charts/` has cilium-1.20.1.tgz + harbor/kargo/cert-manager tgzs + index.yaml.
- Offline registry `10.6.0.1:5000` mirrored for 1.36.2 controlplane + full component image set
  (Cilium/Hubble, Harbor, Spegel, Envoy, Argo, Cert-manager, Casdoor/Casbin, Infisical, Rook/ceph v1.20.6).

## Fixes applied (persist to repo)
- `bootstrap_talos_dev.py` `prune_kubeconfig_prefix`: guard `contexts: null` (TypeError abort in step 02).
- Deleted corrupt stale `/home/cores/.kube/config`.
- Mirrored k8s 1.36.2 controlplane + kube-proxy + kubelet; `cilium/hubble-relay:v1.20.1`,
  `cilium/hubble-ui:v0.13.5` (pre-existing), `cilium/hubble-ui-backend:v0.13.5`.
- Started local helm chart server on `10.6.0.1:8080` (was down → "connection refused").
- `install_cilium_dev.py`: added `hubble.enabled/relay.enabled/ui.enabled=true` (chart default omits relay/ui).

## Done this turn
- [x] Cluster bootstrap (QEMU) green on 1.36.2.
- [x] Cilium installed + rolled out → nodes Ready.
- [x] Hubble installed (relay + ui) → green.
- [x] Rook `--check` validates (scaffold + manifests v1.20.6/deviceFilter:vdb/count:1).

## Next gate (in progress)
- **Rook-Ceph** `--apply` → operator + mon(1) + mgr(1) + 3 OSDs (from 3× worker vdb 40 GiB).
- Then remaining core add-ons (Harbor, Spegel, Envoy GW, ArgoCD, Cert-manager, Casdoor, Casbin, Infisical).
- Base P0 ATDD green.

## Next action (run to resume)
```bash
cd /home/cores/Documents/Projects/Study/HPA/with-bmad
sudo -n cat /root/.kube/config > /tmp/hpacore.kc && chmod 600 /tmp/hpacore.kc
KUBECONFIG=/tmp/hpacore.kc HPDC_KUBERNETES_VERSION=1.36.2 python3 scripts/gitops/install_rook_ceph_dev.py --offline --apply
```

## Blocked / deferred
- k8s 1.37.0: blocked on Talos ≥1.15.
- `03-install-cilium-online.py` arg bug (startup.dev.py passes `--apply`; online step rejects) — latent.
- Optional components (Pulsar/Kargo/Rollouts/Events/Grafana/VM/OTel/Alertmanager/Swagger/mTLS/SPIRE/...): DELAYED one-by-one, NOT skipped.

---
## GATE UPDATE — 2026-08-31 (resumable checkpoint)
### A. Rook-Ceph storage — GREEN (RESOLVED)
- Root cause: rook/ceph:v1.20.6 default uid=2016 (non-root); Talos 1.13.7 grants NO
  CAP_CHOWN to non-root -> mon-a init chown-container-data-dir (chown ceph:167) failed
  "Operation not permitted" -> mon-a Init:Error -> no quorum. Rook 1.20.6 CephCluster CRD
  has NO spec.podSecurityContext (apply rejects: strict decoding unknown field).
- Fix: (1) rook-dirs-bootstrap DaemonSet OnFailure->Always, privileged, chowns /var/lib/rook->167
  (safety net); (2) host MutatingWebhook `rook-sec-hook` (/tmp/webhook.py + /tmp/webhook/*.crt
  + /tmp/deploy_webhook.sh) injects pod securityContext.runAsUser:0 via JSONPatch into
  rook-ceph mon/mgr/osd pods; root uid 0 HAS CAP_CHOWN -> chown succeeds.
  NOTE: host process survives cluster rebuild but NOT host reboot -> resurrect via `bash /tmp/deploy_webhook.sh`.
- State: mon-a(1/1) Running, mgr-a(1/1) Running, osd-0/1/2(1/1) Running, osd-prepare x3 Completed,
  CephCluster phase=Ready/HEALTH_WARN (fsid e246d7f4...), 3 OSDs. Reverted podSecurityContext from
  gitops/rook-ceph/base/rook-ceph.yaml; rendered/dev.yaml re-rendered clean.
- 4/4 nodes Ready (v1.36.2).

### B. Cilium + Hubble — GREEN
hubble-relay 1/1 Ready, hubble-ui 2/2 Ready, cilium x4 + cilium-envoy x4 + operator x2.

### C. ArgoCD — GREEN (pre-existing)
applicationset-controller/dex/notifications/redis/repo-server/server all Running.

### D. Harbor — PENDING (storage SC mismatch)
harbor-nginx+portal Running; database/redis/registry/trivy-jobservice Pending. Harbor install
hardcodes storageClassName=local-path; only rook-ceph-rbd SC existed. Fix: install
local-path-provisioner (rancher/local-path-provisioner, image MIRRORED) -> bind Harbor PVCs.
-> in progress this session.

### E. Remaining core add-ons — INSTALLING
Spegel, Envoy Gateway, Cert-manager, Casband, Casdoor, Infisical.
Optional (Pulsar/Kargo/Argo-Rollouts+Events/Grafana/VM/Otel/Alertmanager/Swagger/API-Key/Spire)
-> DELAYED (not skipped).

### F. Version note (resume-safe)
.env.versions HPDC_KUBERNETES_VERSION=1.37.0 (user) NOT achievable on Talos 1.13.7 (bundles v1.36.2;
1.37 requires Talos>=1.15 + un-cached ISO/CNI). Cluster runs 1.36.2 via env override
(HPDC_KUBERNETES_VERSION=1.36.2; os.environ.setdefault wins, .env.versions untouched at 1.37.0 target).

### G. Resumable artifacts
/tmp/kill_cluster.sh, /tmp/test_toggle.py, /tmp/webhook.py + /tmp/deploy_webhook.sh,
/tmp/hpacore.kc (regen: `sudo -n cat /root/.kube/config > /tmp/hpacore.kc && chmod 600`),
chart server 10.6.0.1:8080 (pid via `ss -ltnp|grep 8080`), local reg 10.6.0.1:5000.

## H. Final Green Roster + Persistence (2026-08-31)
### Green (live cluster)
- **P0 ATDD: 16/16 passed** (4.64s) — survives infisical gitops edits (command/env/probes).
- **Nodes**: 4/4 Ready (v1.36.2): controlplane-1=10.6.0.2, workers 10.6.0.3/4/5.
- **Rook-Ceph**: CephCluster phase=Ready, HEALTH_WARN, fsid e246d7f4-7079-4558-bfc3-bf663c29f80e; mon-a+mgr-a+osd-0/1/2 Running; rbd+cephfs CSI Running. NON-BLOCKING: crashcollector/exporter `Pending` (Talos /var/crash mount path). osd-prepare x3 + bootstrap(rootchown/u167) `Succeeded`.
- **Cilium+Hubble**: 4 cilium + 4 cilium-envoy + 2 operator; hubble-relay 1/1; hubble-ui 2/2.
- **ArgoCD**: 7 pods Running. **Harbor**: 8 pods Running (local-path SC). **Spegel**: 3/3 Running (singleton).
- **Envoy Gateway**: controller 1/1 + Envoy dataplane 2/2; Gateway `hpdc-edge` Accepted+Programmed (172.18.0.2); HTTPRoutes present.
- **cert-manager**: 3/3 Running (chart install, CRDs via `helm template --include-crds`).
- **Casbin**: 1 Running. **Casdoor**: postgres + casdoor Running (transient restarts).
- **Infisical**: app 1/1 Running (1/1 Ready, /health→200); postgres 1/1 + redis 1/1 Running.
- **Webhook**: `rook-sec-hook` https://10.6.0.1:8443/ → 501 (alive; /tmp/webhook.py + /tmp/deploy_webhook.sh).
- **Pods**: 68/80 Running+Ready (12 non-Running = 7 Pending Rook sidecars + 3 Succeeded osd-prepare + 2 Succeeded bootstrap).

### Persisted to gitops (reproducible by future sync)
- gitops/infisical/base/infisical.yaml: `command: ["node","--enable-source-maps","/backend/dist/main.mjs"]`; `args --configPath` REMOVED; env `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD` (was INFISICAL_DATABASE_*); added `REDIS_URL`, `BASE_URL`; `ENCRYPTION_KEY/ROOT_ENCRYPTION_KEY/AUTH_SECRET` via `valueFrom` Secret `infisical-secrets` (runtime-generated, NOT committed); probes `path: /health`; liveness initialDelaySeconds=120/failureThreshold=30, readiness initialDelaySeconds=15.
- gitops/infisical/base/infisical-postgres.yaml (NEW): postgres:15.19-alpine, svc `infisical-postgres:5432`, POSTGRES_PASSWORD=InfisicalAdmin12345 (whitelisted dev value).
- gitops/infisical/base/infisical-redis.yaml (NEW): redis:8.2.8-alpine, args `["redis-server","--appendonly","no"]`, svc `infisical-redis:6379`.
- gitops/infisical/overlays/dev/kustomization.yaml: registered the 2 new base files.
- gitops/infisical/rendered/dev.yaml + gitops/spegel/rendered/dev.yaml: regenerated via `render_overlays.py` (--load-restrictor LoadRestrictionsNone + image substitution); infisical now has command/env/probes correct + 8 docs (incl. postgres/redis deps); spegel v0.7.4 args.
- `component_versions.py` toggle bypass + `/tmp/test_toggle.py` regression: verified.
- High-entropy keys (ENCRYPTION_KEY/AUTH_SECRET/ROOT_ENCRYPTION_KEY) kept in runtime k8s Secret only — ATDD secret scan stays green.

### Resume-safe / resurrection
- KUBECONFIG=/tmp/hpacore.kc (regen: `sudo -n cat /root/.kube/config > /tmp/hpacore.kc && chmod 600`).
- Cluster offline: 10.6.0.1:5000 (image reg) + 10.6.0.1:8080 (chart server, setsid pid 313831).
- Teardown: `/tmp/kill_cluster.sh` (PID-based; never pkill self-referential). Webhook: `bash /tmp/deploy_webhook.sh`.

## I. Carried Forward (post-green, NOT blocking the dev cluster)
- `HPDC_KUBERNETES_VERSION=1.37.0` in `.env.versions` is aspirational — Talos 1.13.7 ceiling is k8s 1.36.2. User to decide: keep 1.37.0 target + env-override 1.36.2, OR bump Talos >=1.15 + un-mirror.
- `component_versions.py` toggle patches: move `/tmp/test_toggle.py` into repo + run bmad-code-review (Blind Hunter / Edge Case / Acceptance). Already verified.
- Rook `crashcollector`/`exporter` Pending (Talos /var/crash path) — investigate only if storage breaks.
- `entity-store`/`pulsar` namespaces: envoy overlay HTTPRoutes reference them — verify still needed after `entity-store` component exists; create if referenced.
