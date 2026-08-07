#!/usr/bin/env python3
"""Validate HPDC MCP tool registry and server."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_BASE = ROOT / "gitops" / "agent-engine" / "base" / "mcp-tools.yaml"
MCP_OVERLAY = ROOT / "gitops" / "agent-engine" / "overlays" / "dev" / "kustomization.yaml"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def main() -> int:
    failures: list[str] = []
    for path in [MCP_BASE, MCP_OVERLAY, PLATFORM_SCAFFOLD]:
        if not path.is_file():
            failures.append(f"missing file: {path.relative_to(ROOT)}")

    manifest = MCP_BASE.read_text(encoding="utf-8")
    required = [
        "kind: Namespace",
        "name: agent-engine",
        "kind: MCPToolRegistry",
        "name: platform-capabilities-mcp-tools",
        "query_databases: true",
        "call_apis: true",
        "trigger_workflows: true",
        "security_policy: required",
        "agent_id: required",
        "tool_name: required",
        "kind: ConfigMap",
        "name: mcp-tool-definitions",
        '"name": "query_database"',
        '"name": "call_api"',
        '"name": "trigger_workflow"',
        "name: mcp-security-policy",
        "require_agent_id: true",
        "require_tool_name: true",
        "kind: Deployment",
        "name: mcp-server",
        "name: mcp-audit-log-config",
        "agent_id",
        "tool_name",
        "parameters",
        "result",
        "storage: vmlogs",
        "kind: Service",
    ]
    for item in required:
        if item not in manifest:
            failures.append(f"mcp-tools.yaml missing {item}")

    scaffold = PLATFORM_SCAFFOLD.read_text(encoding="utf-8")
    for item in ["name: platform-capabilities-mcp-tools", "query_databases: true"]:
        if item not in scaffold:
            failures.append(f"platform-scaffold.yaml missing {item}")

    overlay = MCP_OVERLAY.read_text(encoding="utf-8")
    for item in ["../../base/mcp-tools.yaml", "namespace: agent-engine"]:
        if item not in overlay:
            failures.append(f"agent-engine overlay missing {item}")

    if failures:
        print("MCP tool registry validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("MCP tool registry validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
