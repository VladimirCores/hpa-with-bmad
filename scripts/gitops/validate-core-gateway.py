#!/usr/bin/env python3
"""Validate core gateway — Hubble UI and downstream route readiness."""

from __future__ import annotations

import argparse
import socket
import ssl
import subprocess
import sys
import urllib.request
from urllib.error import URLError

import component_versions

component_versions.load_all_dotenv()


def _run(cmd: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess:
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
    """Verify HTTPS listener on port 443 accepts connections."""
    failures: list[str] = []
    gateway_ip = component_versions.value("HPDC_GATEWAY_IP")
    if not gateway_ip:
        failures.append("HPDC_GATEWAY_IP not set in environment")
        return failures

    result = _run(
        ["kubectl", "exec", "-n", "envoy-gateway-system",
         "deploy/envoy-gateway", "--", "nc", "-z", "-w", "3", gateway_ip, "443"],
        timeout=30,
    )
    if result.returncode != 0:
        failures.append(
            f"HTTPS listener not accepting connections at {gateway_ip}:443"
        )
    return failures


def check_dns_resolution() -> list[str]:
    """Verify hubble.hpdc.local resolves to the gateway IP."""
    failures: list[str] = []
    gateway_ip = component_versions.value("HPDC_GATEWAY_IP")
    if not gateway_ip:
        failures.append("HPDC_GATEWAY_IP not set in environment")
        return failures

    try:
        resolved = socket.getaddrinfo("hubble.hpdc.local", 443, socket.AF_INET)
        resolved_ip = resolved[0][4][0]
        if resolved_ip != gateway_ip:
            failures.append(
                f"hubble.hpdc.local resolves to {resolved_ip}, "
                f"expected {gateway_ip}"
            )
    except socket.gaierror:
        failures.append(
            "hubble.hpdc.local does not resolve — add "
            f"'{gateway_ip} hubble.hpdc.local' to /etc/hosts"
        )
    return failures


def check_hubble_route() -> list[str]:
    """Verify curl -k https://hubble.hpdc.local returns 200 or 302."""
    failures: list[str] = []
    gateway_ip = component_versions.value("HPDC_GATEWAY_IP")
    if not gateway_ip:
        failures.append("HPDC_GATEWAY_IP not set in environment")
        return failures

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = f"https://hubble.hpdc.local:443/"
    try:
        req = urllib.request.Request(url, method="GET")
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        status = resp.getcode()
        if status not in (200, 302):
            failures.append(
                f"https://hubble.hpdc.local returned HTTP {status}, expected 200 or 302"
            )
    except URLError as exc:
        failures.append(f"https://hubble.hpdc.local failed: {exc.reason}")
    except Exception as exc:
        failures.append(f"https://hubble.hpdc.local unexpected error: {exc}")
    return failures


def check_hubble_ui_pods() -> list[str]:
    """Verify Hubble UI pods are Running in the observability namespace."""
    failures: list[str] = []
    result = _run([
        "kubectl", "get", "pods",
        "-n", "observability",
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
            "No hubble-ui pods found in observability namespace — "
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
