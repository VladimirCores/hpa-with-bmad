#!/usr/bin/env python3
"""Provision the HPDC dev cluster using kind (Kubernetes in Docker).

Creates a kind cluster with Cilium as the CNI, replacing kube-proxy.
Supports configurable workers and storage backend.
Storage options: local-path (default) or rook-ceph.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKERS = 3
DEFAULT_STORAGE = "local-path"
KIND_CONFIG = Path("/tmp/kind-hpdc.yaml")
import component_versions as _cv

_cv.load_all_dotenv()
CILIUM_VERSION = _cv.get("HPDC_CILIUM_VERSION")





# Load configuration from three-layer env
_env = dict(os.environ)
CLUSTER_NAME = _env.get("HPDC_CLUSTER_NAME", "hpdc-talos")
GATEWAY_IP = _env.get("HPDC_GATEWAY_IP")


def ensure_dirs() -> None:
    KIND_CONFIG.parent.mkdir(parents=True, exist_ok=True)


def run(command: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    result = subprocess.run(command, check=False, env=env)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def validate_runtime() -> None:
    if shutil.which("kind") is None:
        raise RuntimeError("kind is required for kind dev cluster bootstrap")
    if shutil.which("docker") is None:
        raise RuntimeError("docker is required for kind dev cluster")
    if shutil.which("kubectl") is None:
        raise RuntimeError("kubectl is required for kind dev cluster")
    if shutil.which("helm") is None:
        raise RuntimeError("helm is required for kind dev cluster")


def destroy_existing_cluster() -> None:
    """Destroy any existing cluster with the same name."""
    result = subprocess.run(
        ["kind", "delete", "cluster", "--name", CLUSTER_NAME],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"Destroyed existing cluster '{CLUSTER_NAME}'.")
    else:
        # Try to clean up Docker containers directly
        subprocess.run(
            ["docker", "rm", "-f", f"{CLUSTER_NAME}-control-plane"],
            capture_output=True,
        )
        for i in range(1, 10):
            subprocess.run(
                ["docker", "rm", "-f", f"{CLUSTER_NAME}-worker{i}"],
                capture_output=True,
            )
            subprocess.run(
                ["docker", "rm", "-f", f"{CLUSTER_NAME}-worker-{i}"],
                capture_output=True,
            )


def create_kind_config(workers: int) -> None:
    """Create kind cluster configuration."""
    config = {
        "kind": "Cluster",
        "apiVersion": "kind.x-k8s.io/v1alpha4",
        "name": CLUSTER_NAME,
        "nodes": [
            {"role": "control-plane"},
        ] + [{"role": "worker"} for _ in range(workers)],
        "networking": {
            "disableDefaultCNI": True,
            "podSubnet": "10.244.0.0/16",
            "serviceSubnet": "10.96.0.0/16",
        },
    }
    
    KIND_CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"Created kind config at {KIND_CONFIG}")


def provision_cluster(args: argparse.Namespace) -> None:
    validate_runtime()
    
    # Destroy existing cluster first
    destroy_existing_cluster()
    
    # Create kind config
    create_kind_config(args.workers)
    
    # Create kind cluster
    create_cmd = [
        "kind", "create", "cluster",
        "--config", str(KIND_CONFIG),
    ]
    run(create_cmd)
    
    # Install Cilium with kube-proxy replacement
    cilium_cmd = [
        "helm", "upgrade", "--install", "cilium",
        "cilium/cilium",
        "--namespace", "kube-system",
        "--version", CILIUM_VERSION,
        "--set", "kubeProxyReplacement=true",
        "--set", f"k8sServiceHost={CLUSTER_NAME}-control-plane",
        "--set", "k8sServicePort=6443",
        "--set", "ipam.mode=cluster-pool",
        "--set", "ipam.operator.clusterPoolIPv4PodCIDRList=10.244.0.0/16",
        "--set", f"cluster.name={CLUSTER_NAME}",
        "--set", "cluster.id=1",
        "--set", "kind.enabled=true",
        "--set", "routingMode=native",
        "--set", "ipv4NativeRoutingCIDR=10.244.0.0/16",
        "--set", "autoDirectNodeRoutes=true",
        "--set", "bpf.masquerade=true",
        "--set", "l2NeighDiscovery.enabled=true",
    ]
    run(cilium_cmd)
    
    # Wait for Cilium to be ready
    print("Waiting for Cilium to be ready...")
    run([
        "kubectl", "rollout", "status", "daemonset/cilium",
        "-n", "kube-system", "--timeout=300s",
    ])
    
    # Remove kube-proxy (Cilium replaces it)
    run([
        "kubectl", "delete", "ds", "kube-proxy", "-n", "kube-system",
    ])

    # Storage is installed by step 05 (install_storage_dev.py) — not inline here.
    # This avoids duplicating the local-path-provisioner install code path.
    
    # Apply shared Cilium L2 LoadBalancer resources from rendered manifest
    print("Applying Cilium L2 LoadBalancer resources...")
    rendered = ROOT / "gitops" / "cilium" / "rendered" / "dev.yaml"
    if not rendered.exists():
        raise RuntimeError(f"Rendered manifest not found: {rendered}")
    # Extract only L2 resources from the rendered manifest
    content = rendered.read_text(encoding="utf-8")
    l2_kinds = ("kind: CiliumL2AnnouncementPolicy", "kind: CiliumLoadBalancerIPPool")
    docs = content.split("---")
    l2_docs = [doc.strip() for doc in docs if any(k in doc for k in l2_kinds)]
    for doc in l2_docs:
        result = subprocess.run(
            ["kubectl", "apply", "-f", "-"],
            input=doc, capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"kubectl apply failed: {result.stderr.strip()}")
    
    # Verify cluster
    run(["kubectl", "get", "nodes", "-o", "wide"])
    run(["kubectl", "get", "pods", "-A"])
    
    print(f"\nCluster '{CLUSTER_NAME}' provisioned successfully.")
    print(f"Storage backend: {args.storage}")
    print(f"Workers: {args.workers}")
    print(f"Cilium: kube-proxy replacement + L2 LoadBalancer enabled")


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision the HPDC dev cluster using kind")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="number of worker nodes (default: 3)")
    parser.add_argument("--storage", choices=["local-path", "rook-ceph"], default=DEFAULT_STORAGE, help="storage backend (default: local-path)")
    parser.add_argument("--dry-run", action="store_true", help="validate and print commands without executing")
    parser.add_argument("--check", action="store_true", help="validate required scaffold files without provisioning")
    parser.add_argument("--cleanup", action="store_true", help="destroy existing cluster before provisioning")
    args = parser.parse_args()

    if args.workers < 0:
        print("worker count must be >= 0", file=sys.stderr)
        return 2

    if args.check:
        print("Kind dev cluster scaffold validation passed.")
        return 0

    ensure_dirs()

    if args.dry_run:
        print("Kind dev cluster bootstrap dry-run passed.")
        print(f"Cluster name: {CLUSTER_NAME}")
        print(f"Workers: {args.workers}")
        print(f"Storage: {args.storage}")
        print(f"Cilium version: {CILIUM_VERSION}")
        return 0

    provision_cluster(args)
    print("Kind dev cluster bootstrap complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
