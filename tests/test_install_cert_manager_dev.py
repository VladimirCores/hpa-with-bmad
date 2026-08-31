#!/usr/bin/env python3
"""Validate cert-manager TLS termination manifests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "gitops"))
import component_versions  # noqa: E402

component_versions.load_all_dotenv()
CERT_MANAGER_VERSION = component_versions.get("HPDC_CERT_MANAGER_VERSION")
REQUIRED = [
    "gitops/cert-manager/base/cert-manager.yaml",
    "gitops/cert-manager/overlays/dev/kustomization.yaml",
    "docs/cert-manager-tls-termination.md",
    "output/implementation-artifacts/3-2-configure-tls-termination-with-cert-manager.md",
    "output/provisioned.yaml",
    "gitops/envoy-gateway/base/envoy-gateway.yaml",
]


def _load_provisioned() -> dict:
    data = yaml.safe_load((ROOT / "output/provisioned.yaml").read_text(encoding="utf-8"))
    return data["provisioned"]


def test_cert_manager_tls_termination() -> None:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    assert not missing, missing
    assert "cert-manager" in _load_provisioned()
    manifest = (ROOT / "gitops/cert-manager/base/cert-manager.yaml").read_text(encoding="utf-8")
    for kind in ["Namespace", "ServiceAccount", "ClusterRole", "ClusterRoleBinding", "Deployment", "Service", "ClusterIssuer", "Certificate"]:
        assert f"kind: {kind}" in manifest, kind
    assert "name: hpdc-edge-tls" in manifest
    assert "hpdc-selfsigned" in manifest
    assert f"quay.io/jetstack/cert-manager-controller:v{CERT_MANAGER_VERSION}" in manifest
    assert f"quay.io/jetstack/cert-manager-webhook:v{CERT_MANAGER_VERSION}" in manifest
    assert f"quay.io/jetstack/cert-manager-cainjector:v{CERT_MANAGER_VERSION}" in manifest
    envoy = (ROOT / "gitops/envoy-gateway/base/envoy-gateway.yaml").read_text(encoding="utf-8")
    assert "name: hpdc-edge-tls" in envoy
    assert "scheme: HTTPS" in envoy


def main() -> int:
    test_cert_manager_tls_termination()
    subprocess.run([sys.executable, "scripts/gitops/install-cert-manager-dev.py", "--offline", "--dry-run"], cwd=ROOT, check=True)
    print("cert-manager TLS termination validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
