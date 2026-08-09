---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-08-07'
workflowType: 'testarch-test-design'
inputDocuments:
  - output/planning-artifacts/prds/prd-HPDC-2026-07-21/prd.md
  - output/planning-artifacts/architecture/architecture-HPDC-2026-07-30/ARCHITECTURE-SPINE.md
  - output/planning-artifacts/architecture/architecture-HPDC-2026-07-30/ADR-LOG.md
  - output/planning-artifacts/epics.md
  - output/implementation-artifacts/sprint-status.yaml
  - tests/ (41 existing deployment-test files)
---

# Test Design for Architecture: HPDC Enterprise GitOps Platform

**Purpose:** Architectural concerns, testability gaps, and NFR requirements for review by Architecture/Dev teams. Serves as a contract between QA and Engineering on what must be addressed before test development begins.

**Date:** 2026-08-07
**Author:** Master
**Status:** Architecture Review Pending
**Project:** High Performance Distributed Cluster (HPDC)
**PRD Reference:** `output/planning-artifacts/prds/prd-HPDC-2026-07-21/prd.md`
**ADR Reference:** `output/planning-artifacts/architecture/architecture-HPDC-2026-07-30/ADR-LOG.md` (AD-1..AD-13) + `ARCHITECTURE-SPINE.md` (AD-1..AD-19)

---

## Executive Summary

**Scope:** System-level test design for the full HPDC platform: Gateway-Mediated Domain Segregation (Envoy Gateway → 5 domain routes), serverless-first compute (KNative+Restate, SpinKube WASM, Pulsar Functions), event-mesh integration fabric (Pulsar + Kafka), six-database data plane (CouchDB, YugabyteDB, ArcadeDB, ClickHouse, KeyDB, PostgreSQL), GitOps delivery (Kargo, Argo CD/Rollouts/Events/Workflows, Backstage), Talos + Cilium + Rook-Ceph substrate, observability (VictoriaMetrics, vmlog, OTel, Grafana, Hubble), air-gapped delivery (Harbor, Spegel, local Git mirror), multi-region federation (ClusterMesh, WireGuard, regional sovereignty), and AI Agent Engine (MCP, A2A).

**Business Context** (from PRD):

- **Problem:** Detect security alerts from high-RPS IoT telemetry in real time, respond within seconds, with data sovereignty per region and air-gapped GitOps delivery.
- **GA Launch:** Post-implementation verification — all 9 epics marked `done` in `output/implementation-artifacts/sprint-status.yaml` (2026-08-07). This design targets **verification of an existing deployment**, not pre-implementation guidance.
- **Primary Success Metrics (SM-1..SM-8):** 100K RPS p99<100ms; E2E-to-ClickHouse <2s; alert state initiated <500ms; env bootstrap <30min; entity CRUD <200ms; GraphQL <2s; authz decision <15ms; GitOps sync <60s.

**Architecture** (from ADR/Spine):

- **Key Decision 1 (AD-1):** Envoy Gateway is the exclusive ingress boundary; five hard domain-per-route boundaries with distinct authN/authZ.
- **Key Decision 2 (AD-3):** Serverless-first compute only — KNative+Restate, SpinKube, Pulsar Functions; no Deployment/StatefulSet for application logic.
- **Key Decision 3 (AD-4):** Event-mesh (Pulsar primary + Kafka secondary) is the only cross-domain integration fabric; DB change feeds bridged via KNative Eventing.
- **Key Decision 4 (AD-5, AD-8, AD-9, AD-10, AD-11, AD-13):** Protobuf CommonEnvelope with `origin` + `idempotency_key` (loop prevention/dedup); mTLS via Cilium SPIFFE; GitOps-only delivery; air-gapped delivery; multi-region data sovereignty; secrets via Infisical.

**Expected Scale** (from PRD/Architecture):

- 100K+ RPS telemetry per region; 1M-row ClickHouse query <2s; 10K-node graph traversal <100ms; 24h PromQL <2s; <15ms combined authz; <60s GitOps sync; <30min env bootstrap; retention 7d/30d/1y.

**Risk Summary:**

- **Total risks**: 26
- **High-priority (≥6)**: 12 risks requiring immediate mitigation
- **Test effort**: ~62 scenarios (see QA doc) — ~2-3 weeks for 1 QA, ~1.5-2 weeks for 2 QAs

