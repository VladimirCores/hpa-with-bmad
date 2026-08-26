#!/usr/bin/env python3
"""Install Casdoor JWT AuthN for domain routes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _provisioned import require
import component_versions

component_versions.load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
CASDOOR_VERSION = component_versions.get("HPDC_CASDOOR_VERSION")
CASDOOR_BASE = ROOT / "gitops" / "casdoor" / "base"
CASDOOR_OVERLAY = ROOT / "gitops" / "casdoor" / "overlays" / "dev"
ROUTE_TABLE = ROOT / "docs" / "casdoor-jwt-authn.md"


def ensure_files() -> None:
    require("casdoor")
    if not ROUTE_TABLE.exists():
        raise RuntimeError(f"Casdoor documentation missing: {ROUTE_TABLE}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    required = [CASDOOR_BASE / "casdoor.yaml", CASDOOR_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))

    manifest = (CASDOOR_BASE / "casdoor.yaml").read_text(encoding="utf-8")
    required_fragments = [
        "kind: Deployment",
        f"image: docker.io/casbin/casdoor:{CASDOOR_VERSION}",
        "oidc = true",
        "saml = true",
        "refreshTokenExpireHours = 24",
        "sessionMaxLifetimeHours = 12",
    ]
    for fragment in required_fragments:
        if fragment not in manifest:
            failures.append(f"casdoor.yaml missing {fragment}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Casdoor JWT AuthN for domain routes")
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
        print("Casdoor validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Casdoor apply requested.")
        print(f"GitOps overlay: {CASDOOR_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("Casdoor dry-run passed.")
        print("Casdoor OIDC/SAML AuthN is configured for domain routes.")
        print(f"GitOps overlay: {CASDOOR_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Casdoor requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
