---
title: Reconciliation — PRD vs with-gsd/ Implementation
created: 2026-07-21
status: analysis
---

# PRD ↔ with-gsd/ Reconciliation

## Verdict: **NEEDS ACKNOWLEDGMENT**

The PRD cannot claim "clean-sheet design." It directly references `with-gsd/` patterns (Open Question #8: "Rust (per with-gsd/)"), matches the existing route table, Casbin ext_authz architecture, KNative+Spin workload model, and identical infrastructure stack. The framing should be **"major extension of existing foundation"** — not clean-sheet.

---

## Finding 1: PRD Route Table Is a Direct Lift from with-gsd/

**Evidence:**

| PRD §4.9 Route Table | with-gsd/ Implementation |
|---|---|
| `/data/*` → CouchDB, Casdoor JWT + Casbin | Not yet implemented (PRD to-be-built) |
| `/api/*` → KNative functions, Casdoor JWT + Casbin | `gitops-workloads/functions/overlays/dev/functions/welcome.yaml` — KNative Service `welcome` routed via Envoy Gateway |
| `/gql` → Hasura GraphQL, Casdoor JWT + Casbin | `gitops-workloads/graphql/gql-route.yaml` — HTTPRoute `/gql` → Hasura |
| `/events/*` → Kafka, API-Key header | `gitops-workloads/kafka/base/kafkatopic.yaml` — `hpa-events` KafkaTopic; stream SpinApp consumes it |
| `/telemetry/*` → Pulsar, API-Key header | Not yet implemented (PRD to-be-built) |

The existing route structure (`/api/*`, `/gql`, `/events/*`) is already deployed. The PRD adds two routes (`/data/*` for CouchDB, `/telemetry/*` for Pulsar) as new capabilities. The auth model (Casdoor JWT on app routes, API-key on messaging routes) is identical to what the Casbin authorizer already enforces.

**Impact:** PRD §4.9 should state: "Extends the existing route table from with-gsd/ with two new routes for CouchDB data access and Pulsar telemetry ingestion."

---

## Finding 2: Core Backend Patterns Already Exist and Are Tested

### KNative Function (Go HTTP Server)
- **with-gsd/:** `backend/functions/welcome/main.go` — Go HTTP server with graceful shutdown, health checks (`/health`), structured logging via `slog`, context propagation, centralized config via `internal/config/config.go`
- **PRD:** FR-15 (KNative + Restate), FR-17 (Backstage workload delivery for KNative)
- **Gap:** PRD describes KNative + Restate for stateful processing; with-gsd/ has stateless KNative only. Restate integration is genuinely new.

### Spin WASM Functions (Rust)
- **with-gsd/:** Two SpinApps:
  - `counter` — HTTP trigger, KeyDB INCR, Rust/WASM via SpinKube
  - `stream` — **Kafka trigger** on `hpa-events` topic, parses JSON events (`HpaEvent` struct with `event_id`, `device_type`, `metric_value`, `processed_timestamp`), aggregates per-device_type counts into KeyDB via HINCRBY
- **PRD:** FR-5 (Spin function stream processing from Kafka)
- **Gap:** The stream processor already implements the pattern PRD describes. PRD adds ClickHouse sink (with-gsd/ sinks to KeyDB only) and sub-10ms latency requirements.

### Casbin Authorizer (gRPC ext_authz)
- **with-gsd/:** `backend/authorizers/authz/main.go` — Full gRPC server implementing `authv3.Authorization`, uses `casbin.SyncedEnforcer` with `keyMatch`/`keyMatch3` functions, model+policy files, complete test suite (196 lines, 12 tests)
- **PRD:** FR-41 (RBAC), FR-42 (ReBAC/Zanzibar), FR-43 (ABAC)
- **Gap:** with-gsd/ implements **basic RBAC only** (admin/user/viewer roles with path-based policies). PRD adds ReBAC (Google Zanzibar relationship tuples) and ABAC (attribute-based dynamic policies). This is a significant extension, not a replacement.

### OpenAPI Specifications
- **with-gsd/:** `specs/openapi.yaml` — OpenAPI 3.0.3 spec for `/api/welcome` endpoint
- **PRD:** FR-39 (OpenAPI specification governance)
- **Gap:** PRD describes specs in `specs/` directory as source-of-truth for all endpoints. with-gsd/ has one spec for one endpoint. PRD scales this to full platform governance.

### Kafka Infrastructure
- **with-gsd/:** Strimzi `KafkaTopic` (`hpa-events`, 3 partitions, 7-day retention)
- **PRD:** FR-9 (Alert signal routing to Kafka topics)
- **Gap:** with-gsd/ has Kafka for stream processing. PRD adds Pulsar as primary engine and Kafka as secondary — the dual-engine architecture is new.

### Hasura GraphQL
- **with-gsd/:** `gitops-workloads/graphql/gql-route.yaml` — HTTPRoute `/gql` → Hasura with URL rewrite to `/v1/graphql`
- **PRD:** FR-16 (Unified GraphQL federating YugabyteDB + CouchDB + ClickHouse)
- **Gap:** with-gsd/ has Hasura deployed with route. PRD adds full federation across three databases — genuinely new.

---

## Finding 3: Capabilities in with-gsd/ the PRD Should Acknowledge But Doesn't (or Burials)

### 1. Stream Processor Pattern (Kafka → Spin → KeyDB)
The `stream` SpinApp (`backend/spins/stream/`) already implements the Kafka-consumption pattern PRD describes in FR-5. It consumes `hpa-events` messages, parses `HpaEvent` JSON, and aggregates metrics into KeyDB. This is a working reference implementation — the PRD should acknowledge it as the foundation being extended.

### 2. Go DRY Config Pattern
`backend/internal/config/config.go` provides centralized constants (ports, namespaces, service URLs, env var names, HTTP status codes). This pattern is referenced in README under "M4: Go Application DRY." The PRD doesn't mention this architectural pattern but benefits from it.

### 3. Rust DRY Constants Pattern
`backend/spins/counter/src/constants.rs` mirrors the Go config pattern for Rust services. README documents this as "M5: Rust Application DRY." Same as above — the PRD inherits this pattern without acknowledgment.

### 4. Infisical Secrets Integration (Already Deployed)
Multiple workloads already reference Infisical secrets:
- `welcome-infisical-secrets` (KNative function)
- `casbin-infisical-secrets` (authorizer)
- `counter-infisical-secret`, `stream-infisical-secret` (SpinApps)
- `infisical-secret-stream.yaml`, `infisical-secret-counter.yaml` in gitops-workloads

PRD FR-44 (Infisical secrets management) describes what's already deployed.

### 5. Full Infrastructure Stack (25 Steps, All Implemented)
The with-gsd/ provisioning pipeline has 25 numbered steps covering: bridge setup, Cilium, Rook-Ceph, Harbor, Infisical, Runtimes (KNative + SpinKube + KeyDB), Kafka, Spegel, Casdoor, Casbin, Envoy Gateway, Security Policies, GitOps (ArgoCD + Kargo), Workloads, Streaming, YugabyteDB, Hasura, VictoriaMetrics, vmagent, kube-state-metrics, Grafana, AlertManager, TLS, Seed Hydration.

PRD §4.5 (GitOps Platform Infrastructure) describes this stack but frames it as new design rather than documenting what's already operational.

### 6. Telemetry Function (Java Pulsar Function — Built)
`backend/functions/telemetry/target/classes/com/analytics/pulsar/functions/TelemetryTransformFunction.class` — a compiled Java Pulsar Function. This is the exact pattern PRD FR-6 describes. The PRD should note this function exists as a build artifact.

### 7. Security Policies
`gitops-workloads/security/base/securitypolicy.yaml` — Pod security policies already deployed. PRD's security model should reference this existing layer.

---

## Recommendations

1. **Change framing** from "clean-sheet design" to "extends existing with-gsd/ foundation" in §1 Vision and throughout.
2. **Add explicit acknowledgment section** (e.g., §1.5 "Existing Foundation") listing with-gsd/ capabilities that are already implemented and will be extended.
3. **Distinguish "built" from "to-be-built"** in each FR's testable consequences. Currently all FRs read as if they describe greenfield requirements.
4. **Update Open Question #8** — the reference to "Rust (per with-gsd/)" proves the PRD was written with awareness of the existing codebase. This contradicts the clean-sheet claim.
5. **Add a delta table** showing: what with-gsd/ provides → what the PRD adds → what's genuinely new.

---

## Summary Table

| Capability | with-gsd/ Status | PRD Coverage | Verdict |
|---|---|---|---|
| KNative functions (Go) | Deployed + tested | FR-15, FR-17 | Extension (add Restate) |
| Spin WASM (Rust, Kafka trigger) | Deployed + tested | FR-5 | Extension (add ClickHouse sink) |
| Casbin ext_authz (gRPC) | Deployed + tested (RBAC only) | FR-41, FR-42, FR-43 | Extension (add ReBAC + ABAC) |
| OpenAPI specs | One spec exists | FR-39 | Scale to full governance |
| Kafka (Strimzi) | Topic deployed | FR-9 | Add Pulsar as primary engine |
| Hasura GraphQL | Route deployed | FR-16 | Add full federation |
| Envoy Gateway routing | 3 routes active | FR-36 | Add 2 new routes |
| Infisical secrets | Deployed across workloads | FR-44 | Already operational |
| Talos/Cilium/Rook-Ceph | 25-step pipeline complete | FR-22, FR-23, FR-24 | Already operational |
| CouchDB | Not implemented | FR-13 | Genuinely new |
| YugabyteDB | Provisioned (step 17) | FR-13 | Route/config new |
| ClickHouse | Not implemented | FR-7 | Genuinely new |
| Pulsar | Not implemented | FR-1, FR-6 | Genuinely new |
| Alert state machine | Not implemented | FR-10 | Genuinely new |
| AI Agent Engine | Not implemented | FR-46–48 | Genuinely new |
| Multi-region federation | Not implemented | FR-33–35 | Genuinely new |
| Central hub SPA | Not implemented | FR-35 | Genuinely new |
