---
title: Enterprise GitOps Platform — HPDC
created: 2026-07-21
updated: 2026-07-21
status: final
---

# PRD: Enterprise GitOps Platform — HPDC

*A security platform for high-RPS telemetry ingestion and processing from IoT devices, with alert detection, real-time messaging, distributed workload processing, and AI agent orchestration — built on a GitOps-driven progressive delivery pipeline for offline-first, bare-metal multi-cluster deployment.*

---

## 1. Vision

**v1 is a proof-of-concept:** the full pipeline running on a local dev machine, demonstrating telemetry ingestion at 100K+ RPS, real-time processing, alert detection and response, device state tracking, and the complete GitOps deployment lifecycle.

**Enterprise GitOps Platform** is an offline-first, security-focused IoT telemetry and alert management system built to operate at scale across geographically distributed bare-metal clusters. Drawing patterns from the existing with-gsd/ project, the platform ingests high-throughput telemetry from IoT devices, processes it in real-time, detects security alert signals, and reacts — sending signals back to devices, triggering external hooks, and providing real-time context to operators and AI agents. Platform delivery is GitOps-driven via Kargo, Argo CD, Argo Rollouts, Argo Events, and Backstage. Each regional cluster maintains data sovereignty; a central hub provides cross-region visibility. Scales from a single developer laptop to hundreds of clusters — millions of RPS, fail-tolerant, distributed processing. Air-gapped delivery via Harbor, Spegel P2P, and local Git mirrors — always GitOps-mediated, never a static package.

---

## 2. Target User

### 2.1 Jobs To Be Done

- **Platform Engineer:** "I need to provision, bootstrap, and operate Kubernetes clusters at air-gapped sites without internet access, with full GitOps-driven delivery and centralized observability."
- **SOC/Security Analyst:** "I need to detect security alerts from IoT telemetry in real-time, understand the context (device state, location, history), and respond within seconds — not minutes."
- **Backend Developer:** "I need to deploy new telemetry processing services via self-service templates without waiting for platform team approval."
- **Business Stakeholder:** "I need to see platform metrics — alert throughput, device coverage, SLA compliance, cost per cluster — to make operational decisions."
- **Platform Administrator:** "I need to manage users, roles, and permissions across the organization with fine-grained access control that scales from single-cluster to multi-region."

### 2.2 Non-Users (v1)

- **External customers** consuming the platform as a SaaS — v1 is self-hosted, offline-first.
- **IoT device manufacturers** — the platform consumes telemetry; it does not manage device firmware or hardware.
- **Cloud providers** — the platform runs entirely on-premises with no cloud dependency.

### 2.3 Key User Journeys

**UJ-1. Platform engineer bootstraps a new regional cluster via GitOps pipeline.**
Marcus, a platform engineer at a defense contractor, receives a shipment of 3 bare-metal servers for a new regional deployment in Germany. He plugs them into the internal VPN, PXE-boots Talos Linux, and registers the cluster with the central hub. Argo CD syncs the platform stack — Cilium (eBPF networking), Rook-Ceph (storage), Harbor (OCI registry), Kargo, and all platform services — from Git within 15 minutes. Backstage discovers the new cluster and shows it in the platform dashboard. Marcus deploys the first workload via a Backstage Golden Path template, Kargo promotes it through dev → staging, and Argo Rollouts performs a canary deployment. **Edge case:** if a server fails PXE boot, the bootstrap script retries 3 times then surfaces a clear error with the failing MAC address and instructions for manual intervention.

**UJ-2. SOC analyst investigates and responds to a critical alert.**
Aisha, a SOC analyst on night shift, gets a push notification on her phone: "CRITICAL — Drone fleet #7, geofence violation detected, Region: EU-Central." She opens the central hub SPA, sees the alert in the dashboard with real-time telemetry — the drone's GPS path, last 5 minutes of sensor data, and device health status. She acknowledges the alert (state transitions initial → acknowledged), reviews the AI agent's suggested response (automated geofence lockout), approves it, and the system sends the lockdown command to the device communication microservice. The full interaction takes under 90 seconds. She adds investigation notes and resolves the alert. The workflow engine generates a compliance report automatically. **Edge case:** if the AI agent suggestion is ambiguous (confidence < 70%), the system escalates to a manager for manual review instead of suggesting an action.

**UJ-3. Developer scaffolds a new telemetry processing service via Backstage.**
Raj, a backend developer, opens Backstage and selects the "Telemetry Processor" Golden Path template. He fills in the form: service name, Pulsar topic to consume from, ClickHouse target table, processing logic description. Backstage scaffolds a repo with Dockerfile, Helm chart, catalog-info.yaml, Kargo warehouse config, and Argo CD ApplicationSet entry. Raj pushes his processing logic, CI builds the image, pushes to Harbor, Kargo detects the new image and auto-promotes to dev. Argo CD syncs the workload to the dev cluster within 60 seconds. Raj sees his service running in the Backstage service catalog with live metrics from VictoriaMetrics. **Edge case:** if the scaffolded Helm chart has validation errors, the Backstage template shows inline errors before repo creation.

**UJ-4. Platform administrator manages user permissions across the organization.**
Elena, a platform administrator, needs to grant a new contractor read-only access to the EU-Central region's telemetry data. She opens the admin panel, creates a new user record in PostgreSQL via the API, assigns the "viewer" role, and creates a relationship tuple linking the user to the EU-Central company entity (Zanzibar ReBAC). She adds an ABAC attribute restricting access to read-only operations during business hours (09:00–18:00 CET). The contractor can now view telemetry dashboards but cannot acknowledge alerts or modify device state. Elena audits the permission change in the security log. **Edge case:** if the contractor's access conflicts with an existing policy (e.g., they already have write access via a group), the system flags the conflict and asks Elena to resolve it before applying.

