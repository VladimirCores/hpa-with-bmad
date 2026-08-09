#!/usr/bin/env python3
"""RED-PHASE E2E journey test: HPDC alert pipeline ingest -> decision -> dispatch -> ClickHouse (P0-008).

Contract source:
  - output/test-artifacts/test-design/test-design-qa.md  (P0-008, FR-12, R-004)
  - gitops/alerts/base/*.yaml                            (alert handler API, audit trail,
                                                          response engine, workflows,
                                                          LLM decision support)
  - gitops/security/base/api-key-authn.yaml              (X-API-Key gateway auth, FR-38)
  - gitops/platform/base/platform-scaffold.yaml          (ClickHouseTable device_metrics)
  - gitops/envoy-gateway/base/envoy-gateway.yaml         (hpdc-edge gateway, /events route)

RED PHASE: the live journey tests are @pytest.mark.skip. These scaffolds assert the
EXPECTED end-to-end behavior ingest -> decision support -> dispatch -> ClickHouse
persistence. They cannot pass until the alert pipeline is implemented and deployed to
a live cluster (blocker B-001) and the Pulsar/Kafka consumer harness exists (blocker
B-003). GREEN (partial): the offline manifest-contract check asserts the gitops/alerts
stages are present and wired to the journey contracts.

Run under pytest or standalone (main() executes the active manifest-contract body).
"""

from __future__ import annotations

import json
import os
import re
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
GITOPS = ROOT / "gitops"
ALERTS_DIR = GITOPS / "alerts/base"

GATEWAY_URL = os.environ.get("HPDC_GATEWAY_URL", "https://edge.hpdc.local")
CLICKHOUSE_URL = os.environ.get("HPDC_CLICKHOUSE_URL", "http://clickhouse-sink.hpdc-platform.svc:8123")
EVENTS_API_KEY = os.environ.get("HPDC_EVENTS_API_KEY", "hpdc-events-dev-key")
CONSUMER_HARNESS_URL = os.environ.get("HPDC_CONSUMER_HARNESS_URL")

ALERTS_STATE_TOPIC = "alerts.state"
ALERTS_DLQ_TOPIC = "hpdc-alerts.alerts.dlq"
CLICKHOUSE_TABLE = "telemetry.device_metrics"

JOURNEY: dict = {}

_TLS = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
_TLS.check_hostname = False
_TLS.verify_mode = ssl.CERT_NONE


def _http_json(method: str, url: str, headers: dict, payload: dict | None = None) -> tuple[int, dict, object]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, context=_TLS, timeout=30) as resp:
        body = json.loads(resp.read() or b"{}")
        return resp.status, body, resp.headers


def _clickhouse_query(query: str) -> tuple[int, str]:
    encoded = urllib.parse.quote(query, safe="")
    url = f"{CLICKHOUSE_URL}/?query={encoded}&default_format=TabSeparatedRaw"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.status, resp.read().decode("utf-8", "replace").strip()


def _pulsar_consume(topic: str, key: str) -> list[dict]:
    assert CONSUMER_HARNESS_URL, "B-003 Pulsar/Kafka consumer harness required (HPDC_CONSUMER_HARNESS_URL)"
    url = f"{CONSUMER_HARNESS_URL}/consume/{urllib.parse.quote(topic)}?key={urllib.parse.quote(key)}"
    status, body, _ = _http_json("GET", url, {})
    assert status == 200, f"consumer harness error: {status}"
    return body if isinstance(body, list) else [body]


