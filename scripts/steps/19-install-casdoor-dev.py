#!/usr/bin/env python3
"""Install Casdoor JWT AuthN for domain routes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gitops" / "install-casdoor-dev.py"

STEP_NAME = "19-install-casdoor-dev.py"
STEP_DESCRIPTION = "Install Casdoor JWT AuthN for domain routes"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
