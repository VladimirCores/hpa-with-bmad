---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - output/planning-artifacts/prds/prd-HPDC-2026-07-21/prd.md
  - output/planning-artifacts/architecture/architecture-HPDC-2026-07-30/ARCHITECTURE-SPINE.md
  - output/planning-artifacts/architecture/architecture-HPDC-2026-07-30/SOLUTION-DESIGN.md
---

# High Performance Distributed Cluster (HPDC) - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for High Performance Distributed Cluster (HPDC), decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR-1: Multi-protocol device ingestion — accept telemetry via MQTT, HTTP, gRPC at the ingestion edge using Pulsar native protocol handlers (MoP + gRPC handler); HTTP 429 on rate over capacity.
FR-2: Common envelope normalization — normalize all inbound payloads into a standard envelope (device_id, device_type, event_type, timestamp, payload, region_id) before publishing; reject missing device_id/timestamp (400), preserve raw payload untransformed, reject >64KB (413).
FR-3: Topic partitioning by device type and region — internal Pulsar topics partitioned by device_type + region_id with configurable partition count and ordering guarantees.
FR-4: Back-pressure management — exponential backoff on producers when consumer lag exceeds threshold; drop messages with metric increment (ingestion_dropped_total with reason label) when buffer full.
FR-5: Spin function stream processing — Spin functions via SpinKube consume Kafka topics performing stateless transforms (field mapping, enrichment, filtering) with sub-10ms p99 latency; scale replicas by consumer lag.
FR-6: Pulsar function telemetry processing — Pulsar functions perform aggregation, windowing, and batched ClickHouse writes via JDBC Sink (batch 25,000, 500ms flush, 3 retries then DLQ).
FR-7: ClickHouse analytical storage — MergeTree/ReplacingMergeTree tables partitioned by time and device_type; device_metrics table ORDER BY (device_type, processed_timestamp); 1M rows in <2s; per-env retention.
FR-8: Hot state caching in KeyDB — device state/alert context reads <1ms (p99); configurable TTL (default 5 min); transparent fallback to CouchDB/ClickHouse on miss.
FR-9: Alert signal ingestion via directed streams — dedicated API endpoint for alert signals (alert_id, device_id, severity, timestamp, metadata) routed to Kafka topics separate from telemetry; parallel processing without blocking ingestion.
FR-10: Alert state machine — stateful workflow initial → acknowledged → investigating → resolved → closed; persisted in CouchDB (100ms), cached in KeyDB (50ms); invalid transitions rejected with 409.
FR-11: Automated alert response — trigger device-communication signals (200ms), external webhooks (500ms, 3 attempts exponential backoff), and workflow processes; all logged with correlation ID.
FR-12: Human-in-the-loop alert handling — operators acknowledge/investigate/resolve alerts via central hub SPA; full audit trail; optimistic locking prevents concurrent modification.
FR-13: Triple-database entity storage — CouchDB (entity hierarchy documents), ArcadeDB (graph/lineage), YugabyteDB (relational state); all accessible from KNative and Spin functions; CouchDB _changes feed; ArcadeDB traversal <100ms on 10K-node graphs; Ceph RBD persistence.
FR-14: Entity CRUD and state management — CRUD for companies, clients, devices, assets with RBAC, audit logging (actor, timestamp, diff), bulk ops up to 1000 entities.
FR-15: Change-driven business logic via KNative + Restate — react to CouchDB _changes and YugabyteDB CDC within 500ms; exactly-once via Restate virtual object state; retry + DLQ on failure.
FR-16: Unified GraphQL API via Hasura — federates YugabyteDB, CouchDB, ClickHouse at /gql; cross-store joins <2s; Hasura permission model per role.
FR-17: Backstage developer portal — Software Catalog, Golden Path Templates scaffolding repos (Dockerfile, Helm chart, catalog-info.yaml, Kargo + ArgoCD manifests); KNative + Spin deployment via templates; Argo CD plugin sync status.
FR-18: Kargo lifecycle promotion — Warehouse SemVer image detection, dev Stage auto-promotion, production manual approval, updated digests committed to Kustomize overlays.
FR-19: Argo CD sync engine — ApplicationSet directory generator per-stage; Sync Waves (-10 CRDs, -5 Network, -4 Storage, -3 Platform Core, 1 Applications); sync within 60s; multi-cluster via cluster secrets.
FR-20: Argo Rollouts progressive delivery — canary 90/10 default with VictoriaMetrics analysis; auto-rollback on error threshold; blue-green alternative.
FR-21: Argo Events and Workflows — sensors on Git push, Harbor image update, Kargo Freight creation; DAG workflows for build→test→scan→deploy; execution logging.
FR-22: Talos Linux substrate — immutable, API-managed, declarative machine config YAML; no SSH/bash; cluster lifecycle via Talos API; kube-proxy disabled.
FR-23: Cilium eBPF networking — CNI with kubeProxyReplacement:true; L2 load balancing (CiliumL2AnnouncementPolicy + CiliumLoadBalancerIPPool); ClusterMesh for production.
FR-24: Rook-Ceph persistent storage — CephCluster with OSDs on dedicated disks; RBD + CephFS StorageClasses with dynamic provisioning; all stateful data persisted to Ceph.
FR-25: VictoriaMetrics cluster metrics — vmstorage/vminsert/vmselect with configurable replicas; vmagent scraping; PromQL <2s for 24h range; per-env retention.
FR-26: Log collection via vmlog — stdout/stderr from all pods indexed; search by namespace, pod, content within 5s; per-env retention.
FR-27: Distributed tracing via OpenTelemetry Collector — OTLP receiver; export to VictoriaMetrics or Jaeger; configurable sampling per service.
FR-28: Grafana dashboards and AlertManager — platform health, telemetry throughput, alert stats, business stakeholder dashboards; configurable AlertManager routing.
FR-29: Cilium Hubble network observability — flows, DNS, HTTP/gRPC traffic, service dependency maps, network policy visualization; PromQL queryable.
FR-30: Local Harbor OCI registry — Trivy/Clair scanning on push; reject high-priority CVEs above threshold; Cosign signature verification; Helm charts as OCI artifacts; pre-populated for air-gapped deploy.
FR-31: Spegel P2P image distribution — DaemonSet on all worker nodes; serve cached images to peers; reduce multi-pod scale-up pull time by >50%.
FR-32: Local Git mirror — GitLab self-hosted or Gitea; mirror gitops-infra, gitops-workloads, app-source-code; GitOps pipeline operates fully offline.
FR-33: Cross-cluster service discovery via ClusterMesh — establish ClusterMesh between regions over WireGuard/Netmaker VPN; encrypted cross-cluster traffic; no manual discovery config.
FR-34: Regional data sovereignty — independent data stores per region (ClickHouse, CouchDB, YugabyteDB, ArcadeDB, KeyDB, PostgreSQL); no cross-region replication by default.
FR-35: Central hub cross-region visibility — query regional APIs with region-scoped auth; aggregated dashboards; per-region drill-down; no regional data stored at hub.
FR-36: Envoy Gateway edge routing — Kubernetes Gateway API resources (HTTPRoute/GRPCRoute/TLSRoute) routing /data→CouchDB, /api→KNative, /gql→Hasura, /events→Kafka, /telemetry→Pulsar; per-route rate limiting.
FR-37: TLS termination — at Envoy Gateway via cert-manager auto-renewal; reject plaintext HTTP (configurable per route).
FR-38: API-key authentication for messaging routes — X-API-Key validated natively at Envoy Gateway for /events and /telemetry; 401 on missing/invalid; multiple keys as EG secrets; no Casdoor/Casbin involvement.
FR-39: OpenAPI specification governance — Swagger/OpenAPI YAML in specs/ as source-of-truth contract; CI validation of implementations; Swagger UI at /docs; optional client SDK generation.
FR-40: Authentication via Casdoor — JWT validation at Envoy Gateway for /data, /api, /gql; SSO via OIDC/SAML; refresh tokens with configurable expiration; 401 on invalid.
FR-41: RBAC — Role-Based Access Control — PostgreSQL stores base roles (manager, operator, administrator, technic, developer, CEO, client); Casbin enforcement <5ms p99; role hierarchy (admin > manager > operator > viewer); role change audit log.
FR-42: ReBAC — Relationship-Based Access Control (Google Zanzibar) — relationship tuples in PostgreSQL; Casbin gRPC ext_authz <5ms p99; relationship propagation (company admin inherits client/device access); hot-reload policy updates.
FR-43: ABAC — Attribute-Based Access Control — dynamic attributes (time of day, location, device state, risk, clearance); time-based restrictions; risk-based escalation; <10ms p99 combined with RBAC/ReBAC.
FR-44: Secrets management via Infisical — InfisicalSecret CRD injection into pods; dynamic rotation without restart; secret access audit logging.
FR-45: mTLS for inter-service communication — enforced by Cilium (SPIFFE/SPIRE auto-rotation); reject plaintext HTTP within cluster.
FR-46: LLM integration for decision support — invoke LLM via configured provider; constrain output to actionable recommendations (no autonomous actions without approval); log all interactions; per-use-case model selection.
FR-47: MCP tool invocation — expose platform capabilities as MCP-compatible tools; validate against security policies; log agent ID, tool, params, result.
FR-48: Agent-to-Agent communication (A2A) — agent registration/discovery; authenticated message routing; prevent unauthorized impersonation.

### NonFunctional Requirements

