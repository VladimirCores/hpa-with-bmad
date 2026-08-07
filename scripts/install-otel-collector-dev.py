#!/usr/bin/env python3
"""Install HPDC OpenTelemetry Collector for distributed traces."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VM_BASE = ROOT / "gitops" / "victoria-metrics" / "base"
VM_OVERLAY = ROOT / "gitops" / "victoria-metrics" / "overlays" / "dev"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def ensure_files() -> None:
    for path in [VM_BASE / "otel-collector.yaml", VM_OVERLAY / "kustomization.yaml", PLATFORM_SCAFFOLD]:
        if not path.exists():
            raise RuntimeError(f"required file missing: {path.relative_to(ROOT)}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    manifest = (VM_BASE / "otel-collector.yaml").read_text(encoding="utf-8")
    overlay = (VM_OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")

    required_kinds = [
        "kind: ConfigMap",
        "name: otel-collector-config",
        "receivers:",
        "otlp:",
        "protocols:",
        "grpc:",
        "http:",
        "endpoint: 0.0.0.0:4317",
        "endpoint: 0.0.0.0:4318",
        "processors:",
        "probabilistic_sampler:",
        "sampling_percentage: 25",
        "exporters:",
        "endpoint: vminsert:8480",
        "pipelines:",
        "traces:",
        "kind: ConfigMap",
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
    for item in required_kinds:
        if item not in manifest:
            failures.append(f"otel-collector.yaml missing {item}")

    if "opentelemetry_collector: true" not in PLATFORM_SCAFFOLD.read_text(encoding="utf-8"):
        failures.append("platform-scaffold.yaml missing opentelemetry_collector contract")

    if "otel-collector.yaml" not in overlay:
        failures.append("victoria-metrics overlay missing otel-collector resource")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC OpenTelemetry Collector for distributed traces")
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
        print("OpenTelemetry Collector validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("OpenTelemetry Collector apply requested.")
        print(f"GitOps overlay: {VM_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("OpenTelemetry Collector dry-run passed.")
        print("OTLP traces are accepted on ports 4317/4318 and exported to VictoriaMetrics.")
        print("Trace sampling is configurable per service.")
        print(f"GitOps overlay: {VM_OVERLAY.relative_to(ROOT)}")
        return 0
    print("OpenTelemetry Collector requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
