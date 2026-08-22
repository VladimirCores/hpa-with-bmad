#!/usr/bin/env python3
"""Install storage backend for HPDC dev cluster.

Supports two storage backends:
  - rook-ceph: Full Ceph storage with RBD and CephFS
  - local-path: Lightweight local-path-provisioner for development
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TALOSCONFIG = ROOT / "output" / "talos" / "talosconfig"
LOCAL_PATH_MANIFEST_URL = "https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.26/deploy/local-path-storage.yaml"


def run(command: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    result = subprocess.run(command, check=False, env=env)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def ensure_talosconfig() -> None:
    if not TALOSCONFIG.exists():
        raise RuntimeError(f"Talos config not found: {TALOSCONFIG}")


def ensure_kubectl() -> str:
    kubectl = shutil.which("kubectl")
    if kubectl is None:
        raise RuntimeError("kubectl is required for storage installation")
    return kubectl


def wait_for_nodes_ready(kubectl: str, timeout: int = 120) -> None:
    """Wait for all nodes to be Ready."""
    import time
    start = time.time()
    while time.time() - start < timeout:
        result = subprocess.run(
            [kubectl, "get", "nodes", "-o", "jsonpath={.items[*].status.conditions[?(@.type=='Ready')].status}"],
            capture_output=True, text=True,
        )
        statuses = result.stdout.strip().split()
        if all(s == "True" for s in statuses) and len(statuses) >= 1:
            print("All nodes are Ready.")
            return
        print(f"Waiting for nodes... ({len(statuses)} found, statuses: {statuses})")
        time.sleep(5)
    raise RuntimeError(f"Timeout waiting for nodes to be Ready after {timeout}s")


def install_local_path_provisioner(kubectl: str) -> None:
    """Install local-path-provisioner as the default storage class."""
    print("\n--- Installing local-path-provisioner ---")

    # Ensure PodSecurity labels for namespaces
    print("Setting PodSecurity labels for namespaces...")
    run([kubectl, "label", "namespace", "local-path-storage",
         "pod-security.kubernetes.io/enforce=privileged", "--overwrite"], check=False)
    run([kubectl, "label", "namespace", "default",
         "pod-security.kubernetes.io/enforce=privileged", "--overwrite"], check=False)

    # Download and apply the manifest
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        print(f"Downloading local-path-provisioner manifest...")
        subprocess.run(
            ["curl", "-sLo", tmp_path, LOCAL_PATH_MANIFEST_URL],
            check=True,
        )

        # Apply the manifest
        run([kubectl, "apply", "-f", tmp_path])

        # Wait for the provisioner pod to be ready
        print("Waiting for local-path-provisioner to be ready...")
        run([kubectl, "rollout", "status", "deployment/local-path-provisioner", "-n", "local-path-storage", "--timeout=60s"])

        # Set as default storage class
        print("Setting local-path as default StorageClass...")
        run([kubectl, "patch", "storageclass", "local-path",
             "-p", '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'])

        # Verify
        run([kubectl, "get", "storageclass"])
        print("local-path-provisioner installed successfully.")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def install_rook_ceph(kubectl: str) -> None:
    """Install Rook-Ceph operator and CephCluster."""
    print("\n--- Installing Rook-Ceph ---")

    rook_version = "1.14.12"
    rook_common_url = f"https://raw.githubusercontent.com/rook/rook/v{rook_version}/deploy/examples/common.yaml"
    rook_operator_url = f"https://raw.githubusercontent.com/rook/rook/v{rook_version}/deploy/examples/operator.yaml"
    rook_cluster_url = f"https://raw.githubusercontent.com/rook/rook/v{rook_version}/deploy/examples/cluster.yaml"

    # Use unique filenames for downloads
    common_path = f"/tmp/rook-common-{rook_version}.yaml"
    operator_path = f"/tmp/rook-operator-{rook_version}.yaml"
    cluster_path = f"/tmp/rook-cluster-{rook_version}.yaml"

    try:
        # Download common manifest
        print(f"Downloading Rook-Ceph common manifest...")
        subprocess.run(
            ["curl", "-sLo", common_path, rook_common_url],
            check=True,
        )

        # Download operator manifest
        print(f"Downloading Rook-Ceph operator manifest...")
        subprocess.run(
            ["curl", "-sLo", operator_path, rook_operator_url],
            check=True,
        )

        # Download cluster manifest
        print(f"Downloading Rook-Ceph cluster manifest...")
        subprocess.run(
            ["curl", "-sLo", cluster_path, rook_cluster_url],
            check=True,
        )

        # Create rook-ceph namespace
        print("Creating rook-ceph namespace...")
        run([kubectl, "create", "namespace", "rook-ceph"], check=False)

        # Apply common.yaml (creates service accounts and RBAC)
        print("Applying Rook-Ceph common resources...")
        run([kubectl, "apply", "-f", common_path])

        # Apply operator
        print("Applying Rook-Ceph operator...")
        run([kubectl, "apply", "-f", operator_path])

        # Wait for operator to be ready
        print("Waiting for Rook-Ceph operator to be ready...")
        run([kubectl, "rollout", "status", "deployment/rook-ceph-operator", "-n", "rook-ceph", "--timeout=120s"])

        # Apply cluster (with modifications for dev environment)
        print("Applying Rook-Ceph cluster configuration...")
        run([kubectl, "apply", "-f", cluster_path])

        # Wait for CephCluster to be ready
        print("Waiting for CephCluster to become ready (this may take several minutes)...")
        import time
        start = time.time()
        timeout = 600  # 10 minutes
        while time.time() - start < timeout:
            result = subprocess.run(
                [kubectl, "-n", "rook-ceph", "get", "cephcluster", "rook-ceph", "-o", "jsonpath={.status.phase}"],
                capture_output=True, text=True,
            )
            phase = result.stdout.strip()
            if phase == "Ready":
                print("CephCluster is Ready!")
                break
            print(f"CephCluster phase: {phase} (waiting...)")
            time.sleep(10)
        else:
            raise RuntimeError(f"Timeout waiting for CephCluster to be Ready after {timeout}s")

        # Create storage classes
        print("Creating Rook-Ceph StorageClasses...")
        create_rook_storage_classes(kubectl)

        # Set as default
        print("Setting rook-ceph-rbd as default StorageClass...")
        run([kubectl, "patch", "storageclass", "rook-ceph-rbd",
             "-p", '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'])

        # Verify
        run([kubectl, "get", "storageclass"])
        print("Rook-Ceph installed successfully.")

    finally:
        # Clean up downloaded files
        for path in [common_path, operator_path, cluster_path]:
            if os.path.exists(path):
                os.unlink(path)


def create_rook_storage_classes(kubectl: str) -> None:
    """Create RBD and CephFS StorageClasses."""
    rbd_sc = """apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: rook-ceph-rbd
