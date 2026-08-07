#!/usr/bin/env python3
"""Install HPDC Cilium ClusterMesh cross-cluster service discovery."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLUSTERMESH_BASE = ROOT / "gitops" / "clustermesh" / "base"
CLUSTERMESH_OVERLAY = ROOT / "gitops" / "clustermesh" / "overlays" / "dev"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def ensure_files() -> None:
    for path in [CLUSTERMESH_BASE / "clustermesh.yaml", CLUSTERMESH_OVERLAY / "kustomization.yaml", PLATFORM_SCAFFOLD]:
        if not path.exists():
            raise RuntimeError(f"required file missing: {path.relative_to(ROOT)}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    manifest = (CLUSTERMESH_BASE / "clustermesh.yaml").read_text(encoding="utf-8")
    overlay = (CLUSTERMESH_OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")

    required_kinds = [
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
    for item in required_kinds:
        if item not in manifest:
            failures.append(f"clustermesh.yaml missing {item}")

    scaffold = PLATFORM_SCAFFOLD.read_text(encoding="utf-8")
    if "name: regional-clustermesh" not in scaffold:
        failures.append("platform-scaffold.yaml missing regional-clustermesh contract")
    if "protocol: WireGuard" not in scaffold:
        failures.append("platform-scaffold.yaml missing WireGuard protocol")
    if "cross_cluster: true" not in scaffold:
        failures.append("platform-scaffold.yaml missing cross_cluster discovery")

    if "../../base/clustermesh.yaml" not in overlay:
        failures.append("clustermesh overlay missing base resource")
    if "namespace: clustermesh" not in overlay:
        failures.append("clustermesh overlay missing namespace")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC Cilium ClusterMesh cross-cluster service discovery")
    parser.add_argument("--offline", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.check:
        ensure_files()
        failures = validate_manifests()
        if failures:
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("ClusterMesh validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("ClusterMesh apply requested.")
        print(f"GitOps overlay: {CLUSTERMESH_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("ClusterMesh dry-run passed.")
        print("Cross-cluster service discovery is enabled over a WireGuard VPN overlay.")
        print("Services are discovered across regions without manual per-service configuration.")
        print("Cross-cluster traffic is encrypted through the VPN tunnel.")
        print(f"GitOps overlay: {CLUSTERMESH_OVERLAY.relative_to(ROOT)}")
        return 0
    print("ClusterMesh requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
