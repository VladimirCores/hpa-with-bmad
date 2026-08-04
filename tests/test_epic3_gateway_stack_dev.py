#!/usr/bin/env python3
"""Validate all Epic 3 gateway and auth stories."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "gitops/security/base/api-key-authn.yaml",
    "gitops/security/overlays/dev/kustomization.yaml",
    "gitops/casdoor/base/casdoor.yaml",
    "gitops/casdoor/overlays/dev/kustomization.yaml",
    "gitops/casbin/base/casbin-rbac.yaml",
    "gitops/casbin/overlays/dev/kustomization.yaml",
    "gitops/casbin/base/casbin-rebac.yaml",
    "gitops/casbin/base/casbin-abac.yaml",
    "gitops/infisical/base/infisical.yaml",
    "gitops/infisical/overlays/dev/kustomization.yaml",
    "gitops/openapi/base/openapi.yaml",
    "gitops/openapi/overlays/dev/kustomization.yaml",
    "gitops/backstage/base/backstage.yaml",
    "gitops/backstage/overlays/dev/kustomization.yaml",
    "gitops/tool-ui/base/tool-ui-routes.yaml",
    "gitops/tool-ui/overlays/dev/kustomization.yaml",
    "gitops/observability/base/observability-ui-routes.yaml",
    "gitops/observability/base/envoy-ui-routes.yaml",
    "gitops/observability/overlays/dev/kustomization.yaml",
    "specs/api/hpdc-edge-api.yaml",
    "docs/api-key-auth-messaging-routes.md",
    "docs/casdoor-jwt-authn.md",
    "docs/casbin-rbac-policies.md",
    "docs/casbin-rebac-policies.md",
    "docs/casbin-abac-policies.md",
    "docs/infisical-secrets-management.md",
    "docs/openapi-specification-governance.md",
    "docs/backstage-developer-portal.md",
    "docs/tool-ui-routes-via-envoy-gateway.md",
    "docs/observability-ui-routes-via-envoy-gateway.md",
    "output/security/api-key-authn-workspaces.txt",
    "output/casdoor/casdoor-workspaces.txt",
    "output/casbin/casbin-rbac-workspaces.txt",
    "output/casbin/casbin-rebac-workspaces.txt",
    "output/casbin/casbin-abac-workspaces.txt",
    "output/infisical/infisical-workspaces.txt",
    "output/openapi/openapi-workspaces.txt",
    "output/backstage/backstage-workspaces.txt",
    "output/tool-ui/tool-ui-workspaces.txt",
    "output/observability/observability-ui-workspaces.txt",
]


def test_epic3_gateway_stack() -> None:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    assert not missing, missing

    api_key = (ROOT / "gitops/security/base/api-key-authn.yaml").read_text(encoding="utf-8")
    assert "SecurityPolicy" in api_key
    assert "messaging-api-keys" in api_key
    assert "X-API-Key" in api_key
    assert "value: /events" in api_key
    assert "value: /telemetry" in api_key

    casdoor = (ROOT / "gitops/casdoor/base/casdoor.yaml").read_text(encoding="utf-8")
    assert "casdoor/casdoor:v5.19.0" in casdoor
    assert "oidc = true" in casdoor
    assert "saml = true" in casdoor

    rbac = (ROOT / "gitops/casbin/base/casbin-rbac.yaml").read_text(encoding="utf-8")
    assert "casbin/ext-authz:v0.0.1" in rbac
    assert "administrator, admin" in rbac
    assert "client, viewer" in rbac

    rebac = (ROOT / "gitops/casbin/base/casbin-rebac.yaml").read_text(encoding="utf-8")
    assert "casbin-rebac-ext-authz" in rebac
    assert "company:acme,admin,client:acme" in rebac

    abac = (ROOT / "gitops/casbin/base/casbin-abac.yaml").read_text(encoding="utf-8")
    assert "casbin-abac-ext-authz" in abac
    assert "time_of_day" in abac
    assert "device_state" in abac

    infisical = (ROOT / "gitops/infisical/base/infisical.yaml").read_text(encoding="utf-8")
    assert "infisical/infisical:0.10.0" in infisical
    assert "rotationIntervalDays: 90" in infisical
    assert "csiDriver" in infisical

    openapi = (ROOT / "gitops/openapi/base/openapi.yaml").read_text(encoding="utf-8")
    assert "swagger-ui:v5.32.0" in openapi
    assert "name: swagger-ui" in openapi
    spec = (ROOT / "specs/api/hpdc-edge-api.yaml").read_text(encoding="utf-8")
    assert "openapi: 3.0.3" in spec
    assert "/api/welcome" in spec
    assert "/telemetry" in spec
    assert "/events" in spec
    assert "/gql" in spec

    backstage = (ROOT / "gitops/backstage/base/backstage.yaml").read_text(encoding="utf-8")
    assert "backstage/backstage:1.42.0" in backstage
    assert "casdoor" in backstage
    assert "catalog" in backstage

    tool_ui = (ROOT / "gitops/tool-ui/base/tool-ui-routes.yaml").read_text(encoding="utf-8")
    assert "hpdc-edge-tool-ui-routes" in tool_ui
    assert "name: backstage" in tool_ui
    assert "name: argocd-server" in tool_ui
    assert "name: kargo-ui" in tool_ui
    assert "gateway.envoyproxy.io/casbin-enforced: \"false\"" in tool_ui

    observability = (ROOT / "gitops/observability/base/observability-ui-routes.yaml").read_text(encoding="utf-8")
    assert "grafana.hpdc.local" in observability
    assert "hubble.hpdc.local" in observability
    assert "nativeAuth: true" in observability
    assert "casbinEnforced: false" in observability


def main() -> int:
    test_epic3_gateway_stack()
    for script in [
        "scripts/install-api-key-auth-dev.py",
        "scripts/install-casdoor-dev.py",
        "scripts/install-casbin-dev.py",
        "scripts/install-casbin-rebac-dev.py",
        "scripts/install-casbin-abac-dev.py",
        "scripts/install-infisical-dev.py",
        "scripts/install-openapi-dev.py",
        "scripts/install-backstage-dev.py",
        "scripts/install-tool-ui-routes-dev.py",
        "scripts/install-observability-ui-routes-dev.py",
    ]:
        subprocess.run([sys.executable, script, "--offline", "--dry-run"], cwd=ROOT, check=True)
    print("Epic 3 gateway stack validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
