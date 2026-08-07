#!/usr/bin/env python3
"""Validate HPDC Cilium ClusterMesh cross-cluster service discovery."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLUSTERMESH_BASE = ROOT / "gitops" / "clustermesh" / "base" / "clustermesh.yaml"
CLUSTERMESH_OVERLAY = ROOT / "gitops" / "clustermesh" / "overlays" / "dev" / "kustomization.yaml"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def main() -> int:
    failures: list[str] = []
    for path in [CLUSTERMESH_BASE, CLUSTERMESH_OVERLAY, PLATFORM_SCAFFOLD]:
        if not path.is_file():
            failures.append(f"missing file: {path.relative_to(ROOT)}")

    manifest = CLUSTERMESH_BASE.read_text(encoding="utf-8")
    required = [
        "kind: Namespace",
        "name: clustermesh",
        "kind: ClusterMesh",
        "name: regional-clustermesh",
        "protocol: WireGuard",
        "cross_cluster: true",
        "manual_per_service_discovery: false",
        "encrypted: true",
        "region-1",
        "region-2",
        "kind: ConfigMap",
        "name: clustermesh-config",
        "type: wireguard",
        "nodeEncryption: true",
        "kind: CiliumClusterWideConfig",
        "name: hpdc-clustermesh",
        "clustermesh:",
        "enable: true",
        "cluster-service-region-1.clustermesh.svc",
        "cluster-service-region-2.clustermesh.svc",
        "port: 2379",
        "kind: Service",
        "name: cluster-service-region-1",
        "name: cluster-service-region-2",
        "io.cilium/cluster: region-1",
        "io.cilium/cluster: region-2",
    ]
    for item in required:
        if item not in manifest:
            failures.append(f"clustermesh.yaml missing {item}")

    scaffold = PLATFORM_SCAFFOLD.read_text(encoding="utf-8")
    for item in ["name: regional-clustermesh", "protocol: WireGuard", "cross_cluster: true"]:
        if item not in scaffold:
            failures.append(f"platform-scaffold.yaml missing {item}")

    overlay = CLUSTERMESH_OVERLAY.read_text(encoding="utf-8")
    for item in ["../../base/clustermesh.yaml", "namespace: clustermesh"]:
        if item not in overlay:
            failures.append(f"clustermesh overlay missing {item}")

    if failures:
        print("ClusterMesh validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("ClusterMesh validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
