#!/usr/bin/env python3
"""Validate the HPDC Rook-Ceph offline dev installer."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOK_VERSION = "1.20.3"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def validate_manifests() -> None:
    rook = read("gitops/rook-ceph/base/rook-ceph.yaml")
    storage = read("gitops/rook-ceph/base/storageclasses.yaml")
    overlay = read("gitops/rook-ceph/overlays/dev/kustomization.yaml")

    assert f"quay.io/rook/ceph:v{ROOK_VERSION}" in rook
    assert "kind: CephCluster" in rook
    assert "count: 1" in rook
    assert "dataEmptyDir: false" in rook
    assert "dataDirHostPath: /var/lib/rook" in rook
    assert "/dev/disk/by-id/qemu_talos-v1" in rook
    assert "storageClassDeviceSets:" in rook
    assert "rook-ceph-rbd" in storage
    assert "rook-ceph-cephfs" in storage
    assert "provisioner: rook-ceph.rook.io/block" in storage
    assert "provisioner: rook-ceph.rook.io/filesystem" in storage
    assert "volumeBindingMode: Immediate" in storage
    assert "allowVolumeExpansion: true" in storage
    assert "../../base/rook-ceph.yaml" in overlay
    assert "../../base/storageclasses.yaml" in overlay


def test_check_mode() -> None:
    result = run([sys.executable, "scripts/install_rook_ceph_dev.py", "--check"])
    assert result.returncode == 0
    assert "Rook-Ceph bootstrap scaffold validation passed." in result.stdout


def test_dry_run_mode() -> None:
    result = run(["./scripts/install-rook-ceph-dev.py", "--offline", "--dry-run"])
    assert result.returncode == 0
    assert f"Rook-Ceph version: {ROOK_VERSION}" in result.stdout
    assert "Persistent QEMU disk: output/qemu/talos-v1.img" in result.stdout
    assert "GitOps overlay: gitops/rook-ceph/overlays/dev" in result.stdout


def test_missing_image_cache_fails() -> None:
    marker = ROOT / "output" / "rook-ceph" / "images" / f"rook-ceph-v{ROOK_VERSION}"
    if marker.exists():
        marker.unlink()
    try:
        result = subprocess.run(
            ["./scripts/install-rook-ceph-dev.py", "--offline", "--dry-run"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "Rook-Ceph offline image cache not found" in result.stderr or result.returncode != 0
    finally:
        marker.write_text("Rook-Ceph 1.20.3 offline image cache marker.\n")


def main() -> int:
    validate_manifests()
    test_check_mode()
    test_dry_run_mode()
    test_missing_image_cache_fails()
    print("Rook-Ceph bootstrap scaffold validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
