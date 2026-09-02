#!/usr/bin/env python3
"""Thin step wrapper for validate-core-gateway.py.

Follows the ``scripts/steps/04.5-gen-edge-cert.py`` convention: dispatches
to the gitops script with ``--offline --dry-run --check`` for the default
pipeline run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gitops" / "validate-core-gateway.py"

STEP_NAME = "validate-core-gateway.py"
STEP_DESCRIPTION = "Validate core gateway: GatewayClass Accepted, Gateway Programmed, TLS Secret, Hubble UI route"


def main() -> int:
    return int(subprocess.run(
        [sys.executable, str(SCRIPT), "--offline", "--check"],
        cwd=ROOT, check=False,
    ).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