---

## Quick Guide

### 🚨 BLOCKERS - Team Must Decide (Can't Proceed Without)

**Pre-Implementation Critical Path** — These MUST be completed before QA can write live-cluster E2E/integration tests:

1. **B-001: Live test cluster provisioned** — A healthy HPDC dev cluster (Talos `admin@hpa-dev`) reachable from CI/workstation. Without it, E2E and route-auth tests are blocked. (recommended owner: Platform Eng)
2. **B-002: Test identity fixtures** — Casdoor test users (one per role: operator, manager, administrator, technic, developer, CEO, client), JWT issue/refresh flow, and Envoy Gateway API-Key secrets for `/events` + `/telemetry`. Without tokens/keys, every auth test is blocked. (recommended owner: Security/Backend)
3. **B-003: Test message consumers** — A Pulsar + Kafka consumer/reader harness so tests can assert message arrival on internal topics (FR-1..FR-4, FR-9). Gateway exposes producers only; assertions need consumers. (recommended owner: Backend)
4. **B-004: Multi-region test topology** — Two region clusters (e.g. `admin@hpa-dev-1`, `admin@hpa-dev-2`) with ClusterMesh + WireGuard for Epic 8 tests (FR-33..FR-35, NFR20). (recommended owner: Platform Eng)

**What we need from team:** Complete these 4 items pre-implementation or live-cluster test development is blocked.

---

### ⚠️ HIGH PRIORITY - Team Should Validate (We Provide Recommendation, You Approve)

1. **R-001 (OPS, score 9): GitOps drift** — Direct `kubectl` is forbidden (AD-9) but workflow may have drifted. Approve drift-detection gate: `argocd app diff` + `kustomize build` + `kubectl apply --dry-run=server` on every PR. (approver: Platform Eng)
2. **R-004 (PERF, score 6): 100K RPS not yet demonstrated** — `test_telemetry_capacity_dev.py` exists but no sustained-load report. Approve k6 load scope + nightly run. (approver: Platform Eng + QA)
3. **R-009 (SEC, score 6): AuthN route isolation** — Approve negative tests proving `/events`+`/telemetry` do NOT pass through Casdoor/Casbin and JWT routes reject API-Key. (approver: Security)
4. **R-010 (SEC, score 6): A2A impersonation** — Approve negative tests for agent impersonation prevention (FR-48). (approver: Security)
5. **R-011 (SEC, score 6): MCP policy enforcement** — Approve negative tests for MCP tool invocation without clearance (FR-47). (approver: Security)

**What we need from team:** Review recommendations and approve (or suggest changes).

---

### 📋 INFO ONLY - Solutions Provided (Review, No Decisions Needed)

1. **Test strategy**: 3-tier pyramid per ARCHITECTURE-SPINE §Testing & Quality — Unit, Integration, E2E, plus the existing 41 Python deployment tests retained as the manifest-validity base.
2. **Tooling**: Python `pytest`-style CLI scripts (existing convention), Playwright for UI E2E, k6 for load/performance, `kustomize build`/`kubectl diff`/`argocd app diff` for deployment tests, Spectral for OpenAPI.
3. **Tiered CI/CD**: PR (functional <15min), Nightly (perf + full regression), Weekly (chaos/multi-region/DR).
4. **Coverage**: ~62 scenarios prioritized P0-P3 with risk-based classification (see QA doc).
5. **Quality gates**: P0 100% pass, P1 ≥95%, no open score-9 risks, security scenarios 100%.

**What we need from team:** Just review and acknowledge (we already have the solution).

---

## For Architects and Devs - Open Topics 👷

### Risk Assessment

**Total risks identified**: 26 (12 high-priority score ≥6, 10 medium score 3-5, 4 low score 1-2)

