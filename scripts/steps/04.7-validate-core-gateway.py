#!/usr/bin/env python3
"""Step 04.7: Validate core gateway — Hubble UI and downstream route readiness."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gitops" / "validate-core-gateway.py"

STEP_NAME = "04.7-validate-core-gateway.py"
STEP_DESCRIPTION = "Validate core gateway — Hubble UI and downstream route readiness."


def main() -> int:
    parser = argparse.ArgumentParser(description=STEP_DESCRIPTION)
    parser.add_argument("--offline", action="store_true", default=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Run all validation checks")
    mode.add_argument("--dry-run", action="store_true", help="Print what would be checked")
    mode.add_argument("--apply", action="store_true", help="Run all validation checks")
    args = parser.parse_args()

    cmd = [sys.executable, str(SCRIPT), "--check"]

    if args.dry_run:
        print("Core gateway validation dry-run — checks that would run:")
        print("  1. GatewayClass/hpdc-envoy-gateway Accepted")
        print("  2. Gateway/hpdc-edge Programmed=True")
        print("  3. HTTPS listener accepting at ${HPDC_GATEWAY_IP}:443")
        print("  4. hubble.hpdc.local DNS resolution")
        print("  5. https://hubble.hpdc.local HTTP 200/302")
        print("  6. Hubble UI pods Running in observability namespace")
        return 0

    return int(subprocess.run(cmd, cwd=ROOT, check=False, timeout=120).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
