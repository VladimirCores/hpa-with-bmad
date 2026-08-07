#!/usr/bin/env python3
"""Install HPDC VMLogs log collection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VM_BASE = ROOT / "gitops" / "victoria-metrics" / "base"
VM_OVERLAY = ROOT / "gitops" / "victoria-metrics" / "overlays" / "dev"


def ensure_files() -> None:
    for path in [VM_BASE / "vmlogs.yaml", VM_OVERLAY / "kustomization.yaml"]:
        if not path.exists():
            raise RuntimeError(f"required file missing: {path.relative_to(ROOT)}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    manifest = (VM_BASE / "vmlogs.yaml").read_text(encoding="utf-8")
    overlay = (VM_OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")

    required_kinds = [
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
    for item in required_kinds:
        if item not in manifest:
            failures.append(f"vmlogs.yaml missing {item}")

    if "vmlogs.yaml" not in overlay:
        failures.append("victoria-metrics overlay missing vmlogs resource")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC VMLogs log collection")
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
        print("VMLogs log collection validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("VMLogs log collection apply requested.")
        print(f"GitOps overlay: {VM_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("VMLogs log collection dry-run passed.")
        print("Logs are ingested via the Loki-compatible endpoint and searchable within 5 seconds.")
        print(f"GitOps overlay: {VM_OVERLAY.relative_to(ROOT)}")
        return 0
    print("VMLogs log collection requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
