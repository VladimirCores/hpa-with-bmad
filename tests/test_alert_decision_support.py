#!/usr/bin/env python3
"""Validate basic LLM decision support for alerts, Epic 5 story 5-5."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "alert-decision-support.py"


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, HPDC_LLM_DATA_DIR=str(cwd))
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


def validate_manifests() -> None:
    decision = (ROOT / "gitops/alerts/base/llm-decision-support.yaml").read_text(encoding="utf-8")
    api = (ROOT / "gitops/alerts/base/llm-decision-support-api.yaml").read_text(encoding="utf-8")
    base_ks = (ROOT / "gitops/alerts/base/kustomization.yaml").read_text(encoding="utf-8")
    dashboard = (ROOT / "gitops/monitoring/base/llm-decision-dashboard.json").read_text(encoding="utf-8")

    assert "LlmDecisionSupport" in decision
    assert "execute_without_approval: false" in decision
    assert "auto_execute_threshold" in decision
    assert "llm-decision-support-api" in api
    assert "kind: Service" in api
    assert "llm-decision-support.yaml" in base_ks
    assert "llm-decision-support-api.yaml" in base_ks
    assert "llm_decision" in dashboard or "decision" in dashboard


def test_recommend_sensitive_pending_approval() -> None:
    alert = '{"alert_id":"01900000000000000000000000000010","alert_type":"service_down","severity":"critical","source":"health-check","context":{"deployment_name":"nginx","namespace":"default"}}'
    with tempfile.TemporaryDirectory() as tmp:
        result = run(["recommend", alert], cwd=Path(tmp))
        assert result.returncode == 0
        out = json.loads(result.stdout)
        assert out["action"] == "restart_deployment"
        assert out["sensitive"] is True
        assert out["decision"] == "pending_approval"
        log = Path(tmp) / "decisions.ndjson"
        entries = [json.loads(l) for l in log.read_text().splitlines()]
        assert entries[0]["sensitive"] is True
        assert entries[0]["input_context"]["deployment_name"] == "nginx"


def test_recommend_auto_execute_non_sensitive() -> None:
    alert = '{"alert_id":"01900000000000000000000000000011","alert_type":"unknown_type","severity":"critical","source":"health-check","context":{}}'
    with tempfile.TemporaryDirectory() as tmp:
        result = run(["recommend", alert], cwd=Path(tmp))
        assert result.returncode == 0
        out = json.loads(result.stdout)
        assert out["action"] == "notify_with_context"
        assert out["sensitive"] is False


def test_approve_authorized() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = run(["approve", "rec-123", "--actor", "carol@hpdc"], cwd=Path(tmp))
        assert result.returncode == 0
        log = Path(tmp) / "approvals.ndjson"
        entries = [json.loads(l) for l in log.read_text().splitlines()]
        assert entries[0]["approved"] is True


def test_approve_unauthorized() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = run(["approve", "rec-456", "--actor", "dave@hpdc"], cwd=Path(tmp))
        assert result.returncode != 0
        log = Path(tmp) / "approvals.ndjson"
        entries = [json.loads(l) for l in log.read_text().splitlines()]
        assert entries[0]["approved"] is False
        assert entries[0]["reason"] == "unauthorized"


def main() -> int:
    validate_manifests()
    test_recommend_sensitive_pending_approval()
    test_recommend_auto_execute_non_sensitive()
    test_approve_authorized()
    test_approve_unauthorized()
    print("Alert decision support validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
