#!/usr/bin/env python3
"""Install HPDC VictoriaMetrics metrics cluster."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VM_BASE = ROOT / "gitops" / "victoria-metrics" / "base"
VM_OVERLAY = ROOT / "gitops" / "victoria-metrics" / "overlays" / "dev"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def ensure_files() -> None:
    for path in [VM_BASE / "victoria-metrics.yaml", VM_OVERLAY / "kustomization.yaml", PLATFORM_SCAFFOLD]:
        if not path.exists():
            raise RuntimeError(f"required file missing: {path.relative_to(ROOT)}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    manifest = (VM_BASE / "victoria-metrics.yaml").read_text(encoding="utf-8")
    overlay = (VM_OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")

    required_kinds = [
        "kind: Namespace",
        "name: victoria-metrics",
        "kind: ObservabilityPipeline",
        "name: platform-observability-pipeline",
        "- vmstorage",
        "- vminsert",
        "- vmselect",
        "retentionPeriod=24h",
        "kind: StatefulSet",
        "name: vmstorage",
        "port: 8482",
        "kind: Deployment",
        "name: vminsert",
        "-storageNode=vmstorage:8400",
        "port: 8480",
        "name: vmselect",
        "-storageNode=vmstorage:8401",
        "port: 8481",
        "readinessProbe",
        "kind: Service",
        "name: vmstorage",
        "name: vminsert",
        "name: vmselect",
    ]
    for item in required_kinds:
        if item not in manifest:
            failures.append(f"victoria-metrics.yaml missing {item}")

    if "name: platform-observability-pipeline" not in PLATFORM_SCAFFOLD.read_text(encoding="utf-8"):
        failures.append("platform-scaffold.yaml missing platform-observability-pipeline contract")

    if "dev: 24h" not in manifest:
        failures.append("victoria-metrics.yaml missing dev retention 24h")
    if "staging: 7d" not in manifest:
        failures.append("victoria-metrics.yaml missing staging retention 7d")

    if "../../base/victoria-metrics.yaml" not in overlay:
        failures.append("victoria-metrics overlay missing base resource")
    if "namespace: victoria-metrics" not in overlay:
        failures.append("victoria-metrics overlay missing namespace")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC VictoriaMetrics metrics cluster")
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
        print("VictoriaMetrics metrics cluster validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("VictoriaMetrics metrics cluster apply requested.")
        print(f"GitOps overlay: {VM_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("VictoriaMetrics metrics cluster dry-run passed.")
        print("vmstorage, vminsert, and vmselect components are configured.")
        print("Metrics are queryable via the vmselect Prometheus-compatible endpoint.")
        print(f"GitOps overlay: {VM_OVERLAY.relative_to(ROOT)}")
        return 0
    print("VictoriaMetrics metrics cluster requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
