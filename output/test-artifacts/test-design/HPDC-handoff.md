---
title: 'TEA Test Design → BMAD Handoff Document'
version: '1.0'
workflowType: 'testarch-test-design-handoff'
inputDocuments:
  - output/test-artifacts/test-design/test-design-architecture.md
  - output/test-artifacts/test-design/test-design-qa.md
sourceWorkflow: 'testarch-test-design'
generatedBy: 'TEA Master Test Architect'
generatedAt: '2026-08-07'
projectName: 'High Performance Distributed Cluster (HPDC)'
---

# TEA → BMAD Integration Handoff

## Purpose

This document bridges TEA's test design outputs with BMAD's epic/story decomposition workflow (`create-epics-and-stories`). It provides structured integration guidance so that quality requirements, risk assessments, and test strategies flow into implementation planning.

## TEA Artifacts Inventory

| Artifact | Path | BMAD Integration Point |
| -------- | ---- | ---------------------- |
| Test Design Document (Architecture) | `output/test-artifacts/test-design/test-design-architecture.md` | Epic quality requirements, risk classification, testability blockers |
| Test Design Document (QA) | `output/test-artifacts/test-design/test-design-qa.md` | Story acceptance criteria, test scenarios (TC/P0-P3) |
| Risk Assessment | (embedded in architecture doc, §Risk Assessment) | Epic risk classification, story priority |
| Coverage Strategy | (embedded in QA doc, §Test Coverage Plan) | Story test requirements |
| NFR Testability Requirements | (embedded in architecture doc) | NFR evidence gates in implementation stories |
| Test Execution Strategy | (embedded in QA doc, §Execution Strategy) | CI/CD story scope (PR/Nightly/Weekly) |

## Epic-Level Integration Guidance

### Risk References

**Epic 7 (Security & Compliance — FR-28..FR-32):** P0 risks R-002, R-003, R-007, R-008, R-009 (gateway auth bypass, Casbin fail-open, mTLS, secrets, route confusion). Quality gate: all security P0 tests (P0-003, P0-012..022, P0-024) must pass.

**Epic 8 (Multi-Region — FR-33..FR-35):** P0/P1 risks R-006 (sovereignty), R-005 (delivery). Quality gate: P0-014 negative sovereignty, P1-019 hub aggregation, P2-003 failover drill.

**Epic 9 (API/AI — FR-36..FR-48):** P0 risks R-010, R-011 (A2A impersonation, MCP bypass). Quality gate: P0-015, P0-019..021 must pass.

**Epic 1 (Alert Pipeline — FR-1..FR-12):** P0 risks R-004 (perf), R-005 (loss), R-015, R-018. Quality gate: P0-001..008.

**Epic 4 (Observability & Delivery — FR-18..FR-27):** R-001 (drift, score 9) is release-blocking. Quality gate: P1-008..012 + nightly drift report.

### Quality Gates

Per epic, define these gates in implementation planning:

| Epic | Gate Criteria |
| ---- | ------------- |
| Epic 1 (Alert Pipeline) | P0-001..008 pass; no open R-005 (message loss) evidence gaps |
| Epic 4 (Observability & Delivery) | P1-008 (sync <60s) pass; drift report zero-diff 2 weeks |
| Epic 7 (Security & Compliance) | All security P0 tests pass; secret scan clean; mTLS probe green |
| Epic 8 (Multi-Region) | P0-014 pass; failover drill green |
| Epic 9 (API/AI) | P0-015/019/020/021 pass; MCP audit log evidence |

## Story-Level Integration Guidance

### P0/P1 Test Scenarios → Story Acceptance Criteria

**Critical scenarios that MUST be acceptance criteria (from QA doc P0):**

