# Next Steps — HPDC Project

**Last session:** 2026-08-11
**PRD status:** Finalized (48 FRs, 5 UJs)
**Architecture spine status:** Finalized (13 ADs, 48 FRs mapped, reviewer gate passed)
**Delivery status:** Epics 1–10 implemented + retrospective'd (sweep committed), ATDD green phase (143 passed, 7 skipped), B-002/B-003/B-005 harnesses built
**Outstanding work:** 23 retro action items + live-cluster verification register (10 entries) + setup/provisioning completion

---

## Current State (2026-08-11)

- **Epics 1–10:** all story-tracked and implemented; all 10 retrospectives done (`epic-{1..10}-retrospective: done` in `output/implementation-artifacts/sprint-status.yaml`).
- **Retro sweep committed:** `efa3372` — consolidated 23-item action table at `output/implementation-artifacts/action-items-2026-08-11.md`.
- **Setup fix committed:** `3cb2605` — `scripts/startup.dev.py --offline --dry-run` completes; `scripts/gitops/bootstrap_talos_dev.py` tolerates unreadable root-owned `output/talos/talosconfig`.
- **Test suite:** `pytest tests/` → **143 passed, 7 skipped**. The 7 skips are RED-PHASE ATDD journeys gated on a live cluster (P0-008 × 4, P0-023 soak, P0-025/026 UI).
- **Live-cluster register materialized:** `output/test-artifacts/live-cluster-verification-register.md` (REG-01..REG-10 + unlock path + related RED scaffolds).
- **B-002/B-003/B-005 harnesses built (offline contracts):** identity fixtures (`tests/atdd/support/fixtures.py` + `test_identity_fixtures.py`, 12 tests), consumer harness (`tests/atdd/support/consumer_harness.py` + `test_consumer_harness.py`, 12 tests), k6 load harness (`LoadHarness` in `hpdc_test_client.py` + `test_load_harness.py`, 7 tests).

---

## What's Left to Complete the Work

### A. Record Reconciliation (John) — 7 items

Backfill/clean the audit-trail drift so the plan, tracker, and story files agree:

1. **#6** Clarify story 9-3 in `epics.md`: mark `provide-full-llm-decision-support-engine` explicitly deferred/not-implemented.
2. **#14** Backfill a minimal 5-2 story record or document the gap (done in sprint-status, no story file).
3. **#16** Epic 4: reconcile 4-3..4-9 (no story files, delivered via consolidated scaffold + epic4→platform rename); clear 4-2 unchecked tasks; fix stale paths in `epic-4-offline-gitops-scaffold.md`.
4. **#18** Epic 3: reconcile 3-13 (Grafana/Hubble UI done but untracked + self-contradictory status); decide add-to-tracker vs mark deferred.
5. **#20** Epic 2: deepen shallow records 2-1, 2-3..2-10 (backfill baseline commits; add review-findings depth for 2-4/2-6/2-7/2-8).
6. **#22** Epic 1: reconcile story 1-6 (Harbor) into epics.md (delivered, reused by 2-1, absent from story list).
7. **#23** Epic 1: pin baseline commits on 1-1..1-6.

**Done when:** every `done` story in sprint-status resolves to a real story file with a baseline commit; epics.md story lists match the tracker.

### B. Live-Cluster Verification Register (Murat/Winston/Amelia) — items 3, 4, 8, 10, 12

Materialized in `output/test-artifacts/live-cluster-verification-register.md`. All 10 REG entries are gated on live infrastructure — **none can execute until a cluster exists**. Order of attack:

1. ✅ **B-002 identity fixtures** — BUILT (unlock-path step 1 done).
2. ✅ **B-003 consumer harness** — BUILT (2026-08-11, offline contract): `pulsar_consumer_harness`/`kafka_consumer_harness` + `PulsarConsumerHarness`/`KafkaConsumerHarness` in `tests/atdd/support/consumer_harness.py` (message-arrival + latency asserts, remote HTTP + local NDJSON backends), 12 tests. Unlock-path step 2 done.
3. ✅ **B-005 k6 load harness** — BUILT (2026-08-11, offline contract): `LoadHarness` + `SoakReport` in `hpdc_test_client.py` (k6 soak script, NFR1/NFR3 thresholds, local sim fallback), 7 tests. Unlock-path step 5 done.
4. **B-001 live test cluster** — provision Talos (`admin@hpa-dev`); this is the gating prerequisite for REG-01/02/04..10 and the P0-008 journey bodies.
5. **B-004 multi-region topology** — 2 clusters + ClusterMesh + WireGuard → REG-03 (cross-cluster discovery/encryption).

**Concrete next executable step:** provision a live Talos cluster (B-001) — the only blocker left in the harness/unlock chain. Once it exists: wire the B-003 harness remote URL, run k6 against the gateway, and execute REG-01/02/04..10 + the P0-008 journey bodies. P0-023 full soak needs k6 binary + cluster.

### C. Parity Guards & Route-Topology (Winston/Amelia) — items 1, 7, 11, 19, 21, 5

1. **#1/#11/#19** Route-topology / native-auth consolidation: resolve the `'/'` catch-all ambiguity on the two native-auth UI routes (`hpdc-edge-observability-ui-routes`, `hpdc-edge-tool-ui-routes`) — drop `/` from one or give every UI host a dedicated hostname route. Root family traced through 7-5 and 3-12/3-13.
2. **#7** Record agent-engine parity guard (kustomize-to-installer equality for agent-engine shared config).
3. **#21** Document the harbor parsed-equality drift guard (10-2) as the canonical cross-system parity-guard template, owned at Epic 2.
4. **#5** Codify the in-memory mutation-probe technique into the checkpoint-review workflow.

