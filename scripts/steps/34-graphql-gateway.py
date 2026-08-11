#!/usr/bin/env python3
"""Cross-store GraphQL gateway setup for Epic 6."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "services" / "graphql-gateway.py"

STEP_NAME = "34-graphql-gateway.py"
STEP_DESCRIPTION = "Setup cross-store GraphQL gateway with Hasura role-based permissions."


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--help"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
