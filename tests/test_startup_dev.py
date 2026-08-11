#!/usr/bin/env python3
"""Validate the HPDC startup.dev.py entry point."""

from __future__ import annotations

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
    result = run([sys.executable, "scripts/startup.dev.py", "--offline", "--check"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "HPDC dev setup completed." in result.stdout


def test_selected_dry_run() -> None:
    result = run([sys.executable, "scripts/startup.dev.py", "--offline", "--dry-run", "--step", "15-validate-offline-gitops-pipeline.py"])
    assert result.returncode == 0, result.stdout + result.stderr
    log = (ROOT / "output" / "startup.dev.log").read_text(encoding="utf-8")
    assert "Offline GitOps pipeline validation passed." in log
    log = (ROOT / "output" / "startup.dev.log").read_text(encoding="utf-8")
    assert "command: python3 scripts/startup.dev.py --offline --dry-run --step 15-validate-offline-gitops-pipeline.py" in log
    assert "Offline GitOps pipeline validation passed." in log


def main() -> int:
    test_list()
    test_check_all_steps()
    test_selected_dry_run()
    print("startup.dev.py validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
