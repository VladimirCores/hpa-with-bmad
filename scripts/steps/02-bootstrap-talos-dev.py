#!/usr/bin/env python3
"""Step 02: Provision the offline Talos dev cluster."""

from __future__ import annotations

from bootstrap_talos_dev import main

STEP_NAME = "02-bootstrap-talos-dev.py"
STEP_DESCRIPTION = "Provision the offline Talos dev cluster."

if __name__ == "__main__":
    raise SystemExit(main())
