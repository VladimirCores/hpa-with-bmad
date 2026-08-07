#!/usr/bin/env python3
"""Validate HPDC entity hierarchy store GitOps manifests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTITY_BASE = ROOT / "gitops" / "entity-store" / "base" / "entity-store.yaml"
ENTITY_OVERLAY = ROOT / "gitops" / "entity-store" / "overlays" / "dev" / "kustomization.yaml"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def main() -> int:
    failures = []
    for path in [ENTITY_BASE, ENTITY_OVERLAY, PLATFORM_SCAFFOLD]:
        if not path.is_file():
            failures.append(f"missing file: {path.relative_to(ROOT)}")

    manifest = ENTITY_BASE.read_text(encoding="utf-8")
    required = [
        "kind: Namespace",
        "name: entity-store",
        "kind: StorageClass",
        "name: hpdc-entity-ceph",
        "provisioner: rook-ceph.rbd.csi.ceph.com",
        "kind: EntityStore",
        "name: entity-hierarchy-store",
        "couchdb",
        "document_hierarchy: true",
        "arcadedb",
        "graph_lineage: true",
        "yugabytedb",
        "internal_transactional_state: true",
        "ceph_backed: true",
        "name: couchdb-entity-store",
        "change_feed: /entity_hierarchy/_changes?feed=continuous&include_docs=true",
        "port: 5984",
        "name: arcadedb-entity-store",
        "shortest_path",
        "neighbor_discovery",
        "port: 2480",
        "name: yugabytedb-entity-store",
        "sql_interface: enabled",
        "port: 5433",
        "storageClassName: hpdc-entity-ceph",
    ]
    for item in required:
        if item not in manifest:
            failures.append(f"entity-store.yaml missing {item}")

    if "name: entity-hierarchy-store" not in PLATFORM_SCAFFOLD.read_text(encoding="utf-8"):
        failures.append("platform-scaffold.yaml missing entity-hierarchy-store contract")
    if "../../base/entity-store.yaml" not in ENTITY_OVERLAY.read_text(encoding="utf-8"):
        failures.append("entity-store overlay missing base resource")
    if "namespace: entity-store" not in ENTITY_OVERLAY.read_text(encoding="utf-8"):
        failures.append("entity-store overlay missing namespace")

    if failures:
        print("Entity hierarchy store validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Entity hierarchy store validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
