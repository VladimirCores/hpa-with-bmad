# Story 5-4: Manage Human Alert Handling with Audit Trail

Status: done

Baseline commit: a144afc

## Story

As an On-call Engineer,
I want to acknowledge, investigate, and resolve alerts with a full audit trail,
so that every human action on an alert is traceable to who, when, what, and the result.

## Acceptance Criteria

1. Given an alert in `initial` or `acknowledged` state, when an operator acknowledges it, then the state transitions to `acknowledged` and an audit entry records actor, timestamp, and action.
2. Given an operator adds a note, when the note is saved, then it is appended to the alert audit history with actor and timestamp.
3. Given an operator resolves an alert, when resolved, then the state transitions to `resolved` and the audit entry includes the resolution reason.
4. Given an invalid state transition, when requested, then the handler rejects it with HTTP 409 and records the attempted change in the audit trail.
5. Given an unauthorized actor, when they attempt an action, then the audit entry records `unauthorized` and the action is rejected.

## Implementation Plan

- Create AlertAuditTrail CRD instance binding to the platform audit-trail contract.
- Create alert-handling API Deployment/Service exposing acknowledge/investigate/note/resolve/close actions.
- Implement `alert-handler.py` CLI that validates state transitions, records audit entries, and enforces actor authorization.
- Add Grafana panel for human handling metrics (ack latency, resolution time).

## Files

- `gitops/alerts/base/alert-audit-trail.yaml` (new)
- `gitops/alerts/base/alert-handler-api.yaml` (new)
- `gitops/alerts/base/alert-handler-actions.yaml` (new)
- `scripts/alert-handler.py` (new)
- `scripts/steps/20-alert-human-handling.py` (new)
- `tests/test_alert_handling.py` (new)
- `gitops/monitoring/base/alert-handling-dashboard.json` (new)
