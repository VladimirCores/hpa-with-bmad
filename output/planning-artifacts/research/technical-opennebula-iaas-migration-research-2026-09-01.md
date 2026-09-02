---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
workflowType: 'research'
lastStep: 4
research_type: 'technical'
research_topic: 'Migrating to OpenNebula as IaaS for Dev, Staging, and Production'
research_goals: 'Evaluate miniOne for dev, OpenChoreo integration, ArgoCD/Kargo promotion pipeline, alternatives to bare metal'
user_name: 'Master'
date: '2026-09-01'
web_research_enabled: true
source_verification: true
---

# Research Report: Technical

**Date:** 2026-09-01
**Author:** Master
**Research Type:** Technical

---

## Research Overview

This research evaluates OpenNebula as an IaaS platform to replace bare-metal provisioning for the High Performance Distributed Cluster (HPDC) project. The migration targets dev, staging, and production environments with a phased approach, using OpenNebula's miniOne for development, OpenChoreo as the Internal Developer Platform, and ArgoCD/Kargo for continuous promotion.

---

## Technical Research Scope Confirmation

**Research Topic:** Migrating to OpenNebula as IaaS for Dev, Staging, and Production
**Research Goals:** Evaluate miniOne for dev, OpenChoreo integration, ArgoCD/Kargo promotion pipeline, alternatives to bare metal

**Technical Research Scope:**

- Architecture Analysis - design patterns, frameworks, system architecture
- Implementation Approaches - development methodologies, coding patterns
- Technology Stack - languages, frameworks, tools, platforms
- Integration Patterns - APIs, protocols, interoperability
- Performance Considerations - scalability, optimization, patterns

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-09-01

---

## Technology Stack Analysis

### OpenNebula Core Components

_OpenNebula is a modular cloud management platform with the following core components:_

| Component | Description |
|-----------|-------------|
| `oned` | Core daemon managing nodes, virtual networks, storage, users, and VMs. Provides XML-RPC API. |
| Sunstone | Web UI for administrators and end users to manage cloud resources. |
| OneFlow | Multi-VM service orchestration with auto-scaling policies. |
| OneGate | Allows VMs to communicate with OpenNebula during bootstrap and runtime. |
| Scheduler | Modular resource allocation system with pluggable algorithms. |
| Monitoring | Dedicated daemon (`onemonitord`) for host/VM metrics collection. |

_Source: https://github.com/OpenNebula/one-docs/blob/one-7.2/content/getting_started/understand_opennebula/opennebula_concepts/opennebula_overview.md_

### miniOne Deployment Tool

_miniOne is OpenNebula's rapid installation tool for evaluation and small deployments:_

| Deployment Mode | Requirements | Use Case |
|-----------------|--------------|----------|
| Front-end only | 16 GiB RAM, 80 GiB disk | Management node only |
| Front-end + KVM | 32 GiB RAM, 80 GiB disk | Single-node dev cloud |
| Kubernetes | 64 GiB RAM, 120 GiB disk | K8s cluster workloads |
| AI Factory | 128 GiB RAM, 512 GiB disk, GPU | ML/AI workloads |

**Supported OS:** RHEL/AlmaLinux 9/10, Debian 12/13, Ubuntu 24.04/26.04, openSUSE 16.0, SLES 15.7

**Note:** miniOne is intended for evaluation. Production deployments should use OneDeploy or manual installation.

_Source: https://docs.opennebula.io/7.4/getting_started/install_opennebula/production/minione_frontend_install/_

### OneKS (OpenNebula Kubernetes Service)

_OneKS provides Elastic Kubernetes as a Service on OpenNebula:_

- **CNCF-certified** Kubernetes distribution based on RKE2
- Uses **CAPONE** (Cluster API provider for OpenNebula) for declarative lifecycle management
- Deploys as multi-VM appliance: master, VNF node, storage node, worker nodes
- Features: MetalLB load balancing, Multus/Cilium CNI, Longhorn storage
- Supports HA control plane and dynamic worker scaling

**K8s Cluster Components:**
- Seed VM (temporary bootstrap)
- Control Plane (master node)
- Virtual Router (network connectivity)
- Worker Nodes (compute workload)

_Source: https://docs.opennebula.io/7.4/platform_services/oneks/getting_started/overview/_

### OpenChoreo (CNCF Sandbox IDP)

_OpenChoreo is a modular Internal Developer Platform for Kubernetes:_

**Multi-Plane Architecture:**

