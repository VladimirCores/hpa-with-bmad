# Story 6-2: Provide entity CRUD and bulk operations

Status: done

Baseline commit: 5a30962

## Story

As a Platform Administrator,
I want CRUD and bulk operations for entity types across the entity stores,
so that entities can be provisioned and maintained with role-based access control and full mutation audit logging.

## Acceptance Criteria

1. Given an entity type, when a create operation is issued, then the entity is validated, stored, and logged with actor, timestamp, and change diff.
2. Given an entity id, when a read operation is issued, then the stored entity is returned.
3. Given an existing entity, when an update operation is issued, then the change is applied and the mutation logged with the change diff.
4. Given an existing entity, when a delete operation is issued, then the entity is removed and the mutation logged.
5. Given a batch of entities, when a bulk operation is issued, then all entities are processed up to the configured bulk limit (1000) and each mutation is logged.
6. Given an unauthorized actor, when they issue a mutation, then the operation is rejected and the attempt is logged.
7. Given any mutation, when latency is measured, then it completes within the configured latency budget (200ms).

## Implementation Plan

- Add `EntityCrud` binding to the platform contract under `gitops/entity-store/base/`.
- Declare the entity CRUD API Deployment/Service, action roles, and audit trail.
- Implement `entity-api.py` CLI with create/read/update/delete/bulk subcommands, RBAC, and immutable mutation NDJSON log.
- Register resources in the base kustomization; add step wrapper and validation test.

## Files

- `gitops/entity-store/base/entity-crud.yaml` (new)
- `scripts/entity-api.py` (new)
- `scripts/steps/32-entity-crud.py` (new)
- `tests/test_entity_crud.py` (new)
