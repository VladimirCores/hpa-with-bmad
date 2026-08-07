#!/usr/bin/env python3
"""Install HPDC VMLogs log collection."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "install-vmlogs-dev.py"

STEP_NAME = "36-install-vmlogs-dev.py"
STEP_DESCRIPTION = "Install HPDC VMLogs log collection"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
