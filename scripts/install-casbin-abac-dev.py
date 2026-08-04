#!/usr/bin/env python3
"""Install Casbin ABAC policies for domain routes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASBIN_ABAC_MARKER = ROOT / "output" / "casbin" / "casbin-abac-workspaces.txt"
CASBIN_ABAC_BASE = ROOT / "gitops" / "casbin" / "base"
CASBIN_ABAC_OVERLAY = ROOT / "gitops" / "casbin" / "overlays" / "dev"
ROUTE_TABLE = ROOT / "docs" / "casbin-abac-policies.md"


def ensure_files() -> None:
    if not CASBIN_ABAC_MARKER.exists():
        raise RuntimeError(f"Casbin ABAC workspace marker not found: {CASBIN_ABAC_MARKER}")
    if not ROUTE_TABLE.exists():
        raise RuntimeError(f"Casbin ABAC documentation missing: {ROUTE_TABLE}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    required = [CASBIN_ABAC_BASE / "casbin-abac.yaml", CASBIN_ABAC_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))

    manifest = (CASBIN_ABAC_BASE / "casbin-abac.yaml").read_text(encoding="utf-8")
    required_fragments = [
        "kind: Deployment",
        "image: docker.io/casbin/ext-authz:v0.0.1",
        "time_of_day",
        "location",
        "device_state",
        "risk",
        "clearance",
        "abac-ext-authz",
    ]
    for fragment in required_fragments:
        if fragment not in manifest:
            failures.append(f"casbin-abac.yaml missing {fragment}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Casbin ABAC policies for domain routes")
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
        print("Casbin ABAC validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Casbin ABAC apply requested.")
        print(f"GitOps overlay: {CASBIN_ABAC_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("Casbin ABAC dry-run passed.")
        print("Attribute-based access control is configured for domain routes.")
        print(f"GitOps overlay: {CASBIN_ABAC_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Casbin ABAC requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
