---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-08-07'
workflowType: 'testarch-test-design'
projectName: 'High Performance Distributed Cluster (HPDC)'
tier: 'System-Level'
inputDocuments:
  - output/planning-artifacts/prds/prd-HPDC-2026-07-21/prd.md
  - output/planning-artifacts/architecture/architecture-HPDC-2026-07-30/ARCHITECTURE-SPINE.md
  - output/planning-artifacts/epics.md
  - output/test-artifacts/test-design/test-design-architecture.md
---

# Test Design for QA: HPDC Enterprise GitOps Platform

**Purpose:** Test execution recipe for QA team. Defines what to test, how to test it, and what QA needs from other teams.

**Date:** 2026-08-07
**Author:** Master
**Status:** Draft
**Project:** High Performance Distributed Cluster (HPDC)

**Related:** See Architecture doc (test-design-architecture.md) for testability concerns and architectural blockers.

---

## Executive Summary

**Scope:** System-level verification of the HPDC platform across all 9 epics: alert pipeline (FR-1..13), data management (FR-14..17), observability & delivery (FR-18..27), security & compliance (FR-28..32), multi-region (FR-33..35), API/AI (FR-36..48).

**Risk Summary:**

- Total Risks: 26 (12 high-priority score ≥6, 10 medium, 4 low)
- Critical Categories: SEC (7 high), OPS (R-001 score 9), DATA (R-005, R-006), PERF (R-004)

**Coverage Summary:**

- P0 tests: ~24 (critical paths, security, data integrity)
- P1 tests: ~28 (important features, integration, NFRs)
- P2 tests: ~8 (edge cases, smoke, regression)
- P3 tests: ~2 (exploratory, benchmarks deferred)
- **Total**: ~62 tests (~2-3 weeks with 1 QA)

---

## Not in Scope

| Item | Reasoning | Mitigation |
| ---- | --------- | ---------- |
| **Full DR automation** | Requires 2+ production-grade regions; cost exceeds current phase | Covered by weekly failover drill (TC-55/TC-35); automated DR deferred |
| **AI/LLM model quality eval** | NFR/AI-SPEC not yet defined for agent reasoning quality | Security/permission paths (TC-48..50) covered; model eval via `ai-integration-phase` workflow |
| **UI accessibility audit** | No WCAG requirement in PRD | Deferred; visual smoke only (TC-59..62) |
| **Documentation validation** | Backstage/Grafana docs out of test scope | Manual spot-check during P2 smoke |
| **Load testing on production hardware** | Prod-equivalent cluster unavailable | Baseline on dev cluster; hardware config noted with results |

**Note:** Items listed here have been reviewed and accepted as out-of-scope by QA, Dev, and PM.

---

## Dependencies & Test Blockers

**CRITICAL:** QA cannot proceed without these items from other teams.

### Backend/Architecture Dependencies (Pre-Implementation)

**Source:** See Architecture doc "Quick Guide" for detailed mitigation plans

1. **B-001: Live test cluster** - Platform Eng - Pre-release
   - Healthy HPDC dev cluster (`admin@hpa-dev`) reachable from CI/workstation
   - Blocks: all E2E + route-auth integration tests

2. **B-002: Test identity fixtures** - Security/Backend - Pre-release
   - Casdoor test users (7 roles: operator, manager, administrator, technic, developer, CEO, client)
   - JWT issue/refresh flow; API-Key secrets for `/events` + `/telemetry`
   - Blocks: all authN/authZ tests

3. **B-003: Test message consumers** - Backend - Pre-release
   - Pulsar + Kafka consumer/reader harness for internal topics
   - Blocks: message-arrival assertions (FR-1..4, FR-9)

4. **B-004: Multi-region topology** - Platform Eng - Pre-release
   - 2 region clusters + ClusterMesh + WireGuard (e.g. `admin@hpa-dev-1`, `-2`)
   - Blocks: Epic 8 tests (FR-33..35, NFR20)

5. **B-005: Load harness (k6)** - QA + Platform Eng - Nightly
   - k6 scenarios for NFR1/4/9/10/16
   - Blocks: performance evidence

### QA Infrastructure Setup (Pre-Implementation)

