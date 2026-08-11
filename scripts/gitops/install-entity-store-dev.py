#!/usr/bin/env python3
"""Install HPDC entity hierarchy stores (CouchDB, ArcadeDB, YugabyteDB)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENTITY_BASE = ROOT / "gitops" / "entity-store" / "base"
ENTITY_OVERLAY = ROOT / "gitops" / "entity-store" / "overlays" / "dev"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"
STORAGE_CLASS = "hpdc-entity-ceph"


def ensure_files() -> None:
    for path in [ENTITY_BASE / "entity-store.yaml", ENTITY_OVERLAY / "kustomization.yaml", PLATFORM_SCAFFOLD]:
        if not path.exists():
            raise RuntimeError(f"required file missing: {path.relative_to(ROOT)}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    manifest = (ENTITY_BASE / "entity-store.yaml").read_text(encoding="utf-8")
    overlay = (ENTITY_OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")

    required_kinds = [
        "kind: Namespace",
        "name: entity-store",
        "kind: StorageClass",
        "name: hpdc-entity-ceph",
        "provisioner: rook-ceph.rbd.csi.ceph.com",
        "reclaimPolicy: Retain",
        "kind: EntityStore",
        "name: entity-hierarchy-store",
        "couchdb",
        "document_hierarchy: true",
        "arcadedb",
        "graph_lineage: true",
        "yugabytedb",
        "internal_transactional_state: true",
        "ceph_backed: true",
        "kind: ConfigMap",
        "name: couchdb-entity-store",
        "name: arcadedb-entity-store",
        "name: yugabytedb-entity-store",
        "change_feed: /entity_hierarchy/_changes?feed=continuous&include_docs=true",
        "shortest_path",
        "neighbor_discovery",
        "traversal_latency_budget_ms: 100",
        "sql_interface: enabled",
        "kind: Service",
        "name: couchdb-entity-store",
        "port: 5984",
        "name: arcadedb-entity-store",
        "port: 2480",
        "name: yugabytedb-entity-store",
        "port: 5433",
        "kind: PersistentVolumeClaim",
        "storageClassName: hpdc-entity-ceph",
    ]
    for item in required_kinds:
        if item not in manifest:
            failures.append(f"entity-store.yaml missing {item}")

    if f"storage_class: {STORAGE_CLASS}" not in manifest:
        failures.append("entity-store.yaml missing Ceph storage class binding")

    if "name: entity-hierarchy-store" not in PLATFORM_SCAFFOLD.read_text(encoding="utf-8"):
        failures.append("platform-scaffold.yaml missing entity-hierarchy-store contract")

    if "../../base/entity-store.yaml" not in overlay:
        failures.append("entity-store overlay missing base resource")
    if "namespace: entity-store" not in overlay:
        failures.append("entity-store overlay missing namespace")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC entity hierarchy stores")
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
        print("Entity hierarchy store validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Entity hierarchy store apply requested.")
        print(f"GitOps overlay: {ENTITY_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("Entity hierarchy store dry-run passed.")
        print("CouchDB document hierarchy, ArcadeDB graph lineage, and YugabyteDB relational stores are configured.")
        print("All stores persist to Ceph RBD volumes via the hpdc-entity-ceph StorageClass.")
        print(f"GitOps overlay: {ENTITY_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Entity hierarchy store requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
