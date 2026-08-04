#!/usr/bin/env python3
"""Validate Harbor cache preload scaffolding."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def validate() -> None:
    assert (ROOT / "gitops/harbor/base/preload-images.yaml").read_text(encoding="utf-8").count("kind: ConfigMap") >= 1
    assert "offline-image-cache" in (ROOT / "gitops/harbor/base/preload-images.yaml").read_text(encoding="utf-8")
    assert "kind: Job" in (ROOT / "gitops/harbor/base/preload-images.yaml").read_text(encoding="utf-8")
    assert "docker:2.41-cli" in (ROOT / "gitops/harbor/base/preload-images.yaml").read_text(encoding="utf-8")
    assert (ROOT / "gitops/harbor/base/preload-images-job.yaml").read_text(encoding="utf-8").count("kind: ConfigMap") >= 1
    assert (ROOT / "gitops/harbor/overlays/preload/kustomization.yaml").read_text(encoding="utf-8").count("../../base/preload-images.yaml") >= 1
    assert (ROOT / "output/harbor/cache-images.txt").read_text(encoding="utf-8").count("\n") >= 6
    assert (ROOT / "output/harbor/images/harbor-core-v2.11.3").exists()


def main() -> int:
    validate()
    run([sys.executable, "startup.dev.py", "--offline", "--check", "--step", "07-preload-harbor-cache.py"])
    run([sys.executable, "startup.dev.py", "--offline", "--dry-run", "--step", "07-preload-harbor-cache.py"])
    print("Harbor cache preload validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
