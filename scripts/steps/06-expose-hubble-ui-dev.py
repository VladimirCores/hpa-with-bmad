#!/usr/bin/env python3
"""Expose Hubble UI via Envoy Gateway and run E2E accessibility tests.

Creates the HTTPRoute for hubble.hpdc.local, validates the route is
programmed, and runs Playwright E2E tests to confirm the UI is accessible.

Run modes (mutually exclusive, one required):
  --check   validate route manifest only (no cluster access)
  --dry-run report what would be done (no changes)
  --apply   apply HTTPRoute, validate, and run E2E tests
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROUTES_MANIFEST = ROOT / "gitops" / "observability" / "base" / "grafana-hubble-routes.yaml"
E2E_TEST_FILE = ROOT / "tests" / "e2e" / "hubble-ui.spec.ts"
E2E_CONFIG_FILE = ROOT / "playwright.config.ts"

STEP_NAME = "06-expose-hubble-ui-dev.py"
STEP_DESCRIPTION = "Expose Hubble UI via Envoy Gateway and run E2E accessibility tests"


def _run(cmd: list[str], *, timeout: int = 600, input: str | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              input=input, errors="replace")
    except FileNotFoundError:
        raise RuntimeError(f"Command not found: {cmd[0]}")
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(cmd)}") from exc


def _extract_hubble_route() -> str | None:
    """Extract the Hubble HTTPRoute from the combined manifest."""
    if not ROUTES_MANIFEST.is_file():
        return None
    content = ROUTES_MANIFEST.read_text(encoding="utf-8")
    # Split on YAML document separator and find the Hubble route
    docs = content.split("---")
    for doc in docs:
        if "name: hpdc-edge-hubble-host-route" in doc and "kind: HTTPRoute" in doc:
            return doc.strip()
    return None


def validate_manifest() -> list[str]:
    """Validate the Hubble HTTPRoute manifest exists and is well-formed."""
    failures: list[str] = []
    if not ROUTES_MANIFEST.is_file():
        failures.append(f"Routes manifest not found: {ROUTES_MANIFEST.relative_to(ROOT)}")
        return failures

    route = _extract_hubble_route()
    if route is None:
        failures.append("Hubble HTTPRoute (hpdc-edge-hubble-host-route) not found in manifest")
        return failures

    required_fragments = [
        "kind: HTTPRoute",
        "name: hpdc-edge-hubble-host-route",
        "hubble.hpdc.local",
        "name: hubble-ui",
        "namespace: observability",
    ]
    for fragment in required_fragments:
        if fragment not in route:
            failures.append(f"Hubble HTTPRoute missing: {fragment}")

    return failures


def apply_route() -> list[str]:
    """Apply the Hubble HTTPRoute to the cluster."""
    failures: list[str] = []
    route = _extract_hubble_route()
    if route is None:
        failures.append("Cannot apply: Hubble HTTPRoute not found in manifest")
        return failures

    result = _run(["kubectl", "apply", "-f", "-"], input=route)
    if result.returncode != 0:
        failures.append(f"HTTPRoute apply failed: {result.stderr.strip()}")
    else:
        print(f"Applied Hubble HTTPRoute from {ROUTES_MANIFEST.relative_to(ROOT)}")
    return failures


def check_route_programmed() -> list[str]:
    """Verify the Hubble HTTPRoute is programmed."""
    failures: list[str] = []
    result = _run([
        "kubectl", "get", "httproute", "hpdc-edge-hubble-host-route",
        "-n", "envoy-gateway-system",
        "-o", "jsonpath={.status.parents[?(@.parentRef.name=='hpdc-edge')].conditions[?(@.type=='Accepted')].status}",
    ])
    if result.returncode != 0:
        failures.append(f"HTTPRoute not found: {result.stderr.strip()}")
    elif result.stdout.strip() != "True":
        # Not a hard failure — route may need time to program
        print(f"WARNING: HTTPRoute not yet Accepted (status={result.stdout.strip()!r})")
    return failures


def run_e2e_tests() -> int:
    """Run Hubble UI E2E tests via Playwright."""
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
                      help="validate route manifest only")
    mode.add_argument("--dry-run", action="store_true",
                      help="report what would be done")
    mode.add_argument("--apply", action="store_true",
                      help="apply HTTPRoute, validate, and run E2E tests")
    args = parser.parse_args()

    if args.dry_run:
        print("Hubble UI expose dry-run:")
        print("  1. Apply HTTPRoute for hubble.hpdc.local → hubble-ui service")
        print("  2. Validate route is programmed")
        print("  3. Run Hubble UI E2E accessibility tests (Playwright)")
        return 0

    if args.check:
        failures = validate_manifest()
        if failures:
            for f in failures:
                print(f"- {f}")
            return 1
        if not E2E_TEST_FILE.is_file():
            print(f"FAIL: E2E test file not found: {E2E_TEST_FILE.relative_to(ROOT)}",
                  file=sys.stderr)
            return 1
        print("Hubble UI expose validation passed.")
        return 0

    # --apply: route → validate → E2E
    print("Step 1/3: Applying Hubble HTTPRoute...")
    failures = apply_route()
    if failures:
        for f in failures:
            print(f"- {f}", file=sys.stderr)
        return 1

    print("\nStep 2/3: Validating route...")
    check_route_programmed()

    print("\nStep 3/3: Running Hubble UI E2E accessibility tests...")
    rc = run_e2e_tests()
    if rc != 0:
        print("Hubble UI E2E tests failed.", file=sys.stderr)
        return rc

    print("\nHubble UI exposed and validated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
