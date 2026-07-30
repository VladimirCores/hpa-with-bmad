# Work-Split View — HPDC

*Architecture-level breakdown of work across teams/epics. Each slice is independently buildable; ADs ensure consistency.*

## Slices Overview

| Slice | Epics | ADs | Functions | Primary Tech | Estimated Complexity |
|-------|-------|-----|-----------|-------------|---------------------|
| **Substrate** | Cluster OS + CNI + Storage | AD-7, AD-8 | Talos bootstrap, Cilium, Rook-Ceph | Talos, Cilium, Ceph | High (infra) |
| **GitOps** | Kargo + Argo CD + Harbor | AD-9, AD-10 | Pipeline setup, image registry | Kargo, Argo CD, Kustomize | Medium (tooling) |
| **Messaging** | Pulsar + Kafka | AD-4, AD-5 | Cluster setup, topics, schema registry | Pulsar, Kafka, Strimzi | Medium (infra) |
| **Database** | CouchDB + YugabyteDB + ArcadeDB + ClickHouse + KeyDB + PostgreSQL | AD-6, AD-7 | Cluster setup, CDC feeds | Various DBs | Medium (infra) |
| **Gateway** | Envoy Gateway + Casdoor + Casbin | AD-1, AD-2 | Routes, SecurityPolicies, auth flows | Envoy Gateway, Casdoor, Casbin | Medium (config + dev) |
| **Observability** | VictoriaMetrics + Grafana + OpenTelemetry | AD-12 | Metrics, traces, logs, dashboards | VictoriaMetrics, OTel, Grafana | Low (config) |
| **Secrets** | Infisical | AD-13 | Operator install, CSI Driver, secret onboarding | Infisical | Low (config) |
| **Telemetry Pipeline** | Pulsar Functions + ClickHouse sink | AD-2, AD-3, AD-4, AD-5 | Telemetry aggregator, JDBC sink | Java/Pulsar Functions | Medium (dev) |
| **Alert Engine** | KNative + Restate + Kafka + SpinKube | AD-2, AD-3, AD-4 | Alert ingestion, state machine, notifications | Go/KNative, Restate | High (dev) |
| **Entity Management** | CouchDB CRUD + Hasura GraphQL | AD-2, AD-6 | Entity CRUD APIs, GQL federation | CouchDB, Hasura | Medium (dev) |
| **Auth Integration** | Go gRPC ext_authz + policy models | AD-1, AD-2 | RBAC/ReBAC/ABAC models, gRPC service | Go/Casbin | Medium (dev) |
| **Deployment & Testing** | CI pipeline, test harnesses | Testing § | Kustomize dry-run, integration tests, e2e | Playwright, Go test | Low (test) |
| **Frontend** | SPA (deferred to v2) | — | Backstage as placeholder MVP | Backstage (MVP only) | Low (config) |

## Execution Order (Recommended)

### Wave 1 — Foundation (builds in parallel)
```
Substrate ──────────▶ Cluster running, Ceph available
GitOps    ──────────▶ Git → Kargo → Argo CD pipeline working
Messaging ──────────▶ Pulsar + Kafka clusters with topics
Database  ──────────▶ All 6 databases running, CDC feeds enabled
Gateway   ──────────▶ Envoy Gateway routes defined, Casdoor+Casbin wired
Observability ──────▶ VictoriaMetrics ingesting, Grafana dashboards
Secrets   ──────────▶ Infisical injecting secrets into pods
```

### Wave 2 — Serverless Functions (sequential, each builds on wave 1)
```
Telemetry Pipeline ──▶ IoT → EG(/telemetry) → Pulsar → Functions → ClickHouse
Auth Integration   ──▶ Casbin gRPC → SecurityPolicy → all routes
Alert Engine       ──▶ Kafka → SpinKube → KNative+Restate → CouchDB+KeyDB
Entity Management  ──▶ CouchDB → Hasura → GQL
```

### Wave 3 — Polish
```
Deployment & Testing ──▶ CI pipeline, integration tests, e2e suite
Frontend (v2)       ──▶ SPA on CDN
```

## Team Assignments (Suggested)

| Team | Owns |
|------|------|
| **Platform Team** | Substrate, GitOps, Messaging, Database (infra), Gateway, Observability, Secrets |
| **Backend Team** | Telemetry Pipeline, Alert Engine, Entity Management, Auth Integration |
| **QA/DevOps** | Deployment & Testing, CI pipeline |
| **Frontend Team** (v2) | SPA on CDN |

## Dependency Graph

```
Substrate ◄── GitOps ◄───┬── Gateway ◄─── Auth Integration
                         ├── Messaging ◄── Telemetry Pipeline
                         ├── Messaging ◄── Alert Engine
                         ├── Database  ◄── Entity Management
                         ├── Database  ◄── Telemetry Pipeline (ClickHouse)
                         ├── Database  ◄── Alert Engine (CouchDB, KeyDB)
                         └── Secrets   ◄── ALL (Infisical CSI)
```