1. **Test Data Factories** - QA
   - Entity factory with faker-based randomization (devices, alerts, users)
   - Auto-cleanup fixtures for parallel safety
   - Seed via `/data` API or direct DB `_bulk_docs`/SQL with unique ULIDs

2. **Test Environments** - QA
   - Local: `admin@hpa-dev` Talos cluster; `kubectl` + curl probes
   - CI/CD: PR runner (pytest + Playwright), Nightly runner (k6 + full integration), Weekly runner (chaos + DR)
   - Staging: same as dev for this phase (no separate staging provisioned)

**Example factory pattern:**

```typescript
import { test } from '@seontechnologies/playwright-utils/api-request/fixtures';
import { expect } from '@playwright/test';
import { faker } from '@faker-js/faker';

test('device entity created via /data @p0', async ({ apiRequest }) => {
  const testData = {
    id: `device-${faker.string.uuid()}`,
    name: faker.string.alpha(10),
  };

  const { status } = await apiRequest({
    method: 'POST',
    path: '/data',
    body: testData,
  });

  expect(status).toBe(201);
});
```

---

## Risk Assessment

**Note:** Full risk details in Architecture doc. This section summarizes risks relevant to QA test planning.

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description | Score | QA Test Coverage |
| ------- | -------- | ----------- | ----- | ---------------- |
| **R-001** | OPS | GitOps drift (direct kubectl diverges from Git) | **9** | TC-20 deployment drift gate, TC-21 promotion gate |
| **R-002** | SEC | Gateway auth bypass (route without SecurityPolicy) | **6** | TC-39 route-table audit, TC-18 direct-port denial |
| **R-003** | SEC | Casbin fail-open / DENY-wins not enforced | **6** | TC-29/30 auth matrix, TC-58 multi-tenant isolation |
| **R-004** | PERF | 100K RPS not validated | **6** | TC-02, TC-57 k6 load + capacity baseline |
| **R-005** | DATA | Message loss under back-pressure | **6** | TC-05 drop/backoff semantics, TC-09 consumer delivery |
| **R-006** | DATA | Cross-region replication accidentally enabled | **6** | TC-34 negative sovereignty, TC-35 failover |
| **R-007** | SEC | mTLS not actually enforced | **6** | TC-46 mTLS probe, TC-47 network policy |
| **R-008** | SEC | Secrets leaked to Git/ConfigMaps | **6** | TC-51 secret scan + Infisical CRD check |
| **R-009** | SEC | AuthN route confusion (API-Key vs JWT) | **6** | TC-03 credential-isolation negatives |
| **R-010** | SEC | A2A impersonation | **6** | TC-49/50 agent identity negatives/positives |
| **R-011** | SEC | MCP tool invocation bypass | **6** | TC-48 MCP permission negatives + audit |
| **R-012** | TECH | Change-feed loops | **6** | TC-17 self-origin/loop-termination test |

### Medium/Low-Priority Risks

| Risk ID | Category | Description | Score | QA Test Coverage |
| ------- | -------- | ----------- | ----- | ---------------- |
| R-013 | PERF | ClickHouse 1M-row query >2s | 4 | TC-04 benchmark query |
| R-014 | PERF | KeyDB fallback latency >2x | 4 | TC-41 cache-miss fallback |
| R-015 | DATA | Alert state-machine optimistic-lock race | 4 | TC-06, TC-16 concurrent-write |
| R-016 | OPS | Harbor CVE threshold not enforced | 4 | TC-31 image promotion gate |
| R-017 | OPS | Spegel P2P pull-time reduction not verified | 4 | TC-32 pull-time benchmark |
| R-018 | DATA | Idempotency not honored | 4 | TC-07 duplicate delivery |
| R-019 | PERF | Env bootstrap / sync SLA missed | 4 | TC-20, TC-56 stopwatch |
| R-020 | PERF | GraphQL cross-store >2s | 4 | TC-37 federation benchmark |
| R-021 | OPS | Log search >5s | 4 | TC-26 vmlog latency |
| R-022 | DATA | ArcadeDB traversal >100ms | 3 | TC-42 seeded traversal |
| R-023 | PERF | Webhook retry/backoff | 2 | TC-08 retry test |
| R-024 | OPS | OpenAPI spec drift | 2 | TC-40 Spectral lint |
| R-025 | BUS | Backstage golden-path broken | 2 | TC-19 P2 smoke |
| R-026 | TECH | Non-serverless app workloads (AD-3) | 2 | TC-20 manifest scan |

