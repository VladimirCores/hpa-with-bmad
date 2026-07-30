# C4 Model — HPDC

## Level 1: System Context

```mermaid
C4Context
  title System Context — HPDC Platform

  Person(admin, "Platform Admin", "Manages clusters, GitOps pipelines, secrets, observability")
  Person(dev, "Developer", "Deploys functions via GitOps, monitors Backstage")
  Person(user, "End User", "IoT device operator or API consumer")
  System(iotDevice, "IoT Device", "Sends telemetry via MQTT/gRPC")

  Boundary(hpdc, "HPDC Platform") {
    System(eg, "Envoy Gateway", "API Gateway, ingress controller, ext_authz")
    System(backend, "Serverless Backend", "KNative + SpinKube + Pulsar Functions")
    System(infra, "Platform Infra", "Databases, message brokers, observability")
  }

  System(git, "Git Repositories", "Monorepo with Kustomize overlays")
  System(cdn, "CDN", "Serves SPA frontend")
  System(externalApi, "External APIs", "Alert sources, webhook integrations")

  Rel(admin, git, "Pushes config & code", "HTTPS/Git")
  Rel(admin, infra, "Operates", "kubectl + Argo CD")
  Rel(dev, git, "Pushes functions & config", "HTTPS/Git")
  Rel(dev, backend, "Monitors deployments", "Backstage")
  Rel(user, eg, "API requests", "HTTPS")
  Rel(user, cdn, "Loads SPA", "HTTPS")
  Rel(iotDevice, eg, "Telemetry data", "MQTT/gRPC")
  Rel(externalApi, eg, "Events & webhooks", "HTTPS")
  Rel(git, infra, "GitOps sync", "Kargo + Argo CD")
  Rel(eg, backend, "Routes requests", "mTLS")
  Rel(backend, infra, "Reads/Writes data", "mTLS")
```

## Level 2: Container Diagram

