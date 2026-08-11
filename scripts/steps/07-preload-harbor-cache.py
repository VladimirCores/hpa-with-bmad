#!/usr/bin/env python3
"""Step 07: Preload Harbor image cache."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
GITOPS_DIR = SCRIPTS_DIR / "gitops"
for entry in (SCRIPTS_DIR, GITOPS_DIR):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from preload_harbor_cache import main as record_main

STEP_NAME = "07-preload-harbor-cache.py"
STEP_DESCRIPTION = "Preload Harbor image cache."


def main() -> int:
    argv = sys.argv[1:]
    if argv and Path(argv[0]).name == Path(__file__).name:
        argv = argv[1:]
    return record_main(argv=argv)


if __name__ == "__main__":
    raise SystemExit(main())
