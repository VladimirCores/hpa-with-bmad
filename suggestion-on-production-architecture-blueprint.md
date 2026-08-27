# Suggestion: Production Architecture & Provisioning Blueprint

This document acts as a comprehensive reference guide for transitioning the High Performance Distributed Cluster (HPDC) from local development/prototyping setups to a fully automated, production-grade, highly available, and security-isolated deployment. It consolidates our project architectural review, a strict 12-Factor App compliance audit, physical/virtual hardware sizing matrices, and a declarative three-layer provisioning and integration blueprint.

---

## 1. Executive Architectural Evaluation

The current HPDC monorepo exhibits an exceptionally mature, production-ready, security-first baseline. By shifting local development provisioning to **Talos OS running under QEMU (using libvirt)**, the codebase successfully maintains absolute architectural alignment (parity) with production infrastructure constraints.

### Key Architectural Strengths:
1. **Air-Gapped Delivery Discipline:** Banning upstream container registry fallbacks via `skipFallback` and enforcing container image resolution solely via the local registry cache (`10.6.0.1:5000`) is a model security implementation.
2. **CGI-based Smart Git Mirroring:** The inclusion of an on-demand, CGI-backed smart HTTP Git server (`http://10.6.0.1:9418/with-bmad.git`) resolves classical Go-Git rendering constraints in ArgoCD, enabling declarative GitOps to run natively inside highly locked-down networks.
3. **Host-Side Manifest Compilation:** Pre-building Kustomize overlays host-side using `--load-restrictor LoadRestrictionsNone` and committing flat manifests under `rendered/dev.yaml` bypasses typical ArgoCD container load constraints while maintaining full GitOps declarativity.
4. **Idempotence & Strict Automation:** Python 3 scripts structured with standard flags (`--check`, `--dry-run`, `--apply`) enforce system states cleanly without the fragility of complex shell scripts.
5. **Low-Level Socket Workarounds:** Creating symbolic links (e.g., `talos-state`) to keep UNIX domain sockets below the 108-character limit demonstrates excellent system-level engineering depth.

---

## 2. 12-Factor App Compliance Audit

The HPDC platform translates traditional SaaS-focused 12-Factor guidelines to substrate-level infrastructure and stream processing topologies:

| Factor | Compliance Status | Implementation Details in HPDC |
| :--- | :---: | :--- |
| **I. Codebase** | **Strict** | One single monorepo containing all platform setups, overlays, scripts, and tests. Different environments (dev, staging, prod) are managed via dedicated Kustomize overlays. |
| **II. Dependencies** | **Strict** | Images are strictly pinned using multi-arch digests and cached in the local offline registry. Host-side tools (`talosctl`, `kustomize`) are audited and validated deterministically in python scripts. |
| **III. Config** | **Strict** | Banned hardcoded domains, IPs, and ports in scripts. Centralized in a local `.env` file (copied from `.env.example`) and injected dynamically into runtime processes and containers. |
| **IV. Backing Services** | **Strict** | CouchDB, YugabyteDB, ClickHouse, KeyDB, Pulsar, and Kafka are treated as attached network resources. Swapping from local mocks to cloud clusters requires only a `.env` variable change. |
| **V. Build, Release, Run** | **Strict** | Compiles immutable container images in Harbor (Build), combines them with rendered overlays and secrets in ArgoCD (Release), and executes them in Kubernetes (Run). |
| **VI. Processes** | **Strict** | Serverless-first runtimes (KNative for scaling-to-zero, SpinKube WASM for stateless streams, Pulsar Functions) ensure application nodes remain fully stateless and easily replaceable. |
| **VII. Port Binding** | **Strict** | Private backing services export ports internally, while the Envoy Gateway acts as the exclusive edge boundary mapping client endpoints (`/data`, `/api`, `/gql`, `/telemetry`) to private ports. |
| **VIII. Concurrency** | **Strict** | Handled natively via KNative scaling, Spin WASM near-instant execution, and Pulsar/Kafka stream partitioning which maps incoming sensor events into parallel processing lines. |
| **IX. Disposability** | **Strict** | WASM container starts occur in sub-milliseconds. Microservices are designed to tolerate sudden node failures by relying on queue-based buffers. Teardown routines cleanly wipe cluster resources. |
| **X. Dev/Prod Parity** | **Strict** | Achieved through nested virtualization under QEMU. Exposing raw block devices (`/dev/vdb`) allows developers to run the exact same **Rook-Ceph** storage provider locally as in production. |
| **XI. Logs** | **Strict** | Standard output (`stdout`/`stderr`) streams are automatically collected, buffered, and aggregated by the OpenTelemetry Collector and VictoriaMetrics VMLogs. |
| **XII. Admin Processes** | **Strict** | Database migrations, caching preloads, and system validations are written as isolated Python scripts that run with the exact same variables and configurations as application containers. |

