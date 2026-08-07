# Story 6-1: Store entity hierarchy across CouchDB, ArcadeDB, and YugabyteDB

Status: done

Baseline commit: 273b2f1

## Story

As a Platform Administrator,
I want the entity hierarchy stored across CouchDB, ArcadeDB, and YugabyteDB,
so that documents, graph lineage, and transactional state are persisted to Ceph-backed volumes and accessible to all processing layers.

## Acceptance Criteria

1. Given an entity document, when submitted to the CouchDB entity store, then it is validated against a per-type schema and stored with a `_changes` feed exposed for downstream consumption.
2. Given an entity relationship, when submitted to the ArcadeDB graph store, then vertices and edges are validated against graph schema and graph traversal queries (neighbor discovery) are supported.
3. Given an internal resource record, when submitted to the YugabyteDB store, then it is validated against a relational schema and exposed via a SQL interface.
4. Given a storage request, when any store persists data, then it targets a Ceph RBD-backed StorageClass.
5. Given a store, when read/written by KNative or Spin workloads, then it is reachable via stable Service endpoints inside the cluster.

## Implementation Plan

- Create functional `entity-store` component under `gitops/` (no epic-derived naming).
- Declare Namespace, ServiceAccounts, Services, and Ceph-backed StorageClass for the triple-database store.
- Bind to the `EntityStore` contract from `gitops/platform/base/platform-scaffold.yaml`.
- Install script with `--check` / `--dry-run` / `--apply` semantics, step wrapper, and validation test.

## Files

- `gitops/entity-store/base/entity-store.yaml` (new)
- `gitops/entity-store/overlays/dev/kustomization.yaml` (new)
- `scripts/install-entity-store-dev.py` (new)
- `scripts/steps/31-install-entity-store-dev.py` (new)
- `tests/test_install_entity_store_dev.py` (new)
