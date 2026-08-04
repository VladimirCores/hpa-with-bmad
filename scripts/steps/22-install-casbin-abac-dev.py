#!/usr/bin/env python3
"""Install Casbin ABAC policies for domain routes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "install-casbin-abac-dev.py"

STEP_NAME = "22-install-casbin-abac-dev.py"
STEP_DESCRIPTION = "Install Casbin ABAC policies for domain routes"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
