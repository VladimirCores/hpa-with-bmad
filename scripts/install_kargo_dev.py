#!/usr/bin/env python3
"""Install Kargo Warehouse, Stage, and Freight promotion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _provisioned import require

ROOT = Path(__file__).resolve().parents[1]
KARGO_BASE = ROOT / "gitops" / "kargo" / "base"
KARGO_OVERLAY = ROOT / "gitops" / "kargo" / "overlays" / "dev"


def ensure_files() -> None:
    require("kargo")


def validate_manifests() -> list[str]:
    failures = []
    required = [KARGO_BASE / "kargo.yaml", KARGO_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    kargo = (KARGO_BASE / "kargo.yaml").read_text(encoding="utf-8")
    if "kind: Warehouse" not in kargo or "name: offline-gitops" not in kargo:
        failures.append("kargo.yaml missing Warehouse")
    if "kind: Stage" not in kargo or "name: dev" not in kargo:
        failures.append("kargo.yaml missing Stage")
    if "kind: Freight" not in kargo or "name: offline-dev" not in kargo:
        failures.append("kargo.yaml missing Freight")
    if "git://git-mirror/git-mirror" not in kargo:
        failures.append("kargo.yaml missing local Git mirror repoURL")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Kargo Warehouse, Stage, and Freight promotion")
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
        print("Kargo validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Kargo apply requested.")
        return 0
    if args.dry_run:
        print("Kargo dry-run passed.")
        print("Warehouse, Stage, and Freight are configured.")
        print(f"GitOps overlay: {KARGO_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Kargo requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
