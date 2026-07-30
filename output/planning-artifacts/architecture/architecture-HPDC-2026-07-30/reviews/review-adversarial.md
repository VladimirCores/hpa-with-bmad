# Adversarial Architecture Review — HPDC Architecture Spine

**Reviewer:** Adversarial Architecture Agent
**Date:** 2026-07-30
**Target:** `ARCHITECTURE-SPINE.md` (revision 2026-07-30)
**Paradigm:** Gateway-Mediated Domain Segregation
**Altitude:** Feature

---

## Methodology

Construct two independent implementation units that each obey every AD literally yet produce mutually incompatible systems. For each adversarial pair, identify the specific mechanism of incompatibility: shape clash, ownership overlap, conflicting mutation path, undefined interface, or boundary violation.

---

## 1. Adversarial Pair: CouchDB Document Shape Clash

### Unit A — Device Registration (Entity Management)

Implements AD-2 (`/api/*` domain, serverless workflow), AD-6 (CouchDB ownership of entity hierarchy), AD-3 (KNative+Restate).

Writes device documents to CouchDB with shape:

```json
{
  "_id": "device_01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "type": "device",
  "device_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "device_type": "temperature_sensor",
  "firmware_version": "2.1.0",
  "owner_company_id": "comp_01ARZ3NDEKTSV4RRFFQ69G5FBW",
  "status": "active",
  "registered_at": "2026-07-30T00:00:00Z"
}
```

Enforces ULID format for `device_id` per Consistency Conventions. Uses `_changes` feed to trigger downstream workflows (AD-4). Expects `device_id` to be the authoritative join key across all subsystems.

### Unit B — Alert Management (Alert Lifecycle)

Implements AD-2 (`/events/*` domain, event pub-sub), AD-6 (CouchDB listed for alert management state), AD-3 (KNative+Restate for state machines), AD-4 (Kafka→SpinKube→CouchDB).

Writes alert documents to the **same** CouchDB with shape:

```json
{
  "_id": "alert_01HZ3NDEKTSV4RRFFQ69G5FAV",
  "type": "alert",
  "device_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "severity": "critical",
  "metric": "temperature",
  "threshold": 85.0,
  "value": 92.3,
  "state": "firing",
  "acknowledged_by": null,
  "resolved_at": null
}
```

Additionally writes **back to the device document** to stamp `last_alert_timestamp` and `current_alert_state` — a legitimate optimization to avoid joins during alert dashboards:

```json
{
  "_id": "device_01ARZ3NDEKTSV4RRFFQ69G5FAV",
  ...
  "last_alert_timestamp": "2026-07-30T01:00:00Z",
  "current_alert_state": "critical"
}
```

### Failure Mode

1. **Document shape corruption via CouchDB full-document semantics.** CouchDB lacks partial update. When Unit B writes the `device_*` doc to stamp alert fields, it must read-modify-write the entire document. If Unit A concurrently updates the same device doc (e.g., changes `firmware_version` from `2.1.0` to `2.1.1`), Unit B's write will overwrite Unit A's change (CouchDB conflict → update loses). Result: firmware version silently reverts to `2.1.0` on the device record.

2. **Query ambiguity.** Unit A queries `{type: "device"}` to list devices. Unit B's alert docs (which may carry a `device_id` field) could match or pollute results if any function uses a relaxed filter. Neither unit is wrong per the ADs — they just share a database with overlapping key spaces and no document-type segregation.

3. **`device_id` semantic drift.** Unit A treats `device_id` as an opaque ULID. Unit B's alert documents use the same field `device_id` to reference the same device. If Unit B ever normalizes device identifiers differently (e.g., stripping the `device_` prefix, or lowercasing), the join silently breaks. No cross-function contract defines `device_id` encoding.

**Root cause:** AD-6 grants all functions R/W to all databases ("The ownership boundary prevents duplicating authoritative data across stores, not restricting access"). There is no per-database, per-collection, or per-document-type access control. There is no document-type namespace convention (prefix, separate database per domain, CouchDB `_db` per function category). All functions are implicitly trusted with all data.