NFR1: Ingestion throughput — sustained 100K RPS per region with p99 latency < 100ms from edge to topic.
NFR2: Memory ceiling — ingestion pods do not exceed 2GB RSS under peak load.
NFR3: Spin function processing latency < 10ms per message (p99).
NFR4: ClickHouse time-range queries returning 1M rows in < 2 seconds.
NFR5: KeyDB cached reads < 1ms (p99); TTL default 5 minutes; transparent fallback on miss.
NFR6: Alert state transition persisted to CouchDB within 100ms; KeyDB cache updated within 50ms.
NFR7: Automated response latency — device communication invoked within 200ms; webhook delivered within 500ms with 3-attempt exponential-backoff retry.
NFR8: Entity CRUD latency < 200ms (p99) across CouchDB and YugabyteDB.
NFR9: GraphQL cross-store query resolution < 2 seconds.
NFR10: ArcadeDB graph traversal < 100ms on 10K-node graphs.
NFR11: Envelope max size 64KB; oversized payloads rejected with HTTP 413.
NFR12: Authorization latency — RBAC/ReBAC evaluation < 5ms (p99) each; ABAC combined < 10ms (p99); combined RBAC+ReBAC+ABAC decision < 15ms (p99).
NFR13: GitOps sync — workload changes reconciled to cluster within 60 seconds of Git commit.
NFR14: Log search by namespace/pod/content within 5 seconds.
NFR15: VictoriaMetrics PromQL queries < 2 seconds response for 24h range.
NFR16: Retention policies per environment — dev 24h, staging 7d, production configurable (ClickHouse and VictoriaMetrics).
NFR17: GitOps-only delivery — direct kubectl forbidden; all environment changes flow Git → Kargo → Argo CD.
NFR18: Air-gapped operation — no internet dependency for delivery, image distribution, or GitOps (Harbor, Spegel, local Git mirror).
NFR19: mTLS for all inter-service communication with auto-rotated certificates (Cilium SPIFFE/SPIRE).
NFR20: Data sovereignty — no cross-region data replication by default.
NFR21: Secrets never stored in Git, ConfigMaps, or environment variables; auto-rotation default 90 days.
NFR22: Full environment bootstrap via GitOps pipeline in < 30 minutes.
NFR23: End-to-end processing latency — normalized message reaches ClickHouse within 2 seconds of ingestion.
NFR24: Alert detection — state transition initiated within 500ms of alert API submission.
NFR25: Audit logging — all entity mutations and alert state changes logged with actor, timestamp, change diff.
NFR26: Optimistic locking prevents concurrent alert state modification by two operators.

### Additional Requirements

- AD-1: Envoy Gateway as exclusive ingress boundary — every external route declared as a Kubernetes Gateway API resource (HTTPRoute/GRPCRoute/TLSRoute); no backend service exposes a port externally without a matching route; TLS termination at EG via cert-manager.
- AD-2: Domain-per-route segregation — five hard domain boundaries (/data, /api, /gql, /telemetry, /events); cross-domain communication only via the event mesh or database change feeds; intra-domain function HTTP calls allowed through mTLS mesh.
- AD-3: Serverless-first compute — all application logic runs on KNative (scale-to-zero) + Restate, SpinKube WASM, Pulsar Functions, or Argo Workflows; no Deployment/StatefulSet for application logic.
- AD-4: Event-mesh as the integration fabric — Pulsar primary message backbone (100K+ RPS telemetry); Kafka secondary for alert signals/events + Spin WASM; DB change feeds bridged to KNative Eventing; Argo Events bridges Git/image events into Argo Workflows.
- AD-5: Protobuf normalized envelope — CommonEnvelope proto (device_id, device_type, event_type, timestamp, payload, region_id, origin, idempotency_key) enforced by Schema Registry on Pulsar and Kafka; origin prevents CDC mutation loops; idempotency_key dedup via KeyDB set (TTL 5 min); max 64KB.
- AD-6: Database ownership boundaries — CouchDB (entity hierarchy/docs), YugabyteDB (transactional state), ArcadeDB (graph/lineage), ClickHouse (telemetry analytics), KeyDB (hot cache, alert state, dedup), PostgreSQL (authN/authZ data only); all serverless functions read/write all stores; shape conventions via code review.
- AD-7: Ceph for all persistent state — every stateful workload (CouchDB, YugabyteDB, ClickHouse, KeyDB, ArcadeDB, Pulsar bookies, Kafka brokers, PostgreSQL) uses Ceph RBD PVCs; no hostPath/emptyDir/local volume; RF=1 dev, RF=3 prod.
- AD-8: mTLS for all inter-service communication — Cilium SPIFFE/SPIRE integration with auto-rotation; EG handles external TLS, internal traffic is mTLS.
- AD-9: GitOps-only delivery — monorepo structure (gitops/, platform/, backend/, frontend/, specs/, charts/, docs/); Kustomize overlays (base/dev/prod); Kargo + Argo CD; direct kubectl forbidden.
- AD-10: Air-gapped delivery — Harbor local OCI registry (Trivy scanning, Cosign signing, CephFS storage in prod); Spegel DaemonSet P2P distribution; GitLab/Gitea local mirror; delivery always GitOps-mediated.
- AD-11: Multi-region data sovereignty — independent database instances per region; no automatic cross-region replication; Cilium ClusterMesh over WireGuard VPN; central hub queries regional APIs with region-scoped auth, never stores regional data.
- AD-12: Observability — structured JSON logs to stdout; OpenTelemetry auto-instrumentation of KNative functions; VictoriaMetrics cluster mode; Cilium Hubble; retention 7d raw / 30d aggregated (1h rollup) / 1y monthly; AlertManager on metric thresholds.
- AD-13: Centralized secrets management — all secrets in Infisical, never in version control; Infisical K8s Operator injects via CSI Driver (volume mounts, not env vars); auto-rotation default 90 days; per-component service accounts.
- Starter template: No external starter template is specified. Dev environment is bootstrapped with `talosctl cluster create` (QEMU backend). The monorepo source tree from AD-9/Solution Design §7 serves as the greenfield starting point for Epic 1.
- Project-wide scripting rule: all bootstrap, cache, verification, and automation scripts must be written in Python 3; do not repeat scripting-language constraints in individual story acceptance criteria.
- Substrate decision (confirmed 2026-07-31): Talos Linux retained as the base OS after evaluating Fedora CoreOS and Flatcar. Rationale: minimal attack surface (no SSH/shell by design, API-managed), alignment with AD-8 mTLS/security posture, and the simple QEMU dev bootstrap via `talosctl cluster create`. FCOS/Flatcar offer better ops familiarity but a larger surface and manual kubeadm/ignition dev bootstrap. Team-familiarity risk is flagged as an operational consideration.
- Technology stack versions pinned: Talos 1.13.7, Cilium 1.19.6, Rook-Ceph 1.20.3, Envoy Gateway 1.8.3, Pulsar 4.2.3, ClickHouse 26.7.1, CouchDB 3.5.2, YugabyteDB 2026.1.0.1, ArcadeDB 26.7.3, VictoriaMetrics 1.148.0, Kargo 1.11.0, SpinKube (shim 0.25.1, Spin 4.0.1, Operator 0.6.1).
- Dev topology: single QEMU VM (or 3-VM HA validation), Rook-Ceph single OSD on loop device/thin-LV, single-replica databases, VictoriaMetrics single-node mode, Harbor pre-populated, Spegel across VMs.
- Production topology: 3+ bare-metal nodes per region, Ceph RF=3 on dedicated disks, clustered databases, VictoriaMetrics cluster mode, Harbor HA on CephFS, Argo CD HA.
- Sync Waves ordering: -10 CRDs → -5 Network policies → -4 Storage (Rook-Ceph/StorageClass) → -3 Platform core → 1 Applications/functions.
- Envoy Gateway route table: /data→CouchDB (JWT+RBAC/ReBAC/ABAC), /api→KNative+Restate (JWT+RBAC/ReBAC/ABAC), /gql→Hasura (JWT+RBAC/ReBAC/ABAC), /events→Kafka (API-Key, no Casbin), /telemetry→Pulsar (API-Key, no Casbin).
- DENY-wins authorization: if any model (RBAC/ReBAC/ABAC) evaluates DENY, the decision is DENY.
- ULID for all entity/resource IDs; ISO-8601/RFC3339 timestamps; structured error payload {"code","message","details"}; three-label taxonomy on workloads (app.kubernetes.io/name, /component, part-of: hpdc-platform).
- Testing strategy: unit tests per language (Go httptest, cargo test WASM, Pulsar harness, Spectral lint), integration tests with in-memory fakes, deployment tests (Kustomize build, argocd app diff, server-side dry-run, kargo verify freight, helm lint), route exposure tests, E2E Playwright suite on live cluster.
- Welcome counter walkthrough (Solution Design §6.1) is the canonical end-to-end reference flow: EG /api/welcome → JWT → Casbin ext_authz → KNative welcome (Go) → SpinApp counter (Rust WASM) → KeyDB INCR → "Welcome (N)".
- Deferred (not MVP): central hub SPA framework, full AI Agent Engine (MCP/A2A), Hasura full federation, region-specific configs, backup/DR strategy, resource sizing, canary analysis thresholds, bidirectional device communication.

### UX Design Requirements

No UX design contract was provided for this project. User-facing requirements are captured in the PRD user journeys (UJ-1..UJ-5) and FR list (e.g., FR-12 central hub alert handling, FR-17 Backstage developer portal, FR-28 Grafana dashboards). MVP UI is limited to Backstage + Grafana; the central hub SPA is deferred to v2.

UX-DR1: Expose operational tool UIs in the MVP — Hubble UI (network flows, FR-29), Argo CD UI (sync/health, FR-19), Kargo UI (promotion state, FR-18), Backstage (developer portal, FR-17), and Grafana (dashboards, FR-28) — via Envoy Gateway routes (e.g., `backstage.hpdc.local`, `grafana.hpdc.local`, `argocd.hpdc.local`, `kargo.hpdc.local`, `hubble.hpdc.local`) for TLS termination and a single entry point. Each tool's NATIVE auth (SSO/RBAC/OIDC) handles access — Casdoor/Casbin ext_authz is NOT enforced on tool-UI routes. This gives tool UIs a consistent exposure class distinct from the five domain routes (which retain Casdoor/Casbin and API-Key auth). Rationale: avoids redundant platform-auth on top of the tools' own identity layers while preserving AD-1 (exclusive ingress boundary, centralized TLS/logging).

### FR Coverage Map

