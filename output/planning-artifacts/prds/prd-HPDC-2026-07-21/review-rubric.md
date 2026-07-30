# PRD Quality Review — Enterprise GitOps Platform (HPDC)

## Overall verdict

This PRD is unusually well-structured: 48 FRs with testable consequences, 5 named user journeys with protagonists, a glossary that actually gets used, and honest non-goals. The substance is real — dual-engine messaging, triple-database architecture, and GitOps pipeline are specific enough to build from. The primary risk is scope ambition vs. MVP: the Vision and Features describe a multi-region production platform, but MVP is a single dev laptop proof-of-concept. The gap between "what this PRD describes" and "what ships first" is not bridged by a staged delivery plan — it's left for the reader to infer. A secondary risk is that several Open Questions remain genuinely unresolved (Pulsar vs Kafka split, ClickHouse DDL, resource sizing), which blocks story creation.

## Decision-readiness — adequate

The PRD makes real decisions — dual Pulsar/Kafka engines, triple-database architecture, Casbin for all three authZ models, GitOps-mediated air-gap delivery — and states them with conviction. Non-Goals §5 are explicitly named with clear boundaries. The MVP §6 honestly calls out what's deferred with `[NOTE FOR PM]` and `[NON-GOAL for MVP]` tags at the right tension points (§6.2: "multi-region is the core differentiator — v2 planning should start immediately after MVP validation").

However, the Vision §1 and Features §4 describe a production multi-region platform while MVP §6.1 says "all platform components running on a single local dev machine." There is no staged delivery plan or intermediate milestones. A decision-maker reading the Features would assume they're building all 48 FRs simultaneously; only on reaching §6 would they realize most are deferred. The PRD would benefit from a clear "MVP → v2 → production" delivery roadmap that maps FRs to each phase.

Open Questions §8 are genuinely open (not rhetorical), which is good — but 15 open questions at "draft" status means this PRD is not yet decision-ready for implementation kickoff. Questions 1 (Pulsar payload format), 6 (Pulsar vs Kafka split), and 14 (canary analysis thresholds) are blockers for story creation.

### Findings

- **high** No delivery phasing across FRs (§4 vs §6) — 48 FRs described at feature-complete level, MVP §6.1 lists in-scope items but doesn't map which FRs ship when. *Fix:* Add a delivery matrix or phase tags to each FR (e.g., `[MVP]`, `[v2]`, `[prod]`).
- **medium** 15 Open Questions remain unresolved (§8) — several block story creation (Q1 payload format, Q6 engine split, Q14 canary thresholds). *Fix:* Resolve or defer to architecture phase with explicit owners.
- **medium** Counter-metrics are thin (§7) — only SM-C1 and SM-C2; no counter-metrics for deployment automation (SM-4) or security evaluation latency (SM-7). *Fix:* Add counter-metrics for remaining primary/secondary metrics.

## Substance over theater — strong

This PRD has almost no theater. The 5 user journeys (§2.3) each have named protagonists with specific scenarios and edge cases — Marcus PXE-booting servers, Aisha tripping on drone geofence violations, Raj scaffolding a processor, Elena managing ReBAC tuples, David reviewing quarterly metrics. These are concrete enough to derive stories from.

NFRs are product-specific with numbers: 100K RPS, p99 < 100ms, 2GB RSS ceiling, 50ms cache read, < 15ms authZ evaluation. No "system must be scalable" platitudes. The glossary (§3) contains 40+ terms with platform-specific definitions, not boilerplate.

The Vision (§1) is specific to the point of over-engineering: it names exact technologies (Pulsar, Kafka, Talos, Cilium, Rook-Ceph, Spegel, Kargo) and exact patterns (Spin WASM, Pulsar Functions, Sync Waves). This could be read as premature technology lock-in — but in context of a platform engineering PRD with a reference architecture (with-gsd/), it reads as earned specificity.

### Findings

- **low** One glossary entry is duplicated (Pulsar appears twice: §3 lines 113-114 and 121-122). *Fix:* Deduplicate.
- **low** One glossary entry duplicated (Pulsar Functions: §3 lines 114-115 and 122). *Fix:* Deduplicate.