---

## NFR Test Coverage Plan

**Purpose:** Map NFR requirements to planned validation work. This section defines what evidence QA should create or collect; it does not assign final PASS/CONCERNS/FAIL status.

| NFR Category | Requirement / Threshold | Planned Validation | Tool / Level | Evidence Artifact | Priority |
| ------------ | ----------------------- | ------------------ | ------------ | ----------------- | -------- |
| Security | AuthN per route, DENY-wins, mTLS, secrets, sovereignty, multi-tenancy (NFR15/20/21/24) | Auth matrix negatives, route audit, mTLS probe, secret scan | API/Integration + CI scan | Security test report, secret-scan log | P0 |
| Performance | 100K RPS p99<100ms; 1K alert p99<500ms; ClickHouse<2s; GraphQL<2s; ArcadeDB<100ms; authz<15ms (NFR1/2/4/8/9/10) | k6 load, latency baselines | k6/Integration | k6 report, latency dashboard | P0 |
| Reliability | 4 9s; 99.9% delivery; retry/backoff; OTel traces; chaos recovery (NFR3/7/11/12/17) | Soak 24h, failover drill, retry test, trace assertions | Integration/E2E/monitoring | Soak report, DR drill log, trace evidence | P0 |
| Maintainability | Bootstrap <30min; sync <60s; log search <5s; OpenAPI conformance (NFR13/14/22/23) | Stopwatch bootstrap, sync-latency, vmlog search, Spectral | CI/Integration | Bootstrap log, sync report, Spectral output | P1 |
| Data | Retention 7d/30d/1y; checksums; optimistic locking (NFR19/25/26) | Retention policy check, checksum test, concurrent-write | Integration | Retention report, integrity test results | P1 |
| Scalability | 3.6K edge devices; horizontal scale (NFR16/18) | Capacity + scale-out test | k6/Integration | Capacity report | P1 |

**Missing thresholds or evidence sources:** NFR17 recovery SLO (RTO/RPO) undefined in PRD — clarify with Platform before `nfr-assess`. Chaos framework (Chaos Mesh) not adopted — pod-kill script evidence only.

---

## Entry Criteria

**QA testing cannot begin until ALL of the following are met:**

- [ ] All requirements and assumptions agreed upon by QA, Dev, PM
- [ ] Test environments provisioned and accessible (B-001)
- [ ] Test data factories ready or seed data available
- [x] Pre-implementation harness blockers resolved (B-002, B-003, B-005 built 2026-08-11; B-004 open)
- [ ] Feature deployed to test environment (all 9 epics per sprint-status.yaml)
- [x] Load tooling available (B-005 k6 harness built; full soak needs k6 binary + live cluster)

## Exit Criteria

**Testing phase is complete when ALL of the following are met:**

- [ ] All P0 tests passing
- [ ] All P1 tests passing (or failures triaged and accepted)
- [ ] No open high-priority / high-severity bugs
- [ ] Test coverage agreed as sufficient by QA Lead and Dev Lead
- [ ] Performance baselines met (100K RPS p99<100ms, ClickHouse <2s)
- [ ] R-001 (score 9) mitigation verified closed

---

## Project Team

| Name | Role | Testing Responsibilities |
| ---- | ---- | ------------------------ |
| Master | QA Lead | Test strategy, E2E/API test implementation, test review |
| TBD | Dev Lead | Unit tests, integration test support, testability hooks |
| TBD | PM | Requirements clarification, acceptance criteria, UAT sign-off |
| TBD | Architect | Testability review, NFR guidance, environment provisioning |

---

## Test Coverage Plan

**IMPORTANT:** P0/P1/P2/P3 = **priority and risk level** (what to focus on if time-constrained), NOT execution timing. See "Execution Strategy" for when tests run.

### P0 (Critical)

**Criteria:** Blocks core functionality + High risk (≥6) + No workaround + Affects majority of users

