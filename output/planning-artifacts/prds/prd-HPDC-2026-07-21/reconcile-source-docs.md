# Source Document Reconciliation: PRD vs. docs/

**PRD:** `prd-HPDC-2026-07-21/prd.md`
**Total source documents:** 13
**Date:** 2026-07-21

---

## Document: UP-00 — Backstage Kargo ArgoCD with Fleet.md

### Key Points
- Hub-and-spoke topology: Management Plane (Kargo + Argo CD Fleet Orchestrator) vs. Workload Planes (Spoke clusters with Argo Agent)
- Dev cluster: 4 VMs (1 CP, 3 Workers) via OpenTofu/QEMU with deterministic DHCP (static IPs .100, .110+)
- Production: Cluster API (CAPI) or Terraform targeting cloud/on-prem
- Golden Path template produces: app code, Dockerfile, Helm chart, catalog-info.yaml, Kargo Warehouse, Argo CD Application/ApplicationSet
- Backstage embedded Argo Rollouts tab for canary observation
- CI fails if high-priority CVEs detected; image marked "verified" only after scan pass
- Sync Waves: -10 (CRDs) → -5 (Network) → -4 (Storage) → -3 (Platform Core) → 1 (Applications)
- VictoriaMetrics analytics drives canary analysis
- Step-by-step workflow from developer → Backstage → Git → Kargo → Argo CD → Spoke clusters
- Dev parity table: same CNI/Storage/Secrets/GitOps stack, different runtime substrate

### Coverage Status: COVERED

---

## Document: SP-1 — Provide a plan to implement it step by step — k8s Kargo Workflow.md

### Key Points
- Multi-environment implementation matrix (Dev/Staging/Production) with per-tier config
- Staging: remote OpenTofu over SSH/libvirt RPC (`qemu+ssh://`)
- Production: WireGuard or Netmaker Mesh VPN + Cilium ClusterMesh to connect 5 distinct clusters
- ArcadeDB mentioned as additional database alongside YugabyteDB, CouchDB, KeyDB
- Spegel cache also covers .wasm artifacts, not just OCI images
- Cilium L2 IPAM in dev/staging, physical L2 announcements on top-of-rack switches for production
- Production ClusterMesh connects 5 bare-metal clusters
- Kargo promotion to production updates all 5 clusters simultaneously via ApplicationSet

### Coverage Status: PARTIAL

**Gaps:**
- ArcadeDB (graph database) mentioned alongside YugabyteDB/CouchDB/KeyDB but absent from PRD entirely
- Staging OpenTofu via SSH/libvirt RPC — PRD mentions `talosctl cluster create` for dev but doesn't define staging provisioning mechanism
- Production uses 5-node bare-metal mesh (specific count) — PRD says "hundreds of clusters" but doesn't pin the baseline topology
- Physical L2 announcements on top-of-rack switches (vs. CiliumL2AnnouncementPolicy for dev)

---

## Document: SP-2 — Also provide architecture structure (folders/git repos) for Kargo/ArgoCD pipeline.md

### Key Points
- Three-repository architecture: `app-source-code`, `gitops-infra`, `gitops-workloads`
- `gitops-infra` structure: bootstrap/ (root-app-of-apps, platform-app-set), infrastructure/ (cilium, rook-ceph), iam/ (casdoor, casbin), platform/ (gateway, spegel, knative, spinkube, kafka, pulsar, clickhouse, databases), provisioning/ (opentofu dev/staging)
- `gitops-workloads` structure: kargo/ (stages.yaml, warehouse.yaml), workloads/ (functions base+overlays, spins base+overlays), argocd-apps/ (per-environment workload yamls)
- Concrete Kargo Warehouse YAML (semver constraint `^1.0.0`, `discoveryLimit: 5`)
- Concrete Kargo Stage YAML (dev → fresh Freight, staging → from dev, production → from staging + manual approval)
- Production ApplicationSet maps to 5 regions
- Lifecycle of a code change from commit → CI → Harbor → Warehouse → Kargo updates Kustomize overlays → Argo CD syncs

### Coverage Status: COVERED

(Repo structure details and concrete Kargo manifests align with FR-17, FR-18, FR-19.)

---

## Document: SP-3 — Architecture diagram.md

