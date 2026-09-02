#!/usr/bin/env python3
"""Step 04-validate: Validate Envoy Gateway — GatewayClass Accepted, Gateway Programmed, TLS Secret.

Read-only validation of the gateway infrastructure installed by 04-install-envoy-gateway-dev.py.
Component-specific exposure and E2E tests are in separate expose steps.

Run modes (mutually exclusive, one required):
  --check   run all validation checks
  --dry-run print what would be checked
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATE_SCRIPT = ROOT / "scripts" / "gitops" / "validate-core-gateway.py"

STEP_NAME = "04-validate-envoy-gateway-dev.py"
STEP_DESCRIPTION = "Validate core gateway — GatewayClass Accepted, Gateway Programmed, TLS Secret"


def main() -> int:
    parser = argparse.ArgumentParser(description=STEP_DESCRIPTION)
    parser.add_argument("--offline", action="store_true", default=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Run all validation checks")
    mode.add_argument("--dry-run", action="store_true", help="Print what would be checked")
    args = parser.parse_args()

    if args.dry_run:
        print("Core gateway validation dry-run — checks that would run:")
        print("  1. GatewayClass/hpdc-envoy-gateway Accepted")
        print("  2. Gateway/hpdc-edge Programmed=True")
        print("  3. HTTPS listener accepting at gateway IP:443")
        print("  4. hubble.hpdc.local DNS resolution")
        print("  5. https://hubble.hpdc.local HTTP 200/302")
        print("  6. Hubble UI pods Running in kube-system namespace")
        return 0

    cmd = [sys.executable, str(VALIDATE_SCRIPT), "--check"]
    return int(subprocess.run(cmd, cwd=ROOT, check=False, timeout=120).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
