#!/usr/bin/env python3
"""Entity CRUD and bulk operations setup for Epic 6."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "entity-api.py"

STEP_NAME = "32-entity-crud.py"
STEP_DESCRIPTION = "Setup entity CRUD and bulk operations with RBAC and mutation audit."


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--help"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
