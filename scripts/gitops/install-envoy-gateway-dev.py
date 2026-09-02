#!/usr/bin/env python3
"""Install Envoy Gateway edge routing."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from _provisioned import require
import component_versions

component_versions.load_all_dotenv()
ROOT = Path(__file__).resolve().parents[2]
ENVOY_GATEWAY_VERSION = component_versions.get("HPDC_ENVOY_GATEWAY_VERSION")
ENVOY_BASE = ROOT / "gitops" / "envoy-gateway" / "base"
ENVOY_OVERLAY = ROOT / "gitops" / "envoy-gateway" / "overlays" / "dev"
ROUTE_TABLE = ROOT / "docs" / "envoy-gateway-edge-routing.md"
GATEWAY_CRDS = ROOT / "gitops" / "crds" / "gateway" / "crds.yaml"


def ensure_files() -> None:
    require("envoy-gateway")
    if not ROUTE_TABLE.exists():
        raise RuntimeError(f"Envoy Gateway route table documentation missing: {ROUTE_TABLE}")
    if not GATEWAY_CRDS.exists() or GATEWAY_CRDS.stat().st_size == 0:
        raise RuntimeError(f"Gateway API CRDs missing or empty: {GATEWAY_CRDS}")


def _run(cmd: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise RuntimeError(f"Command not found: {cmd[0]}")
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(cmd)}") from exc
    except UnicodeDecodeError:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        result.stdout = result.stdout.decode(errors="replace") if result.stdout else ""
        result.stderr = result.stderr.decode(errors="replace") if result.stderr else ""
    return result


def apply_crds() -> list[str]:
    failures: list[str] = []
    result = _run(["kubectl", "apply", "-f", str(GATEWAY_CRDS)])
    if result.returncode != 0:
        failures.append(f"Gateway API CRD apply failed: {result.stderr.strip()}")
    else:
        if result.stderr.strip():
            print(f"Gateway API CRD warnings: {result.stderr.strip()}")
        print(f"Gateway API CRDs applied from {GATEWAY_CRDS.relative_to(ROOT)}")
        wait = _run(["kubectl", "wait", "--for", "condition=Established",
                      "-l", "apiVersion=gateway.networking.k8s.io",
                      "--timeout=120s", "crd", "-A"])
        if wait.returncode != 0:
            print(f"WARNING: CRD establishment wait failed: {wait.stderr.strip()}")
    return failures


def apply_envoy_gateway() -> list[str]:
    failures: list[str] = []
    result = _run(["kubectl", "apply", "-f", str(ENVOY_BASE / "envoy-gateway.yaml")])
    if result.returncode != 0:
        failures.append(f"Envoy Gateway manifest apply failed: {result.stderr.strip()}")
    else:
        if result.stderr.strip():
            print(f"Envoy Gateway warnings: {result.stderr.strip()}")
        print(f"Envoy Gateway manifest applied from {ENVOY_BASE.relative_to(ROOT)}")
    return failures


def _gateway_programmed() -> bool:
    result = _run([
        "kubectl", "get", "gateway", "hpdc-edge",
        "-n", "envoy-gateway-system",
        "-o", "jsonpath={.status.conditions[?(@.type=='Programmed')].status}",
    ])
    return result.returncode == 0 and result.stdout.strip() == "True"


def validate_manifests() -> list[str]:
    failures: list[str] = []
    required = [ENVOY_BASE / "envoy-gateway.yaml", ENVOY_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))

    manifest = (ENVOY_BASE / "envoy-gateway.yaml").read_text(encoding="utf-8")
    required_kinds = ["Namespace", "ServiceAccount", "ClusterRole", "ClusterRoleBinding", "ConfigMap", "Deployment", "EnvoyProxy", "GatewayClass", "Gateway", "HTTPRoute"]
    for kind in required_kinds:
        if f"kind: {kind}" not in manifest:
            failures.append(f"envoy-gateway.yaml missing kind {kind}")

    required_routes = [
        "value: /data",
        "value: /api",
        "value: /events",
    ]
    for route in required_routes:
        if route not in manifest:
            failures.append(f"envoy-gateway.yaml missing route {route}")

    for route in ["value: /gql", "value: /telemetry"]:
        if route in manifest:
            failures.append(f"envoy-gateway.yaml must not route {route} (moved to its own route in 10.2)")

    if f"image: docker.io/envoyproxy/gateway:v{ENVOY_GATEWAY_VERSION}" not in manifest:
        failures.append("envoy-gateway.yaml missing pinned Envoy Gateway image")

    if "controllerName: gateway.envoyproxy.io/gatewayclass-controller" not in manifest:
        failures.append("envoy-gateway.yaml missing Envoy Gateway GatewayClass controller")

    if "hostname: \"*.hpdc.local\"" not in manifest:
        failures.append("envoy-gateway.yaml missing hpdc.local hostname")

    if "name: mqtt" not in manifest:
        failures.append("envoy-gateway.yaml missing MQTT listener")
    if "port: 1884" not in manifest:
        failures.append("envoy-gateway.yaml missing MQTT listener port 1884")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Envoy Gateway edge routing")
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
        print("Envoy Gateway validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1

    if args.apply:
        failures = apply_crds()
        if failures:
            for failure in failures:
                print(f"- {failure}")
            return 1
        failures = apply_envoy_gateway()
        if failures:
            for failure in failures:
                print(f"- {failure}")
            return 1
        if not _gateway_programmed():
            print("WARNING: Gateway/hpdc-edge is not yet Programmed=True (may need TLS secret)")
        print("Envoy Gateway applied successfully.")
        return 0

    if args.dry_run:
        print("Envoy Gateway dry-run passed.")
        print("Envoy Gateway, GatewayClass, Gateway, and HTTPRoute route table are configured.")
        print(f"GitOps overlay: {ENVOY_OVERLAY.relative_to(ROOT)}")
        return 0

    print("Envoy Gateway requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
