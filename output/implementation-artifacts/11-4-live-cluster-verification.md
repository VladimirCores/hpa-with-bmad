---
story_key: 11-4-live-cluster-verification
epic: 11
status: in-progress
baseline_commit: a72685e81f083c0032921f1c1a8ec69daedb3af5
completion_commit: TBD
---

# Story 11.4: Live-Cluster Verification

## Story

As a Quality Engineer,
I want the P0 ATDD suite and live-cluster register entries verified against the live cluster,
So that all quantified acceptance criteria are proven working.

## Acceptance Criteria

**Given** platform convergence is complete (story 11-5: all App-of-Apps children Synced & Healthy)
**When** the P0 ATDD suite runs with `HPDC_EDGE_URL` and `HPDC_EVENTS_API_KEY` set
**Then** the 7 previously-skipped RED-phase tests pass or fail with clear diagnostics
**And** REG-01 through REG-10 are verified and closed in `live-cluster-verification-register.md`
**And** `deferred-work.md` entries resolved by live verification are marked resolved
**And** `sprint-status.yaml` is updated to reflect the new epic and closed action items

**Given** a REG entry fails verification
**When** the failure is investigated and fixed
**Then** the entry is re-verified and closed
**And** the fix is committed with a reference to the REG entry

## Tasks / Subtasks

**Prerequisite:** Story 11-5 (platform convergence via App-of-Apps) must be done first — verification targets a converged platform.

