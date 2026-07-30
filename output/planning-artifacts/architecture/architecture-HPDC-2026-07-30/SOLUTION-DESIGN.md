# Solution Design Document — High Performance Distributed Cluster (HPDC)

| Attribute | Value |
|-----------|-------|
| **Document ID** | SD-HPDC-2026-07-30 |
| **Status** | Draft |
| **Paradigm** | Gateway-Mediated Domain Segregation |
| **Altitude** | Feature |
| **Scope** | Enterprise GitOps Platform for IoT telemetry, alert management, and GitOps deployment |
| **Binds** | FR-1 through FR-48, UJ-1 through UJ-5 |
| **Created** | 2026-07-30 |
| **Updated** | 2026-07-30 |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Design Paradigm](#3-design-paradigm)
4. [Architecture Overview](#4-architecture-overview)
5. [Architecture Decisions](#5-architecture-decisions)
6. [Data Flow](#6-data-flow)
7. [Deployment Topology](#7-deployment-topology)
8. [Testing Strategy](#8-testing-strategy)
9. [Work Breakdown](#9-work-breakdown)
10. [Operational Model](#10-operational-model)
11. [Air-Gapped Delivery](#11-air-gapped-delivery)
12. [Deferred Decisions](#12-deferred-decisions)
13. [Glossary](#13-glossary)

---

## 1. Executive Summary

The High Performance Distributed Cluster (HPDC) is an enterprise-grade, offline-first platform purpose-built for high-throughput IoT telemetry ingestion, real-time alert management, and GitOps-driven workload deployment across geographically distributed bare-metal clusters. It is not a cloud service, not a general-purpose Kubernetes platform, and not a SaaS offering — it is a self-hosted security platform designed to operate in environments where internet access is unavailable, compliance mandates data sovereignty, and telemetry volumes exceed 100,000 requests per second per region.

The architecture is organized around a single governing paradigm: **Gateway-Mediated Domain Segregation**. Envoy Gateway sits at the network edge as the exclusive ingress boundary, routing traffic into five hard-separated domain routes — document-serving (`/data`), serverless workflows (`/api`), GraphQL federation (`/gql`), stream ingestion (`/telemetry`), and event pub-sub (`/events`). Each route owns its internal runtime pattern and technology stack. Inter-domain communication flows exclusively through the event-mesh (Apache Pulsar and Apache Kafka), never through direct HTTP calls. This boundary discipline ensures that telemetry ingestion at 100K+ RPS cannot be slowed by GraphQL query load, and that alert state machines cannot block document CRUD operations.

The compute layer is entirely serverless-first. KNative provides scale-to-zero execution for Go and Python functions, Restate adds stateful SAGA workflow capabilities for multi-step business logic, SpinKube runs WASM-based transforms on Kafka topics at sub-10ms latency, and Pulsar Functions handle stream aggregation and JDBC sink writes to ClickHouse. No application logic runs as an always-on microservice. Infrastructure components — databases, message brokers, the gateway itself — run as persistent pods backed by Ceph RBD persistent volumes.

Six databases serve distinct access patterns: CouchDB for document-oriented entity hierarchy, YugabyteDB for distributed transactional state, ArcadeDB for graph traversals and lineage, ClickHouse for time-series telemetry analytics, KeyDB for hot cache and alert state, and PostgreSQL exclusively for Casdoor and Casbin authentication and authorization data. All storage is backed by Ceph RBD via Rook-Ceph, running on Talos Linux with Cilium eBPF networking.

Delivery is GitOps-only. A monorepo with Kustomize overlays feeds into Kargo for multi-stage promotion via Freight artifacts, which drives Argo CD sync across environments. Argo Rollouts handles progressive delivery with canary analysis, Argo Events bridges Git and external events into Argo Workflows, and Backstage provides a developer portal with Golden Path templates for scaffolding new functions. The entire pipeline operates without internet access: Harbor serves as the local OCI registry with Trivy scanning and Cosign signing, Spegel DaemonSet provides P2P image distribution across nodes, and Git repositories are mirrored locally.

The system is designed from inception for multi-region deployment with data sovereignty. Each region maintains independent database instances — no automatic cross-region replication. Cilium ClusterMesh over WireGuard VPN provides cross-region service discovery, and a central hub queries regional APIs with scoped authentication for aggregate visibility only. Regional data never leaves its region.

v1 is a proof-of-concept validating the full pipeline on a single local development machine running Talos Linux in QEMU virtual machines via `talosctl cluster create`. Success is measured by four primary metrics: sustained 100K RPS telemetry ingestion with p99 latency under 100ms, end-to-end processing latency under 2 seconds from ingestion to ClickHouse storage, alert detection and state transition within 500 milliseconds, and full environment bootstrap via GitOps in under 30 minutes.

---

## 2. Problem Statement

### 2.1 IoT Telemetry Ingestion at Scale

Operators of large IoT fleets — drone swarms, industrial sensor networks, vehicle telemetry systems — face a common challenge: ingesting, processing, and acting on high-velocity telemetry streams in environments where latency matters and connectivity cannot be assumed. A single region may produce 100,000 or more telemetry messages per second, each requiring normalization, enrichment, aggregation, and persistent storage. The ingestion layer must handle multiple protocols (MQTT, HTTP, gRPC) simultaneously, apply back-pressure when downstream consumers lag, and guarantee ordering within device-type and region partitions.

### 2.2 Alert Management as a Directed Stream

Security alert signals differ fundamentally from telemetry. Alerts arrive as directed streams — structured events from external security systems, SOC tools, and automated detectors — each requiring stateful lifecycle management. An alert transitions through a well-defined state machine (initial, acknowledged, investigating, resolved, closed), and each transition may trigger automated responses: device lockdown commands, webhook notifications, workflow start signals, or compliance report generation. The alert path must operate independently from the telemetry path so that a telemetry surge cannot delay alert processing, and vice versa.

### 2.3 Air-Gapped Deployment Constraint

The primary deployment environment for this platform has no internet access. This is not an edge case or a nice-to-have — it is the fundamental operational constraint. All container images, Helm charts, Git repositories, and dependency artifacts must be delivered, stored, and distributed locally. The deployment pipeline cannot depend on Docker Hub, GitHub, or any external registry. Image distribution across nodes must work without a central bottleneck. Updates arrive via physical media or local network transfers, and the GitOps pipeline must operate entirely against local mirrors.

### 2.4 Multi-Region Data Sovereignty

Telemetry data may span jurisdictions with different compliance regimes. A drone fleet operating in Germany must not have its positional data replicated to a data center in the United States. Each region owns its data independently. The platform must support cross-region visibility for operational dashboards — a VP of Operations needs to see aggregated alert throughput across all regions — without moving or duplicating regional data. This requires a federated query model where the central hub asks rather than copies.

### 2.5 GitOps-Only Operations in Constrained Environments

In air-gapped, security-conscious deployments, imperative operations (direct kubectl, SSH access, manual configuration changes) are a compliance and audit risk. Every change to the platform — infrastructure configuration, application deployment, policy update, secret rotation — must flow through a documented, auditable, repeatable GitOps pipeline. The platform must enforce this discipline at the architecture level, not rely on operational policy alone.

---

## 3. Design Paradigm

### 3.1 Gateway-Mediated Domain Segregation

The architecture is governed by a single paradigm: **Gateway-Mediated Domain Segregation**. This paradigm has three structural rules that propagate through every architecture decision in this document:

**Rule 1 — Exclusive Ingress.** Envoy Gateway is the sole entry point for all external traffic. No backend service exposes a port without a matching Gateway API route. This is enforced at the network layer by Cilium network policies and at the configuration layer by code review — any Kubernetes manifest that creates a Service of type LoadBalancer or NodePort without a corresponding HTTPRoute must be rejected.

**Rule 2 — Hard Domain Boundaries.** Each gateway route is a bounded domain with its own internal runtime pattern, technology stack, and scaling behavior. The five routes are:

| Route | Domain | Internal Pattern | Technology |
|-------|--------|-----------------|------------|
| `/data/*` | Document-serving | CouchDB native CRUD, MapReduce, `_changes` feed | CouchDB 3.5.2 |
| `/api/*` | Serverless workflows | KNative scale-to-zero with Restate SAGAs | KNative + Restate |
| `/gql` | Data federation | Hasura GraphQL across CouchDB + ClickHouse + YugabyteDB | Hasura |
| `/telemetry/*` | Stream ingestion | Pulsar native MQTT/gRPC handlers with Pulsar Functions | Apache Pulsar 4.2.3 |
| `/events/*` | Event pub-sub | Kafka topics with SpinKube WASM transforms | Apache Kafka + SpinKube |

**Rule 3 — Event-Mesh Integration.** Domains communicate exclusively through the event-mesh (Pulsar topics and Kafka topics) or through database-level change feeds. A function in the `/api` domain never makes a direct HTTP call to a service in the `/telemetry` domain. Function-to-function HTTP calls within the same domain (e.g., a KNative function calling a SpinApp for a stateful counter operation) are permitted and travel through the mTLS mesh, but cross-domain calls must go through a topic. This rule prevents the coupling that traditionally emerges in service-oriented architectures where any service can call any other service's API, creating invisible dependency graphs and cascading failure domains.

### 3.2 Why This Paradigm

Traditional microservice architectures grant every service the ability to call every other service. Over time, this produces a dependency graph that no single team understands fully, where a latency spike in the alert service can cascade through the telemetry pipeline because of an invisible synchronous dependency. Gateway-Mediated Domain Segregation inverts this: instead of trusting teams to maintain discipline about which services call which, the architecture makes cross-domain coupling structurally impossible. The only integration path between domains is an asynchronous topic, which provides natural load levelling, back-pressure, and failure isolation.

This paradigm is particularly suited to the IoT telemetry domain because the ingestion, processing, and alert paths have fundamentally different performance characteristics. The `/telemetry` route must sustain 100K+ RPS with minimal per-message overhead — it cannot afford the latency of a JWT exchange or an ext_authz gRPC call per message. The `/api` route, by contrast, handles human-driven requests where millisecond-level auth overhead is negligible. The paradigm accommodates both by giving each route the authentication mechanism it needs: API-Key validation via native Envoy Gateway header matching for `/telemetry` and `/events`, and full JWT validation with Casbin ext_authz for `/data`, `/api`, and `/gql`.

### 3.3 Implications

- **No cross-domain REST APIs.** If the alert engine needs device hierarchy data, it reads from CouchDB directly (which all functions can do) or subscribes to the `_changes` feed — it does not call the entity management service's HTTP endpoint.
- **Topic-per-integration.** Every cross-domain integration path is a named, versioned topic in Pulsar or Kafka. This makes the integration surface explicit, monitorable, and governable.
- **Unified wire format.** All topics use Protobuf with a CommonEnvelope schema, enforced by Schema Registry. This ensures that a Rust SpinApp, a Java Pulsar Function, and a Go KNative service can all produce and consume the same message type without coordination.
- **Back-pressure at the route level.** Each route handles back-pressure independently. The `/telemetry` route uses Pulsar's per-topic backlog quotas and topic offloading; the `/events` route uses Kafka consumer lag. A backlog in one route cannot affect the others.

---

## 4. Architecture Overview

### 4.1 Layer Diagram and Component Stack

The platform is organized into six layers, each corresponding to a horizontal slice of the deployment:

```
                    ┌──────────────────────────────────────────┐
                    │              Envoy Gateway                 │
                    │  /data  │  /api  │  /gql  │ /telemetry │ /events │
                    ├─────────┼────────┼────────┼─────────────┼──────────┤
                    │ CouchDB │KNative │ Hasura │   Pulsar    │  Kafka   │
                    │  Native │Restate │  GQL   │  Functions  │ SpinKube │
                    ├─────────┴────────┴────────┴─────────────┴──────────┤
                    │              Event Mesh (Pulsar + Kafka)             │
                    ├─────────┬────────┬────────┬──────────┬───────┬───────┤
                    │ CouchDB │Yugabyte│ArcadeDB│ClickHouse│ KeyDB │ PGSQL │
                    │         │  DB    │        │          │       │(Auth) │
                    ├─────────┴────────┴────────┴──────────┴───────┴───────┤
                    │              Ceph RBD (persistent storage)            │
                    │          Talos Linux + Cilium (eBPF) substrate        │
                    └──────────────────────────────────────────────────────┘
```

### 4.2 Gateway Layer

Envoy Gateway serves as the exclusive ingress controller, implementing the Kubernetes Gateway API specification. It handles TLS termination via cert-manager, rate limiting per route, and authentication dispatch. The Gateway API resources define five HTTPRoutes corresponding to the five domain routes. A SecurityPolicy resource attaches ext_authz configuration to the routes that require it.

Casdoor provides JWT-based authentication for the `/data`, `/api`, and `/gql` routes. It issues JWTs, manages users and groups, and supports OIDC/SAML federation with external identity providers. Casbin runs as a Go gRPC service providing authorization decisions through Envoy Gateway's ext_authz filter. It evaluates three authorization models in parallel — RBAC (role-based), ReBAC (relationship-based, Zanzibar-style), and ABAC (attribute-based) — and applies a DENY-wins conflict resolution: if any model evaluates to DENY, the decision is DENY regardless of the other models' results.

The `/telemetry` and `/events` routes use a lighter authentication mechanism: API-Key validation via native Envoy Gateway header matching. This avoids the latency and complexity of Casdoor JWT validation on high-throughput ingestion paths. API keys are configured as Envoy Gateway secrets and managed through Infisical.

### 4.3 Compute Layer

The compute layer is entirely serverless-first. No application logic runs as a Deployment or StatefulSet. Four execution environments cover the full spectrum of workload patterns:

**KNative Serving + Eventing** provides scale-to-zero execution for Go and Python functions. A KNative service scales down to zero replicas when idle and scales up on demand, making it suitable for request-driven workloads on the `/api` route. KNative Eventing connects database change feeds (CouchDB `_changes`, YugabyteDB CDC) to KNative services, enabling change-driven business logic without polling.

**Restate** integrates with KNative to provide stateful workflow capabilities — SAGAs, event sourcing, and long-running multi-step processes. The alert state machine (initial through closed) is implemented as a Restate workflow, ensuring durable execution with exactly-once semantics even across function restarts and node failures.

**SpinKube** runs WASM modules as SpinApp custom resources on Kubernetes. The containerd-shim-spin runtime executes Spin applications in WebAssembly, providing sub-10ms cold start times and sub-10ms per-message processing latency on Kafka topics. Spin functions are ideal for stateless transforms: field mapping, enrichment, filtering, and format conversion on the event path.

**Pulsar Functions** provide stream processing within the Pulsar ecosystem. Java functions handle windowed aggregation, schema validation, and batched writes to ClickHouse via the JDBC Sink connector. Pulsar Functions run within the Pulsar cluster itself, avoiding the overhead of external function invocation for high-throughput stream processing.

**Argo Workflows** handles CI/build/test/deploy pipelines and batch compute tasks. It runs DAG-based workflow definitions triggered by Argo Events from Git pushes, image updates, or Kargo Freight creation.

### 4.4 Messaging Layer

Apache Pulsar is the primary message backbone, handling all telemetry ingestion at 100K+ RPS. It provides native MQTT (via the MoP protocol handler) and gRPC protocol handlers, eliminating the need for separate protocol adapters. Topics are partitioned by `device_type` and `region_id` to enable ordered parallel consumption by downstream processors. Pulsar's built-in backlog quotas and topic offloading to Ceph provide back-pressure and long-term retention.

Apache Kafka serves as the secondary stream engine for alert signals, external events, and Spin WASM consumption. Kafka's consumer-group model is a better fit for the event processing pattern, where multiple independent consumers (Spin functions, KNative services, archival sinks) each need their own offset tracking. Strimzi manages the Kafka cluster, topic definitions, and Schema Registry integration.

The two message systems are not redundant — they serve different purposes. Pulsar handles the high-throughput, multi-protocol ingestion path where its native protocol handlers and tiered storage excel. Kafka handles the event-processing path where its consumer-group semantics and ecosystem integration (Kafka Connect, KSqlDB) provide advantages. Cross-system bridging is handled at the application layer: a KNative function consuming from Pulsar may produce to Kafka, or vice versa.

### 4.5 Data Layer

Six databases serve distinct access patterns, each chosen for its specific strengths:

**CouchDB** (3.5.2) stores the entity hierarchy — companies, clients, devices, and assets — as JSON documents. Its `_changes` feed provides a real-time stream of document mutations, which KNative Eventing consumes to trigger business logic. MapReduce views support ad-hoc query patterns. The document model is a natural fit for the hierarchical, schema-flexible entity data.

**YugabyteDB** (2026.1.0.1) provides distributed SQL for transactional state: workflow/payment data, financial operations, scheduled jobs, reports, and complex relational queries. It is PostgreSQL-compatible, so standard SQL tools and ORMs work without modification. Its Change Data Capture (CDC) feed feeds into KNative Eventing for change-driven workflows.

**ArcadeDB** (26.7.3) provides multi-model graph capabilities for entity lineage, neighbor discovery, shortest-path traversals, and relationship queries that would be expensive or awkward in a document or relational store. The graph model is essential for security use cases: "find all devices within two hops of a compromised gateway."

**ClickHouse** (26.7.1) stores processed telemetry in MergeTree tables, partitioned by time and device type. The columnar storage engine provides fast aggregation queries over large time ranges — returning 1 million rows in under 2 seconds. Pulsar Functions write to ClickHouse via the JDBC Sink connector in batches of 25,000 records with a 500ms flush interval.

**KeyDB** provides clustered in-memory caching for hot device state, active alert state, pub-sub channels, and the idempotency deduplication set. Read latency is under 1 millisecond (p99). Cache entries have configurable TTL (default 5 minutes), and all reads fall back to CouchDB or ClickHouse transparently on cache miss.

**PostgreSQL** is reserved exclusively for Casdoor and Casbin authentication and authorization data: users, roles, policies, and relationship tuples. It is not used for application data.

All databases use Ceph RBD PVCs for persistent storage. All are deployed with CiliumNetworkPolicy resources enforcing mTLS-only access.

### 4.6 Operations Layer

VictoriaMetrics runs in cluster mode with three component types: vmstorage nodes store the actual time-series data, vminsert nodes handle ingestion and sharding, and vmselect nodes handle query resolution. vmagent scrapes metrics from all platform components. Retention is tiered: 7 days at raw resolution, 30 days at 1-hour aggregated rollup, and 1 year at monthly rollup.

OpenTelemetry SDK auto-instruments all KNative functions for distributed tracing and custom metrics. Each function writes structured JSON logs to stdout, collected by vmlog for indexing and search.

Cilium Hubble provides network-level observability without sidecars: real-time flow visibility, DNS monitoring, HTTP/gRPC traffic analysis, and service dependency mapping at the eBPF level.

### 4.7 GitOps Layer

Kargo manages the promotion lifecycle. A Warehouse resource monitors Harbor for new image digests matching a SemVer subscription. When a new image is detected, Kargo creates a Freight artifact — a promotable set of images and configuration references. The dev Stage auto-promotes when new Freight is available; the production Stage requires manual approval. On promotion, Kargo writes updated image digests to Kustomize overlays and commits back to Git.

Argo CD reconciles Git state to the cluster. An ApplicationSet with a directory generator creates per-stage Application resources from the Kustomize overlays. Sync Waves order resource creation: CRDs (wave -10), network policies (wave -5), storage classes and Ceph cluster (wave -4), platform core components like Pulsar and databases (wave -3), and applications and functions (wave 1). Argo Rollouts handles canary deployments with automated analysis against VictoriaMetrics metric thresholds.

---

## 5. Architecture Decisions

### AD-1: Envoy Gateway as Exclusive Ingress Boundary

**Context.** Every external request to the platform — whether from an IoT device sending telemetry, a SOC operator acknowledging an alert, or an external API posting an event — must pass through a single control point that can enforce TLS termination, authentication, authorization, rate limiting, and routing. Without a single ingress boundary, each backend service would need to implement these concerns independently, leading to inconsistent security posture and increased attack surface.

**Decision.** Envoy Gateway is the sole ingress controller. All external routes must be declared as Kubernetes Gateway API resources (HTTPRoute, GRPCRoute, TLSRoute). No backend service exposes a port externally without a matching gateway route. TLS termination happens at Envoy Gateway via cert-manager. Authentication dispatch happens at the route level: API-Key validation via header matching for `/telemetry` and `/events`, JWT validation via Casdoor for `/data`, `/api`, and `/gql`. Authorization is delegated to a Casbin gRPC ext_authz service for the JWT-authenticated routes.

**Alternatives rejected.** Direct Service exposure (type LoadBalancer or NodePort without a gateway route) was rejected because it lacks centralized authentication and authorization — each service would need to implement its own auth layer, and there would be no single point to enforce TLS termination, rate limiting, or access logging. Istio Ingress Gateway was evaluated but rejected because its Gateway API support was less mature at the time of evaluation, and the architecture already uses Cilium for the service mesh (mTLS, network policies), making Istio's additional mesh layer redundant.

**Trade-offs.** Envoy Gateway becomes a critical path component — if it is down, the entire platform is unreachable. This is mitigated by running multiple replicas with pod anti-affinity and by relying on Envoy Gateway's battle-tested production track record. The ext_authz gRPC call adds latency to each authenticated request (typically 5-15ms for the Casbin evaluation), which is acceptable for the `/data`, `/api`, and `/gql` routes but is avoided on `/telemetry` and `/events` by using lightweight API-Key validation instead.

### AD-2: Domain-per-Route Segregation

**Context.** The five route patterns — document CRUD, serverless workflows, GraphQL federation, stream ingestion, and event pub-sub — have fundamentally different runtime characteristics. Document CRUD benefits from direct database access with minimal latency. Serverless workflows benefit from scale-to-zero to avoid paying for idle capacity. Stream ingestion must sustain 100K+ RPS with minimal per-message overhead. Event pub-sub needs Kafka's consumer-group semantics for independent consumer offset tracking. A single backend serving all routes would force all five patterns into a lowest-common-denominator runtime, wasting resources and adding unnecessary latency.

**Decision.** Each route is a hard domain boundary owning its internal pattern and technology stack. The five domains communicate exclusively through the event-mesh (Pulsar and Kafka topics) or through database change feeds — never through direct HTTP calls to another domain's internal services. Function-to-function HTTP calls within the same domain are permitted and travel through the mTLS mesh (e.g., a KNative function calling a SpinApp for a stateful counter operation).

**Alternatives rejected.** A single backend service serving all routes was rejected because it would couple the scaling and failure characteristics of all five patterns. A telemetry surge would compete for CPU and memory with the GraphQL endpoint, and a bug in the entity CRUD handler would take down the alert ingestion path. An API composition layer (BFF pattern) was also considered but rejected because it would add an unnecessary intermediary between the gateway and the domains — the gateway already provides routing, so an additional composition layer would add latency without clear benefit.

**Trade-offs.** Domain segregation means that cross-domain workflows must go through asynchronous topics, adding latency compared to a direct synchronous call. The welcome counter example in Section 6.1 demonstrates this trade-off: the counter SpinApp is in the same domain (`/api`) as the welcome function, so it can be called synchronously. If the counter were in a different domain, the call would need to go through a topic, adding sub-millisecond queueing latency in exchange for decoupling. The assumption is that for cross-domain workflows, the decoupling benefit outweighs the latency cost.

### AD-3: Serverless-First Compute

**Context.** IoT telemetry workloads have variable load patterns. A drone fleet may be active during daytime hours and idle at night. An alert event may trigger a burst of processing that subsides within seconds. Always-on microservices would waste resources during low-activity periods and would need to be manually scaled for predictable bursts. The platform must handle both latency-sensitive request processing and throughput-sensitive stream processing without maintaining idle capacity.

**Decision.** All application logic uses one of four serverless execution environments, eliminating Deployment and StatefulSet resources for application code (reserved exclusively for infrastructure components like databases and message brokers). The four environments are:

- **KNative Serving** for request-driven, scale-to-zero HTTP workloads.
- **Restate** for stateful, multi-step workflows (SAGAs, event-sourcing).
- **SpinKube** for stateless WASM transforms on Kafka topics.
- **Pulsar Functions** for stream aggregation, windowing, and JDBC Sink writes.

**Alternatives rejected.** Always-on microservices were rejected because the telemetry workload is inherently bursty — the platform would need to over-provision for peak load or accept latency spikes during scale-up events. AWS Lambda and similar FaaS offerings were rejected because the platform must operate air-gapped without any cloud dependency. KNative was chosen over OpenWhisk and OpenFaaS because of its native Kubernetes integration, mature scale-to-zero implementation, and support for gRPC and eventing.

**Trade-offs.** Scale-to-zero adds cold-start latency when a function has been idle. KNative's cold start is typically 100-500ms depending on image size and node resource availability. For the `/api` route handling human-driven requests, this is acceptable. For the `/telemetry` route, the warm Pulsar function instances avoid cold starts entirely. The Restate runtime maintains virtual object state across function restarts, so stateful workflows do not lose progress during scale-to-zero events. The trade-off is acceptable because the platform's critical high-throughput paths (telemetry ingestion, stream processing) use execution environments that stay warm (Pulsar Functions, SpinKube), while the request-driven paths (`/api` workflows, change-driven business logic) can tolerate cold-start latency.

### AD-4: Event-Mesh as the Integration Fabric

**Context.** With five domain routes, six databases with change feeds, Git events, image updates, and external API webhooks, the platform needs a decoupled integration mechanism. Point-to-point integrations — where each consumer directly calls each producer — would create an unmanageable dependency graph. The integration fabric must handle multiple messaging patterns (pub-sub, queue, streaming), multiple protocols, and multiple language runtimes.

**Decision.** Pulsar is the primary message backbone for telemetry ingestion (100K+ RPS), handling MQTT and gRPC natively through protocol handlers. Kafka is the secondary stream engine for alert events, external signals, and Spin WASM consumption. Database change feeds (CouchDB `_changes`, YugabyteDB CDC) are bridged into KNative Eventing, which triggers KNative services. Argo Events bridges Git/image/Kafka events into Argo Workflows.

**Alternatives rejected.** A single Pulsar cluster for everything was considered but rejected because Kafka's consumer-group model provides better semantics for the event-processing use case, where multiple independent consumers (Spin functions, KNative services, archival sinks) each need their own offset tracking without rebalancing. gRPC point-to-point integration was rejected because it creates synchronous coupling between domains, violating the Gateway-Mediated Domain Segregation paradigm.

**Trade-offs.** Operating two message systems (Pulsar and Kafka) doubles the operational surface area — each needs separate cluster management, monitoring, and backup procedures. The trade-off is justified because the two systems serve different workload patterns. Pulsar's native MQTT/gRPC protocol support and tiered storage are ideal for the ingestion path. Kafka's consumer-group model and ecosystem (Kafka Connect, Schema Registry, monitoring) are better suited for the event-processing path. Attempting to force both workloads into a single system would require either adding protocol adapters and custom consumer-group logic to Pulsar, or adding MQTT/gRPC protocol support to Kafka — both achievable but with higher complexity than operating two purpose-built systems.

### AD-5: Protobuf Normalized Envelope

**Context.** Messages flow across five language runtimes (Go, Rust, Java, Python, TypeScript) and two message systems (Pulsar and Kafka). Without a shared wire format, each producer-consumer pair would need to negotiate a schema, leading to drift, serialization mismatches, and integration failures at deployment time rather than at compile time. The envelope must include routing metadata (device_id, region_id, event_type) and runtime metadata (origin, idempotency_key) that the messaging layer needs to function, plus the original payload for downstream processing.

**Decision.** All messages on Pulsar and Kafka topics use Protobuf serialization enforced by Schema Registry (Pulsar Schema Registry for Pulsar topics, Karapace or Confluent Schema Registry for Kafka topics). The CommonEnvelope schema is:

```protobuf
message CommonEnvelope {
  string device_id = 1;
  string device_type = 2;
  string event_type = 3;
  int64 timestamp = 4;       // unix millis
  bytes payload = 5;         // original payload, untransformed
  string region_id = 6;
  string origin = 7;         // producer identifier
  string idempotency_key = 8; // unique per logical event
}
```

The `origin` field prevents CDC mutation loops: a function triggered by CouchDB `_changes` checks that `origin != self` before writing back to CouchDB. The `idempotency_key` field is checked against a KeyDB dedup set (TTL 5 minutes) before processing, preventing duplicate processing from at-least-once delivery semantics. Max envelope size is 64KB; oversized payloads are rejected at the gateway with HTTP 413.

**Alternatives rejected.** JSON was rejected because it lacks built-in schema enforcement — producers and consumers can drift without detection until runtime, and the lack of code generation means each language runtime needs a separate JSON parsing library with potentially different behaviors. Avro was considered but rejected because its tooling support across Go, Rust, Java, and Python is less mature than Protobuf's, and the binary Protobuf format is more compact than Avro for the common case of small telemetry messages with a few fields.

**Trade-offs.** Protobuf adds a build-time dependency: all producers and consumers must compile the `.proto` file and handle schema evolution. The Schema Registry introduces a runtime dependency: functions cannot start if they cannot reach the registry. In exchange, the team gets compile-time type safety across all language runtimes, automatic code generation, and schema evolution guarantees (backward-compatible field numbering enforced by the registry). For a system spanning five runtimes and two message systems, this trade-off strongly favors Protobuf.

### AD-6: Database Ownership Boundaries

**Context.** The platform has six databases with different data models and access patterns. Without clear ownership rules, teams may duplicate data across stores (storing telemetry in both ClickHouse and CouchDB, for example), creating ambiguity about which store is the source of truth. The ownership boundary must prevent data duplication without restricting read access — all serverless functions need read access to all stores for cross-domain workflows.

**Decision.** Each database type owns its authoritative data domain. CouchDB owns document hierarchy (companies, clients, devices). YugabyteDB owns transactional state (workflows, payments, reports). ArcadeDB owns graph data (entity lineage, neighbor relationships). ClickHouse owns processed telemetry analytics. KeyDB owns cached/hot state (alert state, sessions, dedup set). PostgreSQL owns auth data (users, roles, policies).

All serverless functions have read and write access to all data stores. The ownership boundary prevents *duplicating authoritative data across stores*, not restricting access. Document shape conventions matching the owning store's schema are enforced via code review — there is no runtime schema enforcement at write time. If a function writes a document to CouchDB that is clearly transactional state belonging in YugabyteDB, that is caught in code review, not by a runtime guard.

**Alternatives rejected.** Per-function scoped database credentials (where each function can only write to its authorized databases) was rejected for MVP simplicity — the credential management overhead across dozens of serverless functions would be significant, and the MVP benefits from the flexibility of universal access. Per-function database partitions (where each function has its own CouchDB database) was rejected for the same reason. Both may be revisited in a production hardening phase.

**Trade-offs.** The absence of runtime write enforcement means that a bug in a function could write data to the wrong store. The mitigation is code review, which relies on human attention and may miss edge cases. In exchange, the platform avoids the operational complexity of managing dozens of database credentials and the development friction of per-function database access configuration. For an MVP that prioritizes velocity over production hardening, this is the right trade-off.

### AD-7: Ceph for All Persistent State

**Context.** Every stateful workload in the platform — six database clusters, two message brokers, the caching layer — needs durable, scalable block storage. In an air-gapped bare-metal environment, there is no cloud block storage (EBS, persistent disk) to rely on. The storage layer must handle the I/O patterns of both databases (random read/write, fsync-heavy) and message brokers (sequential writes, large preallocated files).

**Decision.** Rook-Ceph provides Ceph RBD (RADOS Block Device) PVCs for all stateful workloads. No hostPath, emptyDir, or local volume is used for stateful data. Ceph OSDs run on dedicated disks (or loop devices in the dev QEMU environment) with a replication factor of 1 in dev and 3 in production.

**Alternatives rejected.** Local SSDs (hostPath or local PV) were rejected because data loss would occur on node failure — in a 3-node cluster, losing one node would mean losing one-third of the data with no recovery path. NFS was rejected because its performance characteristics (especially for fsync-heavy database workloads) are significantly worse than Ceph RBD. Mayastor was evaluated but rejected in favor of Ceph's maturity and ecosystem.

**Trade-offs.** Ceph introduces significant operational complexity — OSD management, CRUSH map tuning, network configuration, and monitoring all require expertise. In a production cluster, Ceph may use 20-30% of CPU resources for its OSD daemons. The trade-off is accepted because Ceph provides the only viable path to durable, scalable, self-hosted block storage in an air-gapped bare-metal environment. Alternative solutions either sacrifice durability (local SSDs) or performance (NFS).

### AD-8: mTLS for All Inter-Service Communication

**Context.** In an air-gapped deployment, there is no external certificate authority. All intra-cluster traffic must be encrypted to prevent credential sniffing on the wire, but the certificate lifecycle must operate without internet access. Cilium is already required for eBPF CNI, kube-proxy replacement, and network policies — adding mTLS should leverage the existing Cilium installation rather than adding a separate mesh layer.

**Decision.** Cilium enforces mTLS for all service-to-service traffic via its SPIFFE/SPIRE integration. Certificates are auto-rotated by Cilium without manual intervention. Envoy Gateway handles external TLS termination (cert-manager for public certificates) while internal traffic uses Cilium-managed mTLS between sidecars.

**Alternatives rejected.** Istio mTLS was rejected because Cilium already provides the CNI layer — adding Istio would introduce a separate sidecar proxy and control plane, increasing resource consumption and operational complexity without adding capabilities beyond what Cilium's native mTLS provides. Linkerd was rejected for similar reasons (extra mesh layer with no clear benefit over Cilium's built-in encryption).

**Trade-offs.** Cilium mTLS adds some latency to each connection (certificate validation, encryption overhead), typically in the microsecond range. In exchange, the platform gets transparent encryption of all intra-cluster traffic with automatic certificate rotation and no sidecar overhead. For a platform where security is a primary concern and telemetry messages are small (under 64KB), the encryption overhead is negligible.

### AD-9: GitOps-Only Delivery

**Context.** In an air-gapped, security-conscious deployment, every change must be auditable and repeatable. Imperative operations — direct kubectl, SSH into nodes, manual configuration changes — create audit gaps and configuration drift. The platform must enforce a GitOps workflow where Git is the single source of truth and all changes flow through a documented pipeline. The monorepo structure must support multiple environments (dev, production) with environment-specific overlays.

**Decision.** A monorepo with Kustomize overlays (base, dev, production) serves as the single source of truth. Kargo manages multi-stage promotion via Freight artifacts. Argo CD ApplicationSet with a directory generator syncs workloads to the cluster. Direct kubectl is forbidden in dev and production — all changes must flow through Git -> Kargo -> Argo CD. The monorepo structure is:

```
/
├── gitops/          # Kargo + Argo CD configuration
│   ├── kargo/       # Warehouse, Stage, Freight definitions
│   ├── argocd/      # App-of-Apps, ApplicationSets, Sync Waves
│   └── overlays/    # Kustomize overlays per environment
├── platform/        # Infrastructure component configs (Helm values)
├── backend/         # Serverless function source code
├── frontend/        # SPA source code (shipped from CDN)
├── specs/           # OpenAPI and Protobuf specifications
└── charts/          # Shared Helm charts
```

**Alternatives rejected.** Helm-only delivery was rejected because Kustomize provides better support for environment-specific overlays — base overlays define common configuration, and per-environment overlays add or override specific values. Flux was evaluated but Kargo was chosen because of its more mature promotion model (Freight artifacts, Warehouse image detection, Stage promotion gates).

**Trade-offs.** GitOps-only delivery adds latency between a code commit and its appearance in the cluster — the Kargo promotion cycle, Argo CD sync interval, and Sync Wave ordering may take 30-60 seconds for a simple change. For development velocity, this is a friction point. The platform mitigates this by auto-promoting to dev on image detection (no manual approval needed for dev) and by keeping Argo CD's sync interval low (default 3 minutes, configurable to 60 seconds). In exchange, the platform gets a complete audit trail of every change, repeatable deployments, and the ability to reconstruct any environment state from Git history.

### AD-10: Air-Gapped Delivery

**Context.** Production deployment has no internet access. Container images, Helm charts, and Git repositories must be available locally. Image distribution across nodes during scale-up events must not bottleneck on a single registry. The delivery pipeline must operate entirely against local infrastructure.

**Decision.** Harbor serves as the local OCI registry with Trivy vulnerability scanning and Cosign image signing. Spegel DaemonSet provides peer-to-peer container image distribution at the containerd level — nodes cache and share images without hitting the central registry on every pull. Git repositories are mirrored locally (GitLab self-hosted or Gitea). All delivery is GitOps-mediated — never a static package or direct image pull from the internet.

**Alternatives rejected.** A static artifact bundle (tarball of all images + charts, deployed via script) was rejected because it bypasses GitOps — changes would be applied imperatively, and there would be no audit trail or rollback path through Git. A single Harbor proxy (without Spegel) was considered but rejected because during scale-up events (e.g., a new node joining the cluster), all nodes would pull from the same registry, creating a bandwidth bottleneck. Spegel's P2P distribution reduces peak registry load and pull time by more than 50% in multi-pod scale-up events.

**Trade-offs.** Running Harbor locally requires storage for all container images and Helm charts — typically 50-200GB depending on the number of versions retained. Spegel adds a DaemonSet on each node consuming CPU and memory for P2P cache management. In exchange, the platform gains full autonomy from external registries, faster image pulls during scale-up (P2P distribution), and the ability to operate indefinitely without internet access.

### AD-11: Multi-Region Data Sovereignty

**Context.** IoT telemetry data may be subject to compliance requirements that prohibit cross-border data transfer. Each regional cluster must maintain independent data storage. Cross-region visibility is needed for operational dashboards and aggregated reporting, but data must not leave its region. The platform must support this from day one even though v1 is single-cluster.

**Decision.** Each region deploys independent instances of CouchDB, YugabyteDB, ClickHouse, ArcadeDB, KeyDB, and PostgreSQL. No automatic cross-region data replication occurs. Cilium ClusterMesh over WireGuard VPN provides cross-region service discovery. A central hub queries regional APIs (with region-scoped authentication) for aggregate visibility — regional data never leaves its region. The central hub does not store regional data; it queries it on demand and caches query results temporarily for dashboard display.

**Alternatives rejected.** A global YugabyteDB cluster spanning regions was rejected because it would automatically replicate data across regions (YugabyteDB's replication factor is per-table, not per-row with geo-aware constraints), violating data sovereignty requirements. Cross-region CouchDB replication was rejected for the same reason. A central data lake that ingests all regional data was rejected because it requires data to leave its region.

**Trade-offs.** The independent-databases-per-region approach means that cross-region queries (e.g., "show me all alerts across all regions") must fan out to each regional API and aggregate results. This is slower than a centralized query (adding network round-trip time per region) and more complex (each region may be unreachable, time out, or return partial results). The trade-off is required by the compliance constraint — data sovereignty is not negotiable, so the architecture optimizes for correctness (data never leaves its region) over query performance.

### AD-12: Observability

**Context.** The platform has 25+ components, dozens of serverless functions, two message brokers, six databases, and a GitOps pipeline — all in an air-gapped environment with no access to external observability SaaS. Every component emits metrics, logs, and traces in different formats. Without a unified observability strategy, debugging production issues would require manual correlation across multiple tools.

**Decision.** Every function writes structured JSON logs to stdout (not to files). OpenTelemetry SDK auto-instruments all KNative functions for distributed tracing and custom metrics (counters, histograms). VictoriaMetrics cluster mode (vmstorage, vminsert, vmselect with vmagent for scraping) stores all metrics with configurable retention: 7 days raw, 30 days aggregated (1-hour rollup), 1 year monthly rollup. Cilium Hubble provides network observability at the eBPF level — flow visibility, DNS monitoring, HTTP/gRPC traffic analysis, and service dependency maps — without sidecar overhead. Grafana provides dashboards (platform health, telemetry throughput, alert statistics, business stakeholder views). AlertManager routes metric-based alerts to configured notification channels (no external service dependency).

**Alternatives rejected.** Prometheus standalone was rejected because its local storage has retention limits and no high-availability mode — a Prometheus pod restart could lose metrics. Grafana Cloud was rejected because the platform operates air-gapped. ELK Stack (Elasticsearch, Logstash, Kibana) was evaluated but rejected because its resource consumption (especially Elasticsearch) is significantly higher than VictoriaMetrics + vmlog for the same retention and query performance.

**Trade-offs.** VictoriaMetrics cluster mode is operationally complex — three component types (vmstorage, vminsert, vmselect) each with different scaling characteristics and resource profiles. The team must understand VictoriaMetrics' cluster architecture to operate it effectively. In exchange, VictoriaMetrics provides efficient storage (10-30x compression compared to Prometheus), long retention without memory growth, and PromQL compatibility.

### AD-13: Centralized Secrets Management

**Context.** The platform has 20+ components, each with database credentials, API keys, TLS certificates, and external integration secrets. In an air-gapped deployment, secrets must be managed without internet access. Secrets must not appear in Git (even in encrypted form), ConfigMaps, or environment variables. Rotation must be automated to comply with security policies.

**Decision.** All secrets are stored in Infisical and never in version control. The Infisical Kubernetes Operator injects secrets into pods via the CSI Driver provider (mounted as volumes) or by syncing to native Kubernetes Secrets for cluster-internal use. Secrets auto-rotate on a configurable schedule (default 90 days). Each function and component has its own Infisical service account — no shared credentials.

**Alternatives rejected.** Kubernetes-native Secrets alone were rejected because they lack rotation policies, audit logging, and cross-cluster synchronization — managing secrets across regions would require manual kubectl commands. HashiCorp Vault was evaluated but rejected because its deployment complexity (Vault server, unseal process, storage backend configuration) is higher than Infisical's, and Infisical's Kubernetes Operator and CSI Driver integration is more mature and better documented for this specific use case.

**Trade-offs.** Infisical adds a dependency on a secrets management system that must be operational before any workload can start — if Infisical is down, new pods cannot mount their secrets. This is mitigated by running Infisical with high availability and by caching secret values in the CSI Driver's tmpfs mount (so pods continue to work if Infisical is temporarily unreachable, though rotation is paused). The CSI Driver injects secrets as volumes rather than environment variables, which means applications must read from a file path rather than accessing an environment variable. This is a minor development friction that is well worth the security benefit of never exposing secrets in process environments, logs, or crash dumps.

---

## 6. Data Flow

### 6.1 Welcome Counter End-to-End Walkthrough

The welcome counter demonstrates the architecture's core patterns: gateway routing, JWT authentication, Casbin authorization, KNative serverless execution, SpinKube WASM function invocation, and KeyDB stateful operations. This is the canonical "hello world" of the HPDC platform.

```
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

**Step 1: Gateway Ingress.** A client sends an HTTP GET request to `/api/welcome` with a Bearer JWT token in the Authorization header. Envoy Gateway receives the request, terminates TLS, and matches the path against the `/api/*` HTTPRoute.

**Step 2: JWT Validation.** Envoy Gateway's SecurityPolicy triggers JWT validation against Casdoor. If the token is missing, expired, or invalid, Envoy Gateway returns HTTP 401 immediately without forwarding to the backend.

**Step 3: Authorization.** With a valid JWT, Envoy Gateway calls the Casbin ext_authz gRPC service, passing the JWT claims (user ID, roles) and request context (path, method). Casbin evaluates three authorization models in parallel:
- **RBAC**: Does the user's role have permission to call `GET /api/welcome`?
- **ReBAC**: Does the user's relationship to the relevant entity (e.g., company) grant access?
- **ABAC**: Does the current context (time of day, device status, risk level) allow access?

If any model evaluates to DENY, the overall decision is DENY (HTTP 403). If all models allow, the request is forwarded.

**Step 4: KNative Invocation.** The request reaches the KNative "welcome" service. If the service was scaled to zero, KNative activates a new pod (cold start, typically 100-500ms). The Go handler receives the request.

**Step 5: SpinApp Counter Call.** The welcome function needs to increment a visit counter and return the current count. It makes an HTTP GET to the SpinApp "counter" service within the same `/api` domain — this is an intra-domain function-to-function call permitted under AD-2. The call travels through the Cilium mTLS mesh.

**Step 6: KeyDB Stateful Operation.** The SpinApp counter (Rust WASM, running on SpinKube) receives the request and executes a KeyDB INCR command on key `counter-welcome`. KeyDB returns the incremented value (42 in this example). The SpinApp returns the value to the welcome function.

**Step 7: Response.** The welcome function constructs the response `"Welcome (42)"` with Content-Type `text/plain` and returns it through Envoy Gateway to the client.

**Failure modes.** If Casdoor is unreachable, Envoy Gateway returns 502. If Casbin returns DENY, the client gets 403. If the counter SpinApp is down (or scaled to zero and cold start fails), the KNative function returns 502 with a structured error body. If KeyDB is unreachable, the counter SpinApp returns an error, and the welcome function falls back to returning `"Welcome (0)"` with a warning header — the welcome path is degraded but not broken.

### 6.2 The Six Data Paths

#### Telemetry Path (IoT Device → ClickHouse)

```
IoT Device ──MQTT/gRPC──▶ EG(/telemetry) ──▶ Pulsar ──Pulsar Functions──▶ ClickHouse
                                                        └──Pulsar Functions──▶ CouchDB / YugabyteDB
```

An IoT device sends telemetry via MQTT or gRPC to the `/telemetry` route. Envoy Gateway validates the API-Key header (lighter than JWT — no Casdoor or Casbin). Validated messages reach Pulsar's native protocol handlers (MoP for MQTT, gRPC handler for gRPC), which translate them to Pulsar internal topics partitioned by `device_type` and `region_id`. Pulsar Functions consume from these topics:
- **Telemetry Aggregator**: Performs windowed aggregation (e.g., 10-second rolling average of sensor values) and schema validation.
- **JDBC ClickHouse Sink**: Writes aggregated records to ClickHouse in batches of 25,000 with a 500ms flush interval. Failed batches are retried 3 times before going to a dead-letter queue.
- **Entity Updater**: Updates device last-seen timestamp and status in CouchDB/YugabyteDB.

Back-pressure is handled by Pulsar's per-topic backlog quotas. When consumer lag exceeds a configured threshold, Pulsar applies exponential backoff to producers or drops messages (with a metric increment for `ingestion_dropped_total`).

#### Event Path (External API → Kafka → SpinKube/KNative)

```
External APIs ──────▶ EG(/events) ──▶ Kafka ──SpinKube WASM──▶ ClickHouse / CouchDB
                                                ──KNative+Restate──▶ CouchDB / KeyDB (alert state)
```

External systems post events (including alert signals) to the `/events` route. Envoy Gateway validates the API-Key header and routes to Kafka via an HTTP bridge or Kafka REST proxy. Kafka topics (configured as Strimzi `KafkaTopic` resources) receive the events. Multiple consumer groups process independently:
- **SpinKube WASM functions** perform stateless transforms (field mapping, enrichment, filtering) with sub-10ms latency per message, then write to ClickHouse or CouchDB.
- **KNative + Restate services** handle stateful event processing — the alert state machine consumes events from Kafka, transitions alert state through its lifecycle (initial → acknowledged → investigating → resolved → closed), persists state to CouchDB, caches active alerts in KeyDB, and triggers notifications via Pulsar topics.

#### API Path (Client → KNative + Restate)

```
Clients ──▶ EG(/api) ──extAuth──▶ Casbin gRPC ──▶ KNative+Restate ──▶ DBs
                        │        (RBAC/ReBAC/ABAC)
                        └─▶ JWT validation at Casdoor
```

The `/api` route handles all request-driven, human-facing operations: alert acknowledgment, device registration, report generation. Every request passes through JWT validation (Casdoor) and authorization (Casbin gRPC ext_authz). KNative services implement the business logic, optionally using Restate for stateful SAGA workflows that span multiple database operations and external calls.

#### Data Path (Client → CouchDB)

```
Clients ──▶ EG(/data) ──extAuth──▶ Casbin gRPC ──▶ CouchDB
                        │
                        └─▶ JWT validation at Casdoor
```

The `/data` route provides direct document CRUD access to CouchDB. It is the simplest route: after authentication and authorization, the gateway proxies directly to CouchDB's HTTP API. This route is used for entity hierarchy management (companies, clients, devices, assets) and any document-oriented operations that benefit from CouchDB's native MapReduce and `_changes` feed.

#### GQL Path (Client → Hasura → Federated Databases)

```
Clients ──▶ EG(/gql) ──extAuth──▶ Casbin gRPC ──▶ Hasura ──▶ CouchDB / ClickHouse / YugabyteDB
                        │
                        └─▶ JWT validation at Casdoor
```

The `/gql` route provides a unified GraphQL API that federates CouchDB (entity documents), ClickHouse (telemetry analytics), and YugabyteDB (transactional state). Hasura resolves cross-store queries — for example, "find all devices for company X and return their latest telemetry metrics" — by joining data from CouchDB (device list) with ClickHouse (latest metrics per device). In v1, Hasura is deployed but full federation is deferred — MVP uses direct database access from functions.

#### Change-Driven Path (Database CDC → KNative Eventing → Workflows)

```
CouchDB _changes ──▶ KNative Eventing ──▶ KNative+Restate (SAGA workflows)
YugabyteDB CDC   ──▶ KNative Eventing ──▶ KNative+Restate
```

Database change feeds trigger business logic without polling. CouchDB's `_changes` feed and YugabyteDB's CDC feed both publish change events to KNative Eventing, which triggers KNative services. A change-driven workflow might: when a new device document appears in CouchDB, automatically create an ArcadeDB graph vertex for the device, register it in YugabyteDB, and send a notification via Pulsar — all within a single Restate SAGA that can roll back on failure.

---

## 7. Deployment Topology

### 7.1 Dev Environment

The MVP runs on a single developer machine using Talos Linux in QEMU virtual machines provisioned by `talosctl cluster create`. This is not a production deployment — it is a validation environment that demonstrates the full pipeline from telemetry ingestion to ClickHouse storage to alert state machine execution.

```
Dev (talosctl QEMU, single node)
┌───────────────────────────────────────────────┐
│  Envoy Gateway  │  Casdoor  │  Casbin         │
│  Pulsar + Kafka │  CouchDB  │  YugabyteDB     │
│  ArcadeDB       │  KeyDB    │  ClickHouse     │
│  KNative │ Restate │ SpinKube │ Backstage    │
│  Kargo │ Argo CD │ Argo Rollouts │ Argo Events│
│  VictoriaMetrics│ Grafana  │  Harbor / Spegel │
│  Cilium │ Hubble │ Rook-Ceph (single OSD)     │
└───────────────────────────────────────────────┘
Ceph RBD (loop device or thin-LV)
```

Key characteristics:
- Single QEMU VM (or small cluster of 3 VMs for HA validation).
- Rook-Ceph with a single OSD on a loop device or thin logical volume (no dedicated disks).
- All databases run as single replicas (no clustering).
- Argo CD syncs from the monorepo's `overlays/dev` Kustomize directory.
- Harbor pre-populated with all required images; Spegel distributes across VMs.
- VictoriaMetrics single-node mode (not cluster mode — vmstorage/vminsert/vmselect collapsed).

### 7.2 Production Environment

Production deploys on bare-metal servers with a minimum of 3 nodes per region. Each region is an identical deployment of the full platform stack, isolated by Cilium ClusterMesh over WireGuard VPN.

```
Production (bare-metal, 3+ nodes per region)
┌──────────────────────────────────────────────────────┐
│  Envoy Gateway (2+ replicas, anti-affinity)          │
│  Casdoor (2+ replicas) │ Casbin (2+ replicas)        │
│  Pulsar (3+ bookies) │ Kafka (3+ brokers)            │
│  CouchDB (3+ nodes) │ YugabyteDB (RF=3)              │
│  ArcadeDB (3+ nodes) │ KeyDB (clustered, 3+ nodes)   │
│  ClickHouse (2+ replicas, sharded)                    │
│  PostgreSQL (HA, Patroni)                             │
│  KNative │ Restate │ SpinKube                         │
│  Kargo │ Argo CD (HA) │ Argo Rollouts │ Argo Events   │
│  VictoriaMetrics cluster (2+ vmstorage, vminsert, vmselect)│
│  Grafana │ AlertManager │ Hub    │
│  Harbor (HA) │ Spegel (DaemonSet on all nodes)        │
│  Cilium │ Hubble │ Rook-Ceph (3+ OSD nodes, RF=3)    │
└──────────────────────────────────────────────────────┘
WireGuard VPN ──── ClusterMesh ──── Other regions
```

Key characteristics:
- Minimum 3 nodes for Ceph replication factor 3 and database quorum.
- Dedicated disks for Ceph OSDs (no loop devices).
- Database clustering enabled (CouchDB clustered, YugabyteDB RF=3, KeyDB in cluster mode).
- VictoriaMetrics cluster mode with separate vmstorage, vminsert, vmselect components.
- Harbor with CephFS storage backend for registry persistence.
- Spegel DaemonSet on all worker nodes for P2P image distribution.
- Argo CD deployed in HA mode with multiple replicas.

### 7.3 Region Topology

Each region is a standalone deployment. Regions do not share databases. Cilium ClusterMesh over WireGuard VPN provides:
- Cross-region service discovery (a central hub in region A can discover and query APIs in region B).
- Encrypted cross-region traffic (WireGuard tunnel).
- No cross-region data replication (by design — each region's databases are independent).

The central hub is a lightweight component (deployed in one region, or as a standalone service) that queries regional APIs with region-scoped service accounts. It aggregates data for dashboards without storing it.

---

## 8. Testing Strategy

### 8.1 Three-Tier Pyramid

Testing follows a three-tier pyramid covering every layer from deployment manifests to function logic to full-system behavior on a live cluster. The tiers are designed to catch different failure modes: deployment tests catch configuration drift, unit tests catch logic errors, integration tests catch contract violations between functions, and e2e tests catch system-level behavior regressions.

```
                       ┌─────────────┐
                       │    E2E      │  Playwright + live cluster
                       │   (few)     │  Deployed-system validation
                       ├─────────────┤
                       │ Integration │  In-memory mocks + concurrency
                       │  (some)     │  Inter-function contracts
           ┌───────────┼─────────────┤
           │   Unit    │ Deployment  │  Kustomize dry-run, Argo CD app diff
           │  (many)   ├─────────────┤
           │           │  Routes     │  HTTPRoute validation, SecurityPolicy check
           │           ├─────────────┤
           │           │  Functions  │  Go httptest, Rust cargo test, Pulsar test CLI
           └───────────┴─────────────┘
```

### 8.2 Unit Tests

Every function is tested independently with its own language-native testing tools:

| Layer | Tool | Coverage |
|-------|------|----------|
| Go KNative functions | `go test` + `httptest.NewServer` | Handler logic, error paths, response formats, configuration parsing |
| Rust SpinApps | `cargo test` (WASM target) | Business logic, KeyDB interaction with mock connection |
| Java Pulsar Functions | Pulsar `Context` test harness | Transform logic, schema compliance, error handling, batching |
| OpenAPI specs | Spectral linting | Spec validity, route and response coverage against implementation |

### 8.3 Integration Tests

Integration tests validate inter-function contracts with in-memory fakes for dependencies:

- **Welcome counter end-to-end**: In-memory mutex-guarded integer mimics KeyDB INCR. Validates sequential increments, concurrent access safety, timeout propagation, and error handling (counter unreachable -> HTTP 502).
- **Route authentication**: Validates JWT validation paths (valid token, expired token, missing token, wrong signing key) and Casbin ext_authz gRPC responses per role.
- **Pulsar -> ClickHouse pipeline**: Validates JDBC Sink batch write semantics with an in-memory or test-container ClickHouse instance. Validates batch size limits (25,000 records), flush interval (500ms), retry logic (3 attempts), and DLQ behavior after exhaustion.
- **Alert state machine**: Validates all valid state transitions (initial -> acknowledged -> investigating -> resolved -> closed), invalid transitions (initial -> closed returns 409), and concurrent access prevention (optimistic locking).

### 8.4 Deployment Tests

Executed in CI before any Kargo promotion, deployment tests validate that the GitOps pipeline produces valid, drift-free manifests:

| Test | Tool | Validation |
|------|------|------------|
| Kustomize build | `kustomize build` + `kubectl diff` | Overlay produces valid Kubernetes manifests with correct environment-specific values |
| Argo CD app diff | `argocd app diff` | No drift between Git state and cluster state for platform components |
| Dry-run apply | `kubectl apply --dry-run=server --server-side` | Manifests accepted by the Kubernetes API server |
| Kargo Freight check | `kargo verify freight` | Freight contains all required images and configurations for the target stage |
| Helm lint | `helm lint` | Chart values pass schema validation |

### 8.5 Route Exposure Tests

These validate that Gateway API resources are correctly configured and wired:

| Test | Tool | Validation |
|------|------|------------|
| Gateway API validation | `kubectl apply --dry-run=server -f httproute.yaml` | HTTPRoute, GRPCRoute, TLSRoute resources accepted by the API server |
| SecurityPolicy wiring | Integration test with mock ext_authz | JWT and API-Key auth flows, RBAC/ReBAC/ABAC decision propagation |
| Rate limiting | Integration test | Per-route rate limits enforced; back-pressure triggers correctly |

### 8.6 E2E Tests

Playwright tests against the deployed platform validate end-to-end behavior. These run on the dev cluster after all unit and integration tests pass:

- **Welcome counter** (`welcome-counter.spec.ts`): GET `/api/welcome`, verify `"Welcome (N)"` format, verify sequential increment across 5 calls, verify Content-Type header, verify HTTP 502 when counter is down.
- **Telemetry ingestion**: POST to `/telemetry`, verify message reaches ClickHouse via Pulsar Functions within SLA (2 seconds).
- **Alert lifecycle**: POST alert to `/events`, verify state transitions (initial -> acknowledged -> resolved -> closed) through the API.
- **Entity CRUD**: Create, read, update, delete through `/data` to CouchDB, verify via `/gql`.
- **Auth enforcement**: Verify HTTP 401 on missing or expired JWT, HTTP 403 on unauthorized role, HTTP 200 on valid token with correct permissions.
- **Air-gapped deployment**: Verify Kargo promotion completes from local Harbor, Spegel peers distribute image without internet access.

---

## 9. Work Breakdown

### 9.1 Slices Overview

The architecture is decomposed into 13 independently buildable slices, each corresponding to a coherent set of components and ADs. Slices are organized into three execution waves based on dependencies.

| # | Slice | ADs | Primary Tech | Complexity |
|---|-------|-----|-------------|-----------|
| 1 | Substrate | AD-7, AD-8 | Talos, Cilium, Ceph | High |
| 2 | GitOps | AD-9, AD-10 | Kargo, Argo CD, Kustomize | Medium |
| 3 | Messaging | AD-4, AD-5 | Pulsar, Kafka, Strimzi | Medium |
| 4 | Database | AD-6, AD-7 | 6 database clusters | Medium |
| 5 | Gateway | AD-1, AD-2 | Envoy Gateway, Casdoor, Casbin | Medium |
| 6 | Observability | AD-12 | VictoriaMetrics, OTel, Grafana | Low |
| 7 | Secrets | AD-13 | Infisical | Low |
| 8 | Telemetry Pipeline | AD-2, AD-3, AD-4, AD-5 | Java Pulsar Functions | Medium |
| 9 | Alert Engine | AD-2, AD-3, AD-4 | Go/KNative, Restate | High |
| 10 | Entity Management | AD-2, AD-6 | CouchDB, Hasura | Medium |
| 11 | Auth Integration | AD-1, AD-2 | Go/Casbin | Medium |
| 12 | Deployment & Testing | Testing | Playwright, Go test | Low |
| 13 | Frontend | — | Backstage (MVP only) | Low |

### 9.2 Wave 1 — Foundation (Parallel)

Wave 1 establishes the substrate and tooling that all other slices depend on. These seven slices can be built in parallel by separate teams:

```
Substrate ──────────▶ Cluster running, Ceph available
GitOps    ──────────▶ Git -> Kargo -> Argo CD pipeline working
Messaging ──────────▶ Pulsar + Kafka clusters with topics
Database  ──────────▶ All 6 databases running, CDC feeds enabled
Gateway   ──────────▶ Envoy Gateway routes defined, Casdoor+Casbin wired
Observability ──────▶ VictoriaMetrics ingesting, Grafana dashboards
Secrets   ──────────▶ Infisical injecting secrets into pods
```

### 9.3 Wave 2 — Serverless Functions (Sequential)

Wave 2 builds on Wave 1's foundation. Slices are order-dependent:

```
Telemetry Pipeline ──▶ IoT -> EG(/telemetry) -> Pulsar -> Functions -> ClickHouse
Auth Integration   ──▶ Casbin gRPC -> SecurityPolicy -> all routes
Alert Engine       ──▶ Kafka -> SpinKube -> KNative+Restate -> CouchDB+KeyDB
Entity Management  ──▶ CouchDB -> Hasura -> GQL
```

### 9.4 Wave 3 — Polish

```
Deployment & Testing ──▶ CI pipeline, integration tests, e2e suite
Frontend (v2)       ──▶ SPA on CDN (deferred beyond MVP)
```

### 9.5 Suggested Team Assignments

| Team | Owns |
|------|------|
| **Platform Team** | Substrate, GitOps, Messaging, Database (infra setup), Gateway (infra), Observability, Secrets |
| **Backend Team** | Telemetry Pipeline (Pulsar Functions), Alert Engine (KNative + Restate), Entity Management, Auth Integration (Casbin gRPC service) |
| **QA/DevOps** | Deployment & Testing, CI pipeline, e2e test suite |
| **Frontend Team** (v2) | SPA on CDN, Central Hub UI |

### 9.6 Dependency Graph

```
Substrate ◄── GitOps ◄───┬── Gateway ◄─── Auth Integration
                         ├── Messaging ◄── Telemetry Pipeline
                         ├── Messaging ◄── Alert Engine
                         ├── Database  ◄── Entity Management
                         ├── Database  ◄── Telemetry Pipeline (ClickHouse)
                         ├── Database  ◄── Alert Engine (CouchDB, KeyDB)
                         └── Secrets   ◄── ALL (Infisical CSI)
```

---

## 10. Operational Model

### 10.1 GitOps-Only Operations

The platform enforces a GitOps-only operational model. Every change — infrastructure configuration, application deployment, policy update, secret rotation — must flow through the monorepo. The pipeline is:

1. **Developer pushes code or configuration to Git** (feature branch or direct push depending on workflow).
2. **CI pipeline runs**: lint, unit tests, deployment tests (Kustomize dry-run, helm lint, Freight verification).
3. **Kargo detects new commit or image digest** via Warehouse subscription and creates a Freight artifact.
4. **Kargo auto-promotes to dev Stage** (no manual approval needed for dev).
5. **Argo CD syncs the dev overlays** applying Kustomize patches and Sync Wave ordering.
6. **Argo Rollouts performs canary deployment** for workload changes, analyzing against VictoriaMetrics metric thresholds.
7. **Manual approval gates production promotion** in the Kargo Stage configuration.
8. **Kargo promotes to production** on approval, writing updated image digests to production overlays and committing back to Git.
9. **Argo CD syncs production** with the same Sync Wave ordering as dev.

Direct kubectl is forbidden. All cluster state is observable through Argo CD dashboards, Backstage, or Grafana — never through imperative commands.

### 10.2 Kargo Promotion Pipeline

Kargo orchestrates promotion across three conceptual stages (which may map to actual namespaces, clusters, or overlay directories):

- **Dev Stage**: Auto-promotion on image detection or Git commit. No manual gate. Fast feedback loop.
- **Staging Stage**: Optional intermediate stage for integration testing before production. May auto-promote or require manual approval.
- **Production Stage**: Manual approval required. Promotion updates the production overlay with new image digests and commits back to Git.

Freight artifacts are the unit of promotion — they bundle image digests, Git commit SHAs, and configuration references into a single promotable entity. Kargo verifies that all Freight contents are available (images pushed to Harbor, charts available) before marking the Freight as verified.

### 10.3 Argo CD Sync Waves

Sync Waves order resource application to respect dependencies:

| Wave | Resources | Rationale |
|------|-----------|-----------|
| -10 | CRDs (Cilium, Rook-Ceph, Gateway API, KNative, Strimzi, etc.) | Custom resource definitions must exist before any CR instance can be created |
| -5 | Network policies (CiliumNetworkPolicy) | Network policies must be in place before workloads start, preventing unsecured startup windows |
| -4 | Storage (Rook-Ceph Cluster, StorageClass) | Databases and message brokers need PVCs before they can start |
| -3 | Platform core (Pulsar, Kafka, databases, Envoy Gateway, Casdoor, Casbin) | Core infrastructure must be running before functions can depend on it |
| 1 | Applications and functions (KNative services, SpinApps, Pulsar Functions) | Workloads start after all infrastructure is ready |

Within each wave, Argo CD applies resources in parallel. Resources in later waves depend on resources in earlier waves being healthy.

### 10.4 Observability

Every function writes structured JSON logs to stdout with a consistent schema. OpenTelemetry SDK auto-instruments all KNative functions, exporting traces and custom metrics (counters for processed messages, histograms for processing latency) to VictoriaMetrics. Cilium Hubble exports network flow data — service dependency maps, inter-service latency, DNS lookups — at the eBPF level with no sidecar overhead.

AlertManager evaluates metric thresholds and routes alerts to configured notification channels. Since the platform is air-gapped, notification channels must be self-hosted or use local relays: email via an internal SMTP relay, webhooks to internal services, or PagerDuty integration via a local relay that syncs when connectivity is available.

### 10.5 Secrets Rotation

Infisical manages all secrets with a default rotation schedule of 90 days. The rotation process for a database credential:

1. Infisical generates a new credential for the database user.
2. The database is updated with the new credential (Infisical handles this via its integration).
3. The Infisical Kubernetes Operator detects the secret change and updates the CSI Driver volume mount.
4. Pods reading the secret from the mounted volume see the new value on their next read.
5. The old credential is revoked after a configurable grace period (default 24 hours) to allow in-flight connections to drain.

Secrets are never stored in ConfigMaps, environment variables, or Git. The CSI Driver mounts secrets as volumes (tmpfs) at a well-known path. Applications read from this path rather than from environment variables.

### 10.6 Backup Strategy (Deferred to Production)

Production deployment will require a comprehensive backup strategy covering:
- **etcd backup**: Scheduled snapshots stored to CephFS.
- **Ceph snapshots**: Periodic RBD snapshots for point-in-time recovery.
- **Database-specific backups**: CouchDB replication to backup cluster, YugabyteDB backup to Ceph, ClickHouse backup via `BACKUP TABLE ... TO FILE`.
- **Git repository backup**: Mirror to a separate storage location.
- **Harbor artifact backup**: Image and chart export to offline storage.

These are deferred because v1 is a single-node proof-of-concept where backup is less critical.

---

## 11. Air-Gapped Delivery

### 11.1 The Air-Gapped Constraint

The platform is designed for environments with zero internet access. This means:
- No pulling images from Docker Hub, Quay.io, or any external registry.
- No cloning repositories from GitHub, GitLab SaaS, or any external Git host.
- No fetching Helm charts from artifact repositories.
- No reaching external APIs for license validation, telemetry, or updates.
- No DNS resolution for external hosts beyond the local network.

Everything must be delivered, stored, and operated locally.

### 11.2 Harbor — Local OCI Registry

Harbor serves as the local OCI registry, pre-populated with all required container images and Helm charts. Key features:

- **Trivy vulnerability scanning** on every image push. Images with high-priority CVEs above a configurable threshold are rejected. In an air-gapped environment, vulnerability databases must be updated via periodic offline sync (download the Trivy DB update on a connected machine and transfer it physically).
- **Cosign image signing** ensures image integrity. All images pushed to Harbor are signed, and Argo CD's verification hooks can optionally verify signatures before syncing.
- **Helm charts as OCI artifacts**: Harbor stores Helm charts alongside container images, using OCI artifact storage.
- **Storage backend**: CephFS for production (durable, scalable), local filesystem for dev.

### 11.3 Spegel — P2P Image Distribution

Spegel runs as a DaemonSet on every worker node, providing peer-to-peer container image distribution at the containerd level:

1. When a node needs to pull an image, it first checks its local containerd cache.
2. If the image is not cached locally, Spegel queries peer nodes via a DHT (distributed hash table) to find a node that has the image cached.
3. The image layer is transferred from the peer node over HTTP, avoiding the central Harbor registry.
4. If no peer has the image, Spegel falls back to pulling from Harbor (the central registry).

During scale-up events (multiple pods starting simultaneously on different nodes), Spegel significantly reduces load on Harbor and improves pull time: nodes that have already pulled the image serve it to peers, distributing the bandwidth across all nodes instead of concentrating it on the registry.

### 11.4 Local Git Mirror

Git repositories are mirrored locally using a self-hosted GitLab instance or Gitea. The mirror setup:

- **gitops-infra**: Contains the platform configuration, Kustomize overlays, Argo CD ApplicationSets, and Kargo definitions.
- **gitops-workloads**: Contains function source code, Helm charts, and workload-specific configurations.
- **app-source-code**: Contains the backend function source code repositories.

The GitOps pipeline operates entirely against the local mirror. Argo CD syncs from the local mirror's repository URL. Kargo monitors the local mirror for new commits and image digests. Updates arrive via:
- Physical transfer (USB drive or local network transfer) of a Git bundle.
- Incremental sync when connectivity is available (e.g., scheduled low-bandwidth sync).
- Developer pushes directly to the local mirror from within the internal network.

### 11.5 Delivery Workflow

1. **Artifact preparation on connected machine**: Build container images, push to a temporary Harbor, run Trivy scan, sign with Cosign. Clone and mirror Git repositories.
2. **Physical or local transfer**: Transfer images (as OCI artifacts or tarballs) and Git bundles to the air-gapped environment via USB drive or local network.
3. **Harbor import**: Import images into the air-gapped Harbor instance. Verify signatures and scan results.
4. **Git mirror update**: Push Git bundles to the local GitLab/Gitea instance.
5. **Kargo detection**: Kargo's Warehouse detects new images in Harbor and new commits in the local Git mirror, creates Freight artifacts, and promotes through the pipeline.
6. **Argo CD sync**: Argo CD syncs the latest Freight to the cluster, deploying the new version.
7. **Spegel distribution**: As pods start on different nodes, Spegel distributes images peer-to-peer.

---

## 12. Deferred Decisions

The following decisions are explicitly deferred to v2. They are not architecture gaps — they are deliberate choices to keep the MVP focused on validating the core data path.

| Decision | Why Deferred | Revisit When |
|----------|-------------|--------------|
| **Central hub SPA framework** (React/Vue/Angular) | MVP uses Backstage + Grafana for cross-region visibility. No SPA development needed. | v2 planning starts |
| **Full AI Agent Engine** (MCP/A2A) | Non-goal for MVP. Basic LLM integration for alert analysis may be included as an enhancement. | v2 planning starts |
| **Hasura full federation** (YugabyteDB + CouchDB + ClickHouse) | MVP uses direct database access from functions. Hasura is deployed but not fully configured for cross-store federation. | v2 planning starts |
| **Production region-specific configurations** (compliance, data locality, network policies per region) | v1 is single-cluster MVP. Region-specific configuration requires real compliance requirements. | Before production deployment |
| **Backup/DR strategy** (etcd backup, Ceph snapshots, database backup) | Operational concern, not architecture-invariant. Backup strategy depends on production storage topology. | Before production deployment |
| **Resource sizing per environment** | Depends on actual load testing results from MVP validation. Premature sizing would be incorrect. | After MVP baseline established |
| **Canary analysis thresholds** (error rate, latency p99 for Argo Rollouts) | Tuning depends on real workload patterns and baseline metrics. | Before production deployment |
| **Casbin policy schema format** (PERM model, relationship tuples) | Policy design is an implementation detail of story-level work, not architecture invariant. | Sprint 1 story creation |
| **Argo Workflows vs KNative+Restate split for specific scenarios** | Both are available; exact workload assignment depends on use case characteristics. | Per-story implementation |
| **Observability storage backend** (Ceph vs local vs S3-compatible) | Default to Ceph for simplicity. Optimization depends on VictoriaMetrics performance characteristics under real load. | When VictoriaMetrics performance tuning begins |
| **Pulsar topic partition counts** | Configurable per `device_type` plus `region_id`. Exact counts depend on device fleet size and message volume. | Per-deployment configuration |
| **Bidirectional device communication** | v1 is telemetry ingestion only. Sending signals back to devices requires a dedicated microservice. | Post-v1 |

---

## 13. Glossary

| Term | Definition |
|------|-----------|
| **A2A** | Agent-to-Agent protocol for inter-agent communication and task delegation |
| **ABAC** | Attribute-Based Access Control; evaluates dynamic attributes (time, location, device state) for permission decisions |
| **API-Key** | Auth token in `X-API-Key` header, used for messaging routes at Envoy Gateway |
| **ApplicationSet** | Argo CD resource generating Application manifests from parameters |
| **ArcadeDB** | Multi-model database for graph traversals, entity lineage, and relationship queries |
| **Argo CD** | GitOps sync engine reconciling Git state to Kubernetes clusters |
| **Argo Events** | Event-driven automation triggering workflows from Git changes or external signals |
| **Argo Rollouts** | Progressive delivery controller for canary/blue-green deployments with automated rollback |
| **Argo Workflows** | DAG-based workflow engine for multi-step pipeline tasks |
| **Backstage** | Developer portal with Software Catalog and Golden Path Templates |
| **Casbin** | Authorization library implementing RBAC, ReBAC, and ABAC models with DENY-wins conflict resolution |
| **Casdoor** | AuthN platform providing JWT validation, SSO, and identity federation |
| **Ceph** | Distributed block (RBD) and file (CephFS) storage via CSI drivers |
| **Cilium** | eBPF-based CNI with kube-proxy replacement, L2 load balancing, ClusterMesh, and Hubble |
| **ClickHouse** | Columnar analytical database for time-series telemetry storage and aggregation |
| **CommonEnvelope** | Standardized Protobuf message format: device_id, device_type, event_type, timestamp, payload, region_id, origin, idempotency_key |
| **CouchDB** | Document database storing entity hierarchy with `_changes` feed for real-time change consumption |
| **Envoy Gateway** | Kubernetes Gateway API ingress handling TLS termination, rate limiting, routing, and ext_authz |
| **Freight** | Kargo artifact representing a promotable set of images and configuration references |
| **Golden Path Template** | Backstage scaffolding template generating service repos with GitOps manifests |
| **Harbor** | Local OCI registry with Trivy vulnerability scanning, Cosign image signing, and Helm chart storage |
| **Hasura** | GraphQL engine federating YugabyteDB, CouchDB, and ClickHouse |
| **Infisical** | Secrets management with Kubernetes Operator and CSI Driver for runtime secret injection |
| **Kargo** | GitOps lifecycle promotion engine with image detection and Freight-based multi-stage promotion |
| **KeyDB** | In-memory store (Redis-compatible) for sub-millisecond hot state caching, dedup set, and pub-sub |
| **KNative** | Serverless platform for scale-to-zero and event-driven workloads on Kubernetes |
| **MCP** | Model Context Protocol for structured AI tool invocation |
| **OpenTelemetry Collector** | Vendor-agnostic OTLP trace receiver exporting to configured backends |
| **Pulsar** | Primary message engine with native MQTT/gRPC protocol handlers, Pulsar Functions, and tiered storage |
| **Pulsar Functions** | Serverless compute within Pulsar for windowed aggregation, schema validation, and JDBC Sink writes |
| **RBAC** | Role-Based Access Control; base role assignments (manager, operator, administrator, etc.) |
| **ReBAC** | Relationship-Based Access Control (Google Zanzibar); access derived from user-object relationships |
| **Restate** | Stateful workflow engine for SAGAs, event sourcing, and durable execution with exactly-once semantics |
| **Spegel** | P2P container image distribution DaemonSet at the containerd level |
| **Spin Function** | WASM workload via SpinKube for stateless Kafka stream processing, sub-10ms latency |
| **SpinKube** | WASM runtime on Kubernetes: containerd-shim-spin, Spin Operator, SpinApp CRD |
| **Stage** | Kargo resource defining an environment tier with promotion rules |
| **Sync Wave** | Argo CD ordering mechanism: CRDs -> Network -> Storage -> Platform Core -> Applications |
| **Talos Linux** | Immutable, API-managed Kubernetes OS. Declarative YAML configuration, no SSH or bash |
| **VMCluster** | VictoriaMetrics cluster mode: vmstorage (storage nodes), vminsert (ingestion), vmselect (query) |
| **Warehouse** | Kargo resource polling registries for new image digests matching SemVer subscriptions |
| **WireGuard** | VPN overlay for encrypted cross-cluster ClusterMesh connectivity |
| **YugabyteDB** | Distributed SQL for transactional state, PostgreSQL-compatible, with CDC feed |

---

*End of Solution Design Document — HPDC v1*
