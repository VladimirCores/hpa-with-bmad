# Install Offline Cilium eBPF Networking

## Purpose

Install Cilium on the offline Talos dev cluster with `kubeProxyReplacement:true`, L2 load balancing, `CiliumL2AnnouncementPolicy`, and `CiliumLoadBalancerIPPool`.

## Required offline artifacts

- `output/talos/talosconfig` from cluster bootstrap
- Local Cilium Helm chart at `platform/charts/cilium-<version>.tgz`

## Helm values (L2 LoadBalancer)

The Cilium installer sets these Helm values for L2 LoadBalancer support:

| Helm Value | Purpose |
|------------|---------|
| `l2NeighDiscovery.enabled=true` | Enables L2 neighbor discovery (ARP/NDP) for LoadBalancer IP announcements |
| `ipam.mode=cluster-pool` | IPAM mode for pod and service IPs |
| `defaultLBServiceIPAM=lbipam` | Uses Cilium LB-IPAM for LoadBalancer service IPs |

> **Important:** The correct Helm key for L2 announcement is `l2NeighDiscovery.enabled`,
> not `loadBalancer.l2Announcement.enabled`. The latter is not a valid Cilium Helm value.

## L2 Resources (applied after Helm install)

After Helm install, the installer applies these CRDs from `gitops/cilium/rendered/dev.yaml`:

- `CiliumL2AnnouncementPolicy` — triggers L2 ARP/NDP announcements for LoadBalancer IPs
- `CiliumLoadBalancerIPPool` — defines the CIDR range for LoadBalancer IP allocation

## Docker cluster limitation

On Docker-based dev clusters, Cilium L2 announcement does not work at the host level
because Docker bridge networking does not support ARP/NDP announcements for external IPs.
The L2 responder BPF programs run correctly inside the Cilium agent, but ARP replies
cannot traverse the Docker bridge to reach the host.

**Workaround:** Use `kubectl port-forward` to access services:
```bash
kubectl port-forward -n envoy-gateway-system svc/envoy-<gateway>-<hash> 8443:443
```

On QEMU VM or bare-metal clusters, L2 announcement works natively.

## Expected Cilium state after install

- Cilium agent and operator pods are `Ready`.
- kube-proxy is disabled or absent.
- `kubeProxyReplacement=true` is enabled.
- `enable-l2-neigh-discovery=true` in Cilium configmap.
- `CiliumL2AnnouncementPolicy` and `CiliumLoadBalancerIPPool` CRDs are created.
- L2 responder BPF job is running.

## Notes

- Do not enable mTLS/SPIFFE/SPIRE in this story; Story 1.5 covers Cilium mTLS mesh.
- Do not install Rook-Ceph in this story; Story 1.4 covers persistent storage.
