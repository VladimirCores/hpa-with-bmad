#!/usr/bin/env python3
"""Validate the HPDC Harbor offline registry installer scaffold."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HARBOR_VERSION = "2.15.2"
HARBOR_CHART_VERSION = "1.19.2"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def validate_manifests() -> None:
    harbor = read("gitops/harbor/base/harbor.yaml")
    values = read("gitops/harbor/base/harbor-values.yaml")
    pvcs = read("gitops/harbor/base/harbor-pvcs.yaml")
    overlay = read("gitops/harbor/overlays/dev/kustomization.yaml")

    assert f"goharbor/harbor-core:v{HARBOR_VERSION}" in harbor
    assert f"goharbor/registry-photon:v{HARBOR_VERSION}" in harbor
    assert f"goharbor/harbor-jobservice:v{HARBOR_VERSION}" in harbor
    assert f"goharbor/trivy-adapter-photon:v{HARBOR_VERSION}" in harbor
    # ChartMuseum was removed upstream in Harbor 2.x recent releases
    assert "chartmuseum" not in harbor.lower() or "enabled: false" not in harbor
    assert "redis:7.4-alpine" in harbor
    assert "postgres:15.19-alpine" in harbor
    assert "trivy:" in values and "enabled: true" in values
    assert "clair" in values.lower()
    assert "cosign" in values.lower() or "signature" in values.lower()
    assert "local-path" in values
    assert "kind: PersistentVolumeClaim" in pvcs
    assert "storageClassName: local-path" in pvcs
    assert "../../base/harbor.yaml" in overlay
    assert "../../base/harbor-values.yaml" not in overlay
    assert "kind: ConfigMap" in harbor and "name: harbor-values" in harbor and "harbor-values.yaml: |" in harbor
    assert "../../base/harbor-pvcs.yaml" in overlay

    embed = next(
        (
            d
            for d in yaml.safe_load_all(harbor)
            if isinstance(d, dict)
            and d.get("kind") == "ConfigMap"
            and d.get("metadata", {}).get("name") == "harbor-values"
        ),
        None,
    )
    assert embed is not None, "harbor-values ConfigMap missing from harbor.yaml"
    assert yaml.safe_load(embed["data"]["harbor-values.yaml"]) == yaml.safe_load(values), (
        "harbor-values ConfigMap embed must match gitops/harbor/base/harbor-values.yaml (single source of truth)"
    )

    installer = read("scripts/gitops/install_harbor_dev.py")
    assert f'HARBOR_CHART_VERSION = "{HARBOR_CHART_VERSION}"' in installer
    assert 'persistence.persistentVolumeClaim.registry.storageClass' in installer


def test_check_mode() -> None:
    result = run([sys.executable, "scripts/startup.dev.py", "--offline", "--check", "--step", "06-install-harbor-dev.py"])
    assert result.returncode == 0
    log = (ROOT / "output" / "startup.dev.log").read_text(encoding="utf-8")
    assert "Harbor bootstrap scaffold validation passed." in log


def test_dry_run_mode() -> None:
    result = run([sys.executable, "scripts/startup.dev.py", "--offline", "--dry-run", "--step", "06-install-harbor-dev.py"])
    assert result.returncode == 0
    log = (ROOT / "output" / "startup.dev.log").read_text(encoding="utf-8")
    assert f"Harbor version: {HARBOR_VERSION}" in log
    assert "Rook-Ceph cache: output/rook-ceph/images/rook-ceph-v1.20.6" in log
    assert "GitOps overlay: gitops/harbor/overlays/dev" in log


def test_missing_harbor_cache_fails() -> None:
    marker = ROOT / "output" / "harbor" / "images" / f"harbor-core-v{HARBOR_VERSION}"
    if marker.exists():
        marker.unlink()
    try:
        result = subprocess.run(
            [sys.executable, "scripts/startup.dev.py", "--offline", "--dry-run", "--step", "06-install-harbor-dev.py"],
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
