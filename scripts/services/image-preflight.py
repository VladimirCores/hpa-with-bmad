#!/usr/bin/env python3
"""Image preflight check and cache for HPDC dev cluster.

Scans all component image references, checks local availability,
pulls missing images (online mode), and loads them into the cluster.

Usage:
    python3 scripts/services/image-preflight.py --check          # Report missing images
    python3 scripts/services/image-preflight.py --pull           # Pull missing images
    python3 scripts/services/image-preflight.py --load           # Load images into cluster
    python3 scripts/services/image-preflight.py --pull --load    # Pull and load
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"

# ── Image Registry ──────────────────────────────────────────────────────────
# Maps component -> list of (image_ref, marker_path)
# marker_path is the file created after successful cache/load

IMAGES: dict[str, list[tuple[str, Path]]] = {
    # ── Core Infrastructure ──
    "cilium": [
        ("quay.io/cilium/cilium:v1.20.1", OUTPUT / "cilium" / "images" / "cilium-v1.20.1"),
        ("quay.io/cilium/operator-generic:v1.20.1", OUTPUT / "cilium" / "images" / "operator-generic-v1.20.1"),
        ("quay.io/cilium/hubble-ui:v0.13.5", OUTPUT / "cilium" / "images" / "hubble-ui-v0.13.5"),
        ("quay.io/cilium/cilium-envoy:v1.37.5-1786810558-766ccfb37260a43e9d228837aa84ce3faf9f64e7", OUTPUT / "cilium" / "images" / "cilium-envoy-v1.37.5"),
    ],
    "spire": [
        ("ghcr.io/spiffe/spire-server:1.15.3", OUTPUT / "cilium" / "images" / "spire-server-v1.15.3"),
        ("ghcr.io/spiffe/spire-agent:1.15.3", OUTPUT / "cilium" / "images" / "spire-agent-v1.15.3"),
    ],
    "harbor": [
        ("docker.io/goharbor/harbor-core:v2.15.2", OUTPUT / "harbor" / "images" / "harbor-core-v2.15.2"),
        ("docker.io/goharbor/registry-photon:v2.15.2", OUTPUT / "harbor" / "images" / "registry-photon-v2.15.2"),
        ("docker.io/goharbor/harbor-registryctl:v2.15.2", OUTPUT / "harbor" / "images" / "harbor-registryctl-v2.15.2"),
        ("docker.io/goharbor/harbor-jobservice:v2.15.2", OUTPUT / "harbor" / "images" / "harbor-jobservice-v2.15.2"),
        ("docker.io/goharbor/trivy-adapter-photon:v2.15.2", OUTPUT / "harbor" / "images" / "trivy-adapter-photon-v2.15.2"),
        ("redis:7.4-alpine", OUTPUT / "harbor" / "images" / "redis-7.4-alpine"),
        ("postgres:15.19-alpine", OUTPUT / "harbor" / "images" / "postgres-15.19-alpine"),
    ],
    "spegel": [
        ("ghcr.io/spegel-org/spegel:v0.7.4", OUTPUT / "spegel" / "images" / "spegel-v0.7.4"),
    ],
    "rook-ceph": [
        ("quay.io/rook/ceph:v1.20.6", OUTPUT / "rook-ceph" / "images" / "rook-ceph-v1.20.6"),
    ],

    # ── GitOps / CI/CD ──
    "argocd": [
        ("quay.io/argoproj/argocd:v3.5.1", OUTPUT / "argocd" / "images" / "argocd-v3.5.1"),
        ("docker.io/library/redis:8.2.8-alpine", OUTPUT / "argocd" / "images" / "redis-8.2.8-alpine"),
    ],
    "kargo": [
        ("ghcr.io/akuity/kargo:v1.11.1", OUTPUT / "kargo" / "images" / "kargo-v1.11.1"),
    ],
    "argo-rollouts": [
        ("quay.io/argoproj/argo-rollouts:v1.9.1", OUTPUT / "argo-rollouts" / "images" / "argo-rollouts-v1.9.1"),
    ],
    "argo-events": [
        ("quay.io/argoproj/argo-events:v1.9.11", OUTPUT / "argo-events" / "images" / "argo-events-v1.9.11"),
    ],

    # ── Edge / Gateway ──
    "envoy-gateway": [
        ("docker.io/envoyproxy/gateway:v1.9.0", OUTPUT / "envoy-gateway" / "images" / "envoy-gateway-v1.9.0"),
    ],
    "cert-manager": [
        ("quay.io/jetstack/cert-manager-controller:v1.21.1", OUTPUT / "cert-manager" / "images" / "cert-manager-controller-v1.21.1"),
        ("quay.io/jetstack/cert-manager-webhook:v1.21.1", OUTPUT / "cert-manager" / "images" / "cert-manager-webhook-v1.21.1"),
        ("quay.io/jetstack/cert-manager-cainjector:v1.21.1", OUTPUT / "cert-manager" / "images" / "cert-manager-cainjector-v1.21.1"),
    ],

    # ── Auth / Security ──
    "casdoor": [
        ("docker.io/casbin/casdoor:latest", OUTPUT / "casdoor" / "images" / "casdoor-latest"),
    ],
    "casbin": [
        # ext-authz is a custom image - must be built from source
    ],
    "infisical": [
        # infisical image pull times out - skip for now
    ],

    # ── Observability ──
    "grafana": [
        ("docker.io/grafana/grafana:13.2.0", OUTPUT / "grafana" / "images" / "grafana-v13.2.0"),
    ],
    "victoria-metrics": [
        ("victoriametrics/vmstorage:latest", OUTPUT / "victoria-metrics" / "images" / "vmstorage-latest"),
        ("victoriametrics/vminsert:latest", OUTPUT / "victoria-metrics" / "images" / "vminsert-latest"),
        ("victoriametrics/vmselect:latest", OUTPUT / "victoria-metrics" / "images" / "vmselect-latest"),
        ("victoriametrics/victoria-logs:latest", OUTPUT / "victoria-metrics" / "images" / "victoria-logs-latest"),
    ],
    "otel-collector": [
        ("otel/opentelemetry-collector-contrib:latest", OUTPUT / "victoria-metrics" / "images" / "otel-collector-latest"),
    ],
    "alertmanager": [
        ("prom/alertmanager:v0.34.0", OUTPUT / "monitoring" / "images" / "alertmanager-v0.34.0"),
    ],

    # ── Developer Portal ──
    "backstage": [
        ("ghcr.io/backstage/backstage:1.54.0", OUTPUT / "backstage" / "images" / "backstage-v1.54.0"),
    ],
    "swagger-ui": [
        ("docker.io/swaggerapi/swagger-ui:v5.32.14", OUTPUT / "openapi" / "images" / "swagger-ui-v5.32.14"),
    ],

    # ── Utilities ──
    "git-mirror": [
        ("alpine/git:2.54.0", OUTPUT / "git" / "images" / "git-mirror-v2.54.0"),
    ],
    "preload-job": [
        ("docker:29-cli", OUTPUT / "harbor" / "images" / "docker-29-cli"),
    ],
}

# Images that are custom-built (not pulled from a public registry)
CUSTOM_IMAGES = {
    "hpdc.local/graphql-gateway:0.1.0",
    "hpdc.local/entity-api:0.1.0",
    "hpdc.local/llm-decision-support:0.1.0",
    "hpdc.local/alert-handler:0.1.0",
    "ghcr.io/hpdc/regional-hub-spa:dev",
    "ghcr.io/hpdc/a2a-broker:dev",
    "ghcr.io/hpdc/mcp-server:dev",
}


@dataclass
class ImageStatus:
    image: str
    component: str
    marker_path: Path
    local_available: bool
    cached: bool


def check_docker_image(image: str) -> bool:
    """Check if an image exists in the local Docker daemon."""
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def check_images(components: list[str] | None = None) -> list[ImageStatus]:
    """Check status of all images for specified components (or all)."""
    statuses = []
    for component, image_list in IMAGES.items():
        if components and component not in components:
            continue
        for image_ref, marker_path in image_list:
            local = check_docker_image(image_ref)
            cached = marker_path.exists() and marker_path.stat().st_size > 100
            statuses.append(ImageStatus(
                image=image_ref,
                component=component,
                marker_path=marker_path,
                local_available=local,
                cached=cached,
            ))
    return statuses


def pull_image(image: str) -> bool:
    """Pull a single image. Returns True on success."""
    print(f"  Pulling {image}...")
    result = subprocess.run(
        ["docker", "pull", image],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  FAILED: {result.stderr.strip()}")
        return False
    print(f"  OK")
    return True


def save_marker(marker_path: Path, image_ref: str) -> None:
    """Write a marker file after successful pull/cache."""
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(f"{image_ref}\n", encoding="utf-8")


def pull_missing(statuses: list[ImageStatus], *, force: bool = False) -> int:
    """Pull images that aren't locally available. Returns count of failures."""
    failures = 0
    for status in statuses:
        if status.image in CUSTOM_IMAGES:
            print(f"  SKIP (custom): {status.image}")
            continue
        if status.local_available and not force:
            print(f"  EXISTS: {status.image}")
            continue
        if pull_image(status.image):
            save_marker(status.marker_path, status.image)
        else:
            failures += 1
    return failures


