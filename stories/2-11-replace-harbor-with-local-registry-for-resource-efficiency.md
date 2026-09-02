---
title: "Replace Harbor with Local Registry for Reduced Resource Consumption"
description: "Evaluate and replace Harbor OCI registry with a lighter-weight local registry (registry:2) to reduce cluster resource consumption while maintaining air-gapped delivery capabilities"
tags:-devops, registry, optimization, storage, security
---

## Acceptance Criteria

**Given** the dev cluster has Harbor installed via Story 2.1
**When** I evaluate resource consumption of Harbor vs a minimal registry
**Then** the analysis documents:
  - CPU/RAM usage comparison (peak and steady-state)
  - Storage overhead for typical workloads
  - Impact on image push/pull latency
  - Security feature comparison (scanning, signing, auth)

**And** if resource savings justify the trade-off:
**When** I replace Harbor with `registry:2` or similar minimal registry
**Then**
  - Image push/pull still works without internet access
  - Helm charts can be stored as OCI artifacts
  - Spegel P2P distribution continues to function
  - Local Git mirror operates independently
  - Kargo/CI pipeline can reference images by digest
  - The deployment is GitOps-mediated (no direct kubectl)
  - The script exits with non-zero status on any failure

## Implementation Notes

### Harbor Resource Consumption
- Harbor typically requires: 2+ CPU cores, 2GB+ RAM, 50GB+ storage
- Includes: Trivy scanner, Notary v2, CoreService, Portal, ChartMuseum, Notary-Signer, Notary-Client

### Alternative: Minimal Registry:2
- Standard Docker Registry: ~50MB RAM, minimal CPU
- Image caching via Spegel handles most distribution needs
- Trivy can be run separately as a CI step or external webhook

### Trade-offs to Document
| Feature | Harbor | registry:2 + Spegel |
|---------|--------|---------------------|
| Trivy scanning | Built-in webhook | External CI job |
| Cosign signing | Built-in | External CI job |
| Helm charts | Native OCI support | Native OCI support |
| Multi-tenant | Yes (projects) | No |
| UI | Web UI | No UI (API only) |

## Related

- Story 2.1: Provision Local Harbor OCI Registry with Scanning and Signing
- AD-10: Air-gapped delivery
- FR-30: Local Harbor OCI registry
- Story 2.5: Provision Spegel P2P Image Distribution