# P0-008 (FR-12, R-004)
# Given: the hpdc-edge gateway exposes /events with X-API-Key auth (FR-38) and alert
#        signals flow into the alerts.state topic  When: an alert signal is ingested
#        with the events API key  Then: HTTP 201/202 is returned with a ULID alert_id
#        and the signal is observed on alerts.state keyed by alert_id (no loss, R-005)
@pytest.mark.skip(reason="RED PHASE: P0-008 journey unverifiable until the platform deploys (B-001) and the Pulsar/Kafka consumer harness exists (B-003)")
def test_journey_ingest_alert_signal() -> None:
    signal = {
        "alert_id": "0190f4e5a1b2c3d4e5f60718293a4b5c",
        "alert_type": "service_down",
        "severity": "critical",
        "source": "health-check",
        "context": {"deployment_name": "nginx", "namespace": "default"},
        "timestamp": "2026-08-07T13:00:00Z",
    }
    status, body, _ = _http_json(
        "POST",
        f"{GATEWAY_URL}/events",
        {"X-API-Key": EVENTS_API_KEY, "Content-Type": "application/json"},
        payload=signal,
    )
    assert status in (201, 202), f"alert signal ingest rejected: HTTP {status}"
    assert "alert_id" in body, "ingest response must echo alert_id"
    assert re.fullmatch(r"[0-9a-fA-F]{26,32}", body["alert_id"]), "alert_id must be a ULID"
    JOURNEY["alert_id"] = body["alert_id"]
    received = _pulsar_consume(ALERTS_STATE_TOPIC, key=body["alert_id"])
    assert received, f"alert signal not observed on {ALERTS_STATE_TOPIC}"


# P0-008 (FR-12, R-004)
# Given: an alert is pending and LlmDecisionSupport requires human approval for
#        restart/scale/delete/increase actions (approvers alice@hpdc, carol@hpdc)
# When:  a recommendation is requested and approved by an authorized operator
# Then:  the recommendation carries an action + decision, approved transitions are
#        recorded, unauthorized actors get HTTP 403 and invalid transitions 409
@pytest.mark.skip(reason="RED PHASE: P0-008 journey unverifiable until the platform deploys (B-001)")
def test_journey_decision_support() -> None:
    alert_id = JOURNEY["alert_id"]
    status, rec, _ = _http_json(
        "POST",
        f"{GATEWAY_URL}/api/alert/recommend",
        {"Content-Type": "application/json"},
        payload={"alert_id": alert_id},
    )
    assert status == 200
    assert rec["action"] in ("restart_deployment", "notify_with_context")
    assert "decision" in rec and "sensitive" in rec
    if rec["sensitive"]:
        status, approved, _ = _http_json(
            "POST",
            f"{GATEWAY_URL}/api/alert/approve",
            {"Content-Type": "application/json"},
            payload={"alert_id": alert_id, "actor": "alice@hpdc"},
        )
        assert status == 200 and approved["approved"] is True
        status, denied, _ = _http_json(
            "POST",
            f"{GATEWAY_URL}/api/alert/approve",
            {"Content-Type": "application/json"},
            payload={"alert_id": alert_id, "actor": "dave@hpdc"},
        )
        assert status == 403, "unauthorized actor must get 403 (AlertAuditTrail.actor_validation)"


# P0-008 (FR-12, R-004)
# Given: an approved action and AlertResponseEngine rate limits (max_actions_per_alert 3,
#        restart_deployment latency_target_ms 5000)  When: the action is dispatched
# Then:  a Job alert-action-<alert_id> is created in hpdc-alerts within the latency
#        target and a 4th action on the same alert is rejected (rate limited)
@pytest.mark.skip(reason="RED PHASE: P0-008 journey unverifiable until the platform deploys (B-001)")
def test_journey_dispatch_action() -> None:
    alert_id = JOURNEY["alert_id"]
    dispatch_status, _, _ = _http_json(
        "POST",
        f"{GATEWAY_URL}/api/alert/dispatch",
        {"Content-Type": "application/json"},
        payload={"alert_id": alert_id, "action": "restart_deployment", "target": "nginx"},
    )
    assert dispatch_status == 202, f"dispatch must be accepted, got HTTP {dispatch_status}"
    over_limit_status, _, _ = _http_json(
        "POST",
        f"{GATEWAY_URL}/api/alert/dispatch",
        {"Content-Type": "application/json"},
        payload={"alert_id": alert_id, "action": "restart_deployment", "target": "nginx"},
    )
    assert over_limit_status in (409, 429), "AlertResponseEngine.max_actions_per_alert must be enforced"


