---
story_key: 12-2-split-env-into-three-config-layers
epic: 12
status: done
baseline_commit: 3105e72
completion_commit: TBD
blocked_by: 12-1-docker-kind-default-dev-provisioning-with-local-path
---

# Story 12-2: Split `.env` Into Three Config Layers (Provisioning / Components / Versions)

## Story

As a Platform Engineer,
I want the monolithic `.env` file split into three separate, composable config layers — **provisioning** (`.env.{env}`), **component toggles** (`.env.components.{env}`), and **version pinning** (`.env.versions.{env}`) — loaded together by the bootstrap entrypoint,
So that environment sizing, feature toggles, and version pins are independently editable without merge-conflict noise, and `.env.example` / `.env.components.example` / `.env.versions.example` serve as committed templates for each layer.

## Acceptance Criteria

1. **Given** the project root has three example templates
   **When** a new developer clones the repo
   **Then** they find `.env.example`, `.env.components.example`, and `.env.versions.example` at the project root
   **And** each example file documents every variable with inline comments
   **And** no variable appears in more than one example file (zero duplication across layers)

2. **Given** `.env.example` contains provisioning variables only
   **When** a developer copies `.env.example` → `.env`
   **Then** `.env` contains ONLY: `HPDC_PROVIDER`, `HPDC_CONTROLPLANES`, `HPDC_WORKERS`, `HPDC_CPUS_*`, `HPDC_MEMORY_*`, `HPDC_DISK_CAPACITY_*`, `HPDC_SUBNET`, `HPDC_DISKS`, `HPDC_STORAGE_BACKEND`
   **And** no version variables or component toggles appear in `.env`

3. **Given** `.env.components.example` contains component toggles only
   **When** a developer copies `.env.components.example` → `.env.components`
   **Then** `.env.components` contains ONLY `HPDC_*_ENABLED` toggles and `HPDC_STORAGE_BACKEND`
   **And** no version variables or provisioning sizing variables appear in `.env.components`

4. **Given** `.env.versions.example` contains version pins only
   **When** a developer copies `.env.versions.example` → `.env.versions`
   **Then** `.env.versions` contains ONLY `HPDC_*_VERSION`, `HPDC_*_CHART_VERSION`, `HPDC_*_TAG`, and `HPDC_KUBECTL_VERSION`
   **And** no provisioning sizing variables or component toggles appear in `.env.versions`

5. **Given** `component_versions.load_dotenv()` is the single dotenv loader
   **When** the bootstrap entrypoint runs (e.g., `startup.dev.py`, `bootstrap_talos_dev.py`, `bootstrap_kind_dev.py`)
   **Then** it loads all three files in order: `.env` → `.env.components` → `.env.versions`
   **And** existing environment variables always win over file values (current `setdefault` semantics preserved)
   **And** the call site is a single `load_dotenv()` invocation with an optional list of extra files

6. **Given** the three-file split is in place
   **When** `component_versions.get()` is called for any version variable
   **Then** it resolves from `.env.versions` (or env override) identically to today
   **And** `ENABLED_DEFAULTS` in `component_versions.py` continues to provide committed defaults for toggles
   **And** no script imports or reads `.env` directly — all access goes through `component_versions`

7. **Given** `.gitignore` is updated
   **When** a developer creates local `.env`, `.env.components`, `.env.versions`
   **Then** all three are gitignored
   **And** the three `.example` files remain tracked

8. **Given** the epics file describes Story 12.1 as "Environment Configuration Audit & Consolidation"
   **When** this story is complete
   **Then** every hardcoded value identified in the audit is in the correct layer
   **And** the sprint-status entry for 12-2 reflects completion

## Tasks / Subtasks

