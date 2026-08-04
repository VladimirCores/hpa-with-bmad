#!/usr/bin/env python3
"""Validate the Cilium offline installer scaffold."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    ROOT / "scripts" / "install-cilium-dev.py",
    ROOT / "scripts" / "install_cilium_dev.py",
    ROOT / "gitops" / "cilium" / "base" / "cilium.yaml",
    ROOT / "gitops" / "cilium" / "base" / "cilium-l2-policy.yaml",
    ROOT / "gitops" / "cilium" / "base" / "cilium-loadbalancer-ippool.yaml",
    ROOT / "gitops" / "cilium" / "overlays" / "dev" / "kustomization.yaml",
    ROOT / "docs" / "cilium-dev-networking.md",
    ROOT / "tests" / "test_install_cilium_dev.py",
]


def main() -> int:
    failures = []
    for path in REQUIRED_FILES:
        if not path.exists():
            failures.append(f"missing file: {path.relative_to(ROOT)}")
    cilium = (ROOT / "gitops" / "cilium" / "base" / "cilium.yaml").read_text(encoding="utf-8")
    l2 = (ROOT / "gitops" / "cilium" / "base" / "cilium-l2-policy.yaml").read_text(encoding="utf-8")
    pool = (ROOT / "gitops" / "cilium" / "base" / "cilium-loadbalancer-ippool.yaml").read_text(encoding="utf-8")
    if "kubeProxyReplacement:" not in cilium or "enableOnAllNodes: true" not in cilium:
        failures.append("cilium.yaml missing kubeProxyReplacement enableOnAllNodes:true")
    if "l2AnnouncementMode: true" not in cilium:
        failures.append("cilium.yaml missing l2AnnouncementMode:true")
    if "CiliumL2AnnouncementPolicy" not in l2:
        failures.append("cilium-l2-policy.yaml missing CiliumL2AnnouncementPolicy")
    if "CiliumLoadBalancerIPPool" not in pool:
        failures.append("cilium-loadbalancer-ippool.yaml missing CiliumLoadBalancerIPPool")
    if failures:
        print("Cilium bootstrap scaffold validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Cilium bootstrap scaffold validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