---

## 3. Hardware Sizing Matrices

### A. Local Developer Workstation Requirements
Because the local environment simulates a full Kubernetes control plane, three worker nodes, local registry caches, and a smart HTTP mirror via QEMU VMs, the physical workstation must be a high-performance system.

* **Allocated Cluster Sizing:**
  * Control Plane (1 Node): 2 vCPUs, **6,144 MB RAM**
  * Workers (3 Nodes): 1 vCPU, **4,096 MB RAM** per worker *(12 GB total)*
  * Virtual Disk Space: ~70 GiB *(including raw virtual disks `/dev/vdb` on workers for Ceph OSD)*
* **Physical Workstation Recommendations:**
  * **CPU:** 8 Cores / 16 Threads (Minimum) | **12+ Cores / 24+ Threads** (Recommended, e.g., AMD Ryzen 9 / Intel i9)
  * **RAM:** **32 GB DDR4/DDR5** (Minimum) | **64 GB DDR5** (Recommended, leaving ample memory for IDEs, browsers, and host tools)
  * **Storage:** **256 GB Free SSD Space** (Minimum) | **512 GB+ High-Speed PCIe Gen4 NVMe SSD** (Recommended, as the local docker/registry image directory takes 30-50 GB of cached files)
  * **Host Operating System:** Linux (Fedora/Ubuntu preferred) with active **KVM** virtualization enabled in BIOS and kernel (`/dev/kvm`).

---

### B. Production Cluster Hardware Requirements (HA Setup)
Production sizing shifts the architecture to dedicated bare-metal nodes or high-performance hypervisor VMs (Proxmox/ESXi) with dedicated storage networks. It uses a **Hyperconverged HA Topology** (3 Control Planes + 3 hyperconverged Worker/Storage nodes):

```
┌────────────────────────────────────────────────────────┐
│               MANAGED 10G/25G SWITCH                   │
│   (Jumbo Frames Enabled, MTU 9000, Separated VLANs)    │
└───────┬──────────┬──────────┬──────────┬──────────┬────┘
        │          │          │          │          │
 ┌──────▼───┐┌─────▼────┐┌────▼─────┐┌───▼────┐┌────▼───┐
 │ Control  ││ Control  ││ Control  ││ Worker ││ Worker │  ... (3 Workers Total)
 │ Plane 1  ││ Plane 2  ││ Plane 3  ││ Node 1 ││ Node 2 │
 └──────────┘└──────────┘└──────────┘└────────┘└────────┘
```

#### 1. Control Plane Pool (3 Nodes - Dedicated for HA/etcd)
* **Purpose:** Serves etcd quorum, Kubernetes API servers, Kargo, and ArgoCD core.
* **CPU:** **4 Physical Cores** per node (High clock-speed).
* **RAM:** **16 GB ECC RAM** per node.
* **Storage:** **2 x 240 GB Enterprise SSDs (SATA or NVMe, Hardware/Software RAID-1)**.
  * *Critical Note:* etcd requires extremely low write-latency. Disk SSD write endurance (DWPD) must be high to prevent latency spikes during high-load API events.