- [x] Task 1: Audit current `.env` and classify every variable into one of three layers (AC: #1, #2, #3, #4)
  - [x] Read `.env`, `.env.dev.example`, `.env.example` and list every `HPDC_*` variable
  - [x] Classify each as PROVISIONING (sizing/topology/network/disks), COMPONENT (toggles/storage backend), or VERSION (version/chart/tag)
  - [x] Identify any variables that appear in multiple categories (e.g., `HPDC_STORAGE_BACKEND` is both a component toggle and affects provisioning)
  - [x] Document classification decisions in the story Dev Notes

- [x] Task 2: Create `.env.components.example` (AC: #3)
  - [x] Extract all `HPDC_*_ENABLED` toggles from `.env.dev.example` into new file
  - [x] Include `HPDC_STORAGE_BACKEND` (it controls which storage installer runs)
  - [x] Add section header comments explaining the toggle semantics (core always-on, opt-in defaults)
  - [x] Mirror the `ENABLED_DEFAULTS` dict from `component_versions.py` as committed defaults

- [x] Task 3: Create `.env.versions.example` (AC: #4)
  - [x] Extract all `HPDC_*_VERSION`, `HPDC_*_CHART_VERSION`, `HPDC_*_TAG` from `.env.dev.example` into new file
  - [x] Include `HPDC_KUBECTL_VERSION` and `HPDC_KUBERNETES_VERSION` (version pins, not sizing)
  - [x] Add section header comments grouping by category (CNI, storage, registry, GitOps, auth, observability, portal, utilities)
  - [x] Mirror the `DEFAULTS` dict from `component_versions.py` as committed defaults

- [x] Task 4: Slim down `.env.example` to provisioning only (AC: #2)
  - [x] Remove all version variables (moved to `.env.versions.example`)
  - [x] Remove all component toggles (moved to `.env.components.example`)
  - [x] Keep only: `HPDC_PROVIDER`, `HPDC_CONTROLPLANES`, `HPDC_WORKERS`, `HPDC_CPUS_*`, `HPDC_MEMORY_*`, `HPDC_DISK_CAPACITY_*`, `HPDC_SUBNET`, `HPDC_DISKS`
  - [x] Update header comments to reflect "provisioning & sizing only"

- [x] Task 5: Update `.env.dev.example` to reference the three layers (AC: #1)
  - [x] Replace current monolithic content with pointers to the three example files
  - [x] Or: remove `.env.dev.example` entirely if `.env.example` + `.env.components.example` + `.env.versions.example` cover all dev defaults
  - [x] Decision: keep `.env.dev.example` as a dev-specific override file (only non-default values) or remove it

- [x] Task 6: Update `component_versions.load_dotenv()` (AC: #5)
  - [x] Change signature to accept multiple files: `load_dotenv(env_files: list[Path] | None = None)`
  - [x] Default: load `[ROOT / ".env", ROOT / ".env.components", ROOT / ".env.versions"]` in order
  - [x] Preserve existing semantics: blank/comment lines skipped, `export ` prefix stripped, first `=` split, inline comments stripped, `setdefault` (env wins)
  - [x] Add a `load_all_dotenv()` convenience alias that loads the standard three-file set

- [x] Task 7: Update all call sites to use `load_all_dotenv()` (AC: #5, #6)
  - [x] `scripts/gitops/bootstrap_talos_dev.py:754` — `component_versions.load_dotenv(ROOT / ".env")` → `component_versions.load_all_dotenv()`
  - [x] `scripts/gitops/bootstrap_kind_dev.py:25` — `_cv.load_dotenv()` → `_cv.load_all_dotenv()` AND delete the duplicate `load_dotenv()` function at lines 30-46
  - [x] `scripts/startup.dev.py:196,450` — already calls `component_versions.load_dotenv()` → update to `load_all_dotenv()`
  - [x] `scripts/gitops/install_cilium_online.py:19` — already calls `component_versions.load_dotenv()` → update to `load_all_dotenv()`
  - [x] Verify no script reads `.env` with `open()` / `read_text()` bypassing `component_versions`

- [x] Task 8: Update `.gitignore` (AC: #7)
  - [x] Add `.env.components` and `.env.versions` to gitignore (`.env` is likely already there)
  - [x] Verify `.env.example`, `.env.components.example`, `.env.versions.example` are tracked

- [x] Task 9: Update documentation (AC: #8)
  - [x] Update README or project-context.md to document the three-layer config system
  - [x] Document the loading order and override semantics
  - [x] Document how to add a new variable to the correct layer

- [x] Task 10: Verify end-to-end (AC: #1-#8)
  - [x] `component_versions.load_all_dotenv()` loads all three files
  - [x] `component_versions.get("HPDC_ARGOCD_VERSION")` resolves from `.env.versions`
  - [x] `component_versions.is_enabled("HPDC_ARGOCD_ENABLED")` resolves from `.env.components`
  - [x] `os.getenv("HPDC_PROVIDER")` resolves from `.env`
  - [x] No variable appears in two files (grep validation)
  - [x] `startup.dev.py` boots the cluster correctly with three-file config

## Dev Notes

### Variable Classification

| Variable | Layer | Rationale |
|----------|-------|-----------|
| `HPDC_PROVIDER` | Provisioning | Selects cluster backend (kind/docker/qemu) |
| `HPDC_CONTROLPLANES` | Provisioning | Node count |
| `HPDC_WORKERS` | Provisioning | Node count |
| `HPDC_CPUS_CONTROLPLANE` | Provisioning | Sizing |
| `HPDC_CPUS_WORKER` | Provisioning | Sizing |
| `HPDC_MEMORY_CONTROLPLANE` | Provisioning | Sizing |
| `HPDC_MEMORY_WORKER` | Provisioning | Sizing |
| `HPDC_DISK_CAPACITY_WORKER` | Provisioning | Disk sizing |
| `HPDC_DISK_CAPACITY_CONTROL_PLANE` | Provisioning | Disk sizing |
| `HPDC_SUBNET` | Provisioning | Cluster network |
| `HPDC_DISKS` | Provisioning | QEMU data disk spec |
| `HPDC_STORAGE_BACKEND` | Components | Controls which storage installer runs |
| `HPDC_*_ENABLED` | Components | Feature toggles |
| `HPDC_*_VERSION` | Versions | Image/chart version pins |
| `HPDC_*_CHART_VERSION` | Versions | Helm chart version pins |
| `HPDC_*_TAG` | Versions | Container image tags |
| `HPDC_KUBECTL_VERSION` | Versions | CLI version pin |
| `HPDC_KUBERNETES_VERSION` | Versions | K8s version pin (tied to Talos) |

### Current Loading Chain

```
component_versions.load_dotenv(ROOT / ".env")
  └─ seeds os.environ via setdefault (env wins)
  └─ DEFAULTS dict provides committed fallbacks
  └─ get(name) returns os.environ.get(name, DEFAULTS[name])
```

### Target Loading Chain

```
component_versions.load_all_dotenv()
  ├─ load_dotenv(ROOT / ".env")              # provisioning
  ├─ load_dotenv(ROOT / ".env.components")    # toggles
  └─ load_dotenv(ROOT / ".env.versions")     # versions
  └─ os.environ.setdefault per line (existing env wins)
  └─ DEFAULTS dict provides committed fallbacks (unchanged)
  └─ get(name) resolves identically
```

### Edge Cases

- **`HPDC_STORAGE_BACKEND`**: Lives in `.env.components` but is consumed by `validate_storage_backend()` in `component_versions.py`. No change needed — `get()` resolves from env regardless of which file set it.
- **`HPDC_KUBERNETES_VERSION`**: Version pin (goes in `.env.versions`) but also affects Talos provisioning. The provisioning scripts read it via `component_versions.get()`, so it resolves from `.env.versions` correctly.
- **`HPDC_PULSAR_ENABLED`**: Currently not in `.env.dev.example` but IS in `ENABLED_DEFAULTS`. Must be added to `.env.components.example`.
- **`HPDC_CASBIN_RBAC_ENABLED` / `HPDC_CASBIN_REBAC_ENABLED` / `HPDC_CASBIN_ABAC_ENABLED`**: Sub-system toggles, not in current `.env.dev.example`. Add to `.env.components.example`.

### File Structure (Target)

```
.env.example                  # provisioning: provider, sizing, network, disks
.env.components.example       # toggles: HPDC_*_ENABLED, HPDC_STORAGE_BACKEND
.env.versions.example         # versions: HPDC_*_VERSION, HPDC_*_CHART_VERSION, HPDC_*_TAG
.gitignore                    # ignores .env, .env.components, .env.versions
scripts/gitops/
  component_versions.py       # updated: load_dotenv() loads 3 files, load_all_dotenv() alias
```

### Duplicate `.env` Loaders (Must Consolidate)

`bootstrap_kind_dev.py:30-46` has its **own** `load_dotenv()` function that reads `ROOT / ".env"` independently of `component_versions.load_dotenv()`. This is exactly the DRY violation Story 12.2 targets. During this story, consolidate onto `component_versions.load_dotenv()` / `load_all_dotenv()` and delete the duplicate in `bootstrap_kind_dev.py`.

### References

- `.env` — current monolithic config (3068 bytes)
- `.env.dev.example` — current dev-specific example (7175 bytes, has all three categories mixed)
- `.env.example` — current base example (3022 bytes)
- `scripts/gitops/component_versions.py` — `load_dotenv()` at line 15, `DEFAULTS` at line 240, `ENABLED_DEFAULTS` at line 70
- `scripts/gitops/bootstrap_talos_dev.py:754` — calls `component_versions.load_dotenv(ROOT / ".env")`
- `scripts/gitops/bootstrap_kind_dev.py:25,30-46` — duplicate `.env` loader (`_cv.load_dotenv()` at module level + own `load_dotenv()` function)
- `scripts/startup.dev.py:196,450` — calls `component_versions.load_dotenv()`
- `scripts/gitops/install_cilium_online.py:19` — calls `component_versions.load_dotenv()`
- Story 11-7 (`output/implementation-artifacts/11-7-centralize-component-image-versions-in-env.md`) — version centralization precedent

## Dev Agent Record

### Agent Model Used

mimo-v2.5-free (opencode)

### Debug Log References

### Completion Notes List

- All 10 tasks completed; zero cross-layer variable duplication confirmed via grep
- Created `.env.components.example` (30 toggles + `HPDC_STORAGE_BACKEND`) and `.env.versions.example` (34 version pins)
- Slimmed `.env.example` to provisioning only (11 variables)
- Updated `component_versions.load_dotenv()` to accept `list[Path] | Path | None`; added `load_all_dotenv()` alias
- Updated 25+ call sites from `load_dotenv()` → `load_all_dotenv()` across all bootstrap/install scripts
- Deleted duplicate `load_env()` function in `bootstrap_kind_dev.py` (consolidated onto `component_versions`)
- Deleted unused `_load_dotenv_impl` import alias in `bootstrap_talos_dev.py`
- Updated `.gitignore` with `.env.components` and `.env.versions`
- Updated `project-context.md` with three-layer config documentation
- Code review 2026-08-31: 5 patches applied, 4 deferred, 4 dismissed; reverted bundled YAML changes (git-mirror storageClass, rook restartPolicy, rook image prefix); added Pulsar version pins to .env.versions.example; updated 7 test files to load_all_dotenv()

### File List

- `.env.example`
- `.env.components.example` (new)
- `.env.versions.example` (new)
- `.env.dev.example`
- `.gitignore`
- `scripts/gitops/component_versions.py`
- `scripts/gitops/bootstrap_kind_dev.py`
- `scripts/gitops/bootstrap_talos_dev.py`
- `scripts/startup.dev.py`
- `scripts/gitops/render_app_of_apps.py`
- `scripts/gitops/render_overlays.py`
- `scripts/gitops/install_cilium_online.py`
- `scripts/gitops/initialize_components.py`
- `scripts/gitops/install-backstage-dev.py`
- `scripts/gitops/install-casdoor-dev.py`
- `scripts/gitops/install-cert-manager-dev.py`
- `scripts/gitops/install-envoy-gateway-dev.py`
- `scripts/gitops/install-infisical-dev.py`
- `scripts/gitops/install-openapi-dev.py`
- `scripts/gitops/install_argocd_dev.py`
- `scripts/gitops/install_argoevents_dev.py`
- `scripts/gitops/install_argorollouts_dev.py`
- `scripts/gitops/install_cilium_dev.py`
- `scripts/gitops/install_cilium_mtls_dev.py`
- `scripts/gitops/install_harbor_dev.py`
- `scripts/gitops/install_kargo_dev.py`
- `scripts/gitops/install_rook_ceph_dev.py`
- `scripts/gitops/install_spegel_dev.py`
- `scripts/gitops/install_storage_dev.py`
- `scripts/gitops/preload_harbor_cache.py`
- `scripts/gitops/provision_local_git_mirror.py`
- `scripts/gitops/refresh_harbor_cache.py`
- `scripts/gitops/validate_offline_gitops_pipeline.py`
- `scripts/services/image-preflight.py`
- `gitops/git/base/git-mirror.yaml` (review patch: reverted storageClass)
- `gitops/rook-ceph/base/rook-dirs-bootstrap.yaml` (review patch: reverted restartPolicy + image)
- `tests/test_install_argocd_dev.py` (review patch: load_dotenv → load_all_dotenv)
- `tests/test_install_cert_manager_dev.py` (review patch)
- `tests/test_install_kargo_dev.py` (review patch)
- `tests/test_install_spegel_dev.py` (review patch)
- `tests/test_refresh_harbor_cache.py` (review patch)
- `tests/test_validate_offline_gitops_pipeline.py` (review patch)
- `tests/test_epic3_gateway_stack_dev.py` (review patch)
- `output/project-context.md`

### Review Findings

#### Re-review (2026-08-31)

- [x] [Review][Patch] git-mirror.yaml storageClassName hardcoded to rook-ceph-rbd — gitops/git/base/git-mirror.yaml:212 changed `storageClassName: standard` → `rook-ceph-rbd`; breaks local-path mode (PVC hangs in Pending when `HPDC_STORAGE_BACKEND=local-path`). Unrelated to env split. — PATCHED: reverted to `standard`
- [x] [Review][Patch] rook-dirs-bootstrap.yaml restartPolicy changed to Always — gitops/rook-ceph/base/rook-dirs-bootstrap.yaml:23 changed from `OnFailure` to `Always`; one-shot bootstrap pod now restarts infinitely after success. No `backoffLimit` or `activeDeadlineSeconds`. Unrelated to env split. — PATCHED: reverted to `OnFailure`
- [x] [Review][Patch] rook-dirs-bootstrap.yaml image registry prefix removed — gitops/rook-ceph/base/rook-dirs-bootstrap.yaml:26 changed `quay.io/rook/ceph:v1.20.6` → `rook/ceph:v1.20.6`; bare image name may fail in air-gapped setup if quay.io not in containerd mirror list. Unrelated to env split. — PATCHED: reverted to `quay.io/rook/ceph:v1.20.6`
- [x] [Review][Patch] .env.versions.example missing Pulsar version pins — `HPDC_PULSAR_VERSION` and `HPDC_PULSAR_OPERATOR_VERSION` are in `DEFAULTS` dict and `HPDC_PULSAR_ENABLED=true` is in `.env.components.example`, but neither pin appears in `.env.versions.example`. Breaks "all version pins in one file" contract. — PATCHED: added Pulsar section with both pins
- [x] [Review][Patch] 7 test files still use load_dotenv() — tests/test_install_argocd_dev.py, test_install_cert_manager_dev.py, test_install_kargo_dev.py, test_install_spegel_dev.py, test_refresh_harbor_cache.py, test_validate_offline_gitops_pipeline.py, test_epic3_gateway_stack_dev.py still call `component_versions.load_dotenv()` (loads only `.env`); should use `load_all_dotenv()` to exercise all three layers. — PATCHED: all 7 updated to `load_all_dotenv()`
- [x] [Review][Defer] bootstrap_talos_dev.py module-level DISK_CAPACITY reads — `os.getenv("HPDC_DISK_CAPACITY_WORKER")` at line 39 runs before `load_dotenv()` in `main()`, same pre-existing behavior as before this change (old code also read at module level).
- [x] [Review][Defer] load_dotenv([]) silently no-ops — empty list causes zero iterations; harmless since `load_all_dotenv()` constructs the correct list; no caller passes `[]`.
- [x] [Review][Defer] CLUSTER_NAME scope expanded — `dict(os.environ)` captures all three layers vs old `.env` only; correct behavior since CLUSTER_NAME is provisioning-scoped and would never appear in components/versions layers.
- [x] [Review][Defer] No cross-layer validation — `setdefault` silently ignores misplaced variables; documented rule in project-context.md is sufficient.
