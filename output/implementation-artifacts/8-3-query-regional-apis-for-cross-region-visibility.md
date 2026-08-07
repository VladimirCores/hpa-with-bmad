# Story 8-3: Query Regional APIs for Cross-Region Visibility

Status: done

Baseline commit: 6c9e4fd

## Story

As a Business Stakeholder,
I want a central hub that can query regional APIs for aggregate visibility,
So that I can see platform metrics across regions without storing regional data at the hub.

## Acceptance Criteria

1. Given regional APIs are available with region-scoped authentication, when the central hub queries them, then it displays aggregated metrics across regions.
2. Given regional metrics are displayed, when a region is selected, then it supports per-region drill-down for entity and alert state.
3. Given a query completes, when the hub processes results, then the hub does not store regional data.
4. Given the process runs offline, when it completes, then no internet access is required.
5. Given a failure, when the script runs, then it exits with a non-zero status on failure.

## Implementation Plan

- Add `gitops/regional-hub/` component binding the `RegionalApiHub` contract (central hub stores no regional data, per-region drill-down, region-scoped auth, aggregate metrics).
- Add hub SPA deployment, region-scoped API client, and cross-region metrics dashboards.
- Install script with `--check` / `--dry-run` / `--apply`, step wrapper, and validation test.

## Files

- `gitops/regional-hub/base/regional-hub.yaml` (new)
- `gitops/regional-hub/overlays/dev/kustomization.yaml` (new)
- `scripts/install-regional-hub-dev.py` (new)
- `scripts/steps/42-install-regional-hub-dev.py` (new)
- `tests/test_install_regional_hub_dev.py` (new)
