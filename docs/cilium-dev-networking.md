# Install Offline Cilium eBPF Networking

## Purpose

Install Cilium 1.19.6 on the offline Talos dev cluster with `kubeProxyReplacement:true`, L2 load balancing, `CiliumL2AnnouncementPolicy`, and `CiliumLoadBalancerIPPool`.

## Required offline artifacts

- `output/qemu/talos-v1.img` from Story 1.2
- `output/talos/talosconfig` from Story 1.2
- Pre-cached Cilium 1.19.6 images at `output/cilium/images/cilium-agent-v1.19.6`

## GitOps overlay

Cilium manifests are staged under:

```text
gitops/cilium/overlays/dev/kustomization.yaml
```

The overlay applies:

- `gitops/cilium/base/cilium.yaml`
- `gitops/cilium/base/cilium-l2-policy.yaml`
- `gitops/cilium/base/cilium-loadbalancer-ippool.yaml`

## Installer command

```python
scripts/install-cilium-dev.py --offline --dry-run
```

## Real apply command

```python
scripts/install-cilium-dev.py --offline --apply
```

## Expected output

```text
$ scripts/install-cilium-dev.py --offline --dry-run
Cilium dev cluster dry-run passed.
Cilium version: 1.19.6
Cilium offline image cache: output/cilium/images/cilium-agent-v1.19.6
Talos config: output/talos/talosconfig
GitOps overlay: gitops/cilium/overlays/dev/kustomization.yaml
```

## Expected Cilium state after apply

- Cilium agent and operator pods are `Ready`.
- kube-proxy is disabled or absent.
- `kubeProxyReplacement:true` is enabled.
- Cilium L2 mode is enabled.
- `CiliumL2AnnouncementPolicy` is applied.
- `CiliumLoadBalancerIPPool` is applied.
- A local LoadBalancer service can be reached through the L2 load balancer.

## Notes

- Do not enable mTLS/SPIFFE/SPIRE in this story; Story 1.5 covers Cilium mTLS mesh.
- Do not install Rook-Ceph in this story; Story 1.4 covers persistent storage.
