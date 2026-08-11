#!/usr/bin/env python3
"""Local HPDC identity + authorization service (dev harness for ATDD P0-012..015).

Simulates the Casdoor SSO, group-to-role mapping, token validation, and
per-permission GraphQL authorization contract:

  POST /casdoor/login      - login(email, group) -> jwt encoding the group
  GET  /api/{path}         - protected endpoint (401 on no/expired/revoked token)
  GET  /identity/groups    - resolve the principal's roles from their token
  POST /gql                - authorize a GraphQL query per requester's role

Group-to-role mapping: administrator/manager/operator -> admin,
technic/developer/platform-engineer -> operator, CEO -> manager, client -> viewer.
Expired (exp=0) and revoked tokens are always rejected 401.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

GROUP_RE = re.compile(r"group=([A-Za-z0-9_\-]+)")
ROLE_RE = re.compile(r"role=([A-Za-z0-9_\-]+)")

GQL_PERMISSIONS: dict[str, set[str]] = {
    "couchdb_entities": {"admin"},
    "yugabytedb_resources": {"admin", "manager"},
}
GQL_STORE_RE = re.compile(r"\{\s*([A-Za-z0-9_]+)\s*\{")


def role_for_group(group: str | None) -> str:
    normalized = (group or "").lower().replace("_", "-")
    if normalized in ("administrator", "manager", "operator"):
        return "admin"
    if normalized in ("technic", "developer", "platform-engineer"):
        return "operator"
    if normalized in ("ceo", "chief-executive-officer"):
        return "manager"
    return "viewer"


def token_role(token: str) -> str | None:
    group = GROUP_RE.search(token)
    if group:
        return role_for_group(group.group(1))
    role = ROLE_RE.search(token)
    if role:
        return role.group(1)
    return None


def token_valid(token: str) -> bool:
    if not token:
        return False
    if "exp=0" in token or "revoked" in token:
        return False
    return token_role(token) is not None


class IdentityHandler(BaseHTTPRequestHandler):
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
        raw = self.rfile.read(length)
        return json.loads(raw) if raw else {}

    def _bearer(self) -> str | None:
        header = self.headers.get("Authorization")
        if header and header.startswith("Bearer "):
            return header[len("Bearer ") :]
        return None

    def _login(self) -> None:
        try:
            body = self._read_body()
        except json.JSONDecodeError:
            self._reply(400, {"error": "invalid body"})
            return
        group = body.get("group")
        if not group:
            self._reply(400, {"error": "group is required"})
            return
        jwt = f"eyJhbGciOiJSUzI1NiJ9.group={group}.placeholder"
        self._reply(200, {"jwt": jwt})

    def _welcome(self) -> None:
        token = self._bearer()
        if not token_valid(token):
            self._reply(401, {"error": "unauthorized"})
            return
        self._reply(200, {"message": "welcome"})

    def _groups(self) -> None:
        token = self._bearer()
        if not token_valid(token):
            self._reply(401, {"error": "unauthorized"})
            return
        role = token_role(token) or "viewer"
        self._reply(200, {"groups": [role]})

    def _gql(self) -> None:
        token = self._bearer()
        if not token_valid(token):
            self._reply(401, {"error": "unauthorized"})
            return
        try:
            body = self._read_body()
        except json.JSONDecodeError:
            self._reply(400, {"error": "invalid body"})
            return
        query = body.get("query", "")
        match = GQL_STORE_RE.search(query)
        store = match.group(1) if match else ""
        role = token_role(token) or "viewer"
        allowed = GQL_PERMISSIONS.get(store, {"admin"})
        if role not in allowed:
            self._reply(403, {"error": "forbidden"})
            return
        self._reply(200, {"data": {"store": store}})

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/identity/groups":
            self._groups()
        elif path.startswith("/api/"):
            self._welcome()
        else:
            self._reply(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/casdoor/login":
            self._login()
        elif path == "/gql":
            self._gql()
        else:
            self._reply(404, {"error": "not found"})

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[identity-authz] %s\n" % (fmt % args))


class IdentityServer(ThreadingHTTPServer):
    daemon_threads = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Local HPDC identity + authorization service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8789)
    args = parser.parse_args()
    server = IdentityServer((args.host, args.port), IdentityHandler)
    print(f"identity service listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
