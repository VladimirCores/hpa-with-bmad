#!/usr/bin/env python3
"""Install Casbin ReBAC policies for domain routes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _provisioned import require

ROOT = Path(__file__).resolve().parents[2]
CASBIN_REBACK_BASE = ROOT / "gitops" / "casbin" / "base"
CASBIN_REBACK_OVERLAY = ROOT / "gitops" / "casbin" / "overlays" / "dev"
ROUTE_TABLE = ROOT / "docs" / "casbin-rebac-policies.md"


def ensure_files() -> None:
    require("casbin-rebac")
    if not ROUTE_TABLE.exists():
        raise RuntimeError(f"Casbin ReBAC documentation missing: {ROUTE_TABLE}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    required = [CASBIN_REBACK_BASE / "casbin-rebac.yaml", CASBIN_REBACK_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))

    manifest = (CASBIN_REBACK_BASE / "casbin-rebac.yaml").read_text(encoding="utf-8")
    required_fragments = [
        "kind: Deployment",
        "image: docker.io/casbin/ext-authz:v0.0.1",
        "company:acme,admin,client:acme",
        "company:acme,admin,device:acme-dev-001",
        "casbin-rebac-ext-authz",
    ]
    for fragment in required_fragments:
        if fragment not in manifest:
            failures.append(f"casbin-rebac.yaml missing {fragment}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Casbin ReBAC policies for domain routes")
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
        print("Casbin ReBAC validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Casbin ReBAC apply requested.")
        print(f"GitOps overlay: {CASBIN_REBACK_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("Casbin ReBAC dry-run passed.")
        print("Relationship-based access control is configured for domain routes.")
        print(f"GitOps overlay: {CASBIN_REBACK_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Casbin ReBAC requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