**UJ-5. Business stakeholder reviews platform metrics and alert reports.**
David, a VP of Operations, opens the Grafana dashboard to review quarterly platform performance. He sees: 47M alerts processed across 3 regions, 99.97% platform availability, average alert response time 42 seconds, 12 geofence violations detected and resolved, cost per cluster trending down as Spegel P2P reduced image pull bandwidth by 63%. He drills into EU-Central specifically, sees device coverage (340 active devices), alert breakdown by severity, and SLA compliance (99.9% for critical alerts). He exports the report as PDF for the board meeting. **Edge case:** if a region's metrics are stale (> 5 minutes), the dashboard shows a warning banner and the last known timestamp.

---

## 3. Glossary

- **A2A** — Agent-to-Agent protocol for inter-agent communication and task delegation.
- **ABAC** — Attribute-Based Access Control; evaluates dynamic attributes for permission decisions.
- **Alert Signal** — Structured event via API indicating a security condition requiring response.
- **API-Key** — Auth token in `X-API-Key` header. Used for messaging routes at Envoy Gateway.
- **ApplicationSet** — Argo CD resource generating Application manifests from parameters.
- **ArcadeDB** — Multi-model database for graph traversals, entity lineage, and relationship queries.
- **Argo CD** — GitOps sync engine reconciling Git state to Kubernetes clusters.
- **Argo Events** — Event-driven automation triggering workflows from Git changes or external signals.
- **Argo Rollouts** — Progressive delivery controller for canary/blue-green deployments with automated rollback.
- **Argo Workflows** — DAG-based workflow engine for multi-step pipeline tasks.
- **Backstage** — Developer portal with Software Catalog and Golden Path Templates.
- **Casbin** — Authorization library implementing RBAC, ReBAC, and ABAC models.
- **Casdoor** — AuthN platform providing JWT validation, SSO, and identity federation.
- **Ceph** — Distributed block (RBD) and file (CephFS) storage via CSI drivers.
- **Cilium** — eBPF-based CNI with kube-proxy replacement, L2 load balancing, and ClusterMesh.
- **ClickHouse** — Columnar analytical database for processed telemetry storage.
- **Common Envelope** — Standardized message format: `device_id`, `device_type`, `event_type`, `timestamp`, `payload`, `region_id`.
- **CouchDB** — Document database storing entity hierarchy with change feed for downstream consumption.
- **Envoy Gateway** — Kubernetes Gateway API ingress handling TLS, rate limiting, routing, and ext_authz.
- **Freight** — Kargo artifact representing a promotable set of images and config changes.
- **Golden Path Template** — Backstage scaffolding template generating service repos with GitOps manifests.
- **Harbor** — OCI registry with vulnerability scanning, image signing, and Helm chart storage.
- **Hasura** — GraphQL engine federating YugabyteDB, CouchDB, and ClickHouse at `/gql`.
- **Infisical** — Secrets management with Kubernetes Operator for runtime secret injection.
- **Kargo** — GitOps lifecycle promotion engine with image detection and environment stages.
- **KeyDB** — In-memory store (Redis-compatible) for sub-ms hot state caching.
- **KNative** — Serverless platform for scale-to-zero and event-driven workloads on Kubernetes.
- **KVM/QEMU** — Virtualization for local dev cluster provisioning via `talosctl cluster create`.
- **MCP** — Model Context Protocol for structured AI agent tool invocation.
- **OpenTelemetry Collector** — Vendor-agnostic OTLP trace receiver exporting to configured backends.
- **Pulsar** — Primary messaging engine with native MQTT/gRPC handlers, Pulsar Functions, and tiered storage.
- **Pulsar Functions** — Serverless compute for aggregation, windowing, and ClickHouse JDBC Sink writes.
- **Kafka** — Secondary stream engine for alert signals, event workflows, and Spin WASM consumption.
- **Spin Function** — WASM workload via SpinKube for stateless Kafka stream processing, sub-10ms latency.
- **Stage** — Kargo resource defining an environment tier with promotion rules.
- **Sync Wave** — Argo CD ordering: CRDs → Network → Storage → Platform Core → Applications.
- **Talos Linux** — Immutable, API-managed Kubernetes OS. Declarative YAML, no SSH/bash.
- **VMCluster** — VictoriaMetrics cluster mode: vmstorage, vminsert, vmselect components.
- **Warehouse** — Kargo resource polling registries for new image digests.
- **WireGuard** — VPN overlay for cross-cluster ClusterMesh connectivity.
- **YugabyteDB** — Distributed SQL for sessions, workflow state, configuration, and billing records.

---

## 4. Features

Assumptions are indexed in §9.

### 4.1 Telemetry Ingestion

**Description:** Dual-engine ingestion: Pulsar (primary, MQTT/gRPC native) + Kafka (secondary, alert signals, Spin WASM). Topics partitioned by device type and region.

**Functional Requirements:**

#### FR-1: Multi-protocol device ingestion
The system accepts telemetry payloads via MQTT, HTTP, and gRPC at the ingestion edge. Pulsar protocol handlers (MoP and gRPC handler) handle MQTT and gRPC natively, eliminating separate protocol adapters. Realizes UJ-1.

**Consequences (testable):**
- System accepts a valid MQTT publish and produces a message on the internal Pulsar topic within 50ms.
- System accepts an HTTP POST to the ingestion endpoint and produces a message on the internal Pulsar topic within 50ms.
- System accepts a gRPC telemetry push and produces a message on the internal Pulsar topic within 50ms.
- System returns HTTP 429 when ingestion rate exceeds configured capacity per device type.

