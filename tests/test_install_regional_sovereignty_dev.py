#!/usr/bin/env python3
"""Validate HPDC regional data sovereignty."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOV_BASE = ROOT / "gitops" / "regional-sovereignty" / "base" / "regional-sovereignty.yaml"
SOV_OVERLAY = ROOT / "gitops" / "regional-sovereignty" / "overlays" / "dev" / "kustomization.yaml"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"

# Absence-of-config invariant (FR-34): any of these markers would enable cross-region
# data replication. The tree must contain none of them.
CROSS_REGION_REPLICATION_PATTERNS = [
    re.compile(r"ReplicatedMergeTree"),
    re.compile(r"ReplicatedReplacingMergeTree"),
    re.compile(r"_replicator", re.IGNORECASE),
    re.compile(r"mirrormaker", re.IGNORECASE),
    re.compile(r"replication\.factor\s*[:=]"),
    re.compile(r"xcluster", re.IGNORECASE),
    re.compile(r"replicaof\b", re.IGNORECASE),
    re.compile(r"async.?replication", re.IGNORECASE),
]


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

    # FR-34 no-replication guard: assert no cross-region replication config exists in
    # the gitops tree (absence-of-config invariant). Deployment `replicas:` and the
    # sovereignty policy manifest's own "default: disabled" declaration are exempt.
    for path in sorted((ROOT / "gitops").rglob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        for pattern in CROSS_REGION_REPLICATION_PATTERNS:
            if pattern.search(text):
                failures.append(
                    f"{path.relative_to(ROOT)} enables cross-region replication "
                    f"(matched {pattern.pattern!r}); FR-34 requires no default "
                    "cross-region replication config in the tree"
                )

    if failures:
        print("Regional data sovereignty validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Regional data sovereignty validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