#### High-Priority Risks (Score ≥6) - IMMEDIATE ATTENTION

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Timeline |
| ------- | -------- | ----------- | ----------- | ------ | ----- | ---------- | ----- | -------- |
| **R-001** | **OPS** | GitOps drift: direct kubectl/out-of-band changes diverge from Git (AD-9) | 3 | 3 | **9** | Argo CD app diff + kustomize build + server-side dry-run on every PR; nightly drift report | Platform Eng | Pre-release |
| **R-002** | **SEC** | Gateway auth bypass: route without SecurityPolicy exposes backend (CouchDB/Hasura/Kafka/Pulsar) | 2 | 3 | **6** | Route-table audit test: every HTTPRoute must have matching SecurityPolicy (JWT or API-Key) | Security | Pre-release |
| **R-003** | **SEC** | Casbin fail-open / DENY-wins not enforced: ext_authz failure allows request | 2 | 3 | **6** | Negative tests: unauthenticated, wrong-role, expired-JWT, ext_authz-down → 401/403; DENY-wins matrix | Security | Pre-release |
| **R-004** | **PERF** | 100K RPS p99<100ms not validated on real substrate; QEMU dev may under-provision | 2 | 3 | **6** | k6 load test at 100K RPS; capacity baseline; verify `ingestion_dropped_total` under limit | Platform Eng + QA | Nightly |
| **R-005** | **DATA** | Message loss during back-pressure drops (drop vs loss ambiguity); buffer-full loses data unannounced | 3 | 2 | **6** | Test FR-4: lag>threshold → producer backoff; buffer-full → drop with metric increment; assert no loss before threshold | Backend + QA | Nightly |
| **R-006** | **DATA** | Cross-region replication accidentally enabled → sovereignty/compliance violation (NFR20) | 2 | 3 | **6** | Negative test: no replication config on regional stores by default; explicit-config required path | Platform Eng | Pre-release |
| **R-007** | **SEC** | mTLS not actually enforced: plaintext intra-cluster succeeds (FR-45, AD-8) | 2 | 3 | **6** | Cilium network-policy + mTLS probe tests; assert plaintext HTTP denied | Security | Pre-release |
| **R-008** | **SEC** | Secrets leaked to Git/ConfigMaps despite Infisical (NFR21, AD-13) | 2 | 3 | **6** | Secret-scan on repo; assert no secret literals in gitops/; assert InfisicalSecret CRD usage | Security | Pre-release |
| **R-009** | **SEC** | AuthN route confusion: `/events`+`/telemetry` pass through Casbin/JWT, or JWT routes accept API-Key (FR-38) | 2 | 3 | **6** | Negative tests per route asserting isolation boundaries | Security | Pre-release |
| **R-010** | **SEC** | A2A impersonation not prevented (FR-48) | 2 | 3 | **6** | Negative test: unregistered/forged agent message rejected; `registered_agents_required` enforced | Security | Pre-release |
| **R-011** | **SEC** | MCP tool invocation bypasses security policy (FR-47) | 2 | 3 | **6** | Negative test: tool call without required perms → denied + audit log entry | Security | Pre-release |
| **R-012** | **TECH** | Change-feed loops (AD-16): self-origin CDC/_changes events trigger infinite processing | 2 | 3 | **6** | Integration test with CDC/_changes fakes: self-origin ignored, idempotency dedup, loop terminates | Backend | Pre-release |

#### Medium-Priority Risks (Score 3-5)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner |
| ------- | -------- | ----------- | ----------- | ------ | ----- | ---------- | ----- |
| R-013 | PERF | ClickHouse 1M-row query >2s (NFR4) | 2 | 2 | 4 | k6/benchmark query test; index/partition verification | QA |
| R-014 | PERF | KeyDB cache-miss storm → CouchDB fallback latency (NFR5) | 2 | 2 | 4 | Fallback-path latency test with cache eviction | Backend |
| R-015 | DATA | Alert state-machine optimistic-lock race (NFR26) | 2 | 2 | 4 | Concurrent-operator test; 409 on stale revision | Backend |
| R-016 | OPS | Harbor CVE threshold not enforced → unsigned/unscanned image promoted (FR-30) | 2 | 2 | 4 | Push-with-high-CVE rejected; scan-gate in Kargo Freight | Platform Eng |
| R-017 | OPS | Spegel P2P pull-time reduction not verified (>50%) (FR-31) | 2 | 2 | 4 | Scale-up pull-time benchmark with/without Spegel | Platform Eng |
| R-018 | DATA | Idempotency not honored → duplicate processing (AD-5 `idempotency_key`) | 2 | 2 | 4 | Duplicate-message test asserting single processing | Backend |
| R-019 | PERF | Env bootstrap >30min or sync >60s (NFR13/NFR22) | 2 | 2 | 4 | Stopwatch bootstrap + commit-to-sync latency test | Platform Eng |
| R-020 | PERF | GraphQL cross-store query >2s (NFR9) | 2 | 2 | 4 | Benchmark query on /gql federation | QA |
| R-021 | OPS | Log search >5s by namespace/pod/content (NFR14) | 2 | 2 | 4 | vmlog search latency test | Platform Eng |
| R-022 | DATA | ArcadeDB traversal >100ms on 10K-node graph (NFR10) | 1 | 3 | 3 | Benchmark traversal on seeded 10K graph | Backend |

#### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | Probability | Impact | Score | Action |
| ------- | -------- | ----------- | ----------- | ------ | ----- | ------ |
| R-023 | PERF | Alert response webhook retry/backoff not honored (NFR7) | 1 | 2 | 2 | Monitor (covered by P1 tests) |
| R-024 | OPS | OpenAPI spec drift vs implementation (FR-39) | 1 | 2 | 2 | Monitor (Spectral lint in CI) |
| R-025 | BUS | Backstage catalog/golden-path template broken (FR-17) | 1 | 2 | 2 | Monitor (P2 smoke) |
| R-026 | TECH | Non-serverless Deployment/StatefulSet for app logic (AD-3) | 1 | 2 | 2 | Monitor (manifest scan) |

#### Risk Category Legend

- **TECH**: Technical/Architecture (flaws, integration, scalability)
- **SEC**: Security (access controls, auth, data exposure)
- **PERF**: Performance (SLA violations, degradation, resource limits)
- **DATA**: Data Integrity (loss, corruption, inconsistency)
- **BUS**: Business Impact (UX harm, logic errors, revenue)
- **OPS**: Operations (deployment, config, monitoring)

---

### NFR Testability Requirements

**Purpose:** Capture what architecture must provide so NFR validation can be automated later. This is planning guidance, not final evidence assessment.

| NFR Category | Threshold / Requirement | Current Design Support | Gap / Decision Needed | Planned Evidence |
| ------------ | ----------------------- | ---------------------- | --------------------- | ---------------- |
| Security | AuthN per route (API-Key vs JWT), Casbin DENY-wins, mTLS, secrets-out-of-Git, multi-tenant isolation, data sovereignty (NFR15/20/21/24) | Partial — policies declared in manifests, enforcement not proven | Test identity fixtures (B-002); confirm ext_authz fail-closed semantics | Security test suite (TC-03/29/30/34/38/46-51), secret scan |
| Performance | 100K RPS p99<100ms; 1K RPS alert p99<500ms; ClickHouse 1M<2s; GraphQL<2s; ArcadeDB<100ms; authz<15ms (NFR1/2/4/8/9/10) | Partial — capacity test exists, no load harness | k6 harness (B-005); sustained-load report | k6 load report, latency baselines |
| Reliability | 4 9s availability; 99.9% delivery; retry/backoff; OTel traces; chaos recovery (NFR3/7/11/12/17) | Partial — failover not exercised | Multi-region topology (B-004); chaos tooling | Soak report, DR drill, chaos results |
| Maintainability | Env bootstrap <30min; GitOps sync <60s; log search <5s; OpenAPI conformance (NFR13/14/22/23) | Partial — sync/bootstrap observed manually | Drift gate (R-001); Spectral lint | Bootstrap stopwatch, sync-latency report, Spectral run |

**Unknown thresholds:** NFR17 chaos recovery target SLO value not stated in PRD — assumed "service recovers and resumes normal operation"; confirm target RTO/RPO with Platform. NFR3 sustained-24h target confirmed as 99.9% delivery.

**Assessment boundary:** Final PASS/CONCERNS/FAIL status belongs in `nfr-assess` after implementation evidence exists.

---

### Testability Concerns and Architectural Gaps

**🚨 ACTIONABLE CONCERNS - Architecture Team Must Address**

#### 1. Blockers to Fast Feedback (WHAT WE NEED FROM ARCHITECTURE)

