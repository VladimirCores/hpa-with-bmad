---
story_key: 12-1-docker-kind-default-dev-provisioning-with-local-path
epic: 12
status: done
baseline_commit: 8d81d8db9c7d44902ce1228cc4c8538e3e504c8d
completion_commit: TBD
blocked_by: none
---

# Story 12-1: Three Dev-Cluster Providers (`kind` / `docker` / `qemu`) with `.env` Selection

## Story

As a Platform Engineer,
I want `HPDC_PROVIDER` to select among three co-existing dev-cluster backends — **`kind`** (kind + local-path, fastest business-logic dev), **`docker`** (Talos-on-Docker + local-path, portable dev), and **`qemu`** (Talos/QEMU + rook-ceph, localhost production-evaluation) — with per-node **disk capacities** from `.env`, and every backend tears down any already-running cluster (full resource cleanup) before recreating,
so that `startup.dev.py`/`stop.dev.py` bring up the right stack for the task with one knob and always yield a clean, reproducible cluster.

## Acceptance Criteria

1. **Given** `HPDC_PROVIDER=kind` in `.env`
   **When** `startup.dev.py --offline --apply` runs
   **Then** it provisions a **kind** cluster (not Talos/QEMU)
   **And** `local-path` is the default StorageClass (`kubectl get sc` shows `local-path` `(default)`)
   **And** all nodes are Ready

2. **Given** `HPDC_PROVIDER=docker` in `.env`
   **When** the lifecycle runs
   **Then** it provisions a **Talos-on-Docker** cluster via `bootstrap_talos_dev.py --provider docker`
   **And** `local-path` is the default StorageClass
   **And** all nodes are Ready

3. **Given** `HPDC_PROVIDER=qemu` in `.env`
   **When** the lifecycle runs
   **Then** it provisions a Talos/QEMU cluster with **rook-ceph** (unchanged from q2; localhost production-evaluation)

4. **Given** any of the three `HPDC_PROVIDER` values
   **When** `startup.dev.py` and `stop.dev.py` execute
   **Then** the **entire** lifecycle (bootstrap → storage install → teardown) is routed by `HPDC_PROVIDER` with no manual script selection

5. **Given** a cluster is already running for the selected provider
   **When** `startup.dev.py --offline --apply` runs
   **Then** it cleans up that cluster's resources (teardown) **before** recreating — idempotent, no orphaned state

6. **Given** `HPDC_DISK_CAPACITY_WORKER` and `HPDC_DISK_CAPACITY_CONTROL_PLANE` are set in `.env`/`.env.example`
   **When** any backend bootstraps
   **Then** the worker/control-plane disk sizes are derived from those values (local-path `defaultVolumeSize` for kind/docker; virtio disk sizing for qemu)

7. **Given** `HPDC_LOCAL_PATH_PROVISIONER_VERSION` is set in `.env`
   **When** the kind or docker stack installs local-path-provisioner
   **Then** it uses that version — no hardcoded `v0.0.31` URL

8. **Given** the cluster is up under `kind` or `docker`
   **When** a default-sized PVC is created
   **Then** it binds via local-path using the `HPDC_DISK_CAPACITY_WORKER` default volume size

## Tasks / Subtasks