### Key Points
- GraphQL API at `/gql` via Hasura, federating ClickHouse + YugabyteDB + CouchDB
- Route matrix: `/data` → CouchDB, `/gql` → Hasura, `/api/v1/container` → KNative, high-load ingest → Kafka/Pulsar
- SPEK (Spegel) DaemonSet mesh + Rook-Ceph storage engine at bottom layer
- Unified Data Layer concept: all processors route outputs to shared ClickHouse + YugabyteDB sinks
- AuthN flow: Envoy Gateway → Casdoor (JWT), AuthZ: Envoy Gateway → Casbin (PERM tuple)
- Backend databases: CouchDB (doc), Hasura (GraphQL fed), KNative (functions), Kafka/Pulsar, KeyDB cache, ArcadeDB (graph), SpinKube

### Coverage Status: PARTIAL

**Gaps:**
- ArcadeDB shown in architecture diagram (as graph DB alongside KeyDB cache at `/api` path) — not in PRD
- Route `/api/v1/container` mapped to KNative functions — PRD uses `/api/*` generic route (minor mismatch, but functional coverage is equivalent)
- Hasura federation as "unified data layer" bridging ClickHouse + YugabyteDB + CouchDB is in PRD but deferred (MVP out of scope for full federation — FR-16 says deployed but full federation deferred to v2)

---

## Document: SP-4 — Architecture diagram with observability (VictoriaMetrics).md

### Key Points
- Observability directory structure under `gitops-infra/platform/observability/`:
  - `metrics/` (base/ with vmstorage, vminsert, vmselect + retention.yaml)
  - `collectors/` (vmagent/, vmlog/, otel/)
  - `alertmanager/`
  - `grafana/`
- Clean separation: metrics/ for storage configuration, collectors/ for data discovery rules
- 3-pillar pipeline: traces (OTLP/gRPC) → otel, logs (stdout) → vmlog, metrics (scrape) → vmagent → vmstorage
- AlertManager → Chat/Ops Alerts notifications
- Grafana queries metrics directly from vmstorage
- Upgrade/security patches for collectors decoupled from core datastore via Kargo/ArgoCD

### Coverage Status: COVERED

---

## Document: SP-5 — Shipped offline.md

### Key Points
- "Seeding Appliance" concept: rugged USB/NAS/bootstrap laptop carrying all dependencies
- Structured offline packaging layout: 1-operating-systems/, 2-tofu-registry/, 3-helm-charts/, 4-oci-registry-dump/
- Fetch commands: `helm dependency build`, `docker pull/save`, `tofu providers mirror`
- OpenTofu local filesystem mirror via `.tofurc`
- Three-step bootstrap: (1) Load OS images to QEMU/libvirt storage pool, (2) Load core tars to Harbor, (3) Deploy manifests via ArgoCD/Kargo
- Harbor seeded by `docker load` + `docker tag` + `docker push` loop
- ArgoCD ConfigMap overrides for offline Helm repo access (`helm.repositories` pointing to `private.lan`)
- Spegel as primary network shield for scale-up events
- Complete shipping checklist table (online extraction ↔ offline hydration mapping)
- Uses Ubuntu cloud images (not Talos — this doc predates the Talos switch)

### Coverage Status: PARTIAL

**Gaps:**
- Seeding Appliance concept (structured offline packaging on transport media) — PRD mentions air-gapped delivery via Harbor + Spegel + local Git mirror but doesn't specify the "seed appliance" workflow
- Concrete fetch commands (`helm dependency build`, `docker save`, `tofu providers mirror`) — PRD doesn't detail the offline packaging automation
- ArgoCD ConfigMap override for offline Helm repos — PRD doesn't specify this configuration detail
- References Ubuntu cloud images vs. Talos (outdated — superseded by SP-6 series)

---

## Document: SP-6-1 — Talos OS in Offline mode.md

