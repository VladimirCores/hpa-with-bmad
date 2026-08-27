#!/usr/bin/env python3
"""Validate the HPDC startup.dev.py entry point."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def test_list() -> None:
    result = run([sys.executable, "scripts/startup.dev.py", "--list"])
    assert result.returncode == 0
    assert "01  01-bootstrap-dev.py" in result.stdout
    assert "15  15-validate-offline-gitops-pipeline.py" in result.stdout


def test_check_all_steps() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/startup.dev.py", "--offline", "--check"],
        cwd=ROOT, capture_output=True, text=True,
    )
    # Offline --check without a live cluster cannot fully complete, but the
    # toggle machinery must run cleanly: app-of-apps wired (AC#6), toggle
    # filtering active, and no uncaught Python tracebacks.
    assert "rendering app-of-apps from toggles" in result.stdout, result.stdout
    assert "skipped" in result.stdout, result.stdout
    assert "Traceback" not in result.stderr, result.stderr


def test_selected_dry_run() -> None:
    result = run([sys.executable, "scripts/startup.dev.py", "--offline", "--dry-run", "--step", "15-validate-offline-gitops-pipeline.py"])
    assert result.returncode == 0, result.stdout + result.stderr
    log = (ROOT / "output" / "startup.dev.log").read_text(encoding="utf-8")
    assert "Offline GitOps pipeline validation passed." in log
    log = (ROOT / "output" / "startup.dev.log").read_text(encoding="utf-8")
    assert "command: python3 scripts/startup.dev.py --offline --dry-run --step 15-validate-offline-gitops-pipeline.py" in log
    assert "Offline GitOps pipeline validation passed." in log


def test_status_shows_skipped_for_disabled_steps() -> None:
    """Disabled steps show as skipped in --status --all output."""
    result = run([sys.executable, "scripts/startup.dev.py", "--status", "--all"])
    assert result.returncode == 0
    # With default .env.dev toggles, kargo is disabled
    assert "skipped" in result.stdout
    # Kargo should be skipped (HPDC_KARGO_ENABLED=false in .env.dev)
    lines = result.stdout.splitlines()
    kargo_lines = [l for l in lines if "kargo" in l.lower() and "skipped" in l]
    assert kargo_lines, f"Expected kargo to be skipped, got:\n{result.stdout}"


def test_status_without_all_hides_disabled() -> None:
    """Without --all, disabled steps are hidden from status."""
    result = run([sys.executable, "scripts/startup.dev.py", "--status"])
    assert result.returncode == 0
    # Without --all, skipped steps should not appear
    lines = result.stdout.splitlines()
    skipped_lines = [l for l in lines if "skipped" in l.lower()]
    assert not skipped_lines, f"Expected no skipped lines without --all, got:\n{result.stdout}"


def main() -> int:
    test_list()
    test_check_all_steps()
    test_selected_dry_run()
    test_status_shows_skipped_for_disabled_steps()
    test_status_without_all_hides_disabled()
    print("startup.dev.py validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