| Plane | Purpose | Required |
|-------|---------|----------|
| Control Plane | Central management, API, UI | Yes |
| Data Plane | Application runtime | Yes |
| Workflow Plane | CI/CD workflows | No |
| Observability Plane | Logging and monitoring | No |
| Experience Plane | Developer portal (Backstage) | Yes |

**Default Modules:**
- API Gateway: KGateway (Kubernetes Gateway API compliant)
- CI: Argo Workflows
- GitOps: Flux CD
- Observability: OpenSearch

**Key Features:**
- Modular architecture with pluggable integrations
- Kubernetes-native CRDs for Platform and Developer APIs
- Backstage-powered developer portal
- Built-in AI agents for SRE, cost control, architecture
- Agent-ready interfaces (MCP + skills)

_Source: https://openchoreo.dev/docs/platform-engineer-guide/modules/overview/_
_Source: https://openchoreo.dev/docs/next/overview/architecture/_

### ArgoCD + Kargo Promotion Stack

_Kargo provides continuous promotion orchestration on top of Argo CD:_

| Component | Role |
|-----------|------|
| Argo CD | GitOps deployment/sync - watches Git repo and reconciles cluster state |
| Kargo | Promotion orchestration - decides what version goes to which environment and when |

**Kargo Core Concepts:**

- **Warehouse**: Subscribes to artifact sources (Git, image registries, Helm repos)
- **Freight**: Atomic promotion unit - bundles image tag + Git commit SHA + Helm version
- **Stage**: Represents an environment (dev/staging/prod) in a DAG pipeline
- **PromotionTask**: Reusable promotion step sequences with parameterized variables

**Promotion Flow:**
```
Warehouse → Freight → dev Stage → staging Stage → prod Stage
```

**Verification Features:**
- Implicit verification (Argo CD health checks)
- AnalysisTemplates (integration tests, Prometheus metrics, HTTP endpoints)
- Soak times (minimum duration before downstream promotion)
- Manual approval gates

_Source: https://docs.kargo.io/user-guide/how-to-guides/argo-cd-integration_
_Source: https://akuity.io/blog/how-kargo-fixes-gitops-with-promotion_

### Technology Adoption Trends

_Integration path for HPDC migration:_

```
OpenNebula (IaaS Layer)
  └─ OneKS (Kubernetes provisioning via CAPONE)
      └─ OpenChoreo (IDP - Control + Data + Workflow + Observability Planes)
          └─ ArgoCD + Kargo (GitOps + Continuous Promotion)
```

**Cost vs Bare Metal:**
- Bare metal: High upfront cost, long provisioning time, manual management
- OpenNebula miniOne: Rapid dev setup (<3 min), VM-based isolation, easy scaling
- Production: OneDeploy for automated production-ready deployment

**Scalability:**
- OpenNebula: Up to 2,500 servers, 10,000 VMs per instance
- Federated zones for larger deployments (largest: 16 DCs, 300,000 cores)
- OneKS: Dynamic worker scaling via elasticity rules

---

## Integration Patterns Analysis

### OpenNebula API Layer

_OpenNebula provides multiple API protocols for different use cases:_

| Protocol | Endpoint | Use Case | Performance |
|----------|----------|----------|-------------|
| XML-RPC | `http://one:2633/RPC2` | Legacy integration, broad client support | Text-based XML, higher overhead |
| gRPC | `one:2634` | High-performance, typed contracts | Binary Protobuf, lower latency |

**Client SDKs:**

| Language | Package | Protocol Support |
|----------|---------|------------------|
| Python | `pyone` (`pip install pyone`) | XML-RPC + gRPC |
| Go | `GOCA` (`github.com/OpenNebula/one/src/oca/go/src/goca`) | XML-RPC |
| Ruby | Built-in CLI | XML-RPC + gRPC |
| Java | OCA | XML-RPC |

**gRPC Configuration:**
```bash
# Environment variables
export ONE_XMLRPC="http://one:2633/RPC2"
export ONE_GRPC="one:2634"
export ONEAPI_PROTOCOL=grpc
```

_Source: https://docs.opennebula.io/7.4/product/integration_references/system_interfaces/python/_
_Source: https://docs.opennebula.io/devel/product/control_plane_configuration/large-scale_deployment/grpc/_

### CAPONE (Cluster API Provider for OpenNebula)

_CAPONE provides declarative Kubernetes cluster lifecycle management:_

**Integration Flow:**
```
Cluster API (CAPI) → CAPONE → OpenNebula XML-RPC/gRPC → VM Provisioning → K8s Bootstrap
```

**Required OpenNebula Resources:**
- Public Virtual Network (IPv4 + ETHER address ranges)
- Private Virtual Network (internal cluster communication)
- VM Templates (control plane, worker nodes)
- Image Datastore

