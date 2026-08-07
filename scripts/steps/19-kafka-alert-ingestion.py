#!/usr/bin/env python3
"""Step 19: Kafka alert ingestion setup for Epic 5."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "kafka-produce-alert.py"

STEP_NAME = "19-kafka-alert-ingestion.py"
STEP_DESCRIPTION = "Setup Kafka alert ingestion topics and schema for Epic 5."


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