### Key Points
- Talos OS replaces Ubuntu: immutable, ephemeral, minimal Linux for K8s only
- No SSH, no bash, no package manager — configured via YAML over mTLS gRPC API
- Dev/Staging: QEMU VMs via `talos-amd64.raw` disk image
- Production: Matchbox PXE-boot of bare-metal servers into Talos
- Offline: `talosctl images` to capture system container tars, seed Harbor as bootstrap mirror
- Spegel registry mirror config in Talos MachineConfig (`machine.registries.mirrors`, `machine.containerd.config.discard_unpacked_layers: false`)
- Talos firewall rules for Spegel P2P ports (5000-5002)
- GitOps repo layout: `environments/dev/talos-secrets.yaml`, `provisioning/tofu-libvirt-talos/` with controlplane.yaml.tmpl + worker.yaml.tmpl
- Talos lifecycle: OpenTofu boots raw VM → injects machine config YAML → K8s cluster forms → ArgoCD deploys Cilium/Rook/Spegel → Kargo launches workloads
- Talos minimizes resource contention — no competing background processes at 50K+ RPS

### Coverage Status: COVERED

---

## Document: SP-6-2 — Talos and OpenTofu provisioning libvirt with offline mode (cache).md

### Key Points
- Two cache layers: offline OpenTofu provider plugins + Talos container/image cache
- `.tofurc` with `plugin_cache_dir` and `provider_installation` filesystem_mirror block
- `tofu providers mirror` command to download libvirt provider plugin
- Talos offline ISO creation: `talosctl image cache --with-kubernetes`
- Option A: Custom ISO with built-in cache; Option B: Image Mount Sequence (secondary ISO mapped as disk)
- Strict network isolation in libvirt: `network_name = "your-offline-libvirt-network"` to guarantee no external outbound calls

### Coverage Status: DEFERRED

**Detail:** PRD mentions offline/air-gapped delivery at high level (FR-30→32, FR-22) but defers production PXE/Matchbox bootstrapping (Out of Scope for MVP: "MVP uses `talosctl cluster create` (QEMU backend) only"). The detailed Talos offline ISO caching mechanics are implementation details for v2+ production deployment.

---

## Document: SP-6-3 — Talos and OpenTofu — Ceph disk connected to VMs.md

### Key Points
- Ceph RBD disk attached directly to QEMU VMs via libvirt (bypasses host mounts)
- `libvirt_volume` with `pool = "rbd"`, `format = "raw"`, `source = "rbd/talos-ceph-data-disk"`
- `libvirt_pool` resource for Ceph RBD pool with monitor hosts, auth, and secret config
- Talos post-boot: discovers `/dev/sdb` as SCSI; `machine.disks` partition + mount in Talos MachineConfig for `machine.containerd.root` or etcd storage
- Alternative to Rook-Ceph: Longhorn mentioned as potential consumer

### Coverage Status: DEFERRED

**Detail:** This describes a Ceph-external-to-VM approach (libvirt attaches Ceph RBD directly). PRD uses Rook-Ceph (in-cluster OSDs on raw local disks). The PRD's Rook-Ceph approach (FR-24, SP-6-4) is different — it uses raw secondary libvirt disks discovered by Rook inside the K8s cluster, not directly attached Ceph volumes. This doc covers an alternative topology that was not adopted.

---

## Document: SP-6-4 — Talos and OpenTofu — use Rook-Ceph.md

### Key Points
- Raw unpartitioned secondary disks go to Rook-Ceph OSDs (Rook owns them for BlueStore formatting)
- OpenTofu: separate `libvirt_volume` for boot (qcow2) vs. Ceph OSD (raw, 100GB)
- Talos MachineConfig: `machine.kernel.modules: [{name: "rbd"}]`, `machine.kubelet.extraMounts` for `/var/lib/rook` and `/dev` (bind + rshared)
- Explicit NOT to list secondary disk under `machine.disks` — Talos must ignore it for Rook
- Offline Rook-Ceph Helm install: `helm pull → transfer .tgz → helm install` with local registry override
- `rook-values.yaml`: `kubeletDirPath: /var/lib/kubelet`, `csi.enableRbdDriver: true`, `csi.enableCephfsDriver: true`
- `CephCluster` spec: `useAllNodes: true`, `useAllDevices: true`
- Worker nodes need 4-8GB RAM and 4 vCPU minimum for Ceph OSDs

### Coverage Status: COVERED

---

## Document: SP-6-5 — Talos bootstrapped without kube-proxy, using Cilium CNI.md