```mermaid
C4Container
  title Container Diagram — HPDC Platform

  Person(user, "End User / IoT Device", "API consumer")

  System_Boundary(gateway, "Gateway Layer") {
    Container(eg, "Envoy Gateway", "K8s Gateway API", "Ingress, TLS termination, rate limiting, ext_authz")
    Container(casdoor, "Casdoor", "Go", "AuthN: JWT issuance, SSO, OIDC, API-Key validation")
    Container(casbin, "Casbin ext_authz", "Go gRPC", "AuthZ: RBAC + ReBAC + ABAC, DENY-wins")
  }

  System_Boundary(compute, "Compute Layer") {
    Container(knative, "KNative Serving + Eventing", "Go/Python", "Serverless scale-to-zero, Restate SAGAs")
    Container(spinkube, "SpinKube WASM", "Rust/JS/Go", "WASM transforms on Kafka topics")
    Container(pulsarFn, "Pulsar Functions", "Java", "Stream aggregation, JDBC Sink to ClickHouse")
    Container(argo, "Argo Workflows", "", "CI/build/deploy DAGs")
  }

  System_Boundary(messaging, "Messaging Layer") {
    Container(pulsar, "Apache Pulsar", "4.2.3", "Primary message backbone, MQTT/gRPC, 100K+ RPS")
    Container(kafka, "Apache Kafka", "latest", "Secondary event streams, Spin WASM input")
  }

  System_Boundary(data, "Data Layer") {
    ContainerDb(couchdb, "CouchDB", "3.5.2", "Document DB, CRM/ERP docs, entity hierarchy, _changes feed")
    ContainerDb(yugabyte, "YugabyteDB", "2026.1.0.1", "Distributed SQL, transactional state, CDC")
    ContainerDb(arcadedb, "ArcadeDB", "26.7.3", "Multi-model graph, entity lineage")
    ContainerDb(clickhouse, "ClickHouse", "26.7.1", "Time-series telemetry analytics")
    ContainerDb(keydb, "KeyDB", "latest", "Clustered cache, pub-sub, alert state, dedup set")
    ContainerDb(postgres, "PostgreSQL", "", "Casdoor + Casbin auth data only")
  }

  System_Boundary(ops, "Operations") {
    Container(vm, "VictoriaMetrics", "1.148.0", "Metrics storage, cluster mode")
    Container(grafana, "Grafana", "", "Dashboards, alerting")
    Container(hubble, "Cilium Hubble", "", "Network observability")
    Container(infisical, "Infisical", "", "Secrets management, CSI Driver injection")
  }

  System_Boundary(gitops, "GitOps Layer") {
    Container(kargo, "Kargo", "1.11.0", "Freight-based multi-stage promotion")
    Container(argocd, "Argo CD", "", "Application sync, Sync Waves")
  }

  Rel(user, eg, "HTTPS/MQTT/gRPC")
  Rel(eg, casdoor, "JWT validation")
  Rel(eg, casbin, "ext_authz gRPC")
  Rel(eg, knative, "Route /api/*")
  Rel(eg, pulsar, "Route /telemetry/*")
  Rel(eg, kafka, "Route /events/*")
  Rel(eg, couchdb, "Route /data/*")
  Rel(eg, pulsar, "Route /gql → Hasura")

  Rel(knative, pulsar, "Publish/subscribe", "Protobuf CommonEnvelope")
  Rel(knative, kafka, "Publish/subscribe", "Protobuf CommonEnvelope")
  Rel(knative, keydb, "Stateful operations")
  Rel(knative, couchdb, "Document CRUD")
  Rel(knative, yugabyte, "Transactional state")

  Rel(spinkube, kafka, "Consume/transform")
  Rel(spinkube, clickhouse, "Write analytics")

  Rel(pulsarFn, pulsar, "Stream processing")
  Rel(pulsarFn, clickhouse, "JDBC Sink")

  Rel(kargo, argocd, "Promotes freight")
  Rel(git, kargo, "Git push → Freight")
  Rel(argocd, knative, "Syncs manifests")
  Rel(argocd, spinkube, "Syncs manifests")
  Rel(argocd, pulsarFn, "Syncs manifests")
```

## Level 3: Component — Telemetry Pipeline

```mermaid
C4Component
  title Telemetry Ingestion Pipeline — /telemetry route

  Person(iot, "IoT Device", "MQTT/gRPC publisher")

  Container_Boundary(egress, "Envoy Gateway") {
    Component(egRoute, "HTTPRoute /telemetry", "Gateway API", "Routes to Pulsar MoP/gRPC handler")
    Component(egAuth, "SecurityPolicy", "ext_authz", "API-Key validation via Casbin")
  }

  Container_Boundary(pulsar, "Pulsar Cluster") {
    Component(mop, "MoP Protocol Handler", "Pulsar Proxy", "MQTT → Pulsar topic translation")
    Component(grpcHandler, "gRPC Protocol Handler", "Pulsar Proxy", "gRPC → Pulsar topic")
    Component(topic, "Persistent Topic", "Pulsar", "Per device_type + region_id partitioning")
  }

  Container_Boundary(fn, "Pulsar Functions") {
    Component(agg, "Telemetry Aggregator", "Java", "Windowed aggregation, schema validation")
    Component(sink, "JDBC ClickHouse Sink", "Java", "Batch writes to ClickHouse MergeTree")
  }

  ContainerDb(ch, "ClickHouse", "26.7.1", "Time-series telemetry")

  Rel(iot, egRoute, "MQTT/gRPC")
  Rel(egRoute, egAuth, "API-Key check")
  Rel(egAuth, mop, "Forward", "MQTT")
  Rel(egAuth, grpcHandler, "Forward", "gRPC")
  Rel(mop, topic, "Publish")
  Rel(grpcHandler, topic, "Publish")
  Rel(topic, agg, "Trigger")
  Rel(agg, sink, "Forward")
  Rel(sink, ch, "JDBC batch write")
```

## Level 3: Component — Alert State Machine

