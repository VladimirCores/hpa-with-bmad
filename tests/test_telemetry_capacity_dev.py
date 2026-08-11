#!/usr/bin/env python3
"""Validate HPDC telemetry capacity behavior."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPACITY_SCRIPT = ROOT / "scripts" / "telemetry" / "telemetry_capacity.py"


def validate() -> None:
    under = subprocess.run([sys.executable, str(CAPACITY_SCRIPT), "--device-type", "sensor", "--count", "25000"], cwd=ROOT, text=True, capture_output=True, check=True)
    assert '"status": 202' in under.stdout, under.stdout
    over = subprocess.run([sys.executable, str(CAPACITY_SCRIPT), "--device-type", "sensor", "--count", "25001"], cwd=ROOT, text=True, capture_output=True, check=False)
    assert over.returncode == 2, over.returncode
    assert '"status": 429' in over.stdout, over.stdout


def test_telemetry_capacity_behavior() -> None:
    validate()


def main() -> int:
    validate()
    print("Telemetry capacity validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
