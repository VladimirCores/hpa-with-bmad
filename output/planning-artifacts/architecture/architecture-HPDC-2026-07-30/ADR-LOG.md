# ADR Decision Log — HPDC

*Generated from architecture session memlog. Each ADR corresponds to an AD-n in ARCHITECTURE-SPINE.md.*

| ADR | Title | Status | Binds |
|-----|-------|--------|-------|
| AD-1 | Envoy Gateway as exclusive ingress boundary | Adopted | FR-36, FR-37, FR-38 |
| AD-2 | Domain-per-route segregation | Adopted | FR-1, FR-5, FR-9, FR-13, FR-16, FR-36 |
| AD-3 | Serverless-first compute | Adopted | FR-5, FR-6, FR-11, FR-15, FR-17 |
| AD-4 | Event-mesh as the integration fabric | Adopted | FR-1, FR-2, FR-3, FR-4, FR-9 |
| AD-5 | Protobuf normalized envelope | Adopted | FR-2 |
| AD-6 | Database ownership boundaries | Adopted | FR-13, FR-14 |
| AD-7 | Ceph for all persistent state | Adopted | FR-24 |
| AD-8 | mTLS for all inter-service communication | Adopted | FR-45 |
| AD-9 | GitOps-only delivery | Adopted | FR-17..FR-21 |
| AD-10 | Air-gapped delivery | Adopted | FR-30, FR-31, FR-32 |
| AD-11 | Multi-region data sovereignty | Adopted | FR-33, FR-34, FR-35 |
| AD-12 | Observability | Adopted | FR-25..FR-29 |
| AD-13 | Centralized secrets management | Adopted | FR-44 |

### Decision Details

#### AD-1: Envoy Gateway as exclusive ingress boundary
- **Context**: All external traffic must be authenticated, authorized, and routed through a single control point.
- **Decision**: Every external route declared as a K8s Gateway API resource on Envoy Gateway. No backend service exposes an external port without a matching gateway route. TLS termination at EG via cert-manager.
- **Alternatives considered**: Direct Service exposure (rejected: no centralized auth), Istio Ingress (rejected: less mature Gateway API support).
- **Source**: PRD FR-36, FR-37, FR-38.

#### AD-2: Domain-per-route segregation
- **Context**: Different access patterns (document CRUD, serverless workflows, stream ingestion, event pub-sub, graphql) need different runtime characteristics.
- **Decision**: Routes are hard domain boundaries. `/data/*` → CouchDB native, `/api/*` → KNative+Restate, `/gql` → Hasura, `/telemetry/*` → Pulsar native, `/events/*` → Kafka+SpinKube. Inter-domain communication through event-mesh only. Intra-domain function-to-function HTTP allowed (mTLS mesh).
- **Alternatives considered**: Single backend serving all routes (rejected: coupling scaling of different patterns).
- **Source**: PRD FR-1, FR-5, FR-9, FR-13, FR-16, FR-36.

#### AD-3: Serverless-first compute
- **Context**: IoT workloads have variable load patterns; always-on services waste resources during low-activity periods.
- **Decision**: All compute via KNative (scale-to-zero + Restate SAGAs), SpinKube WASM (stateless transforms), or Pulsar Functions (stream processing). No Deployment/StatefulSet for application logic.
- **Alternatives considered**: Always-on microservices (rejected: resource waste), AWS Lambda (rejected: not self-hosted, air-gapped).
- **Source**: PRD FR-5, FR-6, FR-11, FR-15, FR-17.

