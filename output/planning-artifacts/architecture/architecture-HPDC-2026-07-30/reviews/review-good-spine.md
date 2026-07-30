# Good-Spine Review: HPDC Architecture Spine

**Reviewer:** Rubric Walker  
**Date:** 2026-07-30  
**Spine:** `ARCHITECTURE-SPINE.md`  
**Sources:** PRD (`prd.md`), Memlog (`.memlog.md`)  
**Checklist:** Good-spine checklist (7 criteria)  

---

## Verdict: CONDITIONAL

The spine is structurally sound with a clear paradigm and strong AD coverage for most domains, but falls short on observability as a silent dimension, has a discrete version-verification failure for YugabyteDB, and lacks architectural governance for backpressure, secrets, and the Restate-vs-Argo boundary — all fixable with targeted amendments.

---

## 1. Divergence-point coverage

**Rating: 7/10 — Good coverage but three AD-sized gaps remain.**

The 11 ADs address the majority of real divergence points. Each AD has an enforceable Rule that clearly prevents its stated divergence. The domain-per-route segregation (AD-2), serverless-first compute (AD-3), event-mesh integration (AD-4), and GitOps-only delivery (AD-9) are particularly well-structured.

**Findings:**

**F-1 (Critical) — Observability has no governing AD.** The capability map at line 364 explicitly shows `—` for the "Governed by" column of FR-25..FR-29 (VictoriaMetrics, vmlog, OpenTelemetry, Grafana, Hubble). This means the entire observability dimension — metric-naming conventions, log format, trace sampling policy, dashboard ownership, retention governance — has no architectural invariant. Two teams can independently choose different logging schemas or tracing implementations without violating any AD. This is a whole dimension left silent.

*Recommendation:* Add AD-12 covering observability invariants: structured JSON logging to stdout (in Consistency Conventions but not an AD), metric naming convention, trace sampling minimum requirements, Opentelemetry Collector as sole trace ingress, retention-floor per environment.

**F-2 (Significant) — Backpressure (FR-4) not explicitly governed.** FR-4 requires back-pressure management with exponential backoff, message dropping with metric increment, and memory ceilings. The capability map groups FR-1..FR-4 under AD-2/AD-4/AD-5, but none of those AD rules mention backpressure. A team could implement backpressure differently from another, or neglect it entirely, without violating an AD.

*Recommendation:* Extend AD-4 rule to state: "Pulsar ingestion topology must implement producer-side backpressure with configurable consumer-lag thresholds, message-dropping with `ingestion_dropped_total` counter, and per-pod memory ceiling of 2GB RSS."

**F-3 (Minor) — Secrets management lacks AD governance.** FR-44 (Infisical) appears in the Stack but has no AD rule. The Consistency Conventions mention never using env vars for sensitive data, but conventions lack the binding force of an AD. A developer could inject secrets directly as Kubernetes Secrets without Infisical, or use a different secrets tool, without violating any AD.

*Recommendation:* Add a brief rule to AD-9 (or a new AD-12 subsection): "All secrets at rest and in transit use Infisical Kubernetes Operator (InfisicalSecret CRD). No raw Kubernetes Secrets for sensitive values. Secret rotation must not require pod restart."

---

## 2. Deferred discipline

**Rating: 8/10 — Generally well-disciplined, one boundary issue.**

The Deferred section (lines 442-454) lists 11 items. Most are genuine future decisions: SPA framework choice, full AI agent engine, Hasura federation, production region configs, backup/DR, resource sizing, canary thresholds, Casbin policy format, pulsar partition counts, observability storage backend.

**Finding:**

**F-4 (Minor) — Argo Workflows vs KNative+Restate boundary is an undecided architectural question, not a genuine deferral.** The Deferred entry says "exact split depends on use case" — but this is precisely the kind of ambiguity that lets two units diverge. A workflow developer might implement a SAGA in Argo Workflows while another uses Restate for the same pattern, creating inconsistency.

*Recommendation:* Either add an AD rule drawing the boundary (e.g., "Restate for stateful event-sourced workflows with persistence requirements; Argo Workflows for CI/build/deploy pipelines and batch compute" — which AD-3 almost says but not quite), or acknowledge the divergence risk and note a revisit trigger tied to the first story that encounters the overlap.

---

## 3. Version verification

**Rating: 5/10 — Critical failure on YugabyteDB; 14 of 25 entries not pinned.**

**Finding:**

**F-5 (Critical) — YugabyteDB version mismatch: spine vs memlog.** The spine (line 234) lists `YugabyteDB | 2025.2 LTS`. The memlog (line 21) records the decision as `YugabyteDB v2026.1.0.1`. The spine asserts a version that contradicts what the architecture session actually decided. This is a verification failure.

**F-6 (Significant) — 14 of 25 components listed as "(latest stable)".** Kafka, KeyDB, Argo CD, Argo Rollouts, Argo Events, Argo Workflows, Backstage, KNative, Restate, Casdoor, Casbin, Hasura, Infisical, Harbor, Spegel — all use "(latest stable)" instead of a pinned version. The spine header says "Web-verified at time of writing" (line 222) which is false for these entries since "(latest stable)" is not a verifiable reference. In practice, `latest` will drift over time, potentially introducing incompatibilities.

*Recommendation:* Pin all components to specific semantic versions. If the exact version is TBD, state a minimum-required version range rather than "latest stable." For the YugabyteDB mismatch, correct to `2026.1.0.1` (per memlog).

---

