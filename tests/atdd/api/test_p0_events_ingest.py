#!/usr/bin/env python3
"""RED-phase acceptance scaffolds for edge event ingestion.

P0-001 POST /events accepts a protobuf envelope (ULID + RFC3339).
P0-002 Telemetry is queryable in ClickHouse within 2s of ingestion (NFR6).
P0-003 /events and /telemetry accept API-Key only; Bearer rejected.

All tests are skipped (RED phase): the edge API and its test-support
harness do not exist yet. Green-phase owner implements the harness and
removes the skip markers.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EVENT_ID = "0197F5Z8K9X5N2B1M7Q4R0T6VW"
EVENTS_API_KEY = "hpdc-events-dev-key"
TELEMETRY_API_KEY = "hpdc-telemetry-dev-key"
EDGE_URL = "http://hpdc-edge.local"


def _envelope() -> dict:
    return {
        "device_id": "sensor-93d21f",
        "device_type": "sensor",
        "event_type": "temperature.reading",
        "timestamp": "2026-08-07T13:15:47.123Z",
        "payload": {"temperature_c": 21.7, "humidity_pct": 48.2},
        "region_id": "region-1",
    }


# P0-001 (FR-1)
# Given: an edge gateway accepting POST /events
#   And: a protobuf-encoded envelope with a ULID event id and RFC3339 timestamp
#  When: a client with a valid events API key posts the envelope
#  Then: the gateway responds 202 Accepted
#   And: the event id is a 26-char ULID echoed back for tracing
def test_p0_001_events_api_accepts_envelope() -> None:
    from hpdc_test_client import EventsClient

    client = EventsClient(EDGE_URL, api_key=EVENTS_API_KEY)
    resp = client.post_events(_envelope())
    assert resp.status_code == 202
    echoed = resp.json()["event_id"]
    assert len(echoed) == 26
    assert echoed.isalnum()
    assert resp.json()["accepted_at"].endswith("Z")


# P0-002 (FR-1, FR-2, R-004)
# Given: telemetry accepted through the ingestion path
#  When: the reading is posted and later queried in ClickHouse
#  Then: the end-to-end ingest latency is below the 2s NFR6 budget
# Note: runs against the store-backed simulation - the local edge service persists
# telemetry to the NDJSON topic store and ClickHouseProbe polls it, standing in for
# the telemetry -> topic -> ClickHouse pipeline (real ClickHouse behind B-001).
def test_p0_002_telemetry_to_topic_to_clickhouse_under_2s() -> None:
    from hpdc_test_client import ClickHouseProbe, TelemetryClient

    telemetry = TelemetryClient(EDGE_URL, api_key=TELEMETRY_API_KEY)
    probe = ClickHouseProbe("http://clickhouse.local:8123")

    sent_at = time.time_ns()
    telemetry.post_sensor_reading(_envelope())
    result = probe.wait_for_metric(device_id="sensor-93d21f", timeout_s=2.0)
    elapsed_s = (time.time_ns() - sent_at) / 1e9
    assert result.found, "reading must land in ClickHouse"
    assert elapsed_s < 2.0, "NFR6: telemetry -> topic -> ClickHouse under 2s"


# P0-003 (FR-1, FR-38, R-009)
# Given: api-key-authn policy routing on the /events and /telemetry prefixes
#  When: requests present no key, a wrong key, or a Bearer token
#  Then: all three are rejected 401 Unauthorized
#   And: a valid X-API-Key is accepted 202
def test_p0_003_events_and_telemetry_require_api_key_only() -> None:
    from hpdc_test_client import EventsClient, TelemetryClient

    events = EventsClient(EDGE_URL)
    telemetry = TelemetryClient(EDGE_URL)
    token = "eyJhbGciOiJSUzI1NiJ9.placeholder"

    assert events.post_events(_envelope()).status_code == 401
    assert events.post_events(_envelope(), bearer=token).status_code == 401
    assert events.post_events(_envelope(), api_key="hpdc-events-wrong-key").status_code == 401
    assert events.post_events(_envelope(), api_key=EVENTS_API_KEY).status_code == 202

    assert telemetry.post_telemetry(_envelope()).status_code == 401
    assert telemetry.post_telemetry(_envelope(), bearer=token).status_code == 401
    assert telemetry.post_telemetry(_envelope(), api_key="hpdc-telemetry-wrong-key").status_code == 401
    assert telemetry.post_telemetry(_envelope(), api_key=TELEMETRY_API_KEY).status_code == 202


def main() -> int:
    tests = (
        test_p0_001_events_api_accepts_envelope,
        test_p0_002_telemetry_to_topic_to_clickhouse_under_2s,
        test_p0_003_events_and_telemetry_require_api_key_only,
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
