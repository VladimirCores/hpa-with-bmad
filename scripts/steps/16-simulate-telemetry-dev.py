#!/usr/bin/env python3
"""Step 16: Validate HPDC telemetry simulator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "simulate-telemetry-dev.py"

STEP_NAME = "16-simulate-telemetry-dev.py"
STEP_DESCRIPTION = "Validate HPDC telemetry simulator and acceptance harness."


def main() -> int:
    args = ["--offline"]
    for arg in sys.argv[1:]:
        if arg not in {"--offline", "--dry-run", "--check", "--apply"}:
            args.append(arg)
    if "--check" in sys.argv:
        args.append("--check")
    elif "--apply" in sys.argv:
        args.append("--apply")
    else:
        args.append("--dry-run")
    return int(subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
