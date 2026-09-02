#!/usr/bin/env python3
"""Step 04.5: Generate static self-signed wildcard TLS cert for Envoy Gateway.

Thin step wrapper around ``scripts/gitops/gen-edge-cert.py``. Follows the
``17-install-cert-manager-dev.py`` thin-wrapper convention (subprocess dispatch
to the gitops script) but forwards the active mode flag so the step honors the
``--check`` / ``--dry-run`` / ``--apply`` interface expected by startup.dev.py.

Run modes (mutually exclusive, one required):
  --check   validate local cert state only
  --dry-run report what would be done (no changes)
  --apply   generate cert (if absent) and apply the TLS Secret to the cluster
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gitops" / "gen-edge-cert.py"

STEP_NAME = "04.5-gen-edge-cert.py"
STEP_DESCRIPTION = "Generate static self-signed wildcard TLS cert for Envoy Gateway"


def main() -> int:
    parser = argparse.ArgumentParser(description=STEP_DESCRIPTION)
    parser.add_argument("--offline", action="store_true", default=True,
                        help="no-op; this step is always offline")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate local cert state only")
    mode.add_argument("--dry-run", action="store_true", help="report what would be done")
    mode.add_argument("--apply", action="store_true", help="generate cert and apply Secret to cluster")
    args = parser.parse_args()

    cmd = [sys.executable, str(SCRIPT), "--offline"]
    if args.check:
        cmd.append("--check")
    elif args.dry_run:
        cmd.append("--dry-run")
    else:
        cmd.append("--apply")

    return int(subprocess.run(cmd, cwd=ROOT, check=False, timeout=600).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
