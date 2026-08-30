---
story_key: 11-6-tighten-hpdc-crd-schemas
epic: 11
status: in-progress
baseline_commit: 5ddd040
completion_commit: TBD
---

# Story 11.6: Tighten hpdc.io CRD Schemas

## Story

As a Platform Engineer,
I want the 25 placeholder `hpdc.io/v1` CRDs replaced with validated openAPIV3Schema definitions,
So that controllers, admission validation, and tooling can safely rely on the custom resource contracts.

## Acceptance Criteria

**Given** `gitops/crds/hpdc/hpdc-crds.yaml` currently declares 25 kinds (agentcommunications, alertaudittrails, alerthandleractionses, alertresponseengines, alertsignalstreams, alertstatemachines, alertworkflows, clickhousetables, clustermeshs, entitychangededupes, entitychangefeeds, entitycruds, entitymutationaudits, entitystores, hasuragraphqls, keydbcaches, llmdecisionsupports, mcptoolregistrys, observabilitypipelines, pulsarfunctions, regionalapihubs, regionaldatasovereigntys, spinwasmfunctions, telemetrybackpressurepolicys, tooluiroutes) with preserve-unknown-fields placeholder schemas
**When** each kind's schema is authored against its intended design
**Then** every kind has a real openAPIV3Schema (required fields, types, constraints) — no preserve-unknown-fields placeholders remain except where intentionally justified with a YAML comment

**Given** the tightened schemas are committed
**When** validation runs against the live cluster
**Then** all existing manifest usages validate cleanly via `kubectl apply --dry-run=server` (kubeconform is NOT installed; the live cluster is the gate)
**And** the crds-hpdc Application (and every consuming app) syncs without regression across the App-of-Apps tree

## Tasks / Subtasks

- [ ] Task 1: Inventory kinds, gaps, and intended designs (AC: #1)
  - [ ] Map each kind to its source manifests and consuming components (inventory below; ground truth is the ~40 live CR instances across 18 base files — NOT SOLUTION-DESIGN.md, which has zero hpdc.io schema content)
  - [ ] **GAP — `AlertmanagerConfig` (gitops/monitoring/base/alertmanager.yaml:9): the bundle defines 25 CRDs but 26 distinct kinds are instantiated; this kind has NO CRD.** Decide per architecture review: author the 26th CRD matching the observed spec (`routing.configured`, `stale_metric_warning_minutes`, `channels[]` with name/type/notify/url) OR correct the manifest to a kind that exists. Record the decision; the CR cannot be created at all until one of these lands.
  - [ ] Flag any remaining kind whose intended design is unclear → route to architecture review before authoring
- [ ] Task 2: Author schemas per kind (AC: #1)
  - [ ] Required fields, property types, enums/constraints per the ACTUAL spec fields used in base manifests — e.g. `EntityStore.spec.stores.{couchdb,arcadedb,yugabytedb}` + `stateful_storage.{ceph_backed,storage_class}`; `AlertResponseEngine.spec.{enabled_actions.*,rate_limits,max_actions_per_minute,max_actions_per_alert,health_check}`; `MCPToolRegistry.spec.{tools,validation,logging,agents}`; `ObservabilityPipeline.spec.metrics_cluster.victoriametrics.components[]`
  - [ ] Document any intentionally permissive schema with a `# justification` YAML comment
  - [ ] All CRDs remain `scope: Namespaced` (CRs live in per-component namespaces); do not add cluster-scoped fields
- [ ] Task 3: Validate against live cluster (AC: #2)
  - [ ] `kubectl apply --dry-run=server -f <each base file instantiating hpdc.io CRs>` — fix schema or manifest mismatches. Applies to all 18 consuming files, incl. `gitops/platform/base/platform-scaffold.yaml` (21 CRs)
  - [ ] Regenerate rendered artifacts via `scripts/gitops/render_overlays.py`; commit; refresh git mirror (rerun step 09); hard-refresh + sync `crds-hpdc` and all consuming apps
- [ ] Task 4: Regression check (AC: #2)
  - [ ] Full `kubectl get pods -A` + ArgoCD app health unchanged post-sync for: platform, entity-store, alerts, agent-engine, monitoring, observability, regional-hub, regional-sovereignty, victoria-metrics, clustermesh
  - [ ] Confirm `platform` remains converged (accepted PulsarTopic gap must NOT be re-blocked by schema changes)
  - [ ] Update sprint-status.yaml: 11-6 done

## Dev Notes

- Origin: NEXT.md §A.3 follow-up-story candidate (2026-08-24 session) — schemas were generated from kinds used across manifests as minimal placeholders purely to let App-of-Apps children sync.
- Sequencing: run AFTER 11-5 (convergence) and AFTER 11-4 (live verification) — nothing in verification depends on strict schemas; tightening earlier would churn a moving tree.
- **Schema source of truth:** the ~40 live CR instances in `gitops/{platform,alerts,agent-engine,entity-store,monitoring,observability,regional-hub,regional-sovereignty,victoria-metrics,clustermesh}/base/*.yaml` — their actual `spec` shapes are the contract to encode. `SOLUTION-DESIGN.md` (output/planning-artifacts/architecture/architecture-HPDC-2026-07-30/) has NO hpdc.io schema content.
- Keep bundle structure: single `gitops/crds/hpdc/hpdc-crds.yaml` consumed by the wave-0 crds-hpdc child Application.
- **Prior-story intelligence (11-5):** `crds-hpdc` is `ALWAYS_INCLUDED` (unconditional) in `scripts/gitops/render_app_of_apps.py` `APP_TOGGLE_MAP`; it is wave 0, `syncPolicy.automated.selfHeal: true`, `syncOptions: CreateNamespace=true, ServerSideApply=true`, destination namespace `hpdc-system`. The `platform` app's PulsarTopic gap is accepted/documented — schema tightening must not re-block its convergence.
- **Effort signal:** 25 CRDs + 1 gap (AlertmanagerConfig) with ~1–6 fields each, all sourced from base-manifest spec fields — small per-kind schemas, bulk can be done in one pass.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List