### Key Points
- Talos MachineConfig: `cluster.network.cni.name: none`, `cluster.proxy.disabled: true`
- Cilium offline images: quay.io/cilium/cilium, operator-generic, cilium-envoy (v1.17.0)
- Cilium Helm values: `kubeProxyReplacement: true`, `k8sServiceHost: 127.0.0.1`, `k8sServicePort: 7445`
- Talos-specific Cilium CNI paths: `cni.binPath: /var/libexec/cni`, `cni.confPath: /etc/cni/net.d`, `cgroupsPath: /run/current-system/cgroup`
- Verification: `kubectl exec ds/cilium -- cilium status --compact` → `KubeProxyReplacement: True`

### Coverage Status: COVERED

---

## Document: SP-6-6 — Talos and OpenTofu — dev setup only.md

### Key Points
- Dev-specific OpenTofu configuration: `libvirt` provider (0.8.3) + `talos` provider (0.7.0)
- `libvirt_network` NAT mode with `10.10.10.0/24`, DHCP enabled
- 3 volumes per node: OS (20GB qcow2) + Ceph (50GB raw) — 3 nodes
- `talos_machine_secrets`, `talos_machine_configuration` with `config_patches` for rbd module, kubelet mounts, CNI=none, proxy disabled
- `libvirt_domain` nodes: 6GB RAM, 2 vCPU, 3 disks (Talos ISO + OS + Ceph raw)
- Dev Cilium values: `kubeProxyReplacement: true`, `k8sServiceHost: 10.10.10.10` (matches OpenTofu cluster endpoint), `k8sServicePort: 7445`
- Dev Rook-Ceph values: `useAllNodes: true`, `useAllDevices: true`
- Resource sizing: dev needs 3 nodes × (6GB RAM + 2 vCPU + 20GB OS + 50GB Ceph)

### Coverage Status: COVERED

---

## Document: SP-7 — Pulsar Function.md

### Key Points
- Java Pulsar Function for telemetry transformation (stateless: JSON parse → field-map → emit)
- Function processes via `pulsar-admin functions create` with `--parallelism 8`
- Source topic `persistent://public/default/raw-events` needs ≥ 8 partitions
- Output topic `persistent://public/default/processed-events` feeds ClickHouse JDBC Sink
- ClickHouse JDBC Sink: `batchSize: 25000`, `batchTimeMs: 500`, `useTransactions: false`, 4 parallel sink instances
- At 50K RPS with 4 sink instances × 25K batch × 500ms flush = ~2 bulk inserts/second/instance → fits ClickHouse columnar insertion profile
- Memory: each sink instance holds 25K records in memory before flush; Pulsar worker nodes need sufficient heap (`MaxDirectMemorySize`, `Xmx`)
- Dead Letter Queue for failed records (function returns null on error → producer can route to DLQ)
- ClickHouse table must use MergeTree/ReplacingMergeTree with `ORDER BY (device_type, processed_timestamp)`
- Schema registry open question: JSON bytes assumed (Avro/Protobuf not specified)

### Coverage Status: COVERED

---

## Summary

| Status       | Count |
|-------------|-------|
| COVERED     | 10    |
| PARTIAL     | 2     |
| MISSING     | 0     |
| DEFERRED    | 2     |

**Top gaps:**

1. **ArcadeDB (Graph Database)** — Documented in SP-1, SP-2, and SP-3 architecture diagram as a core database alongside CouchDB, YugabyteDB, and KeyDB. Completely absent from the PRD (not mentioned in any feature, glossary entry, or out-of-scope section). This is a MISSING component.

2. **Staging environment provisioning** — PRD defines dev (QEMU via `talosctl cluster create`) and alludes to production but does not specify the staging environment provisioning mechanism. SP-1 defines staging as remote OpenTofu over SSH/libvirt RPC. This gap affects the completeness of the environment tier matrix.

3. **Seeding Appliance / offline packaging workflow** — PRD covers air-gapped delivery at the component level (Harbor, Spegel, local Git mirror) but lacks the "seeding appliance" concept and the concrete offline packaging automation workflow (`tofu providers mirror`, `helm dependency build`, `docker save` loop, ArgoCD ConfigMap overrides for offline Helm) that SP-5 defines.