**Out of Scope:**
- Device authentication at the edge (handled by §4.10 Security)

#### FR-2: Common envelope normalization
All inbound payloads are normalized into a standard envelope containing `device_id`, `device_type`, `event_type`, `timestamp`, `payload`, and `region_id` before publishing to internal topics.

**Consequences (testable):**
- System rejects payloads missing `device_id` or `timestamp` with HTTP 400 and a structured error.
- System preserves original payload bytes in the `payload` field untransformed.
- Normalized message size does not exceed 64KB; system rejects oversized payloads with HTTP 413.

#### FR-3: Topic partitioning by device type and region
Internal Pulsar topics are partitioned by `device_type` and `region_id` to enable parallel consumption by downstream processors.

**Consequences (testable):**
- System creates topics with configurable partition count at bootstrap.
- Messages with the same `device_type` + `region_id` land on the same partition (ordering guarantee).
- Partition count is adjustable without data loss (Pulsar supports online topic splits).

#### FR-4: Back-pressure management
The ingestion layer applies back-pressure when downstream consumers lag, preventing memory exhaustion and message loss.

**Consequences (testable):**
- System applies exponential backoff to producers when consumer lag exceeds configured threshold.
- System drops messages (with metric increment) when buffer is full rather than blocking producers.
- System emits `ingestion_dropped_total` counter with `reason` label when messages are dropped.

**Feature-specific NFRs:**
- Ingestion throughput: sustained 100K RPS per region with p99 latency < 100ms from edge to topic.
- Memory ceiling: ingestion pods do not exceed 2GB RSS under peak load.

---

### 4.2 Real-time Processing

**Description:** Two pipelines consume normalized telemetry: Pulsar Functions (aggregation, windowing, JDBC Sink to ClickHouse) and Spin WASM functions (stateless Kafka transforms, sub-10ms latency).

**Functional Requirements:**

#### FR-5: Spin function stream processing
Spin functions deployed via SpinKube consume from Kafka topics and perform stateless transformations (field mapping, enrichment, filtering) with sub-10ms processing latency per message.

**Consequences (testable):**
- System deploys Spin functions as WASM workloads via `containerd-shim-spin` on compatible nodes.
- System processes a single message through a Spin function in < 10ms (p99).
- System scales Spin function replicas based on Kafka consumer lag.

#### FR-6: Pulsar function telemetry processing
Pulsar functions consume from Pulsar topics and perform aggregation, windowing, and batched writes to ClickHouse via JDBC Sink.

**Consequences (testable):**
- System runs Pulsar functions with configurable `--parallelism` matching partition count.
- System writes to ClickHouse in batches of 25,000 records with 500ms flush interval.
- System confirms ClickHouse write success via JDBC Sink acknowledgment; failed batches are retried 3 times before DLQ.

#### FR-7: ClickHouse analytical storage
Processed telemetry is stored in ClickHouse tables using MergeTree/ReplacingMergeTree engines, partitioned by time and device type.

**Consequences (testable):**
- System creates `device_metrics` table with `ORDER BY (device_type, processed_timestamp)`.
- System supports time-range queries returning 1M rows in < 2 seconds.
- System applies configurable retention policies per environment (dev: 24h, staging: 7d, production: configurable).

#### FR-8: Hot state caching in KeyDB
Frequently accessed device state and alert context are cached in KeyDB for sub-millisecond read access.

**Consequences (testable):**
- System reads cached device state from KeyDB in < 1ms (p99).
- System evicts stale entries based on configurable TTL (default: 5 minutes).
- System falls back to CouchDB/ClickHouse on KeyDB cache miss without error propagation.

---

### 4.3 Alert Signal Management

**Description:** Alert signals arrive via API as directed streams. State machine workflow (initial → acknowledged → investigating → resolved → closed). KNative + Restate orchestrates business logic. KeyDB tracks active alert state.

**Functional Requirements:**

#### FR-9: Alert signal ingestion via directed streams
The system accepts alert signals from external APIs as directed streams, enabling parallel processing of concurrent alerts.

**Consequences (testable):**
- System accepts alert signals via dedicated API endpoint with structured payload (alert_id, device_id, severity, timestamp, metadata).
- System routes alert signals to dedicated Kafka topics separate from normal telemetry.
- System processes concurrent alert signals without blocking telemetry ingestion.

#### FR-10: Alert state machine
Each alert transitions through a stateful workflow: initial → acknowledged → investigating → resolved → closed. State transitions are persisted in CouchDB and cached in KeyDB.

**Consequences (testable):**
- System transitions alert state only through valid paths (no skip from initial to closed).
- System persists state transition to CouchDB within 100ms.
- System updates KeyDB cache within 50ms of CouchDB write.
- System rejects invalid state transitions with HTTP 409 and current state.

#### FR-11: Automated alert response
The system triggers automated responses when alert conditions are met — sending signals to IoT devices (via device communication microservice), triggering external webhooks, or starting workflow processes.

**Consequences (testable):**
- System invokes device communication microservice within 200ms of alert trigger.
- System delivers webhook payloads within 500ms with retry logic (3 attempts, exponential backoff).
- System logs all automated responses with correlation ID linking to alert_id.

#### FR-12: Human-in-the-loop alert handling
Operators can acknowledge, investigate, and resolve alerts through the central hub SPA, with full audit trail of actions taken.

**Consequences (testable):**
- System displays active alerts with device context and telemetry summary in the central hub.
- System records operator action, timestamp, and notes on each state transition.
- System prevents concurrent state modification by two operators (optimistic locking).

---

### 4.4 Entity & Resource Management

**Description:** Triple-database architecture: CouchDB for document hierarchy, ArcadeDB for graph traversals, YugabyteDB for relational state — each chosen for its access pattern strength. Hasura federates all stores behind GraphQL.