FR1: Epic 4 - Multi-protocol device ingestion (MQTT/HTTP/gRPC)
FR2: Epic 4 - Common envelope normalization
FR3: Epic 4 - Topic partitioning by device type and region
FR4: Epic 4 - Back-pressure management
FR5: Epic 4 - Spin function stream processing
FR6: Epic 4 - Pulsar function telemetry processing
FR7: Epic 4 - ClickHouse analytical storage
FR8: Epic 4 - Hot state caching in KeyDB
FR9: Epic 5 - Alert signal ingestion via directed streams
FR10: Epic 5 - Alert state machine
FR11: Epic 5 - Automated alert response
FR12: Epic 5 - Human-in-the-loop alert handling
FR13: Epic 6 - Triple-database entity storage
FR14: Epic 6 - Entity CRUD and state management
FR15: Epic 6 - Change-driven business logic via KNative + Restate
FR16: Epic 6 - Unified GraphQL API via Hasura
FR17: Epic 3 - Backstage developer portal and workload delivery
FR18: Epic 2 - Kargo lifecycle promotion
FR19: Epic 2 - Argo CD sync engine
FR20: Epic 2 - Argo Rollouts progressive delivery
FR21: Epic 2 - Argo Events and Workflows
FR22: Epic 1 - Talos Linux substrate
FR23: Epic 1 - Cilium eBPF networking
FR24: Epic 1 - Rook-Ceph persistent storage
FR25: Epic 7 - VictoriaMetrics cluster metrics
FR26: Epic 7 - Log collection via vmlog
FR27: Epic 7 - Distributed tracing via OpenTelemetry Collector
FR28: Epic 7 - Grafana dashboards and AlertManager
FR29: Epic 7 - Cilium Hubble network observability
FR30: Epic 2 - Local Harbor OCI registry
FR31: Epic 2 - Spegel P2P image distribution
FR32: Epic 2 - Local Git mirror
FR33: Epic 8 - Cross-cluster service discovery via ClusterMesh (v2)
FR34: Epic 8 - Regional data sovereignty (v2)
FR35: Epic 8 - Central hub cross-region visibility (v2)
FR36: Epic 3 - Envoy Gateway edge routing
FR37: Epic 3 - TLS termination
FR38: Epic 3 - API-key authentication for messaging routes
FR39: Epic 3 - OpenAPI specification governance
FR40: Epic 3 - Authentication via Casdoor
FR41: Epic 3 - RBAC - Role-Based Access Control
FR42: Epic 3 - ReBAC - Relationship-Based Access Control (Zanzibar)
FR43: Epic 3 - ABAC - Attribute-Based Access Control
FR44: Epic 3 - Secrets management via Infisical
FR45: Epic 3 - mTLS for inter-service communication
FR46: Epic 5 - LLM integration for decision support (basic alert analysis in MVP; full engine in Epic 9)
FR47: Epic 9 - MCP tool invocation (v2)
FR48: Epic 9 - Agent-to-Agent communication A2A (v2)

UX-DR1: Epic 3 (Backstage/Argo/Kargo UIs) + Epic 7 (Grafana/Hubble UIs) - tool UI exposure via gateway routes with native auth

## Epic List

## Epic 1: Kubernetes Substrate Provisioning

Platform Engineer can provision a running, immutable Talos Linux cluster with Cilium eBPF networking (kube-proxy replaced, L2 load balancing) and Rook-Ceph persistent storage (RBD + CephFS), ready for platform workloads.

**FRs covered:** FR-22, FR-23, FR-24

**Implementation notes:** Dev bootstrap via `talosctl cluster create` (QEMU); Talos version pinned 1.13.7; Cilium 1.19.6 with kubeProxyReplacement:true and CiliumL2AnnouncementPolicy/CiliumLoadBalancerIPPool; Rook-Ceph 1.20.3 single OSD (loop device/thin-LV) in dev; mTLS mesh via Cilium SPIFFE/SPIRE (AD-8); Ceph for all persistent state (AD-7).

### Story 1.1: Bootstrap Monorepo Structure & Dev Tooling

As a Platform Engineer,
I want the HPDC repository scaffolded with Talos machine configs, Kustomize overlays, and a QEMU bootstrap script,
So that I can provision the substrate without manual setup or external dependencies.

**Acceptance Criteria:**

**Given** the repository is in a clean state
**When** I run the bootstrap script
**Then** the script creates the standard monorepo directories (`gitops/`, `platform/`, `backend/`, `specs/`, `charts/`, `docs/`)
**And** it creates a Talos machine config file under `platform/talos/machine-config.yaml`
**And** it creates a Python 3 dev bootstrap script under `scripts/bootstrap-dev.py` using `talosctl cluster create`
**And** it creates a Kustomize base directory under `gitops/platform/base`
**And** it creates a README with the bootstrap command and expected output
**And** the script exits with a non-zero status on any failure

### Story 1.2: Provision Offline Talos Dev Cluster with Persistent QEMU Disks

As a Platform Engineer,
I want to provision a clean Talos Linux dev cluster from persistent QEMU VM disk images using `talosctl` bootstrap,
So that the substrate is immutable, API-managed, offline-capable, and ready for Cilium and Rook-Ceph installation.

**Acceptance Criteria:**

**Given** the repository contains the Talos machine config, bootstrap script, and pre-cached Talos installer/container images
**When** I run the bootstrap script in offline mode
**Then** it creates persistent QEMU disk image files for the Talos VMs instead of ephemeral VMs
**And** it reuses existing QEMU disk image files across reruns unless an explicit cleanup flag is provided
**And** it boots Talos Linux into maintenance mode and provisions a Talos cluster with version 1.13.7 without requiring internet access
**And** it leaves the persistent disk images available for Rook-Ceph OSD storage
**And** it configures the local `talosconfig` for the new cluster
**And** it verifies cluster access with `talosctl health`
**And** it verifies node discovery with `talosctl get nodes`
**And** it verifies disk installation with `talosctl get disks`
**And** it generates Kubernetes access with `talosctl kubeconfig`
**And** it confirms the cluster is usable without SSH
**And** it exits with a non-zero status on any failure

### Story 1.3: Install Offline Cilium eBPF Networking with kube-proxy Replacement

As a Platform Engineer,
I want to install Cilium 1.19.6 with `kubeProxyReplacement:true` and L2 load balancing on the offline Talos dev cluster,
So that the cluster has service load balancing without kube-proxy and is ready for secure service networking.

**Acceptance Criteria:**

**Given** the offline Talos dev cluster from Story 1.2 is healthy
**And** Cilium 1.19.6 images are pre-cached locally
**When** I apply the Cilium manifest from GitOps
**Then** Cilium is installed as the cluster CNI
**And** kube-proxy is disabled or not present
**And** `kubeProxyReplacement:true` is configured
**And** `CiliumL2AnnouncementPolicy` and `CiliumLoadBalancerIPPool` are applied for L2 load balancing
**And** Cilium agent and operator pods are `Ready`
**And** a test service behind a local LoadBalancer can be reached through the L2 load balancer
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 1.4: Provision Offline Rook-Ceph Persistent Storage on Persistent QEMU Disks

As a Platform Engineer,
I want to install Rook-Ceph 1.20.3 on the persistent QEMU disk images with RBD and CephFS StorageClasses,
So that all stateful platform components have persistent storage that survives cluster recreation.

**Acceptance Criteria:**

**Given** the offline Talos dev cluster from Story 1.2 is healthy
**And** Cilium networking from Story 1.3 is installed
**And** persistent QEMU disk image files are available for Rook-Ceph OSDs
**And** Rook-Ceph 1.20.3 images are pre-cached locally
**When** I apply the Rook-Ceph manifest from GitOps
**Then** Rook-Ceph 1.20.3 is installed
**And** if Rook-Ceph is already initialized on the persistent disks, the script detects the existing `CephCluster` and OSDs and preserves the existing data
**And** if Rook-Ceph is not initialized, the script creates a CephCluster with OSDs on the persistent QEMU disk devices
**And** RBD and CephFS StorageClasses are provisioned with dynamic provisioning
**And** dev topology uses single-OSD Ceph with RF=1 on the persistent disks
**And** stateful data is stored in Ceph, not in hostPath, emptyDir, or local ephemeral volumes
**And** destructive OSD initialization or wiping only happens when an explicit cleanup flag is provided
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 1.5: Enable Cilium mTLS Mesh with SPIFFE/SPIRE

As a Platform Engineer,
I want to enable Cilium mTLS mesh with SPIFFE/SPIRE identities on the offline Talos dev cluster,
So that inter-service traffic is encrypted and authenticated without relying on plaintext HTTP inside the cluster.

**Acceptance Criteria:**

**Given** the offline Talos dev cluster from Story 1.2 is healthy
**And** Cilium networking from Story 1.3 is installed
**And** Rook-Ceph persistent storage from Story 1.4 is installed
**And** Cilium mTLS/SPIFFE/SPIRE images are pre-cached locally
**When** I apply the Cilium mTLS mesh manifest from GitOps
**Then** Cilium mTLS is enabled for pod-to-pod and service traffic
**And** SPIFFE/SPIRE identities are issued to workloads
**And** a test service-to-service request succeeds with valid mTLS identity
**And** a test service-to-service request fails without valid mTLS identity
**And** plaintext HTTP within the cluster is rejected
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

**Implementation notes:** This story owns the Cilium mTLS/SPIRE manifest and installer (`gitops/cilium/base/cilium-mtls.yaml`, `scripts/install-cilium-mtls-dev.py`). Epic 3 Story 3.9 revalidates the same manifest for FR-45 — do not fork a second mTLS manifest under Epic 3.

### Story 1.6: Provision Local Harbor OCI Registry with Scanning and Signing

As a platform engineer,
I want a local Harbor OCI registry with vulnerability scanning and signing,
So that air-gapped deployments can pull trusted images offline.

**Acceptance Criteria:**

**Given** Harbor is deployed on the dev cluster
**When** an image is pushed to the local registry
**Then** the image is scanned for vulnerabilities (Trivy)
**And** high-priority CVEs above threshold are rejected
**And** images are Cosign-signed and verified
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

**Implementation notes:** Delivered as unplanned substrate work reused by Story 2.1 (which adds the pipeline/offline-cache dimension). Tracked as story 1-6 in sprint-status; record added here for plan/tracker parity.

## Epic 2: GitOps Delivery Pipeline

Platform Engineer and Developer can deliver workloads end-to-end through Git → Kargo → Argo CD with progressive delivery, and fully air-gapped delivery via local Harbor registry, Spegel P2P distribution, and local Git mirror.

**FRs covered:** FR-18, FR-19, FR-20, FR-21, FR-30, FR-31, FR-32

