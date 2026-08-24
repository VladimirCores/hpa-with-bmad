#!/usr/bin/env python3
"""Render every component dev overlay into a committed flat manifest.

ArgoCD's repo-server enforces kustomize LoadRestrictionsRootOnly, which the
cross-cutting overlays (../../base, sibling components) cannot satisfy. We
therefore render each overlay host-side -- where no restriction applies --
and commit the result under gitops/<component>/rendered/dev.yaml. The App-of-
Apps children consume these rendered files as plain directory sources.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITOPS = ROOT / "gitops"


def render(component: Path) -> int:
    overlay = component / "overlays" / "dev"
    if not (overlay / "kustomization.yaml").exists():
        return 0
    out_dir = component / "rendered"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["kustomize", "build",
         "--load-restrictor", "LoadRestrictionsNone",
         str(overlay)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        print(f"FAIL {component.name}: {result.stderr.strip()[:300]}")
        return 1
    (out_dir / "dev.yaml").write_text(result.stdout, encoding="utf-8")
    print(f"OK   {component.name} -> gitops/{component.name}/rendered/dev.yaml")
    return 0


def main() -> int:
    failures = 0
    for component in sorted(GITOPS.iterdir()):
        if component.is_dir():
            failures += render(component)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
