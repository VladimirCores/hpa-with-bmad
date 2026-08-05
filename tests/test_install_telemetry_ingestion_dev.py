#!/usr/bin/env python3
"""Validate HPDC telemetry ingestion GitOps manifests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TELEMETRY_BASE = ROOT / "gitops" / "telemetry-ingestion" / "base" / "telemetry-ingestion.yaml"
TELEMETRY_OVERLAY = ROOT / "gitops" / "telemetry-ingestion" / "overlays" / "dev" / "kustomization.yaml"
ENVOY_GATEWAY = ROOT / "gitops" / "envoy-gateway" / "base" / "envoy-gateway.yaml"
API_KEY_AUTHN = ROOT / "gitops" / "security" / "base" / "api-key-authn.yaml"


def main() -> int:
    failures = []
    for path in [TELEMETRY_BASE, TELEMETRY_OVERLAY, ENVOY_GATEWAY, API_KEY_AUTHN]:
        if not path.is_file():
            failures.append(f"missing file: {path.relative_to(ROOT)}")

    manifest = TELEMETRY_BASE.read_text(encoding="utf-8")
    required = [
        "kind: HTTPRoute",
        "name: hpdc-telemetry-http-ingestion",
        "value: /telemetry",
        "port: 8080",
        "kind: GRPCRoute",
        "name: hpdc-telemetry-grpc-ingestion",
        "value: /hpdc.telemetry.v1.TelemetryService",
        "port: 6669",
        "kind: TCPRoute",
        "name: hpdc-telemetry-mqtt-ingestion",
        "sectionName: mqtt",
        "port: 1884",
        "name: telemetry-ingestion-capacity",
        "default: 5000",
        "sensor: 25000",
        "actuator: 25000",
        "gateway: 10000",
    ]
    for item in required:
        if item not in manifest:
            failures.append(f"telemetry-ingestion.yaml missing {item}")

    if "name: mqtt" not in ENVOY_GATEWAY.read_text(encoding="utf-8"):
        failures.append("envoy-gateway.yaml missing MQTT listener")
    if "value: /telemetry" not in API_KEY_AUTHN.read_text(encoding="utf-8"):
        failures.append("api-key-authn.yaml missing /telemetry API key route")
    if "../../base/telemetry-ingestion.yaml" not in TELEMETRY_OVERLAY.read_text(encoding="utf-8"):
        failures.append("telemetry-ingestion overlay missing base resource")

    if failures:
        print("Telemetry ingestion validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Telemetry ingestion validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
