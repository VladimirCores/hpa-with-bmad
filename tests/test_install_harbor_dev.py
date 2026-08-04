#!/usr/bin/env python3
"""Validate the HPDC Harbor offline registry installer scaffold."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARBOR_VERSION = "2.11.3"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def validate_manifests() -> None:
    harbor = read("gitops/harbor/base/harbor.yaml")
    values = read("gitops/harbor/base/harbor-values.yaml")
    pvcs = read("gitops/harbor/base/harbor-pvcs.yaml")
    overlay = read("gitops/harbor/overlays/dev/kustomization.yaml")

    assert "harbor/harbor-core:v2.11.3" in harbor
    assert "harbor/harbor-registry:v2.11.3" in harbor
    assert "harbor/harbor-jobservice:v2.11.3" in harbor
    assert "harbor/harbor-trivy-adapter:v2.11.3" in harbor
    assert "harbor/harbor-chartmuseum:v2.11.3" in harbor
    assert "redis:7.2-alpine" in harbor
    assert "postgres:15-alpine" in harbor
    assert "trivy:" in values and "enabled: true" in values
    assert "clair" in values.lower()
    assert "cosign" in values.lower() or "signature" in values.lower()
    assert "storageClassName: rook-ceph-rbd" in values
    assert "kind: PersistentVolumeClaim" in pvcs
    assert "storageClassName: rook-ceph-rbd" in pvcs
    assert "../../base/harbor.yaml" in overlay
    assert "../../base/harbor-values.yaml" in overlay
    assert "../../base/harbor-pvcs.yaml" in overlay


def test_check_mode() -> None:
    result = run([sys.executable, "scripts/install_harbor_dev.py", "--check"])
    assert result.returncode == 0
    assert "Harbor bootstrap scaffold validation passed." in result.stdout


def test_dry_run_mode() -> None:
    result = run(["./scripts/install-harbor-dev.py", "--offline", "--dry-run"])
    assert result.returncode == 0
    assert f"Harbor version: {HARBOR_VERSION}" in result.stdout
    assert "Rook-Ceph cache: output/rook-ceph/images/rook-ceph-v1.20.3" in result.stdout
    assert "GitOps overlay: gitops/harbor/overlays/dev" in result.stdout


def test_missing_harbor_cache_fails() -> None:
    marker = ROOT / "output" / "harbor" / "images" / f"harbor-core-v{HARBOR_VERSION}"
    if marker.exists():
        marker.unlink()
    try:
        result = subprocess.run(
            ["./scripts/install-harbor-dev.py", "--offline", "--dry-run"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "Harbor offline image cache not found" in result.stderr or result.returncode != 0
    finally:
        marker.write_text(f"Harbor {HARBOR_VERSION} offline image cache marker.\n")


def main() -> int:
    validate_manifests()
    test_check_mode()
    test_dry_run_mode()
    test_missing_harbor_cache_fails()
    print("Harbor bootstrap scaffold validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
