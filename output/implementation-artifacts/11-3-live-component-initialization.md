# Epic 11.3: Live Component Initialization

## Status: Done

## Objective
Initialize essential cluster components for the HPDC dev cluster.

## Tasks

- [x] Install cert-manager for TLS certificates
- [x] Install Harbor container registry
- [x] Install Argo CD GitOps
- [x] Install Kargo promotion workflow
- [x] Install VictoriaMetrics for metrics
- [x] Install Grafana for dashboards
- [x] Install Envoy Gateway
- [x] Configure Cilium L2 LoadBalancer (CiliumLoadBalancerIPPool + CiliumL2AnnouncementPolicy)
- [x] Deploy Envoy Gateway HTTPRoutes for Harbor and ArgoCD
- [ ] Install External Secrets Operator (deferred to future epic)
- [ ] Install Uptime Kuma monitoring (deferred to future epic)
- [ ] Install Metrics Server (deferred to future epic)
- [ ] Deploy Sealed Secrets (deferred to future epic)
- [ ] Configure Grafana dashboards (deferred to future epic)

## Components Installed

| Component | Namespace | Status |
|-----------|-----------|--------|
| cert-manager | cert-manager | Running (3/3) |
| Harbor | harbor | Running (8/8) |
| Argo CD | argocd | Running (7/7) |
| Kargo | kargo | Running (5/6 - 1 completed) |
| VictoriaMetrics | monitoring | Running (1/1) |
| Grafana | monitoring | Running (1/1) |
| Envoy Gateway | envoy-gateway-system | Running (2/2) |
| Cilium | kube-system | Running (4/4) |
| Local Path Provisioner | local-path-storage | Running |

## Gateway Configuration

- **Gateway IP**: 172.18.255.200 (from Cilium L2 LoadBalancer pool)
- **GatewayClass**: envoy-gateway
- **HTTPRoutes**:
  - `harbor.hpdc.local` → harbor service (port 80)
  - `argocd.hpdc.local` → argocd-server service (port 80)

## Verification

- Harbor portal accessible at http://harbor.hpdc.local/ via gateway
- ArgoCD UI accessible at http://argocd.hpdc.local/ via gateway
- All pods Running with 0 restarts

## Notes

- Cilium replaces kube-proxy for eBPF-based networking
- Cilium L2 LoadBalancer replaces MetalLB for LoadBalancer services
- Harbor configured with persistence disabled for dev cluster
- ArgoCD configured with insecure mode (no TLS)
- Kargo configured with dev signing key and password hash
