#!/usr/bin/env python3
"""Install HPDC Cilium ClusterMesh cross-cluster service discovery."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "install-clustermesh-dev.py"

STEP_NAME = "40-install-clustermesh-dev.py"
STEP_DESCRIPTION = "Install HPDC Cilium ClusterMesh cross-cluster service discovery"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
