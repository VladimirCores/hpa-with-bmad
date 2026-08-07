# Story 6-3: React to entity change feeds with Knative Restate

Status: done

Baseline commit: bb6c8c1

## Story

As a Platform Administrator,
I want change-driven business logic invoked via Knative services with Restate,
so that entity changes from CouchDB and YugabyteDB are processed exactly-once within the reaction time budget.

## Acceptance Criteria

1. Given a CouchDB `_changes` or YugabyteDB CDC event, when it arrives, then a Knative service is invoked within 500ms of the change.
2. Given a change event, when the Knative service runs, then it can read and write both CouchDB and YugabyteDB within a single workflow step.
3. Given a change event, when processed, then it is processed exactly-once via Restate virtual object state.
4. Given a failed change event, when retries are exhausted, then it is routed to the configured dead letter queue (`hpdc.entity.dead.letter`).
5. Given an event processor, when it reads an event, then processing idempotency is enforced by deduplicating on the source change id.

## Implementation Plan

- Add `EntityChangeFeed` binding to the platform contract under `gitops/entity-store/base/`.
- Declare the change-feed workflow contract (sources, reaction budget, exactly-once, retry, DLQ).
- Implement `entity-change-processor.py` CLI that deduplicates on source change id, enforces the reaction budget, and routes failures to the DLQ.
- Add step wrapper and validation test.

## Files

- `gitops/entity-store/base/entity-change-feed.yaml` (new)
- `scripts/entity-change-processor.py` (new)
- `scripts/steps/33-entity-change-feed.py` (new)
- `tests/test_entity_change_feed.py` (new)
