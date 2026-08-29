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

| Blocker | Requirement | Owner | Gates | Status |
|---------|-------------|-------|-------|--------|
| B-001 | Live test cluster (`admin@hpa-dev`) | Platform Eng | All E2E + route-auth integration | open |
| B-002 | Identity fixtures (Casdoor 7 roles, JWT, API-Key) | Security/Backend | AuthN/AuthZ | ✅ BUILT 2026-08-11 |
| B-003 | Pulsar/Kafka consumer harness | Backend | Message-arrival assertions (FR-1..4, FR-9) | ✅ BUILT 2026-08-11 (offline contract) |
| B-004 | Multi-region topology (2 clusters + ClusterMesh + WireGuard) | Platform Eng | Epic 8 (FR-33..35, NFR20) | open |
| B-005 | k6 load harness | QA + Platform Eng | Performance evidence (NFR1/4/9/10/16) | ✅ BUILT 2026-08-11 (offline contract) |

## Register

| # | Epic | Requirement / Verification | Quantified ACs | Owner | Blocker(s) | P0 Class | Status |
|---|------|---------------------------|----------------|-------|------------|----------|--------|
| REG-01 | 10 | Deploy Infisical operator + `credentialsRef` so `hpdc-production-secrets` reconciles (R-008) | `InfisicalSecret hpdc-production-secrets` reaches `synced` with managed secret references materialized; no high-entropy secrets in git | Winston | B-001 | P0-022 | blocked |
| REG-02 | 10 | JWT `audiences`/`forwardJWT` + live JWKS fetch (R-001, FR-38) | Gateway forwardJWT audience `hpdc-graphql-gateway`; live fetch of `casdoor.hpdc.local/.well-known/jwks.json` returns valid JWKS and JWT validation succeeds | Amelia | B-001 | P0-008 | blocked |
| REG-03 | 8 | ClusterMesh tunnel live: cross-cluster WireGuard discovery/encryption (FR-33..35, NFR20) | Two regions discover each other over encrypted WireGuard; regional store shows NO default cross-region replication; hub reads region-scoped aggregate without storing regional data | Winston | B-001, B-004 | P0-008 | blocked |
| REG-04 | 7 | Log-search SLO (FR-18/21 class) | Log search ≤5s | Murat | B-001 | P0-008/P0-023 | blocked |
| REG-05 | 7 | Stale-metric SLO (FR-18/21 class) | Stale-metric detection ≤5min | Murat | B-001 | P0-008/P0-023 | blocked |
| REG-06 | 7 | PromQL range SLO | PromQL 24h-range query ≤2s | Murat | B-001 | P0-008/P0-023 | ✅ verified 2026-08-29 |
| REG-07 | 6 | Entity-store mutation SLO (FR-14) | Entity CRUD round-trip p99 ≤200ms | Murat | B-001 | P0-008/P0-023 | ✅ verified 2026-08-29 |
| REG-08 | 6 | Change-reaction SLO (FR-15/16) | Knative/Restate change feed reaction ≤500ms | Murat | B-001 | P0-008/P0-023 | blocked |
| REG-09 | 6 | Exactly-once Restate (FR-15/16, R-018) | Duplicate delivery → single processing, exactly-once via Restate, DLQ routing | Murat | B-001 | P0-008/P0-023 | blocked |
| REG-10 | 6 | Hasura cross-store join SLO (FR-37) | Cross-store join (CouchDB+ArcadeDB+YugabyteDB) ≤2s | Murat | B-001 | P0-008/P0-023 | blocked |

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
2. **B-003 consumer harness** — **BUILT (2026-08-11, offline contract):**
   `pulsar_consumer_harness()` / `kafka_consumer_harness()` factories +
   `PulsarConsumerHarness`/`KafkaConsumerHarness` in
   `tests/atdd/support/consumer_harness.py`. Message-arrival (`assert_arrival`)
   + arrival-within-latency budget (`assert_arrival_within_latency`) assertions;
   remote HTTP backend (`HPDC_CONSUMER_HARNESS_URL` /
   `HPDC_KAFKA_CONSUMER_HARNESS_URL`, `GET /consume/{topic}?key=`) for a live
   cluster + local NDJSON topic-store backend for offline dev. 12 offline
   contract tests (`tests/atdd/support/test_consumer_harness.py`). REG entries
   using it (REG-04..10 style arrival/latency asserts) go live once B-001 exists.
3. **B-001 live cluster** — unlocks REG-01/02/04..10 and the P0-008 journey bodies.
4. **B-004 multi-region topology** — unlocks REG-03 (ClusterMesh/WireGuard).
5. **B-005 k6 load harness** — **BUILT (2026-08-11, offline contract):**
   `LoadHarness` + `SoakReport` in `hpdc_test_client.py` (the exact import +
   call shape `test_p0_performance.py` uses). Runs a k6 soak script
   (constant-arrival-rate, thresholds `http_req_failed rate<0.001` +
   `http_req_duration p(99)<100`) against a live gateway when the k6 binary is
   present; falls back to a bounded local simulation against the dev edge
   service when k6 is absent. 7 offline contract tests
   (`tests/atdd/support/test_load_harness.py`). The 24h/100K RPS soak itself
   still needs k6 + live cluster (P0-023).

## Verification Ownership