def load_image_to_talos(image: str, node_ip: str, endpoint: str, talosconfig: str) -> bool:
    """Load an image into a Talos node via talosctl image pull."""
    result = subprocess.run(
        [
            "sudo", "TALOSCONFIG", talosconfig,
            "talosctl", "image", "pull", image,
            "-n", node_ip, "-e", endpoint,
        ],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def load_images_to_cluster(statuses: list[ImageStatus], *, node_ip: str = "10.6.0.2") -> int:
    """Load cached images into the Talos cluster. Returns count of failures."""
    # Get Talos API endpoint
    result = subprocess.run(
        ["docker", "port", "hpdc-talos-controlplane-1", "50000"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("ERROR: Cannot determine Talos API endpoint")
        return len(statuses)

    endpoint = result.stdout.strip().split(" -> ")[1] if " -> " in result.stdout else ""
    if not endpoint:
        print("ERROR: Cannot parse Talos API endpoint")
        return len(statuses)

    talosconfig = str(OUTPUT / "talos" / "talosconfig")

    # Also try the user's kubeconfig context endpoint
    kubeconfig_result = subprocess.run(
        ["kubectl", "config", "view", "-o", "jsonpath={.clusters[?(@.name==\"hpdc-talos\")].cluster.server}"],
        capture_output=True, text=True,
    )

    failures = 0
    for status in statuses:
        if not status.local_available:
            print(f"  SKIP (not local): {status.image}")
            continue
        print(f"  Loading {status.image} into cluster...")
        if load_image_to_talos(status.image, node_ip, endpoint, talosconfig):
            save_marker(status.marker_path, status.image)
            print(f"  OK")
        else:
            print(f"  FAILED (will retry after Cilium installs)")
            failures += 1

    return failures


def print_report(statuses: list[ImageStatus]) -> None:
    """Print a summary report of image status."""
    total = len(statuses)
    local = sum(1 for s in statuses if s.local_available)
    cached = sum(1 for s in statuses if s.cached)
    missing = total - local

    print(f"\n{'='*60}")
    print(f"Image Preflight Report")
    print(f"{'='*60}")
    print(f"Total images:     {total}")
    print(f"Local available:  {local}")
    print(f"Cached markers:   {cached}")
    print(f"Missing:          {missing}")
    print(f"Custom (skip):    {len(CUSTOM_IMAGES)}")

    if missing > 0:
        print(f"\n{'─'*60}")
        print("Missing images:")
        for status in statuses:
            if not status.local_available:
                print(f"  [{status.component}] {status.image}")

    print(f"{'='*60}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="HPDC image preflight check and cache")
    parser.add_argument("--check", action="store_true", help="Report missing images")
    parser.add_argument("--pull", action="store_true", help="Pull missing images")
    parser.add_argument("--load", action="store_true", help="Load images into Talos cluster")
    parser.add_argument("--components", nargs="*", help="Limit to specific components")
    parser.add_argument("--force", action="store_true", help="Force re-pull even if local exists")
    args = parser.parse_args()

    if not (args.check or args.pull or args.load):
        args.check = True

    statuses = check_images(args.components)

    if args.check:
        print_report(statuses)

    if args.pull:
        print("\nPulling missing images...")
        failures = pull_missing(statuses, force=args.force)
        if failures:
            print(f"\n{failures} image(s) failed to pull")
            return 1
        print("\nAll images pulled successfully")

    if args.load:
        print("\nLoading images into cluster...")
        failures = load_images_to_cluster(statuses)
        if failures:
            print(f"\n{failures} image(s) failed to load")
            return 1
        print("\nAll images loaded successfully")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
