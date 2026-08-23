# High Performance Distributed Cluster (HPDC)

An offline-first, security-focused enterprise platform for high-RPS IoT telemetry ingestion and processing, with real-time alert detection and response, distributed workload processing, entity management, and AI agent orchestration — delivered entirely through a GitOps-driven, air-gapped pipeline.

## System Design

**Paradigm — Gateway-Mediated Domain Segregation.** The Envoy Gateway is the exclusive ingress boundary. Its routes are hard domain boundaries, each owning its internal runtime pattern. The event mesh (Pulsar + Kafka) is the cross-cutting integration fabric. Compute is serverless-first: KNative (scale-to-zero) with Restate for stateful SAGAs, SpinKube WASM for stateless transforms, and Pulsar Functions for stream processing. No always-on microservices. Storage is layered: Local Path Provisioner for dev clusters, Ceph RBD for production.

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
│        Local Path Provisioner (dev) / Ceph RBD (prod)      │
│          kind + Cilium eBPF (kube-proxy replacement)       │
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
| 1 | Kubernetes substrate: Talos 1.13.7 (Docker), Cilium eBPF with kube-proxy replacement + L2 LB, Cilium mTLS (SPIFFE/SPIRE), local-path storage | done |
| 2 | Offline GitOps delivery: Harbor 2.11.3 registry (scan + sign), Spegel P2P image distribution, local Git mirror, Kargo v1.11 Freight promotion, Argo CD v3.5 ApplicationSet + sync waves, Argo Rollouts v1.9 canary, Argo Events v1.9 | done |
| 3 | Secure gateway & access: Envoy Gateway edge routing, cert-manager TLS, API-key auth, Casdoor JWT, Casbin RBAC/ReBAC/ABAC, Infisical secrets, mTLS mesh, OpenAPI governance, Backstage + tool UI routes | done |
| 4 | Real-time telemetry: IoT device simulator, MQTT/HTTP/gRPC ingestion, Protobuf `CommonEnvelope` normalization, partitioned Pulsar topics, back-pressure, ClickHouse metrics + retention, KeyDB hot cache, Spin WASM events, E2E validation | done |
| 5 | Alert detection & response: Kafka-directed alert streams, alert state machine persistence, automated responses, human alert handling with audit trail, basic LLM decision support | done |
| 6 | Entity & device management: CouchDB/ArcadeDB/YugabyteDB triple-store, entity CRUD + bulk with RBAC + mutation audit, change feed with dedupe, Hasura GraphQL federation | done |
| 7 | Observability & reporting: VictoriaMetrics cluster (vmstorage/vminsert/vmselect), VMLogs, OpenTelemetry collector + tracing, Grafana dashboards + Alertmanager, Grafana/Hubble UI routes | done |
| 8 | Multi-region federation: Cilium ClusterMesh over WireGuard, regional data sovereignty (no cross-region replication by default), central hub querying regional APIs | done |
| 9 | AI agent engine: MCP tool registry (query DBs, call APIs, trigger workflows) with security policy + audit, authenticated agent-to-agent (A2A) messaging | done |
| 10 | Dev cluster lifecycle: kind-based dev cluster with Cilium CNI, kube-proxy replacement, component initialization, persistent storage | done |
| 11 | Dev cluster VM provisioning: Talos Docker provider, idempotent startup, Cilium networking, component installation | in progress |

### Architecture sources

- PRD: `output/planning-artifacts/prds/prd-HPDC-2026-07-21/prd.md`
- Architecture spine + ADRs: `output/planning-artifacts/architecture/architecture-HPDC-2026-07-30/`
- Epics: `output/planning-artifacts/epics.md`

## Project-wide scripting rule

All project automation scripts must be written in Python 3. Shell wrappers are not allowed in the project `scripts/` directory.

## DRY Principle (Mandatory)

All configuration must be centralized in `.env` — no hardcoded IPs, ports, or domains in scripts. See `Epic 12: DRY Principle Investigation & Refactoring` for full scope.

**Rules:**
1. All configurable values go in `.env` (copy `.env.example` to `.env`)
2. Scripts load config via `load_env()` utility function
3. No magic numbers or hardcoded strings in scripts
4. `.env.example` must document every variable with descriptions

## Prerequisites

- Python 3
- Docker for container-based dev clusters
- `kind` (Kubernetes in Docker) for dev cluster management
- `kubectl` for cluster management
- `helm` for package management
- Optional: `talosctl` for production Talos clusters

### DNS Wildcard for `*.hpdc.local`

The dev cluster uses `*.hpdc.local` domains (e.g., `harbor.hpdc.local`, `argocd.hpdc.local`) routed through the Cilium L2 LoadBalancer at `172.18.255.200`. Configure your host to resolve these:

**Option A — `/etc/hosts` (simple, per-hostname):**
```bash
echo "172.18.255.200 harbor.hpdc.local argocd.hpdc.local" | sudo tee -a /etc/hosts
```

