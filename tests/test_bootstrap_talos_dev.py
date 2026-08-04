#!/usr/bin/env python3
"""Validate the Talos dev bootstrap scaffold."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    ROOT / "scripts" / "bootstrap-talos-dev.py",
    ROOT / "scripts" / "bootstrap_talos_dev.py",
    ROOT / "platform" / "talos" / "machine-config.yaml",
    ROOT / "docs" / "bootstrap.md",
    ROOT / "docs" / "talos-dev-cluster.md",
    ROOT / "tests" / "test_bootstrap_dev.py",
    ROOT / "tests" / "test_bootstrap_talos_dev.py",
]


def main() -> int:
    failures = []
    for path in REQUIRED_FILES:
        if not path.exists():
            failures.append(f"missing file: {path.relative_to(ROOT)}")
    if failures:
        print("Talos bootstrap scaffold validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Talos bootstrap scaffold validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