## Strategic coherence — adequate

The thesis is clear: "a security platform for IoT telemetry with GitOps-driven progressive delivery on bare-metal multi-cluster." The features serve this arc — ingestion → processing → alerting → deployment → security — in a logical pipeline. The GitOps delivery pipeline (§4.5) is the structural backbone that connects all capabilities.

The PRD's strategic weakness is the gap between Vision (production multi-region platform) and MVP (single dev laptop PoC). The Vision says "scales from a single developer laptop to hundreds of clusters across regions" — but MVP is only the first 5% of that. Success Metrics §7 validate the PoC (100K RPS, 2-second processing, 30-minute bootstrap) but don't validate the strategic thesis (multi-region sovereignty, AI agent orchestration, air-gapped delivery). There are no SMs for the things that would prove the platform thesis works at scale.

Counter-metrics SM-C1 (feature velocity) and SM-C2 (alert false positive rate) are well-conceived but cover only 2 of 8 metrics.

### Findings

- **high** Success Metrics validate MVP only, not the strategic thesis — no SMs for multi-region, air-gapped delivery, AI agent orchestration, or Cross-region visibility. *Fix:* Add deferred SMs tagged `[v2]` or `[prod]` that validate the full thesis.
- **medium** MVP scope kind is unclear — is this problem-solving (PoC validates the architecture), experience (demos a user flow), or platform (proves deployability)? The PRD mixes all three. *Fix:* Explicitly state the MVP's primary validation goal.

## Done-ness clarity — strong

This is the PRD's strongest dimension. Every FR has 2-5 testable consequences with specific numbers. Examples:

- FR-1: "System accepts a valid MQTT publish and produces a message on the internal Pulsar topic within 50ms."
- FR-10: "System transitions alert state only through valid paths (no skip from initial to closed)."
- FR-41: "System evaluates role-based permissions in < 5ms (p99)."
- FR-31: "System reduces image pull time by > 50% during multi-pod scale-up events."

There is no "system handles X gracefully" or "reasonable performance" anywhere. Every consequence is a verifiable condition. SMs cross-reference FRs explicitly (e.g., "SM-1 validates FR-1, FR-2, FR-3").

The few soft spots are in §4.11 AI Agent Engine — FR-46 consequences include "System constrains LLM output to actionable recommendations" (no threshold for what constitutes actionable) and FR-48 consequences include "System prevents unauthorized agent impersonation" (no testable condition specified).

### Findings

- **medium** AI Agent Engine FRs lack testable thresholds (§4.11 FR-46, FR-48) — "actionable recommendations" and "unauthorized impersonation" have no measurable bounds. *Fix:* Add latency, format, or rejection-rate thresholds consistent with other FRs.
- **low** FR-17 Backstage consequences don't include a deployment time SLA — all other infrastructure FRs have latency or time bounds. *Fix:* Add "System deploys Backstage within X minutes of GitOps bootstrap."

## Scope honesty — strong

The PRD is refreshingly honest about what's not included. Non-Goals §5 names 7 explicit exclusions with rationale. MVP §6.2 lists 10 deferred items with `[NOTE FOR PM]` and `[NON-GOAL for MVP]` tags at the right tension points. The Assumptions Index (§9) surfaces 13 inline assumptions for explicit confirmation.

The `[ASSUMPTION: ...]` tags are placed inline at the exact point of inference (e.g., §4.1 FR-2: "ASSUMPTION: JSON envelope with raw payload field is the normalization format"), and all appear in the Assumptions Index. This is well-executed traceability.

Open Questions §8 are genuinely open — they don't have answers hidden in the next sentence. Q10 (Backup/DR strategy) and Q11 (Resource sizing) are particularly honest admissions of missing scope.

### Findings

- **medium** Open Questions density is high (15) for a PRD with MVP §6.1 listing 13 in-scope items — nearly 1.2 open questions per in-scope item. Some should be resolved before story creation. *Fix:* Prioritize Q1, Q6, Q14 as blockers; defer others to architecture phase.
- **low** No `[NOTE FOR PM]` on Open Questions that are architecture-deciding (Q3 KeyDB topology, Q5 YugabyteDB RF). *Fix:* Add PM callouts on decisions that affect cost or timeline.