```mermaid
C4Component
  title Alert Management — /events + /api routes

  Container_Boundary(knative, "KNative + Restate") {
    Component(alertIngest, "Alert Ingestion", "Go", "Receives alerts from Kafka, creates state machine")
    Component(alertSM, "Alert State Machine", "Restate", "SAGA: initial → ack → resolve → close")
    Component(alertNotif, "Alert Notification", "Go", "Pushes notifications via Pulsar")
  }

  Container_Boundary(kafka, "Kafka Cluster") {
    Component(alertTopic, "alert-events Topic", "Kafka", "External alert events")
  }

  Container_Boundary(spin, "SpinKube WASM") {
    Component(eventFilter, "Event Filter", "Rust", "Transforms raw events → structured alert format")
  }

  ContainerDb(couch, "CouchDB", "", "Alert state documents")
  ContainerDb(keydb, "KeyDB", "", "Active alert cache, pub-sub for real-time UI")
  ContainerDb(clickhouse, "ClickHouse", "", "Aggregated alert analytics")

  Rel(alertTopic, eventFilter, "Consume")
  Rel(eventFilter, alertIngest, "Publish via Kafka")
  Rel(alertIngest, alertSM, "Create SAGA")
  Rel(alertSM, couch, "Read/Write state")
  Rel(alertSM, keydb, "Cache active alerts")
  Rel(alertIngest, alertNotif, "Trigger notification")
  Rel(alertNotif, clickhouse, "Write analytics")
```

## Level 3: Component — Auth Flow

```mermaid
C4Component
  title AuthN/AuthZ Flow — Gateway-Mediated Domain Segregation

  Person(client, "Client", "Bearer JWT or API-Key")

  Container_Boundary(eg, "Envoy Gateway") {
    Component(jwtCheck, "JWT Authentication", "Gateway filter", "Validates JWT from Casdoor, extracts claims")
    Component(apiKeyCheck, "API-Key Authentication", "Gateway filter", "Validates API-Key via Casbin")
    Component(extAuth, "ext_authz gRPC", "SecurityPolicy", "Calls Casbin for authorization decision")
  }

  Container_Boundary(auth, "Auth Services") {
    Component(casdoor, "Casdoor", "", "Issues JWT, manages users, SSO/OIDC/SAML")
    Component(casbinSvc, "Casbin ext_authz Service", "Go gRPC", "Evaluates RBAC + ReBAC + ABAC models. DENY-wins conflict resolution.")
  }

  Container_Boundary(data, "Casbin Data") {
    ComponentDb(pg, "PostgreSQL", "", "Users, roles, policies, relationship tuples")
    Component(rbac, "RBAC Model", "casbin-model.conf", "role-based access per route/action")
    Component(rebac, "ReBAC Model", "casbin-model.conf", "Zanzibar-style relationship-based access")
    Component(abac, "ABAC Model", "casbin-model.conf", "attribute-based access (time, location, device status)")
  }

  Rel(client, jwtCheck, "Request with JWT", "HTTPS")
  Rel(client, apiKeyCheck, "Request with API-Key", "HTTPS/gRPC")
  Rel(jwtCheck, extAuth, "Claims + request context")
  Rel(apiKeyCheck, extAuth, "API-Key + request context")
  Rel(extAuth, casbinSvc, "Check authorization", "gRPC")
  Rel(casbinSvc, casdoor, "Verify JWT/API-Key")
  Rel(casbinSvc, pg, "Read policies")
  Rel(casbinSvc, rbac, "Evaluate")
  Rel(casbinSvc, rebac, "Evaluate")
  Rel(casbinSvc, abac, "Evaluate")
  Rel(rbac, extAuth, "Decision", "ALLOW/DENY")
  Rel(rebac, extAuth, "Decision", "ALLOW/DENY")
  Rel(abac, extAuth, "Decision", "ALLOW/DENY")
  Rel(extAuth, client, "HTTP 200/401/403")
```
