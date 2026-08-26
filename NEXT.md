# Next Steps — HPDC Project

**Last session:** 2026-08-25 (QEMU migration COMPLETE — Q2 in review)
**Cluster:** `hpdc-talos` (**qemu provisioner**) — **4/4 nodes Ready**, k8s v1.35.2, Talos v1.13.7, Cilium 1.20.1 KPR (no kube-proxy), **Rook-Ceph Ready/HEALTH_OK on /dev/vdb**, coredns healthy — fully offline via `localhost:5000` mirror
**Sizing:** `.env` (committed template `.env.example`) → CP 6144MB / workers 4096MB
**Trust note:** offline registry binds 0.0.0.0:5000 unauthenticated by design (nodes pull via bridge IP) — any LAN peer can poison the cache; acceptable on trusted dev LAN
**Next:** code-review Q2 (then mark done) → resume 11-5 convergence → 11-4 verification
**All Talos runtime assets under `resources/` (gitignored)**; runbook: `python3 scripts/startup.dev.py --offline --apply` then user-run step 03 + step 05 (see q2 story Dev Notes for the 8 gotchas)

---

## Current State (2026-08-24 evening)

### Offline infrastructure (NEW — all verified)
- **Local image cache**: `hpa-local-registry` container → durable storage at `~/.local/share/hpdc-registry/data` (migrated off /tmp tmpfs after ENOSPC). ~46 repos incl. k8s control-plane v1.35.2, cilium v1.20.1, harbor v2.15.2 (+valkey), argo stack, victoria stack, backstage, casdoor, cert-manager v1.21.1, dex, local-path, busybox, curl.
- **Node mirrors**: every Talos node's containerd points at `http://10.6.0.1:5000` ONLY (`/etc/cri/conf.d/hosts/<upstream>/hosts.toml`, pull+resolve). Missing images hard-fail instead of leaking to internet — empirically proven (etcd:v3.6.8 incident).
- **Git mirror (offline ArgoCD source)**: bare clone of this repo served over **smart HTTP** at `http://10.6.0.1:9418/with-bmad.git` by `scripts/services/git-smart-http.py` (stdlib CGI bridge over `/usr/libexec/git-core/git-http-backend`; plain `git daemon` unavailable, dumb HTTP rejected by go-git). Started idempotently by step 09; refresh = rerun step 09 (fetch refspec + update-server-info).
- **Speedups in place**: parallel per-node `talosctl image pull` fan-out (4 imgs × 4 nodes ≈ 11s), helm charts cached/vendored, kubeconfig self-recovery in `sync_kubeconfigs` (no more empty-config bug).

### App-of-Apps deployment (NEW — replaces per-component imperative installs)
- `gitops/app-of-apps/root-application.yaml` + 19 children in `gitops/apps/*.yaml` (wave-ordered; crds-gateway/crds-hpdc at wave 0).
- **Rendered-manifests pattern**: ArgoCD v3.5 hardwires kustomize `LoadRestrictionsRootOnly`; cross-cutting overlays can't build. `scripts/gitops/render_overlays.py` renders each `overlays/dev` host-side (kustomize v5.4.3 at `~/.local/bin/kustomize`, one-time tool fetch) into committed `gitops/<comp>/rendered/dev.yaml`; children consume these as directory sources.
- **CRD bundles authored**: `gitops/crds/gateway/crds.yaml` (21 CRDs extracted from EG v1.9.0 install.yaml) and `gitops/crds/hpdc/hpdc-crds.yaml` (25 minimal `hpdc.io/v1` CRDs generated from kinds used across manifests — schemas are preserve-unknown-fields placeholders, NOT validated designs).
- **Sync status at session end**: Synced=crds-gateway, crds-hpdc, platform-root, agent-engine, backstage*, casbin*, openapi*, regional-hub*, regional-sovereignty, victoria-metrics* (*Progressing/Degraded = image pulls). OutOfSync/pending: envoy-gateway, casdoor, infisical, kafka, alerts, tool-ui, platform, security, entity-store, observability.
- Pods: **44/57 Running**. Non-running are concentrated on missing images (below).

