#!/usr/bin/env python3
"""Install HPDC authenticated agent-to-agent (A2A) communication."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gitops" / "install-a2a-dev.py"

STEP_NAME = "44-install-a2a-dev.py"
STEP_DESCRIPTION = "Install HPDC authenticated agent-to-agent (A2A) communication"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