---

## 2. Adversarial Pair: Mutations Loop via Database Change Feeds

### Unit A — Hasura GraphQL Federation

Implements AD-2 (`/gql` route), AD-6 (Hasura federates CouchDB + ClickHouse + YugabyteDB).

Receives a mutation from an operator dashboard: `mutation { update_device(id: "01ARZ3NDEKTSV4RRFFQ69G5FAV", set: { status: "maintenance" }) }`. Hasura writes directly to YugabyteDB (its configured data source). The write succeeds.

### Unit B — KNative+Restate Change-Driven Workflow

Implements AD-4 ("YugabyteDB CDC → KNative Eventing → KNative+Restate"), AD-3 (KNative+Restate for SAGAs).

Unit B listens on the YugabyteDB CDC stream for any change to the `devices` table. When Hasura's mutation is detected, Unit B triggers a SAGA workflow that:
1. Reads the device record from YugabyteDB
2. Fires a Pulsar message to pause telemetry ingestion for this device
3. Writes an audit log entry to CouchDB
4. Updates the device record in YugabyteDB with `maintenance_mode: true`

### Failure Mode

**Infinite mutation loop.** Step 4 writes back to YugabyteDB — which triggers another CDC event. KNative Eventing delivers this event to Unit B again. Unit B re-executes the SAGA, writes to YugabyteDB again, triggers another CDC event, ad infinitum.

**Why each unit believes it is correct:**
- Hasura's mutation is a legitimate operator action through the `/gql` route. AD-6 lists YugabyteDB as accessible to all functions; Hasura is not restricted.
- Unit B's CDC subscription is explicitly mandated by AD-4 ("Database change feeds ... trigger KNative services"). There is no idempotency token, no loop-detection marker, no "change originated from" envelope field, and no "ignore self-generated changes" rule anywhere in the spine.

**Root cause:** No AD requires idempotency tokens or origin tracking in database change events. KNative Eventing (AD-4) + database writes (AD-6) create a potential positive-feedback loop. The spine assumes change feeds are one-directional, but writes by change-triggered functions make them bidirectional.

---

## 3. Adversarial Pair: KeyDB Key-Namespace Collision

### Unit A — Session Manager (Auth Domain)

Implements AD-2 (some internal function behind `/api` or Casdoor interaction), AD-6 (KeyDB owns "sessions").

Session TTL: 3600s. Key pattern: `session:{random_hex}`.

```redis
SET session:a1b2c3d4 '{"user_id": "...", "role": "operator"}' EX 3600
```

### Unit B — Alert State Machine (Alert Management Domain)

Implements AD-2 (`/events/*` domain), AD-6 (KeyDB owns "alert state"), AD-3 (Restate for state machine).

Alert TTL: 86400s (alerts can live up to 24h). Key pattern: `alert:{alert_id}:state`.

```redis
SET alert:alert_01HZ3NDEKTSV4RRFFQ69G5FAV:state '"acknowledged"' EX 86400
SET alert:alert_01HZ3NDEKTSV4RRFFQ69G5FAV:owner '"session:a1b2c3d4"' EX 86400
```

### Failure Mode

1. **Key collision.** Unit B stores `alert_owner` as `session:a1b2c3d4` — a valid KeyDB key. If the session manager uses a Redis `SCAN` or `KEYS` operation matching `session:*`, it may accidentally pick up alert documents with owner references. Unlikely but possible with aggressive key scanning (e.g., cleanup jobs).

2. **TTL confusion.** A session expires after 3600s and the session manager issues `DEL session:a1b2c3d4`. But Unit B's alert records still reference `session:a1b2c3d4` as the owner. The alert becomes orphaned — owned by a deleted session. The spine does not define session-owner cleanup hooks for alert states.

3. **No key-namespace convention.** AD-6 lists KeyDB ownership for both "sessions" and "alert state" but defines no key-prefix convention, no KeyDB instance separation, and no database index (`SELECT 0` vs `SELECT 1`) convention. Two functions writing to the same KeyDB cluster with different TTLs and partial key overlap is a ticking collision.

