#!/usr/bin/env python3
"""Local HPDC agent-engine service (dev harness for ATDD).

Simulates the A2A channel and MCP registry contracts for green-phase
acceptance tests:

  GET   /mcp/tools                - tool registry allow-list (readiness)
  POST  /mcp/tools                - invoke a tool through the security gate
  POST  /a2a/token                - issue a channel token to a registered agent
  POST  /a2a/messages             - send an agent-to-agent message
  GET   /a2a/health               - readiness probe

Policy follows the gitops manifests (agent-engine/base/*):

  - MCPToolRegistry: allow-list query_database/call_api/trigger_workflow,
    security_policy required, agent_id + tool_name required in logs.
  - agent-registry: agent-1@hpdc.local (alert-analysis, entity-query),
    agent-2@hpdc.local (telemetry-processing, workflow-trigger).
  - a2a-messaging-config: registered sender required, channel authenticated,
    topic hpdc.agent.messages.

Denied MCP calls are written to the audit store (audit/mcp.ndjson) with the
agent_id and tool_name; routed A2A messages land in the topic store
(topics/agent.messages.ndjson). This is a local stand-in for the a2a-broker,
mcp-server, vmlogs, and the Kafka/Pulsar agent message topic.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

REGISTERED_AGENTS = {
    "agent-1@hpdc.local": {"name": "agent-1", "capabilities": ["alert-analysis", "entity-query"]},
    "agent-2@hpdc.local": {
        "name": "agent-2",
        "capabilities": ["telemetry-processing", "workflow-trigger"],
    },
}

TOOL_ALLOW_LIST = ("query_database", "call_api", "trigger_workflow")
TOOL_CAPABILITY = {
    "query_database": "entity-query",
    "call_api": "call-apis",
    "trigger_workflow": "workflow-trigger",
}

A2A_TOPIC_FILE = "topics/agent.messages.ndjson"
MCP_AUDIT_FILE = "audit/mcp.ndjson"
MAX_BODY_BYTES = 64 * 1024


def rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _token_for(agent_id: str) -> str:
    return f"a2a-token-{agent_id}"


class AgentHandler(BaseHTTPRequestHandler):
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

    def _log_ndjson(self, path: str, entry: dict[str, Any]) -> None:
        log_path = Path(self.server.data_dir) / path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def do_GET(self) -> None:
        if self.path.startswith("/mcp/tools"):
            self._reply(200, {"tools": list(TOOL_ALLOW_LIST)})
        elif self.path.startswith("/a2a/health"):
            self._reply(200, {"status": "ok"})
        else:
            self._reply(404, {"error": "not found"})

    def do_POST(self) -> None:
        try:
            body = self._read_body()
        except (ValueError, json.JSONDecodeError) as exc:
            self._reply(400, {"error": f"invalid body: {exc}"})
            return
        if self.path.startswith("/mcp/tools"):
            self._mcp_invoke(body)
        elif self.path.startswith("/a2a/token"):
            self._a2a_issue_token(body)
        elif self.path.startswith("/a2a/messages"):
            self._a2a_send(body)
        else:
            self._reply(404, {"error": "not found"})

    def _mcp_invoke(self, body: dict[str, Any]) -> None:
        tool = body.get("tool")
        agent_id = body.get("agent_id")
        args = body.get("args") or {}
        audit: dict[str, Any] = {
            "agent_id": agent_id,
            "tool_name": tool,
            "parameters": args,
            "timestamp": rfc3339(),
        }
        denied = False
        reason = ""
        if not tool or not agent_id:
            denied = True
            reason = "agent_id_and_tool_name_required"
        elif tool not in TOOL_ALLOW_LIST:
            denied = True
            reason = "tool_not_allowed"
        elif agent_id not in REGISTERED_AGENTS:
            denied = True
            reason = "agent_not_registered"
        elif TOOL_CAPABILITY.get(tool) not in REGISTERED_AGENTS[agent_id]["capabilities"]:
            denied = True
            reason = "permission_denied"
        if denied:
            audit["decision"] = "denied"
            audit["reason"] = reason
            self._log_ndjson(MCP_AUDIT_FILE, audit)
            self._reply(403, {"reason": reason})
            return
        audit["decision"] = "allowed"
        audit["result"] = "ok"
        self._log_ndjson(MCP_AUDIT_FILE, audit)
        self._reply(200, {"status": "ok", "result": "ok"})

    def _a2a_issue_token(self, body: dict[str, Any]) -> None:
        agent_id = body.get("agent_id")
        if agent_id not in REGISTERED_AGENTS:
            self._reply(403, {"reason": "agent_not_registered"})
            return
        self._reply(200, {"token": _token_for(agent_id)})

    def _a2a_send(self, body: dict[str, Any]) -> None:
        from_agent = body.get("from_agent")
        to_agent = body.get("to_agent")
        channel_token = body.get("channel_token")
        message = body.get("message") or {}
        if from_agent not in REGISTERED_AGENTS:
            self._reply(403, {"reason": "agent_not_registered"})
            return
        if channel_token != _token_for(from_agent):
            self._reply(403, {"reason": "unauthorized"})
            return
        if to_agent not in REGISTERED_AGENTS:
            self._reply(403, {"reason": "recipient_not_registered"})
            return
        routed = dict(message)
        routed.update({"from": from_agent, "to": to_agent, "routed_at": rfc3339()})
        self._log_ndjson(A2A_TOPIC_FILE, routed)
        self._reply(202, {"status": "routed"})


class AgentServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], data_dir: Path) -> None:
        self.data_dir = data_dir
        super().__init__(server_address, AgentHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local HPDC agent-engine (A2A + MCP) service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument(
        "--data-dir",
        default=str(ROOT / "output" / "agent-engine"),
        help="topic + audit persistence directory",
    )
    args = parser.parse_args()
    server = AgentServer((args.host, args.port), Path(args.data_dir))
    print(f"agent-engine service listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
