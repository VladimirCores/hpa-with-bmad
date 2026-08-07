#!/usr/bin/env python3
"""Install HPDC VictoriaMetrics metrics cluster."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "install-victoria-metrics-dev.py"

STEP_NAME = "35-install-victoria-metrics-dev.py"
STEP_DESCRIPTION = "Install HPDC VictoriaMetrics metrics cluster (vmstorage, vminsert, vmselect)"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
