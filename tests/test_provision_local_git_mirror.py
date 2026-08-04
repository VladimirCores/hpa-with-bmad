#!/usr/bin/env python3
"""Validate local Git mirror scaffolding."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def validate() -> None:
    mirror = (ROOT / "gitops/git/base/git-mirror.yaml").read_text(encoding="utf-8")
    assert "kind: Deployment" in mirror
    assert "name: git-mirror" in mirror
    assert "alpine/git:2.45.2" in mirror
    assert "storageClassName: rook-ceph-rbd" in mirror
    assert (ROOT / "output/git/mirror-repositories.txt").read_text(encoding="utf-8").strip() == "git-mirror"


def main() -> int:
    validate()
    run([sys.executable, "startup.dev.py", "--offline", "--check", "--step", "09-provision-local-git-mirror.py"])
    run([sys.executable, "startup.dev.py", "--offline", "--dry-run", "--step", "09-provision-local-git-mirror.py"])
    print("Local Git mirror validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
