#!/usr/bin/env python3
"""Install cert-manager TLS termination for Envoy Gateway."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gitops" / "install-cert-manager-dev.py"

STEP_NAME = "17-install-cert-manager-dev.py"
STEP_DESCRIPTION = "Install cert-manager TLS termination for Envoy Gateway"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
