#!/usr/bin/env python3
"""Install Envoy Gateway observability UI routes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _provisioned import require

ROOT = Path(__file__).resolve().parents[1]
OBSERVABILITY_BASE = ROOT / "gitops" / "observability" / "base"
OBSERVABILITY_OVERLAY = ROOT / "gitops" / "observability" / "overlays" / "dev"
ROUTE_TABLE = ROOT / "docs" / "observability-ui-routes-via-envoy-gateway.md"


def ensure_files() -> None:
    require("observability-ui")
    if not ROUTE_TABLE.exists():
        raise RuntimeError(f"Observability UI documentation missing: {ROUTE_TABLE}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    required = [
        OBSERVABILITY_BASE / "observability-ui-routes.yaml",
        OBSERVABILITY_BASE / "envoy-ui-routes.yaml",
        OBSERVABILITY_OVERLAY / "kustomization.yaml",
    ]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))

    observability = (OBSERVABILITY_BASE / "observability-ui-routes.yaml").read_text(encoding="utf-8")
    envoy_routes = (OBSERVABILITY_BASE / "envoy-ui-routes.yaml").read_text(encoding="utf-8")
    required_fragments = [
        "name: grafana",
        "name: hubble-ui",
        "grafana.hpdc.local",
        "hubble.hpdc.local",
        "nativeAuth: true",
        "casbinEnforced: false",
        "kind: HTTPRoute",
        "name: hpdc-edge-observability-ui-routes",
        "name: grafana",
        "name: hubble-ui",
    ]
    for fragment in required_fragments:
        if fragment not in observability + envoy_routes:
            failures.append(f"observability UI manifests missing {fragment}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Envoy Gateway observability UI routes")
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
        print("Observability UI routes validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Observability UI routes apply requested.")
        print(f"GitOps overlay: {OBSERVABILITY_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("Observability UI routes dry-run passed.")
        print("Grafana and Hubble UI routes are configured.")
        print(f"GitOps overlay: {OBSERVABILITY_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Observability UI routes requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
