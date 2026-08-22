#!/usr/bin/env python3
"""Step 05: Install storage backend."""

from __future__ import annotations

from install_storage_dev import main

STEP_NAME = "05-install-storage-dev.py"
STEP_DESCRIPTION = "Install storage backend (rook-ceph or local-path)."

if __name__ == "__main__":
    raise SystemExit(main())