| Test ID | Requirement | Test Level | Risk Link | Notes |
| ------- | ----------- | ---------- | --------- | ----- |
| **P0-001** | FR-1 | Integration | — | POST /events; protobuf envelope; ULID + RFC3339 |
| **P0-002** | FR-1, FR-2 | Integration | R-004 | Telemetry → topic → ClickHouse <2s (NFR6) |
| **P0-003** | FR-1, FR-38 | Integration | R-009 | /events + /telemetry accept API-Key only; Bearer rejected |
| **P0-004** | FR-4 | Integration | R-005 | Back-pressure: lag→backoff; drop metric; no loss before threshold |
| **P0-005** | FR-5, FR-6 | Integration | R-015 | Alert created on breach; state transitions |
| **P0-006** | FR-6, FR-8 | Integration | R-018 | Duplicate delivery → single processing (idempotency) |
| **P0-007** | FR-9 | Integration | R-005 | Alert routed via Pulsar; consumer receives enriched event |
| **P0-008** | FR-12 | E2E | R-004 | Alert E2E: ingest→decision→dispatch→ClickHouse |
| **P0-009** | FR-14 | Integration | — | Entity CRUD round-trip; <200ms |
| **P0-010** | FR-14, NFR26 | Integration | R-015 | Concurrent update → 409 optimistic lock |
| **P0-011** | FR-15 | Integration | R-012 | CDC self-origin ignored; no loop |
| **P0-012** | FR-28, FR-29 | Integration | R-003 | Casdoor SSO; role→group mapping |
| **P0-013** | FR-28, FR-29 | Integration | R-003 | Expired/revoked JWT → 401; wrong role → 403 |
| **P0-014** | FR-33, NFR20 | Integration | R-006 | Regional store: NO cross-region replication by default |
| **P0-015** | FR-37 | Integration | R-011 | Hasura/MCP query authorized per permission |
| **P0-016** | FR-38 | Deployment | R-002 | Route-table audit: every HTTPRoute has SecurityPolicy |
| **P0-017** | FR-45, NFR24 | Integration | R-007 | mTLS enforced; plaintext intra-cluster denied |
| **P0-018** | FR-46 | Integration | R-007 | Cilium policies deny non-gateway → data-plane |
| **P0-019** | FR-47 | Integration | R-011 | MCP tool without permission → denied + audit |
| **P0-020** | FR-48 | Integration | R-010 | A2A: unregistered agent rejected |
| **P0-021** | FR-48 | Integration | R-010 | A2A: registered agent verified + authorized |
| **P0-022** | NFR21 | Deployment | R-008 | No secrets in git; InfisicalSecret CRD used |
| **P0-023** | NFR3 | Integration | R-004 | 100K RPS sustained 24h, 99.9% delivered |
| **P0-024** | NFR15 | Integration | R-003 | Multi-tenant isolation: tenant A can't read tenant B |
| **P0-025** | UI (login) | E2E | — | Login → dashboard renders (Playwright) |
| **P0-026** | UI (SSO) | E2E | — | Casdoor SSO login (Playwright) |

**Total P0:** ~26 tests

---

### P1 (High)

**Criteria:** Important features + Medium risk (3-4) + Common workflows + Workaround exists but difficult

