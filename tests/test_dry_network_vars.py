#!/usr/bin/env python3
"""DRY guard: ensure base manifests use ${HPDC_*} placeholders instead of hardcoded IPs.

This test prevents regression where network IPs get hardcoded in base manifests,
violating the single-source-of-truth principle established in Story 12-3.

Contract source:
  - output/implementation-artifacts/12-3-centralize-gateway-ip-and-cilium-lb-range-in-env.md
  - gitops/envoy-gateway/base/envoy-gateway.yaml
  - gitops/cilium/base/cilium-loadbalancer-ippool.yaml
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITOPS = ROOT / "gitops"

# Network IPs that MUST be defined as variables, not literals
NETWORK_IPS = {
    "HPDC_GATEWAY_IP": "172.18.0.2",
    "HPDC_CILIUM_LB_POOL_RANGE": "172.18.0.0/24",
}


def test_base_manifests_use_env_placeholders() -> None:
    """Verify base manifests use ${HPDC_*} placeholders instead of hardcoded IPs."""
    violations: list[str] = []
    
    for base_file in GITOPS.glob("*/base/*.yaml"):
        content = base_file.read_text(encoding="utf-8")
        
        for var_name, ip_value in NETWORK_IPS.items():
            if ip_value in content:
                placeholder_pattern = "${" + var_name + "}"
                if placeholder_pattern not in content:
                    violations.append(
                        base_file.relative_to(ROOT)
                    )
    
    assert not violations, (
        "Hardcoded IPs found in base manifests (violates DRY): "
        + ", ".join(str(v) for v in violations)
    )


def test_envoy_gateway_uses_gateway_ip_placeholder() -> None:
    """Verify envoy-gateway.yaml uses HPDC_GATEWAY_IP placeholder."""
    gateway_file = GITOPS / "envoy-gateway" / "base" / "envoy-gateway.yaml"
    if gateway_file.exists():
        content = gateway_file.read_text(encoding="utf-8")
        assert "${HPDC_GATEWAY_IP}" in content, (
            f"{gateway_file.relative_to(ROOT)} must use ${{HPDC_GATEWAY_IP}} placeholder"
        )


def test_cilium_lb_pool_uses_range_placeholder() -> None:
    """Verify cilium-loadbalancer-ippool.yaml uses HPDC_CILIUM_LB_POOL_RANGE placeholder."""
    lb_file = GITOPS / "cilium" / "base" / "cilium-loadbalancer-ippool.yaml"
    if lb_file.exists():
        content = lb_file.read_text(encoding="utf-8")
        assert "${HPDC_CILIUM_LB_POOL_RANGE}" in content, (
            f"{lb_file.relative_to(ROOT)} must use ${{HPDC_CILIUM_LB_POOL_RANGE}} placeholder"
        )