| Concern | Impact | What Architecture Must Provide | Owner | Timeline |
| ------- | ------ | ------------------------------ | ----- | -------- |
| **No live-cluster E2E testbed (B-001)** | E2E route/auth/UI scenarios cannot execute reliably | CI-managed HPDC dev cluster or smoke-checked local cluster (`admin@hpa-dev`); documented runbook | Platform Eng | Pre-release |
| **No test identity fixtures (B-002)** | Every authN/authZ test blocked | Casdoor test users (7 roles) + JWT issue/refresh + API-Key fixtures under `output/test-artifacts/fixtures/` | Security/Backend | Pre-release |
| **No internal test consumers (B-003)** | Message-arrival assertions (FR-1..FR-4, FR-9) impossible | Pulsar/Kafka test consumer harness behind gateway; assert via `idempotency_key` | Backend | Pre-release |
| **Multi-region topology not automated (B-004)** | Epic 8 tests (FR-33..35, NFR20) blocked | 2 region clusters + ClusterMesh + WireGuard; documented topology | Platform Eng | Pre-release |
| **Load tooling absent (B-005)** | NFR1/4/9/10/16 unverifiable | k6 (or locust) scenarios + nightly perf job | QA + Platform Eng | Nightly |
| **No test-data seeding API** | Cannot parallelize tests safely | Provide `POST /test/seed` endpoint or documented direct-DB seeding + auto-cleanup | Backend | Pre-release |

**Example:** No API for test data seeding → Cannot parallelize tests → Provide POST /test/seed endpoint (Backend, pre-implementation)

#### 2. Architectural Improvements Needed (WHAT SHOULD BE CHANGED)

1. **Drift-detection gate (R-001)**
   - **Current problem**: Direct kubectl changes silently diverge from Git, breaking AD-9.
   - **Required change**: Argo CD app diff + `kustomize build` + `kubectl apply --dry-run=server` as PR gate; nightly drift report.
   - **Impact if not fixed**: Non-reproducible environments; release-blocking R-001 stays open.
   - **Owner**: Platform Eng. **Timeline**: Pre-release.

2. **Route-table / SecurityPolicy audit (R-002)**
   - **Current problem**: No automated proof that every HTTPRoute is protected.
   - **Required change**: Enforce SecurityPolicy on all routes; keep route manifests machine-readable for test consumption.
   - **Impact if not fixed**: Unauthenticated access to CouchDB/Hasura/Kafka/Pulsar.
   - **Owner**: Security. **Timeline**: Pre-release.

3. **AuthN boundary hardening (R-009)**
   - **Current problem**: Route-to-authN mapping (API-Key vs JWT) is implicit, not asserted.
   - **Required change**: Declare authN type per route (annotation/CRD); reject mismatched credentials.
   - **Impact if not fixed**: Credential-confusion attacks on `/events`, `/telemetry`, `/gql`.
   - **Owner**: Security. **Timeline**: Pre-release.

---

### Testability Assessment Summary

**📊 CURRENT STATE - FYI**

#### What Works Well

- ✅ **AD-1 exclusive ingress** → single auth chokepoint; route-table audit is tractable.
- ✅ **AD-5 protobuf envelope + `idempotency_key` + `origin`** → deterministic dedup/loop assertions.
- ✅ **AD-9 GitOps-only** → deployment tests via `kustomize build` + `kubectl apply --dry-run=server` + `argocd app diff`; 41 existing Python deployment tests form a solid base.
- ✅ **Structured errors (code/message/details), ULID, RFC3339** → deterministic assertions.
- ✅ **Three-tier pyramid documented** in ARCHITECTURE-SPINE §Testing & Quality.
- ✅ **TelemHub → Kafka → Pulsar event-mesh** → message-flow assertions feasible via existing telemetry tests.

#### Accepted Trade-offs (No Action Required)

For HPDC system-level Phase 1 verification, the following trade-offs are acceptable:

- **No chaos framework (Chaos Mesh) yet** — pod-kill scripts + weekly failover suffice; revisit post-GA.
- **Gateway producer-only exposure** — internal consumers added as test harness (B-003) rather than production endpoints; acceptable for Phase 1.

---

### Risk Mitigation Plans (High-Priority Risks ≥6)

**Purpose**: Detailed mitigation strategies for all 12 high-priority risks (score ≥6). These risks MUST be addressed before release.

#### R-001: GitOps drift (Score: 9) - CRITICAL

**Mitigation Strategy:**

