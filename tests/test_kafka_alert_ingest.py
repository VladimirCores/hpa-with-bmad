#!/usr/bin/env python3
"""Validate Kafka alert ingestion GitOps manifests for Epic 5."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def validate_manifests() -> None:
    manifest = read("gitops/kafka/base/kafka-alerts.yaml")
    overlay = read("gitops/kafka/overlays/dev/kustomization.yaml")

    assert "alerts.incoming" in manifest
    assert "alerts.warning" in manifest
    assert "alerts.critical" in manifest
    assert "alerts.state" in manifest
    assert "alerts.dlq" in manifest
    assert "cleanup.policy: compact" in manifest
    assert "alert-schema" in manifest
    assert "partition" in manifest.lower() or "partitions" in manifest.lower()
    assert "../../base" in overlay


def test_dry_run_produces_alert() -> None:
    alert = '{"alert_id":"01900000000000000000000000000000","source":"test","severity":"info","timestamp":"2026-08-06T00:00:00Z","message":"test alert","context":{"host":"localhost"}}'
    result = run([sys.executable, str(SCRIPTS_DIR / "kafka-produce-alert.py"), "--dry-run", alert])
    assert result.returncode == 0


def test_invalid_alert_rejected() -> None:
    alert = '{"message":"missing fields"}'
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "kafka-produce-alert.py"), "--dry-run", alert],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def main() -> int:
    validate_manifests()
    test_dry_run_produces_alert()
    test_invalid_alert_rejected()
    print("Kafka alert ingestion validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())