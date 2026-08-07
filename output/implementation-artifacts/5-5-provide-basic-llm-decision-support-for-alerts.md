# Story 5-5: Provide Basic LLM Decision Support for Alerts

Status: done

Baseline commit: 7f70c0d

## Story

As an On-call Engineer,
I want basic LLM-generated decision support on alert responses,
so that I receive actionable remediation recommendations with confidence scoring and a clear approval gate.

## Acceptance Criteria

1. Given an alert with context, when decision support runs, then it returns a recommendation with an action, target, and confidence score.
2. Given a low-confidence recommendation, when the response is sensitive, then it is escalated to manual review and marked `pending_approval`.
3. Given a high-confidence recommendation for a non-sensitive action, when configured, then it may be executed automatically.
4. Given an LLM call, when logged, then the input context, output recommendation, and decision context are recorded.
5. Given an unauthorized actor, when they approve a recommendation, then the approval is rejected and the attempt is logged.

## Implementation Plan

- Create LlmDecisionSupport CRD instance binding to the platform contract.
- Create llm-decision-support API Deployment/Service.
- Implement `alert-decision-support.py` CLI that scores recommendations, enforces the sensitive-action approval gate, and logs all decisions.
- Add Grafana panel for decision support metrics (recommendation confidence, approval rate).

## Files

- `gitops/alerts/base/llm-decision-support.yaml` (new)
- `gitops/alerts/base/llm-decision-support-api.yaml` (new)
- `scripts/alert-decision-support.py` (new)
- `scripts/steps/21-llm-decision-support.py` (new)
- `tests/test_alert_decision_support.py` (new)
- `gitops/monitoring/base/llm-decision-dashboard.json` (new)