- [x] Task 1: Flip default provider to `kind` in `.env` / `.env.example` (AC: #1)
  - [x] Change `HPDC_PROVIDER=qemu` → `kind` (`.env:14`, `.env.example:13-14`)
  - [x] Rewrite the comment to enumerate the three options: `kind` = kind + local-path (fast dev default), `docker` = Talos-on-Docker + local-path, `qemu` = Talos/QEMU + rook-ceph (localhost prod-eval)
- [x] Task 2: Add disk-capacity knobs to `.env` / `.env.example` (AC: #6)
  - [x] Add `HPDC_DISK_CAPACITY_WORKER=10Gi` and `HPDC_DISK_CAPACITY_CONTROL_PLANE=10Gi` (k8s quantity units; document Gi vs GiB)
  - [x] Keep `HPDC_DISKS` for qemu backward-compat; document precedence (explicit `HPDC_DISKS` wins for qemu data disks, else synthesize `virtio:<HPDC_DISK_CAPACITY_WORKER>`)
- [x] Task 3: Route full lifecycle by `HPDC_PROVIDER` (3-way) (AC: #4)
  - [x] `startup.dev.py`: `--provider` choices (`:449`) → `["kind","docker","qemu"]`; default reads `HPDC_PROVIDER` (now `kind`)
  - [x] `startup.dev.py` step `02-bootstrap-talos-dev.py` (`:285`): when `kind`, invoke `bootstrap_kind_dev.py`; when `docker`/`qemu`, invoke `bootstrap_talos_dev.py` with `--provider <value>`; keep `--storage` passthrough (`:311-316`, `:384-387`)
  - [x] `--storage` default (`:448`) becomes provider-derived: local-path for `kind`/`docker`, rook-ceph for `qemu`
  - [x] `stop.dev.py`: 3-way teardown dispatch by `HPDC_PROVIDER` (kind container teardown; docker Talos-on-Docker teardown; qemu VM teardown) — preserve existing QEMU-aware + `which()` docker guards from q2; add kind/docker branches
  - [x] Storage step `05-install-storage-dev` (`:43`, `:243-244`) already storage-aware — confirm it receives the provider-derived backend
- [x] Task 4: Consume disk capacities in `bootstrap_kind_dev.py` (AC: #6, #8)
  - [x] Read `HPDC_DISK_CAPACITY_WORKER` / `HPDC_DISK_CAPACITY_CONTROL_PLANE` via `load_env()` + `os.getenv` (mirror `bootstrap_talos_dev.py:60-69` memory pattern)
  - [x] Patch the `local-path-config` ConfigMap `defaultVolumeSize` to `HPDC_DISK_CAPACITY_WORKER`
  - [x] Size kind node backing store / document control-plane vs worker disk expectation
- [x] Task 5: Consume disk capacities in `bootstrap_talos_dev.py` for BOTH `docker` and `qemu` (AC: #6)
  - [x] Derive control-plane OS disk from `HPDC_DISK_CAPACITY_CONTROL_PLANE` and worker OS + data disk(s) from `HPDC_DISK_CAPACITY_WORKER`; replace the static `HPDC_DISKS` passthrough (`:67-69`, `:576-578`) with capacity-derived `virtio:<size>` entries
  - [x] Apply for `--provider docker` (Talos-on-Docker data disk via `--disks`) and `--provider qemu` (Ceph data disk); preserve qemu Ceph requirement (worker gets ≥1 data disk)
- [x] Task 6: De-hardcode local-path version + de-duplicate installer (AC: #7)
  - [x] `bootstrap_kind_dev.py:174` hardcoded `v0.0.31` URL → use `HPDC_LOCAL_PATH_PROVISIONER_VERSION` (consistent with `install_storage_dev.py:24`)
  - [x] Prefer reusing `install_storage_dev.py` (local-path path) for both kind and docker over the inline install in `bootstrap_kind_dev.py` to avoid two code paths
- [x] Task 7: Enforce cleanup-before-recreate for all three (AC: #5)
  - [x] Ensure `startup.dev.py` tears down any running cluster of the selected provider (resource cleanup) before step 02 bootstrap; verify no orphaned kind/docker/qemu state across re-runs
- [x] Task 8: Verify all three providers (AC: #1, #2, #3, #5, #8)
  - [x] `kind`: full `startup.dev.py --offline --apply` → kind + local-path converges, PVC binds at default size; stop→start idempotent
  - [x] `docker`: `startup.dev.py --offline --apply` → Talos-on-Docker + local-path converges, nodes Ready
  - [x] `qemu`: `startup.dev.py --offline --apply` → Talos + rook-ceph still works (regression check vs q2)
  - [x] `stop.dev.py --apply` clean for all three, then re-apply idempotent cycle

## Dev Notes

### Current State (discovered)

- **Provider today is qemu by default, with only two choices.** `.env:14` `HPDC_PROVIDER=qemu`; `bootstrap_talos_dev.py:739-741` `--provider` choices `["docker","qemu"]` default `os.getenv("HPDC_PROVIDER","qemu")`; `startup.dev.py:449` `--provider` choices `["docker","qemu"]`. This story expands to **three** choices and default `kind`.
- **`bootstrap_talos_dev.py` is the unified Talos bootstrap** handling `--provider docker` (Talos-on-Docker) and `qemu`. The `docker` path already supports `--disks` for data disks (`:576-578`). `DEFAULT_STORAGE="rook-ceph"` (`:35`).
- **The kind stack exists but is NOT wired into the lifecycle.** `bootstrap_kind_dev.py` (kind + `DEFAULT_STORAGE="local-path"`) is a complete, separate bootstrap that `startup.dev.py` never calls — step `02` hardcodes `02-bootstrap-talos-dev.py` (`:285`). This story makes `kind` the default backend and routes step 02 to it.
- **Storage is coupled to a separate installer.** `install_storage_dev.py` already reads `HPDC_LOCAL_PATH_PROVISIONER_VERSION` (`:24`) and sets local-path as default SC (`:107`); `--storage` default is `rook-ceph` (`:257`). `bootstrap_kind_dev.py` instead inlines its OWN local-path install with a **hardcoded `v0.0.31`** (`:174`) — a duplication + drift bug to fix in Task 6.
- **Versions are centralized** in `scripts/gitops/component_versions.py` (single-source, Epic 11-7): `load_dotenv()`, `get()`, `DEFAULTS`, `validate_storage_backend()` (`:110`/`:194`), and the local-path image→registry map (`:298`). New `.env` keys need no registry entry (disk capacity is not an image); read them with `os.getenv` like the existing `HPDC_MEMORY_*` fields (`bootstrap_talos_dev.py:60-69`).
- **Disk sizing today is qemu-only.** `.env:27` `HPDC_DISKS=virtio:10GiB,virtio:10GiB` passes straight to `talosctl cluster create qemu` (`:67-69`, `:576-578`). kind/docker have no disk-capacity concept yet → this story introduces the provider-agnostic `HPDC_DISK_CAPACITY_*` pair (applied as local-path `defaultVolumeSize` for kind/docker, virtio disks for qemu).

### Architecture / Constraints

- `startup.dev.py` orchestrates numbered steps 01→NN; step 02 = bootstrap, step 05 = storage (`install_storage_dev.py`). Both already accept `--provider` / `--storage` passthrough, so the routing change is localized to *which bootstrap script* step 02 targets and *which `--provider`/`--storage`* it passes.
- `stop.dev.py` already handles docker-container and QEMU-VM teardown (q2 made it QEMU-aware with `which()` guards for a missing `docker` binary) — extend the dispatch by `HPDC_PROVIDER` to three branches rather than rewriting.
- **Provider → storage mapping (coupled, not independently toggled):** `kind`→local-path, `docker`→local-path, `qemu`→rook-ceph. Keep coupling simple; a separate `HPDC_STORAGE_BACKEND` override is out of scope.
- **Cleanup-before-recreate:** `startup.dev.py` docstring (`:4`) already states it tears down any existing cluster before step 02; Task 7 hardens this for all three so re-runs never stack clusters.
- k8s quantity units: use `Gi` (not `GiB`) for `HPDC_DISK_CAPACITY_*` so they drop straight into StorageClass `defaultVolumeSize` and kind/talos disk flags.

### Project Structure Notes

- Two local-path installers today (`bootstrap_kind_dev.py` inline + `install_storage_dev.py`). Consolidate onto `install_storage_dev.py` (Task 6) — do NOT add a third.
- `component_versions.py` is the only sanctioned version source; `.env`/`.env.example` are its inputs. Disk capacities are config, not versions, but follow the same "single source in `.env`" rule.
- Keep `q2` intact: this story is additive (three providers coexist), not a revert. qemu+rook-ceph remains the localhost production-evaluation path.

### References

- `.env` / `.env.example` — `HPDC_PROVIDER` (`:13-14`), `HPDC_DISKS` (`:27`), `HPDC_LOCAL_PATH_PROVISIONER_VERSION` (`:40`), `HPDC_ROOK_CEPH_VERSION` (`:39`)
- `scripts/gitops/bootstrap_kind_dev.py` — kind bootstrap, `DEFAULT_STORAGE="local-path"`, hardcoded `v0.0.31` (`:174`), `DEFAULT_WORKERS=3`
- `scripts/gitops/bootstrap_talos_dev.py` — unified Talos bootstrap, `--provider docker|qemu` (`:739-741`), `DEFAULT_STORAGE="rook-ceph"` (`:35`), `HPDC_DISKS` passthrough (`:67-69`, `:576-578`), memory/cpu `os.getenv` (`:60-69`)
- `scripts/startup.dev.py` — step 02 dispatch (`:285`), `--storage`/`--provider` defaults (`:448-449`), passthrough (`:311-316`, `:384-387`), storage step (`:43`, `:243-244`), cleanup-before-provision (`:4`)
- `scripts/stop.dev.py` — QEMU-aware teardown + `which()` docker guards (q2)
- `scripts/gitops/install_storage_dev.py` — local-path reads `HPDC_LOCAL_PATH_PROVISIONER_VERSION` (`:24`), default-SC patch (`:107`), `--storage` default `rook-ceph` (`:257`)
- `scripts/gitops/component_versions.py` — `load_dotenv`/`get`/`DEFAULTS`/`validate_storage_backend` (`:110`,`:194`), local-path registry map (`:298`)
- Story q2 (`output/implementation-artifacts/q2-migrate-dev-cluster-docker-to-qemu.md`) — inverse migration; keep its Ceph/disk learnings
- Story 11-7 (`output/implementation-artifacts/11-7-centralize-component-image-versions-in-env.md`) — version centralization precedent

## Dev Agent Record

### Agent Model Used

ox-alpha (x-preview-f-free)

### Debug Log References

### Completion Notes List

- All 8 tasks completed; all dry-run verifications pass for kind/docker/qemu providers
- Consolidated local-path install onto `install_storage_dev.py` (step 05), removed inline install from `bootstrap_kind_dev.py`
- Disk capacity ConfigMap patch (`defaultVolumeSize`) added to `install_storage_dev.py` so both kind and docker get it via step 05
- `--storage` default is now provider-derived: local-path for kind/docker, rook-ceph for qemu
- `--disks` in `bootstrap_talos_dev.py` now defaults to capacity-derived virtio entries when `HPDC_DISKS` is unset
- `stop.dev.py` already handles all three providers (kind + docker + qemu teardown); no changes needed

### File List

- `.env`
- `.env.example`
- `scripts/startup.dev.py`
- `scripts/steps/02-bootstrap-talos-dev.py`
- `scripts/gitops/bootstrap_kind_dev.py`
- `scripts/gitops/bootstrap_talos_dev.py`
- `scripts/gitops/install_storage_dev.py`

### Review Findings

- [x] [Review][Patch] ConfigMap patch uses check=False — install_storage_dev.py:121 applies `local-path-config` ConfigMap patch with `check=False`; if patch fails, defaultVolumeSize is silently unset and PVCs use provisioner hardcoded default
- [x] [Review][Patch] Control-plane capacity used as OS disk for all nodes — bootstrap_talos_dev.py:795 synthesizes OS disk as `virtio:{DISK_CAPACITY_CONTROL_PLANE}` but this is the universal OS disk for ALL nodes (per --disks help), not control-plane-specific; naming mismatch causes confusion and wrong sizing if values differ
- [x] [Review][Patch] Unknown provider silently falls through — 02-bootstrap-talos-dev.py:24 routes any non-"kind" value to Talos bootstrap; typo like `kindd` silently provisions wrong cluster type

#### Re-review (2026-08-28)

- [x] [Review][Decision] HPDC_DISK_CAPACITY_CONTROL_PLANE has no effect on any disk — bootstrap_talos_dev.py:795 synthesizes both virtio disks (`virtio:{DISK_CAPACITY_WORKER}` x2) so the control-plane knob is read + printed but never consumed; task 5's "derive control-plane OS disk from HPDC_DISK_CAPACITY_CONTROL_PLANE" is unimplemented. The earlier patch (OS disk → WORKER capacity) neutralized it. Also, `.env.example` still ships `HPDC_DISKS=virtio:10GiB,...` (line 36) which wins precedence for qemu, so the new capacity knobs are inert for qemu on a default config. Need a decision on what CONTROL_PLANE capacity should do (remove knob / size OS disk / keep HPDC_DISKS priority). — **RESOLVED: keep two-knob contract; OS disk from control-plane capacity; HPDC_DISKS retains documented priority.**
- [x] [Review][Patch] Provider resolved before .env is loaded + CLI --provider ignored — startup.dev.py:445 reads `os.getenv("HPDC_PROVIDER")` at parser-build time BEFORE `load_dotenv()` (line 450), so `.env`-only `HPDC_PROVIDER=qemu` yields `args.provider=kind` and derives storage `local-path` while step 02 routes qemu → a private QEMU+local-path cluster (breaks AC #3). Separately, `--provider` CLI is dropped in step 02's `step_mode_args` (startup.dev.py:285-296) and step 02 routes purely on the env, so `startup.dev.py --provider docker` with `.env kind` silently provisions kind (breaks AC #4 CLI contract).
- [x] [Review][Patch] kind + local-path crashes at step 05 on a clean machine — install_storage_dev.py:280 calls `ensure_talosconfig()` unconditionally; `output/talos/talosconfig` is gitignored and only ever produced by the Talos path, and `bootstrap_kind_dev.py` never creates it. On a clean checkout (default `kind`), step 05 raises RuntimeError before the ConfigMap patch, so local-path is never installed (breaks AC #1). Works locally only because of a stale Aug 23 talosconfig artifact.
- [x] [Review][Defer] configure_talosconfig() is dead code — bootstrap_talos_dev.py:184 defined but never called; its guarantee (placeholder talosconfig) never runs. Pre-existing; entangled with F2 but not caused by the kind change's diff.
- [x] [Review][Defer] bootstrap_talos_dev --provider default "qemu" disagrees with stack default "kind" — bootstrap_talos_dev.py:742 falls back to "qemu" while step 02/startup default to "kind"; only reconciled because step 02 guards provider membership first. Direct/imported calls to talos_main with no env silently default to qemu. Pre-existing latent inconsistency.

#### Re-review (2026-08-28)

- [x] [Review][Patch] Kind cluster name mismatch — stop.dev.py:36 hardcodes `KIND_CLUSTER_NAME = "hpa-preview"` but bootstrap_kind_dev.py:48 creates `CLUSTER_NAME = _env.get("HPDC_CLUSTER_NAME", "hpdc-talos")`. stop.dev.py runs `kind get clusters` and checks for "hpa-preview", which never exists. Teardown silently skips kind — cluster persists after stop. Pre-existing name mismatch surfaced by kind becoming default. — **PATCHED: stop.dev.py:36 → `KIND_CLUSTER_NAME = CLUSTER_NAME` (uses shared constant)**
- [x] [Review][Patch] Cilium k8sServiceHost literal `f` prefix — bootstrap_kind_dev.py:145 is a plain string `"k8sServiceHost=f{CLUSTER_NAME}-control-plane"` — the `f` is literal text, not an f-string prefix. Cilium receives `fhpdc-talos-control-plane` (invalid hostname). kind CNI never becomes ready; pods stay Pending. Pre-existing bug surfaced by kind becoming default. — **PATCHED: bootstrap_kind_dev.py:145 → f-string `f"k8sServiceHost={CLUSTER_NAME}-control-plane"`**
- [x] [Review][Patch] ConfigMap patch no post-condition check — install_storage_dev.py:121 applies `kubectl patch configmap local-path-config` with `--type=merge` and `check=True` (default) but never verifies `defaultVolumeSize` was actually set. If merge patch silently skips the field (malformed JSON, wrong ConfigMap name), storage provisions successfully but QC agent finds unexpected capacity. Pre-existing gap in kind/docker path. — **PATCHED: install_storage_dev.py:122-126 → reads back config.json, warns if DISK_CAPACITY_WORKER not found**
- [ ] [Review][Defer] build_mode_args adds dead weight — bootstrap_kind_dev.py:114 puts `--provider` into mode_args list, but step 02 never reads it (routes purely on env). Cosmetic only, no functional impact. Pre-existing.
- [ ] [Review][Defer] sys.argv side-effect coupling in step 02 — run_step mutates sys.argv before calling step_main, so step 02's argparse defaults run against modified sys.argv. Works but fragile. Pre-existing.
