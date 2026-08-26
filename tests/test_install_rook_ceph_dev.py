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
    assert "dataDirHostPath: /var/lib/rook" in rook
    assert "/dev/vdb" in rook or "deviceFilter: vdb" in rook
    assert "useAllDevices: false" in rook
    assert "rook-ceph-rbd" in storage
    assert "provisioner: rook-ceph.rbd.csi.ceph.com" in storage
    assert "kind: CephBlockPool" in storage
    assert "volumeBindingMode: Immediate" in storage
    assert "allowVolumeExpansion: true" in storage
    assert "../../base/rook-ceph.yaml" in overlay
    assert "../../base/storageclasses.yaml" in overlay


def test_check_mode() -> None:
    result = run([sys.executable, "scripts/startup.dev.py", "--offline", "--check", "--step", "05-install-rook-ceph-dev.py"])
    assert result.returncode == 0
    log = (ROOT / "output" / "startup.dev.log").read_text(encoding="utf-8")
    assert "Rook-Ceph bootstrap scaffold validation passed." in log


def test_dry_run_mode() -> None:
    result = run([sys.executable, "scripts/startup.dev.py", "--offline", "--dry-run", "--step", "05-install-rook-ceph-dev.py"])
    assert result.returncode == 0
    log = (ROOT / "output" / "startup.dev.log").read_text(encoding="utf-8")
    assert f"Rook-Ceph version: {ROOK_VERSION}" in log
    assert "Persistent QEMU disk: /dev/vdb" in log
    assert "GitOps overlay: gitops/rook-ceph/overlays/dev" in log


def test_missing_image_cache_fails() -> None:
    """Registry probe failure must raise, not silently pass."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "install_rook_ceph_dev", ROOT / "scripts" / "gitops" / "install_rook_ceph_dev.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    original = mod.REGISTRY
    mod.REGISTRY = "http://127.0.0.1:1"  # unreachable
    try:
        try:
            mod.ensure_offline_image_cache()
            raised = False
        except RuntimeError:
            raised = True
        assert raised, "expected RuntimeError when registry probe fails"
    finally:
        mod.REGISTRY = original

def main() -> int:
    validate_manifests()
    test_check_mode()
    test_dry_run_mode()
    test_missing_image_cache_fails()
    print("Rook-Ceph bootstrap scaffold validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
