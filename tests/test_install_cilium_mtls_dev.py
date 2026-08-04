#!/usr/bin/env python3
"""Validate the HPDC Cilium mTLS offline installer scaffold."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CILIUM_VERSION = "1.19.6"
SPIRE_VERSION = "1.9.6"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def validate_manifests() -> None:
    cilium = read("gitops/cilium/base/cilium-mtls.yaml")
    test = read("gitops/cilium/base/cilium-mtls-test.yaml")
    overlay = read("gitops/cilium/overlays/mesh/kustomization.yaml")

    assert "kind: Cilium" in cilium
    assert "authentication:" in cilium and "enabled: true" in cilium
    assert "mutual:" in cilium and "enabled: true" in cilium
    assert "spire:" in cilium and "enabled: true" in cilium
    assert "serverAddress: spire-server.cilium-spire.svc:8081" in cilium
    assert "agentSocketPath: /run/spire/sockets/agent/agent.sock" in cilium
    assert "kind: StatefulSet" in cilium and "name: spire-server" in cilium
    assert "kind: DaemonSet" in cilium and "name: spire-agent" in cilium
    assert f"ghcr.io/spiffe/spire-server:v{SPIRE_VERSION}" in cilium
    assert f"ghcr.io/spiffe/spire-agent:v{SPIRE_VERSION}" in cilium
    assert "storageClassName: rook-ceph-rbd" in cilium
    assert "mtls-server" in test and "mtls-client" in test
    assert "curl -fsS http://mtls-server.hpdc-mtls-test.svc.cluster.local/" in test
    assert "../../base/cilium-mtls.yaml" in overlay
    assert "../../base/cilium-mtls-test.yaml" in overlay


def test_check_mode() -> None:
    result = run([sys.executable, "startup.dev.py", "--offline", "--check", "--step", "04-install-cilium-mtls-dev.py"])
    assert result.returncode == 0
    log = (ROOT / "output" / "startup.dev.log").read_text(encoding="utf-8")
    assert "Cilium mTLS bootstrap scaffold validation passed." in log


def test_dry_run_mode() -> None:
    result = run([sys.executable, "startup.dev.py", "--offline", "--dry-run", "--step", "04-install-cilium-mtls-dev.py"])
    assert result.returncode == 0
    log = (ROOT / "output" / "startup.dev.log").read_text(encoding="utf-8")
    assert f"Cilium version: {CILIUM_VERSION}" in log
    assert f"SPIRE version: {SPIRE_VERSION}" in log
    assert "Rook-Ceph cache: output/rook-ceph/images/rook-ceph-v1.20.3" in log
    assert "GitOps overlay: gitops/cilium/overlays/mesh" in log


def test_missing_spire_cache_fails() -> None:
    marker = ROOT / "output" / "cilium" / "images" / f"spire-agent-v{SPIRE_VERSION}"
    if marker.exists():
        marker.unlink()
    try:
        result = subprocess.run(
            [sys.executable, "startup.dev.py", "--offline", "--dry-run", "--step", "04-install-cilium-mtls-dev.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "Cilium mTLS offline image cache not found" in result.stderr or result.returncode != 0
    finally:
        marker.write_text(f"SPIRE agent {SPIRE_VERSION} offline image cache marker.\n")


def main() -> int:
    validate_manifests()
    test_check_mode()
    test_dry_run_mode()
    test_missing_spire_cache_fails()
    print("Cilium mTLS bootstrap scaffold validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