**Functional Requirements:**

#### FR-13: Triple-database entity storage
CouchDB stores entity hierarchy (companies → clients → devices/assets) as documents; ArcadeDB stores graph-structured relationship data (entity connections, lineage, traversals); YugabyteDB stores system internal resources as relational rows. All three are accessible to all processing layers.

**Consequences (testable):**
- System accepts entity documents in CouchDB via API with per-type schema validation.
- System accepts graph data in ArcadeDB via API with vertex/edge schema validation.
- System accepts internal resource records in YugabyteDB via API with relational schema validation.
- System exposes CouchDB `_changes` feed for real-time change consumption.
- System supports ArcadeDB graph traversal queries (shortest path, neighbor discovery) with < 100ms response for 10K-node graphs.
- System provides YugabyteDB SQL interface for relational queries.
- KNative services can read/write all three databases within a single workflow step.
- Spin functions can read/write all three databases within a single function invocation.
- All data persists to Ceph RBD volumes.

#### FR-14: Entity CRUD and state management
The system provides CRUD operations for all entity types across both databases with role-based access control and audit logging.

**Consequences (testable):**
- System supports create, read, update, delete for companies, clients, devices, and assets.
- System enforces role-based access per entity type (§4.10 Security).
- System logs all entity mutations with actor, timestamp, and change diff.
- System supports bulk operations (up to 1000 entities per request) for batch provisioning.

#### FR-15: Change-driven business logic via KNative + Restate
KNative services with Restate react to CouchDB and YugabyteDB change feeds, triggering business logic in a stateful, idempotent manner with access to both data stores.

**Consequences (testable):**
- System invokes KNative service within 500ms of change event from either database.
- KNative service reads/writes both CouchDB and YugabyteDB within the same workflow step.
- System processes change events exactly-once via Restate virtual object state.
- System handles KNative service failure with automatic retry and dead-letter queue.

#### FR-16: Unified GraphQL API via Hasura
Hasura exposes a GraphQL API that federates YugabyteDB, CouchDB, and ClickHouse, enabling cross-store queries that combine entity state with internal resources, telemetry, and analytics.

**Consequences (testable):**
- System resolves a GraphQL query joining CouchDB entities with YugabyteDB resources in < 2 seconds.
- System enforces Hasura permissions model per user role (§4.10 Security).
- System exposes the GraphQL endpoint at `/gql`.

---

### 4.5 GitOps Platform Infrastructure

**Description:** GitOps-driven delivery pipeline: Kargo (lifecycle promotion), Argo CD (sync), Argo Rollouts (progressive delivery), Argo Events + Workflows (event-driven automation), Backstage (developer portal). Talos Linux + Cilium + Rook-Ceph substrate.

**Functional Requirements:**

#### FR-17: Backstage developer portal and workload delivery
Backstage provides a Software Catalog, Golden Path Templates for scaffolding, and workload delivery for KNative and Spin functions. Monitoring dashboards show deployed service health.

**Consequences (testable):**
- System deploys Backstage with Argo CD plugin showing sync status per application.
- System provides Golden Path template that scaffolds a repo with Dockerfile, Helm chart, catalog-info.yaml, Kargo + ArgoCD manifests.
- System registers all deployed services in the Software Catalog.
- System supports KNative service deployment via Backstage templates.
- System supports Spin function deployment via Backstage templates.

#### FR-18: Kargo lifecycle promotion
Kargo manages promotion across environments via Warehouse (image detection), Stage definitions (dev/staging/production), and Freight (promotable artifacts).

**Consequences (testable):**
- System detects new container images in Harbor via Warehouse SemVer subscription.
- System auto-promotes to dev Stage on new image detection.
- System requires manual approval for production Stage promotion.
- System writes updated image digests to Kustomize overlays and commits back to Git.

#### FR-19: Argo CD sync engine
Argo CD reconciles Git state to target clusters via ApplicationSet and Sync Waves, with App-of-Apps pattern for infrastructure bootstrap.

**Consequences (testable):**
- System deploys Argo CD with ApplicationSet using directory generator for per-stage workload sync.
- System orders Sync Waves: -10 (CRDs) → -5 (Network) → -4 (Storage) → -3 (Platform Core) → 1 (Applications).
- System syncs workload changes within 60 seconds of Git commit.
- System supports multi-cluster deployment via Argo CD cluster secrets.

#### FR-20: Argo Rollouts progressive delivery
Argo Rollouts handles canary deployments, blue-green transitions, and automated rollback based on analysis metrics.

**Consequences (testable):**
- System deploys Argo Rollouts with canary strategy (90/10 split default).
- System performs automated canary analysis using VictoriaMetrics queries.
- System promotes canary to full rollout when analysis passes.
- System rolls back automatically when error rate exceeds threshold.
- System supports blue-green deployment strategy as an alternative.

#### FR-21: Argo Events and Workflows
Argo Events orchestrates event-driven workflows triggered by Git changes, image updates, or external signals. Argo Workflows runs multi-step pipeline tasks.

**Consequences (testable):**
- System triggers Argo Events sensors on Git push, Harbor image update, and Kargo Freight creation.
- System runs Argo Workflows for build → test → scan → deploy pipelines.
- System supports DAG-based workflow definitions with retry and error handling.
- System logs all workflow executions with status, duration, and output.

#### FR-22: Talos Linux substrate
Talos Linux provides immutable, API-managed Kubernetes substrate with no SSH, no bash, and mTLS gRPC API.

**Consequences (testable):**
- System provisions Talos nodes via declarative machine configuration YAML.
- System manages cluster lifecycle (upgrade, scale, reset) via Talos API.
- System disables kube-proxy (Cilium replaces via eBPF).

