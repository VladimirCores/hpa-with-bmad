# Next Steps — HPDC Project

**Last session:** 2026-07-30
**PRD status:** Finalized (48 FRs, 5 UJs)
**Architecture spine status:** Finalized (13 ADs, 48 FRs mapped, reviewer gate passed)

---

## BMAD Workflow — What Comes Next

### 1. ✅ Architecture Spine (DONE)
**Command:** `bmad-architecture`
**Output:** 13 ADs, 6 data-flow paths, C4 diagrams, interactive HTML deck, solution design doc, ADR decision log, work-split view.

### 2. Epics & Stories (NEXT)
**Command:** `bmad-create-epics-and-stories`
**What it does:** Breaks the 13 architecture work slices into epics and user stories for sprint planning.
**Depends on:** Architecture ✅
**Why first:** Architecture has enough detail (13 ADs, work-split) to drive story creation directly. UX can proceed in parallel.

**Current state:** `output/planning-artifacts/epics.md` now contains:
- FR/NFR/additional-requirement coverage map
- full 9-epic roadmap
- UX-DR1 split across Epic 3 and Epic 7
- Epic 1 stories 1.1–1.5
- Epic 2 stories 2.1–2.10
- Epic 3 stories 3.1–3.13
- project-wide Python 3 scripting rule

**Next session target:** Generate Epic 4 — IoT Device Onboarding, Lifecycle, and Edge Simulation — sequentially into `epics.md`.

**Epic 4 expected stories:**
1. Device provisioning and identity issuance
2. Device lifecycle state machine and registry
3. OTA metadata and update approval workflow
4. Device credential rotation and revocation
5. Device shadow registry and synchronization
6. Offline IoT simulator for local validation
7. Load/simulation validation for onboarding and lifecycle flows

**Validation before moving on:** update `epics.md` frontmatter `stepsCompleted` to `[1, 2, 3]` and confirm all Epic 4 FR/NFR/additional items are covered.

### 3. UX Specifications (PARALLEL OPTION)
**Command:** `bmad-ux`
**What it does:** UX patterns and design specifications for Backstage dashboards and the v2 central hub SPA.
**Depends on:** Architecture ✅ (minimal — MVP UX is Backstage + Grafana, detailed UX deferred to v2)
**Note:** MVP UX scope is small (Backstage plugins, Grafana dashboards). Full SPA UX is v2 deferred.

---

## Key Decisions to Remember

- **Paradigm:** Gateway-Mediated Domain Segregation — Envoy routes as hard domain boundaries
- **Compute:** Serverless-first — KNative (scale-to-zero + Restate SAGAs), SpinKube WASM, Pulsar Functions. No always-on microservices
- **Messaging:** Pulsar primary (MQTT/gRPC, 100K+ RPS) + Kafka secondary (alerts, Spin WASM). Protobuf CommonEnvelope with origin + idempotency_key fields
- **Databases:** CouchDB (docs/CRM/ERP), YugabyteDB 2026.1.0.1 (transactions), ArcadeDB (graph), ClickHouse (telemetry), KeyDB (cache/pubsub/dedup), PostgreSQL (auth only). All functions R/W all DBs
- **Auth:** Casdoor JWT/API-Key at EG, Casbin ext_authz Go gRPC. Three models (RBAC/ReBAC/ABAC), DENY-wins conflict resolution
- **GitOps:** Monorepo + Kustomize overlays (base/dev/prod) + Kargo Freight promotion + Argo CD ApplicationSet sync
- **Air-gapped:** Harbor (local registry + Trivy + Cosign) + Spegel (P2P distribution) + local Git mirrors
- **Observability:** Structured JSON logs, OpenTelemetry auto-instrumentation, VictoriaMetrics cluster, Hubble network observability. Retention: 7d raw / 30d agg / 1y monthly
- **Secrets:** Infisical K8s Operator CSI Driver injection, 90d auto-rotation, per-function service accounts
- **Operations:** Talos Linux 1.13.7 (k8s v1.36.2, containerd 2.2.6), Cilium 1.19.6 (eBPF CNI, kube-proxy replacement, ClusterMesh), Rook-Ceph v1.20.3 (Ceph v20.2.2)
- **SPA:** Backstage MVP (deployed as Backstage plugin), full SPA on CDN deferred to v2
- **Source tree:** `backend/functions/{knative,spin,pulsar}/` for serverless code, `frontend/` for SPA

---

## Open Items (resolved by Architecture)

### Resolved PRD questions
- ✅ Payload format (Q1) → **Protobuf** (AD-5)
- ✅ Pulsar/Kafka split (Q6) → **Dual: Pulsar primary, Kafka secondary** (AD-4)
- ✅ Spin language (Q8) → **Rust primary, JS/Go secondary**
- ✅ Talos version (Q12) → **1.13.7**
- ✅ Delivery phasing → **Work-split: 3 waves, 13 slices** (see WORK-SPLIT.md)
- ✅ Casbin policy schema (Q15) → **Deferred to Sprint 1 story creation** (per-story design)
- ✅ SPA framework (Q9) → **Backstage MVP, full SPA deferred to v2**

### Remaining open (deferred, revisit triggers defined in spine)

| Item | Revisit trigger |
|------|----------------|
| Backup/DR strategy (etcd, Ceph, DBs) | Before production deployment |
| Production region-specific configs (compliance, data locality) | Before production deployment |
| Resource sizing per environment | After MVP baseline established |
| Canary analysis thresholds (error rate, latency p99) | Before production deployment |
| Casbin policy schema format (PERM model, relationship tuples) | Epic 4 story creation |
| Observability storage backend (Ceph vs local vs S3) | When VictoriaMetrics performance tuning begins |
| Pulsar topic partition counts | Per-deployment configuration |
| Central hub SPA framework (React/Vue/Angular) | v2 planning starts |
| Full AI Agent Engine (MCP/A2A) | v2 planning starts |

---

## Artifact Paths

```
output/planning-artifacts/
├── prds/prd-HPDC-2026-07-21/
│   ├── prd.md                       # Finalized PRD (48 FRs, 5 UJs)
│   ├── .memlog.md                   # Decision audit trail (32 entries)
│   └── reviews/                     # PRD review reports
│
└── architecture/architecture-HPDC-2026-07-30/
    ├── ARCHITECTURE-SPINE.md        # Spine (13 ADs, 48 FRs mapped)
    ├── ARCHITECTURE-C4.md           # C4 model (System Context + Container + Component)
    ├── ARCHITECTURE-DECK.html       # Interactive HTML slide deck (12 slides)
    ├── SOLUTION-DESIGN.md           # Full narrative solution design
    ├── ADR-LOG.md                   # ADR decision log (13 ADRs with rationale)
    ├── WORK-SPLIT.md                # Work breakdown (13 slices, 3 waves)
    ├── .memlog.md                   # Decision audit trail (28 entries)
    └── reviews/                     # Reviewer gate reports (3 reports)
```
