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

import component_versions

component_versions.load_dotenv()
ROOT = Path(__file__).resolve().parents[2]
TALOSCONFIG = ROOT / "output" / "talos" / "talosconfig"
LOCAL_PATH_VERSION = component_versions.get("HPDC_LOCAL_PATH_PROVISIONER_VERSION")
LOCAL_PATH_MANIFEST = ROOT / "platform" / "storage" / "local-path-storage.yaml"
LOCAL_PATH_MANIFEST_URL = f"https://raw.githubusercontent.com/rancher/local-path-provisioner/{LOCAL_PATH_VERSION}/deploy/local-path-storage.yaml"
DISK_CAPACITY_WORKER = os.getenv("HPDC_DISK_CAPACITY_WORKER", "10Gi")


def run(command: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    result = subprocess.run(command, check=False, env=env)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def ensure_dirs() -> None:
    TALOSCONFIG.parent.mkdir(parents=True, exist_ok=True)


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

    # Apply the vendored manifest (offline); fall back to downloading only if absent
    tmp_path: str | None = None
    if LOCAL_PATH_MANIFEST.exists():
        manifest = str(LOCAL_PATH_MANIFEST)
        print("Applying vendored local-path-provisioner manifest (offline)...")
    else:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp:
            tmp_path = tmp.name
        print(f"Downloading local-path-provisioner manifest...")
        subprocess.run(
            ["curl", "-sLo", tmp_path, LOCAL_PATH_MANIFEST_URL],
            check=True,
        )
        manifest = tmp_path

    try:
        # Apply the manifest
        run([kubectl, "apply", "-f", manifest])

        # Wait for the provisioner pod to be ready
        print("Waiting for local-path-provisioner to be ready...")
        run([kubectl, "rollout", "status", "deployment/local-path-provisioner", "-n", "local-path-storage", "--timeout=60s"])

        # Patch local-path-config ConfigMap with defaultVolumeSize from .env
        import json
        configmap_patch = json.dumps({
            "data": {
                "config.json": json.dumps({
                    "nodePathMap": [{
                        "node": "DEFAULT_PATH_FOR_NON_LISTED_NODES",
                        "paths": ["/opt/local-path-provisioner"]
                    }],
                    "defaultVolumeSize": DISK_CAPACITY_WORKER,
                }, indent=2)
            }
        })
        run([kubectl, "patch", "configmap", "local-path-config",
             "-n", "local-path-storage",
             "--type", "merge", "-p", configmap_patch])

        # Verify defaultVolumeSize was applied
        verify = subprocess.run(
            [kubectl, "get", "configmap", "local-path-config",
             "-n", "local-path-storage",
             "-o", "jsonpath={.data.config\\.json}"],
            text=True, capture_output=True)
        if verify.returncode == 0 and DISK_CAPACITY_WORKER not in (verify.stdout or ""):
            print(f"WARNING: defaultVolumeSize may not have been set "
                  f"(expected {DISK_CAPACITY_WORKER} in config.json)")
        elif verify.returncode != 0:
            print(f"WARNING: could not read local-path-config for verification: "
                  f"{verify.stderr.strip()}")

        # Set as default storage class
        print("Setting local-path as default StorageClass...")
        run([kubectl, "patch", "storageclass", "local-path",
             "-p", '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'])

        # Verify
        run([kubectl, "get", "storageclass"])
        print("local-path-provisioner installed successfully.")
    finally:
        if tmp_path and os.path.exists(tmp_path):
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
    parser.add_argument("--offline", action="store_true", help="accepted for runner compatibility")
    parser.add_argument("--apply", action="store_true", help="install the selected storage backend")
    parser.add_argument("--storage", choices=["rook-ceph", "local-path"], default="rook-ceph", help="storage backend to install")
    parser.add_argument("--dry-run", action="store_true", help="validate and print commands without applying")
    parser.add_argument("--check", action="store_true", help="validate prerequisites without applying")
    args = parser.parse_args()

    # Talos config is only required for the Talos-based rook-ceph path;
    # local-path (kind/docker) installs use kubectl only and kind never
    # produces a talosconfig.
    if args.storage == "rook-ceph":
        ensure_talosconfig()
    kubectl = ensure_kubectl()

    if args.check:
        print("Storage installation prerequisites validated.")
        return 0

    if args.dry_run:
        print(f"Storage backend: {args.storage}")
        print(f"StorageClass will be set as default.")
        return 0

    if not args.apply:
        print("Storage install requires --apply (or --dry-run / --check).", file=sys.stderr)
        return 2

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