#### FR-23: Cilium eBPF networking
Cilium provides CNI, kube-proxy replacement, L2 load balancing, and ClusterMesh for multi-cluster networking.

**Consequences (testable):**
- System deploys Cilium with `kubeProxyReplacement: true`.
- System provides L2 load balancing via `CiliumL2AnnouncementPolicy` and `CiliumLoadBalancerIPPool`.
- System supports ClusterMesh for cross-cluster service discovery in production.

#### FR-24: Rook-Ceph persistent storage
Rook-Ceph provides block (RBD) and file (CephFS) storage with CSI drivers for dynamic provisioning.

**Consequences (testable):**
- System provisions CephCluster with OSDs on dedicated disks.
- System provides StorageClass for RBD and CephFS with dynamic provisioning.
- System persists all stateful workload data (CouchDB, YugabyteDB, ClickHouse, KeyDB) to Ceph.

---

### 4.6 Observability & Reporting

**Description:** Metrics (VictoriaMetrics cluster), logs (vmlog), traces (OpenTelemetry), dashboards (Grafana), alerts (AlertManager).

**Functional Requirements:**

#### FR-25: VictoriaMetrics cluster metrics
VictoriaMetrics cluster mode provides scalable metrics storage with vmstorage, vminsert, and vmselect.

**Consequences (testable):**
- System deploys VictoriaMetrics cluster with configurable vmstorage/vminsert/vmselect replica count.
- System scrapes metrics via vmagent from all platform components.
- System supports PromQL queries with < 2 second response time for 24h range.
- System applies retention policies per environment (dev: 24h, staging: 7d, production: configurable).

#### FR-26: Log collection via vmlog
vmlog collects stdout/stderr from all pods and indexes them for search and analysis.

**Consequences (testable):**
- System collects logs from all pods in the cluster.
- System supports log search by namespace, pod, and content within 5 seconds.
- System applies log retention policies per environment.

#### FR-27: Distributed tracing via OpenTelemetry Collector
OpenTelemetry Collector receives OTLP traces from instrumented services and exports to VictoriaMetrics or Jaeger.

**Consequences (testable):**
- System accepts OTLP traces on standard collector endpoint.
- System exports traces to configured backend (VictoriaMetrics or Jaeger).
- System supports trace sampling with configurable rate per service.

#### FR-28: Grafana dashboards and AlertManager
Grafana provides dashboards for platform metrics, alert reports, and SLA monitoring. AlertManager routes alerts to configured notification channels.

**Consequences (testable):**
- System deploys Grafana with pre-configured dashboards for platform health, telemetry throughput, and alert statistics.
- System deploys AlertManager with configurable routing rules.
- System provides business stakeholder dashboards: alert throughput, device coverage, SLA compliance, cost per cluster.

#### FR-29: Cilium Hubble network observability
Hubble provides real-time network flow visibility, DNS, HTTP/gRPC traffic, and service dependency mapping at eBPF level — no sidecar overhead.

**Consequences (testable):**
- System deploys Hubble with Grafana dashboards for network flows, DNS, and HTTP/gRPC traffic.
- System provides service dependency map showing inter-service communication patterns.
- System supports network policy visualization (allowed/denied flows).
- Hubble data is queryable via PromQL in Grafana.

---

### 4.7 Air-gapped GitOps Delivery

**Description:** Harbor (local OCI registry), Spegel (P2P image distribution), local Git mirror. Delivery always GitOps-mediated.

**Functional Requirements:**

#### FR-30: Local Harbor OCI registry
Harbor serves as the local OCI registry with vulnerability scanning and image signing for air-gapped environments.

**Consequences (testable):**
- System deploys Harbor with Trivy/Clair scanning enabled on push.
- System rejects images with high-priority CVEs (configurable threshold).
- System supports Cosign image signature verification.
- System stores Helm charts as OCI artifacts.
- System pre-populates Harbor with required images and charts for air-gapped deployment.

#### FR-31: Spegel P2P image distribution
Spegel DaemonSet provides peer-to-peer container image distribution at the containerd level, reducing dependency on central registry during scale-up.

**Consequences (testable):**
- System deploys Spegel as DaemonSet on all worker nodes.
- System serves cached images to peers without hitting central registry.
- System reduces image pull time by > 50% during multi-pod scale-up events.

#### FR-32: Local Git mirror
Git repositories are mirrored locally for air-gapped GitOps operations.

**Consequences (testable):**
- System supports GitLab self-hosted or Gitea as local Git mirror.
- System mirrors gitops-infra, gitops-workloads, and app-source-code repositories.
- System GitOps pipeline operates against local mirror without internet access.

---

### 4.8 Multi-region Federation

**Description:** Regional clusters maintain data sovereignty via Cilium ClusterMesh and WireGuard VPN overlay. Central hub SPA provides cross-region visibility.

**Functional Requirements:**

#### FR-33: Cross-cluster service discovery via ClusterMesh
Cilium ClusterMesh enables cross-cluster service discovery and connectivity across regions via VPN overlay.

**Consequences (testable):**
- System establishes ClusterMesh between regional clusters over WireGuard/Netmaker VPN.
- System discovers services across clusters without manual configuration.
- System routes cross-cluster traffic via encrypted VPN tunnel.

#### FR-34: Regional data sovereignty
Each region maintains its own data stores (ClickHouse, CouchDB, YugabyteDB) with data locality — no cross-region data replication by default.

**Consequences (testable):**
- System deploys independent data stores per region.
- System does not replicate data across regions without explicit configuration.
- System routes queries to the regional data store for the requesting region.

