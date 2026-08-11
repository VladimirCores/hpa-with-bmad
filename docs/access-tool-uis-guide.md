# Accessing HPDC Tool UIs

This guide explains how to reach the HPDC tool UIs — Hubble UI, Argo CD, Backstage, Grafana, and Kargo — through the Envoy Gateway single entry point.

## Prerequisites

- The HPDC dev cluster is running (Talos on QEMU, network `192.168.100.0/24`).
- The Envoy Gateway (`hpdc-edge`) is deployed with a TLS wildcard certificate for `*.hpdc.local` (cert-manager).
- Cilium L2 load balancing assigns the Envoy Gateway a LoadBalancer address from the pool `192.168.100.200/32`.

## 1. Resolve the gateway address

Get the Envoy Gateway LoadBalancer IP:

```bash
kubectl get svc -n envoy-gateway-system
```

Look for the `hpdc-edge-*` proxy service and note its `EXTERNAL-IP`. It is the single entry point for all tool UIs.

## 2. Map the hostnames

Add the gateway IP and every tool hostname to `/etc/hosts` (all resolve to the same LoadBalancer IP):

```
<GATEWAY_IP> hubble.hpdc.local grafana.hpdc.local backstage.hpdc.local argocd.hpdc.local kargo.hpdc.local
```

The wildcard TLS certificate `*.hpdc.local` covers every host above, so no extra TLS setup is needed.

## 3. Access the UIs

| Tool | URL | Backend | Port |
|------|-----|---------|------|
| Hubble UI | `https://hubble.hpdc.local` | `hubble-ui` | 80 |
| Grafana | `https://grafana.hpdc.local` | `grafana` | 80 |
| Backstage | `https://backstage.hpdc.local` | `backstage` | 80 |
| Argo CD | `https://backstage.hpdc.local/argocd` | `argocd-server` | 80 |
| Kargo | `https://backstage.hpdc.local/kargo` | `kargo-ui` | 8080 |

## 4. Auth behavior

- Native tool auth is enforced per tool (Backstage signs in through Casdoor at `https://casdoor.hpdc.local`).
- Casdoor/Casbin `ext_authz` is **not** enforced on tool UI routes; each tool's own identity layer handles access.

## 5. Verifying connectivity

```bash
# Port 80 redirects to 443
curl -I http://backstage.hpdc.local

# TLS handshake against the wildcard cert
curl -I https://backstage.hpdc.local

# Route check via the gateway
curl -k -I https://hubble.hpdc.local
```

## 6. GitOps sources

| Component | Base manifest |
|-----------|---------------|
| Tool UI routes (Backstage, Argo CD v3.5, Kargo) | `gitops/tool-ui/base/tool-ui-routes.yaml` |
| Observability UI routes (Grafana, Hubble) | `gitops/observability/base/observability-ui-routes.yaml` |
| Grafana/Hubble host routes | `gitops/observability/base/grafana-hubble-routes.yaml` |
| Envoy Gateway / TLS | `gitops/envoy-gateway/base/envoy-gateway.yaml`, `gitops/cert-manager/base/cert-manager.yaml` |

## 7. Troubleshooting

- **Hostname not resolving** — confirm the `/etc/hosts` entry uses the proxy `EXTERNAL-IP` from step 1.
- **404 / wrong tool** — confirm the full path is used for Argo CD (`/argocd`) and Kargo (`/kargo`).
- **Certificate warning** — the wildcard cert covers `*.hpdc.local`; verify the proxy is reachable and the host is one of the listed `hpdc.local` names.
