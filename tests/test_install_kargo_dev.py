#!/usr/bin/env python3
"""Validate Kargo scaffolding."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def validate() -> None:
    kargo = (ROOT / "gitops/kargo/base/kargo.yaml").read_text(encoding="utf-8")
    assert "kind: Warehouse" in kargo and "name: offline-gitops" in kargo
    assert "kind: Stage" in kargo and "name: dev" in kargo
    assert "kind: Freight" in kargo and "name: offline-dev" in kargo
    assert "git://git-mirror/git-mirror" in kargo
    assert (ROOT / "output/kargo/kargo-workspaces.txt").read_text(encoding="utf-8").strip() == "kargo"


def main() -> int:
    validate()
    run([sys.executable, "startup.dev.py", "--offline", "--check", "--step", "11-install-kargo-dev.py"])
    run([sys.executable, "startup.dev.py", "--offline", "--dry-run", "--step", "11-install-kargo-dev.py"])
    print("Kargo validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
