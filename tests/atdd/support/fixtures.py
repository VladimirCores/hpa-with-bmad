#!/usr/bin/env python3
"""Minimal ATDD red-phase fixture infrastructure for HPDC P0 scaffolds.

These are the shared credentials, URLs, and helper contracts that the
tests/atdd/ red-phase scaffolds reference. The green-phase implementation
must satisfy these contracts:

- hpdc_test_client: the API test client module the scaffolds import
- pulsar_consumer_harness: message-arrival assertions for internal topics
- clickhouse_probe: latency/round-trip assertions for telemetry

All values here mirror the deployed manifests under gitops/.
"""

from __future__ import annotations

from dataclasses import dataclass

EVENTS_API_KEY = "hpdc-events-dev-key"
TELEMETRY_API_KEY = "hpdc-telemetry-dev-key"

EDGE_URL = "http://hpdc-edge.local"
CLICKHOUSE_URL = "http://clickhouse.local:8123"
PULSAR_URL = "pulsar://pulsar.local:6650"
KAFKA_URL = "kafka.local:9092"

CASDOOR_ROLES = (
    "operator",
    "manager",
    "administrator",
    "technic",
    "developer",
    "CEO",
    "client",
)


@dataclass(frozen=True)
class Envelope:
    device_id: str
    device_type: str
    event_type: str
    timestamp: str
    payload: dict
    region_id: str


def envelope(device_id: str = "sensor-93d21f", device_type: str = "sensor") -> Envelope:
    return Envelope(
        device_id=device_id,
        device_type=device_type,
        event_type="temperature.reading",
        timestamp="2026-08-07T13:15:47.123Z",
        payload={"temperature_c": 21.7, "humidity_pct": 48.2},
        region_id="region-1",
    )
