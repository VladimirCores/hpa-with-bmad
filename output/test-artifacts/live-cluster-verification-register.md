---
registerType: 'live-cluster-verification'
project: 'High Performance Distributed Cluster (HPDC)'
scope: 'P0-008 / P0-023-class verification items that require a live platform, harness, or multi-region topology'
created: '2026-08-11'
source:
  - 'output/implementation-artifacts/action-items-2026-08-11.md (items 3, 4, 8, 10, 12; theme 2)'
  - 'output/test-artifacts/test-design/test-design-qa.md (B-001..B-005 blockers, P0-008, P0-023)'
  - 'output/test-artifacts/atdd-progress.md (remaining RED scaffolds)'
status: 'registered-open'
---

# Live-Cluster Verification Register

**Purpose:** Single register for every quantified HPDC acceptance criterion that
cannot be proven offline. Each entry records the requirement, its quantified ACs,
the owner, the blocker(s) that gate it, and the P0 class it will verify under.
Entries are config- or manifest-verified today (where possible); the live proof is
deferred until the corresponding blocker is resolved.

The 5 live-cluster P0-008/P0-023-class items registered in the epic retrospective
sweep (action items 3, 4, 8, 10, 12) are materialized here.

## Blocker Reference (from test-design-qa.md)

| Blocker | Requirement | Owner | Gates |
|---------|-------------|-------|-------|
| B-001 | Live test cluster (`admin@hpa-dev`) | Platform Eng | All E2E + route-auth integration |
| B-002 | Identity fixtures (Casdoor 7 roles, JWT, API-Key) | Security/Backend | AuthN/AuthZ |
| B-003 | Pulsar/Kafka consumer harness | Backend | Message-arrival assertions (FR-1..4, FR-9) |
| B-004 | Multi-region topology (2 clusters + ClusterMesh + WireGuard) | Platform Eng | Epic 8 (FR-33..35, NFR20) |
| B-005 | k6 load harness | QA + Platform Eng | Performance evidence (NFR1/4/9/10/16) |

## Register

| # | Epic | Requirement / Verification | Quantified ACs | Owner | Blocker(s) | P0 Class | Status |
|---|------|---------------------------|----------------|-------|------------|----------|--------|
| REG-01 | 10 | Deploy Infisical operator + `credentialsRef` so `hpdc-production-secrets` reconciles (R-008) | `InfisicalSecret hpdc-production-secrets` reaches `synced` with managed secret references materialized; no high-entropy secrets in git | Winston | B-001 | P0-022 | open |
| REG-02 | 10 | JWT `audiences`/`forwardJWT` + live JWKS fetch (R-001, FR-38) | Gateway forwardJWT audience `hpdc-graphql-gateway`; live fetch of `casdoor.hpdc.local/.well-known/jwks.json` returns valid JWKS and JWT validation succeeds | Amelia | B-001 | P0-008 | open |
| REG-03 | 8 | ClusterMesh tunnel live: cross-cluster WireGuard discovery/encryption (FR-33..35, NFR20) | Two regions discover each other over encrypted WireGuard; regional store shows NO default cross-region replication; hub reads region-scoped aggregate without storing regional data | Winston | B-001, B-004 | P0-008 | open |
| REG-04 | 7 | Log-search SLO (FR-18/21 class) | Log search ≤5s | Murat | B-001 | P0-008/P0-023 | open |
| REG-05 | 7 | Stale-metric SLO (FR-18/21 class) | Stale-metric detection ≤5min | Murat | B-001 | P0-008/P0-023 | open |
| REG-06 | 7 | PromQL range SLO | PromQL 24h-range query ≤2s | Murat | B-001 | P0-008/P0-023 | open |
| REG-07 | 6 | Entity-store mutation SLO (FR-14) | Entity CRUD round-trip p99 ≤200ms | Murat | B-001 | P0-008/P0-023 | open |
| REG-08 | 6 | Change-reaction SLO (FR-15/16) | Knative/Restate change feed reaction ≤500ms | Murat | B-001 | P0-008/P0-023 | open |
| REG-09 | 6 | Exactly-once Restate (FR-15/16, R-018) | Duplicate delivery → single processing, exactly-once via Restate, DLQ routing | Murat | B-001 | P0-008/P0-023 | open |
| REG-10 | 6 | Hasura cross-store join SLO (FR-37) | Cross-store join (CouchDB+ArcadeDB+YugabyteDB) ≤2s | Murat | B-001 | P0-008/P0-023 | open |

## Related RED Scaffolds (already deferred in the ATDD suite)

These scaffolds assert the same contracts in RED PHASE and unlock once the same
blockers resolve. They are the executable form of the register entries above.

| Scaffold | Body count | Blockers | Notes |
|----------|-----------|----------|-------|
| `tests/atdd/e2e/test_p0_alert_pipeline_journey.py` | 4 live bodies (+1 manifest-contract body, already green) | B-001, B-003 | P0-008 ingest → decision → dispatch → ClickHouse (REG-02 subclass) |
| `tests/atdd/api/test_p0_performance.py::test_p0_023_soak` | 1 | B-005 | 24h 100K RPS sustained, 99.9% delivered (REG-04..10 subclass) |
| `tests/atdd/e2e/test_p0_ui_journeys.py` | 2 | B-002 | P0-025/026 UI journeys, deferred until UI + identity fixtures exist |

## Unlock Path (dependency order)

1. **B-002 identity fixtures** — **BUILT (2026-08-11):** `api_key_fixture` +
   `jwt_fixture` (real RS256, Casdoor claims) + `jwks_fixture` + `verify_jwt` +
   `CASDOOR_USERS` (7 role->group catalog) in `tests/atdd/support/fixtures.py`,
   with 12 offline tests (`tests/atdd/support/test_identity_fixtures.py`, incl.
   manifest-parity guard). Unlocks UI journeys and identity-relevant live probes.
2. **B-003 consumer harness** — `pulsar_consumer_harness` contract is defined
   (message-arrival + latency assert). Buildable once message brokers exist in a cluster.
3. **B-001 live cluster** — unlocks REG-01/02/04..10 and the P0-008 journey bodies.
4. **B-004 multi-region topology** — unlocks REG-03 (ClusterMesh/WireGuard).
5. **B-005 k6 load harness** — unlocks the P0-023 soak.

## Verification Ownership

- **Winston:** REG-01 (Infisical operator), REG-03 (ClusterMesh tunnel)
- **Amelia:** REG-02 (JWT audiences/forwardJWT + JWKS)
- **Murat:** REG-04..REG-10 (SLOs: observability + entity-store)

## Update Log

- 2026-08-11: Register created from retro-sweep action items 3, 4, 8, 10, 12
  (output/implementation-artifacts/action-items-2026-08-11.md) and the deferred
  RED scaffolds tracked in atdd-progress.md. All entries `open`, gated by B-001..B-005.
- 2026-08-11: B-002 identity fixtures built — `api_key_fixture`, `jwt_fixture`,
  `jwks_fixture`, `verify_jwt`, `CASDOOR_USERS` in
  `tests/atdd/support/fixtures.py` + 12 offline tests
  (`tests/atdd/support/test_identity_fixtures.py`). Unlock-path step 1 done;
  REG-02 (JWKS) groundwork in place.
