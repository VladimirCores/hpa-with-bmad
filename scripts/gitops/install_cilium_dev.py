#!/usr/bin/env python3
"""Install the HPDC Cilium dev cluster using Helm with Talos-compatible settings."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import component_versions

component_versions.load_dotenv()
ROOT = Path(__file__).resolve().parents[2]
CILIUM_VERSION = component_versions.get("HPDC_CILIUM_VERSION")
CILIUM_BASE = ROOT / "gitops" / "cilium" / "base"
CILIUM_OVERLAY = ROOT / "gitops" / "cilium" / "overlays" / "dev"

TALOS_CILIUM_VALUES = {
    "kubeProxyReplacement": "true",
    "ipam.mode": "cluster-pool",
    "ipam.operator.clusterPoolIPv4PodCIDRList": "10.244.0.0/16",
    "cluster.name": "hpdc-talos",
    "cluster.id": "1",
    "kind.enabled": "true",
    "routingMode": "native",
    "ipv4NativeRoutingCIDR": "10.244.0.0/16",
    "autoDirectNodeRoutes": "true",
    "bpf.masquerade": "true",
    "securityContext.privileged": "true",
    "cgroup.autoMount.enabled": "false",
    "cgroup.hostRoot": "/sys/fs/cgroup",
}


def run(command: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    result = subprocess.run(command, check=False, env=env)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def get_k8s_service_host_port() -> tuple[str, str]:
    result = subprocess.run(
        ["kubectl", "get", "nodes", "-o", "jsonpath={.items[0].status.addresses[?(@.type==\"InternalIP\")].address}"],
        capture_output=True, text=True, check=True,
    )
    host = result.stdout.strip()
    return host, "6443"


def install_cilium_helm(args: argparse.Namespace) -> None:
    helm = args.helm
    if shutil.which(helm) is None:
        raise RuntimeError(f"helm executable not found: {helm}")
    kubectl = args.kubectl
    if shutil.which(kubectl) is None:
        raise RuntimeError(f"kubectl executable not found: {kubectl}")

    host, port = get_k8s_service_host_port()
    values_args = []
    for key, value in TALOS_CILIUM_VALUES.items():
        values_args.extend(["--set", f"{key}={value}"])
    values_args.extend(["--set", f"k8sServiceHost={host}"])
    values_args.extend(["--set", f"k8sServicePort={port}"])

    run([
        helm, "upgrade", "--install", "cilium", "cilium/cilium",
        "--namespace", "kube-system",
        "--version", CILIUM_VERSION,
        *values_args,
    ])

    run([kubectl, "rollout", "status", "daemonset/cilium", "-n", "kube-system", "--timeout=300s"])
    run([kubectl, "rollout", "status", "deployment/cilium-operator", "-n", "kube-system", "--timeout=300s"])
    run([kubectl, "get", "pods", "-n", "kube-system", "-l", "k8s-app=cilium"])


def check_scaffold() -> list[str]:
    failures = []
    required = [
        ROOT / "scripts" / "startup.dev.py",
        ROOT / "scripts" / "steps" / "03-install-cilium-dev.py",
    ]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC Cilium dev cluster")
    parser.add_argument("--offline", action="store_true", help="accepted for runner compatibility")
    parser.add_argument("--dry-run", action="store_true", help="validate and print commands without installing")
    parser.add_argument("--check", action="store_true", help="validate required scaffold files")
    parser.add_argument("--apply", action="store_true", help="install Cilium via Helm")
    parser.add_argument("--helm", default="helm", help="helm executable name")
    parser.add_argument("--kubectl", default="kubectl", help="kubectl executable name")
    args = parser.parse_args()

    if args.check:
        failures = check_scaffold()
        if failures:
            print("Cilium scaffold validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("Cilium scaffold validation passed.")
        return 0

    if args.apply:
        install_cilium_helm(args)
        print("Cilium dev cluster installation complete.")
        return 0

    if args.dry_run:
        host, port = get_k8s_service_host_port()
        print("Cilium dev cluster dry-run passed.")
        print(f"Cilium version: {CILIUM_VERSION}")
        print(f"k8sServiceHost: {host}")
        print(f"k8sServicePort: {port}")
        for key, value in TALOS_CILIUM_VALUES.items():
            print(f"  {key}: {value}")
        return 0

    print("Cilium install requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
