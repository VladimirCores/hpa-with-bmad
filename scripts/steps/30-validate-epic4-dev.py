#!/usr/bin/env python3
"""Validate HPDC Epic 4 offline telemetry pipeline scaffold."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate-epic4-dev.py"

STEP_NAME = "30-validate-epic4-dev.py"
STEP_DESCRIPTION = "Validate HPDC Epic 4 offline telemetry pipeline scaffold"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run", "--check"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
