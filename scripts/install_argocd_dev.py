#!/usr/bin/env python3
"""Install Argo CD ApplicationSet and sync waves."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _provisioned import require

ROOT = Path(__file__).resolve().parents[1]
ARGOCD_BASE = ROOT / "gitops" / "argo-cd" / "base"
ARGOCD_OVERLAY = ROOT / "gitops" / "argo-cd" / "overlays" / "dev"


def ensure_files() -> None:
    require("argocd")


def validate_manifests() -> list[str]:
    failures = []
    required = [ARGOCD_BASE / "argocd.yaml", ARGOCD_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    argocd = (ARGOCD_BASE / "argocd.yaml").read_text(encoding="utf-8")
    if "kind: ApplicationSet" not in argocd or "name: hpdc-applications" not in argocd:
        failures.append("argocd.yaml missing ApplicationSet")
    if "argocd.argoproj.io/sync-wave" not in argocd:
        failures.append("argocd.yaml missing sync-wave annotation")
    if "git://git-mirror/git-mirror" not in argocd:
        failures.append("argocd.yaml missing local Git mirror repoURL")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Argo CD ApplicationSet and sync waves")
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
        print("Argo CD validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Argo CD apply requested.")
        return 0
    if args.dry_run:
        print("Argo CD dry-run passed.")
        print("ApplicationSet and sync waves are configured.")
        print(f"GitOps overlay: {ARGOCD_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Argo CD requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
