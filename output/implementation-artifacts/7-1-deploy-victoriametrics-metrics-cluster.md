# Story 7-1: Deploy VictoriaMetrics metrics cluster

Status: done

Baseline commit: d06eccb

## Story

As a Platform Administrator,
I want a VictoriaMetrics metrics cluster with vmstorage, vminsert, and vmselect components,
so that platform metrics are retained per environment and queryable through a single Prometheus-compatible endpoint.

## Acceptance Criteria

1. Given the metrics cluster, when deployed, then vmstorage, vminsert, and vmselect components are all present.
2. Given metrics, when ingested, then they flow through vminsert into vmstorage and are queryable via vmselect.
3. Given a retention policy, when configured, then it matches the platform contract (dev 24h, staging 7d, prod configurable).
4. Given a query, when issued, then the cluster exposes a Prometheus-compatible query endpoint.
5. Given a network request, when it targets the cluster, then components are reachable via stable Service endpoints.

## Implementation Plan

- Create functional `victoria-metrics` component under `gitops/`.
- Declare Namespace, ServiceAccounts, ConfigMaps for components and retention, Services, and the ObservabilityPipeline binding.
- Install script with `--check` / `--dry-run` / `--apply` semantics, step wrapper, and validation test.

## Files

- `gitops/victoria-metrics/base/victoria-metrics.yaml` (new)
- `gitops/victoria-metrics/overlays/dev/kustomization.yaml` (new)
- `scripts/install-victoria-metrics-dev.py` (new)
- `scripts/steps/35-install-victoria-metrics-dev.py` (new)
- `tests/test_install_victoria_metrics_dev.py` (new)
