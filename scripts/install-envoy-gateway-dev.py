#!/usr/bin/env python3
"""Install Envoy Gateway edge routing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVOY_MARKER = ROOT / "output" / "envoy-gateway" / "envoy-gateway-workspaces.txt"
ENVOY_BASE = ROOT / "gitops" / "envoy-gateway" / "base"
ENVOY_OVERLAY = ROOT / "gitops" / "envoy-gateway" / "overlays" / "dev"
ROUTE_TABLE = ROOT / "docs" / "envoy-gateway-edge-routing.md"


def ensure_files() -> None:
    if not ENVOY_MARKER.exists():
        raise RuntimeError(f"Envoy Gateway workspace marker not found: {ENVOY_MARKER}")
    if not ROUTE_TABLE.exists():
        raise RuntimeError(f"Envoy Gateway route table documentation missing: {ROUTE_TABLE}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    required = [ENVOY_BASE / "envoy-gateway.yaml", ENVOY_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))

    manifest = (ENVOY_BASE / "envoy-gateway.yaml").read_text(encoding="utf-8")
    required_kinds = ["Namespace", "ServiceAccount", "ClusterRole", "ClusterRoleBinding", "ConfigMap", "Deployment", "EnvoyProxy", "GatewayClass", "Gateway", "HTTPRoute"]
    for kind in required_kinds:
        if f"kind: {kind}" not in manifest:
            failures.append(f"envoy-gateway.yaml missing kind {kind}")

    required_routes = [
        "value: /data",
        "value: /api",
        "value: /gql",
        "value: /events",
        "value: /telemetry",
    ]
    for route in required_routes:
        if route not in manifest:
            failures.append(f"envoy-gateway.yaml missing route {route}")

    if "image: docker.io/envoyproxy/gateway:v1.8.3" not in manifest:
        failures.append("envoy-gateway.yaml missing pinned Envoy Gateway image")

    if "controllerName: gateway.envoyproxy.io/gatewayclass-controller" not in manifest:
        failures.append("envoy-gateway.yaml missing Envoy Gateway GatewayClass controller")

    if "hostname: \"*.hpdc.local\"" not in manifest:
        failures.append("envoy-gateway.yaml missing hpdc.local hostname")

    if "name: mqtt" not in manifest:
        failures.append("envoy-gateway.yaml missing MQTT listener")
    if "port: 1884" not in manifest:
        failures.append("envoy-gateway.yaml missing MQTT listener port 1884")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Envoy Gateway edge routing")
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
        print("Envoy Gateway validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Envoy Gateway apply requested.")
        print(f"GitOps overlay: {ENVOY_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("Envoy Gateway dry-run passed.")
        print("Envoy Gateway, GatewayClass, Gateway, and HTTPRoute route table are configured.")
        print(f"GitOps overlay: {ENVOY_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Envoy Gateway requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
