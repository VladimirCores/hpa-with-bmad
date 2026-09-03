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

| Route | Host | AuthN | Pattern |
|-------|------|-------|---------|
| `/data/*` | `*.hpdc.local` | X-API-Key | CouchDB native (CRUD, MapReduce, `_changes`) |
| `/api/*` | `*.hpdc.local` | X-API-Key | KNative + Restate (SAGA, event-sourcing) |
| `/gql` | `*.hpdc.local` | Casdoor JWT | Hasura (federates CouchDB + ClickHouse + YugabyteDB) |
| `/telemetry/*` | `*.hpdc.local` | X-API-Key | Pulsar native (MQTT/gRPC handlers) |
| `/events/*` | `*.hpdc.local` | X-API-Key | Kafka + SpinKube WASM |
| `/couchdb/*` | `admin.hpdc.local` | CouchDB native login | CouchDB Fauxton admin UI + full REST API |
| `mqtt:1884` | — | Platform MQTT auth | Pulsar native |

The `/couchdb` admin route on `admin.hpdc.local` is the **only** path that skips gateway key auth: it serves CouchDB's own Fauxton UI and REST API, and the gateway URL rewrite strips `/couchdb` so requests reach CouchDB's root. Auth is CouchDB's own admin session (see [Exposing component admin/settings UIs](docs/envoy-gateway-edge-routing.md#exposing-component-adminsettings-uis)).

### Epics

| Epic | Scope | Status |
|------|-------|--------|
| 1 | Kubernetes substrate: Talos 1.13.7, Cilium eBPF with kube-proxy replacement + L2 LB, Cilium mTLS (SPIFFE/SPIRE), local-path storage | done |
| 2 | Offline GitOps delivery: Harbor registry (scan + sign), Spegel P2P image distribution, local Git mirror, Kargo Freight promotion, Argo CD ApplicationSet + sync waves, Argo Rollouts canary, Argo Events | done |
| 3 | Secure gateway & access: Envoy Gateway edge routing (static TLS for dev), API-key auth, Casdoor JWT, Casbin RBAC/ReBAC/ABAC, Infisical secrets, mTLS mesh, OpenAPI governance, Backstage + tool UI routes | done |
| 4 | Real-time telemetry: IoT device simulator, MQTT/HTTP/gRPC ingestion, Protobuf `CommonEnvelope` normalization, partitioned Pulsar topics, back-pressure, ClickHouse metrics + retention, KeyDB hot cache, Spin WASM events, E2E validation | done |
| 5 | Alert detection & response: Kafka-directed alert streams, alert state machine persistence, automated responses, human alert handling with audit trail, basic LLM decision support | done |
| 6 | Entity & device management: CouchDB/ArcadeDB/YugabyteDB triple-store, entity CRUD + bulk with RBAC + mutation audit, change feed with dedupe, Hasura GraphQL federation | done |
| 7 | Observability & reporting: VictoriaMetrics cluster (vmstorage/vminsert/vmselect), VMLogs, OpenTelemetry collector + tracing, Grafana dashboards + Alertmanager, Grafana/Hubble UI routes | done |
| 8 | Multi-region federation: Cilium ClusterMesh over WireGuard, regional data sovereignty (no cross-region replication by default), central hub querying regional APIs | done |
| 9 | AI agent engine: MCP tool registry (query DBs, call APIs, trigger workflows) with security policy + audit, authenticated agent-to-agent (A2A) messaging | done |
| 10 | Dev cluster lifecycle: kind-based dev cluster with Cilium CNI, kube-proxy replacement, component initialization, persistent storage | done |
| 11 | Dev cluster VM provisioning: Talos 1.13.7 on QEMU, offline image + chart mirrors at 10.6.0.1, idempotent `startup.dev.py` bootstrap, Cilium networking (flannel + kube-proxy disabled at provision), Rook-Ceph storage, full component stack | in progress |

### Architecture sources