#### 2. Worker & Storage Pool (3 Hyperconverged Nodes - Minimum)
* **Purpose:** Runs Envoy Gateway, Pulsar/Kafka event brokers, Rook-Ceph OSDs, ClickHouse, YugabyteDB, and serverless compute nodes.
* **CPU:** **16 to 32 Physical Cores** per node (e.g., AMD EPYC or Intel Xeon).
* **RAM:** **64 GB to 128 GB ECC RAM** per node.
  * *Critical Sizing Reason:* Backing databases (ClickHouse, YugabyteDB) and Java-based brokers (Pulsar Bookies) require massive memory buffers to handle high-RPS streams safely.
* **Resilient Data Storage (Rook-Ceph OSDs):**
  * **2 x 1.92 TB Enterprise-grade U.2/U.3 NVMe SSDs** per worker node (Direct attachment, NO hardware RAID).
  * *Critical Sizing Reason:* Ceph handles replicas natively at the cluster layer. Standardizing on enterprise-grade SSDs is mandatory because consumer-grade drives will experience immediate thermal and write-wear failures under database workloads.
* **Network Interfaces:** **Dual-port 10 GbE or 25 GbE SFP+** per node (configured with LACP or Active-Backup bonding).
  * *Critical Sizing Reason:* Rook-Ceph demands high bandwidth during node replication or data-balancing. Keeping cluster backend storage traffic on a separate VLAN/physical interface from client-facing ingress endpoints is a core production constraint.

---

## 4. Production Orchestration Blueprint (Connecting the System)

