# Next Steps — HPDC Project

**Last session:** 2026-07-21
**PRD status:** Finalized (48 FRs, 5 UJs, 55 glossary terms, 15 open questions, 13 assumptions)

---

## BMAD Workflow — What Comes Next

### 1. Architecture Spine
**Command:** `bmad-architecture`
**What it does:** Produces the architecture — a lean spine of invariants that keeps everything built from it consistent. Projects the PRD into a technical architecture.
**Why next:** Architecture feeds directly into UX design and story creation.

### 2. UX Specifications
**Command:** `bmad-ux`
**What it does:** Plans UX patterns and design specifications for the central hub SPA and Backstage dashboards.
**Depends on:** Architecture (§3 of BMAD workflow)

### 3. Epics & Stories
**Command:** `bmad-create-epics-and-stories`
**What it does:** Breaks requirements into epics and user stories for sprint planning.
**Depends on:** Architecture + UX

---

## Key Decisions to Remember

- **Clean-sheet design** — uses with-gsd/ patterns as reference/examples only, NOT extending
- **v1 MVP = POC on local dev machine** — all components running, 100K+ RPS
- **Dual-engine messaging** — Pulsar (primary: MQTT/gRPC) + Kafka (secondary: alerts, Spin WASM)
- **Triple database** — CouchDB (docs) + ArcadeDB (graph) + YugabyteDB (relational)
- **GitOps delivery** — Kargo + Argo (CD, Rollouts, Events, Workflows) + Backstage
- **Dev provisioning** — `talosctl cluster create` with QEMU backend (cross-platform)
- **Air-gapped** — Harbor + Spegel P2P + local Git mirrors, always GitOps-mediated

---

## Open Items (deferred to Architecture)

1. **Delivery phasing** — FRs don't map to build order yet (reviewer high finding #1)
2. **15 Open Questions** — several block story creation (reviewer high finding #2)
   - **Decisions needed:** Payload format (Q1), Pulsar/Kafka split (Q6), SPA framework (Q9)
   - **Implementation (defer to arch):** ClickHouse DDL (Q2), KeyDB topology (Q3), CouchDB size (Q4), YugabyteDB RF (Q5), Harbor backend (Q7), Spin language (Q8), Talos version (Q12)
   - **Must resolve before sprint 1:** Backup/DR (Q10), Resource sizing (Q11), Region configs (Q13), Canary thresholds (Q14), Casbin policy schema (Q15)

---

## Artifact Paths

```
output/planning-artifacts/prds/prd-HPDC-2026-07-21/
├── prd.md                  # Finalized PRD
├── .memlog.md              # Decision audit trail (32 entries)
├── review-rubric.md        # Quality rubric review
├── review-structure.md     # Structural editorial review
├── reconcile-source-docs.md # Source document reconciliation
└── reconcile-with-gsd.md   # with-gsd/ pattern reconciliation
```