**Option B — dnsmasq wildcard (recommended, all `*.hpdc.local`):**
```bash
sudo dnf install dnsmasq

sudo tee /etc/dnsmasq.d/hpdc.conf << 'EOF'
address=/hpdc.local/172.18.255.200
no-resolv
EOF

sudo mkdir -p /etc/systemd/resolved.conf.d
sudo tee /etc/systemd/resolved.conf.d/hpdc.conf << 'EOF'
[Resolve]
DNS=127.0.0.1
Domains=~local
EOF

sudo systemctl enable --now dnsmasq
sudo systemctl restart systemd-resolved
```

## Getting Started

### 1. Bootstrap the dev cluster

Create a kind cluster with Cilium as the CNI (replacing kube-proxy):

```bash
# Create kind cluster with Cilium
kind create cluster --config /tmp/kind-hpdc.yaml

# Install Cilium with kube-proxy replacement
helm upgrade --install cilium cilium/cilium --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost=hpdc-talos-control-plane \
  --set k8sServicePort=6443 \
  --set ipam.mode=cluster-pool \
  --set ipam.operator.clusterPoolIPv4PodCIDRList="10.244.0.0/16" \
  --set cluster.name=hpdc-talos \
  --set cluster.id=1 \
  --set kind.enabled=true \
  --set routingMode=native \
  --set ipv4NativeRoutingCIDR="10.244.0.0/16" \
  --set autoDirectNodeRoutes=true \
  --set bpf.masquerade=true

# Remove kube-proxy (Cilium replaces it)
kubectl delete ds kube-proxy -n kube-system

# Install local-path-provisioner
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.31/deploy/local-path-storage.yaml
```

### 2. Install platform components

Install all required components:

```bash
# cert-manager
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace --version v1.16.3

# Harbor
helm upgrade --install harbor harbor/harbor \
  --namespace harbor --create-namespace \
  --set expose.type=clusterIP \
  --set persistence.enabled=false

# Argo CD
helm upgrade --install argocd argo/argo-cd \
  --namespace argocd --create-namespace \
  --set server.service.type=ClusterIP \
  --set server.extraArgs[0]=--insecure

# Kargo
helm upgrade --install kargo oci://ghcr.io/akuity/kargo-charts/kargo \
  --namespace kargo --create-namespace \
  --set api.adminAccount.passwordHash='$2a$10$Z9yB0vG7F8y5vQ4z6u5u5e5u5e5u5e5u5e5u5e5u5e5u5e5u5e5u5e' \
  --set api.adminAccount.tokenSigningKey=signing-key-change-me-in-production

# VictoriaMetrics
helm upgrade --install victoria-metrics victoriametrics/victoria-metrics-single \
  --namespace monitoring --create-namespace \
  --set server.retentionPeriod=7d \
  --set server.persistentVolume.enabled=false

# Grafana
helm upgrade --install grafana grafana/grafana \
  --namespace monitoring \
  --set persistence.enabled=false \
  --set adminPassword=admin
```

### 3. Validate the cluster

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

#### Storage backend selection

The cluster supports two storage backends via the `--storage` flag:

- **local-path** (default): Lightweight local-path-provisioner for Docker-based dev clusters
- **rook-ceph**: Full Ceph storage with RBD and CephFS (requires block devices)

```python
# With local-path storage (recommended for Docker dev clusters)
python3 scripts/startup.dev.py --offline --apply --storage local-path

# With rook-ceph storage (requires block devices)
python3 scripts/startup.dev.py --offline --apply --storage rook-ceph
```

## Quick health check

```python
python3 scripts/startup.dev.py --offline --dry-run --step 16-install-envoy-gateway-dev.py
python3 scripts/startup.dev.py --offline --dry-run --step 17-install-telemetry-ingestion-dev.py
python3 scripts/startup.dev.py --offline --dry-run --step 15-validate-offline-gitops-pipeline.py
```

## Local Access to Cluster Components

All cluster components are reached through the Envoy Gateway single entry point, which serves the wildcard host `*.hpdc.local` on port 80.

### Gateway IP (fixed)

The Envoy Gateway LoadBalancer IP is **fixed** at `172.18.255.200` — it's the first IP in the Cilium L2 pool (`172.18.255.200-209`). This IP persists across cluster restarts.

```bash
kubectl get svc -n envoy-gateway-system
```

The `envoy-*` service exposes `EXTERNAL-IP: 172.18.255.200` (from the Cilium L2 LoadBalancer pool).

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

Map every `*.hpdc.local` hostname to the fixed gateway IP `172.18.255.200`.

#### Option A — `/etc/hosts` (per-hostname)

```bash
echo "172.18.255.200 harbor.hpdc.local argocd.hpdc.local grafana.hpdc.local" | sudo tee -a /etc/hosts
```

#### Option B — dnsmasq wildcard (all `*.hpdc.local`)

See [DNS Wildcard for `*.hpdc.local`](#dns-wildcard-for-hpdclocal) in Prerequisites.

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
