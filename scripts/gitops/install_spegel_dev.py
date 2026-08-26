#!/usr/bin/env python3
"""Install Spegel P2P image distribution."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import component_versions

component_versions.load_dotenv()
ROOT = Path(__file__).resolve().parents[2]
SPEGEL_VERSION = component_versions.get("HPDC_SPEGEL_VERSION")
SPEGEL_IMAGE = ROOT / "output" / "spegel" / "images" / f"spegel-v{SPEGEL_VERSION}"
SPEGEL_BASE = ROOT / "gitops" / "spegel" / "base"
SPEGEL_OVERLAY = ROOT / "gitops" / "spegel" / "overlays" / "dev"


def ensure_files() -> None:
    if not SPEGEL_IMAGE.exists():
        raise RuntimeError(f"Spegel offline image cache marker not found: {SPEGEL_IMAGE}")


def validate_manifests() -> list[str]:
    failures = []
    required = [SPEGEL_BASE / "spegel.yaml", SPEGEL_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    spegel = (SPEGEL_BASE / "spegel.yaml").read_text(encoding="utf-8")
    if "kind: DaemonSet" not in spegel or "name: spegel" not in spegel:
        failures.append("spegel.yaml missing DaemonSet")
    if f"ghcr.io/spegel-org/spegel:v{SPEGEL_VERSION}" not in spegel:
        failures.append("spegel.yaml missing Spegel image")
    if "kind: Service" not in spegel or "name: spegel-registry" not in spegel:
        failures.append("spegel.yaml missing registry Service")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Spegel P2P image distribution")
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
        print("Spegel validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Spegel apply requested.")
        return 0
    if args.dry_run:
        print("Spegel dry-run passed.")
        print(f"Spegel image: {SPEGEL_IMAGE.relative_to(ROOT)}")
        print(f"GitOps overlay: {SPEGEL_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Spegel requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
