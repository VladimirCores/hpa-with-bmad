#!/usr/bin/env python3
"""Install Cilium networking for HPDC dev cluster (online mode)."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CILIUM_VERSION = "1.16.5"
CILIUM_NAMESPACE = "kube-system"


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    result = subprocess.run(command, check=False)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def install_cilium_with_helm() -> None:
    """Install Cilium using Helm chart."""
    print("\n--- Installing Cilium networking ---")

    # Check if helm is available
    if not subprocess.run(["which", "helm"], capture_output=True).returncode == 0:
        print("Helm not found, installing Cilium with kubectl apply...")
        install_cilium_with_kubectl()
        return

    # Add Cilium Helm repo
    print("Adding Cilium Helm repository...")
    run(["helm", "repo", "add", "cilium", "https://helm.cilium.io/"])
    run(["helm", "repo", "update"])

    # Install Cilium
    print(f"Installing Cilium {CILIUM_VERSION}...")
    run([
        "helm", "install", "cilium", "cilium/cilium",
        "--namespace", CILIUM_NAMESPACE,
        "--version", CILIUM_VERSION,
        "--set", "kubeProxyReplacement=true",
        "--set", "k8sServiceHost=10.6.0.2",
        "--set", "k8sServicePort=6443",
        "--set", "ipam.mode=cluster-pool",
        "--set", "cluster.name=hpdc-talos",
        "--set", "cluster.id=1",
        "--wait",
    ])

    # Verify installation
    print("Verifying Cilium installation...")
    run(["kubectl", "rollout", "status", "daemonset/cilium", "-n", CILIUM_NAMESPACE, "--timeout=120s"])
    run(["kubectl", "rollout", "status", "deployment/cilium-operator", "-n", CILIUM_NAMESPACE, "--timeout=120s"])

    print("Cilium installed successfully.")


def install_cilium_with_kubectl() -> None:
    """Install Cilium using kubectl apply (fallback method)."""
    print("\n--- Installing Cilium networking (kubectl method) ---")

    cilium_url = f"https://raw.githubusercontent.com/cilium/cilium/v{CILIUM_VERSION}/install/kubernetes/cilium.yaml"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Download Cilium manifest
        print(f"Downloading Cilium manifest...")
        subprocess.run(
            ["curl", "-sLo", tmp_path, cilium_url],
            check=True,
        )

        # Apply the manifest
        print("Applying Cilium manifest...")
        run(["kubectl", "apply", "-f", tmp_path])

        # Wait for Cilium to be ready
        print("Waiting for Cilium to be ready...")
        run(["kubectl", "rollout", "status", "daemonset/cilium", "-n", CILIUM_NAMESPACE, "--timeout=180s"])
        run(["kubectl", "rollout", "status", "deployment/cilium-operator", "-n", CILIUM_NAMESPACE, "--timeout=120s"])

        print("Cilium installed successfully.")

    finally:
        import os
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def verify_cilium() -> None:
    """Verify Cilium installation."""
    print("\n--- Verifying Cilium installation ---")

    # Check Cilium pods
    print("Checking Cilium pods...")
    run(["kubectl", "get", "pods", "-n", CILIUM_NAMESPACE, "-l", "k8s-app=cilium"])

    # Check Cilium status
    print("\nChecking Cilium status...")
    run(["kubectl", "get", "daemonset", "cilium", "-n", CILIUM_NAMESPACE])

    # Check Cilium operator
    print("\nChecking Cilium operator...")
    run(["kubectl", "get", "deployment", "cilium-operator", "-n", CILIUM_NAMESPACE])

    # Check kube-dns
    print("\nChecking kube-dns...")
    run(["kubectl", "get", "service", "kube-dns", "-n", CILIUM_NAMESPACE])


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Cilium networking for HPDC dev cluster")
    parser.add_argument("--dry-run", action="store_true", help="validate and print commands without applying")
    parser.add_argument("--check", action="store_true", help="validate prerequisites without applying")
    parser.add_argument("--verify", action="store_true", help="verify existing installation")
    args = parser.parse_args()

    if args.check:
        print("Cilium installation prerequisites validated.")
        return 0

    if args.verify:
        verify_cilium()
        return 0

    if args.dry_run:
        print(f"Cilium version: {CILIUM_VERSION}")
        print(f"Namespace: {CILIUM_NAMESPACE}")
        print("Installation method: Helm (preferred) or kubectl apply (fallback)")
        return 0

    install_cilium_with_helm()
    verify_cilium()

    print("\nCilium networking installation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
