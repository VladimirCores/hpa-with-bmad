#!/usr/bin/env python3
"""Validate HPDC authenticated agent-to-agent (A2A) communication."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A2A_BASE = ROOT / "gitops" / "agent-engine" / "base" / "a2a.yaml"
A2A_OVERLAY = ROOT / "gitops" / "agent-engine" / "overlays" / "dev" / "kustomization.yaml"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def main() -> int:
    failures: list[str] = []
    for path in [A2A_BASE, A2A_OVERLAY, PLATFORM_SCAFFOLD]:
        if not path.is_file():
            failures.append(f"missing file: {path.relative_to(ROOT)}")

    manifest = A2A_BASE.read_text(encoding="utf-8")
    required = [
        "kind: AgentCommunication",
        "name: authenticated-agent-communication",
        "registered_agents_required: true",
        "authenticated: true",
        "unauthorized_prevented: true",
        "registered_agents_only",
        "kind: ConfigMap",
        "name: agent-registry",
        "agent-1@hpdc.local",
        "agent-2@hpdc.local",
        "name: a2a-messaging-config",
        "require_registered_sender: true",
        "prevent_unauthorized_impersonation: true",
        "transport: kafka",
        "topic: hpdc.agent.messages",
        "kind: Deployment",
        "name: a2a-broker",
        "kind: Service",
    ]
    for item in required:
        if item not in manifest:
            failures.append(f"a2a.yaml missing {item}")

    scaffold = PLATFORM_SCAFFOLD.read_text(encoding="utf-8")
    for item in ["kind: AgentCommunication", "registered_agents_required: true"]:
        if item not in scaffold:
            failures.append(f"platform-scaffold.yaml missing {item}")

    overlay = A2A_OVERLAY.read_text(encoding="utf-8")
    if "../../base/a2a.yaml" not in overlay:
        failures.append("agent-engine overlay missing a2a resource")

    if failures:
        print("A2A communication validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("A2A communication validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
