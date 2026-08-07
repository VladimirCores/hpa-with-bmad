# Story 8-2: Enforce Regional Data Sovereignty

Status: done

Baseline commit: f789a4c

## Story

As a Platform Engineer,
I want independent regional data stores with no automatic cross-region replication,
So that regional data remains local unless explicitly configured otherwise.

## Acceptance Criteria

1. Given each region has its own CouchDB, YugabyteDB, ClickHouse, ArcadeDB, KeyDB, and PostgreSQL, when regional queries are routed, then each query goes to the region-scoped data store.
2. Given cross-region access is not configured, when data operations occur, then cross-region replication does not happen by default.
3. Given a cross-region data movement requirement, when it is requested, then explicit replication configuration is required before data moves.
4. Given the process runs offline, when it completes, then no internet access is required.
5. Given a failure, when the script runs, then it exits with a non-zero status on failure.

## Implementation Plan

- Add `gitops/regional-sovereignty/` component binding the `RegionalDataSovereignty` contract (independent regional stores, replication default disabled, explicit configuration required).
- Add region-scoped route and store manifests per region.
- Install script with `--check` / `--dry-run` / `--apply`, step wrapper, and validation test.

## Files

- `gitops/regional-sovereignty/base/regional-sovereignty.yaml` (new)
- `gitops/regional-sovereignty/overlays/dev/kustomization.yaml` (new)
- `scripts/install-regional-sovereignty-dev.py` (new)
- `scripts/steps/41-install-regional-sovereignty-dev.py` (new)
- `tests/test_install_regional_sovereignty_dev.py` (new)
