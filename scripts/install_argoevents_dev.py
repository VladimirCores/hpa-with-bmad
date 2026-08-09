#!/usr/bin/env python3
"""Install Argo Events and workflows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _provisioned import require

ROOT = Path(__file__).resolve().parents[1]
ARGO_EVENTS_BASE = ROOT / "gitops" / "argo-events" / "base"
ARGO_EVENTS_OVERLAY = ROOT / "gitops" / "argo-events" / "overlays" / "dev"


def ensure_files() -> None:
    require("argo-events")


def validate_manifests() -> list[str]:
    failures = []
    required = [ARGO_EVENTS_BASE / "argoevents.yaml", ARGO_EVENTS_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    events = (ARGO_EVENTS_BASE / "argoevents.yaml").read_text(encoding="utf-8")
    if "kind: EventSource" not in events or "name: offline-gitops" not in events:
        failures.append("argoevents.yaml missing EventSource")
    if "kind: Sensor" not in events or "name: offline-gitops" not in events:
        failures.append("argoevents.yaml missing Sensor")
    if "kind: Workflow" not in events or "name: offline-gitops" not in events:
        failures.append("argoevents.yaml missing Workflow")
    if "git://git-mirror/git-mirror" not in events:
        failures.append("argoevents.yaml missing local Git mirror repoURL")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Argo Events and workflows")
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
        print("Argo Events validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Argo Events apply requested.")
        return 0
    if args.dry_run:
        print("Argo Events dry-run passed.")
        print("EventSource, Sensor, and Workflow are configured.")
        print(f"GitOps overlay: {ARGO_EVENTS_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Argo Events requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