**Implementation notes:** Monorepo structure per AD-9 (gitops/, platform/, backend/, specs/, charts/); Kustomize overlays base/dev/prod; Kargo Warehouse/Stage/Freight; Argo CD ApplicationSet + Sync Waves (-10 CRDs → -5 Network → -4 Storage → -3 Platform Core → 1 Applications); offline image cache is pre-pulled into Harbor by scripts after Harbor is ready and refreshed by pinned digest/version check before Kargo/Argo consume images; UX-DR1 tool-UI routes are sequenced after Epic 3 installs Envoy Gateway; GitOps-only (no direct kubectl).

### Story 2.1: Provision Local Harbor OCI Registry with Scanning and Signing

As a Platform Engineer,
I want to install a local Harbor OCI registry with Trivy/Clair scanning, Cosign signature verification, and OCI Helm chart support,
So that air-gapped deployments can pull trusted images and charts without internet access.

**Acceptance Criteria:**

**Given** the offline Talos dev cluster from Epic 1 is healthy
**And** Harbor container images are pre-cached locally
**When** I apply the Harbor manifest from GitOps
**Then** Harbor is installed as a local OCI registry
**And** Trivy/Clair scanning is enabled on image push
**And** Cosign signature verification is enabled for image pulls
**And** Helm charts can be published as OCI artifacts
**And** the registry is pre-populated for air-gapped deployment use
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 2.2: Preload Offline Image Cache into Harbor

As a Platform Engineer,
I want to pre-pull required images into local Harbor and record pinned digests,
So that later pipeline components can run in an air-gapped environment.

**Acceptance Criteria:**

**Given** Harbor from Story 2.1 is ready
**And** a pinned image manifest lists image names, versions/digests, and source registries
**When** I run the Python pre-cache script
**Then** required images are pulled from source registries and pushed to local Harbor
**And** the script records the final Harbor digest for each image in a cache manifest
**And** the script verifies local Harbor pulls without internet access
**And** unchanged digests are skipped
**And** destructive cleanup is not performed
**And** the process completes offline after initial pulls
**And** the script exits with a non-zero status on any failure

### Story 2.3: Refresh Cached Images on Version or Digest Change

As a Platform Engineer,
I want the image-cache script to compare pinned image versions/digests against Harbor and refresh changed images,
So that offline deployments always use the intended versions without manual intervention.

**Acceptance Criteria:**

**Given** the cache manifest from Story 2.2 exists
**When** I run the cache refresh check
**Then** the script reads each pinned source image version/digest
**And** compares it against the local Harbor digest
**And** unchanged images are skipped
**And** changed images are pulled from the source registry and refreshed in Harbor
**And** stale local images are not deleted until a successful refresh completes
**And** if the process is offline and the local digest differs from the pinned digest, the script fails with a clear error
**And** the cache manifest is updated after successful refreshes
**And** the script exits with a non-zero status on any failure

### Story 2.4: Provision Local Git Mirror for Offline GitOps

As a Platform Engineer,
I want to provision a local Git mirror for required GitOps repositories,
So that the GitOps pipeline can operate fully offline.

**Acceptance Criteria:**

**Given** the offline Talos dev cluster from Epic 1 is healthy
**When** I apply the local Git mirror manifest from GitOps
**Then** a local Git server is installed
**And** the required repositories `gitops-infra`, `gitops-workloads`, and `app-source-code` are created or mirrored
**And** the local Git mirror can be cloned and pushed without internet access
**And** GitOps manifests reference local Harbor and local Git endpoints
**And** no secrets are stored in Git repositories
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 2.5: Provision Spegel P2P Image Distribution

As a Platform Engineer,
I want to deploy Spegel across worker nodes with cached images served peer-to-peer,
So that multi-pod scale-up image pull time is reduced and offline image distribution remains resilient.

**Acceptance Criteria:**

**Given** the offline Talos dev cluster from Epic 1 is healthy
**And** Harbor from Story 2.1 is installed
**And** required images are preloaded into Harbor by Story 2.2
**When** I apply the Spegel manifest from GitOps
**Then** Spegel is installed as a DaemonSet on all worker nodes
**And** cached images are served to peer nodes
**And** multi-pod scale-up image pull time is reduced by more than 50% compared with pulling each image independently
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 2.6: Configure Kargo Warehouse, Stage, and Freight Promotion

As a Platform Engineer,
I want to configure Kargo 1.11.0 Warehouse, Stage, and Freight promotion with dev auto-promotion and production manual approval,
So that GitOps delivery can move images through stages in an offline pipeline.

**Acceptance Criteria:**

**Given** Harbor from Story 2.1 is installed
**And** Local Git Mirror from Story 2.4 is installed
**And** Spegel from Story 2.5 is installed
**When** I apply the Kargo manifest from GitOps
**Then** Kargo 1.11.0 is installed
**And** Kargo Warehouse, Stage, and Freight resources are created
**And** dev Stage auto-promotion is configured
**And** production promotion requires manual approval
**And** updated image digests are committed to Kustomize overlays
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 2.7: Configure Argo CD ApplicationSet and Sync Waves

As a Platform Engineer,
I want to configure Argo CD ApplicationSet and sync waves so GitOps deployments apply in the correct order,
So that workload changes reconcile to the cluster within 60 seconds of a Git commit.

**Acceptance Criteria:**

**Given** Local Git Mirror from Story 2.4 is installed
**And** Kargo from Story 2.6 is installed
**When** I apply the Argo CD manifest from GitOps
**Then** Argo CD is installed
**And** ApplicationSet directory generation is configured per stage
**And** Sync Waves are configured as `-10 CRDs`, `-5 Network`, `-4 Storage`, `-3 Platform Core`, and `1 Applications`
**And** workload changes sync within 60 seconds of a Git commit
**And** multi-cluster access is configured through cluster secrets
**And** direct kubectl is not used for environment changes
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 2.8: Configure Argo Rollouts Progressive Delivery

As a Platform Engineer,
I want to configure Argo Rollouts with canary 90/10 default analysis, automatic rollback on error threshold, and blue-green alternative,
So that workload changes can be deployed progressively with safe rollback.

**Acceptance Criteria:**

**Given** Argo CD from Story 2.7 is installed
**When** I apply the Argo Rollouts manifest from GitOps
**Then** Argo Rollouts is installed
**And** canary analysis is configured with 90/10 traffic split by default
**And** VictoriaMetrics analysis is configured for rollout health checks
**And** auto-rollback is enabled on the configured error threshold
**And** blue-green deployment is available as an alternative strategy
**And** rollout status is visible through GitOps-managed manifests
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 2.9: Configure Argo Events and Workflows

As a Platform Engineer,
I want to configure Argo Events and Workflows to trigger on Git push, Harbor image update, and Kargo Freight creation,
So that build→test→scan→deploy workflows run without internet access.

**Acceptance Criteria:**

**Given** Argo CD from Story 2.7 is installed
**When** I apply the Argo Events and Workflows manifest from GitOps
**Then** Argo Events and Workflows are installed
**And** sensors are configured for Git push, Harbor image update, and Kargo Freight creation
**And** a DAG workflow is configured for build → test → scan → deploy
**And** execution logs are visible through GitOps-managed observability
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 2.10: Validate Offline GitOps Pipeline and Image Cache

As a Platform Engineer,
I want to run an end-to-end offline verification suite for the GitOps delivery pipeline,
So that Harbor, Spegel, Git mirror, Kargo, Argo CD, Argo Rollouts, and Argo Events work together without internet access.

**Acceptance Criteria:**

**Given** all Epic 2 components from Stories 2.1–2.9 are installed
**When** I run the offline GitOps verification suite
**Then** Harbor serves required images without internet access
**And** the offline image cache refresh check detects unchanged digests and skips refresh
**And** the local Git mirror can be cloned without internet access
**And** Kargo promotes a Freight through dev → stage → prod
**And** Argo CD syncs workloads within 60 seconds using sync waves
**And** Argo Rollouts performs a 90/10 canary and rolls back on failure
**And** Argo Events triggers a workflow on Git push and Harbor image update
**And** Spegel serves cached images to peers
**And** the verification suite exits with a non-zero status on any failure

## Epic 3: Secure Gateway & Access Control

Platform Administrator can secure all platform routes: exclusive Envoy Gateway ingress with TLS, JWT authN via Casdoor, RBAC/ReBAC/ABAC authZ via Casbin (DENY-wins), API-Key auth for messaging routes, mTLS inter-service encryption, centralized secrets via Infisical, OpenAPI-spec governance, and post-EG tool UI exposure for Backstage, Argo CD UI, Kargo UI, Grafana, and Hubble.

**FRs covered:** FR-17, FR-36, FR-37, FR-38, FR-39, FR-40, FR-41, FR-42, FR-43, FR-44, FR-45

**Implementation notes:** Five domain routes (/data JWT+Casbin, /api JWT+Casbin, /gql JWT+Casbin, /events API-Key, /telemetry API-Key) per AD-1/AD-2; Casbin Go gRPC ext_authz service; Casbin PERM model + policy schema (deferred detail from architecture, resolved here); Infisical K8s Operator + CSI Driver; secrets rotation default 90 days; tool UI routes are installed after Envoy Gateway exists and after the target tool is deployed.

### Story 3.1: Install Envoy Gateway Edge Routing

As a Platform Administrator,
I want to install Envoy Gateway and Gateway API resources for platform routes,
So that all external traffic enters through one controlled ingress boundary.

**Acceptance Criteria:**

**Given** the offline Talos dev cluster from Epic 1 is healthy
**And** Cilium networking from Epic 1 is installed
**And** Envoy Gateway 1.8.3 images are pre-cached locally
**When** I apply the Envoy Gateway manifest from GitOps
**Then** Envoy Gateway 1.8.3 is installed
**And** GatewayClass and Gateway resources are created
**And** HTTPRoute, GRPCRoute, and TLSRoute resources are declared for `/data`, `/api`, `/gql`, `/events`, and `/telemetry`
**And** per-route rate limiting is configured
**And** backend services do not expose external ports without a matching route
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 3.2: Configure TLS Termination with cert-manager

As a Platform Administrator,
I want Envoy Gateway to terminate TLS with cert-manager auto-renewal and reject plaintext HTTP,
So that external traffic is encrypted and insecure ingress is blocked.