### D. Remaining Offline Code Work (Murat) — items 2, 9

1. **#2** Extend secret-scan `_base_yamls()` to also scan overlay kustomizations (P0-022 base-only gap).
2. **#9** Add a no-replication guard: regional-sovereignty validation asserts absence-of-config (no cross-region replication anywhere in the tree).

### E. Heading Normalization (Winston) — item 17

Normalize Epics 1–4 headings in `epics.md` from `###` (h3 under `## Epic List`, L185) to `##` (h2), matching Epics 5–10, so machine-driven discovery/retro sweeps find them.

---

## Suggested Immediate Order

1. **B-001 live cluster provision** — the only remaining harness/unlock-path blocker; all offline harness work (B-002/B-003/B-005) is done. Wire the B-003 remote URL + run k6 against the gateway once the cluster exists, then execute REG-01/02/04..10 and the P0-008 journey bodies.
2. **E (heading normalization)** — small, mechanical, unblocks machine-driven discovery for everything else.
3. **D (#2, #9)** — offline test-code hardening, immediately verifiable.
4. **C (#1/#11/#19)** — route-topology resolution; manifest-only, offline, closes the catch-all family.
5. **A (record reconciliation)** — doc backfill; do after headings so the reconciled records are discoverable.
6. **C (#7, #21, #5)** — parity-guard codification (docs).

---

## Key Decisions to Remember

- **Paradigm:** Gateway-Mediated Domain Segregation — Envoy routes as hard domain boundaries
- **Compute:** Serverless-first — KNative (scale-to-zero + Restate SAGAs), SpinKube WASM, Pulsar Functions. No always-on microservices
- **Messaging:** Pulsar primary (MQTT/gRPC, 100K+ RPS) + Kafka secondary (alerts, Spin WASM). Protobuf CommonEnvelope with origin + idempotency_key fields
- **Databases:** CouchDB (docs/CRM/ERP), YugabyteDB 2026.1.0.1 (transactions), ArcadeDB (graph), ClickHouse (telemetry), KeyDB (cache/pubsub/dedup), PostgreSQL (auth only). All functions R/W all DBs
- **Auth:** Casdoor JWT/API-Key at EG, Casbin ext_authz Go gRPC. Three models (RBAC/ReBAC/ABAC), DENY-wins conflict resolution. JWT iss `https://casdoor.hpdc.local`, aud `hpdc-graphql-gateway`
- **GitOps:** Monorepo + Kustomize overlays (base/dev/prod) + Kargo Freight promotion + Argo CD ApplicationSet sync
- **Air-gapped:** Harbor (local registry + Trivy + Cosign) + Spegel (P2P distribution) + local Git mirrors
- **Observability:** Structured JSON logs, OpenTelemetry auto-instrumentation, VictoriaMetrics cluster, Hubble network observability. Retention: 7d raw / 30d agg / 1y monthly
- **Secrets:** Infisical K8s Operator CSI Driver injection, 90d auto-rotation, per-function service accounts. InfisicalSecret CRD does NOT reconcile yet (no operator — REG-01)
- **Operations:** Talos Linux 1.13.7 (k8s v1.36.2, containerd 2.2.6), Cilium 1.19.6 (eBPF CNI, kube-proxy replacement, ClusterMesh), Rook-Ceph v1.20.3 (Ceph v20.2.2)
- **SPA:** Backstage MVP (deployed as Backstage plugin), full SPA on CDN deferred to v2
- **Source tree:** `backend/functions/{knative,spin,pulsar}/` for serverless code, `frontend/` for SPA

---

## Open Items (carried from planning)

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
| Casbin policy schema format (PERM model, relationship tuples) | Per-story design |
| Observability storage backend (Ceph vs local vs S3) | When VictoriaMetrics performance tuning begins |
| Pulsar topic partition counts | Per-deployment configuration |
| Central hub SPA framework (React/Vue/Angular) | v2 planning starts |
| Full AI Agent Engine (MCP/A2A) | v2 planning starts |

---

## Artifact Paths

```
output/
├── planning-artifacts/
│   ├── prds/prd-HPDC-2026-07-21/prd.md          # Finalized PRD (48 FRs, 5 UJs)
│   ├── architecture/architecture-HPDC-2026-07-30/ # Spine, C4, deck, solution design, ADR log
│   └── epics.md                                  # Epic 1–10 story lists (heading fix pending, item 17)
│
├── implementation-artifacts/
│   ├── sprint-status.yaml                        # All epics done; 23 action items tracked
│   ├── action-items-2026-08-11.md                # Consolidated retro-sweep action table
│   ├── epic-{1..10}-retro-2026-08-11.md          # Retrospective docs
│   └── deferred-work.md                          # Still-open ledger (10-1 items, catch-all, etc.)
│
└── test-artifacts/
    ├── test-design/test-design-qa.md             # P0 register + blockers B-001..B-005
    ├── atdd-progress.md                          # Green-phase history
    ├── atdd-checklist-hpdc-p0-system.md          # P0 checklist (fixtures table updated)
    └── live-cluster-verification-register.md     # REG-01..REG-10 + unlock path (NEW 2026-08-11)
```

**Test code:** `tests/atdd/support/fixtures.py` (B-002 identity fixtures), `tests/atdd/api/`, `tests/atdd/e2e/`, `hpdc_test_client.py` (repo-root harness, 39 green API tests).