1. `POST /events` accepts API-Key only; Bearer rejected (P0-003) — alert ingestion stories
2. Duplicate delivery → single processing via `idempotency_key` (P0-006) — event-mesh stories
3. CDC/_changes self-origin ignored; no processing loop (P0-011) — change-feed stories
4. Expired/revoked JWT → 401; wrong role → 403 (P0-013) — auth stories
5. Regional store has NO cross-region replication by default (P0-014) — multi-region stories
6. MCP tool without permission → denied + audit log (P0-019) — AI agent stories
7. A2A unregistered agent rejected (P0-020) — AI agent stories
8. No secrets in git; InfisicalSecret CRD used (P0-022) — delivery/security stories
9. Every HTTPRoute has matching SecurityPolicy (P0-016) — gateway stories
10. mTLS enforced; plaintext intra-cluster denied (P0-017) — network/security stories

### Data-TestId Requirements

- Add `data-testid` attributes to: alert list rows, alert detail action buttons (acknowledge/resolve), navigation elements, login form (Casdoor), dashboard tiles. Referenced by E2E tests P0-025/026, P1-031, P2-001/002/005.

## Risk-to-Story Mapping

| Risk ID | Category | P×I | Recommended Story/Epic | Test Level |
| ------- | -------- | --- | ---------------------- | ---------- |
| R-001 | OPS | 9 | Epic 4 (GitOps delivery) | Deployment/Integration |
| R-002 | SEC | 6 | Epic 7 (Gateway security) | Integration/Deployment |
| R-003 | SEC | 6 | Epic 7 (AuthN/AuthZ) | Integration |
| R-004 | PERF | 6 | Epic 1 (Ingestion perf) | Integration/k6 |
| R-005 | DATA | 6 | Epic 1 (Back-pressure) | Integration |
| R-006 | DATA | 6 | Epic 8 (Sovereignty) | Integration |
| R-007 | SEC | 6 | Epic 7 (mTLS) | Integration |
| R-008 | SEC | 6 | Epic 7 (Secrets) | Deployment/CI |
| R-009 | SEC | 6 | Epic 7 (Route isolation) | Integration |
| R-010 | SEC | 6 | Epic 9 (A2A) | Integration |
| R-011 | SEC | 6 | Epic 9 (MCP policy) | Integration |
| R-012 | TECH | 6 | Epic 1 (Change-feed loops) | Integration |
| R-013..R-022 | Mixed | 3-4 | Across Epics 1/4/7/8/9 | Integration |
| R-023..R-026 | Mixed | 1-2 | Cross-cutting | Monitor/Unit |

## Recommended BMAD → TEA Workflow Sequence

1. **TEA Test Design** (`TD`) → produces this handoff document
2. **BMAD Create Epics & Stories** → consumes this handoff, embeds quality requirements
3. **TEA ATDD** (`AT`) → generates acceptance tests per story
4. **BMAD Implementation** → developers implement with test-first guidance
5. **TEA Automate** (`TA`) → generates full test suite
6. **TEA Trace** (`TR`) → validates coverage completeness

**Note for this project:** All 9 epics are already implemented (sprint-status.yaml `done`). The immediate next step is **TEA ATDD** for P0 scenarios and **TEA Automate** for the full suite, then **TEA Trace** to close coverage gaps — the existing test suite (41 files) forms the regression base.

## Phase Transition Quality Gates

| From Phase | To Phase | Gate Criteria |
| ---------- | -------- | ------------- |
| Test Design | Epic/Story Creation | All P0 risks have mitigation strategy (12/12 in architecture doc) |
| Epic/Story Creation | ATDD | Stories have acceptance criteria from test design (P0 scenarios above) |
| ATDD | Implementation | Failing acceptance tests exist for all P0/P1 scenarios |
| Implementation | Test Automation | All acceptance tests pass |
| Test Automation | Release | Trace matrix shows ≥80% coverage of P0/P1 requirements |

**For this project (post-implementation):**

| From Phase | To Phase | Gate Criteria |
| ---------- | -------- | ------------- |
| Test Design | ATDD | Blockers B-001..B-005 resolved; fixtures + harness ready |
| ATDD | Test Automation | P0 acceptance tests written + failing where unimplemented |
| Test Automation | Release | P0 100% pass, P1 ≥95%, R-001 closed, security 100%, 41/41 existing deployment tests green |