**Acceptance Criteria:**

**Given** Envoy Gateway from Story 3.1 is installed
**When** I apply the TLS termination manifest from GitOps
**Then** cert-manager TLS termination is configured for Envoy Gateway
**And** TLS certificates auto-renew
**And** plaintext HTTP is rejected on TLS-protected routes
**And** TLS termination remains centralized at Envoy Gateway
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 3.3: Configure API-Key Auth for Messaging Routes

As a Platform Administrator,
I want Envoy Gateway to validate X-API-Key credentials for `/events` and `/telemetry`,
So that messaging routes can accept authenticated machine traffic without Casdoor/Casbin.

**Acceptance Criteria:**

**Given** Envoy Gateway from Story 3.1 is installed
**When** I apply the API-key authentication manifest from GitOps
**Then** X-API-Key validation is configured for `/events` and `/telemetry`
**And** missing or invalid API keys return HTTP 401
**And** API keys are stored as Envoy Gateway secrets
**And** Casdoor/Casbin is not involved in messaging route authentication
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 3.4: Configure Casdoor JWT AuthN for Domain Routes

As a Platform Administrator,
I want Casdoor JWT authentication for `/data`, `/api`, and `/gql`,
So that users and services can access platform routes through centralized SSO.

**Acceptance Criteria:**

**Given** Envoy Gateway from Story 3.1 is installed
**When** I apply the Casdoor JWT authentication manifest from GitOps
**Then** JWT validation is configured for `/data`, `/api`, and `/gql`
**And** SSO via OIDC/SAML through Casdoor is configured
**And** refresh tokens use configurable expiration
**And** invalid JWTs return HTTP 401
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 3.5: Configure Casbin RBAC Policies

As a Platform Administrator,
I want RBAC policies enforced through Casbin,
So that users can access platform resources according to role hierarchy and DENY-wins authorization.

**Acceptance Criteria:**

**Given** Casdoor JWT auth from Story 3.4 is installed
**When** I apply the RBAC policy manifest from GitOps
**Then** base roles are created: manager, operator, administrator, technic, developer, CEO, and client
**And** role hierarchy is configured as admin > manager > operator > viewer
**And** Casbin RBAC enforcement is configured with p99 latency under 5ms
**And** role changes are audit logged
**And** DENY-wins authorization is enforced
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 3.6: Configure Casbin ReBAC Policies

As a Platform Administrator,
I want relationship-based access control through Casbin,
So that company admins inherit client and device access automatically.

**Acceptance Criteria:**

**Given** RBAC from Story 3.5 is installed
**When** I apply the ReBAC policy manifest from GitOps
**And** relationship tuples are stored in PostgreSQL
**Then** Casbin gRPC ext_authz is configured for ReBAC
**And** relationship propagation grants company admin access to client and device resources
**And** hot-reload policy updates are enabled
**And** Casbin ReBAC enforcement is configured with p99 latency under 5ms
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 3.7: Configure Casbin ABAC Policies

As a Platform Administrator,
I want attribute-based access control through Casbin,
So that access decisions can consider time, location, device state, risk, and clearance.

**Acceptance Criteria:**

**Given** RBAC from Story 3.5 and ReBAC from Story 3.6 are installed
**When** I apply the ABAC policy manifest from GitOps
**Then** dynamic attributes are configured for time of day, location, device state, risk, and clearance
**And** time-based restrictions are enforced
**And** risk-based escalation is configured
**And** combined RBAC+ReBAC+ABAC decisions complete with p99 latency under 10ms
**And** DENY-wins authorization is enforced
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 3.8: Configure Infisical Secrets Management

As a Platform Administrator,
I want Infisical to manage platform secrets through CRDs and CSI injection,
So that secrets are never stored in Git, ConfigMaps, or environment variables.

**Acceptance Criteria:**

**Given** Envoy Gateway from Story 3.1 is installed
**When** I apply the Infisical secrets manifest from GitOps
**Then** InfisicalSecret CRD injection is installed
**And** Infisical K8s Operator and CSI Driver are installed
**And** secrets are injected into pods through volume mounts
**And** dynamic secret rotation works without pod restart
**And** secret access is audit logged
**And** default secret rotation is 90 days
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 3.9: Configure mTLS Mesh Enforcement with Cilium

As a Platform Administrator,
I want Cilium to enforce mTLS for inter-service communication,
So that plaintext HTTP inside the cluster is rejected and service traffic is authenticated.

**Acceptance Criteria:**

**Given** Cilium networking from Epic 1 is installed
**When** I apply the Cilium mTLS manifest from GitOps
**Then** SPIFFE/SPIRE auto-rotation is enabled
**And** mTLS is enforced for inter-service communication
**And** plaintext HTTP within the cluster is rejected
**And** service identities are issued to workloads
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

**Implementation notes:** FR-45 (mTLS) is owned by this epic. The enforcement manifest is implemented once in **Epic 1 Story 1.5** (`gitops/cilium/base/cilium-mtls.yaml`, `scripts/install-cilium-mtls-dev.py`); this story revalidates that the same manifest satisfies FR-45 rather than re-implementing it. Keep the mTLS implementation in Story 1.5 and do not fork a second manifest here.

### Story 3.10: Configure OpenAPI Specification Governance

As a Platform Administrator,
I want OpenAPI specifications to govern API contracts,
So that implementations are validated before deployment and clients can discover API contracts.

**Acceptance Criteria:**

**Given** Envoy Gateway from Story 3.1 is installed
**When** I apply the OpenAPI governance manifest from GitOps
**Then** OpenAPI YAML files are stored in `specs/` as the source of truth
**And** CI validation of implementations is configured
**And** Swagger UI is exposed at `/docs`
**And** optional client SDK generation is configured
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 3.11: Provision Backstage Developer Portal and Golden Path Templates

As a Platform Administrator,
I want Backstage installed with Software Catalog and Golden Path templates,
So that developers can scaffold repos and follow GitOps deployment patterns.

**Acceptance Criteria:**

**Given** Envoy Gateway from Story 3.1 is installed
**And** Casdoor JWT auth from Story 3.4 is installed
**When** I apply the Backstage manifest from GitOps
**Then** Backstage developer portal is installed
**And** Software Catalog is configured
**And** Golden Path templates scaffold repos with Dockerfile, Helm chart, catalog-info.yaml, Kargo, and Argo CD manifests
**And** native auth through Casdoor is configured
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

### Story 3.12: Expose Backstage, Argo CD UI, and Kargo UI via Envoy Gateway

As a Platform Administrator,
I want Backstage, Argo CD UI, and Kargo UI exposed through Envoy Gateway routes with native tool auth,
So that tool users have a consistent ingress entry point without redundant platform auth.

**Acceptance Criteria:**

**Given** Envoy Gateway from Story 3.1 is installed
**And** TLS termination from Story 3.2 is configured
**And** Backstage from Story 3.11 is installed
**And** Argo CD and Kargo from Epic 2 are installed
**When** I apply the tool UI route manifest from GitOps
**Then** `backstage.hpdc.local`, `argocd.hpdc.local`, and `kargo.hpdc.local` routes are exposed through Envoy Gateway
**And** each tool’s native auth handles access
**And** Casdoor/Casbin ext_authz is not enforced on tool UI routes
**And** TLS termination is active
**And** the process completes without internet access
**And** the script exits with a non-zero status on any failure

## Epic 4: Real-Time Telemetry Ingestion & Processing

The platform ingests 100K+ RPS telemetry from IoT devices via MQTT/HTTP/gRPC at the Envoy Gateway `/telemetry` route, normalizes payloads into the Protobuf CommonEnvelope, routes to partitioned Pulsar topics, processes in real time (Pulsar Functions for aggregation/windowing + Spin WASM for stateless Kafka transforms), and stores results in ClickHouse with KeyDB hot-state caching.

**FRs covered:** FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-7, FR-8
**NFRs covered:** NFR1, NFR3, NFR4, NFR5, NFR11, NFR13, NFR16, NFR18, NFR21, NFR23
**Additional requirements:** AD-4, AD-5, AD-7, AD-8, AD-9, AD-10, AD-12, AD-13, Pulsar 4.2.3, Kafka, ClickHouse 26.7.1, KeyDB, Python 3 scripting rule, testing strategy, offline GitOps delivery.
**UX Design Requirements:** No UX Design Requirements apply to this epic.

### Story 4.1: Build IoT Device Simulator and Telemetry Acceptance Harness

As a QA Engineer,
I want a tunable IoT device simulator that can generate telemetry across MQTT, HTTP, and gRPC,
So that the telemetry pipeline can be validated at realistic device counts, message rates, regions, and device types.

**Acceptance Criteria:**

**Given** the simulator configuration exists with device count, message rate, device types, and region IDs
**When** I run the simulator against the local dev platform
**Then** it emits telemetry through MQTT, HTTP, and gRPC routes
**And** each message includes device_id, device_type, event_type, timestamp, payload, and region_id
**And** the simulator can target 100K RPS or a lower configured rate for local validation
**And** the simulator exposes throughput, error rate, and latency metrics for validation runs
**And** the simulator exits with a non-zero status on connection, schema, or generation failure

### Story 4.2: Accept Telemetry Through MQTT, HTTP, and gRPC Routes

As a Platform Engineer,
I want the `/telemetry` ingestion route to accept MQTT, HTTP, and gRPC telemetry,
So that heterogeneous IoT devices can publish telemetry without separate protocol adapters.

**Acceptance Criteria:**

**Given** the simulator from Story 4.1 and the `/telemetry` route are available
**When** I publish valid MQTT, HTTP, and gRPC telemetry payloads
**Then** the platform accepts each payload type
**And** each accepted payload is routed to the internal Pulsar ingestion topic
**And** the platform returns HTTP 429 when ingestion exceeds the configured capacity for a device type
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 4.3: Normalize Telemetry into Protobuf CommonEnvelope

As a Backend Developer,
I want all inbound telemetry normalized into the Protobuf CommonEnvelope,
So that downstream Pulsar, Kafka, and processing components share one schema and one data contract.

**Acceptance Criteria:**

