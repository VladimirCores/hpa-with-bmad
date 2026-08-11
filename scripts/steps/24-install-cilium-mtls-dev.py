#!/usr/bin/env python3
"""Configure Cilium mTLS mesh enforcement."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gitops" / "install_cilium_mtls_dev.py"

STEP_NAME = "24-install-cilium-mtls-dev.py"
STEP_DESCRIPTION = "Configure Cilium mTLS mesh enforcement"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
