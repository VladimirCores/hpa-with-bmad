#!/usr/bin/env python3
"""Install Argo Rollouts progressive delivery."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _provisioned import require
import component_versions

component_versions.load_all_dotenv()
ROOT = Path(__file__).resolve().parents[2]
ARGO_ROLLOUTS_VERSION = component_versions.get("HPDC_ARGO_ROLLOUTS_VERSION")
ARGO_ROLLOUTS_IMAGE = ROOT / "output" / "argo-rollouts" / "images" / f"argo-rollouts-v{ARGO_ROLLOUTS_VERSION}"
ARGO_ROLLOUTS_BASE = ROOT / "gitops" / "argo-rollouts" / "base"
ARGO_ROLLOUTS_OVERLAY = ROOT / "gitops" / "argo-rollouts" / "overlays" / "dev"


def ensure_files() -> None:
    require("argo-rollouts")
    if not ARGO_ROLLOUTS_IMAGE.exists():
        raise RuntimeError(
            f"Argo Rollouts offline image cache marker not found. Pre-cache Argo Rollouts v{ARGO_ROLLOUTS_VERSION} before offline bootstrap: "
            f"{ARGO_ROLLOUTS_IMAGE.relative_to(ROOT)}"
        )


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
    if "kind: Deployment" not in rollouts or "name: argo-rollouts" not in rollouts:
        failures.append("argorollouts.yaml missing argo-rollouts Deployment")
    if f"quay.io/argoproj/argo-rollouts:v{ARGO_ROLLOUTS_VERSION}" not in rollouts:
        failures.append(f"argorollouts.yaml missing Argo Rollouts v{ARGO_ROLLOUTS_VERSION} image")
    if "kind: ClusterRole" not in rollouts or "name: argo-rollouts" not in rollouts:
        failures.append("argorollouts.yaml missing argo-rollouts ClusterRole")
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
        print(f"Argo Rollouts version: {ARGO_ROLLOUTS_VERSION}")
        print(f"Argo Rollouts image cache: {ARGO_ROLLOUTS_IMAGE.relative_to(ROOT)}")
        print("Rollout strategy is configured.")
        print(f"GitOps overlay: {ARGO_ROLLOUTS_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Argo Rollouts requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
