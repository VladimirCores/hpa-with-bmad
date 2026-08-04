#!/usr/bin/env python3
"""Install the HPDC Harbor offline registry from GitOps manifests."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARBOR_VERSION = "2.11.3"
HARBOR_IMAGE = ROOT / "output" / "harbor" / "images" / f"harbor-core-v{HARBOR_VERSION}"
TALOSCONFIG = ROOT / "output" / "talos" / "talosconfig"
ROOK_MARKER = ROOT / "output" / "rook-ceph" / "images" / f"rook-ceph-v1.20.3"
HARBOR_BASE = ROOT / "gitops" / "harbor" / "base"
HARBOR_OVERLAY = ROOT / "gitops" / "harbor" / "overlays" / "dev"


def ensure_dirs() -> None:
    for directory in (HARBOR_BASE, HARBOR_OVERLAY, HARBOR_IMAGE.parent):
        directory.mkdir(parents=True, exist_ok=True)


def ensure_offline_image_cache() -> None:
    required = [
        HARBOR_IMAGE,
        ROOT / "output" / "harbor" / "images" / f"harbor-registry-v{HARBOR_VERSION}",
        ROOT / "output" / "harbor" / "images" / f"harbor-jobservice-v{HARBOR_VERSION}",
        ROOT / "output" / "harbor" / "images" / f"harbor-trivy-adapter-v{HARBOR_VERSION}",
        ROOT / "output" / "harbor" / "images" / f"harbor-chartmuseum-v{HARBOR_VERSION}",
        ROOT / "output" / "harbor" / "images" / "harbor-redis-v1.23",
        ROOT / "output" / "harbor" / "images" / "harbor-postgresql-v15",
    ]
    missing = [path for path in required if not path.exists()]
    if not missing:
        return
    raise RuntimeError(
        "Harbor offline image cache not found. Pre-cache Harbor 2.11.3 and supporting images before offline bootstrap: "
        f"{', '.join(str(path.relative_to(ROOT)) for path in missing)}"
    )


def ensure_talosconfig() -> None:
    if TALOSCONFIG.exists():
        return
    raise RuntimeError(f"Talos config not found: {TALOSCONFIG}")


def ensure_rook_ceph() -> None:
    if ROOK_MARKER.exists():
        return
    raise RuntimeError(f"Rook-Ceph offline image cache not found: {ROOK_MARKER}")


def validate_manifests() -> list[str]:
    failures = []
    required_files = [
        HARBOR_BASE / "harbor.yaml",
        HARBOR_BASE / "harbor-values.yaml",
        HARBOR_BASE / "harbor-pvcs.yaml",
        HARBOR_OVERLAY / "kustomization.yaml",
    ]
    for path in required_files:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    harbor = (HARBOR_BASE / "harbor.yaml").read_text(encoding="utf-8")
    values = (HARBOR_BASE / "harbor-values.yaml").read_text(encoding="utf-8")
    pvcs = (HARBOR_BASE / "harbor-pvcs.yaml").read_text(encoding="utf-8")
    overlay = (HARBOR_OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")
    if "harbor/harbor-core:v2.11.3" not in harbor:
        failures.append("harbor.yaml missing Harbor core image")
    if "harbor/harbor-registry:v2.11.3" not in harbor:
        failures.append("harbor.yaml missing Harbor registry image")
    if "harbor/harbor-trivy-adapter:v2.11.3" not in harbor:
        failures.append("harbor.yaml missing Harbor Trivy adapter image")
    if "trivy:" not in values or "enabled: true" not in values:
        failures.append("harbor-values.yaml missing Trivy scanning enabled:true")
    if "clair" not in values.lower():
        failures.append("harbor-values.yaml missing Clair scanning configuration")
    if "cosign" not in values.lower() and "signature" not in values.lower():
        failures.append("harbor-values.yaml missing Cosign/signature verification configuration")
    if "storageClassName: rook-ceph-rbd" not in values:
        failures.append("harbor-values.yaml missing Rook-Ceph storageClass")
    if "kind: PersistentVolumeClaim" not in pvcs:
        failures.append("harbor-pvcs.yaml missing PVCs")
    if "storageClassName: rook-ceph-rbd" not in pvcs:
        failures.append("harbor-pvcs.yaml missing Rook-Ceph PVC storageClass")
    if "../../base/harbor.yaml" not in overlay:
        failures.append("Harbor overlay missing harbor.yaml")
    if "../../base/harbor-values.yaml" not in overlay:
        failures.append("Harbor overlay missing harbor-values.yaml")
    if "../../base/harbor-pvcs.yaml" not in overlay:
        failures.append("Harbor overlay missing harbor-pvcs.yaml")
    return failures


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    result = subprocess.run(command, check=False)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def apply_manifests(args: argparse.Namespace) -> None:
    ensure_offline_image_cache()
    ensure_talosconfig()
    ensure_rook_ceph()
    kubectl = args.kubectl
    if shutil.which(kubectl) is None:
        raise RuntimeError(f"kubectl executable not found: {kubectl}")
    env = os.environ.copy()
    env["TALOSCTL_OFFLINE_MODE"] = "1"
    run([kubectl, "apply", "-k", str(HARBOR_OVERLAY)], env=env)
    run([kubectl, "rollout", "status", "deployment/harbor-core", "-n", "harbor"], env=env)
    run([kubectl, "rollout", "status", "deployment/harbor-registry", "-n", "harbor"], env=env)
    run([kubectl, "rollout", "status", "deployment/harbor-trivy-adapter", "-n", "harbor"], env=env)
    run([kubectl, "get", "service", "harbor", "-n", "harbor"], env=env)


def check_scaffold() -> list[str]:
    failures = []
    required = [
        ROOT / "scripts" / "install-harbor-dev.py",
        ROOT / "scripts" / "install_harbor_dev.py",
        ROOT / "docs" / "harbor-dev-registry.md",
        ROOT / "tests" / "test_install_harbor_dev.py",
    ]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC Harbor offline registry")
    parser.add_argument("--offline", action="store_true", default=True, help="require offline artifacts")
    parser.add_argument("--dry-run", action="store_true", help="validate and print commands without applying manifests")
    parser.add_argument("--check", action="store_true", help="validate required scaffold files without applying manifests")
    parser.add_argument("--apply", action="store_true", help="apply Harbor manifests from GitOps overlay")
    parser.add_argument("--kubectl", default="kubectl", help="kubectl executable name")
    args = parser.parse_args()

    if args.check:
        failures = check_scaffold()
        if failures:
            print("Harbor bootstrap scaffold validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        failures = validate_manifests()
        if failures:
            print("Harbor manifest validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("Harbor bootstrap scaffold validation passed.")
        return 0

    ensure_dirs()
    if args.offline:
        ensure_offline_image_cache()
    ensure_talosconfig()
    ensure_rook_ceph()
    failures = validate_manifests()
    if failures:
        print("Harbor manifest validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    if args.apply:
        apply_manifests(args)
        print("Harbor offline registry installation complete.")
        return 0

    if args.dry_run:
        print("Harbor offline registry dry-run passed.")
        print(f"Harbor version: {HARBOR_VERSION}")
        print(f"Harbor offline image cache: {HARBOR_IMAGE.relative_to(ROOT)}")
        print(f"Rook-Ceph cache: {ROOK_MARKER.relative_to(ROOT)}")
        print(f"Talos config: {TALOSCONFIG.relative_to(ROOT)}")
        print(f"GitOps overlay: {HARBOR_OVERLAY.relative_to(ROOT)}")
        return 0

    print("Harbor offline registry install requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