- PRD: `output/planning-artifacts/prds/prd-HPDC-2026-07-21/prd.md`
- Architecture spine + ADRs: `output/planning-artifacts/architecture/architecture-HPDC-2026-07-30/`
- Epics: `output/planning-artifacts/epics.md`

## Project-wide scripting rule

All project automation scripts must be written in Python 3. Shell wrappers are not allowed in the project `scripts/` directory.

## DRY Principle (Mandatory)

All configuration must be centralized in `.env` — no hardcoded IPs, ports, domains — **or component image versions** — in scripts. Component versions resolve through `scripts/gitops/component_versions.py` (the single catalog consumed by installers, validators, `image-preflight.py` and the GitOps renderer). See `Epic 12: DRY Principle Investigation & Refactoring` for full scope.

**Rules:**
1. All configurable values go in `.env` (copy `.env.example` to `.env`)
2. Scripts load config via `load_env()` utility function; component versions via `component_versions.get("HPDC_<COMPONENT>_VERSION")` — never declare local version constants
3. No magic numbers or hardcoded strings in scripts
4. `.env.example` must document every variable with descriptions
5. Never commit a mutable `:latest` image tag; pin exact versions (AD-19)

**Changing a component version (offline-safe runbook):**
1. Edit the variable in `.env`
2. `python3 scripts/services/image-preflight.py --check` — the mirror gate fails with exact fill commands for any tag missing from `localhost:5000`; run them (`skopeo copy --all …`)
3. `python3 scripts/gitops/render_overlays.py` → commit regenerated `gitops/<comp>/rendered/dev.yaml`
4. Rerun step 09 (refresh local git mirror) → hard-refresh ArgoCD apps

## Prerequisites

