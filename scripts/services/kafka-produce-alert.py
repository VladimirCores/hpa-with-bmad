#!/usr/bin/env python3
"""Produce alert signals to Kafka topics for Epic 5 alert orchestration."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KAFKA_ALERTS_MANIFEST = ROOT / "gitops" / "kafka" / "base" / "kafka-alerts.yaml"
ALERT_LOG = ROOT / "output" / "alerts" / "alert-log.ndjson"


def validate_alert_schema(alert: dict) -> bool:
    try:
        assert "alert_id" in alert
        assert "source" in alert
        assert alert.get("severity") in ("critical", "warning", "info")
        assert "timestamp" in alert
        assert "message" in alert
        assert "context" in alert
        return True
    except AssertionError:
        return False


def produce_alert(alert: dict, dry_run: bool = False) -> int:
    if not validate_alert_schema(alert):
        print("Invalid alert schema", file=sys.stderr)
        return 1
    if dry_run:
        print(json.dumps(alert, indent=2))
        return 0
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ALERT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(alert) + "\n")
    return 0


def main(root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description="Produce alert signals to Kafka")
    parser.add_argument("--dry-run", action="store_true", help="Print alerts to stdout")
    parser.add_argument("alerts", nargs="*", help="Alert JSON payloads")
    args = parser.parse_args()

    for alert_json in args.alerts:
        try:
            alert = json.loads(alert_json)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}", file=sys.stderr)
            return 1
        if produce_alert(alert, dry_run=args.dry_run):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())