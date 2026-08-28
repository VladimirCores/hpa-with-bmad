---
story_key: 12-1-docker-kind-default-dev-provisioning-with-local-path
epic: 12
status: ready-for-dev
baseline_commit: TBD
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

- [ ] Task 1: Flip default provider to `kind` in `.env` / `.env.example` (AC: #1)
  - [ ] Change `HPDC_PROVIDER=qemu` → `kind` (`.env:14`, `.env.example:13-14`)
  - [ ] Rewrite the comment to enumerate the three options: `kind` = kind + local-path (fast dev default), `docker` = Talos-on-Docker + local-path, `qemu` = Talos/QEMU + rook-ceph (localhost prod-eval)
- [ ] Task 2: Add disk-capacity knobs to `.env` / `.env.example` (AC: #6)
  - [ ] Add `HPDC_DISK_CAPACITY_WORKER=10Gi` and `HPDC_DISK_CAPACITY_CONTROL_PLANE=10Gi` (k8s quantity units; document Gi vs GiB)
  - [ ] Keep `HPDC_DISKS` for qemu backward-compat; document precedence (explicit `HPDC_DISKS` wins for qemu data disks, else synthesize `virtio:<HPDC_DISK_CAPACITY_WORKER>`)
- [ ] Task 3: Route full lifecycle by `HPDC_PROVIDER` (3-way) (AC: #4)
  - [ ] `startup.dev.py`: `--provider` choices (`:449`) → `["kind","docker","qemu"]`; default reads `HPDC_PROVIDER` (now `kind`)
  - [ ] `startup.dev.py` step `02-bootstrap-talos-dev.py` (`:285`): when `kind`, invoke `bootstrap_kind_dev.py`; when `docker`/`qemu`, invoke `bootstrap_talos_dev.py` with `--provider <value>`; keep `--storage` passthrough (`:311-316`, `:384-387`)
  - [ ] `--storage` default (`:448`) becomes provider-derived: local-path for `kind`/`docker`, rook-ceph for `qemu`
  - [ ] `stop.dev.py`: 3-way teardown dispatch by `HPDC_PROVIDER` (kind container teardown; docker Talos-on-Docker teardown; qemu VM teardown) — preserve existing QEMU-aware + `which()` docker guards from q2; add kind/docker branches
  - [ ] Storage step `05-install-storage-dev` (`:43`, `:243-244`) already storage-aware — confirm it receives the provider-derived backend
- [ ] Task 4: Consume disk capacities in `bootstrap_kind_dev.py` (AC: #6, #8)
  - [ ] Read `HPDC_DISK_CAPACITY_WORKER` / `HPDC_DISK_CAPACITY_CONTROL_PLANE` via `load_env()` + `os.getenv` (mirror `bootstrap_talos_dev.py:60-69` memory pattern)
  - [ ] Patch the `local-path-config` ConfigMap `defaultVolumeSize` to `HPDC_DISK_CAPACITY_WORKER`
  - [ ] Size kind node backing store / document control-plane vs worker disk expectation
- [ ] Task 5: Consume disk capacities in `bootstrap_talos_dev.py` for BOTH `docker` and `qemu` (AC: #6)
  - [ ] Derive control-plane OS disk from `HPDC_DISK_CAPACITY_CONTROL_PLANE` and worker OS + data disk(s) from `HPDC_DISK_CAPACITY_WORKER`; replace the static `HPDC_DISKS` passthrough (`:67-69`, `:576-578`) with capacity-derived `virtio:<size>` entries
  - [ ] Apply for `--provider docker` (Talos-on-Docker data disk via `--disks`) and `--provider qemu` (Ceph data disk); preserve qemu Ceph requirement (worker gets ≥1 data disk)
- [ ] Task 6: De-hardcode local-path version + de-duplicate installer (AC: #7)
  - [ ] `bootstrap_kind_dev.py:174` hardcoded `v0.0.31` URL → use `HPDC_LOCAL_PATH_PROVISIONER_VERSION` (consistent with `install_storage_dev.py:24`)
  - [ ] Prefer reusing `install_storage_dev.py` (local-path path) for both kind and docker over the inline install in `bootstrap_kind_dev.py` to avoid two code paths
- [ ] Task 7: Enforce cleanup-before-recreate for all three (AC: #5)
  - [ ] Ensure `startup.dev.py` tears down any running cluster of the selected provider (resource cleanup) before step 02 bootstrap; verify no orphaned kind/docker/qemu state across re-runs
- [ ] Task 8: Verify all three providers (AC: #1, #2, #3, #5, #8)
  - [ ] `kind`: full `startup.dev.py --offline --apply` → kind + local-path converges, PVC binds at default size; stop→start idempotent
  - [ ] `docker`: `startup.dev.py --offline --apply` → Talos-on-Docker + local-path converges, nodes Ready
  - [ ] `qemu`: `startup.dev.py --offline --apply` → Talos + rook-ceph still works (regression check vs q2)
  - [ ] `stop.dev.py --apply` clean for all three, then re-apply idempotent cycle

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

### File List