1. Add `argocd app diff` + `kustomize build` + `kubectl apply --dry-run=server` as a PR gate in the delivery pipeline.
2. Add nightly drift-report job comparing live state vs Git (`argocd app list` + `argocd app diff`); alert on diff.
3. Restrict direct write access: enforce AD-9 (GitOps-only) on dev clusters; audit-log kubectl access.
4. On drift detection, block Kargo Freight promotion until Git/live reconcile.

**Owner:** Platform Eng
**Timeline:** Pre-release
**Status:** Planned
**Verification:** TC-20 (Argo CD healthy + sync <60s); drift report shows zero diffs for 2 consecutive weeks.

#### R-002: Gateway auth bypass (Score: 6) - HIGH

**Mitigation Strategy:**

1. Enforce SecurityPolicy (JWT or API-Key) on every HTTPRoute; fail-closed default.
2. Add route-table audit test asserting each HTTPRoute has matching SecurityPolicy (TC-39).
3. Add negative probe: unauthenticated request to every route → 401/403, no backend exposure.

**Owner:** Security
**Timeline:** Pre-release
**Status:** Planned
**Verification:** TC-39 + TC-18 (direct backend port blocked) pass.

#### R-003: Casbin DENY-wins / fail-open (Score: 6) - HIGH

**Mitigation Strategy:**

1. Confirm ext_authz failure mode is fail-closed (deny on error) in Envoy Gateway config.
2. Add negative auth matrix: unauthenticated, wrong-role, expired-JWT, revoked-token, ext_authz-down → 401/403 (TC-29, TC-30).
3. Add DENY-wins policy tests: explicit deny rule overrides allow (TC-58 multi-tenant).

**Owner:** Security
**Timeline:** Pre-release
**Status:** Planned
**Verification:** TC-29/TC-30/TC-58 pass; no 2xx on unauthorized requests.

#### R-004: 100K RPS not validated (Score: 6) - HIGH

**Mitigation Strategy:**

1. Add k6 load scenarios for `/events` at 100K RPS with p99<100ms assertion (NFR1).
2. Run capacity baseline on dev cluster; document bottleneck (QEMU vs bare-metal).
3. Verify `ingestion_dropped_total` stays 0 until configured drop threshold.

**Owner:** Platform Eng + QA
**Timeline:** Nightly (pre-release baseline)
**Status:** Planned
**Verification:** k6 load report in CI artifacts; TC-02/TC-57 pass.

#### R-005: Message loss under back-pressure (Score: 6) - HIGH

**Mitigation Strategy:**

1. Implement and verify producer backoff when lag > threshold (FR-4).
2. Ensure buffer-full path drops with metric increment (`ingestion_dropped_total`), not silent loss.
3. Add tests: no loss below threshold; counted drops above threshold; consumer lag monitoring.

**Owner:** Backend + QA
**Timeline:** Nightly
**Status:** Planned
**Verification:** TC-05/TC-09 pass; drop metric matches event count under sustained overload.

#### R-006: Cross-region sovereignty violation (Score: 6) - HIGH

**Mitigation Strategy:**

1. Assert regional stores have NO replication config by default (negative test, TC-34).
2. Require explicit opt-in for any cross-region data path; document approval flow.
3. Add manifest-level check that cross-region replication requires a named override label.

**Owner:** Platform Eng
**Timeline:** Pre-release
**Status:** Planned
**Verification:** TC-34 pass; no replication resources present in regional cluster manifests.

#### R-007: mTLS not enforced (Score: 6) - HIGH

**Mitigation Strategy:**

1. Verify Cilium/SPIFFE mTLS mesh policies are applied to all app namespaces.
2. Add probe tests: plaintext HTTP between services denied; mTLS handshake succeeds (TC-46).
3. Add network-policy test: non-gateway → data-plane denied (TC-47).

**Owner:** Security
**Timeline:** Pre-release
**Status:** Planned
**Verification:** TC-46/TC-47 pass; Hubble flow logs show no plaintext intra-cluster traffic.

#### R-008: Secrets in Git (Score: 6) - HIGH

**Mitigation Strategy:**

1. Add secret-scan (gitleaks or equivalent) to CI; block on findings (TC-51).
2. Assert no secret literals in gitops/ manifests; assert InfisicalSecret CRD usage.
3. Rotate any secrets already committed to Git history.

**Owner:** Security
**Timeline:** Pre-release
**Status:** Planned
**Verification:** TC-51 pass; scan clean across repo + history.

