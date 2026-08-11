# Consolidated Action Items — Epic Retrospective Sweep (10→1)

- **Date:** 2026-08-11
- **Scope:** Epics 10, 9, 8, 7, 6, 5, 4, 3, 2, 1
- **Retro docs:** `output/implementation-artifacts/epic-{1..10}-retro-2026-08-11.md`
- **Total action items:** 23 (5 Epic 10; 2 each Epics 9–1)
- **Cross-cutting themes:** record reconciliation (Epics 5/4/3/1), live-cluster verification register (Epics 10/8/7/6), parity guards for shared config (Epics 10/3/2), route-topology/native-auth consolidation (Epics 10/7/3), heading normalization Epics 1–4 (Epic 4, broadened)

## Action Item Table

| # | Epic | Action | Owner | Status |
|---|------|--------|-------|--------|
| 1 | 10 | Resolve native-auth UI `'/'` catch-all ambiguity: drop `'/'` from one UI route or give every UI host a dedicated hostname route | Amelia | open |
| 2 | 10 | Extend secret-scan `_base_yamls()` to also scan overlay kustomizations (P0-022 base-only gap) | Murat | open |
| 3 | 10 | Deploy Infisical operator + credentialsRef so hpdc-production-secrets reconciles (needs live cluster) | Winston | open |
| 4 | 10 | Add JWT audiences/forwardJWT + live JWKS fetch verification (P0-008, needs live cluster) | Amelia | open |
| 5 | 10 | Codify in-memory mutation-probe technique into the checkpoint-review workflow (every dig-in includes a mutation probe) | Amelia + Murat | open |
| 6 | 9 | Clarify story 9-3 status in epics.md: mark provide-full-llm-decision-support-engine explicitly as deferred/not-implemented | John | open |
| 7 | 9 | Record agent-engine parity guard: apply kustomize-to-installer parity-guard agreement to any agent-engine shared config | Winston | open |
| 8 | 8 | Verify ClusterMesh tunnel live: cross-cluster WireGuard discovery/encryption needs P0-008 live-cluster verification (record once a multi-region cluster exists) | Winston | open |
| 9 | 8 | Add a no-replication guard: regional-sovereignty validation asserts no cross-region replication config exists in the tree (absence-of-config invariant) | Murat | open |
| 10 | 7 | Register SLO verification tasks: live-cluster verification for quantified ACs (log search ≤5s, stale-metric ≤5min, PromQL ≤2s) as P0-008/P0-023-class items | Murat | open |
| 11 | 7 | Audit the native-auth tool-route group: UI route topology from 7-5 is root of Epic 10 catch-all ambiguity; fold into Epic 10 action item 1 topology review | Winston | open |
| 12 | 6 | Register entity-store SLO verifications: 200ms p99 mutation, 500ms change reaction, exactly-once Restate, Hasura 2s cross-store join (live-cluster P0-008/P0-023 register) | Murat | open |
| 13 | 6 | Audit /gql route ownership: confirm entity-store-owns-/gql contract documented in the route-topology review (Epic 10 shadowing fix subject) | Winston | open |
| 14 | 5 | Reconcile the 5-2 story record: 5-2 marked done in sprint-status but no story file exists; backfill a minimal record or document the gap | John | open |
| 15 | 5 | Carry the safety-gate pattern forward: sensitive-action approval gate from 5-3/5-5 as a stated requirement for deferred LLM engine 9-3 | Amelia | open |
| 16 | 4 | Reconcile Epic 4 story records: 4-3..4-9 no story files (delivered via consolidated scaffold, epic4→platform rename); 4-2 unchecked tasks despite implementation; fix stale paths in epic-4-offline-gitops-scaffold.md and clear 4-2 task checklist | John | open |
| 17 | 4 | Normalize Epic 1-4 headings in epics.md from `###` (h3, under `## Epic List`) to `##` (h2), matching Epics 5-10, so machine-driven discovery and retro sweeps find them (originally Epic 4 only; broadened per Epic 3 retro) | Winston | open |
| 18 | 3 | Reconcile the 3-13 record: 3-13 (Grafana/Hubble UI via Envoy Gateway) done but missing from epics.md and sprint-status, and self-contradictory (Status: done + deferred until Epic 7); decide add-to-tracker or mark deferred and resolve native-auth-vs-Casdoor ambiguity for observability routes | John | open |
| 19 | 3 | Route-topology lineage: the native tool-auth route pattern from 3-12/3-13 (`casdoor_casbin_ext_authz: false`) is the root family of the Epic 10 `'/'` catch-all; fold into Epic 10 action item 1 topology review | Winston | open |
| 20 | 2 | Deepen the shallow story records: 2-1, 2-3..2-10 are 21-23 line records without Dev Agent Records, review findings, or baseline commits (only 2-2 has all three); backfill baseline commits and add review-findings depth for 2-4/2-6/2-7/2-8 | John | open |
| 21 | 2 | Document the harbor parsed-equality drift guard (10-2, kustomize tree vs install_harbor_dev.py) as the canonical cross-system parity-guard template, owned at its Epic 2 origin | Winston | open |
| 22 | 1 | Reconcile story 1-6 in the plan: 1-6 (Harbor OCI registry) delivered, tracked, reused by 2-1, but absent from epics.md's Epic 1 story list (ends at 1.5); add Story 1.6 or document it as an unplanned delivery Epic 2 reuses without forking | John | open |
| 23 | 1 | Pin Epic 1 records to delivery commits: no baseline commits recorded on 1-1..1-6 despite full-depth records; backfill so the substrate audit trail is verifiable | John | open |

