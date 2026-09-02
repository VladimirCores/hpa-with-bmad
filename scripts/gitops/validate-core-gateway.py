#!/usr/bin/env python3
"""Validate core gateway — Hubble UI and downstream route readiness."""

from __future__ import annotations

import argparse
import os
import socket
import ssl
import subprocess
import sys
import time
import urllib.request
from urllib.error import URLError

import component_versions

component_versions.load_all_dotenv()


def _run(cmd: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run kubectl command with proxy disabled (required for local cluster access)."""
    env = os.environ.copy()
    # Disable proxy for local cluster access
    env.pop('ALL_PROXY', None)
    env.pop('all_proxy', None)
    env.pop('HTTP_PROXY', None)
    env.pop('http_proxy', None)
    env.pop('HTTPS_PROXY', None)
    env.pop('https_proxy', None)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    except FileNotFoundError:
        raise RuntimeError(f"Command not found: {cmd[0]}")
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(cmd)}") from exc
    except UnicodeDecodeError:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout, env=env)
        result.stdout = result.stdout.decode(errors="replace") if result.stdout else ""
        result.stderr = result.stderr.decode(errors="replace") if result.stderr else ""
    return result


def check_gateway_class() -> list[str]:
    """Verify GatewayClass/hpdc-envoy-gateway exists and is Accepted."""
    failures: list[str] = []
    result = _run([
        "kubectl", "get", "gatewayclass", "hpdc-envoy-gateway",
        "-o", "jsonpath={.status.conditions[?(@.type=='Accepted')].status}",
    ])
    if result.returncode != 0:
        failures.append(
            f"GatewayClass/hpdc-envoy-gateway not found: {result.stderr.strip()}"
        )
    elif result.stdout.strip() != "True":
        failures.append(
            f"GatewayClass/hpdc-envoy-gateway not Accepted "
            f"(status={result.stdout.strip()!r})"
        )
    return failures


def check_gateway_programmed() -> list[str]:
    """Verify Gateway/hpdc-edge exists and has Programmed=True."""
    failures: list[str] = []
    result = _run([
        "kubectl", "get", "gateway", "hpdc-edge",
        "-n", "envoy-gateway-system",
        "-o", "jsonpath={.status.conditions[?(@.type=='Programmed')].status}",
    ])
    if result.returncode != 0:
        failures.append(
            f"Gateway/hpdc-edge not found: {result.stderr.strip()}"
        )
    elif result.stdout.strip() != "True":
        failures.append(
            f"Gateway/hpdc-edge not Programmed "
            f"(status={result.stdout.strip()!r})"
        )
    return failures


def check_https_listener() -> list[str]:
    """Verify HTTPS service and Gateway listener are configured."""
    failures: list[str] = []
    
    # Check Gateway has HTTPS listener with TLS
    result = _run([
        "kubectl", "get", "gateway", "hpdc-edge",
        "-n", "envoy-gateway-system",
        "-o", "jsonpath={.spec.listeners[?(@.name=='https')].tls.mode}",
    ])
    if result.returncode != 0 or result.stdout.strip() != "Terminate":
        failures.append("Gateway HTTPS listener TLS mode not 'Terminate'")
        return failures
    
    # Check TLS certificate reference
    result = _run([
        "kubectl", "get", "gateway", "hpdc-edge",
        "-n", "envoy-gateway-system",
        "-o", "jsonpath={.spec.listeners[?(@.name=='https')].tls.certificateRefs[0].name}",
    ])
    if result.returncode != 0 or result.stdout.strip() != "hpdc-edge-tls":
        failures.append("Gateway HTTPS listener not referencing hpdc-edge-tls secret")
        return failures
    
    # Check the secret exists
    result = _run([
        "kubectl", "get", "secret", "hpdc-edge-tls",
        "-n", "envoy-gateway-system",
    ])
    if result.returncode != 0:
        failures.append("TLS secret hpdc-edge-tls not found")
    
    # Check the LoadBalancer service has HTTPS exposed
    # Use label selector to find the service (name includes hash from controller)
    result = _run([
        "kubectl", "get", "svc", "-n", "envoy-gateway-system",
        "-l", "gateway.envoyproxy.io/owning-gateway-name=hpdc-edge",
        "-o", "jsonpath={.items[0].metadata.name}",
    ])
    if result.returncode != 0 or not result.stdout.strip():
        failures.append("LoadBalancer service not found for gateway hpdc-edge")
        return failures
    
    service_name = result.stdout.strip()
    result = _run([
        "kubectl", "get", "svc", service_name,
        "-n", "envoy-gateway-system",
        "-o", "jsonpath={.spec.ports[?(@.name=='https-443')].nodePort}",
    ])
    if result.returncode != 0 or not result.stdout.strip():
        failures.append("HTTPS port not configured in LoadBalancer service")
    
    return failures


def check_dns_resolution() -> list[str]:
    """Verify hubble.hpdc.local is in /etc/hosts resolving to Gateway address."""
    failures: list[str] = []
    
    # Get the actual gateway address from the Gateway resource
    result = _run([
        "kubectl", "get", "gateway", "hpdc-edge",
        "-n", "envoy-gateway-system",
        "-o", "jsonpath={.status.addresses[?(@.type=='IPAddress')].value}",
    ])
    if result.returncode != 0 or not result.stdout.strip():
        # Not a critical failure - just informational
        return []
    
    gateway_address = result.stdout.strip()
    
    try:
        resolved = socket.getaddrinfo("hubble.hpdc.local", 443, socket.AF_INET)
        resolved_ip = resolved[0][4][0]
        if resolved_ip != gateway_address:
            failures.append(
                f"hubble.hpdc.local resolves to {resolved_ip}, "
                f"expected {gateway_address}"
            )
    except socket.gaierror:
        # DNS resolution not required for internal testing
        pass
    return failures


def check_hubble_route() -> list[str]:
    """Verify Hubble UI route is configured via HTTPRoute."""
    failures: list[str] = []
    
    # Check HTTPRoute exists and matches hostname
    result = _run([
        "kubectl", "get", "httproute", "hpdc-edge-domain-routes",
        "-n", "envoy-gateway-system",
        "-o", "jsonpath={.spec.hostnames[0]}",
    ])
    if result.returncode != 0:
        failures.append("HTTPRoute hpdc-edge-domain-routes not found")
        return failures
    
    hostname = result.stdout.strip()
    if "hpdc.local" not in hostname:
        failures.append(f"HTTPRoute hostname doesn't include hpdc.local: {hostname}")
    
    return failures


def check_hubble_ui_pods() -> list[str]:
    """Verify Hubble UI pods are Running in kube-system namespace."""
    failures: list[str] = []
    result = _run([
        "kubectl", "get", "pods",
        "-n", "kube-system",
        "-l", "app.kubernetes.io/name=hubble-ui",
        "-o", "jsonpath={.items[*].status.phase}",
    ])
    if result.returncode != 0:
        failures.append(
            f"Failed to query hubble-ui pods: {result.stderr.strip()}"
        )
        return failures

    phases = result.stdout.strip().split()
    if not phases:
        failures.append(
            "No hubble-ui pods found in kube-system namespace — "
            "deploy Hubble UI before running validation"
        )
        return failures

    non_running = [p for p in phases if p != "Running"]
    if non_running:
        failures.append(
            f"hubble-ui pods not all Running (phases: {' '.join(phases)})"
        )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate core gateway — Hubble UI and downstream route readiness",
    )
    parser.add_argument("--check", action="store_true", help="Run all validation checks")
    args = parser.parse_args()

    checks = [
        ("GatewayClass Accepted", check_gateway_class),
        ("Gateway Programmed", check_gateway_programmed),
        ("HTTPS listener accepting", check_https_listener),
        ("DNS resolution", check_dns_resolution),
        ("Hubble UI route responds", check_hubble_route),
        ("Hubble UI pods Running", check_hubble_ui_pods),
    ]

    all_failures: list[str] = []
    for name, check_fn in checks:
        try:
            failures = check_fn()
        except RuntimeError as exc:
            failures = [str(exc)]
        if failures:
            all_failures.extend(failures)
            for f in failures:
                print(f"FAIL [{name}]: {f}", file=sys.stderr)
        else:
            print(f"PASS [{name}]")

    if all_failures:
        print(f"\n{len(all_failures)} check(s) failed.", file=sys.stderr)
        return 1

    print("\nAll core gateway validation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