provisioner: rook-ceph.rbd.csi.ceph.com
parameters:
  clusterID: rook-ceph
  pool: replicapool
  csi.storage.k8s.io/fstype: ext4
volumeBindingMode: Immediate
allowVolumeExpansion: true
reclaimPolicy: Delete"""

    cephfs_sc = """apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: rook-ceph-cephfs
provisioner: rook-ceph.cephfs.csi.ceph.com
parameters:
  clusterID: rook-ceph
  fsName: myfs
  pool: myfs-data0
volumeBindingMode: Immediate
allowVolumeExpansion: true
reclaimPolicy: Delete"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp:
        tmp.write(rbd_sc)
        tmp.write("\n---\n")
        tmp.write(cephfs_sc)
        tmp_path = tmp.name

    try:
        run([kubectl, "apply", "-f", tmp_path])
    finally:
        os.unlink(tmp_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Install storage backend for HPDC dev cluster")
    parser.add_argument("--storage", choices=["rook-ceph", "local-path"], default="rook-ceph", help="storage backend to install")
    parser.add_argument("--dry-run", action="store_true", help="validate and print commands without applying")
    parser.add_argument("--check", action="store_true", help="validate prerequisites without applying")
    args = parser.parse_args()

    ensure_talosconfig()
    kubectl = ensure_kubectl()

    if args.check:
        print("Storage installation prerequisites validated.")
        return 0

    if args.dry_run:
        print(f"Storage backend: {args.storage}")
        print(f"StorageClass will be set as default.")
        return 0

    # Wait for nodes
    wait_for_nodes_ready(kubectl)

    if args.storage == "local-path":
        install_local_path_provisioner(kubectl)
    elif args.storage == "rook-ceph":
        install_rook_ceph(kubectl)

    print(f"\nStorage backend '{args.storage}' installed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