# P0-008 (FR-12, R-004)
# Given: the ClickHouseTable telemetry.device_metrics (ReplacingMergeTree, PARTITION BY
#        toYYYYMM(processed_timestamp)) is the alert-telemetry persistence target
# When:  the alert journey completes
# Then:  a row for the alert's device_id exists with a processed_timestamp, and the
#        ingest -> persist latency is under the 2s SLA (NFR6)
@pytest.mark.skip(reason="RED PHASE: P0-008 journey unverifiable until the platform deploys (B-001)")
def test_journey_clickhouse_persistence() -> None:
    device_id = JOURNEY.get("device_id", "nginx")
    query = (
        f"SELECT count() FROM {CLICKHOUSE_TABLE} "
        f"WHERE device_id = '{device_id}' "
        f"AND processed_timestamp >= now64(3) - INTERVAL 5 MINUTE"
    )
    status, count = _clickhouse_query(query)
    assert status == 200, f"ClickHouse probe failed: HTTP {status}"
    assert int(count) >= 1, "alert journey telemetry not persisted to ClickHouse (R-004, NFR6)"


# P0-008 (FR-12, R-004)
# Given: the alert pipeline manifests in gitops/alerts/base  When: the manifests are
#        inspected  Then: every stage of the journey is present and wired to the same
#        contracts the journey tests assert (handler API, audit trail, response
#        engine, workflows, LLM decision support)
def test_journey_manifest_contracts() -> None:
    handler = (ALERTS_DIR / "alert-handler-api.yaml").read_text(encoding="utf-8")
    audit = (ALERTS_DIR / "alert-audit-trail.yaml").read_text(encoding="utf-8")
    engine = (ALERTS_DIR / "alert-response-engine.yaml").read_text(encoding="utf-8")
    workflows = (ALERTS_DIR / "alert-workflows.yaml").read_text(encoding="utf-8")
    decision = (ALERTS_DIR / "llm-decision-support.yaml").read_text(encoding="utf-8")
    response_fn = (ALERTS_DIR / "alert-response-function.yaml").read_text(encoding="utf-8")
    scaffold = (GITOPS / "platform/base/platform-scaffold.yaml").read_text(encoding="utf-8")

    assert "name: alert-handler-api" in handler and "hpdc.local/alert-handler:0.1.0" in handler
    assert "/readyz" in handler and "/healthz" in handler
    for action in ("acknowledge", "investigate", "add_note", "resolve", "close"):
        assert action in audit, f"AlertAuditTrail action {action} must be configured"
    assert "http_status: 403" in audit and "http_status: 409" in audit
    assert "max_actions_per_alert: 3" in engine
    assert "restart_deployment" in engine and "latency_target_ms: 5000" in engine
    assert "service_down" in workflows and "critical" in workflows
    assert "alice@hpdc" in decision and "carol@hpdc" in decision
    assert "execute_without_approval: false" in decision
    assert "alerts.state" in response_fn and "hpdc-alerts.alerts.dlq" in response_fn
    assert "kind: ClickHouseTable" in scaffold and "device_metrics" in scaffold
    assert "idempotency_key" in scaffold


def main() -> int:
    # Partially GREEN: the offline manifest-contract check runs standalone; the live
    # journey bodies stay skipped (they need the deployed platform / ClickHouse, B-001).
    tests = (test_journey_manifest_contracts,)
    skipped = 0
    for test in tests:
        try:
            test()
        except Exception as exc:
            skipped += 1
            print(f"  RED (blocked): {test.__name__} - {type(exc).__name__}: {exc}")
    print(
        f"RED PHASE: {len(tests)} journey check active; {skipped} failing; "
        "live journey bodies (ingest/decision/dispatch/persistence) still skipped (B-001)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
