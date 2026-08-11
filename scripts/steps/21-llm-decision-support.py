#!/usr/bin/env python3
"""Step 21: LLM decision support setup for Epic 5."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "services" / "alert-decision-support.py"

STEP_NAME = "21-llm-decision-support.py"
STEP_DESCRIPTION = "Setup basic LLM decision support for alerts."


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--help"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
