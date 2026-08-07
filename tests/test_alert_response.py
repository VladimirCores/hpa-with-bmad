#!/usr/bin/env python3
"""Validate alert response GitOps artifacts for Epic 5."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def validate_manifests() -> None:
    engine = read("gitops/alerts/base/alert-response-engine.yaml")
    workflows = read("gitops/alerts/base/alert-workflows.yaml")
    func = read("gitops/alerts/base/alert-response-function.yaml")
    overlay = read("gitops/alerts/overlays/dev/kustomization.yaml")

    assert "AlertResponseEngine" in engine
    assert "restart_deployment" in engine
    assert "max_actions_per_minute" in engine
    assert "AlertWorkflow" in workflows
    assert "restart-service" in workflows
    assert "memory_pressure" in workflows
    assert "AlertStateMachine" in func
    assert "../../base" in overlay


def test_workflow_yaml_valid() -> None:
    import yaml
    with open("gitops/alerts/base/alert-workflows.yaml") as f:
        data = yaml.safe_load(f)
    assert "spec" in data
    assert "workflows" in data["spec"]
    assert len(data["spec"]["workflows"]) >= 2


def test_dry_run_trigger() -> None:
    alert = json.dumps({
        "alert_id": "01900000000000000000000000000001",
        "alert_type": "service_down",
        "severity": "critical",
        "source": "health-check",
        "timestamp": "2026-08-06T12:00:00Z",
        "context": {"deployment_name": "nginx", "namespace": "default"}
    })
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "alert-response-trigger.py"), "--dry-run", alert],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "DRY-RUN" in result.stdout


def main() -> int:
    validate_manifests()
    test_workflow_yaml_valid()
    test_dry_run_trigger()
    print("Alert response validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
