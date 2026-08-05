#!/usr/bin/env python3
"""Install HPDC telemetry ingestion routes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "install-telemetry-ingestion-dev.py"

STEP_NAME = "17-install-telemetry-ingestion-dev.py"
STEP_DESCRIPTION = "Install HPDC telemetry ingestion routes"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
