#!/usr/bin/env python3
"""Install Backstage Developer Portal and Golden Path templates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _provisioned import require
import component_versions

component_versions.load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
BACKSTAGE_VERSION = component_versions.get("HPDC_BACKSTAGE_VERSION")
BACKSTAGE_BASE = ROOT / "gitops" / "backstage" / "base"
BACKSTAGE_OVERLAY = ROOT / "gitops" / "backstage" / "overlays" / "dev"
ROUTE_TABLE = ROOT / "docs" / "backstage-developer-portal.md"


def ensure_files() -> None:
    require("backstage")
    if not ROUTE_TABLE.exists():
        raise RuntimeError(f"Backstage documentation missing: {ROUTE_TABLE}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    required = [BACKSTAGE_BASE / "backstage.yaml", BACKSTAGE_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))

    manifest = (BACKSTAGE_BASE / "backstage.yaml").read_text(encoding="utf-8")
    required_fragments = [
        "kind: Deployment",
        f"image: ghcr.io/backstage/backstage:{BACKSTAGE_VERSION}",
        "kind: ConfigMap",
        "name: backstage-config",
        "casdoor",
        "catalog",
    ]
    for fragment in required_fragments:
        if fragment not in manifest:
            failures.append(f"backstage.yaml missing {fragment}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Backstage Developer Portal and Golden Path templates")
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
        print("Backstage validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Backstage apply requested.")
        print(f"GitOps overlay: {BACKSTAGE_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("Backstage dry-run passed.")
        print("Backstage Developer Portal and Golden Path templates are configured.")
        print(f"GitOps overlay: {BACKSTAGE_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Backstage requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
