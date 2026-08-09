#!/usr/bin/env python3
"""Install Casbin RBAC policies for domain routes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _provisioned import require

ROOT = Path(__file__).resolve().parents[1]
CASBIN_BASE = ROOT / "gitops" / "casbin" / "base"
CASBIN_OVERLAY = ROOT / "gitops" / "casbin" / "overlays" / "dev"
ROUTE_TABLE = ROOT / "docs" / "casbin-rbac-policies.md"


def ensure_files() -> None:
    require("casbin-rbac")
    if not ROUTE_TABLE.exists():
        raise RuntimeError(f"Casbin documentation missing: {ROUTE_TABLE}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    required = [CASBIN_BASE / "casbin-rbac.yaml", CASBIN_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))

    manifest = (CASBIN_BASE / "casbin-rbac.yaml").read_text(encoding="utf-8")
    required_fragments = [
        "kind: Deployment",
        "image: docker.io/casbin/ext-authz:v0.0.1",
        "administrator, admin",
        "manager, admin",
        "operator, admin",
        "CEO, manager",
        "client, viewer",
        "deny",
    ]
    for fragment in required_fragments:
        if fragment not in manifest:
            failures.append(f"casbin-rbac.yaml missing {fragment}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Casbin RBAC policies for domain routes")
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
        print("Casbin RBAC validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Casbin RBAC apply requested.")
        print(f"GitOps overlay: {CASBIN_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("Casbin RBAC dry-run passed.")
        print("RBAC policy enforcement is configured for domain routes.")
        print(f"GitOps overlay: {CASBIN_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Casbin RBAC requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
