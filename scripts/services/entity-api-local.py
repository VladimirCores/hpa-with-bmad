#!/usr/bin/env python3
"""Local HPDC entity data plane service (dev harness for ATDD P0-009..014).

Simulates the entity CRUD API, optimistic locking, CDC change feed, and
regional sovereignty contract:

  POST   /data                     - create entity (201 + _rev)
  GET    /data/{id}                - read entity (200) or 404
  PUT    /data/{id}                - update (200); stale _rev -> 409
  DELETE /data/{id}                - delete (204)
  GET    /_changes?tenant=         - domain events for a tenant
  POST   /_changes/replay          - replay a change; origin=self is ignored
  GET    /sovereignty/replication-config - regional replication defaults

Regions are isolated stores selected by the X-Hpdc-Region header (region-1 /
region-2 / default). A document written to region-1 is never visible from
region-2 unless replication is explicitly configured. Auth is a bearer token
carrying a role (e.g. role=admin).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]

ROLE_RE = re.compile(r"role=([A-Za-z0-9_]+)")
TENANT_RE = re.compile(r"tenant=([^ .]+)")


class EntityStore:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, Any]] = {}
        self.domain_events: list[dict[str, Any]] = []

    def create(self, doc: dict[str, Any], tenant: str | None = None) -> dict[str, Any]:
        doc_id = doc["id"]
        revision = 1
        rev = _rev(doc_id, revision)
        self.documents[doc_id] = {
            "doc": doc,
            "revision": revision,
            "_rev": rev,
            "tenant": tenant or doc.get("company"),
        }
        return {"id": doc_id, "_rev": rev}

    def get(self, doc_id: str) -> dict[str, Any] | None:
        record = self.documents.get(doc_id)
        if record is None:
            return None
        return dict(record["doc"], _rev=record["_rev"])

    def update(self, doc_id: str, body: dict[str, Any], revision: str) -> str:
        record = self.documents.get(doc_id)
        if record is None:
            raise KeyError(doc_id)
        if record["_rev"] != revision:
            raise PermissionError("stale revision")
        merged = dict(record["doc"], **{k: v for k, v in body.items() if k != "_rev"})
        record["doc"] = merged
        record["revision"] += 1
        record["_rev"] = _rev(doc_id, record["revision"])
        return record["_rev"]

    def delete(self, doc_id: str) -> None:
        self.documents.pop(doc_id, None)


def _rev(doc_id: str, revision: int) -> str:
    digest = hashlib.md5(f"{doc_id}:{revision}".encode("utf-8")).hexdigest()
    return f"{revision}-{digest}"


class EntityHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _store(self) -> EntityStore:
        region = self.headers.get("X-Hpdc-Region") or "default"
        if region not in self.server.stores:
            self.server.stores[region] = EntityStore()
        return self.server.stores[region]

    def _reply(self, status: int, body: dict[str, Any] | None = None) -> None:
        if body is None:
            payload = b""
        else:
            payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length > 64 * 1024:
            raise ValueError("payload too large")
        raw = self.rfile.read(length)
        return json.loads(raw)

    def _auth_ok(self) -> bool:
        header = self.headers.get("Authorization")
        if not header or not header.startswith("Bearer "):
            return False
        return ROLE_RE.search(header) is not None or TENANT_RE.search(header) is not None

    def _requester_tenant(self) -> str | None:
        header = self.headers.get("Authorization") or ""
        match = TENANT_RE.search(header)
        return match.group(1) if match else None

    def _can_access(self, record: dict[str, Any]) -> bool:
        tenant = self._requester_tenant()
        record_tenant = record.get("tenant")
        return tenant is None or record_tenant is None or record_tenant == tenant

    def _require_auth(self) -> bool:
        if self._auth_ok():
            return True
        self._reply(401, {"error": "unauthorized"})
        return False

    def _create(self) -> None:
        if not self._require_auth():
            return
        try:
            doc = self._read_body()
        except (json.JSONDecodeError, ValueError) as exc:
            self._reply(400, {"error": str(exc)})
            return
        if "id" not in doc:
            self._reply(400, {"error": "id is required"})
            return
        result = self._store().create(doc, self._requester_tenant())
        self._reply(201, result)

    def _get(self, doc_id: str) -> None:
        if not self._require_auth():
            return
        store = self._store()
        record = store.documents.get(doc_id)
        if record is None or not self._can_access(record):
            self._reply(404, {"error": "not found"})
            return
        self._reply(200, dict(record["doc"], _rev=record["_rev"]))

    def _list(self) -> None:
        if not self._require_auth():
            return
        query = parse_qs(urlparse(self.path).query)
        requested = (query.get("tenant") or [None])[0]
        requester = self._requester_tenant()
        if requested is not None and requester is not None and requested != requester:
            self._reply(403, {"error": "forbidden"})
            return
        store = self._store()
        items = []
        for doc_id, record in store.documents.items():
            if not self._can_access(record):
                continue
            if requested is not None and record.get("tenant") != requested:
                continue
            items.append(dict(record["doc"], _rev=record["_rev"], id=doc_id))
        self._reply(200, {"items": items})

    def _update(self, doc_id: str) -> None:
        if not self._require_auth():
            return
        try:
            body = self._read_body()
        except (json.JSONDecodeError, ValueError) as exc:
            self._reply(400, {"error": str(exc)})
            return
        store = self._store()
        record = store.documents.get(doc_id)
        if record is None or not self._can_access(record):
            self._reply(404, {"error": "not found"})
            return
        revision = body.get("_rev")
        try:
            if revision is None:
                merged = dict(record["doc"], **{k: v for k, v in body.items() if k != "_rev"})
                record["doc"] = merged
                record["revision"] += 1
                record["_rev"] = _rev(doc_id, record["revision"])
                new_rev = record["_rev"]
            else:
                new_rev = store.update(doc_id, body, revision)
        except PermissionError:
            self._reply(409, {"error": "revision conflict"})
            return
        self._reply(200, {"id": doc_id, "_rev": new_rev})

    def _delete(self, doc_id: str) -> None:
        if not self._require_auth():
            return
        store = self._store()
        record = store.documents.get(doc_id)
        if record is None or not self._can_access(record):
            self._reply(404, {"error": "not found"})
            return
        store.delete(doc_id)
        self._reply(204)

    def _changes(self) -> None:
        if not self._require_auth():
            return
        query = parse_qs(urlparse(self.path).query)
        tenant = (query.get("tenant") or [None])[0]
        requester = self._requester_tenant()
        if tenant is not None and requester is not None and tenant != requester:
            self._reply(403, {"error": "forbidden"})
            return
        events = self._store().domain_events
        if tenant is not None:
            events = [e for e in events if e.get("tenant") == tenant]
        self._reply(200, {"events": events})

    def _replay(self) -> None:
        if not self._require_auth():
            return
        try:
            body = self._read_body()
        except (json.JSONDecodeError, ValueError) as exc:
            self._reply(400, {"error": str(exc)})
            return
        origin = body.get("origin")
        if origin == "self":
            self._reply(200, {"ignored": True})
            return
        self._store().domain_events.append(body)
        self._reply(200, {"ignored": False})

    def _replication_config(self) -> None:
        self._reply(
            200,
            {
                "replication": {
                    "default": "disabled",
                    "explicit_configuration_required": True,
                }
            },
        )

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/data" or path == "/data/":
            self._list()
        elif path.startswith("/data/"):
            self._get(path[len("/data/") :])
        elif path == "/_changes":
            self._changes()
        elif path == "/sovereignty/replication-config":
            self._replication_config()
        else:
            self._reply(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/data":
            self._create()
        elif path == "/_changes/replay":
            self._replay()
        else:
            self._reply(404, {"error": "not found"})

    def do_PUT(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/data/"):
            self._update(path[len("/data/") :])
        else:
            self._reply(404, {"error": "not found"})

    def do_DELETE(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/data/"):
            self._delete(path[len("/data/") :])
        else:
            self._reply(404, {"error": "not found"})

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[entity-api] %s\n" % (fmt % args))


class EntityServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int]) -> None:
        self.stores: dict[str, EntityStore] = {}
        super().__init__(server_address, EntityHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local HPDC entity data plane service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    args = parser.parse_args()
    server = EntityServer((args.host, args.port))
    print(f"entity data plane listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
