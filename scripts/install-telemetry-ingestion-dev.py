#!/usr/bin/env python3
"""Install HPDC telemetry ingestion routes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TELEMETRY_MARKER = ROOT / "output" / "telemetry-ingestion" / "telemetry-ingestion-workspaces.txt"
TELEMETRY_BASE = ROOT / "gitops" / "telemetry-ingestion" / "base"
TELEMETRY_OVERLAY = ROOT / "gitops" / "telemetry-ingestion" / "overlays" / "dev"
ENVOY_GATEWAY = ROOT / "gitops" / "envoy-gateway" / "base" / "envoy-gateway.yaml"
API_KEY_AUTHN = ROOT / "gitops" / "security" / "base" / "api-key-authn.yaml"
ROUTE_TABLE = ROOT / "docs" / "telemetry-ingestion-route.md"


def ensure_files() -> None:
    for path in [TELEMETRY_MARKER, TELEMETRY_BASE / "telemetry-ingestion.yaml", TELEMETRY_OVERLAY / "kustomization.yaml", ENVOY_GATEWAY, API_KEY_AUTHN, ROUTE_TABLE]:
        if not path.exists():
            raise RuntimeError(f"required file missing: {path.relative_to(ROOT)}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    manifest = (TELEMETRY_BASE / "telemetry-ingestion.yaml").read_text(encoding="utf-8")
    envoy = ENVOY_GATEWAY.read_text(encoding="utf-8")
    authn = API_KEY_AUTHN.read_text(encoding="utf-8")
    overlay = (TELEMETRY_OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")

    required_kinds = [
        "kind: Namespace",
        "name: telemetry-ingestion",
        "kind: ServiceAccount",
        "name: pulsar-telemetry-ingestion",
        "kind: ConfigMap",
        "name: telemetry-ingestion-capacity",
        "default: 5000",
        "actuator: 25000",
        "gateway: 10000",
        "sensor: 25000",
        "kind: Service",
        "name: pulsar-telemetry-ingestion",
        "port: 8080",
        "port: 6669",
        "port: 1884",
        "kind: HTTPRoute",
        "name: hpdc-telemetry-http-ingestion",
        "value: /telemetry",
        "name: pulsar-telemetry-ingestion",
        "port: 8080",
        "kind: GRPCRoute",
        "name: hpdc-telemetry-grpc-ingestion",
        "value: /hpdc.telemetry.v1.TelemetryService",
        "port: 6669",
        "kind: TCPRoute",
        "name: hpdc-telemetry-mqtt-ingestion",
        "sectionName: mqtt",
        "port: 1884",
    ]
    for item in required_kinds:
        if item not in manifest:
            failures.append(f"telemetry-ingestion.yaml missing {item}")

    if "name: mqtt" not in envoy:
        failures.append("envoy-gateway.yaml missing MQTT listener")
    if "port: 1884" not in envoy:
        failures.append("envoy-gateway.yaml missing MQTT listener port 1884")
    if "name: hpdc-telemetry-grpc-ingestion" not in authn:
        failures.append("api-key-authn.yaml missing gRPC telemetry SecurityPolicy target")
    if "../../base/telemetry-ingestion.yaml" not in overlay:
        failures.append("telemetry-ingestion overlay missing base resource")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC telemetry ingestion routes")
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
        print("Telemetry ingestion validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Telemetry ingestion apply requested.")
        print(f"GitOps overlay: {TELEMETRY_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("Telemetry ingestion dry-run passed.")
        print("HTTP, gRPC, and MQTT telemetry routes are configured.")
        print("Capacity limits are configured for sensor, actuator, and gateway device types.")
        print(f"GitOps overlay: {TELEMETRY_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Telemetry ingestion requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
