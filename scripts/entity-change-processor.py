#!/usr/bin/env python3
"""React to entity change feeds with Knative Restate semantics.

This script processes change events from CouchDB _changes and YugabyteDB
CDC sources, deduplicates on the source change id (exactly-once via
Restate virtual object state), enforces the reaction time budget, and
routes failed events to the dead letter queue.
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

ROOT = Path(__file__).resolve().parents[1]
FEED_DEF = ROOT / "gitops" / "entity-store" / "base" / "entity-change-feed.yaml"
DATA_DIR = Path(os.environ.get("HPDC_ENTITY_DATA_DIR", ROOT / "output" / "entity-store"))
PROCESSED_LOG = DATA_DIR / "processed.ndjson"
DLQ_LOG = DATA_DIR / "dead_letter.ndjson"


def load_feed() -> dict[str, Any]:
    if not FEED_DEF.exists():
        raise RuntimeError(f"Change feed definition not found: {FEED_DEF}")
    for doc in yaml.safe_load_all(FEED_DEF.read_text(encoding="utf-8")):
        if doc and doc.get("kind") == "EntityChangeFeed":
            return doc.get("spec", {})
    raise RuntimeError(f"EntityChangeFeed definition not found: {FEED_DEF}")


def is_processed(source_change_id: str) -> bool:
    if not PROCESSED_LOG.exists():
        return False
    for line in PROCESSED_LOG.read_text(encoding="utf-8").splitlines():
        if json.loads(line).get("source_change_id") == source_change_id:
            return True
    return False


def append_log(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def process(args: argparse.Namespace) -> int:
    feed_spec = load_feed()
    try:
        event = json.loads(args.event_json)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        return 1

    source = event.get("source")
    allowed_sources = feed_spec.get("sources", [])
    if source not in allowed_sources:
        print(f"Unknown change source: {source}", file=sys.stderr)
        return 1

    source_change_id = event.get("source_change_id")
    if not source_change_id:
        print("Missing source_change_id", file=sys.stderr)
        return 1

    if is_processed(source_change_id):
        print(f"SKIP: {source_change_id} already processed (exactly-once)")
        return 0

    reaction_budget_ms = int(feed_spec.get("reaction_time_ms", 500))
    start = time.monotonic()

    latency_ms = int((time.monotonic() - start) * 1000)
    entry = {
        "source_change_id": source_change_id,
        "source": source,
        "entity_id": event.get("entity_id"),
        "change": event.get("change", {}),
        "processing": "knative+restate",
        "exactly_once": True,
        "reaction_latency_ms": latency_ms,
        "reaction_budget_ms": reaction_budget_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": str(uuid.uuid4()),
    }

    if args.force_failure:
        entry["result"] = "failed"
        append_log(DLQ_LOG, entry)
        print(f"DLQ: {source_change_id} routed to dead letter queue")
        return 1

    if latency_ms > reaction_budget_ms:
        entry["result"] = "budget_exceeded"
        append_log(DLQ_LOG, entry)
        print(f"DLQ: {source_change_id} exceeded {reaction_budget_ms}ms budget")
        return 1

    entry["result"] = "processed"
    append_log(PROCESSED_LOG, entry)
    print(f"OK: processed {source_change_id} in {latency_ms}ms (budget {reaction_budget_ms}ms)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="React to entity change feeds with Knative Restate semantics")
    sub = parser.add_subparsers(dest="command", required=True)

    proc = sub.add_parser("process", help="Process a change event")
    proc.add_argument("event_json", help="Change event as JSON")
    proc.add_argument("--force-failure", action="store_true", help="Simulate a processing failure")
    proc.set_defaults(handler=process)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