#### R-009: AuthN route confusion (Score: 6) - HIGH

**Mitigation Strategy:**

1. Declare authN type per route; enforce in gateway config.
2. Add negative tests: `/events`+`/telemetry` reject Bearer; JWT routes reject API-Key (TC-03).
3. Add route isolation audit to route-table test (TC-39).

**Owner:** Security
**Timeline:** Pre-release
**Status:** Planned
**Verification:** TC-03 pass; no credential-confusion path found in route audit.

#### R-010: A2A impersonation (Score: 6) - HIGH

**Mitigation Strategy:**

1. Enforce registered-agent registry; reject unregistered/forged agent messages (TC-49).
2. Verify registered-agent authN + authZ on A2A endpoints (TC-50).
3. Add audit logging for agent identity resolution failures.

**Owner:** Security
**Timeline:** Pre-release
**Status:** Planned
**Verification:** TC-49/TC-50 pass.

#### R-011: MCP policy bypass (Score: 6) - HIGH

**Mitigation Strategy:**

1. Enforce MCP tool invocation security policy (permission checks per tool).
2. Add negative test: tool call without required perms → denied + audit entry (TC-48).
3. Add positive test: authorized tool call succeeds within tenant scope.

**Owner:** Security
**Timeline:** Pre-release
**Status:** Planned
**Verification:** TC-48 pass; audit log contains denial entries.

#### R-012: Change-feed loops (Score: 6) - HIGH

**Mitigation Strategy:**

1. Verify self-origin CDC/_changes events are ignored (AD-16 origin check).
2. Add integration test with CDC/_changes fakes: self-origin ignored, `idempotency_key` dedup, loop terminates (TC-17).
3. Add loop-termination guard: max-processing-depth counter + alert.

**Owner:** Backend
**Timeline:** Pre-release
**Status:** Planned
**Verification:** TC-17 pass; no runaway processing in 24h soak.

---

### Assumptions and Dependencies

#### Assumptions

1. Live test cluster `admin@hpa-dev` will be reachable and healthy pre-release (B-001).
2. AuthN/AuthZ boundary is API-Key for `/events`+`/telemetry` and JWT+Casbin for `/gql`+admin routes per AD-2 (to be confirmed against manifests).
3. All 9 epics' implementations are deployed and green per sprint-status.yaml; this design verifies behavior, not re-implements.
4. NFR thresholds are as captured in PRD (SM-1..SM-8); NFR17 recovery SLO to be confirmed.
5. Team can provision k6 + Playwright tooling in CI without new vendor approvals.

#### Dependencies

1. B-001 live cluster — required pre-release
2. B-002 identity fixtures (Casdoor users, JWTs, API-Keys) — required pre-release
3. B-003 Pulsar/Kafka test consumer harness — required pre-release
4. B-004 multi-region topology (2 clusters, ClusterMesh, WireGuard) — required pre-release
5. B-005 k6 load harness — required by nightly milestone
6. DR/soak compute capacity on weekly runner — required by weekly milestone

#### Risks to Plan

- **Risk**: Cluster under-provisioned (QEMU) invalidates 100K RPS baseline.
  - **Impact**: NFR1 evidence unreliable; false pass/fail.
  - **Contingency**: Run capacity test on bare-metal/VM cluster; document hardware config with report.
- **Risk**: Playwright/k6 adoption delayed by approvals.
  - **Impact**: E2E/perf tiers slip.
  - **Contingency**: Start with existing Python pytest-style scripts for API/integration; add Playwright/k6 as accepted.
- **Risk**: Identity fixture scope (7 Casdoor roles) underestimated.
  - **Impact**: Auth matrix tests blocked.
  - **Contingency**: Provide 2 roles (administrator, operator) first for P0; expand for P1.

---

**End of Architecture Document**

**Next Steps for Architecture Team:**

1. Review Quick Guide (🚨/⚠️/📋) and prioritize blockers B-001..B-005
2. Assign owners and timelines for high-priority risks (≥6)
3. Validate assumptions and dependencies
4. Provide feedback to QA on testability gaps

**Next Steps for QA Team:**

1. Wait for pre-implementation blockers to be resolved
2. Refer to companion QA doc (test-design-qa.md) for test scenarios
3. Begin test infrastructure setup (factories, fixtures, environments)
