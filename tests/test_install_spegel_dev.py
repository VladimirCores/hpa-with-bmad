#!/usr/bin/env python3
"""Validate Spegel scaffolding."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEGEL_VERSION = "0.4.0"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def validate() -> None:
    spegel = (ROOT / "gitops/spegel/base/spegel.yaml").read_text(encoding="utf-8")
    assert "kind: DaemonSet" in spegel
    assert "name: spegel" in spegel
    assert f"ghcr.io/spegel-org/spegel:v{SPEGEL_VERSION}" in spegel
    assert "kind: Service" in spegel and "name: spegel-registry" in spegel
    assert (ROOT / "output/spegel/images/spegel-v0.4.0").exists()


def main() -> int:
    validate()
    run([sys.executable, "scripts/startup.dev.py", "--offline", "--check", "--step", "10-install-spegel-dev.py"])
    run([sys.executable, "scripts/startup.dev.py", "--offline", "--dry-run", "--step", "10-install-spegel-dev.py"])
    print("Spegel validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
