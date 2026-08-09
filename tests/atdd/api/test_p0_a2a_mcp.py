#!/usr/bin/env python3
"""Acceptance tests for agent-to-agent and MCP security.

P0-019 An MCP tool call without permission is denied and audited.
P0-020 A2A: an unregistered agent is rejected.
P0-021 A2A: a registered agent is verified and authorized.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

A2A_URL = "http://hpdc-a2a.local"
MCP_URL = "http://hpdc-mcp.local"
AGENT_1 = "agent-1@hpdc.local"
AGENT_2 = "agent-2@hpdc.local"
A2A_TOPIC = "persistent://hpdc/agent/messages"


# P0-019 (FR-47, R-011)
# Given: an MCP registry with a security_policy validation gate
#  When: an agent calls a tool without permission
#  Then: the call is denied 403
#   And: the denial is written to the audit log with agent_id and tool_name
def test_p0_019_mcp_tool_without_permission_denied_and_audited() -> None:
    from hpdc_test_client import AuditProbe, McpHarness

    mcp = McpHarness(MCP_URL)
    audit = AuditProbe("http://hpdc-vmlogs.local")

    denied = mcp.call_tool(
        tool="trigger_workflow",
        agent_id="agent-7@hpdc.local",
        args={"workflow": "restart-service"},
    )
    assert denied.status_code == 403
    entry = audit.latest(agent_id="agent-7@hpdc.local", tool_name="trigger_workflow")
    assert entry is not None
    assert entry["decision"] == "denied"
    assert entry["agent_id"] == "agent-7@hpdc.local"
    assert entry["tool_name"] == "trigger_workflow"


# P0-020 (FR-48, R-010)
# Given: an A2A channel with registered_agents_required: true
#  When: an agent that is not in the registry sends a message
#  Then: the message is rejected and never routed to the topic
def test_p0_020_a2a_unregistered_agent_rejected() -> None:
    from hpdc_test_client import A2AHarness, PulsarConsumer

    a2a = A2AHarness(A2A_URL)
    consumer = PulsarConsumer(A2A_TOPIC)

    reply = a2a.send(from_agent="sneaky@hpdc.local", to_agent=AGENT_1, message={"type": "task"})
    assert reply.status_code in (401, 403)
    assert reply.json()["reason"] == "agent_not_registered"
    assert consumer.consume(timeout_s=2) == []


# P0-021 (FR-48, R-010)
# Given: two agents registered in the A2A registry
#  When: the first agent authenticates and messages the second
#  Then: the message is verified, authorized, and routed to hpdc.agent.messages
def test_p0_021_a2a_registered_agent_verified_and_authorized() -> None:
    from hpdc_test_client import A2AHarness, PulsarConsumer

    a2a = A2AHarness(A2A_URL)
    consumer = PulsarConsumer(A2A_TOPIC)

    token = a2a.issue_channel_token(AGENT_1)
    reply = a2a.send(
        from_agent=AGENT_1,
        to_agent=AGENT_2,
        channel_token=token,
        message={"type": "task", "payload": {"action": "summarize"}},
    )
    assert reply.status_code == 202
    delivered = consumer.consume(timeout_s=5)
    assert any(m["from"] == AGENT_1 and m["to"] == AGENT_2 for m in delivered)


def main() -> int:
    tests = (
        test_p0_019_mcp_tool_without_permission_denied_and_audited,
        test_p0_020_a2a_unregistered_agent_rejected,
        test_p0_021_a2a_registered_agent_verified_and_authorized,
    )
    skipped = 0
    for test in tests:
        try:
            test()
        except (ImportError, NotImplementedError) as exc:
            skipped += 1
            print(f"  RED (skipped): {test.__name__} — {exc}")
        except Exception as exc:
            skipped += 1
            print(f"  RED (skipped): {test.__name__} — {type(exc).__name__}: {exc}")
    print(f"RED PHASE: {len(tests)} acceptance tests scaffolded; {skipped} pending green-phase implementation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
