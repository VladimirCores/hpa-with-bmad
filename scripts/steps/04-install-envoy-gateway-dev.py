#!/usr/bin/env python3
"""Step 04: Install Envoy Gateway edge routing in the core layer.

Installs the gateway infrastructure only (cert + EG operator + GatewayClass + Gateway).
Validation is in 04-validate-envoy-gateway-dev.py.
Component exposure (HTTPRoute + E2E) is in separate expose steps.

Run modes (mutually exclusive, one required):
  --check   validate manifests and prerequisites only (no cluster access)
  --dry-run report what would be done (no changes)
  --apply   generate cert and install EG resources to the cluster
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CERT_SCRIPT = ROOT / "scripts" / "gitops" / "gen-edge-cert.py"
EG_SCRIPT = ROOT / "scripts" / "gitops" / "install-envoy-gateway-dev.py"

STEP_NAME = "04-install-envoy-gateway-dev.py"
STEP_DESCRIPTION = "Install Envoy Gateway edge routing in core layer (cert + EG)"


def _run_step(script: Path, mode: str) -> int:
    """Run a gitops script with the given mode. Returns exit code."""
    cmd = [sys.executable, str(script), "--offline", mode]
    result = subprocess.run(cmd, cwd=ROOT, check=False, timeout=600)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=STEP_DESCRIPTION)
    parser.add_argument("--offline", action="store_true", default=True,
                        help="no-op; this step is always offline")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true",
                      help="validate manifests and prerequisites only")
    mode.add_argument("--dry-run", action="store_true",
                      help="report what would be done")
    mode.add_argument("--apply", action="store_true",
                      help="generate cert and install EG resources")
    args = parser.parse_args()

    if args.dry_run:
        print("Envoy Gateway install dry-run:")
        print("  1. Generate static self-signed wildcard TLS cert (*.hpdc.local)")
        print("  2. Install Gateway API CRDs + Envoy Gateway operator")
        print("  3. Apply GatewayClass, Gateway, and HTTPRoutes")
        return 0

    if args.check:
        rc = _run_step(CERT_SCRIPT, "--check")
        if rc != 0:
            print("Cert validation failed.", file=sys.stderr)
            return rc
        rc = _run_step(EG_SCRIPT, "--check")
        if rc != 0:
            print("Envoy Gateway manifest validation failed.", file=sys.stderr)
            return rc
        print("Envoy Gateway install validation passed.")
        return 0

    # --apply: cert → EG install
    print("Step 1/2: Generating static TLS cert...")
    rc = _run_step(CERT_SCRIPT, "--apply")
    if rc != 0:
        print("TLS cert generation failed.", file=sys.stderr)
        return rc

    print("\nStep 2/2: Installing Envoy Gateway...")
    rc = _run_step(EG_SCRIPT, "--apply")
    if rc != 0:
        print("Envoy Gateway install failed.", file=sys.stderr)
        return rc

    print("\nEnvoy Gateway installed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