| Test ID | Requirement | Test Level | Risk Link | Notes |
| ------- | ----------- | ---------- | --------- | ----- |
| **P1-001** | FR-2, FR-3 | Integration | R-013 | Raw + derived telemetry GraphQL; <2s |
| **P1-002** | FR-7 | Integration | R-023 | Webhook retry/backoff; no duplicate fire |
| **P1-003** | FR-10 | Integration | — | Alert update → re-evaluation |
| **P1-004** | FR-11 | Integration | — | Delete alert → closed state, no stale fire |
| **P1-005** | FR-13 | Integration | — | Time-series aggregation → derived telemetry |
| **P1-006** | FR-14, FR-15 | Integration | — | Change feed on entity update |
| **P1-007** | FR-16 | Integration | R-002 | CouchDB only via gateway; direct port blocked |
| **P1-008** | FR-18 | Deployment | R-001 | Argo CD apps healthy; sync <60s (NFR22) |
| **P1-009** | FR-19, FR-20 | Integration | R-016 | Kargo Freight + verification gate promotes on green |
| **P1-010** | FR-21 | Integration | R-001 | Argo Rollouts: canary + rollback on metric fail |
| **P1-011** | FR-22 | Integration | — | Argo Events webhook → workflow |
| **P1-012** | FR-23 | Integration | — | Argo Workflows execute + retry |
| **P1-013** | FR-24 | Integration | R-021 | Prometheus targets UP; <2s queries |
| **P1-014** | FR-25, NFR14 | Integration | R-021 | vmlog search namespace/pod/content <5s |
| **P1-015** | FR-26, NFR12 | Integration | — | OTel traces propagated |
| **P1-016** | FR-30 | Integration | R-016 | Unsigned/high-CVE image rejected at promotion |
| **P1-017** | FR-31 | Integration | R-017 | Spegel P2P: pull time reduced >50% |
| **P1-018** | FR-32 | Integration | — | Image pull from internal mirror |
| **P1-019** | FR-35 | Integration | — | Hub aggregates regional metrics |
| **P1-020** | FR-36 | Integration | R-020 | GraphQL federation <2s (NFR9) |
| **P1-021** | FR-40 | Integration | R-014 | KeyDB hit; fallback <2x (NFR5) |
| **P1-022** | FR-41 | Integration | R-022 | ArcadeDB 10K traversal <100ms (NFR10) |
| **P1-023** | FR-42 | Integration | — | PostgreSQL relational queries |
| **P1-024** | FR-43 | Integration | — | YugabyteDB CRUD + consistency |
| **P1-025** | FR-44 | Integration | R-005 | Alert flow from Pulsar AND Kafka producers |
| **P1-026** | NFR19 | Integration | — | Retention 7d/30d/1y enforced |
| **P1-027** | NFR16 | Integration | — | 3.6K edge devices capacity |
| **P1-028** | NFR18 | Integration | — | Horizontal scale: replicas serve traffic |
| **P1-029** | NFR17 | Integration | — | Pod-kill failover <SLO |
| **P1-030** | NFR13 | Integration | R-019 | Env bootstrap <30min stopwatch |
| **P1-031** | UI (alerts) | E2E | — | Alert list → detail → acknowledge (Playwright) |

**Total P1:** ~31 tests

---

### P2 (Medium)

**Criteria:** Secondary features + Low risk (1-2) + Edge cases + Regression prevention

| Test ID | Requirement | Test Level | Notes |
| ------- | ----------- | ---------- | ----- |
| **P2-001** | FR-17 | E2E | Backstage catalog + golden-path renders |
| **P2-002** | FR-27 | E2E | Grafana dashboards render + data sources healthy |
| **P2-003** | FR-34, NFR11 | E2E | Multi-region failover: primary down → secondary |
| **P2-004** | FR-39, NFR23 | Unit | OpenAPI validated via Spectral |
| **P2-005** | UI (smoke) | E2E | Grafana + Backstage smoke |
| **P2-006** | FR-1 | Unit | Envelope schema validation edge cases |
| **P2-007** | FR-5 | Unit | Alert rule evaluation unit tests (thresholds, boundaries) |
| **P2-008** | FR-28 | Unit | JWT parse/expiry edge cases |

**Total P2:** ~8 tests

---

### P3 (Low)

**Criteria:** Nice-to-have + Exploratory + Performance benchmarks + Documentation validation

| Test ID | Requirement | Test Level | Notes |
| ------- | ----------- | ---------- | ----- |
| **P3-001** | — | E2E | Full DR automation rehearsal (deferred) |
| **P3-002** | NFR10 | Integration | Graph traversal at extreme scale (>10K) benchmark |

**Total P3:** ~2 tests

---

## Execution Strategy

**Philosophy:** Run everything in PRs unless there's significant infrastructure overhead. Playwright with parallelization is extremely fast (100s of tests in ~10-15 min).

**Organized by TOOL TYPE:**

### Every PR: Playwright + pytest Tests (~10-15 min)

**All functional tests** (from any priority level):

- All E2E, API, integration, unit tests using Playwright + pytest-style scripts
- Parallelized across 4 shards
- Total: ~40 Playwright/pytest tests (includes P0, P1, P2, P3 functional)
- Includes: secret scan (TC/P0-022), Spectral lint (P2-004), kustomize dry-run + argocd diff (P1-008, P0-016)

