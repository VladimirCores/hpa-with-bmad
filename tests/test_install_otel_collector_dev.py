#!/usr/bin/env python3
"""Validate HPDC OpenTelemetry Collector GitOps manifests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VM_BASE = ROOT / "gitops" / "victoria-metrics" / "base" / "otel-collector.yaml"
VM_OVERLAY = ROOT / "gitops" / "victoria-metrics" / "overlays" / "dev" / "kustomization.yaml"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def main() -> int:
    failures = []
    for path in [VM_BASE, VM_OVERLAY, PLATFORM_SCAFFOLD]:
        if not path.is_file():
            failures.append(f"missing file: {path.relative_to(ROOT)}")

    manifest = VM_BASE.read_text(encoding="utf-8")
    required = [
        "kind: ConfigMap",
        "name: otel-collector-config",
        "otlp:",
        "endpoint: 0.0.0.0:4317",
        "endpoint: 0.0.0.0:4318",
        "probabilistic_sampler:",
        "sampling_percentage: 25",
        "endpoint: vminsert:8480",
        "name: otel-sampling-config",
        "default: 25",
        "entity-api: 100",
        "graphql-gateway: 50",
        "kind: Deployment",
        "name: otel-collector",
        "port: 4317",
        "port: 4318",
        "kind: Service",
        "name: otel-collector",
    ]
    for item in required:
        if item not in manifest:
            failures.append(f"otel-collector.yaml missing {item}")

    if "opentelemetry_collector: true" not in PLATFORM_SCAFFOLD.read_text(encoding="utf-8"):
        failures.append("platform-scaffold.yaml missing opentelemetry_collector contract")
    if "otel-collector.yaml" not in VM_OVERLAY.read_text(encoding="utf-8"):
        failures.append("victoria-metrics overlay missing otel-collector resource")

    if failures:
        print("OpenTelemetry Collector validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("OpenTelemetry Collector validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
