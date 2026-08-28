#!/usr/bin/env python3
"""Step 02: Provision the offline dev cluster.

Routes to the correct bootstrap based on HPDC_PROVIDER:
  kind   → bootstrap_kind_dev.py (kind + local-path)
  docker → bootstrap_talos_dev.py (Talos-on-Docker + local-path)
  qemu   → bootstrap_talos_dev.py (Talos/QEMU + rook-ceph)
"""

from __future__ import annotations

import os
import sys

STEP_NAME = "02-bootstrap-talos-dev.py"
STEP_DESCRIPTION = "Provision the offline dev cluster."


def main() -> int:
    provider = os.getenv("HPDC_PROVIDER", "kind")
    if provider not in ("kind", "docker", "qemu"):
        print(f"Unknown HPDC_PROVIDER: {provider!r} (expected kind, docker, or qemu)", file=sys.stderr)
        return 1
    if provider == "kind":
        from bootstrap_kind_dev import main as kind_main
        return kind_main()
    else:
        from bootstrap_talos_dev import main as talos_main
        return talos_main()


if __name__ == "__main__":
    raise SystemExit(main())
