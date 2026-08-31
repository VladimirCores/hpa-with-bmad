#!/usr/bin/env python3
"""Install Argo CD ApplicationSet and sync waves."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from _provisioned import require
import component_versions

component_versions.load_all_dotenv()
ROOT = Path(__file__).resolve().parents[2]
ARGOCD_VERSION = component_versions.get("HPDC_ARGOCD_VERSION")
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
    if "http://10.6.0.1:9418/with-bmad.git" not in argocd:
        failures.append("argocd.yaml missing local Git mirror repoURL")
    if f"quay.io/argoproj/argocd:v{ARGOCD_VERSION}" not in argocd:
        failures.append(f"argocd.yaml missing Argo CD v{ARGOCD_VERSION} image")
    for component in ["argocd-server", "argocd-repo-server", "argocd-application-controller", "argocd-applicationset-controller", "argocd-redis"]:
        if f"name: {component}" not in argocd:
            failures.append(f"argocd.yaml missing {component}")
    if "kind: Service" not in argocd or "name: argocd-server" not in argocd:
        failures.append("argocd.yaml missing argocd-server Service")
    return failures


ARGOCD_INSTALL_MANIFEST = (
    "https://raw.githubusercontent.com/argoproj/argo-cd/"
    f"v{ARGOCD_VERSION}/manifests/install.yaml"
)
ARGOCD_INSTALL_MANIFEST_LOCAL = ROOT / "platform" / "manifests" / f"argocd-install-v{ARGOCD_VERSION}.yaml"
# public.ecr.aws is unreachable from dev nodes; use the same redis via docker.io
REDIS_IMAGE = (
    "docker.io/library/redis:"
    + component_versions.get("HPDC_ARGOCD_REDIS_VERSION")
)


def run(command: list[str], *, check: bool = True, env: dict[str, str] | None = None, input_text: str | None = None) -> int:
    print("$", " ".join(command))
    result = subprocess.run(command, check=False, env=env, input=input_text, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result.returncode


def apply_manifests() -> None:
    kubectl = shutil.which("kubectl")
    if kubectl is None:
        raise RuntimeError("kubectl is required for Argo CD install")

    # Official upstream manifests (CRDs exceed client-side apply annotation
    # limits; server-side apply handles them). Force conflicts so re-runs win.
    run([kubectl, "create", "namespace", "argocd"], check=False)
    manifest = str(ARGOCD_INSTALL_MANIFEST_LOCAL) if ARGOCD_INSTALL_MANIFEST_LOCAL.exists() else ARGOCD_INSTALL_MANIFEST
    subprocess.run(
        [kubectl, "apply", "-n", "argocd", "-f", manifest,
         "--server-side=true", "--force-conflicts"],
        check=True,
    )
    # Swap redis to a reachable registry mirror of the same image
    run([kubectl, "set", "image", "deploy/argocd-redis", f"redis={REDIS_IMAGE}", "-n", "argocd"])

    for workload in (
        ("deployment", "argocd-redis"),
        ("deployment", "argocd-repo-server"),
        ("statefulset", "argocd-application-controller"),
        ("deployment", "argocd-server"),
        ("deployment", "argocd-applicationset-controller"),
        ("deployment", "argocd-dex-server"),
        ("deployment", "argocd-notifications-controller"),
    ):
        run([kubectl, "rollout", "status", workload[0], workload[1], "-n", "argocd", "--timeout=600s"])

    # Wire the local git mirror as a known repository
    repo_patch = json.dumps({
        "data": {
            "repositories": (
                "- url: http://10.6.0.1:9418/with-bmad.git\n"
                "  type: git\n"
                "  name: hpdc-git-mirror\n"
            )
        }
    })
    run([kubectl, "patch", "cm", "argocd-cm", "-n", "argocd",
         "--type=merge", "-p", repo_patch])
    run([kubectl, "get", "service", "argocd-server", "-n", "argocd"])


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
        apply_manifests()
        print("Argo CD installation complete.")
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