**Network Requirements:**
- Public network: Two address ranges (IPv4 for IPs, ETHER for LoadBalancer MAC addresses)
- Private network: Complete internet isolation for internal K8s communication

_Source: https://github.com/OpenNebula/cluster-api-provider-opennebula_
_Source: https://github.com/OpenNebula/cluster-api-provider-opennebula/wiki/capi_install_

### OpenChoreo Plane-to-Plane Communication

_OpenChoreo uses agent-based communication with mTLS-secured WebSocket connections:_

**Connection Architecture:**
```
Control Plane (Cluster Gateway :8443)
    ↑ WebSocket (mTLS)
    │
    ├── Data Plane (Cluster Agent)
    ├── Workflow Plane (Cluster Agent)
    └── Observability Plane (Cluster Agent)
```

**Security Model:**
- **Server Trust**: Remote planes verify Control Plane CA certificate
- **Client Authentication**: Agents generate self-signed client certificates via cert-manager
- **Certificate Registration**: Agent CAs registered in DataPlane/WorkflowPlane/ObservabilityPlane CRDs

**Internal API (:8444):**
- Used by `openchoreo-api` and controller-manager
- Protected by separate internal CA (`cluster-gateway-internal-ca`)
- Proxies, execs, and streams logs into connected planes

**Key Parameters:**
```yaml
clusterAgent:
  serverUrl: "wss://cluster-gateway.openchoreo.example.com/ws"
  tls:
    enabled: true
    generateCerts: true
    serverCAConfigMap: cluster-gateway-ca
    caSecretName: ""  # Self-signed for multi-cluster
```

_Source: https://openchoreo.dev/docs/platform-engineer-guide/multi-cluster-connectivity/_
_Source: https://openchoreo.dev/docs/platform-engineer-guide/external-ca-tls-setup/_

### ArgoCD-Kargo Integration Pattern

_Kargo extends Argo CD with promotion orchestration:_

**Integration Mechanism:**
1. Kargo updates Argo CD `Application` resources via `argocd-update` promotion step
2. `Application` must be annotated with `kargo.akuity.io/authorized-stage`
3. Kargo triggers sync and waits for health check via `argocd-wait`

**Promotion Step Pattern:**
```yaml
steps:
  - uses: git-clone
    config:
      repoURL: ${{ vars.gitRepo }}
      checkout:
        - branch: main
          path: ./out
  - uses: helm-update-image
    config:
      path: ./out/values/values-${{ ctx.stage }}.yaml
      images:
        - image: ${{ vars.imageRepo }}
          key: image.tag
          value: Tag
  - uses: git-commit
    config:
      path: ./out
      messageFromSteps: [update-image]
  - uses: git-push
    config:
      path: ./out
  - uses: argocd-update
    config:
      apps:
        - name: my-app-${{ ctx.stage }}
  - uses: argocd-wait
    config:
      timeout: 10m
```

**RBAC Integration:**
- Stage-level role bindings for promotion permissions
- Manual approval gates for production
- Emergency bypass via direct Freight approval

_Source: https://docs.kargo.io/user-guide/how-to-guides/argo-cd-integration_

### Multi-Cluster Networking Pattern

_OpenChoreo supports flexible deployment topologies:_

**Topology Options:**

| Topology | Description | Use Case |
|----------|-------------|----------|
| Single Cluster | All planes co-located | Development, evaluation |
| Hybrid | CP + WP + OP co-located, remote DP | Common production |
| Multi-Region | Central CP, DPs across regions | Global deployments |

**Gateway Exposure:**
```yaml
# TLS passthrough via kgateway
apiVersion: gateway.networking.k8s.io/v1alpha2
kind: TLSRoute
metadata:
  name: cluster-gateway
spec:
  parentRefs:
    - name: kgateway
      sectionName: tls
  hostnames:
    - "cluster-gateway.openchoreo.example.com"
  rules:
    - backendRefs:
        - name: cluster-gateway-external
          port: 8443
```

**Observability in Multi-Cluster:**
- Telemetry collectors push to Observability Plane ingestion endpoints
- Observer API serves logs/metrics/traces to Experience Plane
- CORS configuration for cross-origin portal access

_Source: https://openchoreo.dev/docs/platform-engineer-guide/deployment-topology/_

### Integration Security Patterns

_Authentication and authorization across the stack:_

