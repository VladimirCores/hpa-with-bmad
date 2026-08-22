# Sprint Change Proposal — 2026-08-21

## Section 1: Issue Summary

**Trigger:** Epic Retrospective Sweep (2026-08-11) surfaced 5 live-cluster-gated action items (#3, #4, #8, #10, #12) and the 44-step `startup.dev.py` apply flow has never been run against a real cluster. The dev cluster provisioning (step 02) has only been exercised in dry-run mode.

**Problem statement:** The HPDC platform (10 epics, 59 stories) was validated entirely offline. The `--apply` flow that provisions VMs and configures components against a live Talos cluster has never been executed end-to-end. Additionally, `stop.dev.py` only handles kind clusters — no teardown exists for the Talos/QEMU cluster. Each dev session must cleanly shut down any existing cluster, recreate with idempotent persistent storage (Ceph/Rook), and proceed with component init.

**Evidence:**
- `output/talos/talosconfig` exists — partial bootstrap was run at some point
- No QEMU processes running — cluster VMs are stopped
- `stop.dev.py` only handles kind clusters (line 3: "Delete the local kind dev cluster")
- `live-cluster-verification-register.md` has 10 open entries (REG-01..10) all gated on B-001
- RED-phase ATDD scaffolds (alert pipeline journey, P0 soak, UI journeys) are skipped/blocked
- `bootstrap_talos_dev.py` calls `talosctl cluster create qemu` but has never been validated end-to-end

## Section 2: Impact Analysis

- **Epic Impact:** No existing epics modified. New Epic 11 created for dev cluster lifecycle + live verification.
- **Story Impact:** 4 new stories in Epic 11: VM provisioning, idempotent lifecycle, component init, live verification.
- **Artifact Conflicts:** None — PRD and architecture unchanged.
- **Technical Impact:** `startup.dev.py`, `stop.dev.py`, `bootstrap_talos_dev.py` need modification. New tests for lifecycle and idempotency.

## Section 3: Recommended Approach

**Path: Direct Adjustment** — create a new Epic 11 with 4 stories within the existing plan. No rollback, no scope reduction.

**Rationale:** All 10 epics are delivered and correct. The work is operational hardening to exercise existing deliverables against a live cluster. Low risk (additive), medium effort (~2-3 days), no PRD or architecture changes.

**Effort estimate:** ~2-3 days. **Risk:** low — additive work, no rollback. **Timeline impact:** blocks on QEMU/libvirt availability and Talos ISO pre-cache.

## Section 4: Detailed Change Proposals

### Epic 11: Dev Cluster Bring-Up & Verification

**Epic 11 Story 11.1: Dev Cluster VM Provisioning Lifecycle**

As a Platform Engineer,
I want the dev cluster startup to detect and shut down any existing running cluster before provisioning,
So that each dev session starts clean without resource conflicts.

**Acceptance Criteria:**

**Given** a dev cluster is already running (Talos/QEMU VMs or kind cluster)
**When** `startup.dev.py --offline --apply` is invoked
**Then** the existing cluster is detected and gracefully shut down
**And** QEMU processes and network resources are released
**And** persistent QEMU disk images are preserved for idempotent recreation
**And** the script exits with a non-zero status on failure to shut down

**Given** no dev cluster is running
**When** `startup.dev.py --offline --apply` is invoked
**Then** the cluster is provisioned from scratch
**And** the script exits with a non-zero status on failure to provision

**Implementation notes:** Requires extending `stop.dev.py` (currently kind-only) to handle Talos/QEMU teardown. The `bootstrap_talos_dev.py` already calls `talosctl cluster create qemu` — the teardown must reverse this. Persistent disk images (`output/qemu/talos-v*.img`) must survive the cycle.

---

**Epic 11 Story 11.2: Idempotent Startup with Persistent Storage**

As a Platform Engineer,
I want the dev cluster to be recreatable with idempotent persistent storage,
So that Ceph/Rook data survives cluster recreation cycles.

**Acceptance Criteria:**

**Given** a dev cluster with Rook-Ceph storage and deployed workloads
**When** the cluster is shut down and recreated via `startup.dev.py`
**Then** the persistent QEMU disk images are preserved
**And** Rook-Ceph storage is reinitialized from the preserved disks
**And** previously deployed workloads can access their persistent data
**And** the recreation completes without manual intervention

**Given** the persistent disk images are corrupted or missing
**When** the cluster is recreated
**Then** fresh disks are created and Rook-Ceph initializes from scratch
**And** the script logs the fresh initialization

**Implementation notes:** `bootstrap_talos_dev.py:create_disk_image` already skips existing disks. The idempotency is: stop -> preserve disks -> recreate VMs -> Rook-Ceph reattaches. Requires Rook-Ceph operator to handle disk reattachment gracefully.

---

**Epic 11 Story 11.3: Live Component Initialization**

As a Platform Engineer,
I want the full 44-step component initialization to run against a live cluster,
So that all platform components are verified working end-to-end.

**Acceptance Criteria:**

**Given** a freshly provisioned Talos/QEMU cluster
**When** `startup.dev.py --offline --apply` runs all 44 steps
**Then** each step completes successfully or fails with a clear error
**And** the `output/startup.dev.log` records the outcome of every step
**And** the script exits with a non-zero status on any step failure
**And** the cluster is accessible via `kubectl` after all steps complete

**Given** a step fails during initialization
**When** the failure is investigated and fixed
**Then** the step can be re-run individually via `--step` flag
**And** the remaining steps continue from where they left off

**Implementation notes:** The 44 steps in `scripts/steps/` are already ordered. The `--apply` flag passes `--apply` to each step. The investigation/fix loop uses the `investigate` discipline per failure. Each step should be run individually after a fix to confirm the fix works before re-running the full chain.

---

**Epic 11 Story 11.4: Live-Cluster Verification**

As a Quality Engineer,
I want the P0 ATDD suite and live-cluster register entries verified against the live cluster,
So that all quantified acceptance criteria are proven working.

**Acceptance Criteria:**

**Given** the dev cluster is fully initialized (all 44 steps complete)
**When** the P0 ATDD suite runs with `HPDC_EDGE_URL` and `HPDC_EVENTS_API_KEY` set
**Then** the 7 previously-skipped RED-phase tests pass or fail with clear diagnostics
**And** REG-01 through REG-10 are verified and closed in `live-cluster-verification-register.md`
**And** `deferred-work.md` entries resolved by live verification are marked resolved
**And** `sprint-status.yaml` is updated to reflect the new epic and closed action items

**Given** a REG entry fails verification
**When** the failure is investigated and fixed
**Then** the entry is re-verified and closed
**And** the fix is committed with a reference to the REG entry

**Implementation notes:** The P0 ATDD suite (143 passed, 7 skipped) runs with pytest. The 7 skips are RED-phase live journeys gated on B-001. Harnesses auto-switch to live backends via `HPDC_*` env vars. REG-01..10 entries are in `live-cluster-verification-register.md`. Each entry has owner (Winston/Amelia/Murat), quantified ACs, and P0 class.

## Section 5: Implementation Handoff

**Scope classification:** Moderate — new epic + 4 stories, backlog reorganization needed.

**Handoff recipients:**
- **Amelia (Dev Agent):** Stories 11.1 and 11.2 — VM lifecycle and idempotent startup implementation
- **Murat (TEA):** Stories 11.3 and 11.4 — live component init verification and P0 ATDD live run
- **Winston (Architect):** Oversight on Rook-Ceph persistent storage behavior during recreate cycles

**Responsibilities:**
- Amelia: Implement `stop.dev.py` extension for Talos/QEMU, modify `startup.dev.py` for idempotent lifecycle, modify `bootstrap_talos_dev.py` for persistent storage preservation
- Murat: Run the 44-step chain, investigate failures, run P0 ATDD suite live, close REG-01..10
- Winston: Review Rook-Ceph reattachment behavior, confirm persistent storage survives cycle

**Success criteria:**
- `startup.dev.py --offline --apply` runs end-to-end with idempotent lifecycle
- `stop.dev.py` handles Talos/QEMU teardown
- P0 ATDD suite passes live (143+ passed, 0 skipped)
- REG-01..10 all closed
- `sprint-status.yaml` updated with Epic 11

**Next steps after approval:**
1. Update `epics.md` with Epic 11 section
2. Update `sprint-status.yaml` with new epic and stories
3. Begin Story 11.1 implementation (Amelia)
