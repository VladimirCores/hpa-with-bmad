#!/usr/bin/env python3
"""Install Backstage Developer Portal and Golden Path templates."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gitops" / "install-backstage-dev.py"

STEP_NAME = "26-install-backstage-dev.py"
STEP_DESCRIPTION = "Install Backstage Developer Portal and Golden Path templates"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
