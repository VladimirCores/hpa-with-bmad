#!/usr/bin/env python3
"""Validate Argo Rollouts scaffolding."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def validate() -> None:
    rollouts = (ROOT / "gitops/argo-rollouts/base/argorollouts.yaml").read_text(encoding="utf-8")
    assert "kind: Rollout" in rollouts and "name: rollout-demo" in rollouts
    assert "strategy:" in rollouts and "canary:" in rollouts
    assert "pause: {duration: 30s}" in rollouts
    assert (ROOT / "output/argo-rollouts/rollouts.txt").read_text(encoding="utf-8").strip() == "rollout-demo"


def main() -> int:
    validate()
    run([sys.executable, "startup.dev.py", "--offline", "--check", "--step", "13-install-argorollouts-dev.py"])
    run([sys.executable, "startup.dev.py", "--offline", "--dry-run", "--step", "13-install-argorollouts-dev.py"])
    print("Argo Rollouts validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
