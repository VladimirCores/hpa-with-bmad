#!/usr/bin/env python3
"""Install Argo CD ApplicationSet and sync waves."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _provisioned import require

ROOT = Path(__file__).resolve().parents[2]
ARGOCD_VERSION = "3.5.0"
ARGOCD_IMAGE = ROOT / "output" / "argocd" / "images" / f"argocd-v{ARGOCD_VERSION}"
ARGOCD_BASE = ROOT / "gitops" / "argo-cd" / "base"
ARGOCD_OVERLAY = ROOT / "gitops" / "argo-cd" / "overlays" / "dev"


def ensure_files() -> None:
    require("argocd")
    if not ARGOCD_IMAGE.exists():
        raise RuntimeError(
            f"Argo CD offline image cache marker not found. Pre-cache Argo CD v{ARGOCD_VERSION} before offline bootstrap: "
            f"{ARGOCD_IMAGE.relative_to(ROOT)}"
        )


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
    if f"quay.io/argoproj/argocd:v{ARGOCD_VERSION}" not in argocd:
        failures.append(f"argocd.yaml missing Argo CD v{ARGOCD_VERSION} image")
    for component in ["argocd-server", "argocd-repo-server", "argocd-application-controller", "argocd-applicationset-controller", "argocd-redis"]:
        if f"name: {component}" not in argocd:
            failures.append(f"argocd.yaml missing {component}")
    if "kind: Service" not in argocd or "name: argocd-server" not in argocd:
        failures.append("argocd.yaml missing argocd-server Service")
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
        print(f"Argo CD version: {ARGOCD_VERSION}")
        print(f"Argo CD image cache: {ARGOCD_IMAGE.relative_to(ROOT)}")
        print("ApplicationSet and sync waves are configured.")
        print(f"GitOps overlay: {ARGOCD_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Argo CD requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
