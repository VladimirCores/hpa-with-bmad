#!/usr/bin/env python3
"""Validate the offline GitOps pipeline and image cache."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _provisioned import record, value

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = [
    ROOT / "gitops/harbor/base/harbor.yaml",
    ROOT / "gitops/harbor/base/harbor-values.yaml",
    ROOT / "gitops/harbor/base/harbor-pvcs.yaml",
    ROOT / "gitops/harbor/base/preload-images.yaml",
    ROOT / "gitops/harbor/base/preload-images-job.yaml",
    ROOT / "gitops/harbor/base/image-cache-refresh.yaml",
    ROOT / "gitops/git/base/git-mirror.yaml",
    ROOT / "gitops/spegel/base/spegel.yaml",
    ROOT / "gitops/kargo/base/kargo.yaml",
    ROOT / "gitops/argo-cd/base/argocd.yaml",
    ROOT / "gitops/argo-rollouts/base/argorollouts.yaml",
    ROOT / "gitops/argo-events/base/argoevents.yaml",
    ROOT / "output/harbor/cache-images.txt",
    ROOT / "output/spegel/images/spegel-v0.4.0",
    ROOT / "output/argocd/images/argocd-v3.5.0",
    ROOT / "output/kargo/images/kargo-v1.11.0",
    ROOT / "output/argo-rollouts/images/argo-rollouts-v1.9.1",
    ROOT / "output/argo-events/images/argo-events-v1.9.11",
    ROOT / "output/provisioned.yaml",
]


def validate() -> list[str]:
    failures = []
    for path in REQUIRED:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    for component in ["git-mirror", "kargo", "argocd", "argo-rollouts", "argo-events"]:
        if value(component) is None:
            failures.append(f"provisioned: {component}")
    if (record("argocd") or {}).get("version") != "3.5.0":
        failures.append("provisioned: argocd version")
    for component, version in {
        "kargo": "1.11.0",
        "argo-rollouts": "1.9.1",
        "argo-events": "1.9.11",
    }.items():
        if (record(component) or {}).get("version") != version:
            failures.append(f"provisioned: {component} version")
    images = (record("harbor-image-cache") or {}).get("images") or []
    if not any(image.get("name") == "harbor/harbor-core:v2.11.3" for image in images):
        failures.append("provisioned: harbor-image-cache core image")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate offline GitOps pipeline and image cache")
    parser.add_argument("--offline", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    failures = validate()
    if failures:
        print("Offline GitOps validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Offline GitOps pipeline apply requested.")
        return 0
    if args.dry_run or args.check:
        print("Offline GitOps pipeline validation passed.")
        print("Harbor registry, preload cache, digest refresh, Git mirror, Spegel, Kargo, Argo CD, Rollouts, and Argo Events are configured.")
        return 0
    print("Offline GitOps validation requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