- **Winston:** REG-01 (Infisical operator), REG-03 (ClusterMesh tunnel)
- **Amelia:** REG-02 (JWT audiences/forwardJWT + JWKS)
- **Murat:** REG-04..REG-10 (SLOs: observability + entity-store)

## Live-Cluster Evidence 2026-08-29 (story 11-4 Task 3)

Run against the kind cluster (hpdc-talos-*, kindnet CNI) after Pulsar milestone
convergence. Gateway reachable via NodePort `443:30235` on `172.18.0.2`
(`edge.hpdc.local`; SAN `.hpdc.local`). No MetalLB → LB services stay `<pending>`.

- **REG-06 ✅** — PromQL 24h-range `up` query on `vmselect` (svc `vmselect`, port
  forward 8481): 5 runs all success in **≤0.01s** (SLO 2s); 14 series returned;
  cadence 15s. Infra: vmagent/vminsert/vmselect/vmstorage all `Running` 1/1.
- **REG-07 ✅** — live CouchDB CRUD round-trip against
  `couchdb-entity-store.entity-store.svc` (`/entities/reg07-probe`):
  create **7.6ms**, read **2.0ms**, update **0.5ms** (SLO p99 200ms). CouchDB
  is the only entity-store member deployed; ArcadeDB/YugabyteDB not deployed.
- **REG-01 ⛔ blocked** — no Infisical operator/CRD pods in cluster; gitops
  `infisical` base not applied. `hpdc-production-secrets` InfisicalSecret cannot
  reconcile. `DEV_ONLY_CREDENTIALS` allowlist is the interim posture (R-008).
- **REG-02 ⛔ blocked** — `casdoor-7bf7c5974f-jcpfm` ImagePullBackOff (image not
  in offline mirror), `casbin-abac-ext-authz` ImagePullBackOff. JWKS endpoint
  `casdoor.hpdc.local/.well-known/jwks.json` → 503 (no ready pod). JWT
  SecurityPolicy `hpdc-graphql-gateway-jwt-authn` is manifest-verified but
  cannot validate live.
- **REG-03 ⛔ blocked** — B-004 unresolved: single kind cluster, no ClusterMesh /
  WireGuard / second region exists to verify FR-33..35.
- **REG-04 ⛔ blocked** — `vmlogs` defined in gitops
  (`gitops/victoria-metrics/base/vmlogs.yaml`) but no vmlogs pod/deployment in
  cluster; no log-search backend to time.
- **REG-05 ⛔ blocked** — stale-metric SLO requires the telemetry ingest path +
  alerting; vmagent scrapes live (VM 4 pods + argocd + couchdb targets, E2E
  cadence observed) but the `/telemetry`→`pulsar-telemetry-ingestion` route has
  **no endpoints** (Service selector-less) and no vmalert exists to prove
  ≤5min staleness detection end-to-end.
- **REG-08 / REG-09 ⛔ blocked** — no Knative / Restate / change-feed workloads
  in cluster (PG inbox or reaction consumer absent); cannot measure FR-15/16.
- **REG-10 ⛔ blocked** — no Hasura deployment in cluster; cross-store join SLO
  unmeasurable until Hasura + ArcadeDB/YugabyteDB join.

Summary: **2 verified (REG-06, REG-07), 8 blocked** — all 8 blocked entries carry
a concrete missing-component evidence tuple; none are silently "passing".

## Update Log

- 2026-08-11: Register created from retro-sweep action items 3, 4, 8, 10, 12
  (output/implementation-artifacts/action-items-2026-08-11.md) and the deferred
  RED scaffolds tracked in atdd-progress.md. All entries `open`, gated by B-001..B-005.
- 2026-08-11: B-002 identity fixtures built — `api_key_fixture`, `jwt_fixture`,
  `jwks_fixture`, `verify_jwt`, `CASDOOR_USERS` in
  `tests/atdd/support/fixtures.py` + 12 offline tests
  (`tests/atdd/support/test_identity_fixtures.py`). Unlock-path step 1 done;
  REG-02 (JWKS) groundwork in place.
- 2026-08-11: B-003 consumer harness built (offline contract) —
  `tests/atdd/support/consumer_harness.py` (`pulsar_consumer_harness`,
  `kafka_consumer_harness`, message-arrival + latency assertions, remote HTTP
  + local NDJSON backends) + 12 offline tests
  (`tests/atdd/support/test_consumer_harness.py`). Unlock-path step 2 done.
- 2026-08-11: B-005 k6 load harness built (offline contract) — `LoadHarness` +
  `SoakReport` in `hpdc_test_client.py` (k6 soak script with NFR1/NFR3
  thresholds + bounded local simulation fallback) + 7 offline tests
  (`tests/atdd/support/test_load_harness.py`). Unlock-path step 5 done;
  P0-023 soak itself still gated on k6 + live cluster. Suite now 143 passed /
  7 skipped.
- 2026-08-29: **Task 3 verification pass (story 11-4).** REG-06 + REG-07 verified
  with live measurements (≤0.01s PromQL range; 0.5–7.6ms CouchDB CRUD). REG-01,
  REG-02, REG-04, REG-05, REG-08, REG-09, REG-10 marked **blocked** with
  missing-component evidence (no Infisical operator; casdoor/casbin
  ImagePullBackOff; no vmlogs pod; telemetry ingestion selector-less/not
  deployed; no Restate/Knative; no Hasura). REG-03 remains blocked on B-004
  (no second region). Live-cluster evidence section added above.
