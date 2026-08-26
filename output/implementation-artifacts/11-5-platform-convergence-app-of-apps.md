---
story_key: 11-5-platform-convergence-app-of-apps
epic: 11
status: in-progress
baseline_commit: 6ab6a889ad8e508512c06a2d6bd99de66a606cc5
completion_commit: TBD
blocked_story: 11-4-live-cluster-verification
blocked_by: "cluster-bootstrap (step 02) fails: nodes never reach Ready; see Dev Agent Record"
---

# Story 11.5: Platform Convergence via App-of-Apps

## Story

As a Platform Engineer,
I want all App-of-Apps children converged to Synced & Healthy on the offline docker-provisioned cluster,
So that live-cluster verification (story 11-4) runs against a fully converged platform.

## Acceptance Criteria

**Given** the offline docker-provisioned Talos cluster (`hpdc-talos`, 4/4 nodes Ready) with the local registry mirror
**When** `gitops/app-of-apps/root-application.yaml` is applied and ArgoCD reconciles
**Then** all 19 child Applications reach Synced + Healthy
**And** `kubectl get pods -A` shows zero non-Running pods (excluding Completed jobs)

**Given** manifests reference images missing from the local mirror
**When** the gaps are resolved (authored, built, and mirrored)
**Then** every image ref in rendered manifests resolves via `hpa-local-registry` (10.6.0.1:5000) with no internet fallback

**Given** convergence is complete
**When** `python3 scripts/startup.dev.py --status` is run
**Then** it reports cluster Ready plus the full component table
**And** the output is captured as verification evidence for story 11-4

## Tasks / Subtasks

- [ ] Task 1: Resolve missing images (AC: #2)
  - [ ] Decide regional-hub-spa: author `frontend/` build context and build `ghcr.io/hpdc/regional-hub-spa:dev`, OR drop/disable the regional-hub app until B-004 — record decision + rationale in Dev Agent Record
  - [ ] Author Casbin envoy ext_authz server image (`docker.io/casbin/ext-authz:v0.0.1` upstream denied): Dockerfile under `backend/` or vendor alternative; push to `localhost:5000/<path>` matching manifest ref exactly
  - [ ] Mirror via `skopeo copy --all` (preserves multi-arch digests); re-check `kubectl get pods -A | grep -v Running` after each sync — ArgoCD auto-heals once tags exist
- [ ] Task 2: Converge OutOfSync stragglers (AC: #1)
  - [ ] Verify envoy-gateway app finished syncing: GatewayClass/Gateway programmed
  - [ ] Confirm tool-ui/observability/security routes resolve once EG is up; then casdoor, infisical, kafka, alerts, platform, entity-store converge
  - [ ] For overlay edits: regenerate `gitops/<comp>/rendered/dev.yaml` via `scripts/gitops/render_overlays.py` → commit → refresh git mirror (rerun step 09) → hard-refresh apps
- [ ] Task 3: Evidence capture (AC: #3)
  - [ ] Run `python3 scripts/startup.dev.py --status`; capture Ready + component table output into Dev Agent Record
  - [ ] Update NEXT.md sync-status section to reflect converged state
- [ ] Task 4: Update sprint-status.yaml (AC: #1)
  - [ ] Mark 11-5 done; confirm 11-4 unblocked

## Dev Notes

### Paradigm (2026-08-24 shift)

- Deployment is **App-of-Apps via ArgoCD from the local git mirror** — NOT bespoke installer steps. Steps remain as waiters/validators only.
- **Rendered-manifests pattern**: ArgoCD v3.5 hardwires kustomize `LoadRestrictionsRootOnly`; cross-cutting overlays cannot build in-cluster. Render host-side into committed `gitops/<comp>/rendered/dev.yaml`.
- CRD bundles at wave 0: `gitops/crds/gateway/crds.yaml` (21 EG CRDs), `gitops/crds/hpdc/hpdc-crds.yaml` (25 placeholder-schema hpdc.io/v1 CRDs). Placeholder schemas are acceptable for this story — tightening them is story 11-6.

### Offline Posture (hard-won, do not regress)

- ALL node pulls flow through `hpa-local-registry` (10.6.0.1:5000) with `skipFallback`; missing images hard-fail rather than leak to internet.
- Cache-fill happens host-side via `skopeo copy --all` — `docker push` mangles multi-arch digests and breaks chart digest pins.
- Registry storage lives on disk (`~/.local/share/hpdc-registry/data`), never /tmp.
- Git smart-http server does NOT survive reboot → rerun step 09 after reboot (idempotent).

### Sync Status at Story Creation (2026-08-24 evening)

Synced: crds-gateway, crds-hpdc, platform-root, agent-engine, backstage*, casbin*, openapi*, regional-hub*, regional-sovereignty, victoria-metrics* (*Progressing/Degraded = image pulls).
OutOfSync/pending: envoy-gateway, casdoor, infisical, kafka, alerts, tool-ui, platform, security, entity-store, observability.
Pods: 44/57 Running.

### References

- `NEXT.md` §A (source of this story's scope)
- `gitops/app-of-apps/root-application.yaml` + `gitops/apps/*.yaml`
- `scripts/gitops/render_overlays.py`
- `output/implementation-artifacts/11-4-live-cluster-verification.md` (downstream consumer)

## Dev Agent Record

### Agent Model Used

Claude (hy3-free) — dev-story execution.

### Debug Log References

- `scripts/startup.dev.py --offline --apply --step 02-bootstrap-talos-dev.py` run twice (2026-08-24): both FAILED at 703.8s on `waiting for all k8s nodes to report ready: some nodes are not ready: [all 4]`. Control plane static pods + components reach Ready; worker/control-plane nodes never reach `Ready`.
- Node VMs (`hpdc-talos-*-*`) are created and stay `Up` (docker), but no kube/talos config is generated because the step exits non-zero before writing `output/talos/talosconfig`. Stale `output/talos/talosconfig` is from Aug 23 (endpoints `127.0.0.1:41039`) and does not match the new cluster CA → unusable.
- Environment path anomaly: repo resolved at `/home/cores/Documents/Study/HPA/with-bmad` earlier in session, then remapped to `/home/cores/Documents/Projects/Study/HPA/with-bmad` (the `Study` symlink disappeared). All story edits verified intact at the new path.

### Completion Notes List

- **Task 1 (regional-hub-spa decision) — DONE (decision only):** User chose **Drop until B-004**. Removed the App-of-Apps child pointer `gitops/apps/regional-hub.yaml` (ArgoCD sources `gitops/apps` dir; removing the pointer unmanages the app). `regional-sovereignty` app retained (separate, single-region-safe). Decision recorded. The SPA images/build context was never authored (none existed in repo).
- **Blocked:** Cluster bring-up (precondition for all convergence tasks) fails reproducibly at step 02 node-readiness gate. Cannot proceed to ext_authz image authoring, OutOfSync convergence, or `--status` evidence without a live cluster.
- **Not started:** Task 1 casbin ext_authz authoring, Task 2 convergence, Task 3 evidence, Task 4 tracker update.

### File List

- `gitops/apps/regional-hub.yaml` — REMOVED (git rm, staged) per drop-until-B-004 decision
- `output/implementation-artifacts/sprint-status.yaml` — 11-5 status `ready-for-dev` → `in-progress`
- `output/implementation-artifacts/11-5-platform-convergence-app-of-apps.md` — status + blocked_by + Dev Agent Record updated

### Change Log

- 2026-08-24: Started 11-5. Recorded regional-hub drop decision and removed child pointer. Hit reproducible cluster-bootstrap failure (step 02); story left in-progress/blocked.
