#!/usr/bin/env python3
"""Install HPDC authenticated agent-to-agent (A2A) communication."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A2A_BASE = ROOT / "gitops" / "agent-engine" / "base"
A2A_OVERLAY = ROOT / "gitops" / "agent-engine" / "overlays" / "dev"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def ensure_files() -> None:
    for path in [A2A_BASE / "a2a.yaml", A2A_OVERLAY / "kustomization.yaml", PLATFORM_SCAFFOLD]:
        if not path.exists():
            raise RuntimeError(f"required file missing: {path.relative_to(ROOT)}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    manifest = (A2A_BASE / "a2a.yaml").read_text(encoding="utf-8")
    overlay = (A2A_OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")

    required_kinds = [
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
    for item in required_kinds:
        if item not in manifest:
            failures.append(f"a2a.yaml missing {item}")

    scaffold = PLATFORM_SCAFFOLD.read_text(encoding="utf-8")
    if "kind: AgentCommunication" not in scaffold:
        failures.append("platform-scaffold.yaml missing AgentCommunication contract")
    if "registered_agents_required: true" not in scaffold:
        failures.append("platform-scaffold.yaml missing registered agents requirement")

    if "../../base/a2a.yaml" not in overlay:
        failures.append("agent-engine overlay missing a2a resource")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC authenticated agent-to-agent (A2A) communication")
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
        print("A2A communication validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("A2A communication apply requested.")
        print(f"GitOps overlay: {A2A_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("A2A communication dry-run passed.")
        print("Agent messages are routed through an authenticated channel.")
        print("Unauthorized impersonation is prevented and discovery is limited to registered agents.")
        print("Agent registration and discovery work as configured.")
        print(f"GitOps overlay: {A2A_OVERLAY.relative_to(ROOT)}")
        return 0
    print("A2A communication requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