## Downstream usability — adequate

The glossary (§3) is present and terms are used consistently across FRs, UJs, and SM definitions. FR IDs are contiguous (FR-1 through FR-48, no gaps). UJ IDs are contiguous (UJ-1 through UJ-5). SM IDs are contiguous (SM-1 through SM-8, SM-C1, SM-C2). Cross-references resolve: "§4.10 Security" is referenced from FR-14, FR-16, FR-41, FR-42, FR-43 and all point to the correct section.

Each UJ has a named protagonist (Marcus, Aisha, Raj, Elena, David) carrying context inline. No floating UJs.

The weakness is that FRs don't include UJ traceability — FR-1 says "Realizes UJ-1" but most FRs have no UJ linkage. For downstream story creation, knowing which UJ an FR serves would help prioritize.

### Findings

- **medium** Most FRs lack UJ traceability — only FR-1 explicitly references UJ-1; FR-9 through FR-48 have no UJ linkage. *Fix:* Add "Realizes UJ-X" to each FR for traceability.
- **low** OpenAPI spec location mentioned as `specs/` (§4.9 FR-39) but no actual file path or repo structure defined. *Fix:* Add repo structure appendix or reference.

## Shape fit — adequate

This is a platform engineering PRD with 4 stakeholder personas, 5 user journeys, and 48 FRs. The shape matches: multi-stakeholder B2B platform with meaningful UX (central hub SPA, Backstage, Grafana). UJs with named protagonists are load-bearing here — they ground abstract capabilities in real operator workflows.

The PRD is slightly over-formalized for an MVP that's "all platform components on a single dev laptop." 48 FRs is a lot for a PoC. The Air-gapped Delivery (§4.7) and Multi-region Federation (§4.8) sections describe capabilities explicitly out of MVP scope (§6.2), yet they carry full FRs with testable consequences. This creates confusion about what the PRD is actually asking to be built first.

The shape would be improved by tagging each feature section with `[MVP]` or `[Deferred]` to make the build order unambiguous.

### Findings

- **medium** Feature sections §4.7 (Air-gapped) and §4.8 (Multi-region) carry full FRs despite being explicitly deferred in §6.2 — creates ambiguity about build priority. *Fix:* Tag feature sections with delivery phase markers.
- **low** 4 personas (§2.1) is at the upper bound — all drive decisions (UJ-4 for Elena, UJ-5 for David), so this is justified, but consider whether Platform Administrator and Platform Engineer are distinct enough. *Fix:* Merge if their journeys overlap; keep if they diverge on access patterns.

## Mechanical notes

- **Glossary drift:** "Pulsar" appears as two separate entries in §3 (lines 113-114 and 121-122) with near-identical text. "Pulsar Functions" also duplicated (lines 114-115 and 122). "Kafka" has its own entry (line 123) but is also referenced as secondary engine in §4.1 description. "Zanzibar" and "Google Zanzibar" are separate entries pointing to each other — redundant but not broken.
- **ID continuity:** FR-1 through FR-48 are contiguous with no gaps or duplicates. UJ-1 through UJ-5 contiguous. SM-1 through SM-8 contiguous. SM-C1, SM-C2 appended cleanly. No broken cross-references found.
- **Assumptions Index roundtrip:** All 13 `[ASSUMPTION]` tags in the body appear in §9. Index entries all reference valid § locations. No orphaned index entries or untagged inline assumptions found.
- **UJ protagonist naming:** All 5 UJs have named protagonists (Marcus, Aisha, Raj, Elena, David) with role context inline. No floating UJs.
- **Required sections present:** Vision, Target User (with JTBD), Glossary, Features (with FRs), Non-Goals, MVP Scope, Success Metrics, Open Questions, Assumptions Index — all present and substantive.
- **Minor:** Section numbering jumps from §4.11 (AI Agent Engine) to §5 (Non-Goals) — no §4.12. Not a problem but breaks the pattern of 11 subsections.
