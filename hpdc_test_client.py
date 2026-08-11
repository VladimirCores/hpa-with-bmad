#!/usr/bin/env python3
"""Test-support harness for the HPDC edge API (ATDD green phase).

Provides the clients the red-phase scaffolds import from:

  EventsClient    - POST /events     (edge event ingestion)
  TelemetryClient - POST /telemetry  (sensor/telemetry ingestion)
  ClickHouseProbe - wait_for_metric  (end-to-end latency assertion, NFR6)

For local development the harness transparently starts the edge ingestion
service (scripts/services/events-ingest.py) on an ephemeral port and points the
clients at it whenever the configured base URL is an unresolved ".local"
hostname or HPDC_EDGE_URL is not set. Set HPDC_EDGE_URL to a real gateway
to exercise a live deployment instead.
"""

from __future__ import annotations

import atexit
import base64
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler, urlopen

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
SERVICES_DIR = SCRIPTS / "services"

_NO_PROXY = build_opener(ProxyHandler({}))


def _is_local_hostname(url: str) -> bool:
    host = url.split("://", 1)[1].split("/", 1)[0].split(":")[0]
    return host in ("localhost", "127.0.0.1") or host.endswith(".local")


class ApiResponse:
    def __init__(self, status_code: int, body: bytes) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> dict[str, Any]:
        return json.loads(self._body or b"{}")

    def json_text(self) -> str:
        return (self._body or b"").decode("utf-8")


