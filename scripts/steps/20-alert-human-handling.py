#!/usr/bin/env python3
"""Step 20: Alert human handling setup for Epic 5."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "services" / "alert-handler.py"

STEP_NAME = "20-alert-human-handling.py"
STEP_DESCRIPTION = "Setup human alert handling API and audit trail for Epic 5."


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--help"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
