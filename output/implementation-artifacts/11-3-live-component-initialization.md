# Epic 11.3: Live Component Initialization

## Status: In Progress

## Objective
Initialize essential cluster components for the HPDC dev cluster.

## Tasks

- [x] Install cert-manager for TLS certificates
- [x] Install Harbor container registry
- [x] Install Argo CD GitOps
- [x] Install Kargo promotion workflow
- [x] Install VictoriaMetrics for metrics
- [x] Install Grafana for dashboards
- [ ] Install Envoy Gateway (requires Cilium)
- [ ] Install External Secrets Operator
- [ ] Install Uptime Kuma monitoring
- [ ] Install Metrics Server
- [ ] Install Local Path Provisioner (already installed)
- [ ] Configure metallb for LoadBalancer services
- [ ] Deploy Argo CD Applications
- [ ] Deploy Sealed Secrets
- [ ] Configure Grafana dashboards

## Components Installed

| Component | Namespace | Status |
|-----------|-----------|--------|
| cert-manager | cert-manager | Running |
| Harbor | harbor | Running |
| Argo CD | argocd | Running |
| Kargo | kargo | Running |
| VictoriaMetrics | monitoring | Running |
| Grafana | monitoring | Running |
| Local Path Provisioner | local-path-storage | Running |

## Notes

- Cilium installation requires privileged mode which is not available in Docker dev cluster
- Envoy Gateway requires Cilium for full functionality
- Harbor is configured with persistence disabled for dev cluster
- All components are configured for clusterIP access only
