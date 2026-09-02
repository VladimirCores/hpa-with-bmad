---
title: "Enable Cilium L2 LoadBalancer for External Gateway Access"
description: "Configure Cilium L2 LoadBalancer mode (CiliumL2AnnouncementPolicy + CiliumLoadBalancerIPPool) to enable LoadBalancer services with routable external IPs for Envoy Gateway and Hubble UI access"
tags:-network, l4, l7, networking, security
---

## Acceptance Criteria

**Given** the dev cluster is provisioned (Talos + Cilium installed via startup.dev.py)
**When** I run startup.dev.py with HPDC_GATEWAY_IP set
**Then** the Cilium L2 LoadBalancer resources are applied:
  - `CiliumLoadBalancerIPPool` with IP range matching HPDC_GATEWAY_IP
  - `CiliumL2AnnouncementPolicy` for the gateway IP pool
  - The gateway IP is routable from the host machine

**And** the Envoy Gateway LoadBalancer service accepts connections on the configured IP:443

**And** Hubble UI is accessible via the Gateway at `https://hubble.hpdc.local:443/`

**And** internal services (couchdb, knative, kafka) remain accessible via their respective routes

## Implementation Notes

1. **Cilium L2 LB Configuration:**
   - Create `CiliumLoadBalancerIPPool` with `spec.ipv4Pool: 172.18.0.0/16`
   - Create `CiliumL2AnnouncementPolicy` referencing the pool
   - Ensure `enable-host-traffic` is configured for external reachability

2. **For Docker-based clusters:**
   - The IP must be in the same L2 network as the nodes
   - Docker bridge must be active and routable
   - SELinux policies must permit cross-namespace traffic

3. **Alternative for Development:**
   - Port-forward remains available: `kubectl port-forward svc/hubble-ui 8080:80`
   - Gateway access: `kubectl port-forward svc/envoy-envoy-gateway-system... 8443:443`

## Validation

```bash
# Verify Cilium LB resources exist
kubectl get ciliumloadbalancerippool -n kube-system
kubectl get ciliuml2announcementpolicy -n kube-system

# Verify service has external IP
kubectl get svc envoy-envoy-gateway-system-... -n envoy-gateway-system -o wide

# Test gateway access
curl -k https://hubble.hpdc.local:443/

# Test hubble UI
curl -k https://hubble.hpdc.local:443/hubble/
```

## Related

- FR-23: Cilium eBPF networking with L2 load balancing
- FR-36: Envoy Gateway edge routing
- FR-29: Cilium Hubble network observability
- AD-8: mTLS for all inter-service communication
- FR-57: Gateway Class and HTTPRoutes configuration