**Why run in PRs:** Fast feedback, no expensive infrastructure

### Nightly: k6 Performance Tests (~30-60 min)

**All performance tests** (from any priority level):

- Load, stress, spike, endurance: NFR1/2/4/8/9/10/16 (P0-002, P0-023, P1-001, P1-020, P1-021, P1-022, P1-027)
- Full integration regression: alert pipeline, data plane, GitOps (P0-004..007, P0-014, P1-008..012)
- E2E UI suite (P0-025/026, P1-031, P2-001/002/005)
- vmlog search + bootstrap stopwatch (P1-014, P1-030)

**Why defer to nightly:** Expensive infrastructure (full cluster), long-running (30-60 min per test)

### Weekly: Chaos & Long-Running (~hours)

**Special infrastructure tests** (from any priority level):

- Multi-region failover (P2-003) — requires 2 clusters + ClusterMesh + WireGuard
- Disaster recovery / pod-kill failover (P1-029) — 4+ hours
- Endurance / soak 24h (P0-023)

**Why defer to weekly:** Very expensive infrastructure, very long-running, infrequent validation sufficient

**Manual tests** (excluded from automation):

- DevOps validation (deployment, monitoring)
- Documentation validation

---

## QA Effort Estimate

**QA test development effort only** (excludes DevOps, Backend, Data Eng, Finance work):

| Priority | Count | Effort Range | Notes |
| -------- | ----- | ------------ | ----- |
| P0 | ~26 | ~1-1.5 weeks | Complex setup (security, performance, multi-step) |
| P1 | ~31 | ~1-1.5 weeks | Standard coverage (integration, API tests) |
| P2 | ~8 | ~2-3 days | Edge cases, simple validation |
| P3 | ~2 | ~1-2 days | Exploratory, benchmarks |
| **Total** | ~62 | **~2.5-4 weeks** | **1 QA engineer, full-time** |

**Assumptions:**

- Includes test design, implementation, debugging, CI integration
- Excludes ongoing maintenance (~10% effort)
- Assumes test infrastructure (factories, fixtures) ready (B-001..B-005)
- Interval ranges account for fixture complexity and cluster provisioning unknowns

**Dependencies from other teams:**

- See "Dependencies & Test Blockers" section for what QA needs from Backend, DevOps, Data Eng

---

## Implementation Planning Handoff (Optional)

**Include only if this test design produces implementation tasks that must be scheduled.**

**Use this to inform implementation planning; if no dedicated QA, assign to Dev owners.**

| Work Item | Owner | Target Milestone (Optional) | Dependencies/Notes |
| --------- | ----- | --------------------------- | ------------------ |
| Provision live test cluster | Platform Eng | Pre-release | B-001; Talos `admin@hpa-dev` |
| Create identity fixtures | Security/Backend | Pre-release | ✅ B-002 built 2026-08-11 (tests/atdd/support/fixtures.py) |
| Build consumer harness | Backend | Pre-release | ✅ B-003 built 2026-08-11 (tests/atdd/support/consumer_harness.py) |
| Provision multi-region topology | Platform Eng | Pre-release | B-004; ClusterMesh + WireGuard |
| Add k6 load harness | QA + Platform Eng | Nightly | ✅ B-005 built 2026-08-11 (LoadHarness in hpdc_test_client.py); full soak needs k6 binary + cluster |
| Author P0 integration tests | QA | Pre-release | Covers P0-001..024 |
| Author E2E Playwright suite | QA | Pre-release | P0-025/026, P1-031, P2-001..005 |
| Wire PR/Nightly/Weekly CI tiers | QA + Platform Eng | Pre-release | Tier config per Execution Strategy |
| Stabilization + Harbor triage | QA | Pre-release | Triage `test_install_harbor_dev.py` baseline |

---

## Tooling & Access

| Tool or Service | Purpose | Access Required | Status |
| --------------- | ------- | --------------- | ------ |
| Playwright | UI E2E (Playwright-utils fixtures) | None (open source) | Ready |
| k6 | Load/performance (NFR1/4/9/10/16) | None (open source) | Harness built (B-005, LoadHarness); k6 binary needed to run |
| pytest (Python) | Integration scripts (existing convention) | None | Ready |
| kubectl / Talosctl | Deployment probes, drift checks | Cluster access `admin@hpa-dev` | Pending (B-001) |
| argocd CLI | App diff, sync health | Cluster access | Pending (B-001) |
| gitleaks | Secret scan (NFR21) | None | Ready |