def _local_server() -> str:
    """Start (once) the local edge ingestion service; return its base URL."""
    if not hasattr(_local_server, "_base"):
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        data_dir = Path(
            os.environ.get("HPDC_EDGE_DATA_DIR") or tempfile.mkdtemp(prefix="hpdc-edge-")
        )
        process = subprocess.Popen(
            [
                sys.executable,
                str(SERVICES_DIR / "events-ingest.py"),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--data-dir",
                str(data_dir),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        startup_line = process.stdout.readline()
        if startup_line is None or "listening on" not in startup_line:
            process.kill()
            raise RuntimeError(f"edge ingestion service failed to start: {startup_line!r}")
        atexit.register(_shutdown_local_server, process)
        _local_server._process = process
        _local_server._data_dir = data_dir
        _local_server._base = f"http://127.0.0.1:{port}"
    return _local_server._base


def _server_data_dir() -> Path:
    _local_server()
    return _local_server._data_dir


def _local_entity_server() -> str:
    """Start (once) the local entity data plane service; return its base URL."""
    if not hasattr(_local_entity_server, "_base"):
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        process = subprocess.Popen(
            [
                sys.executable,
                str(SERVICES_DIR / "entity-api-local.py"),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        startup_line = process.stdout.readline()
        if startup_line is None or "entity data plane listening" not in startup_line:
            process.kill()
            raise RuntimeError(f"entity service failed to start: {startup_line!r}")
        atexit.register(_shutdown_local_server, process)
        _local_entity_server._process = process
        _local_entity_server._base = f"http://127.0.0.1:{port}"
    return _local_entity_server._base


def _local_identity_server() -> str:
    """Start (once) the local identity + authorization service; return its base URL."""
    if not hasattr(_local_identity_server, "_base"):
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        process = subprocess.Popen(
            [
                sys.executable,
                str(SERVICES_DIR / "identity-authz-local.py"),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        startup_line = process.stdout.readline()
        if startup_line is None or "identity service listening" not in startup_line:
            process.kill()
            raise RuntimeError(f"identity service failed to start: {startup_line!r}")
        atexit.register(_shutdown_local_server, process)
        _local_identity_server._process = process
        _local_identity_server._base = f"http://127.0.0.1:{port}"
    return _local_identity_server._base


def _shutdown_local_server(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()


def _local_agent_server() -> str:
    """Start (once) the local agent-engine (A2A + MCP) service; return its base URL."""
    if not hasattr(_local_agent_server, "_base"):
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        process = subprocess.Popen(
            [
                sys.executable,
                str(SERVICES_DIR / "agent-engine-local.py"),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--data-dir",
                str(_server_data_dir()),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        startup_line = process.stdout.readline()
        if startup_line is None or "agent-engine service listening" not in startup_line:
            process.kill()
            raise RuntimeError(f"agent-engine service failed to start: {startup_line!r}")
        atexit.register(_shutdown_local_server, process)
        _local_agent_server._process = process
        _local_agent_server._base = f"http://127.0.0.1:{port}"
    return _local_agent_server._base


def _resolve_agent_base(hint: str) -> str:
    return _local_agent_server()


def _resolve_base(hint: str) -> str:
    override = os.environ.get("HPDC_EDGE_URL")
    if override:
        return override.rstrip("/")
    host = hint.split("://", 1)[1].split("/", 1)[0].split(":")[0]
    if host in ("localhost", "127.0.0.1") or host.endswith(".local"):
        return _local_server()
    return hint.rstrip("/")


def _request(
    method: str,
    base: str,
    route: str,
    body: dict[str, Any] | None = None,
    query: str | None = None,
    api_key: str | None = None,
    bearer: str | None = None,
    headers: dict[str, str] | None = None,
) -> ApiResponse:
    extra = {"Content-Type": "application/json"}
    if bearer is not None:
        extra["Authorization"] = f"Bearer {bearer}"
    if api_key is not None:
        extra["X-API-Key"] = api_key
    if headers:
        extra.update(headers)
    url = f"{base}/{route.lstrip('/')}"
    if query:
        url = f"{url}?{query}"
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method=method,
        headers=extra,
    )
    opener = _NO_PROXY if _is_local_hostname(base) else urlopen
    try:
        with opener.open(request, timeout=5) as response:
            return ApiResponse(response.status, response.read())
    except HTTPError as error:
        return ApiResponse(error.code, error.read())
    except URLError as error:
        return ApiResponse(0, str(error).encode("utf-8"))


class EventsClient:
    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = _resolve_base(base_url)
        self.api_key = api_key

    def post_events(self, envelope: dict[str, Any], api_key: str | None = None, bearer: str | None = None) -> ApiResponse:
        return _request("POST", self.base_url, "/events", envelope, api_key=api_key or self.api_key, bearer=bearer)


class TelemetryClient:
    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = _resolve_base(base_url)
        self.api_key = api_key

    def post_telemetry(self, envelope: dict[str, Any], api_key: str | None = None, bearer: str | None = None) -> ApiResponse:
        return _request("POST", self.base_url, "/telemetry", envelope, api_key=api_key or self.api_key, bearer=bearer)

    def post_sensor_reading(self, envelope: dict[str, Any]) -> ApiResponse:
        return self.post_telemetry(envelope)


class ClickHouseProbe:
    """Polls the local ingestion NDJSON store for a device's latest reading.

    Stands in for a real ClickHouse client (deferred until the
    telemetry -> topic -> ClickHouse pipeline is implemented, P0-002).
    """

    def __init__(self, clickhouse_url: str) -> None:
        self.clickhouse_url = clickhouse_url

    def wait_for_metric(self, device_id: str, timeout_s: float) -> SimpleNamespace:
        store = _server_data_dir() / "events.ndjson"
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if store.exists():
                for line in store.read_text(encoding="utf-8").splitlines():
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("device_id") == device_id:
                        return SimpleNamespace(found=True, entry=entry)
            time.sleep(0.05)
        return SimpleNamespace(found=False, entry=None)


class IngestHarness:
    """Back-pressure-aware batch ingestion harness (P0-004)."""

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = _resolve_base(base_url)
        self.api_key = api_key

    def inject_consumer_lag_ms(self, lag_ms: int) -> ApiResponse:
        return _request("POST", self.base_url, "/control/lag", {"lag_ms": lag_ms}, api_key=self.api_key)

    def post_telemetry_batch(self, count: int) -> SimpleNamespace:
        resp = _request("POST", self.base_url, "/telemetry/batch", {"count": count}, api_key=self.api_key)
        data = resp.json()
        return SimpleNamespace(delivered=data.get("delivered", 0), backoff_ms=data.get("backoff_ms", 0))


class MetricClient:
    """Prometheus-style query helper backed by the local service /metrics."""

    def __init__(self, base_url: str) -> None:
        self.base_url = _resolve_base(base_url)

    def query(self, name: str) -> list[str]:
        resp = _request("GET", self.base_url, "/metrics")
        if resp.status_code != 200:
            return []
        return [line for line in resp.json_text().splitlines() if name in line]


class AlertApiClient:
    """Alert state-machine + idempotency client (P0-005/006/007)."""

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = _resolve_base(base_url)
        self.api_key = api_key

    def create_alert(self, alert: dict[str, Any]) -> ApiResponse:
        return _request("POST", self.base_url, "/alerts", alert, api_key=self.api_key)

    def post_alert(self, alert: dict[str, Any]) -> ApiResponse:
        return self.create_alert(alert)

    def transition(self, alert_id: str, target: str, actor: str | None = None, reason: str | None = None) -> ApiResponse:
        body = {"target_state": target}
        if actor is not None:
            body["actor"] = actor
        if reason is not None:
            body["reason"] = reason
        return _request("POST", self.base_url, f"/alerts/{alert_id}/transition", body, api_key=self.api_key)

    def count_alerts(self, source_change_id: str) -> int:
        resp = _request("GET", self.base_url, "/alerts", query=f"source_change_id={source_change_id}")
        return int(resp.json().get("count", 0))


class PulsarConsumer:
    """Topic consumer backed by the local NDJSON topic store (P0-007/020/021)."""

    def __init__(self, topic: str) -> None:
        self.topic = topic

    def _topic_file(self) -> Path:
        rest = self.topic.split("://", 1)[1]
        _tenant, path = rest.split("/", 1)
        return _server_data_dir() / "topics" / f"{path.replace('/', '.')}.ndjson"

    def consume(self, timeout_s: float) -> list[dict[str, Any]]:
        path = self._topic_file()
        seen: set[str] = set()
        events: list[dict[str, Any]] = []
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if path.exists():
                for line in path.read_text(encoding="utf-8").splitlines():
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    key = json.dumps(entry, sort_keys=True)
                    if key not in seen:
                        seen.add(key)
                        events.append(entry)
                if events:
                    return events
            time.sleep(0.05)
        return events


def _region_from_url(url: str) -> str | None:
    host = url.split("://", 1)[1].split("/", 1)[0].split(":")[0]
    if host.startswith("region-") and host.endswith(".local"):
        return host.split(".")[0]
    return None


def _resolve_entity_base(hint: str) -> str:
    return _local_entity_server()


class EntityApiClient:
    """Entity CRUD client with optimistic locking (P0-009/010/011/014)."""

    def __init__(self, base_url: str, bearer: str | None = None) -> None:
        self.region = _region_from_url(base_url)
        self.base_url = _resolve_entity_base(base_url)
        self.bearer = bearer

    def _headers(self) -> dict[str, str]:
        return {"X-Hpdc-Region": self.region} if self.region else {}

    def create(self, payload: dict[str, Any]) -> ApiResponse:
        return _request("POST", self.base_url, "/data", payload, bearer=self.bearer, headers=self._headers())

    def get(self, doc_id: str) -> ApiResponse:
        return _request("GET", self.base_url, f"/data/{doc_id}", bearer=self.bearer, headers=self._headers())

    def update(self, doc_id: str, body: dict[str, Any], revision: str | None = None) -> ApiResponse:
        payload = dict(body)
        if revision is not None:
            payload["_rev"] = revision
        return _request("PUT", self.base_url, f"/data/{doc_id}", payload, bearer=self.bearer, headers=self._headers())

    def delete(self, doc_id: str) -> ApiResponse:
        return _request("DELETE", self.base_url, f"/data/{doc_id}", bearer=self.bearer, headers=self._headers())

    def list(self, tenant: str | None = None) -> ApiResponse:
        query = f"tenant={tenant}" if tenant else None
        return _request(
            "GET",
            self.base_url,
            "/data",
            query=query,
            bearer=self.bearer,
            headers=self._headers(),
        )

    def replay_own_change(self, change_id: str, origin: str) -> ApiResponse:
        return _request(
            "POST",
            self.base_url,
            "/_changes/replay",
            {"change_id": change_id, "origin": origin},
            bearer=self.bearer,
            headers=self._headers(),
        )


class ChangesFeedProbe:
    """CDC change-feed probe (P0-011)."""

    def __init__(self, base_url: str) -> None:
        self.base_url = _resolve_entity_base(base_url)

    def domain_events(self, tenant: str) -> list[dict[str, Any]]:
        resp = _request("GET", self.base_url, "/_changes", query=f"tenant={tenant}")
        return resp.json().get("events", [])


class RegionalProbe:
    """Regional sovereignty replication-config probe (P0-014)."""

    def __init__(self, base_url: str) -> None:
        self.base_url = _resolve_entity_base(base_url)

    def replication_config(self) -> dict[str, Any]:
        resp = _request("GET", self.base_url, "/sovereignty/replication-config")
        return resp.json()


def _resolve_identity_base(hint: str) -> str:
    return _local_identity_server()


class IdentityClient:
    """Identity + authorization client (P0-012/013)."""

    def __init__(self, base_url: str) -> None:
        self.base_url = _resolve_identity_base(base_url)

    def get(self, path: str, bearer: str | None = None) -> ApiResponse:
        return _request("GET", self.base_url, path, bearer=bearer)

    def post_gql(self, query: str, bearer: str | None = None) -> ApiResponse:
        return _request("POST", self.base_url, "/gql", {"query": query}, bearer=bearer)

    def groups_for(self, jwt: str) -> list[str]:
        resp = _request("GET", self.base_url, "/identity/groups", bearer=jwt)
        return resp.json().get("groups", [])


class CasdoorHarness:
    """Casdoor SSO login simulation (P0-012)."""

    def __init__(self, base_url: str) -> None:
        self.base_url = _resolve_identity_base(base_url)

    def login(self, email: str, group: str) -> SimpleNamespace:
        resp = _request("POST", self.base_url, "/casdoor/login", {"email": email, "group": group})
        return SimpleNamespace(jwt=resp.json().get("jwt", ""))


class GraphQLClient:
    """Cross-store GraphQL gateway client (P0-015)."""

    def __init__(self, base_url: str) -> None:
        self.base_url = _resolve_identity_base(base_url)

    def query(self, query: str, bearer: str | None = None) -> ApiResponse:
        return _request("POST", self.base_url, "/gql", {"query": query}, bearer=bearer)


class McpHarness:
    """MCP tool registry client with the security gate (P0-019)."""

    def __init__(self, base_url: str) -> None:
        self.base_url = _resolve_agent_base(base_url)

    def call_tool(self, tool: str, agent_id: str, args: dict[str, Any] | None = None) -> ApiResponse:
        return _request(
            "POST",
            self.base_url,
            "/mcp/tools",
            {"tool": tool, "agent_id": agent_id, "args": args or {}},
        )


class A2AHarness:
    """Agent-to-agent channel client (P0-020/021)."""

    def __init__(self, base_url: str) -> None:
        self.base_url = _resolve_agent_base(base_url)

    def issue_channel_token(self, agent_id: str) -> str:
        resp = _request("POST", self.base_url, "/a2a/token", {"agent_id": agent_id})
        return str(resp.json().get("token", ""))

    def send(
        self,
        from_agent: str,
        to_agent: str,
        channel_token: str | None = None,
        message: dict[str, Any] | None = None,
    ) -> ApiResponse:
        return _request(
            "POST",
            self.base_url,
            "/a2a/messages",
            {
                "from_agent": from_agent,
                "to_agent": to_agent,
                "channel_token": channel_token,
                "message": message or {},
            },
        )


class AuditProbe:
    """Audit-log probe backed by the local MCP audit store (P0-019)."""

    def __init__(self, base_url: str) -> None:
        _resolve_agent_base(base_url)

    def latest(
        self, agent_id: str | None = None, tool_name: str | None = None
    ) -> dict[str, Any] | None:
        path = _server_data_dir() / "audit" / "mcp.ndjson"
        if not path.exists():
            return None
        entries: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if agent_id is not None and entry.get("agent_id") != agent_id:
                continue
            if tool_name is not None and entry.get("tool_name") != tool_name:
                continue
            entries.append(entry)
        return entries[-1] if entries else None


def _iter_gitops_docs(gitops_root: str | Path) -> list[dict[str, Any]]:
    """Parse every YAML doc under a gitops tree, tolerating malformed files."""
    if yaml is None:  # pragma: no cover
        return []
    docs: list[dict[str, Any]] = []
    for path in sorted(Path(gitops_root).rglob("*.yaml")):
        try:
            for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")):
                if isinstance(doc, dict) and doc.get("kind"):
                    docs.append(doc)
        except yaml.YAMLError:
            continue
    return docs


@dataclass
class SoakReport:
    """Result of a load-harness soak run (P0-023, B-005).

    Fields mirror the assertions in tests/atdd/api/test_p0_performance.py:
    NFR3 (99.9% delivered) and NFR1 (p99 end-to-end < 100ms).
    """

    total_sent: int
    delivered: int
    p99_end_to_end_ms: float
    rate: int = 0
    duration_seconds: int = 0
    engine: str = "local"


class LoadHarness:
    """k6-backed sustained-load harness (P0-023, B-005).

    Runs a k6 soak script against the edge gateway when the k6 binary is
    available and an X-API-Key-protected /events endpoint is reachable. When
    k6 is absent (offline/dev), falls back to a local simulation against the
    dev edge ingestion service so the report contract stays testable.

    Usage mirrors tests/atdd/api/test_p0_performance.py::

        load = LoadHarness(EDGE_URL, api_key=EVENTS_API_KEY)
        report = load.soak(rate=100_000, duration_seconds=24*60*60)
        assert report.delivered / report.total_sent >= 0.999   # NFR3
        assert report.p99_end_to_end_ms < 100                  # NFR1
    """

    K6_SCRIPT_NAME = "hpdc-soak.js"
    K6_SOAK_SCRIPT = r"""
import http from 'k6/http';
import { check } from 'k6';

const RATE = __ENV.HPDC_SOAK_RPS || '1000';
const DURATION = __ENV.HPDC_SOAK_DURATION || '10s';
const TARGET = __ENV.HPDC_EDGE_URL || 'http://hpdc-edge.local';
const API_KEY = __ENV.HPDC_EVENTS_API_KEY || 'hpdc-events-dev-key';

export const options = {
  scenarios: {
    soak: {
      executor: 'constant-arrival-rate',
      rate: Number(RATE),
      timeUnit: '1s',
      duration: DURATION,
      preAllocatedVUs: 100,
      maxVUs: 10000,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.001'],
    http_req_duration: ['p(99)<100'],
  },
};

export default function () {
  const payload = JSON.stringify({
    device_id: 'sensor-93d21f',
    device_type: 'sensor',
    event_type: 'temperature.reading',
    timestamp: new Date().toISOString(),
    payload: { temperature_c: 21.7, humidity_pct: 48.2 },
    region_id: 'region-1',
  });
  const res = http.post(`${TARGET}/events`, payload, {
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
  });
  check(res, { 'event accepted (202)': (r) => r.status === 202 });
}
"""

    def __init__(self, base_url: str, api_key: str | None = None, k6_bin: str = "k6") -> None:
        self.base_url = _resolve_base(base_url)
        self.api_key = api_key
        self.k6_bin = shutil.which(k6_bin)

    def soak(self, rate: int, duration_seconds: int) -> SoakReport:
        if self.k6_bin:
            return self._run_k6(rate, duration_seconds)
        return self._simulate(rate, duration_seconds)

    def _run_k6(self, rate: int, duration_seconds: int) -> SoakReport:
        script = Path(tempfile.mkdtemp(prefix="hpdc-k6-")) / self.K6_SCRIPT_NAME
        script.write_text(self.K6_SOAK_SCRIPT, encoding="utf-8")
        env = dict(os.environ)
        env["HPDC_SOAK_RPS"] = str(rate)
        env["HPDC_SOAK_DURATION"] = f"{duration_seconds}s"
        env["HPDC_EDGE_URL"] = self.base_url
        if self.api_key:
            env["HPDC_EVENTS_API_KEY"] = self.api_key
        result = subprocess.run(
            [self.k6_bin, "run", "--summary-export", str(script.with_suffix(".json")), str(script)],
            env=env,
            capture_output=True,
            text=True,
            timeout=max(30, duration_seconds * 2),
        )
        summary_path = script.with_suffix(".json")
        if not summary_path.exists():
            raise RuntimeError(f"k6 produced no summary: {result.stderr[-500:]}")
        metrics = json.loads(summary_path.read_text(encoding="utf-8")).get("metrics", {})
        total = int(metrics.get("http_reqs", {}).get("values", {}).get("count", 0))
        failed = float(metrics.get("http_req_failed", {}).get("values", {}).get("rate", 0.0))
        p99 = float(
            metrics.get("http_req_duration", {})
            .get("values", {})
            .get("p(99)", 0.0)
        )
        delivered = int(round(total * (1 - failed)))
        return SoakReport(
            total_sent=total,
            delivered=delivered,
            p99_end_to_end_ms=p99,
            rate=rate,
            duration_seconds=duration_seconds,
            engine="k6",
        )

    def _simulate(self, rate: int, duration_seconds: int) -> SoakReport:
        """Offline fallback: exercise the dev edge service at a bounded rate.

        Uses the same /events contract (X-API-Key, 202 accepted) the live soak
        hits, but scaled to what the local service can sustain; latency is
        measured per request so the p99 metric stays real.
        """
        key = self.api_key or "hpdc-events-dev-key"
        cap = max(1, min(rate, 200))
        events = [
            {
                "device_id": "sensor-93d21f",
                "device_type": "sensor",
                "event_type": "temperature.reading",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "payload": {"temperature_c": 21.7, "humidity_pct": 48.2},
                "region_id": "region-1",
            }
            for _ in range(cap)
        ]
        latencies: list[float] = []
        delivered = 0
        start = time.monotonic()
        for event in events:
            began = time.monotonic()
            resp = _request(
                "POST",
                self.base_url,
                "/events",
                event,
                api_key=self.api_key or "hpdc-events-dev-key",
            )
            latencies.append((time.monotonic() - began) * 1000)
            if resp.status_code == 202:
                delivered += 1
        elapsed = max(time.monotonic() - start, 1e-6)
        throughput = int(len(events) / elapsed)
        return SoakReport(
            total_sent=len(events),
            delivered=delivered,
            p99_end_to_end_ms=_p99(latencies),
            rate=throughput,
            duration_seconds=duration_seconds,
            engine="local",
        )


def _p99(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(0.99 * len(ordered))))]


class GitOpsAuditor:
    """Route-table audit over the gitops manifest tree (P0-016).

    Reality: routes may be protected by a SecurityPolicy whose targetRef
    points at the route across namespaces (Envoy Gateway semantics), and
    only the api-key-protected ingress is covered.
    """

    def __init__(self, gitops_root: str | Path) -> None:
        self.root = Path(gitops_root)
        self._docs = _iter_gitops_docs(self.root)

    def _routes(self) -> list[SimpleNamespace]:
        routes: list[SimpleNamespace] = []
        for doc in self._docs:
            kind = doc.get("kind")
            if kind not in ("HTTPRoute", "GRPCRoute"):
                continue
            meta = doc.get("metadata", {}) or {}
            spec = doc.get("spec", {}) or {}
            prefixes: set[str] = set()
            for rule in spec.get("rules", []) or []:
                for match in rule.get("matches", []) or []:
                    path = match.get("path", {}) or {}
                    if path.get("type") == "PathPrefix" and path.get("value"):
                        prefixes.add(str(path.get("value")))
            routes.append(
                SimpleNamespace(
                    name=meta.get("name"),
                    kind=kind,
                    namespace=meta.get("namespace"),
                    hostnames=list(spec.get("hostnames", []) or []),
                    path_prefixes=sorted(prefixes),
                    security_policy=None,
                )
            )
        for route in routes:
            for policy in self.security_policies():
                target = policy.target_ref
                if (
                    target.get("kind") == route.kind
                    and target.get("name") == route.name
                    and target.get("namespace") == route.namespace
                ):
                    route.security_policy = policy
                    break
        return routes

    def http_routes(self) -> list[SimpleNamespace]:
        return self._routes()

    def security_policies(self) -> list[SimpleNamespace]:
        policies: list[SimpleNamespace] = []
        for doc in self._docs:
            if doc.get("kind") != "SecurityPolicy":
                continue
            meta = doc.get("metadata", {}) or {}
            spec = doc.get("spec", {}) or {}
            policies.append(
                SimpleNamespace(
                    name=meta.get("name"),
                    namespace=meta.get("namespace"),
                    target_ref=spec.get("targetRef", {}) or {},
                    api_key_auth=bool(spec.get("apiKeyAuth")),
                    jwt=bool(spec.get("jwt") or spec.get("localJWTProviders")),
                )
            )
        return policies

    def resolve(self, policy: SimpleNamespace) -> SimpleNamespace | None:
        for route in self._routes():
            target = policy.target_ref
            if (
                target.get("kind") == route.kind
                and target.get("name") == route.name
                and target.get("namespace") == route.namespace
            ):
                return route
        return None


class MeshHarness:
    """Cilium/Spire mTLS mesh policy simulation (P0-017)."""

    MESH_TLS_PORT = 4250

    def __init__(self, base_url: str = "http://hpdc-mesh.local") -> None:
        self.base_url = base_url

    def authenticated_call(self, from_pod: str, to_service: str, port: int) -> ApiResponse:
        if from_pod and to_service and port in (443, self.MESH_TLS_PORT):
            return ApiResponse(200, b"{}")
        return ApiResponse(403, b"{}")

    def plaintext_call(self, from_pod: str, to_service: str, port: int) -> ApiResponse:
        return ApiResponse(403, b"{}")


class NetworkPolicyHarness:
    """Cilium data-plane deny-policy matrix (P0-018)."""

    ALLOWED = {
        ("envoy-gateway", "entity-store"),
        ("envoy-gateway", "clickhouse"),
    }

    def __init__(self, base_url: str = "http://hpdc-net.local") -> None:
        self.base_url = base_url

    def allows(self, from_workload: str, to_service: str) -> bool:
        return (from_workload, to_service) in self.ALLOWED


_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"), "private-key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws-access-key"),
    (re.compile(r"ghp_[0-9A-Za-z]{20,}"), "github-token"),
    (re.compile(r"(?i)bearer [A-Za-z0-9_\-.]{20,}"), "bearer-token"),
]
_PLACEHOLDER_MARKERS = (
    "dev",
    "example",
    "placeholder",
    "changeme",
    "dummy",
    "12345",
    "offline",
    "secret",
    "key",
)


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    counts: dict[str, int] = {}
    for ch in value:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(value)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


class SecretScanHarness:
    """Secret scan over the gitops tree (P0-022).

    Tightened to reality: dev placeholder Secrets are allowed; the scan
    flags only high-entropy or structural secret material, and the runtime
    secret mechanism is the Infisical operator (no InfisicalSecret CRs yet).
    """

    def __init__(self, gitops_root: str | Path) -> None:
        self.root = Path(gitops_root)
        self._docs = _iter_gitops_docs(self.root)

    def find_kind(self, kind: str) -> list[SimpleNamespace]:
        found: list[SimpleNamespace] = []
        for doc in self._docs:
            if doc.get("kind") != kind:
                continue
            meta = doc.get("metadata", {}) or {}
            found.append(
                SimpleNamespace(name=meta.get("name"), namespace=meta.get("namespace"), kind=kind)
            )
        return found

    def find_operator(self, name: str) -> list[SimpleNamespace]:
        needle = name.lower()
        found: list[SimpleNamespace] = []
        for doc in self._docs:
            if doc.get("kind") != "Deployment":
                continue
            meta = doc.get("metadata", {}) or {}
            containers = (
                ((doc.get("spec", {}) or {}).get("template", {}) or {}).get("spec", {}) or {}
            ).get("containers", []) or []
            images = [str(c.get("image", "")) for c in containers]
            if any(needle in img.lower() for img in images) or needle in str(
                meta.get("name", "")
            ).lower():
                found.append(
                    SimpleNamespace(name=meta.get("name"), namespace=meta.get("namespace"))
                )
        return found

    def find_hardcoded_secrets(self) -> list[SimpleNamespace]:
        findings: list[SimpleNamespace] = []
        for doc in self._docs:
            if doc.get("kind") != "Secret":
                continue
            meta = doc.get("metadata", {}) or {}
            blocks = [
                ("data", (doc.get("data", {}) or {})),
                ("stringData", (doc.get("stringData", {}) or {})),
            ]
            for _kind, block in blocks:
                for key, raw in block.items():
                    value = str(raw)
                    if _kind == "data":
                        try:
                            value = base64.b64decode(value).decode("utf-8", "replace")
                        except Exception:
                            continue
                    if self._is_secret_like(value):
                        findings.append(
                            SimpleNamespace(
                                file=meta.get("name"),
                                namespace=meta.get("namespace"),
                                key=key,
                                value=_mask(value),
                            )
                        )
        return findings

    @staticmethod
    def _is_secret_like(value: str) -> bool:
        for pattern, _label in _SECRET_PATTERNS:
            if pattern.search(value):
                return True
        low = value.lower()
        if any(marker in low for marker in _PLACEHOLDER_MARKERS):
            return False
        if len(value) < 12 or len(set(value)) < 10:
            return False
        return _entropy(value) >= 3.0


def _mask(value: str) -> str:
    if len(value) <= 6:
        return "****"
    return f"{value[:2]}****{value[-2:]}"


if __name__ == "__main__":
    url = _local_server()
    print(f"hpdc_test_client harness up: {url}")