- [ ] Task 1: Set up live-cluster environment variables (AC: #1)
  - [ ] Discover gateway LB address (`kubectl get gateway -A`; Cilium L2 LB on docker net) and set `HPDC_EDGE_URL` accordingly — port-forward fallback
  - [ ] Verify `HPDC_EVENTS_API_KEY` is set with valid key from api-key-auth secret (step 18 resources / `security` overlay)
  - [ ] Confirm kubectl connectivity to cluster
- [ ] Task 2: Run P0 ATDD suite against live cluster (AC: #1, #2)
  - [ ] Run full pytest suite: `pytest tests/atdd/ -v --tb=long`
  - [ ] Identify the 7 previously-skipped RED-phase tests
  - [ ] Verify each skip is now either PASS or provides clear diagnostics
  - [ ] Record results in atdd-progress.md
- [ ] Task 3: Close REG-01 through REG-10 (AC: #2)
  - [ ] REG-01: Verify Infisical operator deployed and `hpdc-production-secrets` syncs
  - [ ] REG-02: Verify JWT audiences/forwardJWT and live JWKS fetch
  - [ ] REG-03: Verify ClusterMesh tunnel (if multi-region available; otherwise document B-004 blocker)
  - [ ] REG-04: Verify log-search SLO (≤5s)
  - [ ] REG-05: Verify stale-metric SLO (≤5min)
  - [ ] REG-06: Verify PromQL range SLO (≤2s for 24h)
  - [ ] REG-07: Verify entity-store mutation SLO (p99 ≤200ms)
  - [ ] REG-08: Verify change-reaction SLO (≤500ms)
  - [ ] REG-09: Verify exactly-once Restate processing
  - [ ] REG-10: Verify Hasura cross-store join SLO (≤2s)
- [ ] Task 4: Update deferred-work.md (AC: #3)
  - [ ] Mark entries resolved by live verification as resolved
  - [ ] Add resolution notes with commit references
- [ ] Task 5: Update sprint-status.yaml (AC: #4)
  - [ ] Mark story 11-4 as done
  - [ ] Mark Epic 11 as done
  - [ ] Update linked action items to done
- [ ] Task 6: Close blocked action items from sprint-status.yaml
  - [ ] Epic 10: Deploy Infisical operator + credentialsRef (Winston)
  - [ ] Epic 10: Add JWT audiences/forwardJWT + live JWKS verification (Amelia)
  - [ ] Epic 8: Verify ClusterMesh tunnel live (Winston)
  - [ ] Epic 7: Register SLO verification tasks (Murat)
  - [ ] Epic 6: Register entity-store SLO verifications (Murat)

## Dev Notes

### Cluster State (refreshed 2026-08-24)

Cluster `hpdc-talos` (docker provisioner): **4/4 nodes Ready**, k8s v1.35.2, Cilium KPR, fully OFFLINE-initialized via local registry mirror (`skipFallback` proven).
- Deployment paradigm: **App-of-Apps via ArgoCD from local git mirror** (`gitops/app-of-apps/root-application.yaml` + 19 wave-ordered children) — NOT bespoke installer steps. Steps remain as waiters/validators.
- Pods at last check: 44/57 Running; ~10 apps OutOfSync awaiting EG routes + 2 missing images. **Convergence is story 11-5, prerequisite to this story's Tasks 2–3.**
- Offline posture: all node pulls flow through `hpa-local-registry` (10.6.0.1:5000) only; cache-fill host-side via `skopeo copy --all`.
- Git mirror for ArgoCD: smart HTTP at `http://10.6.0.1:9418/with-bmad.git` (rerun step 09 after reboot; idempotent).

### Gateway Configuration

- Gateway LB address: discover dynamically via `kubectl get gateway -A` (Cilium L2 LoadBalancer on the docker network); port-forward fallback for host access.
- Routes exposed by App-of-Apps children (wave-ordered): harbor, argocd, tool-ui, observability, security, plus component routes.

### Blocker Status

| Blocker | Requirement | Status |
|---------|-------------|--------|
| B-001 | Live test cluster | **RESOLVED** (cluster running) |
| B-002 | Identity fixtures | BUILT (2026-08-11) |
| B-003 | Consumer harness | BUILT (2026-08-11) |
| B-004 | Multi-region topology | **OPEN** (single cluster only) |
| B-005 | k6 load harness | BUILT (2026-08-11) |

**Impact**: B-004 being open means REG-03 (ClusterMesh tunnel) cannot be fully verified. Document as blocked by B-004.

### REG Entry Ownership

| REG | Owner | Verification Method |
|-----|-------|---------------------|
| REG-01 | Winston | Infisical operator status + InfisicalSecret CRD sync |
| REG-02 | Amelia | JWT validation + JWKS endpoint probe |
| REG-03 | Winston | ClusterMesh status (blocked by B-004) |
| REG-04 | Murat | Log search latency measurement |
| REG-05 | Murat | Stale-metric detection timing |
| REG-06 | Murat | PromQL query performance |
| REG-07 | Murat | Entity CRUD latency measurement |
| REG-08 | Murat | Change-feed reaction timing |
| REG-09 | Murat | Duplicate delivery test + Restate verification |
| REG-10 | Murat | Hasura cross-store join performance |

### Test Suite Context

- **Current state**: 143 passed, 7 skipped (RED-phase live journeys)
- **7 skips**: Gated on B-001 (live cluster), now resolved
- **Test location**: `tests/atdd/` (api/ and e2e/ subdirectories)
- **Env vars**: `HPDC_EDGE_URL`, `HPDC_EVENTS_API_KEY` for live mode

### Previous Story Intelligence (from 11-3)

- All8 core components installed and verified running
- Gateway at172.18.255.200 PROGRAMMED=True
- HTTPRoutes for Harbor and ArgoCD in place
- Cilium L2 LoadBalancer configured
- Deferred items (External Secrets Operator, Uptime Kuma, Metrics Server, Sealed Secrets, Grafana dashboards) are explicitly scoped out

### References

- `output/implementation-artifacts/11-5-platform-convergence-app-of-apps.md` — prerequisite story (convergence)
- `output/implementation-artifacts/11-6-tighten-hpdc-crd-schemas.md` — follow-up (runs after this story)
- `output/test-artifacts/live-cluster-verification-register.md` — REG-01..10 entries
- `output/implementation-artifacts/deferred-work.md` — deferred items to close
- `output/implementation-artifacts/sprint-status.yaml` — story/epic status tracking
- `output/test-artifacts/atdd-progress.md` — ATDD workflow progress
- `tests/atdd/` — P0 ATDD test suite

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
