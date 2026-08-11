#!/usr/bin/env python3
"""Install HPDC Grafana and Hubble tool UI host routes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OBS_BASE = ROOT / "gitops" / "observability" / "base"
OBS_OVERLAY = ROOT / "gitops" / "observability" / "overlays" / "dev"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def ensure_files() -> None:
    for path in [OBS_BASE / "grafana-hubble-routes.yaml", OBS_OVERLAY / "kustomization.yaml", PLATFORM_SCAFFOLD]:
        if not path.exists():
            raise RuntimeError(f"required file missing: {path.relative_to(ROOT)}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    manifest = (OBS_BASE / "grafana-hubble-routes.yaml").read_text(encoding="utf-8")
    overlay = (OBS_OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")

    required_kinds = [
        "kind: ToolUIRoute",
        "name: grafana-hubble-tool-ui-routes",
        "host: grafana.hpdc.local",
        "service: grafana",
        "native_auth: true",
        "host: hubble.hpdc.local",
        "service: hubble-ui",
        "casdoor_casbin_ext_authz: false",
        "termination: envoy_gateway",
        "kind: HTTPRoute",
        "name: hpdc-edge-grafana-hubble-host-routes",
        "grafana.hpdc.local",
        "name: hpdc-edge-hubble-host-route",
        "hubble.hpdc.local",
        "name: hubble-ui",
    ]
    for item in required_kinds:
        if item not in manifest:
            failures.append(f"grafana-hubble-routes.yaml missing {item}")

    scaffold = PLATFORM_SCAFFOLD.read_text(encoding="utf-8")
    if "grafana-hubble-tool-ui-routes" not in scaffold:
        failures.append("platform-scaffold.yaml missing grafana-hubble-tool-ui-routes contract")
    if "host: grafana.hpdc.local" not in scaffold:
        failures.append("platform-scaffold.yaml missing grafana.hpdc.local host")
    if "host: hubble.hpdc.local" not in scaffold:
        failures.append("platform-scaffold.yaml missing hubble.hpdc.local host")

    if "grafana-hubble-routes.yaml" not in overlay:
        failures.append("observability overlay missing grafana-hubble-routes resource")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC Grafana and Hubble tool UI host routes")
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
        print("Grafana and Hubble tool UI routes validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Grafana and Hubble tool UI routes apply requested.")
        print(f"GitOps overlay: {OBS_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("Grafana and Hubble tool UI routes dry-run passed.")
        print("grafana.hpdc.local and hubble.hpdc.local are exposed via the Envoy Gateway with native auth.")
        print("TLS is terminated at the Envoy Gateway.")
        print(f"GitOps overlay: {OBS_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Grafana and Hubble tool UI routes require --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