| Layer | Mechanism | Protocol |
|-------|-----------|----------|
| OpenNebula API | Session token (`oneadmin:password`) | XML-RPC/gRPC |
| OpenNebula CLI | `ONE_AUTH` file | XML-RPC/gRPC |
| OneKS K8s Cluster | kubeconfig (X.509 certs) | Kubernetes API |
| OpenChoreo API | OAuth2/OIDC (ThunderID) | HTTPS |
| OpenChoreo Planes | mTLS (cert-manager) | WebSocket |
| Kargo | RBAC + manual approval | Kubernetes API |

**Certificate Hierarchy:**
```
Control Plane CA
├── Gateway Server Cert
└── Agent Client Certs (self-signed per plane)
    ├── Data Plane Agent
    ├── Workflow Plane Agent
    └── Observability Plane Agent
```

---

## Architectural Patterns and Design

### Multi-Layer Platform Architecture

_The HPDC migration follows a four-layer architecture:_

```
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 4: Promotion Orchestration (Kargo + ArgoCD)                  │
│  - Warehouse → Freight → Stage DAG pipeline                        │
│  - Verification gates (AnalysisTemplates, soak times)              │
│  - Manual approval for production                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 3: Internal Developer Platform (OpenChoreo)                 │
│  - Control Plane: API, controllers, Backstage portal               │
│  - Data Plane: Application workloads                               │
│  - Workflow Plane: Argo Workflows (CI builds)                      │
│  - Observability Plane: Logs, metrics, traces                      │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 2: Kubernetes (OneKS via CAPONE)                            │
│  - RKE2 distribution                                               │
│  - Cluster API declarative lifecycle                               │
│  - HA control plane + dynamic worker scaling                       │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 1: IaaS (OpenNebula)                                        │
│  - KVM hypervisor                                                  │
│  - Virtual Networks (public + private)                             │
│  - Storage (Ceph, LVM, NFS)                                        │
│  - Sunstone UI + XML-RPC/gRPC API                                  │
└─────────────────────────────────────────────────────────────────────┘
```

_Source: https://docs.opennebula.io/7.4/platform_services/oneks/references/architecture/_

### Environment Promotion Pipeline Design

_Three-environment pipeline with OpenChoreo-native promotion model:_

**OpenChoreo's Promotion Model:**
- `ComponentRelease`: Immutable snapshot (ComponentType + Workload + Traits)
- `ReleaseBinding`: Binds ComponentRelease to Environment
- Promotion = new ReleaseBinding targeting different Environment (same immutable release)

**Kargo Extension for Multi-Stage Orchestration:**
```yaml
# Kargo Stage DAG
Warehouse (discovers new images)
  → dev Stage (auto-promote)
    → staging Stage (soak time + verification)
      → prod Stage (manual approval)
```

**Combined Flow:**
1. CI (Argo Workflows) builds image, creates Workload CR via API
2. Kargo Warehouse detects new image tag
3. Kargo updates Git repo with ReleaseBinding for dev
4. ArgoCD syncs dev environment
5. Verification passes → Kargo promotes to staging
6. Soak time + verification → manual approval for prod

_Source: https://openchoreo.dev/docs/platform-engineer-guide/gitops/automations/build-and-release-workflows/_

### Argo Workflows as OpenChoreo CI Engine

_OpenChoreo uses Argo Workflows as its default and only natively supported CI engine:_

**Workflow Architecture:**
```
Control Plane                          Workflow Plane
┌──────────────────┐                   ┌──────────────────────┐
│ Workflow CR       │ ──── render ──── │ Argo Workflow         │
│ (runTemplate)     │                   │ (ClusterWorkflowTemplates)
│                   │                   │                      │
│ WorkflowRun CR    │ ──── trigger ──── │ Workflow instance    │
└──────────────────┘                   └──────────────────────┘
```

**Three-Layer Workflow Design:**

| Layer | Resource | Owner | Purpose |
|-------|----------|-------|---------|
| Step | ClusterWorkflowTemplate | Platform Engineer | Reusable step logic (checkout, build, push) |
| Pipeline | Workflow (runTemplate) | Platform Engineer | Composes CWTs with CEL expressions |
| Instance | WorkflowRun | Developer | Triggers execution with parameters |

**Default CI Workflows:**
- `dockerfile-builder`: Dockerfile-based builds
- `google-cloud-buildpacks-builder`: Source-to-image (Go, Java, Node.js, Python)
- `react-gitops-release`: React/SPA with nginx
- `bulk-gitops-release`: Promote existing releases (no build)

_Source: https://openchoreo.dev/docs/platform-engineer-guide/workflows/creating-workflows/_

### OneKS Kubernetes Provisioning Architecture

_OneKS provides standardized K8s cluster provisioning on OpenNebula:_

