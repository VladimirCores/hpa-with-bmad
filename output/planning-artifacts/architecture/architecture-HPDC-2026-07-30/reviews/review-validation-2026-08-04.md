# Architecture Spine Validation Report — HPDC

**Date:** 2026-08-04  
**Target:** `output/planning-artifacts/architecture/architecture-HPDC-2026-07-30/ARCHITECTURE-SPINE.md`  
**Intent:** Validate existing architecture spine without changing it.

---

## Gate Verdict

**Conditional Pass.** The spine is usable for downstream implementation planning, but it should be amended before development starts if internal trust boundaries and operational upgrade invariants must be treated as hard requirements.

---

## Deterministic Review

Command:

```text
uv run /home/cores/Documents/Projects/Study/HPA/with-bmad/.agents/skills/bmad-architecture/scripts/lint_spine.py --workspace /home/cores/Documents/Projects/Study/HPA/with-bmad/output/planning-artifacts/architecture/architecture-HPDC-2026-07-30
```

Result:

- **Pass**
- **Total findings:** 0
- **Mechanical issues:** none detected

Checks passed:

- No placeholder content.
- No duplicate `AD` IDs.
- Each `AD` has `Binds`, `Prevents`, and `Rule`.
- Stack versions are present.

---

## Coverage Review

### Requirements Coverage

The spine binds all PRD requirements:

```text
FR-1..FR-48
UJ-1..UJ-5
```

The capability map covers all major architecture domains:

- Telemetry ingestion
- Stream processing
- Alert management
- Entity management
- GitOps delivery
- Kubernetes substrate
- Observability
- Air-gapped delivery
- Multi-region federation
- API gateway
- Security
- AI agent engine
- Auth routes

### Invariants

The spine currently defines 13 architecture decisions:

- AD-1: Envoy Gateway as exclusive ingress boundary
- AD-2: Domain-per-route segregation
- AD-3: Serverless-first compute
- AD-4: Event-mesh as integration fabric
- AD-5: Protobuf normalized envelope
- AD-6: Database ownership boundaries
- AD-7: Ceph for all persistent state
- AD-8: mTLS for inter-service communication
- AD-9: GitOps-only delivery
- AD-10: Air-gapped delivery
- AD-11: Multi-region data sovereignty
- AD-12: Observability
- AD-13: Centralized secrets management

### Structural Seed

The spine includes:

- Dev topology
- Production topology
- Monorepo source tree
- Stack table
- Testing and quality model
- Deferred decisions

---

## Semantic Findings

### Finding 1 — Internal Function Authorization Is Not Fully Governed

**Severity:** High  
**Affected areas:** AD-2, AD-8, Consistency Conventions

The spine governs external ingress through Envoy Gateway and internal transport security through Cilium mTLS. However, it does not fully define authorization for function-to-function calls.

Current rule allows KNative functions to call KNative functions or SpinApps over HTTP for stateful operations. That creates a trust boundary gap: mTLS authenticates transport, but does not enforce per-callee authorization.

**Recommendation:** Add an invariant defining whether function-to-function calls must go through:

1. event-mesh only,
2. local sidecar/envoy mediation with SPIFFE identity authorization, or
3. explicit per-function allow lists.

**Recommended action:** Amend before implementation if internal authN/authZ is considered a hard requirement.

---

### Finding 2 — Database Access Scope Is Broad

**Severity:** High  
**Affected areas:** AD-6

AD-6 states that all serverless functions have read/write access to all data stores. This is operationally convenient but weakens the domain segregation model.

A compromised telemetry function, alert function, or entity function could access unrelated authoritative stores directly.

**Recommendation:** Add per-function database access scoping:

- per-deployment credentials,
- declared read/write scope,
- approved policy matrix,
- minimum privilege enforcement,
- KeyDB key namespace conventions.

**Recommended action:** Amend before production readiness; optional for MVP if threat model treats functions as trusted.

---

### Finding 3 — Change Feed Loop Detection Is Partially Covered

**Severity:** Medium  
**Affected areas:** AD-4, AD-5

AD-5 defines `origin` and `idempotency_key` for message envelopes. That helps with event deduplication, but database change feeds and CDC paths do not have a fully explicit loop-detection rule.

A KNative workflow triggered by CDC that writes back to the same database can create repeated CDC events unless origin/idempotency logic is consistently enforced.

**Recommendation:** Add a rule requiring change events to carry origin, idempotency key, and self-ignoring behavior for mutating workflows.

**Recommended action:** Amend before implementation of KNative + Restate stateful workflows.

---

### Finding 4 — Argo Workflows vs Restate Boundary Is Deferred

**Severity:** Medium  
**Affected areas:** AD-3, Deferred section

The spine defers the exact split between Argo Workflows and KNative + Restate by saying the split depends on use case. That is reasonable for a spine, but it leaves a real implementation divergence point open.

**Recommendation:** Either keep the deferral with a clear revisit trigger or add a lightweight rule:

- Restate for stateful SAGA/workflow state.
- Argo Workflows for CI/build/test/deploy and batch orchestration.

**Recommended action:** Resolve during story creation or before implementing workflow-heavy stories.

---

### Finding 5 — Upgrade Strategy Is Not Fully Governed

**Severity:** Medium  
**Affected areas:** AD-9, Stack, Structural Seed

The stack table says versions should be updated in place as the project evolves, but the spine does not define an upgrade invariant.

For a GitOps platform, component upgrades should be treated as environment mutations.

**Recommendation:** Add an AD or convention that all platform component upgrades flow through GitOps and are promoted through Kargo/Argo CD, not applied imperatively.

