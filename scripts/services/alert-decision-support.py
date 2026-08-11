#!/usr/bin/env python3
"""Provide basic LLM decision support for alert responses.

This script generates actionable remediation recommendations with
confidence scoring, enforces the sensitive-action approval gate, and
logs every decision with its input context and decision context.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[2]
DECISION_DEF = ROOT / "gitops" / "alerts" / "base" / "llm-decision-support.yaml"
DATA_DIR = Path(os.environ.get("HPDC_LLM_DATA_DIR", ROOT / "output" / "alerts"))
DECISION_LOG = DATA_DIR / "decisions.ndjson"
APPROVAL_LOG = DATA_DIR / "approvals.ndjson"


def load_config() -> dict[str, Any]:
    if not DECISION_DEF.exists():
        raise RuntimeError(f"Decision support definition not found: {DECISION_DEF}")
    data = yaml.safe_load(DECISION_DEF.read_text(encoding="utf-8"))
    return data.get("spec", {})


def score_recommendation(alert: dict) -> tuple[str, float]:
    """Return a deterministic (action, confidence) recommendation."""
    alert_type = alert.get("alert_type", "")
    severity = alert.get("severity", "info")
    confidence = 0.9 if severity == "critical" else 0.7

    if alert_type == "service_down":
        return "restart_deployment", confidence
    if alert_type == "memory_pressure":
        return "increase_hpa_target", confidence
    if alert_type == "node_unreachable":
        return "delete_pod", confidence
    return "notify_with_context", 0.4


def append_jsonl(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def recommend(args: argparse.Namespace) -> int:
    config = load_config()

    try:
        alert = json.loads(args.alert_json)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        return 1

    action, confidence = score_recommendation(alert)
    sensitive_actions = config.get("approval", {}).get("required_for", [])
    requires_approval = action in sensitive_actions

    auto_execute_threshold = config.get("confidence", {}).get("auto_execute_threshold", 0.85)
    decision = "execute" if (not requires_approval and confidence >= auto_execute_threshold) else "pending_approval"

    entry = {
        "recommendation_id": str(uuid.uuid4()),
        "alert_id": alert.get("alert_id"),
        "action": action,
        "confidence": confidence,
        "sensitive": requires_approval,
        "decision": decision,
        "input_context": alert.get("context", {}),
        "decision_context": {
            "auto_execute_threshold": auto_execute_threshold,
            "sensitive_action_policy": config.get("sensitive_action_policy"),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    append_jsonl(DECISION_LOG, entry)

    print(json.dumps({
        "action": action,
        "confidence": confidence,
        "sensitive": requires_approval,
        "decision": decision,
    }))
    return 0


def approve(args: argparse.Namespace) -> int:
    config = load_config()
    authorized_users = config.get("approvers", [])
    if args.actor not in authorized_users:
        append_jsonl(APPROVAL_LOG, {
            "recommendation_id": args.recommendation_id,
            "actor": args.actor,
            "approved": False,
            "reason": "unauthorized",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        print(f"Unauthorized: {args.actor} cannot approve", file=sys.stderr)
        return 403
    append_jsonl(APPROVAL_LOG, {
        "recommendation_id": args.recommendation_id,
        "actor": args.actor,
        "approved": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    print(f"Approved: {args.recommendation_id} by {args.actor}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Provide basic LLM decision support for alerts")
    sub = parser.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("recommend", help="Generate a recommendation for an alert")
    rec.add_argument("alert_json", help="Alert signal as JSON")
    rec.set_defaults(handler=recommend)

    appr = sub.add_parser("approve", help="Approve a pending recommendation")
    appr.add_argument("recommendation_id")
    appr.add_argument("--actor", required=True, help="Approving actor identity")
    appr.set_defaults(handler=approve)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