To orchestrate these physical/virtual resources dynamically into a single, cohesive, self-healing system, you implement a three-layer provisioning and GitOps pipeline.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        3. APPLICATION & EVENT LAYER                    │
│    Hasura GQL ←── Envoy Ingress ──→ Event Mesh (Pulsar/Kafka) ──→ MCP   │
├────────────────────────────────────────────────────────────────────────┤
│                          2. GITOPS SUBSTRATE LAYER                     │
│    Argo CD App-of-Apps ←── [ Cilium eBPF | Rook-Ceph | Infisical ]     │
├────────────────────────────────────────────────────────────────────────┤
│                        1. DYNAMIC PROVISIONING LAYER                   │
│    OpenTofu (Terraform) ──→ Virtual/Physical Hardware ──→ Talos OS    │
└────────────────────────────────────────────────────────────────────────┘
```

### Layer 1: Dynamic Substrate Provisioning (OpenTofu + Talos)
1. **Infrastructure as Code (IaC):** Write **OpenTofu** manifests detailing VMs, physical disk maps, network configurations, and VLAN tagging.
2. **Talos Configuration Generation:** Use the Terraform Talos provider (`siderolabs/talos`) to generate cryptographically signed machine configurations (`controlplane.yaml` and `worker.yaml`).
3. **Automated Bootstrapping:**
   * Nodes boot via PXE network booting or an immutable ISO template.
   * OpenTofu injects the generated machine config through the Talos API (port `50001`).
   * Talos automatically configures interfaces, disk storage, and launches `etcd`.
   * OpenTofu securely retrieves the generated `kubeconfig` and passes it to the GitOps bootstrapper.

### Layer 2: GitOps Substrate Delivery (ArgoCD Wave Orchestration)
Once the Kubernetes API is reachable, OpenTofu installs a lightweight **Argo CD** instance. From that point, Argo CD reads from the Git repository and coordinates the deployment via **Sync Waves** to resolve dependencies dynamically:

* **Wave -2 (Core CRDs):** Applies Envoy Gateway CRDs, KNative CRDs, Cert-Manager CRDs, and custom HPDC schemas.
* **Wave -1 (Network & Secrets):** Installs **Cilium CNI** (with kube-proxy-replacement mode enabled for eBPF routing) and **Infisical Secrets Operator** (which pulls DB passwords and API keys from a secure Infisical server and injects them as native Kubernetes secrets).
* **Wave 0 (Rook-Ceph Cluster):** Declares Rook-Ceph OSDs. Ceph scans the secondary NVMe disks `/dev/vdb` mapped in Layer 1, initializes storage pools, and spins up persistent storage layers.
* **Wave 1 (Gateway & Auth):** Brings up **Envoy Gateway** and the **Casdoor** authentication framework.
* **Wave 2 (Attached Services):** Spawns **YugabyteDB**, **ClickHouse**, **CouchDB**, **KeyDB**, and the **Pulsar/Kafka** message brokers, attaching them to Ceph block storage volumes.
* **Wave 3 (Compute, Observability & UI):** Deploys KNative (scale-to-zero pod controllers), VictoriaMetrics, and the Backstage developer portal.

### Layer 3: System-Wide Integration (Unified API, Federation, & Event Mesh)
To bind all decoupled services into a single, cohesive logical system, three architectural components are connected at the application level:

1. **Hasura Data Federation Hub (`/gql` Ingress):**
   * Rather than microservices querying multiple separate databases directly, all primary persistent databases (YugabyteDB, ClickHouse, CouchDB) register their schemas with **Hasura GraphQL Engine**.
   * Hasura compiles these systems into a unified GraphQL schema exposed over a single route (`/gql`). Client tools, dashboards, and AI agents write standard GraphQL queries that join records across ClickHouse metrics and CouchDB documents dynamically.
2. **Envoy Gateway Edge Boundary:**
   * Envoy functions as the exclusive gateway proxy. It terminates TLS (using Cert-Manager), applies Casdoor JWT authorization policies on `/gql` or `/api/*`, applies API-Key authorization on stream endpoints, and routes client connections securely to the private backend cluster IP.
3. **Pulsar-to-Kafka Telemetry Event Pipeline:**
   * High-RPS telemetry sensor data binding to port `1884` (MQTT) or `/telemetry/*` (gRPC/HTTP) enters the high-throughput **Pulsar topic mesh**.
   * **Pulsar Functions** process, filter, and normalize the telemetry.
   * If anomalous metrics or system threshold failures are detected, they are published to the **Kafka Alert Stream**.
   * A stateless consumer process listens to the alert stream, updates persistent databases (YugabyteDB), and triggers automated remediation tasks or alerts human operators via the UI.
4. **Model Context Protocol (MCP) Agent Engine:**
   * AI agents interface with the unified system through the **MCP Tool Registry**. 
   * Security policies on Envoy Gateway and authentication parameters inside Infisical ensure that AI agent queries and actions are strictly audited and authenticated.

---

## 5. Client Multi-Tenancy & Access Isolation

When multiple clients share the same physical clusters or regional infrastructure, isolation is enforced at the Gateway, IAM, and Database layers:

1. **Sub-Domain Routing Segregation (Envoy Gateway):**
   Envoy Gateway dynamically binds unique sub-domains for each client (e.g., `client-a.hpdc.io`, `client-b.hpdc.io`).
2. **Central Identity Federation (Casdoor JWT):**
   A unified or regional Casdoor instance manages OAuth/JWT credentials. Every request passing through Envoy must contain a JWT signed by Casdoor indicating the client's distinct tenant-id.
3. **RBAC/ABAC Gatekeeping (Casbin):**
   Casbin runs as an external authz filter on Envoy. It intercepts routing and parses the JWT token's client organization claim, dynamically blocking Client A from ever invoking a route, event stream (`/events/*`), or database backend belonging to Client B.
4. **Data Isolation (Hasura + Multi-Tenant DBs):**
   * **Dedicated Database Namespaces:** Separate client workloads are deployed to separate Kubernetes namespaces utilizing dedicated CouchDB, YugabyteDB, or ClickHouse schemas.
   * **Hasura Federation Roles:** Hasura acts as the central federation endpoint, utilizing **Row-Level Security (RLS)**. It parses the incoming Casdoor tenant-id JWT claim and dynamically rewrites SQL/GraphQL queries, ensuring a tenant's query can only fetch database rows matching their specific tenant-id.

---

## 6. Dynamic Multi-Region & Multi-Tenant Scaling Blueprint

To scale the HPDC platform dynamically across multiple regions—allowing cluster instances (spokes) to be added, resized, or removed on-demand as clients register or leave—you must transition to a **Declarative Multi-Cluster Management Plane**.

### A. The Hub-and-Spoke Topology

The network and deployment control flows are separated into two distinct roles:
1. **The Hub Cluster (Management Plane):**
   * A highly resilient, statically provisioned cluster in a core region.
   * Runs **Backstage** (user portal), **Kargo** (delivery promoter), **Argo CD** (fleet reconciler), **Cluster API (CAPI)** controllers, and **Infisical** (global secrets management).
2. **The Spoke Clusters (Workload Planes):**
   * Dynamically created, scaled, or destroyed cluster footprints.
   * Represent either a dedicated physical region (e.g., EU-West, US-East) or a dedicated single-tenant client environment.

```
                         ┌─────────────────────────────┐
                         │   HUB CLUSTER (MANAGEMENT)  │
                         │ [CAPI] [ArgoCD] [Backstage] │
                         └──────────────┬──────────────┘
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             │ (Dynamic CAPI Prov)      │ (Dynamic CAPI Prov)      │ (Dynamic CAPI Prov)
             ▼                          ▼                          ▼
┌────────────────────────┐ ┌────────────────────────┐ ┌────────────────────────┐
│     SPOKE CLUSTER A    │ │     SPOKE CLUSTER B    │ │     SPOKE CLUSTER C    │
│    (Region: EU-West)   │ │    (Region: US-East)   │ │    (Region: AP-South)  │
│ [Cilium] [Rook] [Apps] │ │ [Cilium] [Rook] [Apps] │ │ [Cilium] [Rook] [Apps] │
└────────────────────────┘ └────────────────────────┘ └────────────────────────┘
```

---

### B. Dynamic Infrastructure Provisioning via Cluster API (CAPI)

To avoid manual hypervisor configuration when adding regions or client clusters, use **Cluster API (CAPI)**. CAPI extends Kubernetes, treating entire cluster resources as declarative YAML manifests managed by the Hub cluster.

1. **Declarative Cluster Definitions:** 
   Define cluster footprints, machine sizes, and Talos OS nodes as custom resources on the Hub cluster:
   ```yaml
   apiVersion: cluster.x-k8s.io/v1beta1
   kind: Cluster
   metadata:
     name: hpdc-client-delta-us-east
     namespace: default
   spec:
     clusterNetwork:
       pods:
         cidrBlocks: ["10.244.0.0/16"]
     infrastructureRef:
       apiVersion: infrastructure.cluster.x-k8s.io/v1alpha3
       kind: TalosCluster
       name: hpdc-client-delta-infra
     controlPlaneRef:
       apiVersion: controlplane.cluster.x-k8s.io/v1alpha3
       kind: TalosControlPlane
       name: hpdc-client-delta-cp
   ```
2. **On-Demand Lifecycle:**
   * **Add a Cluster:** Commit a new CAPI cluster manifest to the GitOps control repository. The Hub cluster's CAPI controllers detect it and call the cloud provider or bare-metal hypervisor APIs dynamically to boot new Talos VMs.
   * **Scale a Cluster:** Edit the `MachineDeployment` replica count from `3` to `10`. CAPI dynamically provisions 7 additional worker VMs, installs Talos, and joins them to the cluster automatically.
   * **Remove a Cluster:** Run `kubectl delete cluster hpdc-client-delta-us-east`. CAPI coordinates the graceful draining of workloads, terminates the VM nodes, and reclaims all Ceph storage volumes.

---

### C. Automated GitOps Onboarding via ArgoCD ApplicationSets

To automatically deploy the entire HPDC substrate (Cilium, Ceph, Kafka, databases, gateway) onto a newly created spoke cluster, use **Argo CD ApplicationSets** combined with the **Git Generator**:

1. **ApplicationSet Cluster Controller:**
   Configure an ApplicationSet on the Hub cluster that continuously scans the Git repository's `gitops/clusters/` directory.
2. **The Dynamic Sync Loop:**
   * When a new sub-folder (e.g., `gitops/clusters/hpdc-client-delta/`) containing cluster metadata is committed, the ApplicationSet controller automatically generates a suite of 19 Wave-Ordered applications tailored for that specific cluster.
   * Argo CD connects to the new cluster's API endpoint, bootstraps Cilium, mounts Ceph OSDs on the new disks, and provisions the target local databases and telemetry pipelines without any manual operator scripts.

---

### D. Multi-Region Networking via Cilium ClusterMesh

To connect dynamically provisioned regions and client spokes into a unified logical system, use **Cilium ClusterMesh** routed over an on-demand encrypted private overlay:

1. **Dynamic Mesh Connections:**
   As spoke clusters boot, the Hub's CAPI pipeline automatically establishes secure, encrypted **WireGuard VPN tunnels** between the Hub and the new Spoke cluster.
2. **Cilium ClusterMesh Joining:**
   Cilium’s ClusterMesh controller automatically exchanges etcd metadata between clusters. It assigns non-overlapping pod CIDR blocks to each cluster and establishes cross-cluster service routing:
   * **Global Services:** Define services with `io.cilium/global-service: "true"` annotations. Envoy Ingress can now transparently distribute traffic across multiple regions or automatically fail over to a healthy region if a local database cluster experiences an outage.
   * **Decentralized sovereignty:** Regional event brokers (Pulsar) stream metrics to local ClickHouse nodes to comply with regional sovereignty requirements, while central analytical tools on the Hub execute cross-cluster queries via Hasura over the secure ClusterMesh.

---

### E. Developer Portal Self-Service (The Golden Path)

To coordinate this entire ecosystem—from client request to fully running regional cluster—you wrap the workflow in a **Backstage Golden Path Template**:

1. **Onboard Client Wizard:**
   A developer or operator accesses the Backstage Portal and opens the **"Onboard New Client"** template.
2. **Input Parameters:**
   The wizard prompts for: Client Name, Target Cloud Region, Storage capacity, and expected telemetry RPS limit.
3. **Automated Manifest Commitment:**
   Upon submission, Backstage executes its Scaffolder engine to:
   * Write OpenTofu/CAPI definitions for the new spoke cluster into `gitops-infra/`.
   * Create the GitOps ApplicationSet config directories in `gitops-workloads/`.
   * Register the new client credentials in Casdoor and define authorization policies in Casbin.
   * Commit the changes to Git.
4. **Autonomous Convergence:**
   CAPI provisions the VMs $\rightarrow$ ArgoCD ApplicationSets detect the directories and apply the 19 Sync Waves $\rightarrow$ Cilium establishes WireGuard + ClusterMesh $\rightarrow$ The new client cluster reports **Healthy** in Backstage within minutes.

---

## 7. Local OpenTofu Provisioning Engine (Third Local Option)

To align local development environment delivery with staging/production paradigms, OpenTofu can be integrated as a third local developer provisioning option (alongside the legacy Docker and the CLI QEMU wrappers).

### **Strict Offline Constraints (Dynamic Air-Gap):**
* **Local Talos Base Image:** The OpenTofu LibVirt resource `libvirt_volume.talos_os` must point to a localized, pre-cached Talos OS `.qcow2` virtual image stored under `resources/` (e.g. via `var.talos_base_image_path`), completely bypassing internet fetches.
* **Offline Mirror Config Patches:** To ensure all subsequent container pulls stay isolated inside the bridge, OpenTofu's `talos_machine_configuration` data resource must dynamically read and apply the localized registry mirror patch (`platform/talos/talos-offline-mirror-patch.yaml`) that binds containerd to the host's offline registry proxy (`10.6.0.1:5000`) with `skipFallback: true`.

### A. Directory Layout
To implement this, you introduce a new directory **`platform/provisioning/dev/`** to house the OpenTofu code:
```
platform/provisioning/dev/
├── providers.tf        # Configures LibVirt and Talos providers
├── variables.tf        # Maps local sizing (CPUs, RAM, Subnet) matching .env
├── main.tf             # Provisions network, storage volumes, and VMs
├── talos.tf            # Generates Talos configs and bootstraps the nodes
└── outputs.tf          # Emits kubeconfig and talosconfig to resources/
```

### B. Core Provider Configuration (`providers.tf`)
```hcl
terraform {
  required_version = ">= 1.8.0"
  required_providers {
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = "~> 0.7.6"
    }
    talos = {
      source  = "siderolabs/talos"
      version = "~> 0.5.0"
    }
  }
}

provider "libvirt" {
  uri = "qemu:///system"
}
```

### C. Declarative Machine Provisioning (`main.tf`)
This configuration establishes a local Nat-routed libvirt network matching your subnets and attaches dual volumes to worker VMs (OS Boot + Raw block data disk for Ceph OSD):
```hcl
resource "libvirt_network" "hpa_net" {
  name      = "hpa-tofu-net"
  mode      = "nat"
  domain    = "hpdc.local"
  addresses = [var.subnet_cidr] # e.g. "10.6.0.0/24"
  dhcp {
    enabled = true
  }
}

resource "libvirt_volume" "talos_os" {
  count  = var.worker_count + 1
  name   = "talos-os-${count.index}.qcow2"
  pool   = "default"
  source = var.talos_base_image_path # Local offline base image path (e.g. resources/talos/talos.qcow2)
  format = "qcow2"
}

resource "libvirt_volume" "ceph_disk" {
  count  = var.worker_count
  name   = "ceph-data-${count.index}.raw"
  pool   = "default"
  size   = 10737418240 # 10 GiB
  format = "raw"
}

resource "libvirt_domain" "talos_node" {
  count      = var.worker_count + 1
  name       = count.index == 0 ? "hpdc-cp-0" : "hpdc-worker-${count.index - 1}"
  memory     = count.index == 0 ? var.memory_controlplane : var.memory_worker
  vcpu       = count.index == 0 ? var.cpus_controlplane : var.cpus_worker
  autostart  = true

  network_interface {
    network_id     = libvirt_network.hpa_net.id
    wait_for_lease = true
  }

  disk {
    volume_id = libvirt_volume.talos_os[count.index].id
  }

  dynamic "disk" {
    for_each = count.index > 0 ? [1] : []
    content {
      volume_id = libvirt_volume.ceph_disk[count.index - 1].id
    }
  }
}
```

### D. Talos Machine Configuration Injection (`talos.tf`)
The Talos Terraform provider generates the configs and bootstraps the cluster automatically, injecting the local offline mirror patch yaml to keep all operations 100% offline:
```hcl
resource "talos_machine_secrets" "secrets" {}

data "talos_machine_configuration" "cp" {
  cluster_name     = var.cluster_name
  cluster_endpoint = "https://${libvirt_domain.talos_node[0].network_interface[0].addresses[0]}:6443"
  machine_type     = "controlplane"
  machine_secrets  = talos_machine_secrets.secrets.machine_secrets
  config_patches = [
    file("${path.module}/../../talos/talos-offline-mirror-patch.yaml") # Inject local offline mirror configurations
  ]
}

resource "talos_machine_configuration_apply" "cp" {
  client_configuration        = talos_machine_secrets.secrets.client_configuration
  machine_configuration_input = data.talos_machine_configuration.cp.machine_configuration
  node                        = libvirt_domain.talos_node[0].network_interface[0].addresses[0]
}

resource "talos_machine_bootstrap" "bootstrap" {
  depends_on           = [talos_machine_configuration_apply.cp]
  client_configuration = talos_machine_secrets.secrets.client_configuration
  node                 = libvirt_domain.talos_node[0].network_interface[0].addresses[0]
}
```

### E. Python 3 Orchestrator Integration
To support this third option alongside the other two, `bootstrap_talos_dev.py` parser options are updated with `HPDC_PROVIDER=opentofu` as a third choice:

```python
# In scripts/gitops/bootstrap_talos_dev.py:

PROVIDER_DOCKER = "docker"
PROVIDER_QEMU = "qemu"
PROVIDER_OPENTOFU = "opentofu" # NEW THIRD OPTION

def main():
    parser.add_argument("--provider", default=os.getenv("HPDC_PROVIDER", "qemu"), 
                        choices=["docker", "qemu", "opentofu"])
    args = parser.parse_args()

    if args.provider == PROVIDER_DOCKER:
        bootstrap_docker_cluster(args)
    elif args.provider == PROVIDER_QEMU:
        bootstrap_qemu_cluster_cli(args) # Current CLI script implementation
    elif args.provider == PROVIDER_OPENTOFU:
        bootstrap_via_opentofu(args) # NEW OPENTOFU LOOP
```

The `bootstrap_via_opentofu(args)` function simply injects the `.env` variables into the environment as `TF_VAR_*` variables and executes `tofu init` and `tofu apply -auto-approve` inside `platform/provisioning/dev/` before copying out the kubeconfigs:

```python
def bootstrap_via_opentofu(args):
    # 1. Map .env configurations to TF variables
    tf_vars = {
        "TF_VAR_cluster_name": CLUSTER_NAME,
        "TF_VAR_worker_count": args.workers,
        "TF_VAR_memory_worker": args.memory_worker,
        "TF_VAR_memory_controlplane": args.memory_controlplane,
    }
    env = {**os.environ, **tf_vars}
    
    # 2. Execute declarative OpenTofu steps
    tofu_dir = ROOT / "platform" / "provisioning" / "dev"
    run(["tofu", "init"], env=env)
    run(["tofu", "apply", "-auto-approve"], env=env)
    
    # 3. Secure output configurations back into native locations
    extract_and_write_kubeconfigs(tofu_dir)
```

### F. Summary of Parity Alignment
Adding OpenTofu gives you a flawless progression matrix, bridging your development loops straight to staging and cloud production:

| Feature | Docker (Legacy) | QEMU (CLI) | OpenTofu (NEW) | Production (Spokes) |
| :--- | :--- | :--- | :--- | :--- |
| **VM Target** | Standard containers | Virtual Machine (Nested) | Virtual Machine (Nested) | Bare Metal / Enterprise Cloud |
| **Prov Engine** | `talosctl cluster` | `talosctl cluster qemu` | **OpenTofu CLI** | **OpenTofu / CAPI CLI** |
| **State Tracker** | None (Docker container) | Imperative Virsh polling | **TF State Graph (`.tfstate`)** | **Secure Remote TF State S3** |
| **IaC Code Parity**| Low | Medium | **High (Matches Prod)** | **High (Matches Prod)** |

---

## 8. Immediate Practical Next Steps

When resuming development from the `NEXT.md` status, keep this production blueprint in mind. The immediate progression remains focused on perfecting the developer VM loop:

1. **Verify QEMU-Talos Storage Parity:** Ensure the Rook-Ceph controller on the development cluster can successfully mount `/dev/vdb` on the workers and reach `HEALTH_OK`.
2. **Resolve Image Mirror Deficits (Story 11-5):** Compile and copy custom developer images (specifically `casbin/ext-authz` and `regional-hub-spa`) into the host-side registry copy directory under `~/.local/share/hpdc-registry/data`.
3. **Run the P0 Acceptance Harness (Story 11-4):** Run `pytest tests/atdd/ -v` once Envoy Gateway routing is reconciled, verifying route-level JWT and API key enforcement against the live QEMU cluster.
