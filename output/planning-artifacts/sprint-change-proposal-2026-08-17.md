# Sprint Change Proposal — 2026-08-17

## Section 1: Issue Summary

**Trigger:** End-of-sprint retro (2026-08-11) surfaced 23 open action items across the retrospective sweep. Sprint Status (2026-08-11) confirmed all 10 epics delivered (59/59 stories) but exposed governance drift: story records missing or shallow, tracker inconsistencies, and hardening gaps that were identified but never codified as guards.

**Problem statement:** The delivered cluster (HPDC, 10 epics) has complete implementation but incomplete *governance* — story records do not consistently pin baseline commits, the sprint tracker mislabels delivered work, two test guards (secret-scan base-only, no cross-region replication) were identified but never written, and the native-auth route topology ambiguity recorded in the deferred-work ledger was never resolved.

**Evidence:**
- Story 9.3 marked done in tracker but is intentionally deferred (Epic 9 = v2-deferred).
- Story 3.13 self-contradictory: `Status: done` + "deferred until Epic 7".
- Stories 4-3..4-9 no story files (delivered via consolidated scaffold).
- Story 5-2 done in tracker but no story file exists.
- Story 1-6 delivered and reused by 2-1 but absent from epics.md.
- Epics 1-4 headings h3 under `## Epic List`; Epics 5-10 h2 — machine discovery inconsistent.
- Two native-auth UI routes (`hpdc-edge-observability-ui-routes`, `hpdc-edge-tool-ui-routes`) both carried a `*.hpdc.local` PathPrefix `/` catch-all — non-deterministic Envoy Gateway resolution (deferred-work ledger, 2026-08-08).
- Secret-scan test only walked base kustomizations; overlays were unscanned (P0-022 base-only gap).
- No guard asserted the absence of cross-region replication (FR-34).

## Section 2: Impact Analysis

- **Epic Impact:** Epics 1, 2, 3, 4 (records/headings), Epics 5, 6, 7, 8, 9 (record/tracker reconciliation), Epic 10 (route topology, secret-scan hardening).
- **Story Impact:** 1-6 (added), 2-1..2-10 (record depth), 3-13 (superseded), 4-2 (checklist cleared), 5-2 (record backfilled), 9-3 (marked deferred + safety-gate requirement).
- **Artifact Conflicts:** `epics.md`, `sprint-status.yaml`, `deferred-work.md`, story record files, checkpoint-preview skill, action-items ledger.
- **Technical Impact:** One route manifest edit (envoy-ui-routes.yaml), one test-invariant tightening (route-audit), one new test guard (FR-34), one test extension (secret-scan overlay coverage), two new doc artifacts (parity-guards.md, this proposal).

## Section 3: Recommended Approach

**Path: Direct Adjustment** — modify/add records and guards within the existing plan. No rollback, no scope reduction; the delivered functionality is correct, only governance and hardening lag.

**Rationale:** All ten epics are delivered. The action items are record reconciliation, tracker fixes, and codified hardening — not product changes. Direct Adjustment resolves 18/23 items offline; the remaining 5 are live-cluster verifications already registered (REG-01..REG-10) and blocked on infrastructure provisioning (B-001/B-004).

**Effort estimate:** ~2 hours (proposals already applied and verified). **Risk:** low — one manifest change (verified 9/9 route-audit pass) and additive test guards. **Timeline impact:** none — sprint already delivered; this is hardening close-out.

## Section 4: Detailed Change Proposals

### Group A — Record reconciliation (John)

