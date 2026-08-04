#!/usr/bin/env python3
"""Install Envoy Gateway API-key auth for messaging routes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECURITY_MARKER = ROOT / "output" / "security" / "api-key-authn-workspaces.txt"
SECURITY_BASE = ROOT / "gitops" / "security" / "base"
SECURITY_OVERLAY = ROOT / "gitops" / "security" / "overlays" / "dev"
ROUTE_TABLE = ROOT / "docs" / "api-key-auth-messaging-routes.md"


def ensure_files() -> None:
    if not SECURITY_MARKER.exists():
        raise RuntimeError(f"API-key auth workspace marker not found: {SECURITY_MARKER}")
    if not ROUTE_TABLE.exists():
        raise RuntimeError(f"API-key auth documentation missing: {ROUTE_TABLE}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    required = [SECURITY_BASE / "api-key-authn.yaml", SECURITY_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))

    manifest = (SECURITY_BASE / "api-key-authn.yaml").read_text(encoding="utf-8")
    required_fragments = [
        "kind: SecurityPolicy",
        "name: messaging-api-keys",
        "value: /events",
        "value: /telemetry",
        "name: X-API-Key",
    ]
    for fragment in required_fragments:
        if fragment not in manifest:
            failures.append(f"api-key-authn.yaml missing {fragment}")

    if "name: hpdc-messaging-api-key-authn" not in manifest:
        failures.append("api-key-authn.yaml missing hpdc-messaging-api-key-authn policy")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Envoy Gateway API-key auth for messaging routes")
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
        print("API-key auth validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("API-key auth apply requested.")
        print(f"GitOps overlay: {SECURITY_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("API-key auth dry-run passed.")
        print("X-API-Key validation is configured for /events and /telemetry.")
        print(f"GitOps overlay: {SECURITY_OVERLAY.relative_to(ROOT)}")
        return 0
    print("API-key auth requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
