#!/usr/bin/env python3
"""Validate HPDC VMLogs log collection GitOps manifests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VM_BASE = ROOT / "gitops" / "victoria-metrics" / "base" / "vmlogs.yaml"
VM_OVERLAY = ROOT / "gitops" / "victoria-metrics" / "overlays" / "dev" / "kustomization.yaml"


def main() -> int:
    failures = []
    for path in [VM_BASE, VM_OVERLAY]:
        if not path.is_file():
            failures.append(f"missing file: {path.relative_to(ROOT)}")

    manifest = VM_BASE.read_text(encoding="utf-8")
    required = [
        "kind: ConfigMap",
        "name: vmlogs-config",
        "search_within_seconds: 5",
        "indexed_fields:",
        "- namespace",
        "- app",
        "- level",
        "- host",
        "kind: Deployment",
        "name: vmlogs",
        "port: 9428",
        "readinessProbe",
        "kind: Service",
        "name: vmlogs",
    ]
    for item in required:
        if item not in manifest:
            failures.append(f"vmlogs.yaml missing {item}")

    if "vmlogs.yaml" not in VM_OVERLAY.read_text(encoding="utf-8"):
        failures.append("victoria-metrics overlay missing vmlogs resource")

    if failures:
        print("VMLogs log collection validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("VMLogs log collection validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
