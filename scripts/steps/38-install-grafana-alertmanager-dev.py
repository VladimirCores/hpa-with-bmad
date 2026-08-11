#!/usr/bin/env python3
"""Install HPDC Grafana dashboards and Alertmanager."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gitops" / "install-grafana-alertmanager-dev.py"

STEP_NAME = "38-install-grafana-alertmanager-dev.py"
STEP_DESCRIPTION = "Install HPDC Grafana dashboards and Alertmanager"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
