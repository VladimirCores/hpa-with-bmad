---
title: Epic 5: Alert Orchestration System
created: 2026-08-06
updated: 2026-08-06
status: final
---

# PRD: Epic 5 Alert Orchestration System

## 1. Vision

Build a directed, replay-capable alert system that processes alerts from telemetry streams through Kafka ingestion, stores alert state in Pulsar, and triggers automated or human-handled responses. This completes the observability loop: telemetry in → alerts out → action.

## 2. Target User

### 2.1 Jobs To Be Done
- **Platform Engineer** can detect and diagnose platform anomalies within seconds.
- **On-call Engineer** can receive actionable alerts with context and clear remediation paths.
- **Automation System** can respond to alerts without human intervention when safe.

### 2.2 Non-Users (v1)
Not for external customer-facing alert routing or enterprise SIEM integration.

### 2.3 Key User Journeys
- **UJ-1. DevOps engineer gets paged on a node disk alert.** System correlates with recent deployments, shows affected workloads, offers one-click restart.
- **UJ-2. SRE observes high alert volume.** Dashboard shows top alert types, source, trend, allows snooze/label adjustments.

## 3. Glossary
- **Alert Signal** — structured event (JSON) from sensors, metrics, logs.
- **Kafka Streams** — directed processing graph routing alerts by type/priority.
- ** Pulsar Topic** — partitioned, durable message log for alert state.
- ** Alert State Machine** — lifecycle: `received` → `acknowledged` → `resolved` → `closed`.

## 4. Features

### 4.1 Alert Ingestion & Directed Routing
Alerts enter via `alerts.incoming` Kafka topic. Directed streams route by severity (`alerts.critical`, `alerts.warning`) and by domain (`alerts.network`, `alerts.compute`, `alerts.storage`).

**Functional Requirements:**
- **FR-1: Alert Signal Validation** — invalid signals route to `alerts.dlq` with error context.
- **FR-2: Exactly-once Deduplication** — signals with same `alert_id` within 60s dropped.
- **FR-3: Severity Tagging** — every alert tagged `critical`, `warning`, `info`.

**Consequences:**
- JSON schema validation rejects 99.9% of malformed signals at edge.
- Alert deduplication handles restart replay after 60s window.

### 4.2 Alert State Persistence
Alert state transitions stored in Pulsar `alerts.state` topic. Each transition message includes previous state, new state, timestamp, source.

**Functional Requirements:**
- **FR-4: State Transition Logging** — every state change emitted as immutable Pulsar message.
- **FR-5: Replay Capability** — alert history reconstructable from Kafka → Pulsar.

### 4.3 Automated Response Engine
Pulsar Functions evaluate alert conditions and trigger Kubernetes Jobs or Argo CD sync.

**Functional Requirements:**
- **FR-6: Automated Restart** — `restart` action triggers `kubectl rollout restart` on affected pods.
- **FR-7: ConfigMap Update** — `increase_resource` action patches Deployment HPA.

### 4.4 Human Alert Handling
Alerts surface in Grafana/Kiali with actionable runbooks. Acknowledgment tracked in Pulsar state.

**Functional Requirements:**
- **FR-8: Acknowledgment Tracking** — who acknowledged when, visible in UI.
- **FR-9: Audit Trail** — all human actions logged with who, when, what, result.

## 5. Non-Goals (Explicit)
- Alert deduplication beyond 60s window.
- Alert escalation (PagerDuty, OpsGenie) — deferred to v2.
- Alert enrichment from external systems (chatops, ticketing) — deferred to v2.

## 6. MVP Scope

### 6.1 In Scope
- Kafka topic `alerts.incoming` with 12 partitions, 7-day retention.
- Compact topic `alerts.state` for dedup.
- Pulsar Functions for state transitions.
- Kubernetes Jobs for automated restarts.
- Grafana dashboard for alert throughput and top sources.

### 6.2 Out of Scope
- Multi-cluster alert aggregation.
- LLM-powered alert summarization.
- ChatOps alert notification.

## 7. Success Metrics

**Primary:**
- **SM-1**: 99% of alerts processed within 5s validates FR-3.
- **SM-2**: MTTR reduced 40% from current 8min baseline.

**Counter-metrics:**
- **SM-C1**: Alert fatigue rate — page-up rate should not increase >5% without proportional incident reduction.

## 8. Open Questions
1. Who owns alert silencing rules? (Assume: same team as alert definitions).
2. What SLA on alert processing? (Assume: 99.5% within 10s).

## 9. Assumptions Index
- Pulsar Functions support Go 1.22 runtime (confirmed in Epic 4 docs).
- External IPs available for alert receivers (within VPC).

---

## Adapt-In Menu

### Cross-cutting NFRs
- **Reliability** — 99.5% of alerts processed within 10s.
- **Security** — All alert sources mTLS-verified; auth via X-API-Key.

### Constraints and Guardrails
- **Offline-Safe** — All manifests work offline; no external API calls at runtime.

### Developer products
- **API Contracts** — `POST /alerts` with JSON body matching `_alertSchema.yaml`.

---

## Stories
| ID | Status | Description |
|---|---|---|
| 5-1 | in_progress | Ingest alert signals through directed Kafka streams |
| 5-2 | backlog | Persist alert state machine transitions |
| 5-3 | backlog | Trigger automated alert responses |
| 5-4 | backlog | Manage human alert handling with audit trail |
| 5-5 | backlog | Provide basic LLM decision support for alerts |