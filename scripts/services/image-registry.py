#!/usr/bin/env python3
"""Ensure the offline image-cache registry container is running.

Container: hpa-local-registry (registry:2), port 5000, restart unless-stopped.
Durable storage lives INSIDE the project: <root>/resources/registry/data
(gitignored). Idempotent: starts existing container or recreates it with the
canonical config if missing.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DATA = ROOT / "resources" / "registry" / "data"
CONTAINER = "hpa-local-registry"


def _run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=check)


def ensure_registry() -> int:
    REGISTRY_DATA.mkdir(parents=True, exist_ok=True)

    # Running?
    result = _run(["docker", "ps", "--filter", f"name=^/{CONTAINER}$", "--format", "{{.Names}}"], check=False)
    if result.returncode == 0 and result.stdout.strip() == CONTAINER:
        print(f"{CONTAINER} already running.")
        return 0

    # Exists but stopped -> start it
    result = _run(["docker", "ps", "-a", "--filter", f"name=^/{CONTAINER}$", "--format", "{{.Names}}"], check=False)
    if result.returncode == 0 and result.stdout.strip() == CONTAINER:
        print(f"Starting existing {CONTAINER}...")
        _run(["docker", "start", CONTAINER])
    else:
        # Recreate with canonical project-local storage
        print(f"Creating {CONTAINER} with storage at {REGISTRY_DATA} ...")
        _run([
            "docker", "run", "-d",
            "--name", CONTAINER,
            "--restart", "unless-stopped",
            "-p", "5000:5000",
            "-v", f"{REGISTRY_DATA}:/var/lib/registry",
            "registry:2",
        ])

    # Health probe
    import urllib.request
    try:
        with urllib.request.urlopen(os.getenv("HPDC_LOCAL_REGISTRY_URL", "http://localhost:5000") + "/v2/_catalog", timeout=5) as resp:
            repos = len(__import__("json").load(resp).get("repositories", []))
        print(f"{CONTAINER} healthy: {repos} repos cached.")
        return 0
    except Exception as error:
        print(f"Warning: registry probe failed: {error}", file=sys.stderr)
        return 1


def main() -> int:
    return ensure_registry()


if __name__ == "__main__":
    raise SystemExit(main())
