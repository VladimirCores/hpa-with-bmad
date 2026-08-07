# Story 8-1: Establish Cross-Cluster Service Discovery with ClusterMesh

Status: done

Baseline commit: 51ded98

## Story

As a Platform Engineer,
I want ClusterMesh to connect regional clusters over WireGuard VPN,
So that services can discover each other across regions without manual configuration.

## Acceptance Criteria

1. Given two regional clusters are provisioned, when ClusterMesh is configured over WireGuard VPN, then services are discovered across clusters.
2. Given cross-cluster services, when traffic flows between regions, then it is encrypted through the VPN tunnel.
3. Given cross-cluster discovery, when no per-service configuration exists, then services are discovered automatically.
4. Given the process runs offline, when it completes, then no internet access is required.
5. Given a failure, when the script runs, then it exits with a non-zero status on failure.

## Implementation Plan

- Add `gitops/clustermesh/` component binding the `ClusterMesh` contract (`protocol: WireGuard`, `cross_cluster: true`, `manual_per_service_discovery: false`, `encrypted: true`).
- Enable Cilium WireGuard encryption and ClusterMesh agent config.
- Install script with `--check` / `--dry-run` / `--apply`, step wrapper, and validation test.

## Files

- `gitops/clustermesh/base/clustermesh.yaml` (new)
- `gitops/clustermesh/overlays/dev/kustomization.yaml` (new)
- `scripts/install-clustermesh-dev.py` (new)
- `scripts/steps/40-install-clustermesh-dev.py` (new)
- `tests/test_install_clustermesh_dev.py` (new)
