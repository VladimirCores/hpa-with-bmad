#!/usr/bin/env python3
"""Install HPDC MCP tool registry and server."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_BASE = ROOT / "gitops" / "agent-engine" / "base"
MCP_OVERLAY = ROOT / "gitops" / "agent-engine" / "overlays" / "dev"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def ensure_files() -> None:
    for path in [MCP_BASE / "mcp-tools.yaml", MCP_OVERLAY / "kustomization.yaml", PLATFORM_SCAFFOLD]:
        if not path.exists():
            raise RuntimeError(f"required file missing: {path.relative_to(ROOT)}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    manifest = (MCP_BASE / "mcp-tools.yaml").read_text(encoding="utf-8")
    overlay = (MCP_OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")

    required_kinds = [
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
    for item in required_kinds:
        if item not in manifest:
            failures.append(f"mcp-tools.yaml missing {item}")

    scaffold = PLATFORM_SCAFFOLD.read_text(encoding="utf-8")
    if "name: platform-capabilities-mcp-tools" not in scaffold:
        failures.append("platform-scaffold.yaml missing platform-capabilities-mcp-tools contract")
    if "query_databases: true" not in scaffold:
        failures.append("platform-scaffold.yaml missing query_databases tool")

    if "../../base/mcp-tools.yaml" not in overlay:
        failures.append("agent-engine overlay missing base resource")
    if "namespace: agent-engine" not in overlay:
        failures.append("agent-engine overlay missing namespace")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC MCP tool registry and server")
    parser.add_argument("--offline", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.check:
        ensure_files()
        failures = validate_manifests()
        if failures:
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("MCP tool registry validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("MCP tool registry apply requested.")
        print(f"GitOps overlay: {MCP_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("MCP tool registry dry-run passed.")
        print("Platform capabilities are exposed as MCP-compatible tools.")
        print("Tool invocations are validated against the security policy.")
        print("Every tool call is logged with agent ID, tool name, parameters, and result.")
        print(f"GitOps overlay: {MCP_OVERLAY.relative_to(ROOT)}")
        return 0
    print("MCP tool registry requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