**Given** a valid telemetry payload arrives at the ingestion route
**When** it is normalized before publishing to internal topics
**Then** it contains `device_id`, `device_type`, `event_type`, `timestamp`, `payload`, `region_id`, `origin`, and `idempotency_key`
**And** the message is serialized as Protobuf
**And** missing `device_id` or `timestamp` returns HTTP 400 with a structured error
**And** payloads larger than 64KB return HTTP 413 with a structured error
**And** the original payload bytes are preserved untransformed in `payload`
**And** schema compatibility is enforced by Schema Registry

### Story 4.4: Create Partitioned Pulsar Topics for Telemetry

As a Platform Engineer,
I want Pulsar topics partitioned by device type and region,
So that telemetry for the same device type and region can be processed in parallel while preserving ordering.

**Acceptance Criteria:**

**Given** normalized telemetry is published to the ingestion route
**When** the platform creates or uses internal Pulsar topics
**Then** topics are partitioned by `device_type` and `region_id`
**And** messages with the same `device_type` + `region_id` land on the same partition
**And** partition count is adjustable without data loss
**And** the topic configuration supports dev and production overlays
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 4.5: Apply Telemetry Back-Pressure and Drop-Metric Controls

As a Platform Engineer,
I want the ingestion layer to apply back-pressure when consumers lag,
So that the platform prevents memory exhaustion and message loss during load spikes.

**Acceptance Criteria:**

**Given** downstream consumer lag exceeds the configured threshold
**When** producers continue publishing telemetry
**Then** the ingestion layer applies exponential backoff to producers
**And** messages are dropped only when the buffer is full
**And** each dropped message increments `ingestion_dropped_total` with a `reason` label
**And** ingestion pods do not exceed the configured memory ceiling under peak load
**And** the platform remains available for new telemetry after the lag clears
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 4.6: Process Telemetry with Pulsar Functions and Write to ClickHouse

As a Backend Developer,
I want Pulsar Functions to aggregate, window, and batch telemetry writes to ClickHouse,
So that normalized telemetry becomes queryable analytical data with reliable retry behavior.

**Acceptance Criteria:**

**Given** partitioned Pulsar topics contain normalized telemetry
**When** Pulsar Functions process the telemetry stream
**Then** they perform aggregation and windowing
**And** they write ClickHouse batches of 25,000 records with a 500ms flush interval
**And** failed ClickHouse writes retry 3 times before being sent to a dead-letter queue
**And** each write confirms success through the JDBC Sink acknowledgment path
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 4.7: Create ClickHouse Device Metrics Tables and Retention Policies

As a Data Engineer,
I want ClickHouse tables for processed telemetry with time and device-type partitioning,
So that operators can query telemetry analytics quickly and retain data by environment.

**Acceptance Criteria:**

**Given** Pulsar Functions are writing normalized telemetry
**When** the ClickHouse sink initializes storage
**Then** it creates `device_metrics` using MergeTree or ReplacingMergeTree
**And** the table uses `ORDER BY (device_type, processed_timestamp)`
**And** time-range queries return 1M rows in under 2 seconds
**And** retention policies are applied per environment: dev 24h, staging 7d, production configurable
**And** processed telemetry is stored on Ceph-backed persistent storage
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 4.8: Cache Hot Device State and Alert Context in KeyDB

As a Backend Developer,
I want hot device state and alert context cached in KeyDB,
So that downstream telemetry and alert handlers can read context with sub-millisecond latency and fall back safely on cache misses.

**Acceptance Criteria:**

**Given** device state or alert context exists in the authoritative stores
**When** a downstream handler reads that context
**Then** KeyDB returns cached values in under 1ms p99 when present
**And** cached entries use a configurable TTL with 5 minutes as the default
**And** cache misses fall back to CouchDB or ClickHouse without propagating cache errors
**And** cached state is refreshed after authoritative telemetry or alert changes
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 4.9: Process Event Telemetry with Spin WASM Functions

As a Backend Developer,
I want Spin WASM functions to transform event telemetry on Kafka topics,
So that stateless filtering, enrichment, and field-mapping logic runs with very low latency.

**Acceptance Criteria:**

**Given** normalized telemetry is published to the Kafka event path
**When** a Spin function consumes the message
**Then** it performs field mapping, enrichment, or filtering
**And** a single message is processed in under 10ms p99
**And** replicas scale based on Kafka consumer lag
**And** transformed messages are written to the configured downstream store or topic
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 4.10: Validate End-to-End Telemetry Pipeline Performance

As a QA Engineer,
I want an end-to-end telemetry validation suite,
So that the platform proves the telemetry path meets throughput, latency, storage, and offline delivery requirements.

**Acceptance Criteria:**

**Given** the simulator, ingestion routes, normalization, Pulsar topics, Pulsar Functions, ClickHouse, KeyDB, and Spin functions are installed
**When** I run the telemetry validation suite
**Then** the platform sustains 100K RPS from simulated devices in the configured local dev topology
**And** p99 ingestion latency from edge to topic is under 100ms
**And** a normalized message reaches ClickHouse within 2 seconds of ingestion
**And** telemetry metrics, logs, and traces are visible through the observability stack
**And** the validation suite confirms offline operation without internet access
**And** the suite exits with a non-zero status on any failed metric, error path, or offline dependency

## Epic 5: Alert Detection & Response

SOC Analyst can detect security alerts from directed API streams, track them through a stateful lifecycle (initial → acknowledged → investigating → resolved → closed), trigger automated responses (device signals, webhooks, workflows), and handle alerts with full audit trail — plus basic LLM decision support for alert analysis.

**FRs covered:** FR-9, FR-10, FR-11, FR-12, FR-46 (basic)
**NFRs covered:** NFR6, NFR7, NFR12, NFR21, NFR24, NFR25, NFR26
**Additional requirements:** AD-2, AD-3, AD-4, AD-5, AD-6, AD-7, AD-8, AD-9, AD-10, AD-12, AD-13, Python 3 scripting rule, testing strategy, offline GitOps delivery.
**UX Design Requirements:** No UX Design Requirements apply to this epic.

### Story 5.1: Ingest Alert Signals Through Directed Kafka Streams

As a SOC Analyst,
I want alert signals submitted through a dedicated API stream,
So that concurrent alerts can be processed in parallel without blocking telemetry ingestion.

**Acceptance Criteria:**

**Given** the alert API endpoint and `/events` route are available
**When** I submit a valid alert signal with `alert_id`, `device_id`, `severity`, `timestamp`, and metadata
**Then** the platform accepts the alert signal
**And** the alert signal is routed to a Kafka topic separate from telemetry
**And** concurrent alert submissions do not block telemetry ingestion
**And** invalid or malformed alert payloads return a structured HTTP error
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 5.2: Persist Alert State Machine Transitions

As a SOC Analyst,
I want alert state transitions persisted to CouchDB and cached in KeyDB,
So that alert lifecycle state is durable, fast to read, and safe to audit.

**Acceptance Criteria:**

**Given** an alert exists in the initial state
**When** it transitions to acknowledged, investigating, resolved, or closed
**Then** the transition follows the valid path `initial → acknowledged → investigating → resolved → closed`
**And** the transition is persisted to CouchDB within 100ms
**And** KeyDB is updated within 50ms of the CouchDB write
**And** invalid transitions return HTTP 409 with the current state
**And** each transition records actor, timestamp, and change diff
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 5.3: Trigger Automated Alert Responses

As a SOC Analyst,
I want automated responses triggered when alert conditions are met,
So that alerts can be acted on quickly while still preserving human approval for sensitive actions.

**Acceptance Criteria:**

**Given** an alert reaches the configured trigger condition
**When** the automated response engine evaluates it
**Then** it invokes the device communication microservice within 200ms
**And** it delivers webhook payloads within 500ms using 3 attempts with exponential backoff
**And** it starts the appropriate workflow process
**And** every automated response is logged with correlation ID tied to `alert_id`
**And** ambiguous low-confidence AI suggestions are escalated for manual review instead of executed
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 5.4: Manage Human Alert Handling with Audit Trail

As a SOC Analyst,
I want to acknowledge, investigate, and resolve alerts with notes and audit history,
So that incident response actions are visible, reviewable, and protected from concurrent edits.

**Acceptance Criteria:**

**Given** an alert is active and visible in the operator workflow
**When** I acknowledge, investigate, add notes, and resolve it
**Then** the alert state changes through the valid lifecycle
**And** every action is recorded with actor, timestamp, and notes
**And** concurrent operators cannot modify the same alert state at the same time
**And** the latest alert state and audit trail are visible to authorized users
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 5.5: Provide Basic LLM Decision Support for Alerts

As a SOC Analyst,
I want basic LLM decision support for alert analysis,
So that I can review suggested responses while remaining in control of final action.

**Acceptance Criteria:**

**Given** an alert has relevant device, telemetry, and history context
**When** I request decision support
**Then** the system invokes the configured LLM provider
**And** the response is constrained to actionable recommendations only
**And** the system refuses to autonomously execute sensitive actions without approval
**And** the LLM interaction is logged with input, output, and decision context
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

## Epic 6: Entity & Device Management

Operators can manage the company → client → devices/assets hierarchy with CRUD and audit logging across CouchDB (documents), ArcadeDB (graph/lineage), and YugabyteDB (transactional state), with change-driven business logic via KNative + Restate and unified GraphQL via Hasura.

**FRs covered:** FR-13, FR-14, FR-15, FR-16
**NFRs covered:** NFR8, NFR9, NFR10, NFR12, NFR16, NFR21, NFR25
**Additional requirements:** AD-2, AD-3, AD-4, AD-5, AD-6, AD-7, AD-8, AD-9, AD-10, AD-12, AD-13, Python 3 scripting rule, testing strategy, offline GitOps delivery.
**UX Design Requirements:** No UX Design Requirements apply to this epic.

### Story 6.1: Store Entity Hierarchy Across CouchDB, ArcadeDB, and YugabyteDB

As an Operator,
I want entities and relationships stored across the approved databases,
So that document hierarchy, graph lineage, and transactional state remain consistent with the architecture boundaries.

**Acceptance Criteria:**

**Given** an entity document is submitted for a company, client, device, or asset
**When** the system stores it in the owning data store
**Then** CouchDB stores the document hierarchy and document CRUD data
**And** ArcadeDB stores graph-structured lineage and relationship data
**And** YugabyteDB stores internal transactional state
**And** all serverless functions can read and write the required stores through the approved access patterns
**And** Ceph-backed persistent storage is used for stateful workloads
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 6.2: Provide Entity CRUD and Bulk Operations