## Owner Load

| Owner | Items |
|-------|-------|
| John | 7 (#6, 14, 16, 18, 20, 22, 23) |
| Winston | 7 (#3, 7, 8, 13, 17, 19, 21) |
| Murat | 4 (#2, 9, 10, 12) |
| Amelia | 4 (#1, 4, 15) + #5 with Murat |
| Amelia + Murat | 1 (#5) |

## Cross-Cutting Themes

1. **Record reconciliation (John)** — Epics 5 (5-2), 4 (4-3..4-9), 3 (3-13), 1 (1-6): the audit trail has drifted in both directions (missing records, untracked implementations, plan/tracker mismatches). Items 14, 16, 18, 22.
2. **Live-cluster verification register (Murat/Winston)** — Epics 10 (JWKS/P0-008), 8 (ClusterMesh), 7 (SLOs), 6 (entity-store SLOs): quantified ACs are config-only until a cluster exists. Materialized as `output/test-artifacts/live-cluster-verification-register.md` (REG-01..REG-10 + unlock path + related RED scaffolds). Items 3, 4, 8, 10, 12.
3. **Parity guards for shared config (Winston)** — Epics 10 (harbor drift guard), 9 (agent-engine), 3 (tool routes), 2 (harbor template): one fact, two representations → enforce equality. Items 3, 7, 19, 21.
4. **Route-topology / native-auth consolidation (Winston/Amelia)** — Epics 10 (`'/'` catch-all), 7 (7-5 tool routes), 3 (3-12/3-13): the native tool-auth pattern is one family; needs one topology rule. Items 1, 11, 19.
5. **Heading normalization Epics 1–4 (Winston)** — h3 under `## Epic List` vs h2 for Epics 5–10; breaks machine discovery. Item 17.

## Sweep Summary

- **Retrospectives:** 10/10 complete (`epic-{1..10}-retrospective: done` in sprint-status.yaml)
- **Story completeness:** Epic 2 10/10 files+tracker+plan; Epic 1 6/6 files+tracker but 5/6 plan; Epic 3 13/13 files but 12/12 tracked (3-13 untracked); Epics 4/5/9 have missing-file or deferred gaps; Epics 6/7/8 clean on paper
- **Deferred-work ledger:** still open from pre-sweep (native-auth annotation, InfisicalSecret reconciliation, JWT audiences/forwardJWT, secret-scan base-only gap, P0-008 live-cluster items)
