#!/usr/bin/env python3
"""Install HPDC regional data sovereignty."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOV_BASE = ROOT / "gitops" / "regional-sovereignty" / "base"
SOV_OVERLAY = ROOT / "gitops" / "regional-sovereignty" / "overlays" / "dev"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def ensure_files() -> None:
    for path in [SOV_BASE / "regional-sovereignty.yaml", SOV_OVERLAY / "kustomization.yaml", PLATFORM_SCAFFOLD]:
        if not path.exists():
            raise RuntimeError(f"required file missing: {path.relative_to(ROOT)}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    manifest = (SOV_BASE / "regional-sovereignty.yaml").read_text(encoding="utf-8")
    overlay = (SOV_OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")

    required_kinds = [
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
    for item in required_kinds:
        if item not in manifest:
            failures.append(f"regional-sovereignty.yaml missing {item}")

    scaffold = PLATFORM_SCAFFOLD.read_text(encoding="utf-8")
    if "name: regional-data-sovereignty" not in scaffold:
        failures.append("platform-scaffold.yaml missing regional-data-sovereignty contract")
    if "replication:" not in scaffold:
        failures.append("platform-scaffold.yaml missing replication policy")

    if "../../base/regional-sovereignty.yaml" not in overlay:
        failures.append("regional-sovereignty overlay missing base resource")
    if "namespace: regional-sovereignty" not in overlay:
        failures.append("regional-sovereignty overlay missing namespace")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC regional data sovereignty")
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
        print("Regional data sovereignty validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Regional data sovereignty apply requested.")
        print(f"GitOps overlay: {SOV_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("Regional data sovereignty dry-run passed.")
        print("Each region maintains independent data stores with no automatic cross-region replication.")
        print("Regional queries route to the region-scoped data store.")
        print("Explicit replication configuration is required before cross-region data movement.")
        print(f"GitOps overlay: {SOV_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Regional data sovereignty requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
