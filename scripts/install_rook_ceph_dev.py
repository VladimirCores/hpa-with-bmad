#!/usr/bin/env python3
"""Install the HPDC Rook-Ceph dev cluster from offline GitOps manifests."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOK_VERSION = "1.20.3"
ROOK_IMAGE = ROOT / "output" / "rook-ceph" / "images" / f"rook-ceph-v{ROOK_VERSION}"
TALOSCONFIG = ROOT / "output" / "talos" / "talosconfig"
CILIUM_IMAGE = ROOT / "output" / "cilium" / "images" / f"cilium-agent-v1.19.6"
QEMU_DISK = ROOT / "output" / "qemu" / "talos-v1.img"
ROOK_BASE = ROOT / "gitops" / "rook-ceph" / "base"
ROOK_OVERLAY = ROOT / "gitops" / "rook-ceph" / "overlays" / "dev"


def ensure_dirs() -> None:
    for directory in (ROOK_BASE, ROOK_OVERLAY, ROOK_IMAGE.parent):
        directory.mkdir(parents=True, exist_ok=True)


def ensure_offline_image_cache() -> None:
    if ROOK_IMAGE.exists():
        return
    raise RuntimeError(
        "Rook-Ceph offline image cache not found. Pre-cache Rook-Ceph 1.20.3 images before offline bootstrap: "
        f"{ROOK_IMAGE}"
    )


def ensure_talosconfig() -> None:
    if TALOSCONFIG.exists():
        return
    raise RuntimeError(f"Talos config not found: {TALOSCONFIG}")


def ensure_cilium() -> None:
    if CILIUM_IMAGE.exists():
        return
    raise RuntimeError(f"Cilium offline image cache not found: {CILIUM_IMAGE}")


def ensure_qemu_disk() -> None:
    if QEMU_DISK.exists():
        return
    raise RuntimeError(f"Persistent QEMU disk not found: {QEMU_DISK}")


def validate_manifests() -> list[str]:
    failures = []
    required_files = [
        ROOK_BASE / "rook-ceph.yaml",
        ROOK_BASE / "storageclasses.yaml",
        ROOK_OVERLAY / "kustomization.yaml",
    ]
    for path in required_files:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    rook = (ROOK_BASE / "rook-ceph.yaml").read_text(encoding="utf-8")
    storage = (ROOK_BASE / "storageclasses.yaml").read_text(encoding="utf-8")
    if "quay.io/rook/ceph:v1.20.3" not in rook:
        failures.append("rook-ceph.yaml missing Rook-Ceph 1.20.3 image")
    if "kind: CephCluster" not in rook:
        failures.append("rook-ceph.yaml missing CephCluster")
    if "count: 1" not in rook:
        failures.append("rook-ceph.yaml missing single mon/osd topology")
    if "dataEmptyDir: false" not in rook:
        failures.append("rook-ceph.yaml must not use dataEmptyDir for Ceph OSD data")
    if "dataDirHostPath: /var/lib/rook" not in rook:
        failures.append("rook-ceph.yaml missing Rook dataDirHostPath")
    if "devices:" not in rook or "/dev/disk/by-id/qemu_talos-v1" not in rook:
        failures.append("rook-ceph.yaml missing persistent QEMU disk OSD device")
    if "storageClassDeviceSets:" not in rook:
        failures.append("rook-ceph.yaml missing storageClassDeviceSets")
    if "pool: rook-ceph" not in storage:
        failures.append("storageclasses.yaml missing rook-ceph pool")
    if "provisioner: rook-ceph.rook.io/block" not in storage:
        failures.append("storageclasses.yaml missing RBD StorageClass")
    if "provisioner: rook-ceph.rook.io/filesystem" not in storage:
        failures.append("storageclasses.yaml missing CephFS StorageClass")
    if "volumeBindingMode: Immediate" not in storage:
        failures.append("storageclasses.yaml missing immediate volume binding")
    if "allowVolumeExpansion: true" not in storage:
        failures.append("storageclasses.yaml missing volume expansion")
    return failures


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    result = subprocess.run(command, check=False)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def detect_existing_cluster(kubectl: str) -> None:
    env = os.environ.copy()
    env["TALOSCTL_OFFLINE_MODE"] = "1"
    run([kubectl, "-n", "rook-ceph", "get", "cephcluster", "rook-ceph"], env=env, check=False)
    run([kubectl, "-n", "rook-ceph", "get", "osd"], env=env, check=False)


def apply_manifests(args: argparse.Namespace) -> None:
    ensure_offline_image_cache()
    ensure_talosconfig()
    ensure_cilium()
    ensure_qemu_disk()
    kubectl = args.kubectl
    if shutil.which(kubectl) is None:
        raise RuntimeError(f"kubectl executable not found: {kubectl}")
    env = os.environ.copy()
    env["TALOSCTL_OFFLINE_MODE"] = "1"
    detect_existing_cluster(kubectl)
    run([kubectl, "apply", "-k", str(ROOK_OVERLAY)], env=env)
    run([kubectl, "rollout", "status", "deployment/rook-ceph-operator", "-n", "rook-ceph"], env=env)
    run([kubectl, "get", "storageclass", "rook-ceph-rbd", "rook-ceph-cephfs"], env=env)
    if args.cleanup:
        print("Cleanup flag accepted; this offline installer does not wipe QEMU disk images.")


def check_scaffold() -> list[str]:
    failures = []
    required = [
        ROOT / "scripts" / "install-rook-ceph-dev.py",
        ROOT / "scripts" / "install_rook_ceph_dev.py",
        ROOT / "docs" / "rook-ceph-dev-storage.md",
        ROOT / "tests" / "test_install_rook_ceph_dev.py",
    ]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC Rook-Ceph dev cluster")
    parser.add_argument("--offline", action="store_true", default=True, help="require offline artifacts")
    parser.add_argument("--dry-run", action="store_true", help="validate and print commands without applying manifests")
    parser.add_argument("--check", action="store_true", help="validate required scaffold files without applying manifests")
    parser.add_argument("--apply", action="store_true", help="apply Rook-Ceph manifests from GitOps overlay")
    parser.add_argument("--cleanup", action="store_true", help="allow destructive cleanup behavior only for --apply")
    parser.add_argument("--kubectl", default="kubectl", help="kubectl executable name")
    args = parser.parse_args()

    if args.check:
        failures = check_scaffold()
        if failures:
            print("Rook-Ceph bootstrap scaffold validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        failures = validate_manifests()
        if failures:
            print("Rook-Ceph manifest validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("Rook-Ceph bootstrap scaffold validation passed.")
        return 0

    ensure_dirs()
    if args.offline:
        ensure_offline_image_cache()
    ensure_talosconfig()
    ensure_cilium()
    ensure_qemu_disk()
    failures = validate_manifests()
    if failures:
        print("Rook-Ceph manifest validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    if args.apply:
        apply_manifests(args)
        print("Rook-Ceph dev cluster installation complete.")
        return 0

    if args.dry_run:
        print("Rook-Ceph dev cluster dry-run passed.")
        print(f"Rook-Ceph version: {ROOK_VERSION}")
        print(f"Rook-Ceph offline image cache: {ROOK_IMAGE.relative_to(ROOT)}")
        print(f"Talos config: {TALOSCONFIG.relative_to(ROOT)}")
        print(f"Cilium cache: {CILIUM_IMAGE.relative_to(ROOT)}")
        print(f"Persistent QEMU disk: {QEMU_DISK.relative_to(ROOT)}")
        print(f"GitOps overlay: {ROOK_OVERLAY.relative_to(ROOT)}")
        return 0

    print("Rook-Ceph dev cluster install requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