### Storage & core
- local-path provisioner installed & default (docs-recommended for docker clusters; rook-ceph deferred — needs block devices). Harbor healthy (8/8) incl. valkey-photon fix. ArgoCD healthy (7 pods). Kargo installed w/ its own cert-manager chart.

---

## What's Left to Complete the Work

### QEMU Migration (NEW — blocks 11-4 completion, est. 1-2 hours)
**Problem:** Docker provisioner can't provide real block devices for Ceph OSD. **SOLVED:** QEMU cluster live (see header).
**Done:** Q1 zone (source-subnet binding) ✓ · Q2 code + live bootstrap + Cilium KPR ✓
**Remaining in Q2:** Task 5 — Rook-Ceph OSD on virtio-blk (`/dev/vdb` on workers; registry has rook images? verify `rook-ceph` repo in catalog) · Task 6 — stop/start idempotent cycle proof.
**Then:** 11-5 convergence → 11-4 verification.
**Runbook:** `python3 scripts/startup.dev.py --offline --apply` (01.5 firewalld → 02 qemu → …). Teardown keeps zone+registry+ISO; `stop.dev.py --cleanup` also wipes VM disks.

1. **Q1: firewalld zone config** (`q1-firewalld-zone-for-qemu-provisioner`, ready-for-dev)
   - Create `scripts/steps/01.5-configure-firewalld-talos.py`
   - Add `talos` zone with ACCEPT target, interfaces `talos+` and `veth+`
   - Add zone teardown to `stop.dev.py`
2. **Q2: Docker→QEMU migration** (`q2-migrate-dev-cluster-docker-to-qemu`, ready-for-dev, blocked_by: Q1)
   - Switch `bootstrap_talos_dev.py` from Docker to QEMU provider
   - Update `stop.dev.py` for QEMU lifecycle
   - Add `--disks "virtio:10GiB"` for Ceph OSD
   - Preserve persistent disk images across teardown/startup cycles
   - Verify Cilium on QEMU networking, Rook-Ceph on real block devices

### C0. Immediate housekeeping — ✅ DONE (commit `6ab6a88`)
1. ~~Commit uncommitted mirror work~~ — smart-http server + mirror refactor + test adaptations committed; `.kube/` gitignored.
2. Restart-safe: registry container has `--restart unless-stopped` ✓; git-smart-http does NOT survive reboot → rerun step 09 after reboot (idempotent).

### A. Finish platform convergence (est. half-day) — now tracked as **story 11-5** (`output/implementation-artifacts/11-5-platform-convergence-app-of-apps.md`, ready-for-dev; do this BEFORE resuming 11-4)
1. **Missing images** (sync via skopeo into `localhost:5000/<path>` matching manifest refs):
   - `ghcr.io/hpdc/regional-hub-spa:dev` — **custom project image, NO build context in repo** (no frontend/ dir). Decision needed: author it or drop regional-hub app until B-004 anyway.
   - `docker.io/casbin/ext-authz:v0.0.1` — upstream denied (private/nonexistent); casbin-ext-authz also denied. Needs a built image (Casbin envoy ext_authz server) — author Dockerfile under backend/ or vendor alternative.
   - Re-check `kubectl get pods -A | grep -v Running` after each sync; ArgoCD auto-heals pulls once tags exist.
2. **OutOfSync stragglers**: mostly waiting on EG routes (envoy-gateway app itself was mid-sync when paused — verify GatewayClass/Gateway came up, then tool-ui/observability/security routes resolve).
3. **hpdc.io CRDs are placeholder schemas** — fine for sync, but tighten openAPIV3Schema per kind before any controller/validation relies on them (promoted to **story 11-6**, runs after 11-4).
4. After convergence: `python3 scripts/startup.dev.py --status` should show cluster Ready + full component table; capture as evidence.

