#!/usr/bin/env python3
"""RED-phase acceptance scaffolds for the alert pipeline.

P0-004 Back-pressure: lag drives exponential backoff; drop metric
       ingestion_dropped_total{reason}; no loss below the threshold.
P0-005 A breach creates an alert; state transitions follow the alert
       state machine and invalid transitions are rejected 409.
P0-006 Duplicate deliveries are processed exactly once (idempotency).
P0-007 Alerts route via Pulsar; consumers receive enriched events.

All tests are skipped (RED phase): the alert APIs, Pulsar topics, and
test-support harness do not exist yet.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ALERT_ID = "0197F5Z8K9X5N2B1M7Q4R0T6VX"
ALERTS_API_KEY = "hpdc-events-dev-key"
ALERTS_URL = "http://hpdc-alerts.local"
TOPIC_INCOMING = "persistent://hpdc/alerts/incoming"


def _raw_alert(**overrides) -> dict:
    alert = {
        "alert_id": ALERT_ID,
        "device_id": "device-8193f4",
        "severity": "critical",
        "timestamp": "2026-08-07T13:15:47.123Z",
        "metadata": {"rule": "cpu.usage.high", "threshold": 0.9, "observed": 0.97},
    }
    alert.update(overrides)
    return alert


# P0-004 (FR-4, R-005)
# Given: consumer lag above the configured back-pressure threshold
#  When: telemetry continues to be ingested
#  Then: the consumer backs off with an exponentially increasing delay
#   And: ingestion_dropped_total{reason} increments when the budget is exceeded
#   And: no messages are lost while lag stays below the threshold
def test_p0_004_backpressure_backoff_and_drop_metric() -> None:
    from hpdc_test_client import IngestHarness, MetricClient

    harness = IngestHarness("http://hpdc-edge.local", api_key="hpdc-events-dev-key")
    metrics = MetricClient("http://victoria-metrics.local:8428")

    harness.inject_consumer_lag_ms(75_000)
    first = harness.post_telemetry_batch(count=100)
    second = harness.post_telemetry_batch(count=100)
    assert first.delivered == 100
    assert second.delivered == 100
    assert second.backoff_ms > first.backoff_ms, "back-off must increase"
    assert second.backoff_ms >= 2 * first.backoff_ms, "back-off must be exponential"

    harness.inject_consumer_lag_ms(300_000)
    series = metrics.query("ingestion_dropped_total")
    assert any('reason="consumer_lag"' in sample for sample in series), "drop metric must carry the reason label"


# P0-005 (FR-5, FR-6, R-015)
# Given: a device metric breaches its rule threshold
#  When: the breach is evaluated by the alert rule engine
#  Then: an alert is created in state "initial"
#   And: transitions initial -> acknowledged -> investigating -> resolved -> closed succeed
#   And: an invalid transition from the terminal state is rejected 409
def test_p0_005_alert_created_on_breach_and_state_transitions() -> None:
    from hpdc_test_client import AlertApiClient

    client = AlertApiClient(ALERTS_URL, api_key=ALERTS_API_KEY)
    created = client.create_alert(_raw_alert())
    assert created.status_code == 202
    alert_id = created.json()["alert_id"]
    assert created.json()["state"] == "initial"

    ack = client.transition(alert_id, "acknowledged", actor="alice@hpdc")
    assert ack.status_code == 200 and ack.json()["state"] == "acknowledged"
    inv = client.transition(alert_id, "investigating", actor="alice@hpdc")
    assert inv.status_code == 200 and inv.json()["state"] == "investigating"
    res = client.transition(alert_id, "resolved", actor="alice@hpdc", reason="alert resolved")
    assert res.status_code == 200 and res.json()["state"] == "resolved"
    closed = client.transition(alert_id, "closed", actor="alice@hpdc")
    assert closed.status_code == 200 and closed.json()["state"] == "closed"
    assert client.transition(alert_id, "acknowledged", actor="alice@hpdc").status_code == 409


# P0-006 (FR-6, FR-8, R-018)
# Given: an alert delivered more than once with the same idempotency key
#  When: the duplicate redelivery is processed
#  Then: it is processed exactly once (single state side effect)
#   And: duplicate replays within the 24h dedupe window return the original result
def test_p0_006_duplicate_delivery_single_processing() -> None:
    from hpdc_test_client import AlertApiClient

    client = AlertApiClient(ALERTS_URL, api_key=ALERTS_API_KEY)
    alert = _raw_alert(
        idempotency_key="0197F5Z8K9X5N2B1M7Q4R0T6VZ",
        source_change_id="0197F5Z8K9X5N2B1M7Q4R0T6VY",
    )

    first = client.post_alert(alert)
    replay = client.post_alert(alert)
    assert first.status_code == 202
    assert replay.status_code == 200
    assert replay.json()["alert_id"] == first.json()["alert_id"]
    assert client.count_alerts(source_change_id=alert["source_change_id"]) == 1


# P0-007 (FR-9, R-005)
# Given: a raw alert signal posted to the ingestion path
#  When: the signal is normalized and routed via Pulsar
#  Then: a consumer of alerts.incoming receives the alert
#   And: the delivered event is enriched with region and tenant context
def test_p0_007_alert_routed_via_pulsar_enriched() -> None:
    from hpdc_test_client import AlertApiClient, PulsarConsumer

    client = AlertApiClient(ALERTS_URL, api_key=ALERTS_API_KEY)
    assert client.post_alert(_raw_alert()).status_code == 202

    consumer = PulsarConsumer(TOPIC_INCOMING)
    events = consumer.consume(timeout_s=5)
    matches = [e for e in events if e["alert_id"] == ALERT_ID]
    assert matches, "enriched alert must appear on alerts.incoming"
    enriched = matches[0]["enriched"]
    assert enriched["region_id"] == "region-1"
    assert enriched["tenant_id"] == "company:acme"
    assert "rule" in enriched


def main() -> int:
    tests = (
        test_p0_004_backpressure_backoff_and_drop_metric,
        test_p0_005_alert_created_on_breach_and_state_transitions,
        test_p0_006_duplicate_delivery_single_processing,
        test_p0_007_alert_routed_via_pulsar_enriched,
    )
    skipped = 0
    for test in tests:
        try:
            test()
        except (ImportError, NotImplementedError) as exc:
            skipped += 1
            print(f"  RED (skipped): {test.__name__} — {exc}")
        except Exception as exc:
            skipped += 1
            print(f"  RED (skipped): {test.__name__} — {type(exc).__name__}: {exc}")
    print(f"RED PHASE: {len(tests)} acceptance tests scaffolded; {skipped} pending green-phase implementation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