As an Operator,
I want CRUD and bulk operations for entities,
So that device and asset management can be performed consistently and efficiently.

**Acceptance Criteria:**

**Given** the entity API is available
**When** I create, read, update, delete, or bulk-create entities
**Then** the system supports companies, clients, devices, and assets
**And** operations are enforced with role-based access control
**And** entity mutations are logged with actor, timestamp, and change diff
**And** bulk operations support up to 1000 entities per request
**And** entity create/update operations complete in under 200ms p99
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 6.3: React to Entity Change Feeds with KNative + Restate

As a Backend Developer,
I want KNative services with Restate to react to CouchDB and YugabyteDB change feeds,
So that business logic runs statefully, idempotently, and consistently when entity data changes.

**Acceptance Criteria:**

**Given** CouchDB `_changes` or YugabyteDB CDC events occur
**When** KNative services with Restate process them
**Then** the service reacts within 500ms
**And** the service reads and writes the required CouchDB and YugabyteDB state in the same workflow step
**And** change events are processed exactly once through Restate virtual object state
**And** service failure triggers automatic retry and a dead-letter queue
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 6.4: Expose Cross-Store Queries Through Hasura GraphQL

As an Operator,
I want cross-store queries through Hasura GraphQL,
So that I can view entity state, telemetry, and internal resources without joining data manually.

**Acceptance Criteria:**

**Given** CouchDB, YugabyteDB, and ClickHouse data are available
**When** I query the Hasura GraphQL endpoint at `/gql`
**Then** the system resolves a query joining CouchDB entities with YugabyteDB resources
**And** the query completes in under 2 seconds
**And** Hasura permissions follow the configured role model
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

## Epic 7: Observability & Business Reporting

Operators and business stakeholders can monitor platform health, telemetry throughput, alert statistics, network flows, and SLA/business metrics through VictoriaMetrics, Grafana, AlertManager, Cilium Hubble, vmlog, and OpenTelemetry tracing.

**FRs covered:** FR-25, FR-26, FR-27, FR-28, FR-29
**NFRs covered:** NFR4, NFR14, NFR15, NFR16, NFR18, NFR21
**Additional requirements:** AD-1, AD-2, AD-3, AD-4, AD-7, AD-8, AD-9, AD-10, AD-12, AD-13, Python 3 scripting rule, testing strategy, offline GitOps delivery.
**UX Design Requirements:** UX-DR1 applies to tool UI exposure through Envoy Gateway with native tool auth.

### Story 7.1: Deploy VictoriaMetrics Metrics Cluster

As a Platform Engineer,
I want a VictoriaMetrics cluster for platform metrics,
So that metrics can be scraped, queried, and retained at platform scale.

**Acceptance Criteria:**

**Given** the platform has a local dev cluster or production topology available
**When** I apply the VictoriaMetrics cluster configuration
**Then** vmstorage, vminsert, and vmselect are deployed with configurable replica counts
**And** vmagent scrapes metrics from all platform components
**And** PromQL queries return 24h range results in under 2 seconds
**And** retention policies are applied per environment
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 7.2: Collect Logs with vmlog

As a Platform Engineer,
I want vmlog to collect stdout and stderr from all pods,
So that operators can search logs by namespace, pod, and content.

**Acceptance Criteria:**

**Given** platform pods emit structured JSON logs to stdout
**When** vmlog indexes those logs
**Then** logs are searchable by namespace, pod, and content within 5 seconds
**And** log retention is applied per environment
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 7.3: Export Distributed Traces with OpenTelemetry Collector

As a Platform Engineer,
I want OpenTelemetry Collector to receive and export traces,
So that service behavior can be traced across the platform.

**Acceptance Criteria:**

**Given** instrumented services emit OTLP traces
**When** the OpenTelemetry Collector receives them
**Then** traces are exported to the configured backend, VictoriaMetrics or Jaeger
**And** sampling is configurable per service
**And** trace data is visible in the observability stack
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 7.4: Configure Grafana Dashboards and AlertManager

As a Business Stakeholder,
I want dashboards and alert routing for platform performance and SLA metrics,
So that I can monitor throughput, device coverage, SLA compliance, and cost per cluster.

**Acceptance Criteria:**

**Given** VictoriaMetrics and AlertManager are deployed
**When** I open Grafana
**Then** I see dashboards for platform health, telemetry throughput, and alert statistics
**And** business dashboards show alert throughput, device coverage, SLA compliance, and cost per cluster
**And** AlertManager routes alerts to configured channels
**And** stale metrics older than 5 minutes show a warning banner
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 7.5: Expose Grafana and Hubble Tool UIs via Envoy Gateway

As a Platform Administrator,
I want Grafana and Hubble UIs exposed through Envoy Gateway routes with native tool auth,
So that observability users have a consistent ingress entry point without redundant platform auth.

**Acceptance Criteria:**

**Given** Envoy Gateway from Epic 3 is installed
**And** TLS termination from Epic 3 is configured
**And** Grafana and Hubble from this epic are installed
**When** I apply the tool UI route manifest from GitOps
**Then** `grafana.hpdc.local` and `hubble.hpdc.local` routes are exposed through Envoy Gateway
**And** each tool’s native auth handles access
**And** Casdoor/Casbin ext_authz is not enforced on tool UI routes
**And** TLS termination is active
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

## Epic 8: Multi-Region Federation (v2 - deferred)

Cross-region visibility with data sovereignty: Cilium ClusterMesh over WireGuard VPN, independent regional data stores with no cross-region replication, and a central hub querying regional APIs with region-scoped auth.

**FRs covered:** FR-33, FR-34, FR-35
**NFRs covered:** NFR12, NFR18, NFR20, NFR21
**Additional requirements:** AD-1, AD-2, AD-4, AD-7, AD-8, AD-9, AD-10, AD-11, AD-12, AD-13, Python 3 scripting rule, testing strategy, offline GitOps delivery.
**UX Design Requirements:** No UX Design Requirements apply to this epic.

### Story 8.1: Establish Cross-Cluster Service Discovery with ClusterMesh

As a Platform Engineer,
I want ClusterMesh to connect regional clusters over WireGuard VPN,
So that services can discover each other across regions without manual configuration.

**Acceptance Criteria:**

**Given** two regional clusters are provisioned
**When** ClusterMesh is configured over WireGuard VPN
**Then** services are discovered across clusters
**And** cross-cluster traffic is encrypted through the VPN tunnel
**And** no manual per-service discovery configuration is required
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 8.2: Enforce Regional Data Sovereignty

As a Platform Engineer,
I want independent regional data stores with no automatic cross-region replication,
So that regional data remains local unless explicitly configured otherwise.

**Acceptance Criteria:**

**Given** each region has its own CouchDB, YugabyteDB, ClickHouse, ArcadeDB, KeyDB, and PostgreSQL
**When** regional queries are routed
**Then** each query goes to the region-scoped data store
**And** cross-region replication does not happen by default
**And** explicit replication configuration is required before cross-region data movement
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 8.3: Query Regional APIs for Cross-Region Visibility

As a Business Stakeholder,
I want a central hub that can query regional APIs for aggregate visibility,
So that I can see platform metrics across regions without storing regional data at the hub.

**Acceptance Criteria:**

**Given** regional APIs are available with region-scoped authentication
**When** the central hub queries them
**Then** it displays aggregated metrics across regions
**And** it supports per-region drill-down for entity and alert state
**And** the hub does not store regional data
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

## Epic 9: AI Agent Engine (v2 - deferred)

Full AI agent orchestration: MCP tool invocation and A2A inter-agent communication with the platform's capabilities.

**FRs covered:** FR-47, FR-48, FR-46 (full)
**NFRs covered:** NFR12, NFR21, NFR25
**Additional requirements:** AD-2, AD-3, AD-4, AD-6, AD-8, AD-9, AD-10, AD-12, AD-13, Python 3 scripting rule, testing strategy, offline GitOps delivery.
**UX Design Requirements:** No UX Design Requirements apply to this epic.

### Story 9.1: Expose Platform Capabilities as MCP Tools

As an AI Agent,
I want platform capabilities exposed as MCP-compatible tools,
So that agents can query databases, call APIs, and trigger workflows through a consistent interface.

**Acceptance Criteria:**

**Given** the platform exposes MCP-compatible tool definitions
**When** an agent invokes a tool
**Then** the invocation is validated against security policies
**And** the tool call is logged with agent ID, tool name, parameters, and result
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 9.2: Enable Agent-to-Agent Communication

As an AI Agent,
I want authenticated agent-to-agent messaging,
So that coordinated decision-making and task delegation can happen without unauthorized impersonation.

**Acceptance Criteria:**

**Given** agents are registered with the platform
**When** one agent sends a message to another
**Then** the message is routed through an authenticated channel
**And** unauthorized impersonation is prevented
**And** agent registration and discovery work as configured
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 9.3: Provide Full LLM Decision-Support Engine — DEFERRED / NOT-IMPLEMENTED

**Status:** deferred — not implemented. See Epic 9 header (`v2 - deferred`). Sprint tracker intentionally omits 9-3; only 9-1 and 9-2 were delivered.

