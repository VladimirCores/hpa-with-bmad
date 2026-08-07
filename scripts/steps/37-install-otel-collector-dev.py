#!/usr/bin/env python3
"""Install HPDC OpenTelemetry Collector for distributed traces."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "install-otel-collector-dev.py"

STEP_NAME = "37-install-otel-collector-dev.py"
STEP_DESCRIPTION = "Install HPDC OpenTelemetry Collector for distributed traces"


def main() -> int:
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
