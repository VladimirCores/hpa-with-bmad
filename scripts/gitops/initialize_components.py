#!/usr/bin/env python3
"""Epic 11.3: Live Component Initialization

Initialize essential cluster components for the HPDC dev cluster.
This script installs components on a kind cluster with Cilium CNI.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import component_versions

component_versions.load_all_dotenv()

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    result = subprocess.run(command, check=False)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def wait_for_nodes_ready(timeout: int = 120) -> None:
    """Wait for all nodes to be Ready."""
    start = time.time()
    while time.time() - start < timeout:
        result = subprocess.run(
            ["kubectl", "get", "nodes", "-o", "jsonpath={.items[*].status.conditions[?(@.type=='Ready')].status}"],
            capture_output=True, text=True,
        )
        statuses = result.stdout.strip().split()
        if all(s == "True" for s in statuses) and len(statuses) >= 1:
            print("All nodes are Ready.")
            return
        print(f"Waiting for nodes... ({len(statuses)} found)")
        time.sleep(5)
    raise RuntimeError(f"Timeout waiting for nodes to be Ready after {timeout}s")


def install_kargo() -> None:
    """Install Kargo promotion workflow."""
    print("\n--- Installing Kargo ---")

    # Create namespace
    print("Creating kargo namespace...")
    run(["kubectl", "create", "namespace", "kargo"], check=False)

    # Install Kargo with Helm
    print("Installing Kargo...")
    run([
        "helm", "upgrade", "--install", "kargo",
        "oci://ghcr.io/akuity/kargo-charts/kargo",
        "--namespace", "kargo",
        "--set", "api.adminAccount.passwordHash=$2a$10$Z9yB0vG7F8y5vQ4z6u5u5e5u5e5u5e5u5e5u5e5u5e5u5e5u5e5u5e",
        "--set", "api.adminAccount.tokenSigningKey=signing-key-change-me-in-production",
    ])

    print("Kargo installed successfully.")


def install_argocd() -> None:
    """Install Argo CD GitOps."""
    print("\n--- Installing Argo CD ---")

    # Create namespace
    print("Creating argocd namespace...")
    run(["kubectl", "create", "namespace", "argocd"], check=False)

    # Install Argo CD with Helm
    print("Installing Argo CD...")
    run([
        "helm", "upgrade", "--install", "argocd", "argo/argo-cd",
        "--namespace", "argocd",
        "--set", "server.service.type=ClusterIP",
        "--set", "server.extraArgs[0]=--insecure",
        "--set", "configs.secret.argocdServerAdminPassword=admin123",
        "--set", "redis.image.repository=docker.io/library/redis",
        "--set", "redis.image.tag=8.6.4-alpine",
    ])

    print("Argo CD installed successfully.")


def install_victoria_metrics() -> None:
    """Install VictoriaMetrics for metrics collection."""
    print("\n--- Installing VictoriaMetrics ---")

    # Create namespace
    print("Creating monitoring namespace...")
    run(["kubectl", "create", "namespace", "monitoring"], check=False)

    # Install VictoriaMetrics with Helm
    print("Installing VictoriaMetrics...")
    run([
        "helm", "upgrade", "--install", "victoria-metrics",
        "victoriametrics/victoria-metrics-single",
        "--namespace", "monitoring",
        "--set", "server.persistentVolume.enabled=false",
        "--set", "server.retentionPeriod=7d",
    ])

    print("VictoriaMetrics installed successfully.")


def install_grafana() -> None:
    """Install Grafana for dashboards."""
    print("\n--- Installing Grafana ---")

    # Create namespace
    print("Creating monitoring namespace...")
    run(["kubectl", "create", "namespace", "monitoring"], check=False)

    # Install Grafana with Helm
    print("Installing Grafana...")
    run([
        "helm", "upgrade", "--install", "grafana", "grafana/grafana",
        "--namespace", "monitoring",
        "--set", "persistence.enabled=false",
        "--set", "adminPassword=admin",
        "--set", "adminUser=admin",
    ])

    print("Grafana installed successfully.")


def main() -> int:
    """Main entry point for component initialization."""
    print("=== HPDC Dev Cluster Component Initialization ===\n")

    # Wait for nodes to be ready
    wait_for_nodes_ready()

    # Install core components
    components = [
        ("kargo", install_kargo),
        ("argocd", install_argocd),
        ("victoria-metrics", install_victoria_metrics),
        ("grafana", install_grafana),
    ]

    failed = []
    for name, installer in components:
        try:
            print(f"\n{'='*60}")
            print(f"Installing {name}...")
            print(f"{'='*60}")
            installer()
        except Exception as e:
            print(f"Failed to install {name}: {e}")
            failed.append(name)
            continue

    # Summary
    print(f"\n{'='*60}")
    print("Component Installation Summary")
    print(f"{'='*60}")

    if failed:
        print(f"Failed components: {', '.join(failed)}")
        print("Some components failed to install. Check the logs above for details.")
        return 1
    else:
        print("All components installed successfully!")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
