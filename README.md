# High Performance Distributed Cluster (HPDC)

An offline-first, security-focused enterprise platform for high-RPS IoT telemetry ingestion and processing, with real-time alert detection and response, distributed workload processing, entity management, and AI agent orchestration — delivered entirely through a GitOps-driven, air-gapped pipeline.

## System Design

**Paradigm — Gateway-Mediated Domain Segregation.** The Envoy Gateway is the exclusive ingress boundary. Its routes are hard domain boundaries, each owning its internal runtime pattern. The event mesh (Pulsar + Kafka) is the cross-cutting integration fabric. Compute is serverless-first: KNative (scale-to-zero) with Restate for stateful SAGAs, SpinKube WASM for stateless transforms, and Pulsar Functions for stream processing. No always-on microservices.

```
┌────────────────────────────────────────────────────────────┐
│                       Envoy Gateway                         │
│  /data │ /api │ /gql │ /telemetry │ /events │ tool UIs     │
├────────┼──────┼──────┼────────────┼─────────┼──────────────┤
│ CouchDB│KNative│Hasura│  Pulsar    │ Kafka   │ Backstage,   │
│        │Restate│      │  Functions │SpinKube │ ArgoCD,      │
├────────┴──────┴──────┴────────────┴─────────┴──────────────┤
│              Event Mesh (Pulsar + Kafka)                    │
├──────┬────────┬────────┬──────────┬────────┬───────────────┤
│Couch │Yugabyte│ArcadeDB│ClickHouse│ KeyDB  │ PostgreSQL    │
│  DB  │  DB    │        │          │        │ (Auth)        │
├──────┴────────┴────────┴──────────┴────────┴───────────────┤
│              Ceph RBD (persistent storage)                  │
│          Talos Linux + Cilium (eBPF) substrate              │
└────────────────────────────────────────────────────────────┘
```

### Route domains (AD-2)

| Route | Domain | AuthN | Pattern |
|-------|--------|-------|---------|
| `/data/*` | Document-serving | Casdoor JWT | CouchDB native (CRUD, MapReduce, `_changes`) |
| `/api/*` | Serverless workflows | Casdoor JWT | KNative + Restate (SAGA, event-sourcing) |
| `/gql` | Data federation | Casdoor JWT | Hasura (federates CouchDB + ClickHouse + YugabyteDB) |
| `/telemetry/*` | Stream ingestion | API-Key | Pulsar native (MQTT/gRPC handlers) |
| `/events/*` | Event pub-sub | API-Key | Kafka + SpinKube WASM |
| `mqtt:1884` | Device telemetry | Platform MQTT auth | Pulsar native |

### Epics

| Epic | Scope | Status |
|------|-------|--------|
| 1 | Kubernetes substrate: Talos 1.13.7 (QEMU), Cilium eBPF with kube-proxy replacement + L2 LB, Cilium mTLS (SPIFFE/SPIRE), Rook-Ceph RBD | done |
| 2 | Offline GitOps delivery: Harbor 2.11.3 registry (scan + sign), Spegel P2P image distribution, local Git mirror, Kargo v1.11 Freight promotion, Argo CD v3.5 ApplicationSet + sync waves, Argo Rollouts v1.9 canary, Argo Events v1.9 | done |
| 3 | Secure gateway & access: Envoy Gateway edge routing, cert-manager TLS, API-key auth, Casdoor JWT, Casbin RBAC/ReBAC/ABAC, Infisical secrets, mTLS mesh, OpenAPI governance, Backstage + tool UI routes | done |
| 4 | Real-time telemetry: IoT device simulator, MQTT/HTTP/gRPC ingestion, Protobuf `CommonEnvelope` normalization, partitioned Pulsar topics, back-pressure, ClickHouse metrics + retention, KeyDB hot cache, Spin WASM events, E2E validation | done |
| 5 | Alert detection & response: Kafka-directed alert streams, alert state machine persistence, automated responses, human alert handling with audit trail, basic LLM decision support | done |
| 6 | Entity & device management: CouchDB/ArcadeDB/YugabyteDB triple-store, entity CRUD + bulk with RBAC + mutation audit, change feed with dedupe, Hasura GraphQL federation | done |
| 7 | Observability & reporting: VictoriaMetrics cluster (vmstorage/vminsert/vmselect), VMLogs, OpenTelemetry collector + tracing, Grafana dashboards + Alertmanager, Grafana/Hubble UI routes | done |
| 8 | Multi-region federation: Cilium ClusterMesh over WireGuard, regional data sovereignty (no cross-region replication by default), central hub querying regional APIs | done |
| 9 | AI agent engine: MCP tool registry (query DBs, call APIs, trigger workflows) with security policy + audit, authenticated agent-to-agent (A2A) messaging | done |

