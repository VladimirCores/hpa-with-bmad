#!/usr/bin/env python3
"""Run Hubble UI E2E tests via Playwright (headless Chromium).

This step executes after Hubble UI routes are installed (step 39)
and validates the UI is accessible and backend resources are healthy.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

STEP_NAME = "40-test-hubble-ui-e2e.py"
STEP_DESCRIPTION = "Run Hubble UI E2E tests (Playwright headless Chromium)"

TEST_FILE = ROOT / "tests" / "e2e" / "hubble-ui.spec.ts"
CONFIG_FILE = ROOT / "playwright.config.ts"


def main() -> int:
    if not TEST_FILE.is_file():
        print(f"FAIL: test file not found: {TEST_FILE.relative_to(ROOT)}", file=sys.stderr)
        return 1

    if not CONFIG_FILE.is_file():
        print(f"FAIL: playwright config not found: {CONFIG_FILE.relative_to(ROOT)}", file=sys.stderr)
        return 1

    cmd = [
        "bunx", "playwright", "test",
        "--config", str(CONFIG_FILE),
        "--reporter=list",
    ]

    print(f"Running Hubble UI E2E tests: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT, check=False)

    if result.returncode == 0:
        print("Hubble UI E2E tests passed.")
    else:
        print(f"Hubble UI E2E tests failed (exit code {result.returncode})", file=sys.stderr)

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
