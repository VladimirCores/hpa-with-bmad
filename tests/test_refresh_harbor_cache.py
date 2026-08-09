#!/usr/bin/env python3
"""Validate Harbor cache refresh scaffolding."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from _provisioned import record  # noqa: E402


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def validate() -> None:
    refresh = (ROOT / "gitops/harbor/base/image-cache-refresh.yaml").read_text(encoding="utf-8")
    images = (record("harbor-image-cache") or {}).get("images") or []
    assert "kind: ConfigMap" in refresh
    assert "harbor-image-cache-refresh" in refresh
    assert "digest:" in refresh
    assert "changed: false" in refresh
    core = next((image for image in images if image.get("name") == "harbor/harbor-core:v2.11.3"), None)
    assert core is not None and core.get("digest") == "sha256:offline-core"
    assert (ROOT / "output/harbor/images/harbor-core-v2.11.3").exists()


def main() -> int:
    validate()
    run([sys.executable, "startup.dev.py", "--offline", "--check", "--step", "08-refresh-harbor-cache.py"])
    run([sys.executable, "startup.dev.py", "--offline", "--dry-run", "--step", "08-refresh-harbor-cache.py"])
    print("Harbor cache refresh validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
