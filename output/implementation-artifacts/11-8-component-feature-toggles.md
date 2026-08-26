# Story 11.8: Component Feature Toggles via .env

baseline_commit: e5a2e23c8511e9e54c9a729583188342ee6eacc2

Status: review

## Story

As a Platform Engineer,
I want per-component and per-sub-system feature toggles (`*_ENABLED=true|false`) in environment-specific `.env` files,
so that I can enable only the components I need for a given deployment (dev/prod), test them individually, and avoid overwhelming setup with unnecessary components.

## Acceptance Criteria

**Given** `.env.dev` and `.env.dev.example` exist (committed), and `.env.prod` exists (gitignored or committed per team preference)
**When** the user copies `.env.dev` to `.env` (or `.env.prod` to `.env`)
**Then** every component and sub-system has an `HPDC_<COMPONENT>_ENABLED=true|false` variable
**And** core components are always `true` and cannot be overridden to `false`: `HPDC_CILIUM_ENABLED`, `HPDC_HUBBLE_ENABLED`, `HPDC_ROOK_CEPH_ENABLED` (or `HPDC_LOCAL_PATH_ENABLED`), `HPDC_HARBOR_ENABLED`, `HPDC_SPEGEL_ENABLED`
**And** storage backend is selectable: `HPDC_STORAGE_BACKEND=rook-ceph|local-path` (mutually exclusive; only one storage provisioner runs)

**Given** a component has `HPDC_<COMPONENT>_ENABLED=false`
**When** `startup.dev.py` runs (any mode: `--dry-run`, `--apply`, `--check`)
**Then** the component's step is completely skipped (not installed, not checked, not dry-run-printed)
**And** the component still appears in `startup.dev.py --status` with state `skipped`

**Given** a sub-system has `HPDC_<FEATURE>_ENABLED=false`
**When** its parent component is enabled but the sub-system is disabled
**Then** the sub-system step is skipped while the parent component installs normally
**And** the sub-system appears in `--status` as `skipped`

**Given** `.env` has no `*_ENABLED` variables (old `.env` without toggles)
**When** any consumer resolves toggles
**Then** every component defaults to `enabled=false` (safe default — new components are opt-in, not opt-out)

**Given** a component has `HPDC_<COMPONENT>_ENABLED=false`
**When** `render_overlays.py` or `gitops-render-apps.py` runs (the render step that produces `gitops/apps/`)
**Then** the disabled component's ArgoCD Application manifest is **excluded** from `gitops/apps/`
**And** the root-application.yaml still points to `gitops/apps/` — ArgoCD only syncs the apps present in that directory
**And** a manifest of enabled apps is printed so the operator can verify what will be deployed

**Given** `python3 -m pytest tests/ -q` runs
**When** tests assert toggle behavior
**Then** the suite passes including new toggle tests

## Component Toggle Inventory

### Core Components (always enabled, toggle is informational only)

| Variable | Component | Step | Notes |
|----------|-----------|------|-------|
| `HPDC_CILIUM_ENABLED=true` | Cilium CNI | 03 | Always on |
| `HPDC_HUBBLE_ENABLED=true` | Hubble UI | 03 | Installed with Cilium |
| `HPDC_ROOK_CEPH_ENABLED=true` | Rook-Ceph storage | 05 | Mutually exclusive with local-path |
| `HPDC_LOCAL_PATH_ENABLED=false` | Local-Path Provisioner | 05 | Mutually exclusive with Rook-Ceph |
| `HPDC_HARBOR_ENABLED=true` | Harbor registry | 06 | Always on |
| `HPDC_SPEGEL_ENABLED=true` | Spegel P2P distribution | 10 | Always on |

### Optional Components (toggleable)

| Variable | Component | Step | Dev Default | Prod Default |
|----------|-----------|------|-------------|--------------|
| `HPDC_GIT_MIRROR_ENABLED=true` | Git Mirror | 09 | true | true |
| `HPDC_KARGO_ENABLED=false` | Kargo warehouse | 11 | false | true |
| `HPDC_ARGOCD_ENABLED=false` | ArgoCD GitOps | 12 | false | true |
| `HPDC_ARGO_ROLLOUTS_ENABLED=false` | Argo-Rollouts | 13 | false | true |
| `HPDC_ARGO_EVENTS_ENABLED=false` | Argo-Events | 14 | false | true |
| `HPDC_ENVOY_GATEWAY_ENABLED=true` | Envoy Gateway | 16 | true | true |
| `HPDC_CERT_MANAGER_ENABLED=false` | Cert-Manager | 17 | false | true |
| `HPDC_CASDOOR_ENABLED=true` | Casdoor AuthN | 19 | true | true |
| `HPDC_CASBIN_ENABLED=true` | Casbin AuthZ | 20 | true | true |
| `HPDC_INFISICAL_ENABLED=false` | Infisical Secrets | 23 | false | true |
| `HPDC_BACKSTAGE_ENABLED=false` | Backstage Portal | 24 | false | true |
| `HPDC_GRAFANA_ENABLED=false` | Grafana Dashboards | 25 | false | true |
| `HPDC_VICTORIA_METRICS_ENABLED=false` | Victoria Metrics | 26 | false | true |
| `HPDC_OTEL_ENABLED=false` | OTEL Collector | 27 | false | true |
| `HPDC_ALERTMANAGER_ENABLED=false` | Alertmanager | 28 | false | true |
| `HPDC_SWAGGER_UI_ENABLED=false` | Swagger UI / OpenAPI | 29 | false | true |

