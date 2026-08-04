#!/usr/bin/env python3
"""Provision a local Git mirror for offline GitOps."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIT_MIRROR = ROOT / "output" / "git" / "mirror-repositories.txt"
GIT_BASE = ROOT / "gitops" / "git" / "base"
GIT_OVERLAY = ROOT / "gitops" / "git" / "overlays" / "dev"


def ensure_files() -> None:
    if not GIT_MIRROR.exists():
        raise RuntimeError(f"Git mirror repository list not found: {GIT_MIRROR}")


def validate_manifests() -> list[str]:
    failures = []
    required = [GIT_BASE / "git-mirror.yaml", GIT_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    mirror = (GIT_BASE / "git-mirror.yaml").read_text(encoding="utf-8")
    if "kind: Deployment" not in mirror or "name: git-mirror" not in mirror:
        failures.append("git-mirror.yaml missing Git mirror Deployment")
    if "alpine/git:2.45.2" not in mirror:
        failures.append("git-mirror.yaml missing Git image")
    if "storageClassName: rook-ceph-rbd" not in mirror:
        failures.append("git-mirror.yaml missing Rook-Ceph PVC storageClass")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision local Git mirror for offline GitOps")
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
        print("Local Git mirror validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Local Git mirror apply requested.")
        return 0
    if args.dry_run:
        repos = [line.strip() for line in GIT_MIRROR.read_text(encoding="utf-8").splitlines() if line.strip()]
        print("Local Git mirror dry-run passed.")
        print(f"Repositories mirrored: {len(repos)}")
        for repo in repos:
            print(f"- {repo}")
        print(f"GitOps overlay: {GIT_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Local Git mirror requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
