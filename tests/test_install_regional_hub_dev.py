#!/usr/bin/env python3
"""Validate HPDC regional API hub for cross-region visibility."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB_BASE = ROOT / "gitops" / "regional-hub" / "base" / "regional-hub.yaml"
HUB_OVERLAY = ROOT / "gitops" / "regional-hub" / "overlays" / "dev" / "kustomization.yaml"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def main() -> int:
    failures: list[str] = []
    for path in [HUB_BASE, HUB_OVERLAY, PLATFORM_SCAFFOLD]:
        if not path.is_file():
            failures.append(f"missing file: {path.relative_to(ROOT)}")

    manifest = HUB_BASE.read_text(encoding="utf-8")
    required = [
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
    for item in required:
        if item not in manifest:
            failures.append(f"regional-hub.yaml missing {item}")

    scaffold = PLATFORM_SCAFFOLD.read_text(encoding="utf-8")
    for item in ["name: regional-apis", "stores_regional_data: false"]:
        if item not in scaffold:
            failures.append(f"platform-scaffold.yaml missing {item}")

    overlay = HUB_OVERLAY.read_text(encoding="utf-8")
    for item in ["../../base/regional-hub.yaml", "namespace: regional-hub"]:
        if item not in overlay:
            failures.append(f"regional-hub overlay missing {item}")

    if failures:
        print("Regional API hub validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Regional API hub validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
