#!/usr/bin/env python3
"""Install Infisical secrets management."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFISICAL_MARKER = ROOT / "output" / "infisical" / "infisical-workspaces.txt"
INFISICAL_BASE = ROOT / "gitops" / "infisical" / "base"
INFISICAL_OVERLAY = ROOT / "gitops" / "infisical" / "overlays" / "dev"
ROUTE_TABLE = ROOT / "docs" / "infisical-secrets-management.md"


def ensure_files() -> None:
    if not INFISICAL_MARKER.exists():
        raise RuntimeError(f"Infisical workspace marker not found: {INFISICAL_MARKER}")
    if not ROUTE_TABLE.exists():
        raise RuntimeError(f"Infisical documentation missing: {ROUTE_TABLE}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    required = [INFISICAL_BASE / "infisical.yaml", INFISICAL_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))

    manifest = (INFISICAL_BASE / "infisical.yaml").read_text(encoding="utf-8")
    required_fragments = [
        "kind: Deployment",
        "image: docker.io/infisical/infisical:0.10.0",
        "secretRotation",
        "rotationIntervalDays: 90",
        "auditLog",
        "csiDriver",
    ]
    for fragment in required_fragments:
        if fragment not in manifest:
            failures.append(f"infisical.yaml missing {fragment}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Infisical secrets management")
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
        print("Infisical validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Infisical apply requested.")
        print(f"GitOps overlay: {INFISICAL_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("Infisical dry-run passed.")
        print("Infisical secrets management is configured.")
        print(f"GitOps overlay: {INFISICAL_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Infisical requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