#### FR-35: Central hub cross-region visibility
The central hub SPA queries regional cluster APIs for cross-region visibility, reporting, and management without storing regional data.

**Consequences (testable):**
- System central hub queries regional APIs with region-scoped authentication.
- System displays aggregated metrics across regions in dashboards.
- System supports per-region drill-down to detailed entity and alert state.

---

### 4.9 API Gateway

**Description:** Envoy Gateway with 5-route table. JWT auth for /data, /api, /gql; API-Key for /events, /telemetry. See §4.10 for authN/authZ.

| Route | Backend | AuthN | AuthZ |
|-------|---------|-------|-------|
| `/data/*` | CouchDB | Casdoor JWT | Casbin (RBAC/ReBAC/ABAC) |
| `/api/*` | KNative functions | Casdoor JWT | Casbin (RBAC/ReBAC/ABAC) |
| `/gql` | Hasura GraphQL | Casdoor JWT | Casbin (RBAC/ReBAC/ABAC) |
| `/events/*` | Kafka | API-Key header (EG native) | None |
| `/telemetry/*` | Pulsar | API-Key header (EG native) | None |

**Functional Requirements:**

#### FR-36: Envoy Gateway edge routing
Envoy Gateway routes external traffic to internal services via Kubernetes Gateway API resources (HTTPRoute, GRPCRoute, TLSRoute).

**Consequences (testable):**
- System routes `/data/*` to CouchDB via HTTPRoute.
- System routes `/api/*` to KNative services via HTTPRoute (e.g. `/api/welcome` → welcome function, `/api/telemetry` → telemetry function).
- System routes `/gql` to Hasura via HTTPRoute.
- System routes `/events/*` to Kafka via HTTPRoute.
- System routes `/telemetry/*` to Pulsar via HTTPRoute.
- System applies rate limiting per route with configurable limits.

#### FR-37: TLS termination
Envoy Gateway handles TLS termination at the edge, with certificate management via cert-manager or manual provisioning.

**Consequences (testable):**
- System terminates TLS before routing to backend services.
- System supports automated certificate renewal via cert-manager.
- System rejects plaintext HTTP requests at the gateway (configurable per route).

#### FR-38: API-key authentication for messaging routes
Kafka (`/events`) and Pulsar (`/telemetry`) routes use simple API-key authentication via `X-API-Key` header, validated natively by Envoy Gateway header matching — no Casdoor or Casbin involved.

**Consequences (testable):**
- System validates `X-API-Key` header on `/events/*` and `/telemetry/*` routes at Envoy Gateway.
- System rejects requests with missing or invalid API key with HTTP 401.
- System supports multiple valid API keys configured as Envoy Gateway secrets.
- Requests to `/events/*` and `/telemetry/*` do NOT pass through Casdoor or Casbin.

#### FR-39: OpenAPI specification governance
Swagger/OpenAPI specifications in YAML serve as the source-of-truth contract for all API endpoints, stored in Git for internal and external consumers.

**Consequences (testable):**
- System stores OpenAPI specs in `specs/` directory of the Git repository.
- System validates API implementations against OpenAPI specs in CI pipeline.
- System exposes Swagger UI for API documentation at `/docs`.
- System generates client SDKs from OpenAPI specs (optional, configurable).

---

### 4.10 Security

**Description:** Triple access control: RBAC (base roles), ReBAC (Zanzibar via Casbin), ABAC (attribute-based policies). Casdoor for AuthN. Infisical for secrets.

**Functional Requirements:**

#### FR-40: Authentication via Casdoor
Casdoor provides JWT-based authentication at the Envoy Gateway edge for `/data`, `/api`, and `/gql` routes, supporting SSO and identity federation.

**Consequences (testable):**
- System validates JWT tokens at Envoy Gateway before routing to backend services.
- System rejects requests with invalid/missing tokens with HTTP 401.
- System supports SSO integration via OIDC/SAML with external identity providers.
- System issues refresh tokens with configurable expiration.

#### FR-41: RBAC — Role-Based Access Control
PostgreSQL stores base role assignments (manager, operator, administrator, technic, developer, CEO, client) and Casbin enforces them.

**Consequences (testable):**
- System assigns roles to users with configurable scope (per company, per client, per device group).
- System evaluates role-based permissions in < 5ms (p99).
- System supports role hierarchy (admin > manager > operator > viewer).
- System logs all role assignments and changes.

#### FR-42: ReBAC — Relationship-Based Access Control (Google Zanzibar)
Casbin enforces Zanzibar-style relationship-based permissions — access is derived from user-object relationships (e.g., "user X is manager of company Y → can view devices in Y").

**Consequences (testable):**
- System stores user, object, and relationship tuples in PostgreSQL.
- System evaluates relationship-based permissions via Casbin gRPC ext_authz in < 5ms (p99).
- System supports relationship propagation (e.g., company admin inherits access to all clients and devices).
- System supports policy updates without gateway restart (hot-reload).

#### FR-43: ABAC — Attribute-Based Access Control
Attribute-based policies evaluate dynamic attributes (time of day, location, device state, risk level, clearance level) for fine-grained access decisions.

**Consequences (testable):**
- System evaluates ABAC policies based on request attributes (user attributes, resource attributes, environment attributes).
- System supports time-based access restrictions (e.g., "operator can acknowledge alerts only during shift hours").
- System supports risk-based escalation (e.g., "high-risk alert requires manager approval").
- System evaluates ABAC policies in < 10ms (p99) combined with RBAC/ReBAC.

#### FR-44: Secrets management via Infisical
Infisical Kubernetes Operator manages secrets injection into pods at runtime.

**Consequences (testable):**
- System injects secrets via InfisicalSecret CRD into target pods.
- System rotates secrets without pod restart (dynamic secret support).
- System logs all secret access with actor and timestamp.

