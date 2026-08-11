#!/usr/bin/env python3
"""Provide entity CRUD and bulk operations with RBAC and mutation audit.

This script supports create, read, update, delete, and bulk operations for
entity types (company, client, device, asset), enforces role-based access
control, and records every mutation with actor, timestamp, and change diff
in an immutable mutation log.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[2]
CRUD_DEF = ROOT / "gitops" / "entity-store" / "base" / "entity-crud.yaml"
DATA_DIR = Path(os.environ.get("HPDC_ENTITY_DATA_DIR", ROOT / "output" / "entity-store"))
ENTITIES_DIR = DATA_DIR / "entities"
MUTATION_LOG = DATA_DIR / "mutations.ndjson"


def load_crud() -> dict[str, Any]:
    if not CRUD_DEF.exists():
        raise RuntimeError(f"CRUD definition not found: {CRUD_DEF}")
    for doc in yaml.safe_load_all(CRUD_DEF.read_text(encoding="utf-8")):
        if doc and doc.get("kind") == "EntityCrud":
            return doc.get("spec", {})
    raise RuntimeError(f"EntityCrud definition not found: {CRUD_DEF}")


def validate_entity_type(crud_spec: dict[str, Any], entity_type: str) -> None:
    if entity_type not in crud_spec.get("entity_types", []):
        raise ValueError(f"unknown entity type: {entity_type}")


def get_actor_role(crud_spec: dict[str, Any], actor: str) -> str | None:
    return crud_spec.get("users", {}).get(actor)


def is_authorized(crud_spec: dict[str, Any], operation: str, actor: str) -> bool:
    role = get_actor_role(crud_spec, actor)
    if role is None:
        return False
    return role in crud_spec.get("operations", {}).get(operation, {}).get("roles", [])


def record_mutation(entry: dict[str, Any]) -> None:
    MUTATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with MUTATION_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def entity_path(entity_type: str, entity_id: str) -> Path:
    return ENTITIES_DIR / entity_type / f"{entity_id}.json"


def read_entity(entity_type: str, entity_id: str) -> dict[str, Any] | None:
    path = entity_path(entity_type, entity_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_entity(entity_type: str, entity_id: str, data: dict[str, Any]) -> None:
    path = entity_path(entity_type, entity_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def compute_change_diff(before: dict[str, Any] | None, after: dict[str, Any]) -> dict[str, Any]:
    before = before or {}
    diff: dict[str, Any] = {}
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            diff[key] = {"from": before.get(key), "to": after.get(key)}
    return diff


def log_mutation(crud_spec: dict[str, Any], operation: str, entity_type: str,
                 entity_id: str, actor: str, change_diff: dict[str, Any],
                 result: str, error: str | None = None, latency_ms: int = 0) -> None:
    record_mutation({
        "entity_type": entity_type,
        "entity_id": entity_id,
        "operation": operation,
        "actor": actor,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "change_diff": change_diff,
        "result": result,
        "error": error,
        "latency_ms": latency_ms,
        "correlation_id": str(uuid.uuid4()),
    })


def create_entity(args: argparse.Namespace) -> int:
    crud_spec = load_crud()
    try:
        validate_entity_type(crud_spec, args.entity_type)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 400

    if not is_authorized(crud_spec, "create", args.actor):
        log_mutation(crud_spec, "create", args.entity_type, args.entity_id, args.actor, {}, "unauthorized")
        print(f"Unauthorized: actor {args.actor} cannot create", file=sys.stderr)
        return 403

    start = time.monotonic()
    data = json.loads(args.data)
    data["entity_type"] = args.entity_type
    data["entity_id"] = args.entity_id
    save_entity(args.entity_type, args.entity_id, data)
    latency_ms = int((time.monotonic() - start) * 1000)
    log_mutation(crud_spec, "create", args.entity_type, args.entity_id, args.actor,
                 compute_change_diff(None, data), "success", latency_ms=latency_ms)
    print(f"OK: created {args.entity_type}/{args.entity_id} by {args.actor}")
    return 0


def read_command(args: argparse.Namespace) -> int:
    crud_spec = load_crud()
    try:
        validate_entity_type(crud_spec, args.entity_type)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 400

    if not is_authorized(crud_spec, "read", args.actor):
        log_mutation(crud_spec, "read", args.entity_type, args.entity_id, args.actor, {}, "unauthorized")
        print(f"Unauthorized: actor {args.actor} cannot read", file=sys.stderr)
        return 403

    entity = read_entity(args.entity_type, args.entity_id)
    if entity is None:
        print(f"Not found: {args.entity_type}/{args.entity_id}", file=sys.stderr)
        return 404
    print(json.dumps(entity))
    return 0


def update_entity(args: argparse.Namespace) -> int:
    crud_spec = load_crud()
    try:
        validate_entity_type(crud_spec, args.entity_type)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 400

    if not is_authorized(crud_spec, "update", args.actor):
        log_mutation(crud_spec, "update", args.entity_type, args.entity_id, args.actor, {}, "unauthorized")
        print(f"Unauthorized: actor {args.actor} cannot update", file=sys.stderr)
        return 403

    before = read_entity(args.entity_type, args.entity_id)
    if before is None:
        print(f"Not found: {args.entity_type}/{args.entity_id}", file=sys.stderr)
        return 404

    start = time.monotonic()
    data = json.loads(args.data)
    data["entity_type"] = args.entity_type
    data["entity_id"] = args.entity_id
    save_entity(args.entity_type, args.entity_id, data)
    latency_ms = int((time.monotonic() - start) * 1000)
    log_mutation(crud_spec, "update", args.entity_type, args.entity_id, args.actor,
                 compute_change_diff(before, data), "success", latency_ms=latency_ms)
    print(f"OK: updated {args.entity_type}/{args.entity_id} by {args.actor}")
    return 0


def delete_entity(args: argparse.Namespace) -> int:
    crud_spec = load_crud()
    try:
        validate_entity_type(crud_spec, args.entity_type)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 400

    if not is_authorized(crud_spec, "delete", args.actor):
        log_mutation(crud_spec, "delete", args.entity_type, args.entity_id, args.actor, {}, "unauthorized")
        print(f"Unauthorized: actor {args.actor} cannot delete", file=sys.stderr)
        return 403

    before = read_entity(args.entity_type, args.entity_id)
    if before is None:
        print(f"Not found: {args.entity_type}/{args.entity_id}", file=sys.stderr)
        return 404

    start = time.monotonic()
    entity_path(args.entity_type, args.entity_id).unlink()
    latency_ms = int((time.monotonic() - start) * 1000)
    log_mutation(crud_spec, "delete", args.entity_type, args.entity_id, args.actor,
                 compute_change_diff(before, {}), "success", latency_ms=latency_ms)
    print(f"OK: deleted {args.entity_type}/{args.entity_id} by {args.actor}")
    return 0


def bulk_operations(args: argparse.Namespace) -> int:
    crud_spec = load_crud()
    operations = json.loads(args.operations)
    if not isinstance(operations, list):
        print("bulk requires a JSON array of operations", file=sys.stderr)
        return 400
    if len(operations) > crud_spec.get("bulk_limit", 1000):
        print(f"bulk exceeds limit {crud_spec.get('bulk_limit', 1000)}", file=sys.stderr)
        return 400

    start = time.monotonic()
    for op in operations:
        operation = op.get("operation")
        if not is_authorized(crud_spec, operation, args.actor):
            log_mutation(crud_spec, operation, op.get("entity_type", ""), op.get("entity_id", ""),
                         args.actor, {}, "unauthorized")
            print(f"Unauthorized: actor {args.actor} cannot {operation}", file=sys.stderr)
            return 403
    latency_ms = int((time.monotonic() - start) * 1000)

    for op in operations:
        entity_type = op.get("entity_type")
        entity_id = op.get("entity_id")
        operation = op.get("operation")
        data = op.get("data", {})
        before = read_entity(entity_type, entity_id)
        if operation == "create":
            data["entity_type"] = entity_type
            data["entity_id"] = entity_id
            save_entity(entity_type, entity_id, data)
            change_diff = compute_change_diff(None, data)
        elif operation == "update":
            if before is None:
                log_mutation(crud_spec, operation, entity_type, entity_id, args.actor, {}, "not_found")
                continue
            data["entity_type"] = entity_type
            data["entity_id"] = entity_id
            save_entity(entity_type, entity_id, data)
            change_diff = compute_change_diff(before, data)
        elif operation == "delete":
            if before is not None:
                entity_path(entity_type, entity_id).unlink()
            change_diff = compute_change_diff(before, {})
        else:
            log_mutation(crud_spec, operation, entity_type, entity_id, args.actor, {}, "unknown_operation")
            continue
        log_mutation(crud_spec, operation, entity_type, entity_id, args.actor,
                     change_diff, "success", latency_ms=latency_ms)

    print(f"OK: bulk processed {len(operations)} operations by {args.actor}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Provide entity CRUD and bulk operations")
    sub = parser.add_subparsers(dest="command", required=True)

    create_p = sub.add_parser("create", help="Create an entity")
    create_p.add_argument("entity_type")
    create_p.add_argument("entity_id")
    create_p.add_argument("--data", required=True, help="Entity document as JSON")
    create_p.add_argument("--actor", required=True, help="Actor identity (user@hpdc)")
    create_p.set_defaults(handler=create_entity)

    read_p = sub.add_parser("read", help="Read an entity")
    read_p.add_argument("entity_type")
    read_p.add_argument("entity_id")
    read_p.add_argument("--actor", required=True, help="Actor identity (user@hpdc)")
    read_p.set_defaults(handler=read_command)

    update_p = sub.add_parser("update", help="Update an entity")
    update_p.add_argument("entity_type")
    update_p.add_argument("entity_id")
    update_p.add_argument("--data", required=True, help="Entity document as JSON")
    update_p.add_argument("--actor", required=True, help="Actor identity (user@hpdc)")
    update_p.set_defaults(handler=update_entity)

    delete_p = sub.add_parser("delete", help="Delete an entity")
    delete_p.add_argument("entity_type")
    delete_p.add_argument("entity_id")
    delete_p.add_argument("--actor", required=True, help="Actor identity (user@hpdc)")
    delete_p.set_defaults(handler=delete_entity)

    bulk_p = sub.add_parser("bulk", help="Bulk create/update/delete operations")
    bulk_p.add_argument("--operations", required=True, help="JSON array of operations")
    bulk_p.add_argument("--actor", required=True, help="Actor identity (user@hpdc)")
    bulk_p.set_defaults(handler=bulk_operations)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
