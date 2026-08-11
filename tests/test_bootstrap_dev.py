#!/usr/bin/env python3
"""Validate the HPDC bootstrap scaffold."""

from pathlib import Path
import glob
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DIRS = [
    ROOT / "gitops",
    ROOT / "platform",
    ROOT / "backend",
    ROOT / "specs",
    ROOT / "charts",
    ROOT / "docs",
    ROOT / "scripts",
    ROOT / "tests",
]
REQUIRED_FILES = [
    ROOT / "scripts/startup.dev.py",
    ROOT / "scripts" / "steps" / "01-bootstrap-dev.py",
    ROOT / "platform" / "talos" / "machine-config.yaml",
    ROOT / "gitops" / "platform" / "base" / "kustomization.yaml",
    ROOT / "gitops" / "platform" / "overlays" / "dev" / "kustomization.yaml",
    ROOT / "gitops" / "platform" / "overlays" / "prod" / "kustomization.yaml",
    ROOT / "docs" / "bootstrap.md",
    ROOT / "README.md",
    ROOT / "tests" / "test_bootstrap_dev.py",
]

def main() -> int:
    failures = []
    for path in REQUIRED_DIRS:
        if not path.is_dir():
            failures.append(f"missing directory: {path.relative_to(ROOT)}")
    for path in REQUIRED_FILES:
        if not path.is_file():
            failures.append(f"missing file: {path.relative_to(ROOT)}")
    for path in glob.glob(str(ROOT / "scripts" / "*.sh")):
        failures.append(f"non-Python script found: {Path(path).relative_to(ROOT)}")
    if failures:
        print("HPDC scaffold validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("HPDC scaffold validation passed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