#### FR-45: mTLS for inter-service communication
All intra-cluster service communication uses mTLS, enforced by Cilium service mesh.

**Consequences (testable):**
- System rejects plaintext HTTP between services within the cluster.
- System auto-rotates certificates via Cilium SPIFFE/SPIRE integration.

---

### 4.11 AI Agent Engine

**Description:** LLM integration for alert analysis, MCP for tool invocation, A2A for inter-agent communication.

**Functional Requirements:**

#### FR-46: LLM integration for decision support
The system integrates LLMs for natural language processing, alert analysis, and decision support with scoped permissions.

**Consequences (testable):**
- System invokes LLM inference via configured provider endpoint.
- System constrains LLM output to actionable recommendations (not autonomous actions without approval).
- System logs all LLM interactions with input, output, and decision context.
- System supports model selection per use case (configurable).

#### FR-47: MCP tool invocation
The system uses Model Context Protocol (MCP) for structured tool invocation by agents — querying databases, calling APIs, triggering workflows.

**Consequences (testable):**
- System exposes platform capabilities as MCP-compatible tools.
- System validates agent tool invocations against security policies (§4.10).
- System logs all tool invocations with agent ID, tool name, parameters, and result.

#### FR-48: Agent-to-Agent communication (A2A)
Agents communicate with each other via A2A protocols for coordinated decision-making and task delegation.

**Consequences (testable):**
- System supports agent registration and discovery.
- System routes agent-to-agent messages via authenticated channels.
- System prevents unauthorized agent impersonation.

---

## 5. Non-Goals (Explicit)

- **Not a cloud-hosted SaaS.** The platform is offline-first, deployed on bare-metal inside internal VPN. No cloud dependency, no managed service offering.
- **Not a general-purpose Kubernetes platform.** This is a security-focused IoT telemetry and alert management system. It does not aim to be a generic application hosting platform.
- **Not a replacement for existing CRM/WMS/ERP.** The platform manages device/entity state and integrates with external systems. It does not replace standalone CRM, WMS, or ERP products.
- **Not bidirectional device communication in v1.** v1 focuses on telemetry ingestion and processing only. Sending signals back to IoT devices is deferred to a dedicated microservice post-v1.
- **Not real-time video or media streaming.** The platform processes structured telemetry data (JSON/Avro/Protobuf payloads), not raw video or audio streams.
- **Not a BPMN workflow engine.** Workflow orchestration (Camunda, Restate) is a consuming capability, not a core platform responsibility. External systems define and manage workflows.
- **Not an AI model training platform.** The AI Agent Engine consumes existing LLMs and AI services via MCP/A2A. It does not train or host models.

---

## 6. MVP Scope

### 6.1 In Scope

- All platform components running on a single local dev machine (QEMU VMs via talosctl) [FR-22, FR-23, FR-24]
- Telemetry ingestion at 100K+ RPS from simulated IoT devices [FR-1, FR-2, FR-3, FR-4]
- Real-time processing pipeline: Pulsar Functions (Pulsar) + Spin functions (Kafka) → ClickHouse [FR-5, FR-6, FR-7, FR-8]
- Alert signal detection from API (directed streams) [FR-9, FR-10, FR-11]
- Alert state tracking (stateful workflow through KeyDB + CouchDB) [FR-8, FR-10, FR-12]
- Device/entity state management (CouchDB clustered + YugabyteDB) [FR-13, FR-14, FR-15, FR-16]
- GitOps deployment pipeline: Backstage + Kargo + Argo CD + Argo Rollouts + Argo Events + Argo Workflows [FR-17, FR-18, FR-19, FR-20, FR-21]
- Talos Linux substrate with Cilium eBPF networking and Rook-Ceph storage [FR-22, FR-23, FR-24]
- Observability stack: VictoriaMetrics cluster, Grafana, AlertManager [FR-25, FR-26, FR-27, FR-28]
- Security edge: Envoy Gateway + Casdoor (AuthN) + Casbin (RBAC/ReBAC/ABAC) [FR-36, FR-37, FR-38, FR-40, FR-41, FR-42, FR-43]
- Infisical secrets management [FR-44]
- OpenAPI specification governance (Swagger YAML in Git) [FR-39]
- Air-gapped delivery via local Harbor registry, Spegel P2P, and local Git mirror [FR-30, FR-31, FR-32]
- End-to-end validation: device → ingestion → processing → alert → response [FR-1, FR-5, FR-9, FR-10, FR-11]

### 6.2 Out of Scope for MVP

- **Production multi-region deployment** — deferred to v2. MVP validates on single dev cluster only.
- **Bidirectional device communication** — dedicated microservice post-v1. v1 ingests only.
- **CRM / WMS / ERP integration** — entity hierarchy (companies → clients → devices) is stored but external system integration is deferred.
- **Billing integration** — external billing source connection deferred to v2.
- **Central hub SPA** — cross-region management UI deferred to v2. MVP uses Backstage + Grafana for visibility.
- **Full AI Agent Engine** — MCP/A2A orchestration deferred. MVP may include basic LLM integration for alert analysis only. [NON-GOAL for MVP]
- **BPMN workflow engine (Camunda)** — external workflow orchestration deferred. MVP uses simple state machine for alert workflow.
- **Production PXE/Matchbox bootstrapping** — MVP uses `talosctl cluster create` (QEMU backend) only.
- **Cilium ClusterMesh** — single-cluster only in MVP. Cross-cluster federation deferred.
- **Hasura GraphQL federation** — Hasura deployed but full federation across YugabyteDB + CouchDB + ClickHouse deferred to v2. MVP uses direct database access.

