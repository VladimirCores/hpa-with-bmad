#!/usr/bin/env python3
"""Install Envoy Gateway tool UI routes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_UI_MARKER = ROOT / "output" / "tool-ui" / "tool-ui-workspaces.txt"
TOOL_UI_BASE = ROOT / "gitops" / "tool-ui" / "base"
TOOL_UI_OVERLAY = ROOT / "gitops" / "tool-ui" / "overlays" / "dev"
ROUTE_TABLE = ROOT / "docs" / "tool-ui-routes-via-envoy-gateway.md"


def ensure_files() -> None:
    if not TOOL_UI_MARKER.exists():
        raise RuntimeError(f"Tool UI workspace marker not found: {TOOL_UI_MARKER}")
    if not ROUTE_TABLE.exists():
        raise RuntimeError(f"Tool UI documentation missing: {ROUTE_TABLE}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    required = [TOOL_UI_BASE / "tool-ui-routes.yaml", TOOL_UI_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))

    manifest = (TOOL_UI_BASE / "tool-ui-routes.yaml").read_text(encoding="utf-8")
    required_fragments = [
        "kind: HTTPRoute",
        "name: hpdc-edge-tool-ui-routes",
        "name: backstage",
        "name: argocd-server",
        "name: kargo-ui",
        "gateway.envoyproxy.io/casbin-enforced: \"false\"",
    ]
    for fragment in required_fragments:
        if fragment not in manifest:
            failures.append(f"tool-ui-routes.yaml missing {fragment}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Envoy Gateway tool UI routes")
    parser.add_argument("--offline", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.check:
        ensure_files()
        failures = validate_manifests()
        if failures:
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("Tool UI routes validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Tool UI routes apply requested.")
        print(f"GitOps overlay: {TOOL_UI_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("Tool UI routes dry-run passed.")
        print("Backstage, Argo CD, and Kargo UI routes are configured.")
        print(f"GitOps overlay: {TOOL_UI_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Tool UI routes requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