#### AD-4: Event-mesh as integration fabric
- **Context**: Five route domains plus database change feeds need a decoupled integration mechanism.
- **Decision**: Pulsar primary (telemetry ingestion, 100K+ RPS), Kafka secondary (alert events, Spin WASM). Database CDCs (CouchDB _changes, YugabyteDB CDC) → KNative Eventing. Argo Events bridges Git/image/Kafka events.
- **Alternatives considered**: Single Pulsar cluster for everything (rejected: Kafka's consumer-group model better for Spin WASM transforms), gRPC point-to-point (rejected: coupling).
- **Source**: PRD FR-1, FR-2, FR-3, FR-4, FR-9.

#### AD-5: Protobuf normalized envelope
- **Context**: Multiple message producers and consumers across different languages (Go, Rust, Java, Python) need a shared wire format.
- **Decision**: All messaging uses Protobuf with CommonEnvelope (device_id, device_type, event_type, timestamp, payload, region_id, origin, idempotency_key). Schema Registry enforces compatibility. Max envelope 64KB.
- **Alternatives considered**: JSON (rejected: schema enforcement), Avro (rejected: less IDE tooling support).
- **Source**: PRD FR-2.

#### AD-6: Database ownership boundaries
- **Context**: Six databases with different data models (document, relational, graph, time-series, cache, auth). Authorship authority must be clear.
- **Decision**: Ownership per database type prevents data duplication, not access restriction. All serverless functions R/W all databases — MVP simplicity. Document shape conventions enforced via code review.
- **Alternatives considered**: Per-function scoped credentials (deferred: MVP simplicity preferred), per-function DB partitions (deferred).
- **Source**: PRD FR-13, FR-14.

#### AD-7: Ceph for all persistent state
- **Context**: Stateful workloads need durable, scalable storage in an air-gapped bare-metal environment.
- **Decision**: Ceph RBD PVCs for all stateful workloads: databases, message brokers, cache. No hostPath, emptyDir, or local volumes.
- **Alternatives considered**: Local SSD (rejected: data loss on node failure), NFS (rejected: performance).
- **Source**: PRD FR-24.

#### AD-8: mTLS for all inter-service communication
- **Context**: Air-gapped cluster needs intra-cluster encryption without external CA dependency.
- **Decision**: Cilium-managed mTLS via SPIFFE/SPIRE with auto-rotation. EG handles external TLS; internal is mTLS between sidecars.
- **Alternatives considered**: Istio mTLS (rejected: Cilium already provides CNI), Linkerd (rejected: extra mesh layer).
- **Source**: PRD FR-45.

#### AD-9: GitOps-only delivery
- **Context**: Air-gapped deployment requires auditable, repeatable promotion across environments.
- **Decision**: Monorepo with Kustomize overlays (base/dev/prod). Kargo Freight promotion → Argo CD ApplicationSet sync. Direct kubectl forbidden.
- **Alternatives considered**: Helm-only (rejected: Kustomize better for environment overlays), Flux (rejected: less mature promotion model).
- **Source**: PRD FR-17..FR-21.

#### AD-10: Air-gapped delivery
- **Context**: Production deployment has no internet access. Must handle images, charts, and git data locally.
- **Decision**: Harbor (local OCI registry, Trivy scan, Cosign sign). Spegel (P2P image distribution). Local Git mirrors. All delivery GitOps-mediated.
- **Alternatives considered**: Static artifact bundle (rejected: no GitOps), single Harbor proxy (rejected: Spegel P2P reduces bandwidth).
- **Source**: PRD FR-30, FR-31, FR-32.

#### AD-11: Multi-region data sovereignty
- **Context**: IoT data may span compliance zones. Each region owns its data independently.
- **Decision**: Independent DB instances per region. No automatic cross-region replication. Cilium ClusterMesh over WireGuard VPN for cross-region service discovery. Central hub queries regional APIs.
- **Alternatives considered**: Global YugabyteDB cluster (rejected: automatically replicates data across regions), Cross-region CouchDB replication (rejected: violates compliance).
- **Source**: PRD FR-33, FR-34, FR-35.

#### AD-12: Observability
- **Context**: 25+ components, serverless functions, and event pipelines need unified observability without external SaaS dependency.
- **Decision**: Structured JSON logs to stdout. OpenTelemetry SDK auto-instrumentation for all KNative functions. VictoriaMetrics cluster (vmstorage/vminsert/vmselect). Hubble for network observability. Retention: 7d raw, 30d aggregated (1h rollup), 1y monthly.
- **Alternatives considered**: Prometheus standalone (rejected: retention limits), Grafana Cloud (rejected: air-gapped), ELK (rejected: resource overhead).
- **Source**: PRD FR-25..FR-29. Added via reviewer gate.

#### AD-13: Centralized secrets management
- **Context**: 20+ components, databases, and external integrations each need credentials. Must work air-gapped.
- **Decision**: All secrets in Infisical; never in git or ConfigMaps. Infisical K8s Operator CSI Driver injects secrets as volumes. Auto-rotation 90 days. Per-function service accounts.
- **Alternatives considered**: K8s-native Secrets only (rejected: no rotation, no audit), HashiCorp Vault (rejected: more complex, less K8s-native).
- **Source**: PRD FR-44. Added via reviewer gate.