**Cluster Topology Components:**
```
┌─────────────────────────────────────────────────────┐
│ OneKS K8s Cluster                                   │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐                │
│  │ Virtual Router│  │ Control Plane│                │
│  │ (public+priv) │  │ (RKE2 master)│                │
│  └──────┬───────┘  └──────┬───────┘                │
│         │                  │                        │
│         └────────┬─────────┘                        │
│                  │ Private Network                  │
│         ┌────────┴─────────┐                        │
│         │   Worker Nodes   │                        │
│         │  (node group 1)  │                        │
│         └──────────────────┘                        │
└─────────────────────────────────────────────────────┘
```

**Flavour Options:**
- `standalone`: Single-node control plane (dev/test)
- `ha`: Three-node HA control plane (production)

**Scaling Model:**
- Control plane: Fixed flavour (standalone or ha)
- Workers: Dynamic node groups with configurable count
- Scaling via OneKS API, Sunstone UI, or CLI

_Source: https://docs.opennebula.io/7.4/platform_services/oneks/getting_started/core_concepts/_

### Single-Cluster vs Multi-Cluster OpenChoreo

_Topology decision for HPDC deployment:_

| Aspect | Single Cluster | Multi-Cluster (Hybrid) |
|--------|----------------|------------------------|
| Complexity | Low | Medium |
| Isolation | Namespace-based | Cluster-based |
| Networking | In-cluster | mTLS WebSocket |
| Use Case | Dev/staging | Production |
| Cost | Lower | Higher |

**Recommended Approach for HPDC:**
- **Dev**: Single cluster with miniOne (OpenNebula + OneKS + OpenChoreo all-in-one)
- **Staging**: Hybrid (CP+WP+OP co-located, separate Data Plane)
- **Production**: Multi-cluster with HA control planes

**Development Topology (Single Cluster):**
```
miniOne Server (32 GiB RAM)
└── OneKS K8s Cluster (standalone flavour)
    └── OpenChoreo (all planes co-located)
        ├── Control Plane
        ├── Data Plane
        ├── Workflow Plane (Argo Workflows)
        └── Observability Plane (optional)
```

_Source: https://openchoreo.dev/docs/platform-engineer-guide/deployment-topology/_

### GitOps Repository Structure

_Recommended repository layout for OpenChoreo + ArgoCD/Kargo:_

```
gitops-config/
├── argocd/                          # ArgoCD Applications
│   ├── dev/
│   │   ├── app-dev.yaml
│   │   └── kustomization.yaml
│   ├── staging/
│   │   ├── app-staging.yaml
│   │   └── kustomization.yaml
│   └── prod/
│       ├── app-prod.yaml
│       └── kustomization.yaml
├── env/                             # Environment-specific values
│   ├── dev/
│   │   └── values.yaml
│   ├── staging/
│   │   └── values.yaml
│   └── prod/
│       └── values.yaml
├── kargo/                           # Kargo promotion config
│   ├── warehouse.yaml
│   ├── stages.yaml
│   └── promotion-tasks.yaml
├── openchoreo/                      # OpenChoreo platform resources
│   ├── environments/
│   │   ├── development.yaml
│   │   ├── staging.yaml
│   │   └── production.yaml
│   ├── component-types/
│   │   └── service.yaml
│   └── workflows/
│       └── docker-gitops-release.yaml
└── workloads/                       # Application manifests
    └── <namespace>/
        ├── components/
        │   └── <component>/
        │       ├── component.yaml
        │       ├── workload.yaml
        │       └── releases/
        └── projects/
            └── <project>.yaml
```

_Source: https://github.com/openchoreo/sample-gitops_

### Security Architecture

_Defense-in-depth across all layers:_

| Layer | Security Control | Implementation |
|-------|------------------|----------------|
| IaaS | Network isolation | OpenNebula Virtual Networks (public/private) |
| K8s | RBAC + NetworkPolicies | RKE2 defaults + OpenChoreo policies |
| IDP | OAuth2/OIDC | ThunderID or external IdP |
| CI/CD | Secret management | External Secrets Operator + ClusterSecretStore |
| Promotion | Approval gates | Kargo Stage RBAC + manual approval |
| mTLS | Certificate rotation | cert-manager + self-signed CAs |

**Secret Flow:**
```
External Secrets Operator
    └── ClusterSecretStore (Vault, AWS SM, etc.)
        └── Workflow Plane: Git/Registry credentials
        └── Data Plane: Application secrets
        └── Control Plane: IdP credentials
```

_Source: https://openchoreo.dev/docs/platform-engineer-guide/external-ca-tls-setup/_

---

<!-- Implementation research content will be appended in step 5 -->
