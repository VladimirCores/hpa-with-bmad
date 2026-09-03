#!/usr/bin/env python3
"""Validate the offline GitOps pipeline and image cache."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _provisioned import record, value
import component_versions

component_versions.load_all_dotenv()

ROOT = Path(__file__).resolve().parents[2]
SPEGEL_VERSION = component_versions.get("HPDC_SPEGEL_VERSION")
ARGOCD_VERSION = component_versions.get("HPDC_ARGOCD_VERSION")
KARGO_VERSION = component_versions.get("HPDC_KARGO_VERSION")
ARGO_ROLLOUTS_VERSION = component_versions.get("HPDC_ARGO_ROLLOUTS_VERSION")
ARGO_EVENTS_VERSION = component_versions.get("HPDC_ARGO_EVENTS_VERSION")
REQUIRED = [
    ROOT / "gitops/git/base/git-mirror.yaml",
    ROOT / "gitops/spegel/base/spegel.yaml",
    ROOT / "gitops/kargo/base/kargo.yaml",
    ROOT / "gitops/argo-cd/base/argocd.yaml",
    ROOT / "gitops/argo-rollouts/base/argorollouts.yaml",
    ROOT / "gitops/argo-events/base/argoevents.yaml",
    ROOT / "gitops/registry/base/registry.yaml",
    ROOT / "output" / "spegel" / "images" / f"spegel-v{SPEGEL_VERSION}",
    ROOT / "output" / "argocd" / "images" / f"argocd-v{ARGOCD_VERSION}",
    ROOT / "output" / "kargo" / "images" / f"kargo-v{KARGO_VERSION}",
    ROOT / "output" / "argo-rollouts" / "images" / f"argo-rollouts-v{ARGO_ROLLOUTS_VERSION}",
    ROOT / "output" / "argo-events" / "images" / f"argo-events-v{ARGO_EVENTS_VERSION}",
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
    if (record("argocd") or {}).get("version") != ARGOCD_VERSION:
        failures.append("provisioned: argocd version")
    for component, version in {
        "kargo": KARGO_VERSION,
        "argo-rollouts": ARGO_ROLLOUTS_VERSION,
        "argo-events": ARGO_EVENTS_VERSION,
    }.items():
        if (record(component) or {}).get("version") != version:
            failures.append(f"provisioned: {component} version")
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
        print("Registry, preload cache, Git mirror, Spegel, Kargo, Argo CD, Rollouts, and Argo Events are configured.")
        return 0
    print("Offline GitOps validation requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
