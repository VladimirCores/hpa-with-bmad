#!/usr/bin/env python3
"""Preload offline image cache into Harbor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARBOR_MARKER = ROOT / "output" / "harbor" / "images" / "harbor-core-v2.11.3"
IMAGE_LIST = ROOT / "output" / "harbor" / "cache-images.txt"
HARBOR_BASE = ROOT / "gitops" / "harbor" / "base"
HARBOR_OVERLAY = ROOT / "gitops" / "harbor" / "overlays" / "preload"


def ensure_files() -> None:
    if not HARBOR_MARKER.exists():
        raise RuntimeError(f"Harbor image cache marker not found: {HARBOR_MARKER}")
    if not IMAGE_LIST.exists():
        raise RuntimeError(f"Offline image cache manifest not found: {IMAGE_LIST}")


def validate_manifests() -> list[str]:
    failures = []
    required = [HARBOR_BASE / "preload-images.yaml", HARBOR_BASE / "preload-images-job.yaml", HARBOR_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    preload = (HARBOR_BASE / "preload-images.yaml").read_text(encoding="utf-8")
    job = (HARBOR_BASE / "preload-images-job.yaml").read_text(encoding="utf-8")
    if "kind: ConfigMap" not in preload or "offline-image-cache" not in preload:
        failures.append("preload-images.yaml missing offline image cache ConfigMap")
    if "kind: Job" not in preload or "preload-offline-image-cache" not in preload:
        failures.append("preload-images.yaml missing preload Job")
    if "docker:2.41-cli" not in preload:
        failures.append("preload-images.yaml missing preload image")
    if "kind: ConfigMap" not in job or "preload-images-job-config" not in job:
        failures.append("preload-images-job.yaml missing preload job config")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Preload offline image cache into Harbor")
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
        print("Preload Harbor cache validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Preload Harbor cache apply requested.")
        return 0
    if args.dry_run:
        images = [line.strip() for line in IMAGE_LIST.read_text(encoding="utf-8").splitlines() if line.strip()]
        print("Preload Harbor cache dry-run passed.")
        print(f"Images to preload: {len(images)}")
        for image in images:
            print(f"- {image}")
        print(f"GitOps overlay: {HARBOR_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Preload Harbor cache requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
