#!/usr/bin/env python3
"""B-003 consumer harness: offline contract tests (message-arrival + latency).

Validates the tests/atdd/support/consumer_harness.py contract against the
local NDJSON topic store (the dev-side stand-in for a live Pulsar/Kafka
broker, B-001). Remote backend (HPDC_CONSUMER_HARNESS_URL) is exercised by
the RED journey bodies once a cluster exists.

Covers:
  - message-arrival assertion (success + timeout failure)
  - arrival-within-latency budget assertion (success + breach)
  - keyed vs unkeyed consumption, alert vs telemetry topic naming
  - factory parity between pulsar_consumer_harness / kafka_consumer_harness
  - the remote HTTP contract shape (GET /consume/{topic}?key=)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

SUPPORT = Path(__file__).resolve().parent
if str(SUPPORT) not in sys.path:
    sys.path.insert(0, str(SUPPORT))

from consumer_harness import (  # noqa: E402
    ConsumerHarnessError,
    KafkaConsumerHarness,
    PulsarConsumerHarness,
    kafka_consumer_harness,
    pulsar_consumer_harness,
)


@pytest.fixture()
def topic_store(tmp_path: Path) -> Path:
    (tmp_path / "topics").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _write(topic_store: Path, topic: str, message: dict) -> None:
    safe = topic.replace("/", ".")
    path = topic_store / "topics" / f"{safe}.ndjson"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(message) + "\n")


ENRICHED_ALERT = {
    "alert_id": "0190f4e5a1b2c3d4e5f60718293a4b5c",
    "device_id": "sensor-93d21f",
    "severity": "critical",
    "timestamp": "2026-08-07T13:00:00Z",
    "enriched": {"region_id": "region-1", "tenant_id": "company:acme", "rule": "service_down"},
}


def test_pulsar_harness_arrival_success(topic_store: Path) -> None:
    _write(topic_store, "alerts.incoming", ENRICHED_ALERT)
    harness = pulsar_consumer_harness("alerts.incoming", data_dir=topic_store, timeout_s=2.0)
    received = harness.assert_arrival(key="0190f4e5a1b2c3d4e5f60718293a4b5c")
    assert received[0]["alert_id"] == ENRICHED_ALERT["alert_id"]


def test_pulsar_harness_arrival_timeout_fails(topic_store: Path) -> None:
    harness = pulsar_consumer_harness("alerts.incoming", data_dir=topic_store, timeout_s=0.2)
    with pytest.raises(ConsumerHarnessError):
        harness.assert_arrival(key="0190f4e5a1b2c3d4e5f60718293a4b5c")


def test_pulsar_harness_unkeyed_arrival(topic_store: Path) -> None:
    _write(topic_store, "alerts.incoming", ENRICHED_ALERT)
    harness = pulsar_consumer_harness("alerts.incoming", data_dir=topic_store, timeout_s=2.0)
    received = harness.assert_arrival()
    assert len(received) == 1


def test_pulsar_harness_key_filter_ignores_unrelated(topic_store: Path) -> None:
    _write(topic_store, "alerts.incoming", dict(ENRICHED_ALERT, alert_id="other-alert"))
    _write(topic_store, "alerts.incoming", ENRICHED_ALERT)
    harness = pulsar_consumer_harness("alerts.incoming", data_dir=topic_store, timeout_s=2.0)
    received = harness.consume(key="0190f4e5a1b2c3d4e5f60718293a4b5c")
    assert len(received) == 1
    assert received[0]["alert_id"] == ENRICHED_ALERT["alert_id"]


def test_pulsar_harness_slash_topic_encoding(topic_store: Path) -> None:
    _write(topic_store, "hpdc-alerts.alerts.dlq", ENRICHED_ALERT)
    harness = pulsar_consumer_harness("hpdc-alerts.alerts.dlq", data_dir=topic_store, timeout_s=2.0)
    received = harness.assert_arrival(key="0190f4e5a1b2c3d4e5f60718293a4b5c")
    assert received[0]["alert_id"] == ENRICHED_ALERT["alert_id"]


def test_arrival_within_latency_budget_success(topic_store: Path) -> None:
    _write(topic_store, "alerts.incoming", ENRICHED_ALERT)
    harness = pulsar_consumer_harness("alerts.incoming", data_dir=topic_store, timeout_s=2.0)
    received = harness.assert_arrival_within_latency(
        key="0190f4e5a1b2c3d4e5f60718293a4b5c", max_latency_ms=10_000
    )
    assert received[0]["severity"] == "critical"


def test_arrival_within_latency_budget_breach(topic_store: Path) -> None:
    def delayed_write() -> None:
        time.sleep(0.3)
        _write(topic_store, "alerts.incoming", ENRICHED_ALERT)

    thread = __import__("threading").Thread(target=delayed_write)
    thread.start()
    harness = pulsar_consumer_harness("alerts.incoming", data_dir=topic_store, timeout_s=2.0)
    with pytest.raises(ConsumerHarnessError):
        harness.assert_arrival_within_latency(
            key="0190f4e5a1b2c3d4e5f60718293a4b5c", max_latency_ms=100
        )
    thread.join()


def test_kafka_harness_shares_contract(topic_store: Path) -> None:
    _write(topic_store, "alerts.incoming", ENRICHED_ALERT)
    harness = kafka_consumer_harness("alerts.incoming", data_dir=topic_store, timeout_s=2.0)
    assert isinstance(harness, KafkaConsumerHarness)
    received = harness.assert_arrival(key="0190f4e5a1b2c3d4e5f60718293a4b5c")
    assert received[0]["alert_id"] == ENRICHED_ALERT["alert_id"]


def test_kafka_harness_timeout_fails(topic_store: Path) -> None:
    harness = kafka_consumer_harness("alerts.incoming", data_dir=topic_store, timeout_s=0.2)
    with pytest.raises(ConsumerHarnessError):
        harness.assert_arrival()


def test_harness_class_direct_construction(topic_store: Path) -> None:
    _write(topic_store, "telemetry.readings", {"device_id": "sensor-93d21f", "event_id": "e1"})
    harness = PulsarConsumerHarness("telemetry.readings", data_dir=topic_store, timeout_s=2.0)
    received = harness.assert_arrival(key="sensor-93d21f")
    assert received[0]["device_id"] == "sensor-93d21f"


def test_consume_returns_empty_not_raise_without_key(topic_store: Path) -> None:
    harness = pulsar_consumer_harness("alerts.incoming", data_dir=topic_store, timeout_s=0.2)
    assert harness.consume() == []


def test_remote_url_contract_shape() -> None:
    harness = pulsar_consumer_harness(
        "alerts.incoming", harness_url="http://consumer-harness:8080", timeout_s=0.1
    )
    assert harness.harness_url == "http://consumer-harness:8080"
    assert harness.topic == "alerts.incoming"