**Deferred requirements note (action item #15):** When implemented, 9-3 inherits the safety-gate pattern from 5-3/5-5 — sensitive actions require explicit human approval (no autonomous execution), and ambiguous or low-confidence recommendations are escalated for manual review instead of executed. Both gates are stated requirements, not optional.

As a Platform Administrator,
I want a full LLM decision-support engine with per-use-case model selection,
So that operators receive actionable recommendations across alerts, entities, and workflows with complete auditability.

**Acceptance Criteria:**

**Given** LLM provider endpoints are configured per use case
**When** I request decision support for a platform decision
**Then** the engine selects the model appropriate to the use case (alert analysis, entity guidance, workflow optimization)
**And** the response is constrained to actionable recommendations only
**And** the engine refuses to autonomously execute sensitive actions without approval
**And** ambiguous or low-confidence suggestions are escalated for manual review instead of executed
**And** every LLM interaction is logged with input, output, decision context, and model used
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

## Epic 11: Dev Cluster Bring-Up & Verification

Platform Engineer can provision, tear down, and recreate the HPDC dev cluster with idempotent persistent storage, run the full 44-step component initialization against a live Talos/QEMU cluster, and verify all live-cluster acceptance criteria (REG-01..10).

**FRs covered:** FR-1..48 (all platform FRs verified live)
**NFRs covered:** NFR1..26 (all platform NFRs verified live)
**Additional requirements:** Idempotent dev cluster lifecycle, persistent Ceph/Rook storage across recreate cycles, Talos/QEMU teardown capability.
**UX Design Requirements:** No UX Design Requirements apply to this epic.

### Story 11.1: Dev Cluster VM Provisioning Lifecycle

As a Platform Engineer,
I want the dev cluster startup to detect and shut down any existing running cluster before provisioning,
So that each dev session starts clean without resource conflicts.

**Acceptance Criteria:**

**Given** a dev cluster is already running (Talos/QEMU VMs or kind cluster)
**When** `startup.dev.py --offline --apply` is invoked
**Then** the existing cluster is detected and gracefully shut down
**And** QEMU processes and network resources are released
**And** persistent QEMU disk images are preserved for idempotent recreation
**And** the script exits with a non-zero status on failure to shut down

**Given** no dev cluster is running
**When** `startup.dev.py --offline --apply` is invoked
**Then** the cluster is provisioned from scratch
**And** the script exits with a non-zero status on failure to provision

**Implementation notes:** Requires extending `stop.dev.py` (currently kind-only) to handle Talos/QEMU teardown. The `bootstrap_talos_dev.py` already calls `talosctl cluster create qemu` — the teardown must reverse this. Persistent disk images (`output/qemu/talos-v*.img`) must survive the cycle.

### Story 11.2: Idempotent Startup with Persistent Storage

As a Platform Engineer,
I want the dev cluster to be recreatable with idempotent persistent storage,
So that Ceph/Rook data survives cluster recreation cycles.

**Acceptance Criteria:**

**Given** a dev cluster with Rook-Ceph storage and deployed workloads
**When** the cluster is shut down and recreated via `startup.dev.py`
**Then** the persistent QEMU disk images are preserved
**And** Rook-Ceph storage is reinitialized from the preserved disks
**And** previously deployed workloads can access their persistent data
**And** the recreation completes without manual intervention

**Given** the persistent disk images are corrupted or missing
**When** the cluster is recreated
**Then** fresh disks are created and Rook-Ceph initializes from scratch
**And** the script logs the fresh initialization

**Implementation notes:** `bootstrap_talos_dev.py:create_disk_image` already skips existing disks. The idempotency is: stop -> preserve disks -> recreate VMs -> Rook-Ceph reattaches. Requires Rook-Ceph operator to handle disk reattachment gracefully.

### Story 11.3: Live Component Initialization

As a Platform Engineer,
I want the full 44-step component initialization to run against a live cluster,
So that all platform components are verified working end-to-end.

**Acceptance Criteria:**

**Given** a freshly provisioned Talos/QEMU cluster
**When** `startup.dev.py --offline --apply` runs all 44 steps
**Then** each step completes successfully or fails with a clear error
**And** the `output/startup.dev.log` records the outcome of every step
**And** the script exits with a non-zero status on any step failure
**And** the cluster is accessible via `kubectl` after all steps complete

**Given** a step fails during initialization
**When** the failure is investigated and fixed
**Then** the step can be re-run individually via `--step` flag
**And** the remaining steps continue from where they left off

**Implementation notes:** The 44 steps in `scripts/steps/` are already ordered. The `--apply` flag passes `--apply` to each step. The investigation/fix loop uses the `investigate` discipline per failure. Each step should be run individually after a fix to confirm the fix works before re-running the full chain.

### Story 11.4: Live-Cluster Verification

As a Quality Engineer,
I want the P0 ATDD suite and live-cluster register entries verified against the live cluster,
So that all quantified acceptance criteria are proven working.

**Acceptance Criteria:**

**Given** the dev cluster is fully initialized (all 44 steps complete)
**When** the P0 ATDD suite runs with `HPDC_EDGE_URL` and `HPDC_EVENTS_API_KEY` set
**Then** the 7 previously-skipped RED-phase tests pass or fail with clear diagnostics
**And** REG-01 through REG-10 are verified and closed in `live-cluster-verification-register.md`
**And** `deferred-work.md` entries resolved by live verification are marked resolved
**And** `sprint-status.yaml` is updated to reflect the new epic and closed action items

**Given** a REG entry fails verification
**When** the failure is investigated and fixed
**Then** the entry is re-verified and closed
**And** the fix is committed with a reference to the REG entry

**Implementation notes:** The P0 ATDD suite (143 passed, 7 skipped) runs with pytest. The 7 skips are RED-phase live journeys gated on B-001. Harnesses auto-switch to live backends via `HPDC_*` env vars. REG-01..10 entries are in `live-cluster-verification-register.md`. Each entry has owner (Winston/Amelia/Murat), quantified ACs, and P0 class.

## Epic 10: Production Hardening

Close the verified hardening gaps surfaced by the P0 ATDD acceptance audits: full per-route security-policy coverage, malformed GitOps YAML, and overlay drift — keeping validation offline/GitOps-safe.

**FRs covered:** FR-37, FR-38, FR-40, FR-44, FR-45
**NFRs covered:** NFR17, NFR18, NFR21
**Additional requirements:** Python 3 scripting rule, testing strategy, offline GitOps delivery.
**UX Design Requirements:** No UX Design Requirements apply to this epic.

### Story 10.1: Harden Edge Gateway Security Coverage and Fix GitOps Drift

As a Platform Engineer,
I want every edge route covered by an explicit security policy and the GitOps tree free of malformed YAML and overlay drift,
So that the P0 route-audit and secret-scan acceptance contracts hold and no route bypasses authentication.

**Acceptance Criteria:**

**Given** the edge gateway routes declared in GitOps
**When** the P0 route-table audit runs
**Then** every `hpdc-edge` attached route has a SecurityPolicy whose targetRef resolves to it
**And** the `hpdc-graphql-gateway` and `hpdc-telemetry-http-ingestion` routes are covered
**And** the `envoy-ui-routes.yaml` overlay reference matches the base it extends
**And** the harbor base manifest parses as valid YAML
**And** the process completes without internet access
**And** the script exits with a non-zero status on failure

### Story 10.2: Harden Route-Policy Live Config, GitOps Build Validity, Secret Isolation, and Test-Suite Robustness

As a Platform Engineer,
I want the route-policy set to be live (no shadowed SecurityPolicies, in-tree JWKS host), the GitOps tree to actually build, secret stores to enforce key-level isolation, and the P0 suite to catch regressions it currently misses,
So that production onboarding does not silently deploy dead auth config or a non-building GitOps tree, and R-009/R-008/R-001 contracts hold.

**Acceptance Criteria:**

**Given** the `hpdc-edge-domain-routes` HTTPRoute and the SecurityPolicy set
**When** the route-table audit runs with path-level awareness
**Then** `/data`, `/api`, and `/events` carry path-level apiKeyAuth on `hpdc-edge-domain-routes`, and the duplicated `/gql` and `/telemetry` matches are removed from that route (owned by `hpdc-graphql-gateway` and `hpdc-telemetry-http-ingestion`)
**And** no SecurityPolicy targets a route whose traffic is shadowed by an identical PathPrefix + wildcard hostname route
**And** the JWKS host `casdoor.hpdc.local` resolves in-tree via an HTTPRoute
**And** every overlay builds with `kustomize build --load-restrictor=LoadRestrictionsNone`
**And** `events-key` authenticates only `/events` and `telemetry-key` only `/telemetry` (R-009)
**And** the prod-named InfisicalSecret does not embed the dev `envSlug`
**And** the P0 suite adds a structural GitOps build-validity check, duplicate-key YAML detection, and strict `main()` tuple guards
**And** all existing P0 checks stay GREEN with validation remaining offline/GitOps-safe

## Epic 12: DRY Principle Investigation & Refactoring

Audit the codebase for duplicated logic, hardcoded values, and inconsistent patterns; refactor to DRY (Don't Repeat Yourself) with centralized configuration.

**FRs covered:** N/A (cross-cutting concern)
**NFRs covered:** N/A (code quality)
**Additional requirements:** Environment-based configuration via `.env`, centralized constants, eliminate magic numbers/strings.
**UX Design Requirements:** No UX Design Requirements apply to this epic.

### Story 12.1: Environment Configuration Audit & Consolidation

As a Platform Engineer,
I want all hardcoded values (IPs, ports, domains, cluster names) centralized in `.env` with a single source of truth,
So that configuration changes propagate everywhere without manual updates.

**Acceptance Criteria:**

**Given** the codebase has hardcoded IPs, ports, and domains
**When** the audit runs
**Then** every hardcoded value is identified and cataloged
**And** a migration plan to `.env` is documented
**And** no script contains hardcoded values that should be configurable

**Given** `.env` is the source of truth
**When** a value changes in `.env`
**Then** all scripts and configurations reflect the change
**And** `.env.example` documents every variable with descriptions

### Story 12.2: Script DRY Refactoring

As a Platform Engineer,
I want shared utility functions extracted into reusable modules (e.g., `utils/`, `common/`),
So that scripts don't duplicate logic for kubectl operations, helm installs, or status checks.

**Acceptance Criteria:**

**Given** multiple scripts contain similar kubectl/helm commands
**When** the refactoring runs
**Then** common operations are extracted to shared modules
**And** all scripts import from shared modules
**And** no script duplicates logic that exists in shared modules

**Given** scripts use `run()` function for subprocess calls
**When** the function is extended
**Then** it supports `.env` loading, logging, and error handling centrally
**And** all scripts use the centralized `run()` function

### Story 12.3: Documentation & Enforcement

As a Platform Engineer,
I want DRY principles documented and enforced via code review,
So that new code doesn't reintroduce duplication.

**Acceptance Criteria:**

**Given** the DRY principle is established
**When** a developer adds new code
**Then** the code review checklist includes DRY validation
**And** the README documents the DRY principle as mandatory
**And** `.env.example` is kept in sync with all configurable values