### B. Story 11-4 remaining tasks (the original point) — resume AFTER 11-5 convergence; story file refreshed 2026-08-24
- [ ] Task 1: env vars — set `HPDC_EDGE_URL` to Envoy Gateway address (Cilium LB on docker net; check `kubectl get gateway`/svc) and `HPDC_EVENTS_API_KEY` from api-key-auth secret (step 18 resources / `security` overlay).
- [ ] Task 2: run P0 ATDD suite live: `HPDC_EDGE_URL=… HPDC_EVENTS_API_KEY=… pytest tests/atdd/ -v --tb=long`; the 7 RED-phase skips must pass or fail-with-diagnostics; record in atdd-progress.md.
- [ ] Task 3: REG closure — REG-01 (Infisical), REG-02 (JWKS via Casdoor route), REG-04..06 (Victoria SLOs), REG-07..10 (entity-store SLOs) become executable once §A converges. REG-03 stays blocked by B-004 (single cluster) — document, don't fake.
- [ ] Task 4: mark resolved entries in `deferred-work.md`.
- [ ] Task 5/6: sprint-status.yaml — 11-4 → review/done, Epic 11 done, linked action items done.

### D. Carried from previous NEXT.md (unchanged)
- Record reconciliation leftovers if any resurface during Task 5 (epics.md vs tracker parity).
- B-004 multi-region topology (2nd cluster + ClusterMesh) still open — gates REG-03.

---

## Key Decisions to Remember (new this session)

- **Offline posture**: ALL node pulls flow through `hpa-local-registry` (10.6.0.1:5000) with skipFallback; cache-fill happens host-side via `skopeo copy --all` (preserves multi-arch digests — `docker push` mangles them, breaking chart digest pins).
- **Registry storage lives on disk** (`~/.local/share/hpdc-registry/data`), never /tmp (tmpfs ENOSPC corrupted repos once; recovery = delete affected repo dirs + re-push).
- **Deployment paradigm**: App-of-Apps via ArgoCD from local git mirror — NOT bespoke installer scripts. Steps remain as waiters/validators; rendered/ dirs are the sync artifacts (regenerate via render_overlays.py after overlay edits, then commit + refresh mirror + hard-refresh apps).
- **Storage**: local-path default for the docker dev cluster; rook-ceph path kept but gated behind QEMU/block-device flows.
- **Talos bootstrap** now always applies `platform/talos/talos-offline-mirror-patch.yaml` (mirrors + skipFallback) alongside the CNI patch.
- **Kubeconfig**: single canonical context admin@hpdc-talos written to repo `.kube/config` + `~/.kube/config`; sync_kubeconfigs regenerates via `talosctl kubeconfig` when create times out pre-merge.
- Prior decisions (paradigm, compute, messaging, auth, GitOps, air-gap, observability, secrets, operations, SPA, source tree) — unchanged, see git history of this file.

---

## Artifact Paths (updated)

```
platform/
├── talos/                     # cni patch, offline-mirror patch, registry patches, machine config
├── charts/                    # vendored: harbor-1.19.2, kargo-1.11.1, cert-manager-v1.21.1
├── manifests/                 # argocd-install-v3.5.1.yaml
└── storage/local-path-storage.yaml

gitops/
├── apps/                      # 19 child Applications (wave-ordered)
├── app-of-apps/root-application.yaml
├── crds/{gateway,hpdc}/       # CRD bundles
└── <component>/rendered/dev.yaml   # sync artifacts (generated)

scripts/services/
├── git-smart-http.py          # offline smart-HTTP git server (port 9418)
└── image-preflight.py         # moved here from scripts/

~/.local/share/hpdc-git-mirror/with-bmad.git   # bare mirror served to ArgoCD
~/.local/share/hpdc-registry/data/             # docker registry storage
output/test-artifacts/live-cluster-verification-register.md    # REG-01..10 (update next)
output/implementation-artifacts/11-4-live-cluster-verification.md
output/implementation-artifacts/11-5-platform-convergence-app-of-apps.md   # NEW — do first
output/implementation-artifacts/11-6-tighten-hpdc-crd-schemas.md           # NEW — after 11-4
output/implementation-artifacts/q1-firewalld-zone-for-qemu-provisioner.md  # NEW — QEMU migration prerequisite
output/implementation-artifacts/q2-migrate-dev-cluster-docker-to-qemu.md   # NEW — QEMU migration main story
```

**Runbook (post-reboot, post-QEMU migration)**: start docker → registry auto-starts → `python3 scripts/startup.dev.py --offline --apply` (runs all steps including firewalld zone + QEMU bootstrap) → watch `--status`. Persistent QEMU disk images survive teardown; `stop.dev.py --apply` destroys VMs but preserves images; re-run startup restores from existing disks.
