# Story 5-3: Trigger Automated Alert Responses

Status: done

Baseline commit: 5327adf

## Story

As a Platform Engineer,
I want automated responses triggered by alert conditions,
so that common incidents are remediated without human intervention.

## Acceptance Criteria

1. Given a `critical` severity alert enters `initial` state, when the response engine matches a workflow, then the predefined Kubernetes action executes within 5s.
2. Given an alert matches `restart_service` action, when triggered, then `kubectl rollout restart` runs on the affected Deployment.
3. Given an alert matches `increase_resource` action, when triggered, then the Deployment HPA target is patched.
4. Given `require_human_approval` applies, when the action is sensitive, then the alert transitions to `awaiting_approval` state.

## Implementation Plan

- Create Pulsar Function to evaluate alert state and trigger Kubernetes Jobs
- Define alert workflow CRD with action selectors
- Implement Kubernetes Job operator for restart/increase_resource actions
- Add Grafana alert rule for response latency observability

## Files

- `gitops/epic5/base/alert-response-engine.yaml` (new)
- `gitops/epic5/base/alert-workflows.yaml` (new)
- `scripts/alert-response-trigger.py` (new)
- `tests/test_alert_response.py` (new)