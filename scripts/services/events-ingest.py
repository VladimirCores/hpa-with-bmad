#!/usr/bin/env python3
"""Local HPDC edge ingestion + alert pipeline service (dev harness for ATDD).

Simulates the edge dataplane contract for green-phase acceptance tests:

  POST  /events                  - accepts a CommonEnvelope (ULID + RFC3339)
  POST  /telemetry               - accepts telemetry envelopes
  POST  /telemetry/batch         - back-pressure-aware batch ingest (P0-004)
  POST  /control/lag             - inject consumer lag in ms (P0-004)
  GET   /metrics                 - Prometheus-style text (ingestion_dropped_total)
  POST  /alerts                  - create alert (state machine, idempotency)
  POST  /alerts/{id}/transition  - alert state transition (409 on invalid)
  GET   /alerts?source_change_id - alert count by idempotency source
  GET   /metrics                 - drop/back-pressure counters

Ingested and enriched alert events are persisted as NDJSON (event + topic)
so the harness can assert arrival and end-to-end behavior. This is a local
stand-in for the Envoy Gateway edge route, Pulsar topics, and the alert
rule engine.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
EVENTS_API_KEY = "hpdc-events-dev-key"
TELEMETRY_API_KEY = "hpdc-telemetry-dev-key"

REQUIRED_FIELDS = (
    "device_id",
    "device_type",
    "event_type",
    "timestamp",
    "payload",
    "region_id",
)
MAX_BODY_BYTES = 64 * 1024

ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

BACKPRESSURE_THRESHOLD_MS = 50_000
DROP_BUDGET_MS = 200_000
BACKOFF_BASE_MS = 200

ALERT_STATES = ("initial", "acknowledged", "investigating", "resolved", "closed")
ALERT_TRANSITIONS = {
    "initial": ("acknowledged",),
    "acknowledged": ("investigating",),
    "investigating": ("resolved",),
    "resolved": ("closed",),
    "closed": (),
}

DEVICE_CONTEXT = {
    "device-8193f4": {"region_id": "region-1", "tenant_id": "company:acme"},
    "sensor-93d21f": {"region_id": "region-1", "tenant_id": "company:acme"},
}


def ulid() -> str:
    """Generate a 26-char Crockford base32 ULID (48-bit time + 80-bit randomness)."""
    timestamp = int(time.time() * 1000)
    time_encoded = ""
    for i in range(10):
        shift = (10 - i - 1) * 5
        time_encoded += ULID_ALPHABET[(timestamp >> shift) & 0x1F]
    random_bytes = secrets.token_bytes(10)
    value = int.from_bytes(random_bytes, "big")
    random_encoded = ""
    for i in range(16):
        shift = (16 - i - 1) * 5
        random_encoded += ULID_ALPHABET[(value >> shift) & 0x1F]
    return (time_encoded + random_encoded)[:26]


def rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def validate_envelope(data: Any) -> None:
    if not isinstance(data, dict):
        raise ValueError("envelope must be a JSON object")
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise ValueError(f"missing envelope fields: {', '.join(missing)}")
    if not isinstance(data.get("payload"), dict):
        raise ValueError("payload must be a JSON object")
    timestamp = data.get("timestamp")
    if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
        raise ValueError("timestamp must be an RFC3339 string ending in Z")


class EdgeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _reply(self, status: int, body: dict[str, Any]) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length > MAX_BODY_BYTES:
            raise ValueError("payload too large")
        raw = self.rfile.read(length)
        return json.loads(raw)

    def _auth_ok(self, expected: str) -> bool:
        key = self.headers.get("X-API-Key")
        return key is not None and key == expected and self.headers.get("Authorization") is None

    def _log_ndjson(self, path: str, entry: dict[str, Any]) -> None:
        log_path = Path(self.server.data_dir) / path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def _reject_or_accept(self, route: str) -> None:
        expected = EVENTS_API_KEY if route == "/events" else TELEMETRY_API_KEY
        if not self._auth_ok(expected):
            self._reply(401, {"error": "unauthorized"})
            return
        try:
            data = self._read_body()
            validate_envelope(data)
        except (json.JSONDecodeError, ValueError) as exc:
            self._reply(400, {"error": str(exc)})
            return
        event_id = ulid()
        accepted_at = rfc3339()
        self._log_ndjson("events.ndjson", dict(data, event_id=event_id, accepted_at=accepted_at, route=route))
        self._reply(202, {"event_id": event_id, "accepted_at": accepted_at})

    def _telemetry_batch(self) -> None:
        if not self._auth_ok(EVENTS_API_KEY) and not self._auth_ok(TELEMETRY_API_KEY):
            self._reply(401, {"error": "unauthorized"})
            return
        try:
            body = self._read_body()
        except (json.JSONDecodeError, ValueError) as exc:
            self._reply(400, {"error": str(exc)})
            return
        count = int(body.get("count", 0))
        lag = self.server.lag_ms
        if lag >= DROP_BUDGET_MS:
            self.server.dropped_total += count
            self._reply(202, {"delivered": 0, "dropped": count, "backoff_ms": BACKOFF_BASE_MS * 2**12})
            return
        if lag >= BACKPRESSURE_THRESHOLD_MS:
            self.server.backoff_count += 1
            backoff_ms = BACKOFF_BASE_MS * 2**self.server.backoff_count
            self._reply(202, {"delivered": count, "dropped": 0, "backoff_ms": backoff_ms})
            return
        self.server.backoff_count = 0
        self._reply(202, {"delivered": count, "dropped": 0, "backoff_ms": 0})

    def _control_lag(self) -> None:
        if not self._auth_ok(EVENTS_API_KEY):
            self._reply(401, {"error": "unauthorized"})
            return
        try:
            body = self._read_body()
        except (json.JSONDecodeError, ValueError) as exc:
            self._reply(400, {"error": str(exc)})
            return
        self.server.lag_ms = int(body.get("lag_ms", 0))
        if self.server.lag_ms >= DROP_BUDGET_MS:
            self.server.dropped_total += 1
        self._reply(200, {"lag_ms": self.server.lag_ms})

    def _metrics(self) -> None:
        body = (
            "# HELP ingestion_dropped_total Messages dropped by the ingestion consumer.\n"
            f'ingestion_dropped_total{{reason="consumer_lag"}} {self.server.dropped_total}\n'
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _enriched_event(self, alert: dict[str, Any]) -> dict[str, Any]:
        context = DEVICE_CONTEXT.get(alert.get("device_id"), {"region_id": "region-1", "tenant_id": "company:acme"})
        return {
            "alert_id": alert["alert_id"],
            "device_id": alert.get("device_id"),
            "severity": alert.get("severity"),
            "timestamp": alert.get("timestamp"),
            "enriched": {
                "region_id": context["region_id"],
                "tenant_id": context["tenant_id"],
                "rule": (alert.get("metadata") or {}).get("rule"),
            },
        }

    def _create_alert(self) -> None:
        if not self._auth_ok(EVENTS_API_KEY):
            self._reply(401, {"error": "unauthorized"})
            return
        try:
            alert = self._read_body()
        except (json.JSONDecodeError, ValueError) as exc:
            self._reply(400, {"error": str(exc)})
            return
        alert_id = alert.get("alert_id")
        if not alert_id:
            self._reply(400, {"error": "alert_id is required"})
            return
        source_change_id = alert.get("source_change_id")
        if source_change_id and source_change_id in self.server.idempotency:
            original = self.server.idempotency[source_change_id]
            existing = self.server.alerts[original]
            self._reply(200, {"alert_id": original, "state": existing["state"]})
            return
        record = {
            "alert_id": alert_id,
            "state": "initial",
            "body": alert,
            "created_at": rfc3339(),
            "history": [],
        }
        self.server.alerts[alert_id] = record
        if source_change_id:
            self.server.idempotency[source_change_id] = alert_id
        self._log_ndjson("topics/alerts.incoming.ndjson", self._enriched_event(alert))
        self._reply(202, {"alert_id": alert_id, "state": "initial"})

    def _transition_alert(self, alert_id: str) -> None:
        if not self._auth_ok(EVENTS_API_KEY):
            self._reply(401, {"error": "unauthorized"})
            return
        try:
            body = self._read_body()
        except (json.JSONDecodeError, ValueError) as exc:
            self._reply(400, {"error": str(exc)})
            return
        record = self.server.alerts.get(alert_id)
        if record is None:
            self._reply(404, {"error": "alert not found"})
            return
        target = body.get("target_state")
        current = record["state"]
        if target not in ALERT_TRANSITIONS.get(current, ()):
            self._reply(409, {"error": f"invalid transition {current} -> {target}"})
            return
        record["state"] = target
        record["history"].append({"to": target, "actor": body.get("actor"), "reason": body.get("reason")})
        self._reply(200, {"alert_id": alert_id, "state": target})

    def _count_alerts(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        source_change_id = (query.get("source_change_id") or [None])[0]
        if source_change_id is None:
            self._reply(400, {"error": "source_change_id is required"})
            return
        count = 1 if source_change_id in self.server.idempotency else 0
        self._reply(200, {"count": count})

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/metrics":
            self._metrics()
        elif path == "/alerts":
            self._count_alerts()
        else:
            self._reply(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/events", "/telemetry"):
            self._reject_or_accept(path)
        elif path == "/telemetry/batch":
            self._telemetry_batch()
        elif path == "/control/lag":
            self._control_lag()
        elif path == "/alerts":
            self._create_alert()
        elif path.startswith("/alerts/") and path.endswith("/transition"):
            alert_id = path[len("/alerts/") : -len("/transition")]
            self._transition_alert(alert_id)
        else:
            self._reply(404, {"error": "not found"})

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[events-ingest] %s\n" % (fmt % args))


class EdgeServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], data_dir: Path) -> None:
        self.data_dir = data_dir
        self.lag_ms = 0
        self.backoff_count = 0
        self.dropped_total = 0
        self.alerts: dict[str, dict[str, Any]] = {}
        self.idempotency: dict[str, str] = {}
        super().__init__(server_address, EdgeHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local HPDC edge ingestion + alert pipeline service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument(
        "--data-dir",
        default=str(ROOT / "output" / "edge-ingest"),
        help="NDJSON persistence directory",
    )
    args = parser.parse_args()
    server = EdgeServer((args.host, args.port), Path(args.data_dir))
    print(f"edge ingestion listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
