# Cilium mTLS Mesh Enforcement

This story is covered by the existing Cilium mTLS implementation from Epic 1 story 1.5.

## Completed

- Cilium authentication is enabled.
- Mutual TLS is enabled.
- SPIRE integration is configured.
- Cilium service identities are issued to workloads.
- Plaintext HTTP rejection is enforced by the mTLS mesh.

## GitOps paths

- Base manifest: `gitops/cilium/base/cilium-mtls.yaml`
- Dev overlay: `gitops/cilium/overlays/mesh/kustomization.yaml`
