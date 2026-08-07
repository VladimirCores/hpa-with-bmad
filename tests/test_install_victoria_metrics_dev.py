#!/usr/bin/env python3
"""Validate HPDC VictoriaMetrics metrics cluster GitOps manifests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VM_BASE = ROOT / "gitops" / "victoria-metrics" / "base" / "victoria-metrics.yaml"
VM_OVERLAY = ROOT / "gitops" / "victoria-metrics" / "overlays" / "dev" / "kustomization.yaml"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def main() -> int:
    failures = []
    for path in [VM_BASE, VM_OVERLAY, PLATFORM_SCAFFOLD]:
        if not path.is_file():
            failures.append(f"missing file: {path.relative_to(ROOT)}")

    manifest = VM_BASE.read_text(encoding="utf-8")
    required = [
        "kind: Namespace",
        "name: victoria-metrics",
        "kind: ObservabilityPipeline",
        "name: platform-observability-pipeline",
        "- vmstorage",
        "- vminsert",
        "- vmselect",
        "retentionPeriod=24h",
        "dev: 24h",
        "staging: 7d",
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
    for item in required:
        if item not in manifest:
            failures.append(f"victoria-metrics.yaml missing {item}")

    if "name: platform-observability-pipeline" not in PLATFORM_SCAFFOLD.read_text(encoding="utf-8"):
        failures.append("platform-scaffold.yaml missing platform-observability-pipeline contract")
    if "../../base/victoria-metrics.yaml" not in VM_OVERLAY.read_text(encoding="utf-8"):
        failures.append("victoria-metrics overlay missing base resource")
    if "namespace: victoria-metrics" not in VM_OVERLAY.read_text(encoding="utf-8"):
        failures.append("victoria-metrics overlay missing namespace")

    if failures:
        print("VictoriaMetrics metrics cluster validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("VictoriaMetrics metrics cluster validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
