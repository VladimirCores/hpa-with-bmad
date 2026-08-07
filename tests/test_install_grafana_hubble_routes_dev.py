#!/usr/bin/env python3
"""Validate HPDC Grafana and Hubble tool UI host routes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OBS_BASE = ROOT / "gitops" / "observability" / "base" / "grafana-hubble-routes.yaml"
OBS_OVERLAY = ROOT / "gitops" / "observability" / "overlays" / "dev" / "kustomization.yaml"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def main() -> int:
    failures: list[str] = []
    for path in [OBS_BASE, OBS_OVERLAY, PLATFORM_SCAFFOLD]:
        if not path.is_file():
            failures.append(f"missing file: {path.relative_to(ROOT)}")

    manifest = OBS_BASE.read_text(encoding="utf-8")
    required = [
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
    for item in required:
        if item not in manifest:
            failures.append(f"grafana-hubble-routes.yaml missing {item}")

    scaffold = PLATFORM_SCAFFOLD.read_text(encoding="utf-8")
    for item in ["grafana-hubble-tool-ui-routes", "host: grafana.hpdc.local", "host: hubble.hpdc.local"]:
        if item not in scaffold:
            failures.append(f"platform-scaffold.yaml missing {item}")

    overlay = OBS_OVERLAY.read_text(encoding="utf-8")
    if "grafana-hubble-routes.yaml" not in overlay:
        failures.append("observability overlay missing grafana-hubble-routes resource")

    if failures:
        print("Grafana and Hubble tool UI routes validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Grafana and Hubble tool UI routes validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
