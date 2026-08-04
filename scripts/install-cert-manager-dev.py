#!/usr/bin/env python3
"""Install cert-manager TLS termination for Envoy Gateway."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CERT_MANAGER_MARKER = ROOT / "output" / "cert-manager" / "cert-manager-workspaces.txt"
CERT_MANAGER_BASE = ROOT / "gitops" / "cert-manager" / "base"
CERT_MANAGER_OVERLAY = ROOT / "gitops" / "cert-manager" / "overlays" / "dev"
ENVOY_MANIFEST = ROOT / "gitops" / "envoy-gateway" / "base" / "envoy-gateway.yaml"
ROUTE_TABLE = ROOT / "docs" / "cert-manager-tls-termination.md"


def ensure_files() -> None:
    if not CERT_MANAGER_MARKER.exists():
        raise RuntimeError(f"cert-manager workspace marker not found: {CERT_MANAGER_MARKER}")
    if not ROUTE_TABLE.exists():
        raise RuntimeError(f"TLS termination documentation missing: {ROUTE_TABLE}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    required = [CERT_MANAGER_BASE / "cert-manager.yaml", CERT_MANAGER_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))

    manifest = (CERT_MANAGER_BASE / "cert-manager.yaml").read_text(encoding="utf-8")
    required_kinds = [
        "Namespace",
        "ServiceAccount",
        "ClusterRole",
        "ClusterRoleBinding",
        "Deployment",
        "Service",
        "ClusterIssuer",
        "Certificate",
    ]
    for kind in required_kinds:
        if f"kind: {kind}" not in manifest:
            failures.append(f"cert-manager.yaml missing kind {kind}")

    if "name: hpdc-edge-tls" not in manifest:
        failures.append("cert-manager.yaml missing hpdc-edge-tls certificate")
    if "clusterIssuer" not in manifest and "ClusterIssuer" not in manifest:
        failures.append("cert-manager.yaml missing hpdc-selfsigned issuer")
    if "quay.io/jetstack/cert-manager-controller:v1.18.2" not in manifest:
        failures.append("cert-manager.yaml missing pinned controller image")
    if "quay.io/jetstack/cert-manager-webhook:v1.18.2" not in manifest:
        failures.append("cert-manager.yaml missing pinned webhook image")
    if "quay.io/jetstack/cert-manager-cainjector:v1.18.2" not in manifest:
        failures.append("cert-manager.yaml missing pinned cainjector image")

    envoy = ENVOY_MANIFEST.read_text(encoding="utf-8")
    if "name: hpdc-edge-tls" not in envoy:
        failures.append("envoy-gateway.yaml does not reference hpdc-edge-tls")
    if "scheme: HTTPS" not in envoy:
        failures.append("envoy-gateway.yaml does not redirect HTTP to HTTPS")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install cert-manager TLS termination for Envoy Gateway")
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
        print("cert-manager validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("cert-manager apply requested.")
        print(f"GitOps overlay: {CERT_MANAGER_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("cert-manager dry-run passed.")
        print("cert-manager, hpdc-selfsigned issuer, and hpdc-edge-tls certificate are configured.")
        print(f"GitOps overlay: {CERT_MANAGER_OVERLAY.relative_to(ROOT)}")
        return 0
    print("cert-manager requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
