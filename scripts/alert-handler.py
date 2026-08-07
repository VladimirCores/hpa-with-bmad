#!/usr/bin/env python3
"""Manage human alert handling with an audit trail.

This script processes human actions (acknowledge, investigate, add_note,
resolve, close, reopen) on alerts, validates state transitions and actor
authorization, and records every action in an immutable audit log.
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

ROOT = Path(__file__).resolve().parents[1]
ACTIONS_DEF = ROOT / "gitops" / "alerts" / "base" / "alert-handler-actions.yaml"
DATA_DIR = Path(os.environ.get("HPDC_ALERT_DATA_DIR", ROOT / "output" / "alerts"))
AUDIT_LOG = DATA_DIR / "audit.ndjson"
STATE_LOG = DATA_DIR / "state.ndjson"


def load_actions() -> dict[str, Any]:
    if not ACTIONS_DEF.exists():
        raise RuntimeError(f"Actions definition not found: {ACTIONS_DEF}")
    data = yaml.safe_load(ACTIONS_DEF.read_text(encoding="utf-8"))
    return data.get("spec", {})


def load_alert_state(alert_id: str) -> dict[str, Any] | None:
    if not STATE_LOG.exists():
        return None
    for line in STATE_LOG.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if entry.get("alert_id") == alert_id:
            return entry
    return None


def save_alert_state(alert_id: str, state: str, updated_at: str) -> None:
    entry = {"alert_id": alert_id, "state": state, "updated_at": updated_at}
    STATE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with STATE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def record_audit(entry: dict[str, Any]) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def get_actor_role(actions_spec: dict[str, Any], actor: str) -> str | None:
    users = actions_spec.get("users", {})
    return users.get(actor)


def is_authorized(actions_spec: dict[str, Any], action: str, actor: str) -> bool:
    role = get_actor_role(actions_spec, actor)
    if role is None:
        return False
    action_roles = actions_spec.get("actions", {}).get(action, {}).get("roles", [])
    return role in action_roles


def validate_transition(actions_spec: dict[str, Any], action: str, current_state: str | None) -> str:
    action_def = actions_spec.get("actions", {}).get(action)
    if action_def is None:
        raise ValueError(f"unknown action: {action}")
    current = current_state or "initial"
    from_states = action_def.get("from", [])
    to_state = action_def.get("to", current)
    if current not in from_states:
        raise ValueError(f"invalid transition: {current} -> {to_state} via {action}")
    return to_state


def handle_action(args: argparse.Namespace) -> int:
    actions_spec = load_actions()

    alert_id = args.alert_id
    current = load_alert_state(alert_id)
    current_state = current.get("state") if current else "initial"
    now = datetime.now(timezone.utc).isoformat()

    if not is_authorized(actions_spec, args.action, args.actor):
        entry = {
            "alert_id": alert_id,
            "actor": args.actor,
            "action": args.action,
            "state_before": current_state,
            "state_after": current_state,
            "timestamp": now,
            "result": "unauthorized",
        }
        record_audit(entry)
        print(f"Unauthorized: actor {args.actor} cannot {args.action}", file=sys.stderr)
        return 403

    try:
        to_state = validate_transition(actions_spec, args.action, current_state)
    except ValueError as e:
        entry = {
            "alert_id": alert_id,
            "actor": args.actor,
            "action": args.action,
            "state_before": current_state,
            "state_after": current_state,
            "timestamp": now,
            "result": "invalid_transition",
            "error": str(e),
        }
        record_audit(entry)
        print(str(e), file=sys.stderr)
        return 409

    action_def = actions_spec.get("actions", {}).get(args.action, {})
    if action_def.get("requires_reason") and not args.reason:
        entry = {
            "alert_id": alert_id,
            "actor": args.actor,
            "action": args.action,
            "state_before": current_state,
            "state_after": current_state,
            "timestamp": now,
            "result": "missing_reason",
        }
        record_audit(entry)
        print(f"Action {args.action} requires a reason", file=sys.stderr)
        return 400

    save_alert_state(alert_id, to_state, now)
    entry = {
        "alert_id": alert_id,
        "actor": args.actor,
        "action": args.action,
        "state_before": current_state,
        "state_after": to_state,
        "timestamp": now,
        "result": "success",
        "reason": args.reason or None,
        "correlation_id": str(uuid.uuid4()),
    }
    record_audit(entry)
    print(f"OK: {args.action} {alert_id} {current_state} -> {to_state} by {args.actor}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage human alert handling with audit trail")
    sub = parser.add_subparsers(dest="action", required=True)

    for name, opts in {
        "acknowledge": {"to": "acknowledged"},
        "investigate": {"to": "investigating"},
        "resolve": {"to": "resolved"},
        "close": {"to": "closed"},
        "reopen": {"to": "initial"},
        "add_note": {},
    }.items():
        p = sub.add_parser(name, help=f"Transition alert to {opts.get('to', 'note')} state")
        p.add_argument("alert_id")
        p.add_argument("--actor", required=True, help="Actor identity (user@hpdc)")
        p.add_argument("--reason", default=None, help="Required for resolve/close/reopen")

    args = parser.parse_args()
    return handle_action(args)


if __name__ == "__main__":
    raise SystemExit(main())
