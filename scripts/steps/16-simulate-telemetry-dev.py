#!/usr/bin/env python3
"""Step 16: Validate HPDC telemetry simulator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "telemetry" / "simulate-telemetry-dev.py"

STEP_NAME = "16-simulate-telemetry-dev.py"
STEP_DESCRIPTION = "Validate HPDC telemetry simulator and acceptance harness."


def main() -> int:
    # Validation-only gate (mirrors the other app-layer manifest gates which run
    # validate-only with --dry-run). This step "validates the telemetry simulator
    # and acceptance harness" (config + payload generation + schema), not live
    # emission. It must NOT be driven by startup's --apply: the simulator's
    # --apply performs live emission against localhost:8080/1883/50051 (see
    # output/telemetry-simulator/config.yaml), which have no listener in the
    # offline dev cluster (envoy-gateway is itself a validate-only gate), so
    # --apply always fails with "Connection refused" (exit 5).
    return int(subprocess.run([sys.executable, str(SCRIPT), "--offline", "--dry-run"], cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
