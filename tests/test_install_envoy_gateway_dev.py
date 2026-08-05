#!/usr/bin/env python3
"""Validate Envoy Gateway edge routing manifests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "gitops/envoy-gateway/base/envoy-gateway.yaml",
    "gitops/envoy-gateway/overlays/dev/kustomization.yaml",
    "docs/envoy-gateway-edge-routing.md",
    "output/implementation-artifacts/3-1-install-envoy-gateway-edge-routing.md",
    "output/envoy-gateway/envoy-gateway-workspaces.txt",
]


def validate() -> None:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    assert not missing, missing
    manifest = (ROOT / "gitops/envoy-gateway/base/envoy-gateway.yaml").read_text(encoding="utf-8")
    for route in ["/data", "/api", "/gql", "/events", "/telemetry"]:
        assert f"value: {route}" in manifest, route
    assert "kind: GatewayClass" in manifest
    assert "kind: Gateway" in manifest
    assert "kind: HTTPRoute" in manifest
    assert "name: mqtt" in manifest
    assert "port: 1884" in manifest
    assert "name: pulsar-telemetry-ingestion" in manifest
    assert "port: 8080" in manifest
    assert "../../../telemetry-ingestion/base" in (ROOT / "gitops/envoy-gateway/overlays/dev/kustomization.yaml").read_text(encoding="utf-8")


def test_install_envoy_gateway_dev() -> None:
    validate()


def main() -> int:
    validate()
    subprocess.run([sys.executable, "scripts/install-envoy-gateway-dev.py", "--offline", "--dry-run"], cwd=ROOT, check=True)
    print("Envoy Gateway edge routing validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