### Sub-System Toggles (independent of parent component)

| Variable | Sub-System | Parent | Step | Dev Default | Prod Default |
|----------|-----------|--------|------|-------------|--------------|
| `HPDC_MTLS_ENABLED=false` | Cilium mTLS | Cilium | 04 | false | true |
| `HPDC_SPIRE_ENABLED=false` | SPIRE identity | Cilium | 04 | false | true |
| `HPDC_API_KEY_AUTH_ENABLED=false` | API Key Auth | Envoy Gateway | 18 | false | true |
| `HPDC_CASBIN_RBAC_ENABLED=false` | Casbin RBAC | Casbin | 21 | false | true |
| `HPDC_CASBIN_REBAC_ENABLED=false` | Casbin ReBAC | Casbin | 22 | false | true |
| `HPDC_CASBIN_ABAC_ENABLED=false` | Casbin ABAC | Casbin | 22 | false | true |

## Tasks / Subtasks

- [x] Task 1: Create `.env.dev.example` with all toggles (AC: #1, #4)
  - [x] Create committed `.env.dev.example` with all `HPDC_*_ENABLED` vars and version vars
  - [x] Core components always `true`; optional components use dev defaults
  - [x] `HPDC_STORAGE_BACKEND=rook-ceph` (default)
  - [x] Backward-compatible: no `_ENABLED` vars → all disabled (safe default: opt-in)

- [x] Task 2: Create `.env.dev` and `.env.prod` (AC: #1, #2)
  - [x] `.env.dev` = copy of `.env.dev.example` with dev defaults (optional components disabled)
  - [x] `.env.prod` = copy with all components enabled
  - [x] `.env.dev` committed; `.env.prod` committed

- [x] Task 3: Extend `component_versions.py` with toggle resolution (AC: #1, #4)
  - [x] Add `ENABLED_DEFAULTS: dict[str, bool]` mapping each `HPDC_*_ENABLED` var to its default
  - [x] Add `is_enabled(component: str) -> bool` API: reads `os.environ.get(f"HPDC_{component}_ENABLED")`, falls back to `ENABLED_DEFAULTS`, falls back to `False` (safe default: opt-in)
  - [x] Core components (`CILIUM`, `HUBBLE`, `ROOK_CEPH`/`LOCAL_PATH`, `HARBOR`, `SPEGEL`) are always `True` regardless of env
  - [x] `HPDC_STORAGE_BACKEND` resolution: `rook-ceph` → `ROOK_CEPH_ENABLED=True, LOCAL_PATH_ENABLED=False`; `local-path` → inverse
  - [x] Load toggles from `.env` via existing `load_dotenv()` (same dialect)

- [x] Task 4: Wire `startup.dev.py` to respect toggles (AC: #2, #3)
  - [x] In `discover_steps()` or `selected_steps()`, filter out steps whose component toggle is disabled
  - [x] Disabled steps appear in `--status` table with state `skipped` (not `never-run`)
  - [x] Add `--all` flag to show all steps including skipped (for debugging)
  - [x] Log skipped steps: `[SKIP] step_name: component disabled via HPDC_*_ENABLED=false`

- [x] Task 5: Update installers to check toggles (AC: #2, #3)
  - [x] Each `install_*_dev.py` reads its toggle at entry and exits early (code 0) if disabled
  - [x] Or: startup.dev.py filters before calling — single point of control (preferred)
  - [x] Ensure sub-system steps (04-mtls, 18-api-key-auth, 21/22-casbin-*) check their own toggle

- [x] Task 6: Storage backend mutual exclusion (AC: #1)
  - [x] `HPDC_STORAGE_BACKEND` resolves to exactly one of `rook-ceph` or `local-path`
  - [x] Startup validates: if both `HPDC_ROOK_CEPH_ENABLED=true` and `HPDC_LOCAL_PATH_ENABLED=true`, error with remediation
  - [x] `--storage` CLI flag on `startup.dev.py` maps to `HPDC_STORAGE_BACKEND`

- [x] Task 7: Tests (AC: #5)
  - [x] `test_component_versions.py`: add `test_is_enabled_default_false`, `test_is_enabled_disabled`, `test_core_always_enabled`, `test_storage_backend_mutex`
  - [x] `test_startup_dev.py`: verify skipped steps appear in status, toggle filtering works
  - [x] Existing tests unchanged (no `_ENABLED` vars → non-core components disabled, core always on)

- [x] Task 8: Filter ArgoCD app-of-apps by toggles (AC: #6)
  - [x] Create `scripts/gitops/render_app_of_apps.py` that reads toggles and writes only enabled app YAMLs to `gitops/apps/`
  - [x] Map each `gitops/apps/*.yaml` to its component toggle: `backstage.yaml` → `HPDC_BACKSTAGE_ENABLED`, `victoria-metrics.yaml` → `HPDC_VICTORIA_METRICS_ENABLED`, etc.
  - [x] Disabled components: their app YAML is NOT written to `gitops/apps/` (moved to `gitops/apps.all/` staging dir)
  - [x] Enabled components: their app YAML is written to `gitops/apps/` as before
  - [x] Print summary: `apps rendered: 12 enabled, 6 skipped (disabled via toggle)`
  - [x] `root-application.yaml` unchanged — ArgoCD syncs whatever is in `gitops/apps/`
  - [x] Wire into startup pipeline: run after component installs, before ArgoCD sync
  - [x] `--dry-run` mode: show which apps would be included/excluded without writing

- [x] Task 9: Documentation
  - [x] README: document toggle system, dev vs prod defaults, how to enable/disable components
  - [x] `.env.dev.example` header comments explaining each toggle group
  - [x] Document app-of-apps filtering: how toggles affect ArgoCD deployments

## Dev Notes

### Current state

- `.env` contains only version vars + sizing/topology. No `_ENABLED` toggles exist yet.
- `startup.dev.py` runs ALL steps in order; no filtering. Steps are discovered by filename pattern in `scripts/steps/`.
- `scripts/steps/` contains ~30 step files numbered 01–29. Each step is a standalone Python script with `main()`.
- `component_versions.py` has `load_dotenv()`, `resolve()`, `get()`, `image_refs()`, `substitution_map()`, `marker_for()` — no toggle API yet.
- `--status` table shows step results from `output/startup.dev.log` and component versions from `output/provisioned.yaml`.
- `--storage` flag already exists on `startup.dev.py` (choices: `rook-ceph`, `local-path`) but only passes to step 02 and 05.

### Toggle resolution priority

1. Core components: always `True` (override ignored with warning)
2. `os.environ[f"HPDC_{component}_ENABLED"]` (set by shell export or `.env` via `load_dotenv`)
3. `ENABLED_DEFAULTS[component]` (hardcoded per-component default in `component_versions.py`)
4. `False` (safe default: new/unknown components are opt-in, not opt-out)

### Future consideration: HPDC_PROFILE

Named profiles (e.g., `HPDC_PROFILE=dev-minimal`) that expand to a preset set of toggles. Saved for future story — current `.env`-based approach is sufficient for now.

### Storage mutual exclusion

- `HPDC_STORAGE_BACKEND=rook-ceph` sets `ROOK_CEPH_ENABLED=True, LOCAL_PATH_ENABLED=False`
- `HPDC_STORAGE_BACKEND=local-path` sets `ROOK_CEPH_ENABLED=False, LOCAL_PATH_ENABLED=True`
- If both are explicitly `true` in env, startup errors with: "Set HPDC_STORAGE_BACKEND to one of: rook-ceph, local-path"

### Key files to modify

- `scripts/gitops/component_versions.py` — add `ENABLED_DEFAULTS`, `is_enabled()`, storage backend resolution
- `scripts/startup.dev.py` — filter steps by toggle, show "skipped" in status
- `scripts/gitops/render_app_of_apps.py` (new) — filter ArgoCD apps by toggles
- `.env.dev.example` (new) — committed toggle reference
- `.env.dev` (new) — dev defaults
- `.env.prod` (new) — prod defaults (all enabled)
- `tests/test_component_versions.py` — toggle tests
- `tests/test_startup_dev.py` — skipped step tests
- `README.md` — toggle documentation

### App-of-apps toggle mapping

Each `gitops/apps/*.yaml` maps to a component toggle. The render step reads toggles and only writes enabled app manifests to `gitops/apps/`.

| App YAML | Toggle Variable | Dev Default | Prod Default |
|----------|----------------|-------------|--------------|
| `agent-engine.yaml` | (future) | — | — |
| `alerts.yaml` | `HPDC_ALERTMANAGER_ENABLED` | false | true |
| `backstage.yaml` | `HPDC_BACKSTAGE_ENABLED` | false | true |
| `casbin.yaml` | `HPDC_CASBIN_ENABLED` | true | true |
| `casdoor.yaml` | `HPDC_CASDOOR_ENABLED` | true | true |
| `crds-gateway.yaml` | `HPDC_ENVOY_GATEWAY_ENABLED` | true | true |
| `crds-hpdc.yaml` | (always) | true | true |
| `entity-store.yaml` | (future) | — | — |
| `envoy-gateway.yaml` | `HPDC_ENVOY_GATEWAY_ENABLED` | true | true |
| `infisical.yaml` | `HPDC_INFISICAL_ENABLED` | false | true |
| `kafka.yaml` | (future) | — | — |
| `observability.yaml` | `HPDC_GRAFANA_ENABLED` | false | true |
| `openapi.yaml` | `HPDC_SWAGGER_UI_ENABLED` | false | true |
| `platform.yaml` | (always) | true | true |
| `regional-sovereignty.yaml` | (future) | — | — |
| `security.yaml` | `HPDC_CILIUM_ENABLED` | true | true |
| `tool-ui.yaml` | (future) | — | — |
| `victoria-metrics.yaml` | `HPDC_VICTORIA_METRICS_ENABLED` | false | true |

### Testing standards

Plain pytest functions, no conftest/fixtures; each test file has standalone `main()` runner; canonical invocation: `python3 -m pytest tests/ -q`.

### References

- [Source: scripts/startup.dev.py:129–178] `print_status()` — current status table
- [Source: scripts/startup.dev.py:181–188] `discover_steps()` — step discovery
- [Source: scripts/startup.dev.py:360–465] `main()` — CLI args, step execution loop
- [Source: scripts/gitops/component_versions.py:59–107] `DEFAULTS` — current version vars
- [Source: .env:1–81] Current .env structure (no toggles)
- [Source: scripts/steps/] Step files (01–29) — each is a standalone installer

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- Task 1-2: Created `.env.dev.example`, `.env.dev`, `.env.prod` with all version vars and toggle vars
- Task 3: Added `ENABLED_DEFAULTS`, `CORE_TOGGLES`, `is_enabled()`, `list_toggles()`, `_resolve_storage_backend()` to `component_versions.py`
- Task 4: Added `STEP_TOGGLE_MAP`, `_is_step_enabled()`, `_step_toggle_reason()` to `startup.dev.py`; added `--all` flag; disabled steps show as "skipped" in status
- Task 5: Single point of control in `startup.dev.py` filters before calling installers
- Task 6: Storage backend mutual exclusion enforced in `_resolve_storage_backend()`; raises ValueError if both enabled
- Task 7: Added 7 new tests to `test_component_versions.py` (17 total); added 2 new tests to `test_startup_dev.py` (5 total); all 22 tests pass
- Task 8: Created `scripts/gitops/render_app_of_apps.py` with toggle-based filtering; bootstraps `gitops/apps.all/` from `gitops/apps/` on first run
- Task 9: Updated README.md with toggle system documentation, dev vs prod defaults, and app-of-apps filtering

### File List

- `.env.dev.example` (new) — committed toggle reference with all version vars and toggle vars
- `.env.dev` (new) — dev defaults (minimal footprint)
- `.env.prod` (new) — prod defaults (full stack, all enabled)
- `scripts/gitops/component_versions.py` (modified) — added `ENABLED_DEFAULTS`, `CORE_TOGGLES`, `is_enabled()`, `list_toggles()`, `_resolve_storage_backend()`
- `scripts/startup.dev.py` (modified) — added `STEP_TOGGLE_MAP`, `_is_step_enabled()`, `_step_toggle_reason()`, `--all` flag, toggle filtering in status and execution
- `scripts/gitops/render_app_of_apps.py` (new) — filter ArgoCD apps by toggles
- `gitops/apps.all/` (new) — staging directory with all app YAMLs (canonical source)
- `tests/test_component_versions.py` (modified) — added 7 toggle tests
- `tests/test_startup_dev.py` (modified) — added 2 toggle tests
- `README.md` (modified) — added toggle system documentation

### Change Log

- 2026-08-26: Initial implementation of Story 11.8 — Component Feature Toggles via .env