**Root cause:** AD-6 assigns two logically distinct concerns (session management, alert state) to the same KeyDB instance without any namespacing rule. No AD defines a "one logical use per KeyDB database index" or "registered key prefix" convention.

---

## 4. Adversarial Pair: Paradigm Violation in the Welcome Flow

### The spine's own example

```text
Client ──HTTP GET──▶ EG(/api/welcome)
                       │
                       ├── JWT validation (Casdoor)
                       ├── ext_authz check (Casbin gRPC)
                       │
                       ▼
                 KNative Service "welcome" (Go)
                       │
                       ├── HTTP GET ──▶ SpinApp "counter" (Rust WASM)
                       │                    │
                       │                    └── KeyDB INCR counter-welcome
                       │
                        └── Response: "Welcome (42)"
```

### What AD-2 requires

"Domains communicate exclusively through the event-mesh (Pulsar topics, Kafka topics) or database-level change feeds — **never through direct HTTP calls to another domain's internal services.** "

### Failure Mode

**The welcome flow makes a direct HTTP call from KNative "welcome" to SpinApp "counter."** This is a direct HTTP call to an internal service. If the welcome function lives in the `/api` route domain and counter is a separate function (possibly in the same route, but AD-2's text forbids even same-route direct HTTP), this violates the paradigm's core segregation rule.

**Why neither unit will fix this:**
- Unit A (welcome function author) reads the "Function-to-function calls" section in Consistency Conventions and sees: "KNative functions may call other KNative functions or SpinApps via HTTP for stateful operations." This is an explicit carve-out.
- Unit B (security/compliance reviewer) reads AD-2 and sees: "never through direct HTTP calls to another domain's internal services."

**The contradiction means:**
1. The exception in Consistency Conventions contradicts AD-2. No AD overrides or clarifies the priority.
2. If direct HTTP calls are allowed, the Gateway-Mediated Domain Segregation paradigm has a gap: functions can bypass the gateway entirely for inter-function communication.
3. The `welcome → counter` call has no:
   - Gateway mediation (no Envoy between them)
   - Authentication/authorization (no JWT, no ext_authz)
   - Auditing/rate-limiting
   - Circuit breaking or timeout propagation

**Concrete attack:** A compromised KNative function (e.g., via a dependency vulnerability) can call ANY other SpinApp or KNative function's internal HTTP endpoint. There is no trust boundary between functions on the internal mesh. AD-8 provides mTLS (transport security), but no authorization — any function can invoke any other function's internal API.

---

## 5. Trust Boundary Violation: No Function-to-Function Authorization

### The Problem

AD-1 establishes Envoy Gateway as the sole ingress with full authN/authZ. But the internal mesh (function-to-function HTTP calls, database access) has no equivalent authorization layer.

### Attack Scenarios

1. **Direct database access bypassing auth.** A Pulsar Function `telemetry-aggregator` in the `/telemetry` route has R/W access to YugabyteDB (AD-6). If its JAR is replaced or compromised, it can directly read financial data or modify transactional records. No gateway inspects or authorizes this access — AD-6 gives I/O access to all functions unconditionally.

2. **Database credential exposure.** AD-6 says "All serverless functions via SDK." This implies all functions share the same database credentials or have equivalent access. If one function is compromised, ALL databases are compromised. No credential scope per function type.

3. **Hasura auth bypass.** Hasura sits behind `/gql` with auth, but the underlying databases (CouchDB, ClickHouse, YugabyteDB) are also directly accessible by KNative functions that may not implement the same auth checks. A function reading from CouchDB can access data that would be denied to a Hasura role. The auth model is inconsistent between the two access paths.

### Root Cause

AD-6's explicit "no restriction" policy and the absence of any AD requiring per-function database credential scoping, per-function database access gating, or gateway mediation for function-to-function calls.

---

## 6. Auth Model Conflict: RBAC vs ReBAC vs ABAC

### The Problem

Casbin implements three models simultaneously (AD-2 route table, Casbin platform config). No conflict-resolution rule is defined.

### Concrete Scenario

| Model | Rule | Result |
|-------|------|--------|
| RBAC | User `alice` has role `device_viewer`. Role `device_viewer` permits `read` on `device:*` | Allow read, Deny write |
| ReBAC | User `alice` is an `owner` of `device:01ARZ3NDEKTSV4RRFFQ69G5FAV` | Allow write on owned device |
| ABAC | Context: current time is 02:00 (maintenance window), policy says `deny all mutations during maintenance window` | Deny write |

**What happens when `alice` tries to update her device at 02:00?**

- RBAC: deny write (role only permits read)
- ReBAC: allow write (ownership overrides role)
- ABAC: deny write (time-based restriction)

The spine provides no answer. Three possible interpretations with equally valid architectural backing:
1. **Most restrictive wins** (defense in depth) — deny write
2. **Most specific wins** (ReBAC is more specific than RBAC, ABAC is most specific) — deny or allow depending on interpretation
3. **Decision chain priority undefined** — Casbin might evaluate in any order, producing inconsistent results

### Additional Auth Conflicts

- **API-Key auth for `/telemetry` and `/events`** (AD-2) vs **JWT auth for other routes**. What if a stolen API key for telemetry is used to craft messages that trigger alert workflows? The alert workflow (KNative, authenticated by mTLS) trusts the event it received. There is no mechanism to trace the original API key through the event-mesh to enforce authz at the workflow level.

- **Cross-region auth.** AD-11 says central hub queries regional APIs with "region-scoped auth." What form does this auth take? If it's the same Casdoor/Casbin stack, regional auth domains must trust each other. No cross-region trust mechanism is defined.

---

## 7. Undefined Interfaces

| Interface | Between | Missing specification |
|-----------|---------|----------------------|
| KNative→SpinApp HTTP | `welcome` function → `counter` SpinApp | Auth, retry, timeout, circuit-breaker, rate limit, idempotency |
| Pulsar→CouchDB | Telemetry enrichment pipeline | CouchDB document shape for telemetry records, conflict strategy (overwrite vs create new revision) |
| CouchDB _changes→KNative Eventing | Database change feed triggers | Idempotency token, loop detection, ordering guarantees, deduplication window |
| CDC→KNative Eventing | YugabyteDB CDC triggers | Same as above — plus schema evolution strategy for CDC Avro/JSON |
| SpinApp→KeyDB | Stateful counter writes | Connection pooling, retry semantics, TTL management, expiry handling |
| Envoy→Casbin ext_authz | Gateway authz check | Timeout, caching policy, failure mode (deny-open vs deny-closed), policy reload mechanism |

---

## 8. Paradigm Integrity Assessment

**Gateway-Mediated Domain Segregation** as applied here has three structural weaknesses:

1. **The domain boundary is only at ingress.** Segregation at Envoy Gateway creates the illusion of isolation, but since all functions share all databases (AD-6) and can make unauthenticated HTTP calls to each other (Consistency Conventions carve-out), the domain boundary is a single chokepoint on external traffic — not an actual segregation architecture. Functions within the cluster operate in a trust-everything model.

2. **The event-mesh is optional, not enforced.** AD-4 says event-mesh is "the integration fabric," but AD-6 and the function-to-function HTTP carve-out provide alternative integration paths. Because these alternatives are simpler (direct HTTP, direct DB), they will be preferred by implementors, and the event-mesh becomes a second-class citizen.

3. **No authorization inside the trust boundary.** Once past Envoy Gateway, there is zero authorization. mTLS (AD-8) provides transport security but not authorization. Any function can access any database, any function's HTTP endpoint, any event topic. The paradigm should be "Gateway-Mediated Domain Segregation with Internal AuthZ" but the internal authZ layer is absent.

---

## Summary Table

| Finding | Type | Severity | Affected ADs |
|---------|------|----------|-------------|
| CouchDB document shape clash (device vs alert records) | Shared-data shape clash, ownership overlap | CRITICAL | AD-6 |
| Hasura/KNative mutation loop via CDC | Conflicting state-mutation path | CRITICAL | AD-4, AD-6 |
| KeyDB key collision (session vs alert state) | Ownership overlap | HIGH | AD-6 |
| Welcome flow violates AD-2 (direct HTTP) | Boundary violation | HIGH | AD-2, Consistency Conventions |
| No function-to-function auth (trust boundary) | Trust boundary violation | CRITICAL | AD-1, AD-8 |
| RBAC/ReBAC/ABAC conflict resolution undefined | Undefined interface | HIGH | AD-2 (Casbin model) |
| Undefined KNative→SpinApp interface | Undefined interface | MEDIUM | Consistency Conventions |
| No per-function database credential scoping | Trust boundary violation | CRITICAL | AD-6 |
| No CDC/mutation loop detection | Undefined interface | HIGH | AD-4 |
| Multi-region auth trust not defined | Undefined interface | MEDIUM | AD-11 |

---

## Recommended ADs to Close These Holes

### Tighten AD-6 — Database Access Scoping

Replace "The ownership boundary prevents duplicating authoritative data across stores, not restricting access" with:

- AD-6a: Each function type (KNative function, SpinApp, Pulsar Function) MUST declare its database access scope in a `function.yaml` manifest (read-only, write, read-write per database and collection/table). Kargo promotion MUST validate that declared scope matches a pre-approved policy matrix.
- AD-6b: Database credentials MUST be scoped per function deployment (not shared). Infisical Operator injects per-function credentials with the minimum required permissions.
- AD-6c: KeyDB keys MUST be namespaced by a registered prefix per logical concern. Prefixes registered in `specs/keydb-namespaces.yaml`.

### Add AD-12 — Change Feed Loop Detection

- All database change events that trigger KNative services MUST carry an `x-change-origin` marker. KNative sinks MUST inspect this marker and ignore events whose origin matches their own deployed identity.
- All mutating workflows triggered by change feeds MUST include an idempotency check (deduplication window, idempotency key in the target document).

### Clarify AD-2 — Inter-Function Communication

- Direct HTTP function-to-function calls MUST be mediated by a local envoy sidecar that validates function identity (SPIFFE ID from mTLS) against an allowed-caller list per function. Alternatively, all inter-function calls MUST go through the event-mesh.
- Remove the "KNative functions may call other KNative functions or SpinApps via HTTP" carve-out, OR elevate it to a first-class AD with strict interface contracts.

### Add AD-13 — Authorization Model Priority

- Define Casbin eval priority: ABAC → ReBAC → RBAC (most specific first). Document conflict resolution: on conflicting decision, DENY wins (default-deny).
- Document the exact Envoy SecurityPolicy → Casbin ext_authz contract: timeout (50ms default), failure mode (deny-closed), caching policy (TTL=60s per decision).

### Add AD-14 — Function-to-Function Authorization

- Every inter-function HTTP call MUST present the caller's SPIFFE ID. The callee MUST validate the caller against an allow list or use Envoy sidecar for authorization.
- Database access functions MUST present a database-specific identity (distinct from the function's general identity) scoped to the minimum required privileges.

### Tighten AD-4 — Event-Mesh as Exclusive Integration Fabric

- Reinforce that the event-mesh is the ONLY mechanism for inter-domain communication. Remove the function-to-function HTTP carve-out.
- Add a route/function adjacency matrix that explicitly lists which functions may communicate and through which event channels.

---

## Verdict

**CONDITIONAL** — The spine's ADs are structurally sound at the top level but contain six specific gaps that will produce incompatible implementations. The most critical issue is AD-6's unrestricted database access, which undermines the entire segregation paradigm. Secondarily, the AD-2/Consistency-Conventions contradiction around function-to-function HTTP calls creates a trust boundary the paradigm explicitly sought to prevent.

The paradigm (Gateway-Mediated Domain Segregation) is viable but incomplete — it needs internal authorization to match the strength of its external authorization. Without the recommended ADs, two teams implementing independently will produce systems that work in isolation but fail when integrated due to database shape clashes, mutation loops, and inconsistent auth decisions.
