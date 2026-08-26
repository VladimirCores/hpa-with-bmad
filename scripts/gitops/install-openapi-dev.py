#!/usr/bin/env python3
"""Install OpenAPI specification governance."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _provisioned import require
import component_versions

component_versions.load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
SWAGGER_UI_VERSION = component_versions.get("HPDC_SWAGGER_UI_VERSION")
OPENAPI_BASE = ROOT / "gitops" / "openapi" / "base"
OPENAPI_OVERLAY = ROOT / "gitops" / "openapi" / "overlays" / "dev"
SPEC = ROOT / "specs" / "api" / "hpdc-edge-api.yaml"
ROUTE_TABLE = ROOT / "docs" / "openapi-specification-governance.md"


def ensure_files() -> None:
    require("openapi")
    if not ROUTE_TABLE.exists():
        raise RuntimeError(f"OpenAPI documentation missing: {ROUTE_TABLE}")
    if not SPEC.exists():
        raise RuntimeError(f"OpenAPI spec missing: {SPEC}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    required = [OPENAPI_BASE / "openapi.yaml", OPENAPI_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))

    manifest = (OPENAPI_BASE / "openapi.yaml").read_text(encoding="utf-8")
    required_fragments = [
        "kind: Deployment",
        f"image: docker.io/swaggerapi/swagger-ui:{SWAGGER_UI_VERSION}",
        "name: swagger-ui",
        "name: swagger-ui-config",
    ]
    for fragment in required_fragments:
        if fragment not in manifest:
            failures.append(f"openapi.yaml missing {fragment}")

    spec = SPEC.read_text(encoding="utf-8")
    if "openapi: 3.0.3" not in spec:
        failures.append("hpdc-edge-api.yaml missing OpenAPI version")
    if "/api/welcome" not in spec:
        failures.append("hpdc-edge-api.yaml missing /api/welcome route")
    if "/telemetry" not in spec:
        failures.append("hpdc-edge-api.yaml missing /telemetry route")
    if "/events" not in spec:
        failures.append("hpdc-edge-api.yaml missing /events route")
    if "/gql" not in spec:
        failures.append("hpdc-edge-api.yaml missing /gql route")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install OpenAPI specification governance")
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
        print("OpenAPI validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("OpenAPI apply requested.")
        print(f"GitOps overlay: {OPENAPI_OVERLAY.relative_to(ROOT)}")
        return 0
    if args.dry_run:
        print("OpenAPI dry-run passed.")
        print("OpenAPI governance and Swagger UI are configured.")
        print(f"GitOps overlay: {OPENAPI_OVERLAY.relative_to(ROOT)}")
        return 0
    print("OpenAPI requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
