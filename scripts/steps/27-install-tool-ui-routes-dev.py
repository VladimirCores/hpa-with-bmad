#!/usr/bin/env python3
"""Install Envoy Gateway tool UI routes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gitops" / "install-tool-ui-routes-dev.py"

STEP_NAME = "27-install-tool-ui-routes-dev.py"
STEP_DESCRIPTION = "Install Envoy Gateway tool UI routes"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