- **A1** `epics.md` — added `### Story 1.6: Provision Local Harbor OCI Registry with Scanning and Signing` to Epic 1. *Before:* Epic 1 ended at 1.5. *After:* 1-6 tracked, matching delivered/reused work. (#22)
- **A2** `epics.md` — Story 9.3 header now `### Story 9.3: Provide Full LLM Decision-Support Engine — DEFERRED / NOT-IMPLEMENTED` + status note. (#6)
- **A3** `output/implementation-artifacts/3-13-expose-grafana-and-hubble-ui-via-envoy-gateway.md` — Status → `superseded — resolved 2026-08-11`; deferred-until-Epic-7 bullet → superseded by Story 7.5. (#18)
- **A4** `output/implementation-artifacts/5-2-persist-alert-state-machine-transitions.md` — backfilled full record. (#14)
- **A5** `output/implementation-artifacts/epic-4-offline-gitops-scaffold.md` — header → `# Epic 4 Consolidated Scaffold — Stories 4.3–4.10`. (#16)
- **A6** Epic 2 records 2-1, 2-3..2-10 — added `## Record Depth` (baseline commit + gap note). (#20)
- **A7** Epic 1 records 1-1..1-6 — added `## Record Depth` (baseline commit + gap note). (#23)
- **A8** `epics.md` Story 9.3 — added **Deferred requirements note**: safety-gate pattern from 5-3/5-5 is a *stated requirement* when 9-3 is implemented. (#15)

### Group B — Tracker fixes (Winston)

- **B1** `epics.md` — Epics 1-4 headings normalized `###` → `##` (matching Epics 5-10). (#17)
- **B2** `sprint-status.yaml` — `epic-10: in-progress` → `epic-10: done`.

### Group C — Hardening & guards (Murat / Winston / Amelia)

- **C1** `tests/atdd/e2e/test_p0_secret_scan.py` — added `_scanned_yamls()`: base + overlay kustomization resources, deduped, structural resolver. Verified: 7 secret scans declared; 7 executed; 0 failing. (#2)
- **C2** `tests/test_install_regional_sovereignty_dev.py` — added FR-34 no-replication guard (scans `gitops/**/*.yaml` for cross-region replication patterns). Verified: pass. (#9)
- **C3** `docs/parity-guards.md` — created canonical parsed-equality drift-guard template (Epic 2 origin). (#21)
- **C4** `docs/parity-guards.md` — agent-engine kustomize-to-installer parity agreement recorded. (#7)
- **C5** `gitops/observability/base/envoy-ui-routes.yaml` + `tests/atdd/e2e/test_p0_route_table_audit.py` — dropped redundant `/` catch-all from `hpdc-edge-observability-ui-routes` (grafana/hubble have dedicated hostname routes); tightened `test_no_route_shadowing` so two native-auth routes may share subpaths but never a wildcard `/`. Verified: 9 route-audit checks; 0 failing. (#1/#11/#19)
- **C6** `output/implementation-artifacts/deferred-work.md` — recorded `/gql` ownership contract (entity-store owns `/gql`, domain-routes must not path-match it) + native-auth lineage from 3-12/3-13 + `RESOLVED 2026-08-17` on the catch-all entry. (#13/#19)
- **C7** `.agents/skills/bmad-checkpoint-preview/step-03-detail-pass.md` — codified **mutation-probe** as step 5 of TARGETED RE-REVIEW ("every dig-in includes a mutation probe"). (#5)

### Group D — Live-cluster verifications (already registered, no offline change)

- **D1** #3 (Infisical operator), #4 (JWT), #8 (ClusterMesh), #10 (observability SLOs), #12 (entity-store SLOs) — all confirmed materialized in `output/test-artifacts/live-cluster-verification-register.md` (REG-01..REG-10). Blocked on B-001/B-004 (live infrastructure). Status stays `open` by design.

## Section 5: Implementation Handoff

**Scope: Minor** — direct implementation, already applied and verified in this session.

- **Applied by:** Developer agent (this session), per-proposal approval from Master.
- **Handoff recipients:** Owners recorded per item in `sprint-status.yaml` (John, Winston, Murat, Amelia) — record-keeping responsibility for the remaining live-cluster items transfers to the live-cluster verification run.
- **Success criteria:** 18/23 action items closed as `done`; 5 remaining `open` with explicit `blocked` context (B-001/B-004); all three verification suites green (secret-scan 7/7, route-audit 9/9, regional-sovereignty pass); record/heading reconciliation verified by re-run of retro sweeps.

**Carried forward (live-cluster blocked):** #3 (Infisical operator reconcile), #4 (JWT audiences/forwardJWT + live JWKS), #8 (ClusterMesh tunnel), #10 (SLO verification register), #12 (entity-store SLO register) — registered in `live-cluster-verification-register.md`.