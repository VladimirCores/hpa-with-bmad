#!/usr/bin/env python3
"""Install the HPDC Cilium dev cluster from offline GitOps manifests."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CILIUM_VERSION = "1.19.6"
CILIUM_IMAGE = ROOT / "output" / "cilium" / "images" / f"cilium-agent-v{CILIUM_VERSION}"
TALOSCONFIG = ROOT / "output" / "talos" / "talosconfig"
CILIUM_BASE = ROOT / "gitops" / "cilium" / "base"
CILIUM_OVERLAY = ROOT / "gitops" / "cilium" / "overlays" / "dev"


def ensure_dirs() -> None:
    for directory in (CILIUM_BASE, CILIUM_OVERLAY, CILIUM_IMAGE.parent):
        directory.mkdir(parents=True, exist_ok=True)


def ensure_offline_image_cache() -> None:
    if CILIUM_IMAGE.exists():
        return
    raise RuntimeError(
        "Cilium offline image cache not found. Pre-cache Cilium 1.19.6 images before offline bootstrap: "
        f"{CILIUM_IMAGE}"
    )


def ensure_talosconfig() -> None:
    if TALOSCONFIG.exists():
        return
    raise RuntimeError(f"Talos config not found: {TALOSCONFIG}")


def validate_manifests() -> list[str]:
    failures = []
    required_files = [
        CILIUM_BASE / "cilium.yaml",
        CILIUM_BASE / "cilium-l2-policy.yaml",
        CILIUM_BASE / "cilium-loadbalancer-ippool.yaml",
        CILIUM_OVERLAY / "kustomization.yaml",
    ]
    for path in required_files:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    cilium = (CILIUM_BASE / "cilium.yaml").read_text(encoding="utf-8")
    l2 = (CILIUM_BASE / "cilium-l2-policy.yaml").read_text(encoding="utf-8")
    pool = (CILIUM_BASE / "cilium-loadbalancer-ippool.yaml").read_text(encoding="utf-8")
    if "kubeProxyReplacement:" not in cilium or "enableOnAllNodes: true" not in cilium:
        failures.append("cilium.yaml missing kubeProxyReplacement enableOnAllNodes:true")
    if "l2AnnouncementMode: true" not in cilium:
        failures.append("cilium.yaml missing l2AnnouncementMode:true")
    if "CiliumL2AnnouncementPolicy" not in l2:
        failures.append("cilium-l2-policy.yaml missing CiliumL2AnnouncementPolicy")
    if "CiliumLoadBalancerIPPool" not in pool:
        failures.append("cilium-loadbalancer-ippool.yaml missing CiliumLoadBalancerIPPool")
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
    kubectl = args.kubectl
    if shutil.which(kubectl) is None:
        raise RuntimeError(f"kubectl executable not found: {kubectl}")
    env = os.environ.copy()
    env["TALOSCTL_OFFLINE_MODE"] = "1"
    run([kubectl, "apply", "-k", str(CILIUM_OVERLAY)], env=env)
    run([kubectl, "rollout", "status", "daemonset/cilium", "-n", "kube-system"], env=env)
    run([kubectl, "rollout", "status", "deployment/cilium-operator", "-n", "kube-system"], env=env)
    run([kubectl, "get", "service", "kube-dns", "-n", "kube-system"], env=env)


def check_scaffold() -> list[str]:
    failures = []
    required = [
        ROOT / "scripts" / "startup.dev.py",
        ROOT / "scripts" / "steps" / "03-install-cilium-dev.py",
        ROOT / "docs" / "cilium-dev-networking.md",
        ROOT / "tests" / "test_install_cilium_dev.py",
    ]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC Cilium dev cluster")
    parser.add_argument("--offline", action="store_true", default=True, help="require offline artifacts")
    parser.add_argument("--dry-run", action="store_true", help="validate and print commands without applying manifests")
    parser.add_argument("--check", action="store_true", help="validate required scaffold files without applying manifests")
    parser.add_argument("--apply", action="store_true", help="apply Cilium manifests from GitOps overlay")
    parser.add_argument("--kubectl", default="kubectl", help="kubectl executable name")
    args = parser.parse_args()

    if args.check:
        failures = check_scaffold()
        if failures:
            print("Cilium bootstrap scaffold validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        failures = validate_manifests()
        if failures:
            print("Cilium manifest validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("Cilium bootstrap scaffold validation passed.")
        return 0

    ensure_dirs()
    if args.offline:
        ensure_offline_image_cache()
    ensure_talosconfig()
    failures = validate_manifests()
    if failures:
        print("Cilium manifest validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    if args.apply:
        apply_manifests(args)
        print("Cilium dev cluster installation complete.")
        return 0

    if args.dry_run:
        print("Cilium dev cluster dry-run passed.")
        print(f"Cilium version: {CILIUM_VERSION}")
        print(f"Cilium offline image cache: {CILIUM_IMAGE.relative_to(ROOT)}")
        print(f"Talos config: {TALOSCONFIG.relative_to(ROOT)}")
        print(f"GitOps overlay: {CILIUM_OVERLAY.relative_to(ROOT)}")
        return 0

    print("Cilium dev cluster install requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
