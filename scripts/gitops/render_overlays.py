#!/usr/bin/env python3
"""Render every component dev overlay into a committed flat manifest.

ArgoCD's repo-server enforces kustomize LoadRestrictionsRootOnly, which the
cross-cutting overlays (../../base, sibling components) cannot satisfy. We
therefore render each overlay host-side -- where no restriction applies --
and commit the result under gitops/<component>/rendered/dev.yaml. The App-of-
Apps children consume these rendered files as plain directory sources.

After the kustomize build, image tags are substituted name-keyed from
scripts/gitops/component_versions.py so that component versions chosen in
.env flow into the committed rendered artifacts. Repositories not present in
the catalog (CRD bundles, custom project builds) pass through untouched.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import component_versions

ROOT = Path(__file__).resolve().parents[2]
GITOPS = ROOT / "gitops"

_IMAGE_LINE = re.compile(
    r'^(\s*(?:-\s*)?image:\s*)(["\']?)([^:"\'\s]+):([^"\'#\s]+)\2(\s*#.*)?$'
)


def substitute_images(text: str) -> tuple[str, list[tuple[str, str, str]]]:
    """Rewrite catalogued image tags in rendered YAML.

    Returns (new_text, [(repo, old_tag, new_tag), ...]) — substitutions only;
    unknown repos and already-correct tags are left byte-identical.
    """
    mapping = component_versions.substitution_map()
    # longest repo spelling first so prefixed names can't shadow each other
    ordered = sorted(mapping.items(), key=lambda kv: -len(kv[0]))
    changes: list[tuple[str, str, str]] = []

    def repl(match: re.Match[str]) -> str:
        prefix, quote, repo, tag, comment = match.groups()
        for want_repo, full_ref in ordered:
            if repo == want_repo:
                new_tag = full_ref.split(":", 1)[1]
                if new_tag != tag:
                    changes.append((repo, tag, new_tag))
                    return f"{prefix}{quote}{want_repo}:{new_tag}{quote}{comment or ''}"
                return match.group(0)
        return match.group(0)

    lines = [ _IMAGE_LINE.sub(repl, line) for line in text.splitlines(keepends=True) ]
    return "".join(lines), changes


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
    rendered, changes = substitute_images(result.stdout)
    target = out_dir / "dev.yaml"
    if target.exists() and target.read_text(encoding="utf-8") == rendered:
        print(f"OK   {component.name} -> gitops/{component.name}/rendered/dev.yaml (unchanged)")
        return 0
    target.write_text(rendered, encoding="utf-8")
    detail = f" [{len(changes)} img: " + ", ".join(f"{r.rsplit('/', 1)[-1]}:{o}->{n}" for r, o, n in changes[:4]) + "]" if changes else ""
    print(f"OK   {component.name} -> gitops/{component.name}/rendered/dev.yaml{detail}")
    return 0


def main() -> int:
    component_versions.load_all_dotenv()
    component_versions.resolve()
    failures = 0
    for component in sorted(GITOPS.iterdir()):
        if component.is_dir():
            failures += render(component)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
