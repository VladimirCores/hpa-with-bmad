#!/usr/bin/env python3
"""Install Infisical secrets management."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gitops" / "install-infisical-dev.py"

STEP_NAME = "23-install-infisical-dev.py"
STEP_DESCRIPTION = "Install Infisical secrets management"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
