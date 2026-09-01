#!/usr/bin/env python3
"""Step 05: Install Rook-Ceph storage (staging-only; dev uses local-path).

Rook-Ceph is reserved for a future staging cluster. It is gated at the
startup toggle layer on HPDC_STAGING_ENABLED (default False) so the dev
cluster never attempts it; dev storage defaults to local-path.
"""

from __future__ import annotations

from install_rook_ceph_staging import main

STEP_NAME = "05-install-rook-ceph-staging.py"
STEP_DESCRIPTION = "Install Rook-Ceph storage (staging-only)."

if __name__ == "__main__":
    raise SystemExit(main())
