#!/usr/bin/env python3
"""Install Argo Rollouts progressive delivery."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARGO_ROLLOUTS_MARKER = ROOT / "output" / "argo-rollouts" / "rollouts.txt"
ARGO_ROLLOUTS_BASE = ROOT / "gitops" / "argo-rollouts" / "base"
ARGO_ROLLOUTS_OVERLAY = ROOT / "gitops" / "argo-rollouts" / "overlays" / "dev"


def ensure_files() -> None:
    if not ARGO_ROLLOUTS_MARKER.exists():
        raise RuntimeError(f"Argo Rollouts marker not found: {ARGO_ROLLOUTS_MARKER}")


def validate_manifests() -> list[str]:
    failures = []
    required = [ARGO_ROLLOUTS_BASE / "argorollouts.yaml", ARGO_ROLLOUTS_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    rollouts = (ARGO_ROLLOUTS_BASE / "argorollouts.yaml").read_text(encoding="utf-8")
    if "kind: Rollout" not in rollouts or "name: rollout-demo" not in rollouts:
        failures.append("argorollouts.yaml missing Rollout")
    if "strategy:" not in rollouts or "canary:" not in rollouts:
        failures.append("argorollouts.yaml missing canary strategy")
    if "pause: {duration: 30s}" not in rollouts:
        failures.append("argorollouts.yaml missing pause steps")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Argo Rollouts progressive delivery")
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
        print("Argo Rollouts validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Argo Rollouts apply requested.")
        return 0
    if args.dry_run:
        print("Argo Rollouts dry-run passed.")
        print("Rollout strategy is configured.")
        print(f"GitOps overlay: {ARGO_ROLLOUTS_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Argo Rollouts requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
