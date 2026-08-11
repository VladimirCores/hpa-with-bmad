#!/usr/bin/env python3
"""Validate human alert handling with audit trail for Epic 5 story 5-4."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "services" / "alert-handler.py"


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, HPDC_ALERT_DATA_DIR=str(cwd))
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


def validate_manifests() -> None:
    audit = (ROOT / "gitops/alerts/base/alert-audit-trail.yaml").read_text(encoding="utf-8")
    api = (ROOT / "gitops/alerts/base/alert-handler-api.yaml").read_text(encoding="utf-8")
    actions = (ROOT / "gitops/alerts/base/alert-handler-actions.yaml").read_text(encoding="utf-8")
    overlay = (ROOT / "gitops/alerts/overlays/dev/kustomization.yaml").read_text(encoding="utf-8")
    base_ks = (ROOT / "gitops/alerts/base/kustomization.yaml").read_text(encoding="utf-8")

    assert "AlertAuditTrail" in audit
    assert "acknowledge" in audit
    assert "invalid_transition_response" in audit
    assert "alert-handler-api" in api
    assert "kind: Service" in api
    assert "AlertHandlerActions" in actions
    assert "resolve" in actions
    assert "roles" in actions
    assert "hpdc-alerts" in overlay
    assert "alert-handler-actions.yaml" in base_ks
    assert "alert-handler-api.yaml" in base_ks

    dashboard = (ROOT / "gitops/monitoring/base/alert-handling-dashboard.json").read_text(encoding="utf-8")
    assert "Alert Human Handling" in dashboard
    assert "alert_audit_actions_total" in dashboard


def test_acknowledge_audited() -> None:
    alert_id = "01900000000000000000000000000001"
    with tempfile.TemporaryDirectory() as tmp:
        run(["acknowledge", alert_id, "--actor", "alice@hpdc"], cwd=Path(tmp))
        audit_path = Path(tmp) / "audit.ndjson"
        assert audit_path.exists(), audit_path
        entries = [json.loads(l) for l in audit_path.read_text().splitlines()]
        assert entries[0]["action"] == "acknowledge"
        assert entries[0]["result"] == "success"
        assert entries[0]["state_before"] == "initial"
        assert entries[0]["state_after"] == "acknowledged"
        assert entries[0]["actor"] == "alice@hpdc"


def test_invalid_transition_rejected() -> None:
    alert_id = "01900000000000000000000000000002"
    with tempfile.TemporaryDirectory() as tmp:
        run(["acknowledge", alert_id, "--actor", "alice@hpdc"], cwd=Path(tmp))
        result = run(["acknowledge", alert_id, "--actor", "alice@hpdc"], cwd=Path(tmp))
        assert result.returncode != 0
        audit_path = Path(tmp) / "audit.ndjson"
        entries = [json.loads(l) for l in audit_path.read_text().splitlines()]
        assert entries[1]["result"] == "invalid_transition"


def test_unauthorized_actor_rejected() -> None:
    alert_id = "01900000000000000000000000000003"
    with tempfile.TemporaryDirectory() as tmp:
        result = run(["resolve", alert_id, "--actor", "dave@hpdc", "--reason", "fixed"], cwd=Path(tmp))
        assert result.returncode != 0
        audit_path = Path(tmp) / "audit.ndjson"
        entries = [json.loads(l) for l in audit_path.read_text().splitlines()]
        assert entries[0]["result"] == "unauthorized"


def test_resolve_requires_reason() -> None:
    alert_id = "01900000000000000000000000000004"
    with tempfile.TemporaryDirectory() as tmp:
        run(["acknowledge", alert_id, "--actor", "bob@hpdc"], cwd=Path(tmp))
        result = run(["resolve", alert_id, "--actor", "bob@hpdc"], cwd=Path(tmp))
        assert result.returncode != 0
        audit_path = Path(tmp) / "audit.ndjson"
        entries = [json.loads(l) for l in audit_path.read_text().splitlines()]
        assert entries[1]["result"] == "missing_reason"


def test_full_lifecycle() -> None:
    alert_id = "01900000000000000000000000000005"
    with tempfile.TemporaryDirectory() as tmp:
        run(["acknowledge", alert_id, "--actor", "alice@hpdc"], cwd=Path(tmp))
        run(["investigate", alert_id, "--actor", "bob@hpdc"], cwd=Path(tmp))
        result = run(["resolve", alert_id, "--actor", "bob@hpdc", "--reason", "root cause fixed"], cwd=Path(tmp))
        assert result.returncode == 0
        run(["close", alert_id, "--actor", "carol@hpdc", "--reason", "verified"], cwd=Path(tmp))
        audit_path = Path(tmp) / "audit.ndjson"
        entries = [json.loads(l) for l in audit_path.read_text().splitlines()]
        actions = [e["action"] for e in entries]
        assert actions == ["acknowledge", "investigate", "resolve", "close"]


def main() -> int:
    validate_manifests()
    test_acknowledge_audited()
    test_invalid_transition_rejected()
    test_unauthorized_actor_rejected()
    test_resolve_requires_reason()
    test_full_lifecycle()
    print("Alert human handling validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
