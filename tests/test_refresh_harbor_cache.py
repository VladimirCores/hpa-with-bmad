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

sys.path.insert(0, str(ROOT / "scripts" / "gitops"))
import component_versions  # noqa: E402

component_versions.load_all_dotenv()
HARBOR_VERSION = component_versions.get("HPDC_HARBOR_VERSION")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def validate() -> None:
    refresh = (ROOT / "gitops/harbor/base/image-cache-refresh.yaml").read_text(encoding="utf-8")
    images = (record("harbor-image-cache") or {}).get("images") or []
    assert "kind: ConfigMap" in refresh
    assert "harbor-image-cache-refresh" in refresh
    assert "digest:" in refresh
    assert "changed: false" in refresh
    core = next((image for image in images if image.get("name") == f"harbor/harbor-core:v{HARBOR_VERSION}"), None)
    assert core is not None and core.get("digest") == "sha256:offline-core"
    assert (ROOT / f"output/harbor/images/harbor-core-v{HARBOR_VERSION}").exists()


def main() -> int:
    validate()
    run([sys.executable, "scripts/startup.dev.py", "--offline", "--check", "--step", "08-refresh-harbor-cache.py"])
    run([sys.executable, "scripts/startup.dev.py", "--offline", "--dry-run", "--step", "08-refresh-harbor-cache.py"])
    print("Harbor cache refresh validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
