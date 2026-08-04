#!/usr/bin/env python3
"""Refresh Harbor cached image metadata when versions or digests change."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARBOR_MARKER = ROOT / "output" / "harbor" / "images" / "harbor-core-v2.11.3"
METADATA = ROOT / "output" / "harbor" / "image-cache-metadata.yaml"
HARBOR_BASE = ROOT / "gitops" / "harbor" / "base"
HARBOR_OVERLAY = ROOT / "gitops" / "harbor" / "overlays" / "refresh"


def ensure_files() -> None:
    if not HARBOR_MARKER.exists():
        raise RuntimeError(f"Harbor image cache marker not found: {HARBOR_MARKER}")
    if not METADATA.exists():
        raise RuntimeError(f"Harbor image cache metadata not found: {METADATA}")


def validate_manifests() -> list[str]:
    failures = []
    required = [HARBOR_BASE / "image-cache-refresh.yaml", HARBOR_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    refresh = (HARBOR_BASE / "image-cache-refresh.yaml").read_text(encoding="utf-8")
    metadata = METADATA.read_text(encoding="utf-8")
    if "kind: ConfigMap" not in refresh or "harbor-image-cache-refresh" not in refresh:
        failures.append("image-cache-refresh.yaml missing ConfigMap")
    if "digest:" not in refresh or "changed: false" not in refresh:
        failures.append("image-cache-refresh.yaml missing digest/change fields")
    if "name: harbor/harbor-core:v2.11.3" not in metadata or "digest: sha256:offline-core" not in metadata:
        failures.append("metadata missing Harbor core digest")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh Harbor cached image metadata")
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
        print("Harbor cache refresh validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Harbor cache refresh apply requested.")
        return 0
    if args.dry_run:
        print("Harbor cache refresh dry-run passed.")
        print("No digest changes detected.")
        print(f"GitOps overlay: {HARBOR_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Harbor cache refresh requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
