---
name: High Performance Distributed Cluster (HPDC)
type: architecture-spine
purpose: build-substrate
altitude: feature
paradigm: Gateway-Mediated Domain Segregation
scope: Enterprise GitOps Platform for IoT telemetry, alert management, and GitOps deployment
status: final
created: 2026-07-30
updated: 2026-07-30
binds: [FR-1..FR-48, UJ-1..UJ-5]
sources:
  - output/planning-artifacts/prds/prd-HPDC-2026-07-21/prd.md
companions: []
---

# Architecture Spine — HPDC

## Design Paradigm

**Gateway-Mediated Domain Segregation** — Envoy Gateway routes are hard domain boundaries. Each route owns its internal pattern (document-serving, serverless workflow, stream ingestion, event pub-sub, graphql federation). The event-mesh (Pulsar + Kafka) is the cross-cutting integration fabric. The compute layer is entirely serverless-first: KNative (scale-to-zero) with Restate for stateful SAGAs/workflows, SpinKube WASM for stateless transforms, Pulsar Functions for stream processing. No always-on microservices.

```
┌──────────────────────────────────────────────────────────┐
│                    Envoy Gateway                          │
│  /data  │  /api  │  /gql  │  /telemetry  │  /events     │
├─────────┼────────┼────────┼──────────────┼───────────────┤
│ CouchDB │KNative │ Hasura │   Pulsar     │    Kafka      │
│         │Restate │        │  Functions   │  SpinKube     │
├─────────┴────────┴────────┴──────────────┴───────────────┤
│              Event Mesh (Pulsar + Kafka)                  │
├─────────┬────────┬────────┬──────────┬───────┬───────────┤
│ CouchDB │Yugabyte│ArcadeDB│ClickHouse│ KeyDB │ PostgreSQL│
│         │  DB    │        │          │       │(Auth)     │
├─────────┴────────┴────────┴──────────┴───────┴───────────┤
│              Ceph RBD (persistent storage)                │
│         Talos Linux + Cilium (eBPF) substrate            │
└──────────────────────────────────────────────────────────┘

── Example flow: Welcome endpoint with stateful counter ──
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

## Invariants & Rules

### AD-1 — Envoy Gateway as exclusive ingress boundary

- **Binds:** FR-36, FR-37, FR-38, all external traffic
- **Prevents:** Services bypassing the gateway; direct external access to backend services; unauthenticated routes
- **Rule:** Every external route must be declared as a Kubernetes Gateway API resource (HTTPRoute/GRPCRoute/TLSRoute) on Envoy Gateway. No backend service exposes a port externally without a matching gateway route. TLS termination at EG via cert-manager.

### AD-2 — Domain-per-route segregation

- **Binds:** FR-1, FR-5, FR-9, FR-13, FR-16, FR-36
- **Prevents:** Cross-route coupling; mixed access-patterns on the same route; route A directly importing route B's internals
- **Rule:** Each route is its own bounded domain:

| Route | Domain | AuthN | Pattern |
|-------|--------|-------|---------|
| `/data/*` | Document-serving | Casdoor JWT | CouchDB native (CRUD, MapReduce, _changes) |
| `/api/*` | Serverless workflows | Casdoor JWT | KNative + Restate (SAGA, event-sourcing) |
| `/gql` | Data federation | Casdoor JWT | Hasura (federates CouchDB + ClickHouse + YugabyteDB) |
| `/telemetry/*` | Stream ingestion | API-Key | Pulsar native (MQTT/gRPC handlers) |
| `/events/*` | Event pub-sub | API-Key | Kafka + SpinKube WASM |

Domains communicate exclusively through the event-mesh (Pulsar topics, Kafka topics) or database-level change feeds — never through direct HTTP calls to another domain's internal services. Function-to-function HTTP calls within the same domain (e.g., KNative → SpinApp for stateful operations) are permitted and travel through the mTLS mesh. Backpressure for the `/telemetry` route is handled by Pulsar's per-topic backlog quotas and topic offloading to S3/Ceph.

### AD-3 — Serverless-first compute

- **Binds:** FR-5, FR-6, FR-11, FR-15, FR-17, all compute workloads
- **Prevents:** Always-on microservices; long-running daemon pods; persistent server processes
- **Rule:** All compute must use one of:
  - **KNative** (scale-to-zero) + **Restate** for stateful, multi-step workflows (SAGAs, event-sourcing, alert state machines, change-driven business logic)
  - **SpinKube** (containerd-shim-spin) for stateless WASM transforms on Kafka topics
  - **Pulsar Functions** for stream aggregation, windowing, and JDBC Sink writes to ClickHouse
  - **Argo Workflows** for CI/build/test/deploy pipelines and batch compute
  No Deployment/StatefulSet for application logic. Only infrastructure components (databases, message brokers, gateway) run as persistent pods.

### AD-4 — Event-mesh as the integration fabric

- **Binds:** FR-1, FR-2, FR-3, FR-4, FR-9, inter-domain communication
- **Prevents:** Point-to-point integrations between domains; synchronous coupling hiding behind async protocols
- **Rule:** Pulsar is the primary message backbone handling all telemetry ingestion (MQTT/gRPC → Pulsar topics) at 100K+ RPS. Kafka is the secondary stream handling alert signals, external events, and Spin WASM consumption. Database change feeds (CouchDB `_changes`, YugabyteDB CDC) trigger KNative services via KNative Eventing. Argo Events bridges Git/image/Kafka events into Argo Workflows.

```
── Telemetry path ──────────────────────────────────────────
IoT Devices ──MQTT/gRPC──▶ EG(/telemetry) ──▶ Pulsar ──Pulsar Functions──▶ ClickHouse
                                                    └──Pulsar Functions──▶ CouchDB / YugabyteDB

── Event path ──────────────────────────────────────────────
External APIs ──────▶ EG(/events) ──▶ Kafka ──SpinKube WASM──▶ ClickHouse / CouchDB
                                          ──KNative+Restate──▶ CouchDB / KeyDB (alert state)

── API path (with auth) ────────────────────────────────────
Clients ──▶ EG(/api) ──extAuth──▶ Casbin gRPC ──▶ KNative+Restate ──▶ DBs
                        │        (RBAC/ReBAC/ABAC)
                        └─▶ JWT validation at Casdoor

── Data path ───────────────────────────────────────────────
Clients ──▶ EG(/data) ──extAuth──▶ Casbin gRPC ──▶ CouchDB
                        │
                        └─▶ JWT validation at Casdoor

── GQL path ────────────────────────────────────────────────
Clients ──▶ EG(/gql) ──extAuth──▶ Casbin gRPC ──▶ Hasura ──▶ CouchDB / ClickHouse / YugabyteDB
                        │
                        └─▶ JWT validation at Casdoor

── Change-driven path ──────────────────────────────────────
CouchDB _changes ──▶ KNative Eventing ──▶ KNative+Restate (SAGA workflows)
YugabyteDB CDC   ──▶ KNative Eventing ──▶ KNative+Restate
```

### AD-5 — Protobuf normalized envelope

- **Binds:** FR-2
- **Prevents:** Mixed serialization on the wire; schema drift between producers and consumers
- **Rule:** All messages on Pulsar and Kafka topics use Protobuf serialization with Pulsar Schema Registry / Kafka Schema Registry. The common envelope is:

```protobuf
message CommonEnvelope {
  string device_id = 1;
  string device_type = 2;
  string event_type = 3;
  int64 timestamp = 4;       // unix millis
  bytes payload = 5;         // original payload, untransformed
  string region_id = 6;
  string origin = 7;         // who produced this message (function name / service ID)
  string idempotency_key = 8; // unique per logical event; checked against KeyDB dedup set
}
```

The `origin` field prevents CDC mutation loops: CDC-triggered functions check that `origin != self` before writing back to the triggering store. The `idempotency_key` field prevents duplicate processing: Pulsar Functions and KNative services check a KeyDB dedup set (TTL = 5 minutes) before processing a message.

Max envelope size: 64KB. Oversized payloads rejected at gateway (HTTP 413).

### AD-6 — Database ownership boundaries

- **Binds:** FR-13, FR-14
- **Prevents:** Ambiguous write-authority; data duplication without clear source-of-truth
- **Rule:**

| Database | Owns | Accessed by |
|----------|------|-------------|
| CouchDB | CRM/ERP documents, entity hierarchy (company → client → devices/assets), document CRUD + MapReduce + `_changes` feed | All serverless functions via SDK |
| YugabyteDB | Transactional state, workflow/payment data, financial operations, cron jobs, reports, complex relations | All serverless functions via SDK |
| ArcadeDB | Graph data, entity lineage, neighbor discovery, shortest-path traversals | All serverless functions via SDK |
| ClickHouse | Processed telemetry analytics (time-series, aggregations) | All serverless functions via SQL |
| KeyDB (clustered) | Hot cache, pub-sub channels, alert state, sessions | All serverless functions via SDK |
| PostgreSQL | Casdoor + Casbin authN/authZ data (users, roles, policies, relationship tuples) | Casdoor, Casbin only |

All serverless functions have read/write access to all data stores. The ownership boundary prevents *duplicating authoritative data across stores*, not restricting access. Document shape conventions (matching the owning store's schema) are enforced via code review — there is no runtime schema enforcement at write time.

### AD-7 — Ceph for all persistent state

- **Binds:** FR-24
- **Prevents:** Ephemeral storage assumptions; data loss on pod restart
- **Rule:** Every stateful workload uses Ceph RBD PVCs for persistent storage: CouchDB, YugabyteDB, ClickHouse, KeyDB, ArcadeDB, Pulsar bookies, Kafka brokers, PostgreSQL. No hostPath, emptyDir, or local volume for stateful data.

### AD-8 — mTLS for all inter-service communication

- **Binds:** FR-45
- **Prevents:** Plaintext intra-cluster traffic; credential sniffing on the wire
- **Rule:** All service-to-service traffic uses mTLS enforced by Cilium. Certificate lifecycle managed via Cilium SPIFFE/SPIRE integration with auto-rotation. Envoy Gateway handles external TLS termination; internal traffic is mTLS between sidecars.

### AD-9 — GitOps-only delivery

- **Binds:** FR-17, FR-18, FR-19, FR-20, FR-21, environment mutations
- **Prevents:** Imperative drift; out-of-band changes; configuration skew between environments
- **Rule:** All infrastructure and workload changes must flow through Git → Kargo (multi-stage promotion via Freight) → Argo CD (sync via ApplicationSet with Sync Waves). Direct kubectl is forbidden in dev and production. The monorepo structure:

```
/
├── gitops/                     # Kargo + Argo CD configuration
│   ├── kargo/                  # Warehouse, Stage, Freight definitions
│   ├── argocd/                 # App-of-Apps, ApplicationSets, Sync Waves
│   ├── overlays/               # Kustomize overlays per environment
│   │   ├── dev/
│   │   └── prod/
│   └── clusters/               # Cluster registration secrets
├── platform/                   # Infrastructure component configs (Helm values)
├── backend/                    # Serverless function source code
├── frontend/                   # SPA source code (shipped from CDN)
├── specs/                      # OpenAPI specifications
└── charts/                     # Helm charts
```

### AD-10 — Air-gapped delivery

- **Binds:** FR-30, FR-31, FR-32
- **Prevents:** External internet dependency during deployment; registry unavailability
- **Rule:** Harbor serves as the local OCI registry with vulnerability scanning (Trivy) and Cosign image signing. Spegel DaemonSet provides P2P image distribution across nodes. Git repositories mirrored locally (GitLab/Gitea). All delivery is GitOps-mediated — never a static package or direct image pull from the internet.

### AD-11 — Multi-region data sovereignty

- **Binds:** FR-33, FR-34, FR-35
- **Prevents:** Accidental cross-region data replication; compliance violations
- **Rule:** Each region maintains independent CouchDB, YugabyteDB, ClickHouse, ArcadeDB, KeyDB, and PostgreSQL instances. No automatic cross-region data replication. Cilium ClusterMesh over WireGuard VPN provides cross-region service discovery. Central hub queries regional APIs (with region-scoped auth) for aggregate visibility only — regional data never leaves its region.

### AD-12 — Observability

- **Binds:** FR-25, FR-26, FR-27, FR-28, FR-29
- **Prevents:** Opaque system behavior; metrics/traces/logs divergence between functions; unmeasured performance
- **Rule:** Every function writes structured JSON logs to stdout. OpenTelemetry SDK auto-instruments all KNative functions for traces and metrics. VictoriaMetrics cluster (vmstorage/vminsert/vmselect) stores all metrics with Grafana dashboards. Cilium Hubble provides network observability (flows, DNS, service maps). Retention: 7 days raw, 30 days aggregated (1h rollup), 1 year monthly. AlertManager on metric thresholds. Custom function metrics (counter, histogram) published via OpenTelemetry.

### AD-13 — Centralized secrets management

- **Binds:** FR-44
- **Prevents:** Secrets in git, ConfigMaps, or environment variables; credential sprawl; rotation gaps
- **Rule:** All secrets (DB credentials, API keys, TLS certificates) stored in Infisical and never in version control. Infisical K8s Operator injects secrets into pods via the CSI Driver provider (mounted as volumes) or operator syncs to native K8s Secrets for cluster-internal use. Secrets auto-rotate on a configurable schedule (default 90 days). Service accounts (per-function, per-component) in Infisical, never shared credentials.

## Consistency Conventions

| Concern | Convention |
|---------|------------|
| Naming (entities, files, interfaces) | snake_case for protobuf fields, kebab-case for Kubernetes resources, PascalCase for entity types |
| Data & formats (ids, dates, error shapes) | ULID for all entity/resource IDs. ISO-8601/RFC3339 for all timestamps. Structured error payload: `{"code": "<http-status>", "message": "<human>", "details": {...}}` |
| State & cross-cutting (mutation, errors, logging, config, auth) | Structured JSON logging to stdout (not files). Config via ConfigMap/Secret, never env vars for sensitive data. AuthN via Casdoor JWT or API-Key; AuthZ via Casbin ext_authz (Go gRPC) at Envoy Gateway SecurityPolicy. Auth model conflict resolution: DENY wins — if any model (RBAC/ReBAC/ABAC) evaluates to DENY, the decision is DENY regardless of other model results. |
| Function-to-function calls | KNative functions may call other KNative functions or SpinApps via HTTP for stateful operations (e.g., welcome function → counter SpinApp → KeyDB). Calls use DNS service discovery with context-based timeouts. SpinApps never call other SpinApps directly. |
| Protobuf schemas | All `.proto` files in `specs/proto/` with Pulsar/Kafka Schema Registry enforcing compatibility. Backward-compatible field numbering. |
| Environment naming | `dev` (local/talosctl QEMU), `prod` (production bare-metal) |
| Kubernetes resource labels | Three-label taxonomy on all workload resources: `app.kubernetes.io/name`, `app.kubernetes.io/component` (`knative-function`, `spin-function`, `pulsar-function`, `infrastructure`), `app.kubernetes.io/part-of: hpdc-platform` |

## Stack

*Web-verified at time of writing (2026-07-30). The code owns these versions once deployed — update in place as the project evolves.*

| Name | Version | Notes |
|------|---------|-------|
| Talos Linux | 1.13.7 | Immutable K8s OS. Contains k8s v1.36.2, containerd 2.2.6 |
| Cilium | 1.19.6 | eBPF CNI, kube-proxy replacement, L2 LB, ClusterMesh, Hubble |
| Rook-Ceph | 1.20.3 | Ceph v20.2.2, RBD + CephFS CSI |
| Envoy Gateway | 1.8.3 | K8s Gateway API ingress, ext_authz, rate limiting |
| Pulsar | 4.2.3 | Native MQTT (MoP) + gRPC protocol handlers, Pulsar Functions |
| Kafka | (latest stable) | Event streams, Spin WASM input |
| ClickHouse | 26.7.1 | MergeTree engine, JDBC Sink target |
| CouchDB | 3.5.2 | Document DB, `_changes` feed, MapReduce |
| YugabyteDB | 2026.1.0.1 | Distributed SQL for transactional state |
| ArcadeDB | 26.7.3 | Multi-model graph DB |
| KeyDB | (latest stable) | Clustered in-memory cache, pub-sub, state |
| VictoriaMetrics | 1.148.0 | Cluster mode (vmstorage/vminsert/vmselect) |
| Kargo | 1.11.0 | GitOps promotion engine |
| Argo CD | (latest stable) | GitOps sync engine + ApplicationSet |
| Argo Rollouts | (latest stable) | Progressive delivery (canary/blue-green) |
| Argo Events | (latest stable) | Event-driven automation triggers |
| Argo Workflows | (latest stable) | DAG workflow engine |
| Backstage | (latest stable) | Developer portal, Software Catalog, Golden Path templates |
| KNative | (latest stable) | Serverless scale-to-zero + Eventing |
| Restate | (latest stable) | Stateful workflow/SAGA engine |
| SpinKube | shim v0.25.1 | WASM runtime: Spin v4.0.1, Operator v0.6.1. Helm charts from `spinframework` org. |
| Casdoor | (latest stable) | AuthN: JWT, SSO, OIDC/SAML |
| Casbin | (latest stable) | AuthZ: RBAC + ReBAC (Zanzibar) + ABAC |
| Hasura | (latest stable) | GraphQL federation backend |
| Infisical | (latest stable) | Secrets management with K8s Operator |
| Harbor | (latest stable) | OCI registry with Trivy scanning, Cosign signing |
| Spegel | (latest stable) | P2P container image distribution |

## Structural Seed

### Deployment topology (v1)

```
┌─────────────────────────────────────────────────────┐
│              Dev (talosctl QEMU, single node)        │
│  ┌───────────────────────────────────────────────┐  │
│  │  Envoy Gateway  │  Casdoor  │  Casbin         │  │
│  │  Pulsar + Kafka │  CouchDB  │  YugabyteDB     │  │
│  │  ArcadeDB       │  KeyDB    │  ClickHouse     │  │
│  │  KNative  │ Restate │ SpinKube │ Backstage    │  │
│  │  Kargo │ Argo CD │ Argo Rollouts │ Argo Events│  │
│  │  VictoriaMetrics│ Grafana  │  Harbor / Spegel │  │
│  │  Cilium │ Hubble │ Rook-Ceph (single OSD)     │  │
│  └───────────────────────────────────────────────┘  │
│  Ceph RBD (loop device or thin-LV)                  │
└─────────────────────────────────────────────────────┘

Production (bare-metal, 3+ nodes per region)
  One or more regions, each identical to the above
  but with HA replicas for all stateful services.
  WireGuard VPN for ClusterMesh between regions.
```

### Source tree (monorepo)

```
hpdc/
├── gitops/
│   ├── kargo/
│   │   ├── warehouse-dev.yaml
│   │   ├── warehouse-prod.yaml
│   │   ├── stage-dev.yaml
│   │   └── stage-prod.yaml
│   ├── argocd/
│   │   ├── app-of-apps.yaml
│   │   └── applicationsets/
│   └── overlays/
│       ├── base/                      # Common labels, namespace
│       │   └── kustomization.yaml
│       ├── dev/
│       │   └── kustomization.yaml     # References functions/ + spins/ + secrets
│       └── prod/
│           └── kustomization.yaml
├── platform/
│   ├── cilium/
│   ├── rook-ceph/
│   ├── pulsar/
│   ├── kafka/
│   │   └── kafkatopic.yaml           # Strimzi KafkaTopic definitions
│   ├── couchdb/
│   ├── yugabytedb/
│   ├── arcadedb/
│   ├── clickhouse/
│   ├── keydb/
│   ├── envoy-gateway/
│   │   ├── gateway.yaml              # GatewayClass + Gateway
│   │   ├── routes/                   # HTTPRoute per domain
│   │   └── security-policy.yaml      # SecurityPolicy for extAuth
│   ├── victoriametrics/
│   ├── kargo/
│   ├── argocd/
│   ├── backstage/
│   ├── knative/
│   ├── restate/
│   ├── spinkube/
│   ├── casdoor/
│   ├── casbin/
│   │   ├── deployment.yaml           # Go gRPC ext_authz service
│   │   ├── casbin-model.conf         # RBAC/ReBAC/ABAC model
│   │   └── casbin-policy.csv         # Static policy defaults
│   ├── hasura/
│   ├── harbor/
│   └── spegel/
├── backend/
│   ├── functions/                    # All serverless functions
│   │   ├── knative/                  # Go/Python KNative services, Restate SAGAs
│   │   │   ├── alert-processor/
│   │   │   ├── device-registration/
│   │   │   ├── telemetry-enricher/
│   │   │   └── welcome/              # Stateful counter example
│   │   ├── spin/                     # Rust WASM SpinApps (SpinApp CRD)
│   │   │   ├── counter/              # KeyDB-backed counter
│   │   │   ├── stream/               # Kafka-triggered event processor
│   │   │   ├── kafka-transforms/
│   │   │   └── event-filters/
│   │   └── pulsar/                   # Java Pulsar Functions (JAR)
│   │       ├── telemetry-aggregator/ # JDBC ClickHouse Sink
│   │       └── alert-detector/
│   └── services/                     # Persistent microservices (future)
├── frontend/                         # SPA (shipped from CDN)
├── specs/
│   ├── proto/                        # Protobuf .proto files + schema registry
│   ├── openapi/                      # OpenAPI 3.x specs per route
│   └── asyncapi/                     # AsyncAPI specs for event channels
├── charts/                           # Shared Helm charts
└── docs/                             # Architecture docs, operational runbooks
```

## Capability → Architecture Map

| Capability / Area | Lives in | Governed by |
|-------------------|----------|-------------|
| Telemetry ingestion (FR-1..FR-4) | Pulsar (MoP + gRPC handlers), `/telemetry` route | AD-2, AD-4, AD-5 |
| Stream processing (FR-5..FR-8) | Pulsar Functions → ClickHouse, SpinKube WASM → Kafka | AD-2, AD-3, AD-4 |
| Alert management (FR-9..FR-12) | KNative + Restate, Kafka, KeyDB, CouchDB | AD-2, AD-3, AD-4 |
| Entity management (FR-13..FR-16) | CouchDB, YugabyteDB, ArcadeDB, Hasura `/gql` | AD-2, AD-6 |
| GitOps pipeline (FR-17..FR-21) | Kargo, Argo CD, Argo Rollouts, Argo Events/Workflows, Backstage | AD-9 |
| K8s substrate (FR-22..FR-24) | Talos, Cilium, Rook-Ceph | AD-7, AD-8 |
| Observability (FR-25..FR-29) | VictoriaMetrics, Grafana, OpenTelemetry, Hubble | AD-12 |
| Air-gapped delivery (FR-30..FR-32) | Harbor, Spegel, local Git mirror | AD-10 |
| Multi-region (FR-33..FR-35) | Cilium ClusterMesh, WireGuard, Central hub | AD-11 |
| API Gateway (FR-36..FR-39) | Envoy Gateway, OpenAPI specs | AD-1, AD-2 |
| Security (FR-40..FR-45) | Casdoor, Casbin (RBAC/ReBAC/ABAC), Infisical, mTLS | AD-8, AD-13 |
| AI Agent Engine (FR-46..FR-48) | KNative + Restate, MCP, A2A (deferred to v2) | AD-3 |
| Auth routes | Casdoor (signin/signup) | AD-1, AD-2 |

## Testing & Quality

Three-tier testing pyramid covering every layer from deployment to function logic, with the e2e tier testing the system as a deployed whole.

```
                      ┌─────────────┐
                      │   E2E       │  Playwright + live cluster
                      │  (few)      │  Deployed-system validation
                      ├─────────────┤
                      │ Integration │  In-memory mocks + concurrency
                      │ (some)      │  Inter-function contracts
          ┌───────────┼─────────────┤
          │  Unit     │  Deployment │  Kustomize dry-run, Argo CD app diff
          │ (many)    ├─────────────┤
          │           │  Routes     │  HTTPRoute validation, SecurityPolicy check
          │           ├─────────────┤
          │           │  Functions  │  Go httptest, Rust cargo test, Pulsar test CLI
          └───────────┴─────────────┘
```

### Unit tests — every function independently

| Layer | Tool | What it covers |
|-------|------|----------------|
| Go KNative functions | `go test` + `httptest.NewServer` | Handler logic, error paths, response formats, env-var-driven config |
| Rust SpinApps | `cargo test` (WASM target) | Business logic, KeyDB interaction with mock connection |
| Java Pulsar Functions | Pulsar `Context` test harness | Transform logic, schema compliance, error handling |
| OpenAPI specs | Spectral linting | Spec validity, route/response coverage against implementation |

### Integration tests — inter-function contracts

Each function's integration test validates its contract with dependencies using in-memory fakes:

- **Stateful counter**: in-memory mutex-guarded int mimics KeyDB INCR; tested for sequential increments, concurrent access, timeout propagation, error propagation (e.g., counter unreachable → HTTP 502)
- **Route auth**: verify JWT validation + Casbin ext_authz gRPC responses per role
- **Pulsar → ClickHouse**: batched JDBC Sink write semantics with test ClickHouse instance

### Deployment tests — GitOps correctness

Executed in CI before any Kargo promotion:

| Test | Tool | What it validates |
|------|------|-------------------|
| Kustomize build | `kustomize build` + `kubectl diff` | Overlay produces valid Kubernetes manifests with correct env-specific values |
| Argo CD app diff | `argocd app diff` | No drift between Git state and cluster state for platform components |
| Dry-run apply | `kubectl apply --dry-run=server --server-side` | Manifests are accepted by the Kubernetes API server |
| Kargo Freight check | `kargo verify freight` | Freight contains all required images/configs for the target stage |
| Helm lint | `helm lint` | Chart values pass schema validation |

### Route exposure tests

| Test | Tool | What it validates |
|------|------|-------------------|
| Gateway API validation | `kubectl apply --dry-run=server -f httproute.yaml` | HTTPRoute, GRPCRoute, TLSRoute resources accepted |
| SecurityPolicy wiring | Integration test with mock ext_authz | JWT+API-Key auth flows, RBAC/ReBAC/ABAC decision propagation |
| Rate limiting | Integration test | Per-route rate limits enforced; back-pressure triggers |

### E2E tests — full system on live cluster

Playwright (or equivalent) tests against the deployed platform:

- **Welcome counter** (`welcome-counter.spec.ts`): GET `/api/welcome`, verify `"Welcome (N)"` format, sequential increment across 5 calls, Content-Type header, 502 on counter down
- **Telemetry ingestion**: POST to `/telemetry`, verify message reaches ClickHouse via Pulsar Functions within SLA
- **Alert lifecycle**: POST alert to `/events`, verify state transitions (initial → acknowledged → resolved → closed) through the API
- **Entity CRUD**: Create/read/update/delete through `/data` to CouchDB, verify via `/gql`
- **Auth enforcement**: Verify 401 on missing/expired JWT, 403 on unauthorized role, 200 on valid token with correct permissions
- **Air-gapped deployment**: Verify Kargo promotion completes from local Harbor, Spegel peers distribute image without internet

## Deferred

| Decision | Why deferred | Revisit when |
|----------|-------------|--------------|
| Central hub SPA framework (React/Vue/Angular) | Out of MVP scope. MVP uses Backstage + Grafana for visibility | v2 planning starts |
| Full AI Agent Engine (MCP/A2A) | Non-goal for MVP. Basic LLM alert analysis may be included | v2 planning starts |
| Hasura full federation (YugabyteDB + CouchDB + ClickHouse) | MVP uses direct DB access; Hasura deployed but not fully federated | v2 planning starts |
| Production region-specific configs (compliance, data locality) | v1 is single-cluster MVP on dev machine | Before production deployment |
| Backup/DR strategy (etcd backup, Ceph snapshots, DB backup) | Operational concern, not architecture-invariant | Before production deployment |
| Resource sizing per environment | Depends on actual load testing results | After MVP baseline established |
| Canary analysis thresholds (error rate, latency p99) | Tuning depends on real workload patterns | Before production deployment |
| Casbin policy schema format (PERM model, relationship tuples) | Policy design is implementation detail of story creation | Sprint 1 story creation |
| Argo Workflows vs KNative+Restate for specific scenarios | Complementary — exact split depends on use case | Per-story implementation |
| Observability storage backend (Ceph vs local vs S3) | Default to Ceph; optimization deferred | When VictoriaMetrics performance tuning begins |
| Pulsar topic partition counts | Configurable per device_type + region_id; exact count depends on load | Per-deployment configuration |
