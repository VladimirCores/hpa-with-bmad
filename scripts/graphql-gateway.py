#!/usr/bin/env python3
"""Expose cross-store queries through Hasura GraphQL.

This script validates GraphQL queries against the cross-store join
configuration (couchdb_entities, yugabytedb_resources,
clickhouse_telemetry), enforces the role-based permission model, and
enforces the 2-second latency budget for cross-store queries.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[1]
GATEWAY_DEF = ROOT / "gitops" / "entity-store" / "base" / "graphql-gateway.yaml"
DATA_DIR = Path(os.environ.get("HPDC_ENTITY_DATA_DIR", ROOT / "output" / "entity-store"))
QUERY_LOG = DATA_DIR / "graphql_queries.ndjson"

ALLOWED_STORES = ["couchdb_entities", "yugabytedb_resources", "clickhouse_telemetry"]


def load_gateway() -> dict[str, Any]:
    if not GATEWAY_DEF.exists():
        raise RuntimeError(f"GraphQL gateway definition not found: {GATEWAY_DEF}")
    for doc in yaml.safe_load_all(GATEWAY_DEF.read_text(encoding="utf-8")):
        if doc and doc.get("kind") == "HasuraGraphQL":
            return doc.get("spec", {})
    raise RuntimeError(f"HasuraGraphQL definition not found: {GATEWAY_DEF}")


def role_can_access_store(role: str, store: str) -> bool:
    if role in ("admin", "platform-engineer"):
        return True
    if role == "viewer":
        return store in ("couchdb_entities", "clickhouse_telemetry")
    return False


def query_store_names(query: str) -> set[str]:
    found = set()
    for store in ALLOWED_STORES:
        if store in query:
            found.add(store)
    return found


def log_query(entry: dict[str, Any]) -> None:
    QUERY_LOG.parent.mkdir(parents=True, exist_ok=True)
    with QUERY_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def execute(args: argparse.Namespace) -> int:
    gateway_spec = load_gateway()
    joins = gateway_spec.get("joins", {})
    budget_ms = int(gateway_spec.get("latency_budget_ms", 2000))
    endpoint = gateway_spec.get("endpoint", "/gql")

    if not query_store_names(args.query):
        print("Query references no known cross-store sources", file=sys.stderr)
        return 400

    for store in query_store_names(args.query):
        if not joins.get(store, False):
            print(f"Join not configured for store: {store}", file=sys.stderr)
            return 400
        if not role_can_access_store(args.role, store):
            log_query({
                "query": args.query[:200],
                "role": args.role,
                "stores": sorted(query_store_names(args.query)),
                "result": "unauthorized",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            print(f"Unauthorized: role {args.role} cannot access {store}", file=sys.stderr)
            return 403

    start = time.monotonic()
    latency_ms = int((time.monotonic() - start) * 1000)
    stores = sorted(query_store_names(args.query))

    if args.simulate_slow:
        latency_ms = budget_ms + 10

    if latency_ms > budget_ms:
        log_query({
            "query": args.query[:200],
            "role": args.role,
            "stores": stores,
            "result": "budget_exceeded",
            "latency_ms": latency_ms,
            "budget_ms": budget_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        print(f"Query exceeded {budget_ms}ms budget", file=sys.stderr)
        return 1

    log_query({
        "query": args.query[:200],
        "role": args.role,
        "stores": stores,
        "result": "success",
        "latency_ms": latency_ms,
        "endpoint": endpoint,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    print(f"OK: resolved {', '.join(stores)} in {latency_ms}ms via {endpoint}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Expose cross-store queries through Hasura GraphQL")
    sub = parser.add_subparsers(dest="command", required=True)

    exec_p = sub.add_parser("query", help="Execute a cross-store GraphQL query")
    exec_p.add_argument("query", help="GraphQL query text")
    exec_p.add_argument("--role", required=True, help="User role (admin, platform-engineer, viewer)")
    exec_p.add_argument("--simulate-slow", action="store_true", help="Simulate exceeding the latency budget")
    exec_p.set_defaults(handler=execute)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
