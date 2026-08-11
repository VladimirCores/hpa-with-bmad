#!/usr/bin/env python3
"""Validate Argo Events scaffolding."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]



def _load_provisioned() -> dict:
    data = yaml.safe_load((ROOT / "output" / "provisioned.yaml").read_text(encoding="utf-8"))
    return data["provisioned"]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def validate() -> None:
    events = (ROOT / "gitops/argo-events/base/argoevents.yaml").read_text(encoding="utf-8")
    assert "kind: EventSource" in events and "name: offline-gitops" in events
    assert "kind: Sensor" in events and "name: offline-gitops" in events
    assert "kind: Workflow" in events and "name: offline-gitops" in events
    assert "git://git-mirror/git-mirror" in events
    provisioned = _load_provisioned()
    assert provisioned["argo-events"]["value"] == "offline-gitops"


def main() -> int:
    validate()
    run([sys.executable, "scripts/startup.dev.py", "--offline", "--check", "--step", "14-install-argoevents-dev.py"])
    run([sys.executable, "scripts/startup.dev.py", "--offline", "--dry-run", "--step", "14-install-argoevents-dev.py"])
    print("Argo Events validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