**Access requests needed (if any):**

- [ ] Cluster access to `admin@hpa-dev`, `admin@hpa-dev-1`, `admin@hpa-dev-2`
- [ ] Casdoor admin credentials for fixture users (B-002)
- [ ] Pulsar/Kafka cluster admin for topic/consumer provisioning (B-003)

---

## Interworking & Regression

**Services and components impacted by this feature:**

| Service/Component | Impact | Regression Scope | Validation Steps |
| ----------------- | ------ | ---------------- | ---------------- |
| **Envoy Gateway routes** | AuthN/authZ boundary changes affect all tests | Route-table audit (P0-016) | Re-run P0-003/012/013 after any route change |
| **Pulsar/Kafka mesh** | Message format/flow changes affect alert pipeline | Existing telemetry tests | Re-run P0-002/004/007 after event-mesh change |
| **GitOps manifests** | New workloads must stay GitOps-only | 41 existing deployment tests | All existing `tests/` Python scripts must pass |
| **CouchDB/YugabyteDB** | Data-plane changes affect CRUD + change-feed | P0-009/010/011 | Re-run data-plane P0 suite after schema change |
| **Identity (Casdoor/Casbin)** | Role/policy changes affect all authz | P0-012/013/024 | Re-run auth matrix on any policy change |

**Regression test strategy:**

- All 41 existing deployment tests must pass before release (regression base).
- Run full integration suite nightly; triage any P0/P1 regression within 24h.
- Cross-team coordination: Platform Eng owns cluster/manifest changes, Backend owns pipeline changes; QA owns test fixtures and suite.

---

## Appendix A: Code Examples & Tagging

**Playwright Tags for Selective Execution:**

```typescript
import { test } from '@seontechnologies/playwright-utils/api-request/fixtures';
import { expect } from '@playwright/test';

// P0 critical test - unauthenticated request returns 401
test('@P0 @Security unauthenticated /gql returns 401', async ({ apiRequest }) => {
  const { status, body } = await apiRequest({
    method: 'POST',
    path: '/gql',
    body: { query: '{ alerts { id } }' },
    skipAuth: true,
  });

  expect(status).toBe(401);
  expect(body.error).toContain('unauthorized');
});

// P1 integration test - entity change feed
test('@P1 @Integration entity update emits change feed', async ({ apiRequest }) => {
  await apiRequest({
    method: 'POST',
    path: '/data',
    body: { id: 'device-feed-1', name: 'sensor-a' },
  });

  const { status, body } = await apiRequest({
    method: 'GET',
    path: '/data/device-feed-1',
  });

  expect(status).toBe(200);
  expect(body).toHaveProperty('name', 'sensor-a');
});
```

**Run specific tags:**

```bash
# Run only P0 tests
npx playwright test --grep @P0

# Run P0 + P1 tests
npx playwright test --grep "@P0|@P1"

# Run only security tests
npx playwright test --grep @Security

# Run all Playwright tests in PR (default)
npx playwright test
```

**Python integration tests (existing convention):**

```bash
python3 tests/test_alert_handling.py   # alert state machine
python3 tests/test_entity_crud.py      # entity CRUD + change feed
python3 tests/test_graphql_gateway.py  # gateway route auth
```

---

## Appendix B: Knowledge Base References

- **Risk Governance**: `resources/knowledge/risk-governance.md` - Risk scoring methodology
- **Test Priorities Matrix**: `resources/knowledge/test-priorities-matrix.md` - P0-P3 criteria
- **Test Levels Framework**: `resources/knowledge/test-levels-framework.md` - E2E vs API vs Unit selection
- **Probability-Impact Matrix**: `resources/knowledge/probability-impact.md` - P×I scoring (≥6 high)
- **NFR Criteria**: `resources/knowledge/nfr-criteria.md` - NFR planning for system-level mode

---

**Generated by:** BMad TEA Agent
**Workflow:** `bmad-testarch-test-design`
**Version:** 4.0 (BMad v6)
