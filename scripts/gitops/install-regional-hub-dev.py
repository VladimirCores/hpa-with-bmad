#!/usr/bin/env python3
"""Install HPDC regional API hub for cross-region visibility."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HUB_BASE = ROOT / "gitops" / "regional-hub" / "base"
HUB_OVERLAY = ROOT / "gitops" / "regional-hub" / "overlays" / "dev"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def ensure_files() -> None:
    for path in [HUB_BASE / "regional-hub.yaml", HUB_OVERLAY / "kustomization.yaml", PLATFORM_SCAFFOLD]:
        if not path.exists():
            raise RuntimeError(f"required file missing: {path.relative_to(ROOT)}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    manifest = (HUB_BASE / "regional-hub.yaml").read_text(encoding="utf-8")
    overlay = (HUB_OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")

    required_kinds = [
        "kind: Namespace",
        "name: regional-hub",
        "kind: RegionalApiHub",
        "name: regional-apis",
        "stores_regional_data: false",
        "per_region_drilldown: true",
        "region_scoped: true",
        "aggregate_metrics: true",
        "region-1",
        "region-2",
        "kind: ConfigMap",
        "name: regional-api-config",
        "https://region-1.api.hpdc.local",
        "https://region-2.api.hpdc.local",
        "region_scoped_token",
        "kind: Deployment",
        "name: regional-hub-spa",
        "name: hub-visibility-config",
        "store_regional_data: false",
        "query_regional_apis: true",
        "kind: Service",
    ]
    for item in required_kinds:
        if item not in manifest:
            failures.append(f"regional-hub.yaml missing {item}")

    scaffold = PLATFORM_SCAFFOLD.read_text(encoding="utf-8")
    if "name: regional-apis" not in scaffold:
        failures.append("platform-scaffold.yaml missing regional-apis contract")
    if "stores_regional_data: false" not in scaffold:
        failures.append("platform-scaffold.yaml missing stores_regional_data: false")

    if "../../base/regional-hub.yaml" not in overlay:
        failures.append("regional-hub overlay missing base resource")
    if "namespace: regional-hub" not in overlay:
        failures.append("regional-hub overlay missing namespace")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC regional API hub for cross-region visibility")
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
        print("Regional API hub validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Regional API hub apply requested.")
        print(f"GitOps overlay: {HUB_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("Regional API hub dry-run passed.")
        print("The central hub queries regional APIs with region-scoped authentication.")
        print("Aggregated metrics are displayed across regions with per-region drill-down.")
        print("Regional data is never stored at the hub.")
        print(f"GitOps overlay: {HUB_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Regional API hub requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