**Recommended action:** Amend before production rollout.

---

### Finding 6 — Version Pinning Is Mixed

**Severity:** Low  
**Affected areas:** Stack table

The spine includes both pinned versions and `(latest stable)` entries. Pinned entries are acceptable and concrete; `(latest stable)` entries are not version locks.

**Recommendation:** Keep `(latest stable)` only where the version is intentionally non-blocking or too volatile to pin. Add minimum compatible versions where compatibility matters.

**Recommended action:** No blocker for MVP, but track before production.

---

## Existing Review Context

Existing review files are present in:

```text
output/planning-artifacts/architecture/architecture-HPDC-2026-07-30/reviews/
```

Observed files:

- `review-good-spine.md`
- `review-adversarial.md`
- `review-versions.md`

The current spine already contains several decisions that reduce older concerns, especially AD-12 for observability and AD-13 for secrets.

---

## Validation Decision

**Proceed with planning if:**

- internal function authorization is accepted as mTLS-only for MVP,
- broad database access is accepted as trusted-function behavior for MVP,
- upgrade automation is handled as a later production-readiness concern.

**Do not proceed without amendment if:**

- the project treats every compromised function as a potential lateral-movement risk,
- database least privilege is a hard requirement,
- upgrade automation is required before implementation starts.

---

## Recommended Next Step

Run `bmad-spec` next to adopt this spine as a companion implementation contract.

If you want the architecture tightened before implementation, run an **Update** pass and add the high-severity invariants around:

1. internal function authorization,
2. per-function database access scope,
3. change-feed loop detection,
4. GitOps upgrade enforcement.

---

## Post-Amendment Note

**Date:** 2026-08-04  
**Finding addressed:** Finding 1 — Internal Function Authorization Is Not Fully Governed.

Added `AD-14 — Internal function authorization` to the spine and updated the Consistency Conventions and testing section. Reran the deterministic spine lint pass after the amendment.

**Result:** `lint_spine.py` passes with 0 findings.

---

## Post-Amendment Note

**Date:** 2026-08-04  
**Finding addressed:** Finding 2 — Database Access Scope Is Broad.

Added `AD-15 — Per-function database access scoping` to the spine. The new rule requires each function to declare minimum required database access in a Git-owned policy file, use per-function Infisical credentials, and read/write only approved databases, collections, tables, and KeyDB prefixes. CI must validate function manifests against the policy matrix before Kargo promotion.

Updated the source tree with a `platform/database-access/` directory and added database access scope validation to deployment tests.

**Result:** `lint_spine.py` passes with 0 findings.

---

## Post-Amendment Note

**Date:** 2026-08-04  
**Finding addressed:** Finding 3 — Change Feed Loop Detection Is Partially Covered.

Added `AD-16 — Change-feed loop detection` to the spine. The new rule requires CouchDB `_changes` and YugabyteDB CDC events that trigger KNative or Restate workflows to carry `event_id`, `origin`, `idempotency_key`, target domain, and mutation direction. KNative and Restate sinks must ignore self-origin events, enforce idempotency, and prevent recursive CDC/_changes loops.

Updated the Consistency Conventions, added `platform/change-feed/` to the source tree, and added change-feed loop prevention to integration tests.

**Result:** `lint_spine.py` passes with 0 findings.

---

## Post-Amendment Note

**Date:** 2026-08-04  
**Finding addressed:** Finding 4 — Argo Workflows vs Restate Boundary Is Deferred.

Added `AD-17 — Workflow orchestrator boundary` to the spine. The new rule assigns Restate to stateful SAGA/workflow state, durable business processes, idempotent state transitions, and change-feed-driven workflows. Argo Workflows is limited to CI/CD pipelines, build/test/scan/deploy automation, batch orchestration, and one-shot offline GitOps jobs. A single business workflow must not be implemented in both systems.

Clarified ownership: business workflow implementation code belongs under `backend/` as serverless functions or SAGA modules; `platform/workflows/` contains only orchestrator policy matrices, allowed transition graphs, and ownership rules.

Updated the source tree with a `platform/workflows/` directory and added workflow orchestrator boundary validation to deployment tests.

**Result:** `lint_spine.py` passes with 0 findings.

---

## Post-Amendment Note

**Date:** 2026-08-04  
**Finding addressed:** Finding 5 — Upgrade Strategy Is Not Fully Governed.

Added `AD-18 — GitOps component upgrade enforcement` to the spine. The new rule requires all platform component upgrades to be declared as GitOps changes and promoted through Kargo Freight and Argo CD. In-place Helm upgrades, direct `kubectl` changes, and manual image tag swaps are forbidden. Each component upgrade must include version, rollback target, compatibility matrix, required sync-wave order, and validation evidence before staging or production promotion.

Updated the source tree with `gitops/upgrades/` and added component upgrade validation to deployment tests.

**Result:** `lint_spine.py` passes with 0 findings.

---

## Post-Amendment Note

**Date:** 2026-08-04  
**Finding addressed:** Finding 6 — Version Pinning Is Not Fully Governed.

Added `AD-19 — Version pinning and provenance enforcement` to the spine. The new rule requires GitOps manifests to pin platform components by immutable digest or exact version, not `latest` or mutable tags. Kargo Freight may promote only Harbor images/configs with required scan, SBOM, and signing evidence. Mutable stack-table entries must be converted to exact pins or approved exceptions with owner, expiry, and rollback target.

Updated the stack table to remove mutable `(latest stable)` placeholders and added `gitops/component-versions/` to the source tree.

**Result:** `lint_spine.py` passes with 0 findings.
