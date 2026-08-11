#!/usr/bin/env python3
"""B-003 consumer harness: Pulsar/Kafka message-arrival + latency assertions.

Contract source:
  - output/test-artifacts/live-cluster-verification-register.md (B-003)
  - output/test-artifacts/atdd-checklist-hpdc-p0-system.md (Pulsar/Kafka Consumer
    Harness: consume telemetry partitioned topics + alert topics; success = enriched
    alert event received within expected latency; failure = no message within timeout)
  - tests/atdd/e2e/test_p0_alert_pipeline_journey.py (remote HTTP harness contract:
    GET /consume/{topic}?key={key})

Two backends:

  remote (live cluster, green phase):
      HPDC_CONSUMER_HARNESS_URL  - Pulsar consumer harness base URL
      HPDC_KAFKA_CONSUMER_HARNESS_URL - Kafka consumer harness base URL
      GET {base}/consume/{topic}?key={key} -> 200 + JSON list of messages

  local (offline, dev-side):
      NDJSON topic store under the edge data dir (default repo output/edge-ingest
      or $HPDC_EDGE_DATA_DIR), mirroring how scripts/services/events-ingest.py persists
      topics/alerts.incoming.ndjson. The local backend is what the offline
      contract tests exercise; the remote backend is what REG entries use once a
      cluster (B-001) exists.

Factories `pulsar_consumer_harness()` / `kafka_consumer_harness()` are the
contract the P0 scaffolds import.
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_S = 5.0

PULSAR_HARNESS_URL_ENV = "HPDC_CONSUMER_HARNESS_URL"
KAFKA_HARNESS_URL_ENV = "HPDC_KAFKA_CONSUMER_HARNESS_URL"


class ConsumerHarnessError(AssertionError):
    """A message-arrival or latency contract was violated (or no backend)."""


def _default_data_dir() -> Path:
    env = os.environ.get("HPDC_EDGE_DATA_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "output" / "edge-ingest"


def _topic_file(topic: str, data_dir: Path) -> Path:
    safe = topic.replace("/", ".")
    return data_dir / "topics" / f"{safe}.ndjson"


def _read_messages(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    messages: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        messages.append(entry)
    return messages


def _matches(messages: list[dict[str, Any]], key: str | None) -> list[dict[str, Any]]:
    if key is None:
        return messages
    return [
        m
        for m in messages
        if m.get("alert_id") == key
        or m.get("event_id") == key
        or m.get("device_id") == key
        or m.get("id") == key
        or m.get("message_id") == key
    ]


class PulsarConsumerHarness:
    """Message-arrival + latency assertions against a Pulsar topic.

    ``consume`` returns messages matching ``key`` (or all) within ``timeout_s``;
    ``assert_arrival`` fails the contract if none arrives in time; and
    ``assert_arrival_within_latency`` additionally bounds the wall-clock time
    from the start of the wait until the keyed message is observed.
    """

    def __init__(
        self,
        topic: str,
        *,
        harness_url: str | None = None,
        data_dir: Path | str | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self.topic = topic
        self.harness_url = harness_url or os.environ.get(PULSAR_HARNESS_URL_ENV)
        self.data_dir = Path(data_dir) if data_dir else _default_data_dir()
        self.timeout_s = timeout_s

    def _remote_consume(self, key: str | None) -> list[dict[str, Any]]:
        url = f"{self.harness_url}/consume/{urllib.parse.quote(self.topic, safe='')}"
        if key is not None:
            url += f"?key={urllib.parse.quote(key, safe='')}"
        with urllib.request.urlopen(url, timeout=self.timeout_s) as resp:
            body = json.loads(resp.read() or b"[]")
        return body if isinstance(body, list) else [body]

    def consume(self, key: str | None = None, timeout_s: float | None = None) -> list[dict[str, Any]]:
        budget = timeout_s if timeout_s is not None else self.timeout_s
        if self.harness_url:
            return _matches(self._remote_consume(key), key)
        deadline = time.monotonic() + budget
        path = _topic_file(self.topic, self.data_dir)
        while time.monotonic() < deadline:
            messages = _matches(_read_messages(path), key)
            if messages:
                return messages
            time.sleep(0.05)
        return []

    def assert_arrival(self, key: str | None = None, timeout_s: float | None = None) -> list[dict[str, Any]]:
        messages = self.consume(key=key, timeout_s=timeout_s)
        if not messages:
            where = f"key {key!r}" if key else "any message"
            raise ConsumerHarnessError(
                f"no message arrived on topic {self.topic!r} ({where}) within "
                f"{timeout_s if timeout_s is not None else self.timeout_s}s"
            )
        return messages

    def assert_arrival_within_latency(
        self,
        key: str | None = None,
        max_latency_ms: int = 2000,
        timeout_s: float | None = None,
    ) -> list[dict[str, Any]]:
        started = time.monotonic()
        messages = self.consume(key=key, timeout_s=timeout_s)
        latency_ms = (time.monotonic() - started) * 1000
        if not messages:
            where = f"key {key!r}" if key else "any message"
            raise ConsumerHarnessError(
                f"no message arrived on topic {self.topic!r} ({where}) within "
                f"{timeout_s if timeout_s is not None else self.timeout_s}s"
            )
        if latency_ms > max_latency_ms:
            raise ConsumerHarnessError(
                f"message arrived on {self.topic!r} after {latency_ms:.0f}ms, "
                f"exceeding the {max_latency_ms}ms budget"
            )
        return messages


class KafkaConsumerHarness(PulsarConsumerHarness):
    """Same contract over Kafka topics (secondary bus, Epic 5 alerts).

    Remote backend resolves HPDC_KAFKA_CONSUMER_HARNESS_URL; local backend
    reads the same NDJSON topic store.
    """

    def __init__(self, topic: str, **kwargs: Any) -> None:
        harness_url = kwargs.pop("harness_url", None) or os.environ.get(KAFKA_HARNESS_URL_ENV)
        super().__init__(topic, harness_url=harness_url, **kwargs)


def pulsar_consumer_harness(
    topic: str,
    *,
    harness_url: str | None = None,
    data_dir: Path | str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> PulsarConsumerHarness:
    """Factory for a Pulsar topic consumer harness (B-003 contract)."""
    return PulsarConsumerHarness(
        topic,
        harness_url=harness_url,
        data_dir=data_dir,
        timeout_s=timeout_s,
    )


def kafka_consumer_harness(
    topic: str,
    *,
    harness_url: str | None = None,
    data_dir: Path | str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> KafkaConsumerHarness:
    """Factory for a Kafka topic consumer harness (B-003 contract)."""
    return KafkaConsumerHarness(
        topic,
        harness_url=harness_url,
        data_dir=data_dir,
        timeout_s=timeout_s,
    )
