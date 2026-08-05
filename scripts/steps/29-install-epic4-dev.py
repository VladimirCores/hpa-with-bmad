#!/usr/bin/env python3
"""Install HPDC Epic 4 offline GitOps scaffold."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate-epic4-dev.py"

STEP_NAME = "29-install-epic4-dev.py"
STEP_DESCRIPTION = "Install HPDC Epic 4 offline GitOps scaffold"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