- Python 3
- QEMU/KVM (`/dev/kvm` present) — the dev cluster runs on **Talos 1.13.7 VMs**, not `kind`
- `talosctl` v1.13.7 (Talos config at `~/.talos/config`; bundled `output/talos/talosconfig`)
- `kubectl` v1.36.2 (matches the cluster's Kubernetes version)
- `helm` v3 (Helm charts served from the local `10.6.0.1:8080` chart server)
- `skopeo` (offline image prefetch / mirroring into `10.6.0.1:5000`)

### DNS / gateway address for `*.hpdc.local`

The dev cluster is fully offline. The Envoy Gateway edge address is the value of
**`HPDC_GATEWAY_IP`** in `.env` (default `172.18.0.2`), i.e. the Cilium L2
LoadBalancer IP assigned to the `envoy-*` Service in `envoy-gateway-system` (see
`gitops/envoy-gateway/base/envoy-gateway.yaml` and
`gitops/cilium/base/cilium-loadbalancer-ippool.yaml`). All `*.hpdc.local`
hostnames resolve there. Map them on your host (`HPDC_GATEWAY_IP` is loaded from
`.env` by `scripts/startup.dev.py`):

**Option A — `/etc/hosts` (per-hostname):**
```bash
GATEWAY_IP="${HPDC_GATEWAY_IP:-172.18.0.2}"
echo "$GATEWAY_IP harbor.hpdc.local argocd.hpdc.local grafana.hpdc.local" | sudo tee -a /etc/hosts
echo "$GATEWAY_IP backstage.hpdc.local hubble.hpdc.local admin.hpdc.local" | sudo tee -a /etc/hosts
```

**Option B — dnsmasq wildcard (all `*.hpdc.local`):**
```bash
sudo dnf install dnsmasq

sudo tee /etc/dnsmasq.d/hpdc.conf << 'EOF'
address=/hpdc.local/${HPDC_GATEWAY_IP:-172.18.0.2}
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

The dev cluster is a **Talos 1.13.7 / Kubernetes v1.36.2** cluster on QEMU VMs,
provisioned fully offline: all images pull from `10.6.0.1:5000`, all Helm charts
from `10.6.0.1:8080`. The bootstrap (`scripts/startup.dev.py --offline --apply`)
provisions the cluster with **flannel and kube-proxy disabled** via
`platform/talos/talos-cni-patch.yaml` (`cluster.cni.name: none`,
`cluster.proxy.disabled: true`); Cilium is then installed as the only CNI in
kube-proxy-replacement mode. Rook-Ceph provides the dev storage backend.

Bring the cluster up idempotently:

```bash
export KUBECONFIG=/tmp/hpacore.kc   # written by the bootstrap; regenerate with:
sudo -n cat /root/.kube/config > /tmp/hpacore.kc && chmod 600

python3 scripts/startup.dev.py --offline --apply --storage rook-ceph
```

**Resume-safe state (survives interruption / host reboot):**
- QEMU VMs on a host bridge (`talos3fa363a2`, `10.6.0.1/24`; nodes `10.6.0.2`–`10.6.0.5`)
  hold etcd + Pod state on persistent disks — a re-run of `startup.dev.py` resumes
  where it left off.
- `KUBECONFIG=/tmp/hpacore.kc` — regenerate after a reboot with
  `sudo -n cat /root/.kube/config > /tmp/hpacore.kc && chmod 600`.
- The local registry (`10.6.0.1:5000`) and Helm chart server (`10.6.0.1:8080`,
  setsid) run as host background processes; QEMU nodes mirror exclusively through them.
- A host MutatingWebhook `rook-sec-hook` (`https://10.6.0.1:8443`) injects
  `pod.securityContext.runAsUser:0` into Rook pods — a workaround for Talos blocking
  the `/var/lib/rook` chown (JSONPatch only; Merge is silently dropped on uid). It
  survives a cluster rebuild but **not** a host reboot. Resurrect it with
  `bash /tmp/deploy_webhook.sh`.

Tear down cleanly (PID-based — never `pkill -f` a self-referential pattern):

```bash
bash /tmp/kill_cluster.sh
```

### 2. Install platform components

Platform components deploy **declaratively via GitOps** — no manual `helm install`.
Each component is a rendered Kustomize overlay under `gitops/<component>/rendered/dev.yaml`,
reconciled by Argo CD through the app-of-apps children in `gitops/apps/`.

The bootstrap order is encoded as numbered steps in `scripts/startup.dev.py`
(inspect with `--status` / `--status --all`). After a version or toggle change,
regenerate all rendered overlays from `.env` (offline-safe):

```bash
python3 scripts/gitops/render_overlays.py       # gitops/<component>/rendered/dev.yaml
python3 scripts/gitops/render_app_of_apps.py    # gitops/apps/ Argo CD Application children
```

Component image versions are centralized in `.env.versions`, resolved exclusively
through `scripts/gitops/component_versions.py`, and validated against the offline
mirror by `python3 scripts/services/image-preflight.py --check`.

### 3. Validate the cluster

```python
python3 -m compileall -q scripts tests
for t in tests/test_*.py; do python3 "$t"; done
```

A single component's install validator:

```python
python3 tests/test_install_grafana_alertmanager_dev.py
```

### 4. Run the ATDD P0 suite

The green-phase contract suite lives under `tests/atdd/`. The **P0 suite (16/16
passed in 4.64s)** gates the live cluster — it audits route-table security-policy
coverage (`test_p0_route_table_audit.py`) and gitops secret hygiene
(`test_p0_secret_scan.py`):

```bash
KUBECONFIG=/tmp/hpacore.kc python3 -m pytest \
  tests/atdd/e2e/test_p0_route_table_audit.py \
  tests/atdd/e2e/test_p0_secret_scan.py -v
```

The wider `tests/` tree (143 passed, 7 skipped as of 2026-08-11) additionally
includes RED-phase live journeys still gated on a live cluster (B-001).

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

The dev cluster uses **Rook-Ceph** (`HPDC_STORAGE_BACKEND=rook-ceph` in
`.env.components`) — a CephCluster with 3 OSDs and RBD/CephFS CSI, running on the
QEMU worker nodes. (The legacy `local-path` backend is retained for single-node
Docker dev only; it is **not** the active dev configuration.)

#### Component feature toggles

Per-component and per-sub-system toggles (`HPDC_*_ENABLED=true|false`) control which
steps run. Toggle values live in the three-layer `.env` stack:

- `.env` — your local overrides (**gitignored**)
- `.env.components` — committed dev config (toggles + storage backend)
- `.env.versions` — committed version pins

`startup.dev.py` / `component_versions.load_all_dotenv()` load all three in order
(`.env` → `.env.components` → `.env.versions`); **existing environment variables
always win.**

**Toggle resolution priority:**
1. Core components (`CILIUM`, `HUBBLE`, `HARBOR`, `SPEGEL`): always enabled (override ignored)
2. `HPDC_STORAGE_BACKEND` selects storage provisioner (`rook-ceph` or `local-path`)
3. `os.environ["HPDC_<COMPONENT>_ENABLED"]` (shell export or `.env`)
4. `ENABLED_DEFAULTS` in `component_versions.py` (per-component hardcoded default)
5. `False` (safe default — opt-in, not opt-out)

The committed dev defaults (`.env.components`) enable: Cilium/Hubble, Harbor, Spegel,
Git Mirror, Envoy Gateway (with static self-signed TLS via step 04.5), ArgoCD,
Casdoor, Casbin and Infisical (Rook-Ceph storage). Everything else (Kargo, Argo-Rollouts,
Argo-Events, Backstage, full observability, mTLS/SPIRE, API-key auth, Casbin
RBAC/ReBAC/ABAC) is **off** by default — enable it in `.env` to opt in.

```bash
# Show status (skipped steps hidden)
python3 scripts/startup.dev.py --status

# Preview which Argo CD apps the toggles would deploy
python3 scripts/gitops/render_app_of_apps.py --dry-run

# Filter apps by toggles (writes enabled apps to gitops/apps/)
python3 scripts/gitops/render_app_of_apps.py
```

## Quick health check

```python
python3 scripts/startup.dev.py --offline --dry-run --step 16-install-envoy-gateway-dev.py
python3 scripts/startup.dev.py --offline --dry-run --step 17-install-telemetry-ingestion-dev.py
python3 scripts/startup.dev.py --offline --dry-run --step 15-validate-offline-gitops-pipeline.py
```

## Local Access to Cluster Components

All cluster components are reached through the Envoy Gateway single entry point,
which serves the wildcard host `*.hpdc.local`. The `envoy-*` Service is a Cilium
LoadBalancer whose external IP is the value of `HPDC_GATEWAY_IP` from `.env`
(default `172.18.0.2`; see `gitops/envoy-gateway/base/envoy-gateway.yaml` and
`gitops/cilium/base/cilium-loadbalancer-ippool.yaml`).

```bash
kubectl -n envoy-gateway-system get svc
# envoy-envoy-gateway-system-hpdc-edge-...  LoadBalancer  10.97.127.64  <HPDC_GATEWAY_IP from .env>
```

| Component | URL |
|-----------|-----|
| Backstage | `https://backstage.hpdc.local` |
| Argo CD | `https://backstage.hpdc.local/argocd` |
| Kargo | `https://backstage.hpdc.local/kargo` |
| Grafana | `https://grafana.hpdc.local` |
| Hubble UI | `https://hubble.hpdc.local` |
| Casdoor (SSO) | `https://casdoor.hpdc.local` |
| CouchDB Fauxton admin | `https://admin.hpdc.local/couchdb/_utils/` |
| Domain routes | `https://<any>.hpdc.local/data`, `/api`, `/gql`, `/telemetry`, `/events` (path-based, port 443) |
| MQTT device route | `mqtt://<any>.hpdc.local:1884` |

Native tool auth is enforced per tool (e.g. Backstage signs in via Casdoor); Casdoor/Casbin `ext_authz` is **not** enforced on tool-UI routes.

### Hosts file setup

Map the hostnames above to the value of `HPDC_GATEWAY_IP` from `.env` (default
`172.18.0.2`). (For the full wildcard, see
[DNS / gateway address](#dns--gateway-address-for-hpdclocal) in Prerequisites.)

**Linux:**
```bash
GATEWAY_IP="${HPDC_GATEWAY_IP:-172.18.0.2}"
echo "$GATEWAY_IP harbor.hpdc.local argocd.hpdc.local grafana.hpdc.local" | sudo tee -a /etc/hosts
echo "$GATEWAY_IP backstage.hpdc.local hubble.hpdc.local admin.hpdc.local casdoor.hpdc.local" | sudo tee -a /etc/hosts
```

**macOS:**
```bash
GATEWAY_IP="${HPDC_GATEWAY_IP:-172.18.0.2}"
echo "$GATEWAY_IP *.hpdc.local" | sudo tee -a /etc/hosts
# or install dnsmasq `brew install dnsmasq` and point it at $GATEWAY_IP
```

**Windows** (Notepad as Administrator → `C:\Windows\System32\drivers\etc\hosts`):
```
<GATEWAY_IP> harbor.hpdc.local argocd.hpdc.local grafana.hpdc.local
<GATEWAY_IP> backstage.hpdc.local hubble.hpdc.local admin.hpdc.local casdoor.hpdc.local
<GATEWAY_IP> hpdc.local api.hpdc.local gql.hpdc.local telemetry.hpdc.local events.hpdc.local
```

Flush the DNS cache:
```bash
# macOS
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder
# Linux (systemd-resolved)
sudo resolvectl flush-caches
```

Verify:
```bash
ping hubble.hpdc.local
curl -k -I https://hubble.hpdc.local
```

> The TLS certificate for `*.hpdc.local` is a **static self-signed wildcard** generated by `scripts/gitops/gen-edge-cert.py` (step 04.5 in the boot sequence). See [Static TLS Termination](docs/static-tls-termination.md) for details. Browsers will show a certificate warning because the cert is self-signed; use `-k` for curl or "proceed anyway" in the browser.

### Production Considerations

The dev cluster uses a **static self-signed wildcard cert** for TLS termination. This is
suitable for offline development only. Production deployments require:

- **cert-manager** with a proper issuer (e.g. Let's Encrypt, internal CA) and `Certificate`
  resources for automated certificate lifecycle management, or
- **External CA** with certificates pre-provisioned and injected via CI/CD or a secrets
  manager (e.g. Infisical, Vault)

Production TLS is not implemented. The production architecture should define certificate
rotation, revocation, and renewal policies. See [Static TLS Termination](docs/static-tls-termination.md)
for the dev approach and its limitations.

### Repo layout

```
├── gitops/            # Kustomize bases + overlays per component (functional naming)
│   ├── platform/      # Platform scaffold + contract bindings
│   ├── cilium/        # Networking, L2 LB, mTLS mesh
│   ├── envoy-gateway/ # Edge routing (Gateway, GatewayClass, HTTPRoutes)
│   ├── harbor/ kargo/ argo-cd/ argo-rollouts/ argo-events/ spegel/   # Offline GitOps delivery
│   ├── casdoor/ casbin/ infisical/                     # Security & access
│   ├── telemetry-* / entity-store / alerts / agent-engine             # Workloads
│   ├── victoria-metrics/ monitoring/ observability/                   # Observability
│   └── clustermesh/ regional-sovereignty/ regional-hub/               # Multi-region
├── scripts/           # Python 3 automation (startup.dev.py, stop.dev.py, gitops/ services/ telemetry/ steps/)
├── tests/             # Python validation tests (test_*.py)
│   └── atdd/          # P0 acceptance suite (api/, e2e/, support/ fixtures + harnesses)
├── hpdc_test_client.py# Dev-side test harness (EventsClient, LoadHarness, etc.)
└── output/            # Generated artifacts, logs, offline caches
```