### 6.3 Stakeholder Note

> Multi-region is the core differentiator — v2 planning should start immediately after MVP validation.

---

## 7. Success Metrics

*Each SM cross-references the FR(s) it validates. Counter-metrics counterbalance specific primary or secondary metrics.*

**Primary**

- **SM-1**: Telemetry throughput — system sustains 100K RPS ingestion from simulated devices with p99 ingestion latency < 100ms. Validates FR-1, FR-2, FR-3.
- **SM-2**: Processing latency — normalized message reaches ClickHouse storage within 2 seconds of ingestion (end-to-end). Validates FR-5, FR-6, FR-7.
- **SM-3**: Alert detection — alert signal detected and state transition initiated within 500ms of API submission. Validates FR-9, FR-10, FR-11.
- **SM-4**: Deployment automation — new environment bootstrapped to running platform in < 30 minutes via GitOps pipeline. Validates FR-18, FR-19, FR-20.

**Secondary**

- **SM-5**: Entity CRUD latency — entity create/update operations complete in < 200ms (p99) across CouchDB and YugabyteDB. Validates FR-13, FR-14.
- **SM-6**: GraphQL query performance — cross-store queries (CouchDB + YugabyteDB + ClickHouse) resolve in < 2 seconds. Validates FR-16.
- **SM-7**: Security evaluation latency — combined RBAC/ReBAC/ABAC authorization decision in < 15ms (p99). Validates FR-41, FR-42, FR-43.
- **SM-8**: GitOps sync — workload changes committed to Git are reconciled to cluster within 60 seconds. Validates FR-19.

**Counter-metrics (do not optimize)**

- **SM-C1**: Feature velocity — number of features shipped per sprint. Counterbalances SM-4 (deployment speed) — faster deployment must not come at the cost of feature completeness.
- **SM-C2**: Alert false positive rate — percentage of alerts that are not actionable. Counterbalances SM-3 (alert detection speed) — faster detection must not increase noise.

---

## 8. Open Questions

### Decisions Needed

1. **Pulsar payload format** — JSON, Avro, or Protobuf? Affects ingestion normalization (FR-2) and ClickHouse schema (FR-7). [ASSUMPTION: JSON envelope with raw payload field.]
2. **Pulsar vs Kafka split** — Pulsar handles MQTT/gRPC ingestion + Pulsar Functions; Kafka handles alert signals + Spin functions. Confirm telemetry load splitting strategy.
3. **Central hub SPA framework** — React, Vue, Angular? Not specified.

### Implementation Decisions (defer to architecture)

4. **ClickHouse table DDL** — exact schema for `device_metrics` table not defined. Needs DDL before implementation.
5. **KeyDB deployment topology** — standalone, replicated, or clustered? Affects FR-8 availability guarantees.
6. **CouchDB cluster size** — how many nodes in the clustered deployment for dev/staging/production?
7. **YugabyteDB deployment topology** — RF (replication factor), number of nodes per environment?
8. **Harbor storage backend** — local filesystem, CephFS, or S3-compatible? Affects air-gapped registry performance.
9. **Spin function language** — Rust (per with-gsd/) or multi-language? Affects SpinKube node requirements.
10. **Talos version** — not explicitly pinned.

### Requirements Gaps (must resolve before sprint 1)

11. **Backup/DR strategy** — no mention of etcd backup, Ceph snapshots, or database backup. Required for production.
12. **Resource sizing** — no authoritative RAM/CPU/disk sizing per environment tier.
13. **Region-specific configs** — production overlays mention "prod-us, prod-eu" but no region-specific data locality or compliance requirements defined.
14. **Canary analysis thresholds** — Argo Rollouts canary analysis thresholds (error rate, latency p99) not defined. What values trigger rollback?
15. **Casbin policy schema** — no example PERM policy file or relationship tuple format defined for Zanzibar model.

---

## 9. Assumptions Index

*Every `[ASSUMPTION]` from the document, surfaced for explicit confirmation:*

- §4.1 FR-2: [ASSUMPTION: JSON envelope with raw payload field is the normalization format.]
- §4.2 FR-5: [ASSUMPTION: Spin functions run Rust WASM modules via SpinKube on compatible nodes.]
- §4.2 FR-6: [ASSUMPTION: Pulsar functions use `pulsar-io-jdbc-clickhouse` sink with batch size 25,000 and 500ms flush.]
- §4.3 FR-9: [ASSUMPTION: Alert signals arrive as structured JSON payloads with fields: alert_id, device_id, severity, timestamp, metadata.]
- §4.4 FR-13: [ASSUMPTION: CouchDB cluster uses 3 nodes minimum for dev, 5 for production.]
- §4.4 FR-14: [ASSUMPTION: Entity hierarchy is company → client → [devices, assets] with document references.]
- §4.5 FR-22: [ASSUMPTION: Talos Linux version pinned to stable release (not specified which).]
- §4.6 FR-25: [ASSUMPTION: VictoriaMetrics cluster uses 2 vmstorage, 1 vminsert, 1 vmselect minimum.]
- §4.7 FR-30: [ASSUMPTION: Harbor storage backend is CephFS for air-gapped environments.]
- §4.8 FR-33: [ASSUMPTION: VPN overlay uses WireGuard (not Netmaker) for ClusterMesh.]
- §4.9 FR-36: [ASSUMPTION: Envoy Gateway routes are defined as Kubernetes Gateway API resources (HTTPRoute, GRPCRoute).]
- §4.10 FR-41: [ASSUMPTION: Base roles are manager, operator, administrator, technic, developer, CEO, client — static list.]
- §4.11 FR-46: [ASSUMPTION: LLM integration is configurable per deployment — no specific model mandated.]