### Architecture sources

- PRD: `output/planning-artifacts/prds/prd-HPDC-2026-07-21/prd.md`
- Architecture spine + ADRs: `output/planning-artifacts/architecture/architecture-HPDC-2026-07-30/`
- Epics: `output/planning-artifacts/epics.md`

## Project-wide scripting rule

All project automation scripts must be written in Python 3. Shell wrappers are not allowed in the project `scripts/` directory.

## Prerequisites

- Python 3
- `talosctl` for real Talos bootstrap
- QEMU or `qemu-img`
- Optional: `kubectl` for real cluster apply and readiness checks

## Getting Started

### 1. Bootstrap the dev repository

Run the scaffold bootstrap once:

```python
python3 scripts/gitops/bootstrap_dev.py
```

### 2. Run offline dev setup dry-runs

Run the platform and GitOps setup without applying to a live cluster:

```python
python3 scripts/startup.dev.py --offline --dry-run
```

Run one ordered step only:

```python
python3 scripts/startup.dev.py --offline --dry-run --step 02-bootstrap-talos-dev.py
```

List all ordered steps:

```python
python3 scripts/startup.dev.py --list
```

Each startup run rewrites `output/startup.dev.log` before executing so the selected dry-run, check, or apply flow is reviewable.

### 3. Validate all implemented stories

Run the validation tests:

```python
python3 -m compileall -q scripts tests
for t in tests/test_*.py; do python3 "$t"; done
```

Or run a single test:

```python
python3 tests/test_install_grafana_alertmanager_dev.py
```

### 4. Run the ATDD P0 suite

The acceptance suite under `tests/atdd/` is the green-phase contract suite
(143 passed, 7 skipped as of 2026-08-11). Run it with pytest:

```python
python3 -m pytest tests/ -q
```

The 7 skips are RED-phase live journeys still gated on a live cluster (B-001).

**Harnesses that back the suite** (all built 2026-08-11, offline contracts):

| Harness | Where | Contract |
|---------|-------|----------|
| Identity fixtures (B-002) | `tests/atdd/support/fixtures.py` | `api_key_fixture`, `jwt_fixture` (RS256), `jwks_fixture`, `verify_jwt`, 7 Casdoor roles |
| Consumer harness (B-003) | `tests/atdd/support/consumer_harness.py` | `pulsar_consumer_harness`/`kafka_consumer_harness` message-arrival + latency asserts (remote HTTP `HPDC_CONSUMER_HARNESS_URL` / local NDJSON store) |
| Load harness (B-005) | `hpdc_test_client.py` → `LoadHarness` | k6 soak script (NFR1/NFR3 thresholds) + local simulation fallback |

The harnesses switch to live backends automatically via env vars:
`HPDC_CONSUMER_HARNESS_URL`, `HPDC_KAFKA_CONSUMER_HARNESS_URL`,
`HPDC_EDGE_URL`, `HPDC_EVENTS_API_KEY`. With `k6` on PATH, `LoadHarness.soak()`
runs a real constant-arrival-rate soak against the gateway; without it, it
runs a bounded local simulation against the dev edge service.

### 5. Apply to a real offline Talos cluster

Apply only after the dry-runs pass and `output/talos/talosconfig` exists:

```python
python3 scripts/startup.dev.py --offline --apply
```

`--apply` requires `kubectl` and a healthy offline Talos cluster.

## Quick health check

```python
python3 scripts/startup.dev.py --offline --dry-run --step 16-install-envoy-gateway-dev.py
python3 scripts/startup.dev.py --offline --dry-run --step 17-install-telemetry-ingestion-dev.py
python3 scripts/startup.dev.py --offline --dry-run --step 15-validate-offline-gitops-pipeline.py
```

## Local Access to Cluster Components

All cluster components are reached through the Envoy Gateway single entry point, which serves the wildcard host `*.hpdc.local` on port 443 (HTTPS, TLS terminated by cert-manager) and redirects port 80.

### Find the gateway address

