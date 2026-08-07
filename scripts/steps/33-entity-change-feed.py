#!/usr/bin/env python3
"""Entity change feed processing setup for Epic 6."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "entity-change-processor.py"

STEP_NAME = "33-entity-change-feed.py"
STEP_DESCRIPTION = "Setup entity change feed processing with Knative Restate semantics."


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--help"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
