#!/usr/bin/env python3
"""Step 04: Install Envoy Gateway edge routing in the core layer.

Unified step combining:
  - TLS cert generation (static self-signed wildcard for *.hpdc.local)
  - Envoy Gateway operator + GatewayClass + Gateway apply
  - Core gateway validation (GatewayClass Accepted, Gateway Programmed, etc.)
  - Hubble UI E2E accessibility tests (Playwright headless Chromium)

Run modes (mutually exclusive, one required):
  --check   validate manifests and prerequisites only (no cluster access)
  --dry-run report what would be done (no changes)
  --apply   generate cert, install EG, apply Gateway, validate, and run E2E tests
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CERT_SCRIPT = ROOT / "scripts" / "gitops" / "gen-edge-cert.py"
EG_SCRIPT = ROOT / "scripts" / "gitops" / "install-envoy-gateway-dev.py"
VALIDATE_SCRIPT = ROOT / "scripts" / "gitops" / "validate-core-gateway.py"
E2E_TEST_FILE = ROOT / "tests" / "e2e" / "hubble-ui.spec.ts"
E2E_CONFIG_FILE = ROOT / "playwright.config.ts"

STEP_NAME = "04-install-envoy-gateway-dev.py"
STEP_DESCRIPTION = "Install Envoy Gateway edge routing in core layer (cert + EG + validation + E2E)"


def _run_step(script: Path, mode: str) -> int:
    """Run a gitops script with the given mode. Returns exit code."""
    cmd = [sys.executable, str(script), "--offline", mode]
    result = subprocess.run(cmd, cwd=ROOT, check=False, timeout=600)
    return result.returncode


def _run_e2e_tests() -> int:
    """Run Hubble UI E2E tests via Playwright. Returns exit code."""
    if not E2E_TEST_FILE.is_file():
        print(f"FAIL: E2E test file not found: {E2E_TEST_FILE.relative_to(ROOT)}",
              file=sys.stderr)
        return 1
    if not E2E_CONFIG_FILE.is_file():
        print(f"FAIL: playwright config not found: {E2E_CONFIG_FILE.relative_to(ROOT)}",
              file=sys.stderr)
        return 1

    cmd = ["bunx", "playwright", "test", "--config", str(E2E_CONFIG_FILE), "--reporter=list"]
    print(f"Running Hubble UI E2E tests: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT, check=False, timeout=120)
    if result.returncode == 0:
        print("Hubble UI E2E tests passed.")
    else:
        print(f"Hubble UI E2E tests failed (exit code {result.returncode})",
              file=sys.stderr)
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
                      help="generate cert, install EG, apply Gateway, validate, run E2E")
    args = parser.parse_args()

    if args.dry_run:
        print("Envoy Gateway unified step dry-run:")
        print("  1. Generate static self-signed wildcard TLS cert (*.hpdc.local)")
        print("  2. Install Gateway API CRDs + Envoy Gateway operator")
        print("  3. Validate: GatewayClass Accepted, Gateway Programmed, TLS Secret, DNS, Hubble UI")
        print("  4. Run Hubble UI E2E accessibility tests (Playwright headless Chromium)")
        return 0

    if args.check:
        # Validate cert prerequisites + EG manifests (no cluster access)
        rc = _run_step(CERT_SCRIPT, "--check")
        if rc != 0:
            print("Cert validation failed.", file=sys.stderr)
            return rc
        rc = _run_step(EG_SCRIPT, "--check")
        if rc != 0:
            print("Envoy Gateway manifest validation failed.", file=sys.stderr)
            return rc
        # Validate E2E test artifacts exist
        if not E2E_TEST_FILE.is_file():
            print(f"FAIL: E2E test file not found: {E2E_TEST_FILE.relative_to(ROOT)}",
                  file=sys.stderr)
            return 1
        if not E2E_CONFIG_FILE.is_file():
            print(f"FAIL: playwright config not found: {E2E_CONFIG_FILE.relative_to(ROOT)}",
                  file=sys.stderr)
            return 1
        print("Envoy Gateway unified step validation passed.")
        return 0

    # --apply: cert → EG install → validate → E2E tests
    print("Step 1/4: Generating static TLS cert...")
    rc = _run_step(CERT_SCRIPT, "--apply")
    if rc != 0:
        print("TLS cert generation failed.", file=sys.stderr)
        return rc

    print("\nStep 2/4: Installing Envoy Gateway...")
    rc = _run_step(EG_SCRIPT, "--apply")
    if rc != 0:
        print("Envoy Gateway install failed.", file=sys.stderr)
        return rc

    print("\nStep 3/4: Validating core gateway...")
    rc = _run_step(VALIDATE_SCRIPT, "--check")
    if rc != 0:
        print("Core gateway validation failed.", file=sys.stderr)
        return rc

    print("\nStep 4/4: Running Hubble UI E2E accessibility tests...")
    rc = _run_e2e_tests()
    if rc != 0:
        print("Hubble UI E2E tests failed.", file=sys.stderr)
        return rc

    print("\nEnvoy Gateway installed, validated, and E2E tested successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
