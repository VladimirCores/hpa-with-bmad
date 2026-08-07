#!/usr/bin/env python3
"""Validate HPDC regional data sovereignty."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOV_BASE = ROOT / "gitops" / "regional-sovereignty" / "base" / "regional-sovereignty.yaml"
SOV_OVERLAY = ROOT / "gitops" / "regional-sovereignty" / "overlays" / "dev" / "kustomization.yaml"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def main() -> int:
    failures: list[str] = []
    for path in [SOV_BASE, SOV_OVERLAY, PLATFORM_SCAFFOLD]:
        if not path.is_file():
            failures.append(f"missing file: {path.relative_to(ROOT)}")

    manifest = SOV_BASE.read_text(encoding="utf-8")
    required = [
        "kind: Namespace",
        "name: regional-sovereignty",
        "kind: RegionalDataSovereignty",
        "name: regional-data-sovereignty",
        "couchdb: true",
        "yugabytedb: true",
        "clickhouse: true",
        "arcadedb: true",
        "keydb: true",
        "postgresql: true",
        "default: disabled",
        "explicit_configuration_required: true",
        "region-1",
        "region-2",
        "kind: ConfigMap",
        "name: regional-route-config",
        "couchdb.region-1.svc:5984",
        "couchdb.region-2.svc:5984",
        "clickhouse.region-1.svc:8123",
        "yugabytedb.region-2.svc:5433",
        "name: replication-policy-config",
        "default_replication: disabled",
        "require_region_scoped_credentials: true",
    ]
    for item in required:
        if item not in manifest:
            failures.append(f"regional-sovereignty.yaml missing {item}")

    scaffold = PLATFORM_SCAFFOLD.read_text(encoding="utf-8")
    for item in ["name: regional-data-sovereignty", "replication:"]:
        if item not in scaffold:
            failures.append(f"platform-scaffold.yaml missing {item}")

    overlay = SOV_OVERLAY.read_text(encoding="utf-8")
    for item in ["../../base/regional-sovereignty.yaml", "namespace: regional-sovereignty"]:
        if item not in overlay:
            failures.append(f"regional-sovereignty overlay missing {item}")

    if failures:
        print("Regional data sovereignty validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Regional data sovereignty validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
