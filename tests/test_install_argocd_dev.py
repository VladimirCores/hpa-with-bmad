#!/usr/bin/env python3
"""Validate Argo CD scaffolding."""

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
    argocd = (ROOT / "gitops/argo-cd/base/argocd.yaml").read_text(encoding="utf-8")
    assert "kind: ApplicationSet" in argocd and "name: hpdc-applications" in argocd
    assert "argocd.argoproj.io/sync-wave" in argocd
    assert "git://git-mirror/git-mirror" in argocd
    provisioned = _load_provisioned()
    assert provisioned["argocd"]["value"] == "argocd"


def main() -> int:
    validate()
    run([sys.executable, "startup.dev.py", "--offline", "--check", "--step", "12-install-argocd-dev.py"])
    run([sys.executable, "startup.dev.py", "--offline", "--dry-run", "--step", "12-install-argocd-dev.py"])
    print("Argo CD validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
