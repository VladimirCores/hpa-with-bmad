# Story 9-1: Expose Platform Capabilities as MCP Tools

Status: done

Baseline commit: ba011aa

## Story

As an AI Agent,
I want platform capabilities exposed as MCP-compatible tools,
So that agents can query databases, call APIs, and trigger workflows through a consistent interface.

## Acceptance Criteria

1. Given the platform exposes MCP-compatible tool definitions, when an agent invokes a tool, then the invocation is validated against security policies.
2. Given a tool call, when it completes, then the call is logged with agent ID, tool name, parameters, and result.
3. Given the process runs offline, when it completes, then no internet access is required.
4. Given a failure, when the script runs, then it exits with a non-zero status on failure.

## Implementation Plan

- Add `gitops/agent-engine/` component binding the `MCPToolRegistry` contract (query databases, call APIs, trigger workflows; security policy validation; agent ID / tool name logging).
- Add MCP server deployment, tool definitions ConfigMap, and audit log.
- Install script with `--check` / `--dry-run` / `--apply`, step wrapper, and validation test.

## Files

- `gitops/agent-engine/base/mcp-tools.yaml` (new)
- `gitops/agent-engine/overlays/dev/kustomization.yaml` (new)
- `scripts/install-mcp-tools-dev.py` (new)
- `scripts/steps/43-install-mcp-tools-dev.py` (new)
- `tests/test_install_mcp_tools_dev.py` (new)
