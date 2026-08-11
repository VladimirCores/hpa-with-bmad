#!/usr/bin/env python3
"""Install HPDC entity hierarchy stores (CouchDB, ArcadeDB, YugabyteDB)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gitops" / "install-entity-store-dev.py"

STEP_NAME = "31-install-entity-store-dev.py"
STEP_DESCRIPTION = "Install HPDC entity hierarchy stores (CouchDB, ArcadeDB, YugabyteDB)"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
