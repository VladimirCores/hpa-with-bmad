#!/usr/bin/env python3
"""Epic 11.3: Live Component Initialization

Initialize essential cluster components for the HPDC dev cluster.
This script focuses on components that work with the standard flannel CNI.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

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


def install_cert_manager() -> None:
    """Install cert-manager for TLS certificate management."""
    print("\n--- Installing cert-manager ---")

    # Add Jetstack Helm repo
    print("Adding Jetstack Helm repository...")
    run(["helm", "repo", "add", "jetstack", "https://charts.jetstack.io"])
    run(["helm", "repo", "update"])

    # Apply cert-manager CRDs
    print("Applying cert-manager CRDs...")
    run(["kubectl", "apply", "-f", "https://github.com/cert-manager/cert-manager/releases/download/v1.16.3/cert-manager.crds.yaml"])

    # Create namespace
    print("Creating cert-manager namespace...")
    run(["kubectl", "create", "namespace", "cert-manager"], check=False)

    # Install cert-manager with Helm
    print("Installing cert-manager...")
    run([
        "helm", "upgrade", "--install", "cert-manager", "jetstack/cert-manager",
        "--namespace", "cert-manager",
        "--version", "v1.16.3",
        "--set", "global.leaderElection.namespace=cert-manager",
        "--set", "webhook.timeoutSeconds=30",
        "--wait",
    ])

    # Verify installation
    print("Verifying cert-manager installation...")
    run(["kubectl", "rollout", "status", "deployment/cert-manager", "-n", "cert-manager", "--timeout=120s"])
    run(["kubectl", "rollout", "status", "deployment/cert-manager-webhook", "-n", "cert-manager", "--timeout=120s"])
    run(["kubectl", "rollout", "status", "deployment/cert-manager-cainjector", "-n", "cert-manager", "--timeout=120s"])

    print("cert-manager installed successfully.")


def install_harbor() -> None:
    """Install Harbor registry."""
    print("\n--- Installing Harbor registry ---")

    # Create namespace
    print("Creating harbor namespace...")
    run(["kubectl", "create", "namespace", "harbor"], check=False)

    # Install Harbor with Helm
    print("Installing Harbor...")
    run([
        "helm", "upgrade", "--install", "harbor", "harbor/harbor",
        "--namespace", "harbor",
        "--set", "expose.type=clusterIP",
        "--set", "expose.clusterIP.name=harbor-core",
        "--set", "expose.clusterIP.ports.httpPort=80",
        "--set", "expose.clusterIP.ports.httpsPort=443",
        "--set", "expose.tls.auto.commonName=harbor.hpdc.local",
        "--set", "persistence.enabled=false",
        "--set", "externalURL=http://harbor-core.harbor.svc.cluster.local",
        "--wait",
    ])

    print("Harbor installed successfully.")


def install_envoy_gateway() -> None:
    """Install Envoy Gateway for edge routing."""
    print("\n--- Installing Envoy Gateway ---")

    # Create namespace
    print("Creating envoy-gateway-system namespace...")
    run(["kubectl", "create", "namespace", "envoy-gateway-system"], check=False)

    # Install Envoy Gateway with Helm
    print("Installing Envoy Gateway...")
    run([
        "helm", "upgrade", "--install", "envoy-gateway",
        "oci://docker.io/envoyproxy/gateway-helm",
        "--namespace", "envoy-gateway-system",
        "--wait",
    ])

    print("Envoy Gateway installed successfully.")


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
        "--set", "api.enabled=true",
        "--set", "api.service.type=ClusterIP",
        "--set", "api.adminAccount.passwordHash=$2a$10$Z9YmnLzYJLmJLzYJLmJLmOeKk5Yz0Yz1Yz2Yz3Yz4Yz5Yz6Yz7",
        "--set", "api.adminAccount.name=admin",
        "--set", "api.adminAccount.password=admin",
        "--wait",
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
        "--wait",
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
        "--wait",
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
        "--set", "service.type=ClusterIP",
        "--wait",
    ])

    print("Grafana installed successfully.")


def main() -> int:
    """Main entry point for component initialization."""
    print("=== HPDC Dev Cluster Component Initialization ===\n")

    # Wait for nodes to be ready
    wait_for_nodes_ready()

    # Install core components
    components = [
        ("cert-manager", install_cert_manager),
        ("harbor", install_harbor),
        ("envoy-gateway", install_envoy_gateway),
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