## 4. Brownfield fidelity

**N/A — Greenfield project. Skipped.**

---

## 5. PRD coverage

**Rating: 8/10 — All 48 FRs mapped in capability table, but three have shallow or absent AD governance.**

The capability → architecture map (lines 356-370) covers every FR and UJ. The `binds:` header in the spine frontmatter lists `[FR-1..FR-48, UJ-1..UJ-5]` — correct cardinality.

| FR Group | Coverage | Notes |
|----------|----------|-------|
| FR-1..FR-4 (Telemetry) | AD-2, AD-4, AD-5 | FR-4 backpressure not governed (F-2) |
| FR-5..FR-8 (Processing) | AD-2, AD-3, AD-4, AD-6 | Full coverage |
| FR-9..FR-12 (Alerts) | AD-2, AD-3, AD-4 | Alert state machine (FR-10) covered by Restate |
| FR-13..FR-16 (Entities) | AD-2, AD-6 | Full coverage |
| FR-17..FR-21 (GitOps) | AD-9 | Full coverage |
| FR-22..FR-24 (Substrate) | AD-7, AD-8 | FR-22 (Talos) has no AD but is in structural seed |
| FR-25..FR-29 (Observability) | — | **No governing AD** (F-1) |
| FR-30..FR-32 (Air-gap) | AD-10 | Full coverage |
| FR-33..FR-35 (Multi-region) | AD-11 | Full coverage |
| FR-36..FR-39 (Gateway) | AD-1, AD-2 | Full coverage |
| FR-40..FR-45 (Security) | AD-1, AD-2, AD-8 | FR-44 (Infisical) has no AD (F-3) |
| FR-46..FR-48 (AI Agent) | AD-3 | Deferred per PRD non-goals — correct |

---

## 6. Operational envelope

**Rating: 6/10 — Deployment and infra provider are well-covered; observability and upgrade strategy are silent.**

Dimensions addressed:
- **Deployment environments & topology**: AD-9 + structural seed provides dev and production topologies with clear environment naming. ✓
- **Infrastructure/provider strategy**: Talos + bare-metal (structural seed), Ceph RBD (AD-7), Cilium ClusterMesh (AD-11), air-gapped (AD-10). ✓
- **Network strategy**: Cilium eBPF, mTLS (AD-8), WireGuard VPN (AD-11). ✓
- **Storage strategy**: Ceph RBD for all stateful workloads (AD-7). ✓
- **Secrets management**: Infisical in Stack but no AD rule (F-3). 
- **Observability**: FR-25..FR-29 listed in capability map with no governing AD (F-1). No architectural invariants for metric collection, log shipping, trace sampling, dashboard ownership, or retention enforcement.
- **Backup/DR**: Explicitly deferred — acceptable for v1 MVP.
- **Upgrade strategy**: Not mentioned anywhere in the spine. For a platform with 20+ components, the absence of an upgrade/in-place-update invariant is notable. Not a blocker for feature-altitude spine but worth flagging.

**Finding:**

**F-7 (Minor) — Component upgrade strategy not addressed.** The spine correctly notes "update in place as the project evolves" in the Stack header, but there is no architectural invariant governing how upgrades happen (e.g., "all component upgrades follow the GitOps pipeline via Kargo+Argo CD; no in-place Helm upgrades outside the pipeline"). Without this, teams may upgrade components imperatively, creating drift.

---

## 7. Paradigm clarity

**Rating: 9/10 — Named, coherent, and consistently governs the ADs.**

The paradigm **"Gateway-Mediated Domain Segregation"** is clearly named and described (lines 21-22). The three pillars — Envoy routes as hard domain boundaries, event-mesh as integration fabric, serverless-first compute — directly map to AD-1/AD-2, AD-4, and AD-3 respectively. The remaining ADs (storage, security, delivery, multi-region) are substrate concerns that operate under the paradigm without contradicting it.

The example flow (lines 41-53) concretely illustrates the paradigm in action, which is excellent for downstream consumers.

No findings. This is the spine's strongest dimension.

---

## Summary of Findings

| # | Severity | Criterion | Finding |
|---|----------|-----------|---------|
| F-1 | Critical | 1. Divergence / 5. PRD / 6. Ops | Observability (FR-25..FR-29) has no governing AD — silent dimension |
| F-2 | Significant | 1. Divergence / 5. PRD | FR-4 backpressure not covered by any AD rule |
| F-3 | Minor | 1. Divergence / 5. PRD | FR-44 secrets management (Infisical) has no AD rule |
| F-4 | Minor | 2. Deferred | Restate vs Argo Workflows boundary is an undecided architectural question, not a genuine deferral |
| F-5 | Critical | 3. Version | YugabyteDB version mismatch: spine says "2025.2 LTS", memlog says "2026.1.0.1" |
| F-6 | Significant | 3. Version | 14 of 25 components use "(latest stable)" — not verifiable |
| F-7 | Minor | 6. Operations | Upgrade strategy for platform components not addressed |

---

## Gate Decision

**CONDITIONAL** — the spine is accepted for downstream work provided that:

1. **F-5 must be corrected immediately** (YugabyteDB version) — this is a concrete data error.
2. **F-1 (observability AD) should be resolved before the first story involving telemetry storage, log shipping, or dashboard creation reaches implementation.** Without it, two stories could independently set different observability conventions.
3. **F-2, F-3, F-4, F-6, F-7** are advisory and can be addressed during story creation or in a spine amendment after MVP baseline.