```bash
kubectl get svc -n envoy-gateway-system
```

The `hpdc-edge-*` proxy service exposes the `EXTERNAL-IP` (from the Cilium L2 LoadBalancer pool `192.168.100.200/32` in the dev cluster). Note it — this is the single IP for every component below.

### Component hostnames

| Component | URL |
|-----------|-----|
| Backstage | `https://backstage.hpdc.local` |
| Argo CD | `https://backstage.hpdc.local/argocd` |
| Kargo | `https://backstage.hpdc.local/kargo` |
| Grafana | `https://grafana.hpdc.local` |
| Hubble UI | `https://hubble.hpdc.local` |
| Casdoor (SSO) | `https://casdoor.hpdc.local` |
| Domain routes | `https://<any>.hpdc.local/data`, `/api`, `/gql`, `/telemetry`, `/events` (path-based, port 443) |
| MQTT device route | `mqtt://<any>.hpdc.local:1884` |

Native tool auth is enforced per tool (e.g. Backstage signs in via Casdoor); Casdoor/Casbin `ext_authz` is **not** enforced on tool-UI routes.

### Hosts file setup

Map every `hpdc.local` hostname to the gateway IP. Replace `<GATEWAY_IP>` with the `EXTERNAL-IP` from above.

#### macOS / Linux

Edit `/etc/hosts`:

```bash
sudo vim /etc/hosts
```

Add (all resolve to the same gateway IP):

```
<GATEWAY_IP> hubble.hpdc.local grafana.hpdc.local casdoor.hpdc.local
<GATEWAY_IP> backstage.hpdc.local argocd.hpdc.local kargo.hpdc.local
<GATEWAY_IP> hpdc.local api.hpdc.local gql.hpdc.local telemetry.hpdc.local events.hpdc.local
```

Any `*.hpdc.local` name works for the path-based domain routes; the explicit names above are for readability.

Flush the DNS cache:

```bash
# macOS
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder

# Linux (systemd-resolved)
sudo resolvectl flush-caches
# or
sudo systemd-resolve --flush-caches
```

Verify:

```bash
ping hubble.hpdc.local
curl -k -I https://hubble.hpdc.local
```

#### Windows

Edit the hosts file as Administrator. Open **Notepad as Administrator**, then open `C:\Windows\System32\drivers\etc\hosts` and add:

```
<GATEWAY_IP> hubble.hpdc.local grafana.hpdc.local casdoor.hpdc.local
<GATEWAY_IP> backstage.hpdc.local argocd.hpdc.local kargo.hpdc.local
<GATEWAY_IP> hpdc.local api.hpdc.local gql.hpdc.local telemetry.hpdc.local events.hpdc.local
```

Flush the DNS cache:

```powershell
ipconfig /flushdns
```

Verify:

```powershell
ping hubble.hpdc.local
curl.exe -k -I https://hubble.hpdc.local
```

> The TLS certificate for `*.hpdc.local` is a cert-manager-issued wildcard (self-signed CA for offline dev). Browsers will show a certificate warning unless you trust the dev CA; use `-k` for curl or "proceed anyway" in the browser.

### Repo layout

```
├── gitops/            # Kustomize bases + overlays per component (functional naming)
│   ├── platform/      # Platform scaffold + contract bindings
│   ├── cilium/        # Networking, L2 LB, mTLS mesh
│   ├── envoy-gateway/ # Edge routing (Gateway, GatewayClass, HTTPRoutes)
│   ├── harbor/ kargo/ argo-cd/ argo-rollouts/ argo-events/ spegel/   # Offline GitOps delivery
│   ├── casdoor/ casbin/ infisical/ cert-manager/                     # Security & access
│   ├── telemetry-* / entity-store / alerts / agent-engine             # Workloads
│   ├── victoria-metrics/ monitoring/ observability/                   # Observability
│   └── clustermesh/ regional-sovereignty/ regional-hub/               # Multi-region
├── scripts/           # Python 3 automation (startup.dev.py, stop.dev.py, gitops/ services/ telemetry/ steps/)
├── tests/             # Python validation tests (test_*.py)
│   └── atdd/          # P0 acceptance suite (api/, e2e/, support/ fixtures + harnesses)
├── hpdc_test_client.py# Dev-side test harness (EventsClient, LoadHarness, etc.)
└── output/            # Generated artifacts, logs, offline caches
```
