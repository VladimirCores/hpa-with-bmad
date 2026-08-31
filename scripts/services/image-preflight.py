#!/usr/bin/env python3
"""Image preflight check and cache for HPDC dev cluster.

Scans all component image references (derived from
scripts/gitops/component_versions.py — the single version catalog fed by
.env/.env.example), checks local availability AND presence in the offline
registry mirror, pulls missing images (online mode), and loads them into the
cluster. The mirror check is the version gate: nodes pull exclusively through
the mirror with skipFallback, so a tag absent there can only end in a silent
ImagePullBackOff later.

Usage:
    python3 scripts/services/image-preflight.py --check          # Report missing images + mirror gate
    python3 scripts/services/image-preflight.py --pull           # Pull missing images
    python3 scripts/services/image-preflight.py --load           # Load images into cluster
    python3 scripts/services/image-preflight.py --pull --load    # Pull and load
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"
MIRROR = "http://localhost:5000"

sys.path.insert(0, str(ROOT / "scripts" / "gitops"))
import component_versions  # noqa: E402

component_versions.load_all_dotenv()
component_versions.resolve()

# ── Image Registry ──────────────────────────────────────────────────────────
# Derived entirely from the component_versions catalog:
# Maps component -> list of (image_ref, marker_path)
# marker_path is the file created after successful cache/load

IMAGES: dict[str, list[tuple[str, Path]]] = {}
for _component, _ref in component_versions.image_refs():
    _marker = component_versions.marker_for(_ref.rsplit(":", 1)[0], _ref)
    if _marker is not None:
        IMAGES.setdefault(_component, []).append((_ref, _marker))

# Images that are custom-built (not pulled from a public registry)
CUSTOM_IMAGES = set(component_versions.CUSTOM_IMAGES)

_DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def mirror_repo_candidates(image_ref: str) -> list[str]:
    """Possible local-registry paths for an upstream ref (host prefix stripped).

    quay.io/argoproj/argocd:v1 -> [argoproj/argocd]
    docker.io/library/redis:X  -> [library/redis]
    victoriametrics/vmstorage  -> [victoriametrics/vmstorage]
    redis:7.4-alpine           -> [redis, library/redis]   (historical pushes vary)
    etcd:v3.6.12               -> [etcd, library/etcd]
    """
    ref = image_ref.split("@")[0]
    repo = ref.rpartition(":")[0]
    if "/" not in repo:
        return [repo, f"library/{repo}"]
    host, _, path = repo.partition("/")
    if "." not in host and ":" not in host and host != "localhost":
        return [f"{host}/{path}"]
    return [path]


def mirror_repo_path(image_ref: str) -> str:
    """Primary local-registry path for an upstream ref."""
    return mirror_repo_candidates(image_ref)[0]


@dataclass
class ImageStatus:
    image: str
    component: str
    marker_path: Path
    local_available: bool
    cached: bool
    mirrored: bool | None = None  # None = mirror unreachable / not checked


def check_docker_image(image: str) -> bool:
    """Check if an image exists in the local Docker daemon."""
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def check_mirror_tag(image_ref: str) -> bool | None:
    """True/False when the mirror answers; None when unreachable."""
    import urllib.error

    tag = image_ref.rsplit(":", 1)[-1].split("@")[0]
    saw_mirror = False
    for path in mirror_repo_candidates(image_ref):
        try:
            with _DIRECT_OPENER.open(f"{MIRROR}/v2/{path}/tags/list", timeout=5) as resp:
                saw_mirror = True
                if tag in (json.load(resp).get("tags") or []):
                    return True
        except urllib.error.HTTPError:
            # 404 NAME_UNKNOWN etc.: mirror answered — repo/tag genuinely absent
            saw_mirror = True
        except Exception:
            continue
    return None if not saw_mirror else False


def remediation_for(image_ref: str) -> str:
    path = mirror_repo_path(image_ref) or ""
    tag = image_ref.split("@")[0].rsplit(":", 1)[-1]
    return (
        f"skopeo copy --all docker://{image_ref} docker://localhost:5000/{path}:{tag}"
        f"   (or: python3 scripts/services/mirror-image.py {image_ref} {path}:{tag})"
    )


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
                mirrored=check_mirror_tag(image_ref),
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
        if status.mirrored and not status.local_available:
            # Mirror-only conventions (e.g. rook's -root variant) have no
            # upstream tag; the mirror already serves what nodes need.
            print(f"  IN-MIRROR (no upstream tag): {status.image}")
            save_marker(status.marker_path, status.image)
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
    mirror_unknown = [s for s in statuses if s.mirrored is None]
    not_mirrored = [s for s in statuses if s.mirrored is False and s.image not in CUSTOM_IMAGES]

    print(f"\n{'='*60}")
    print(f"Image Preflight Report")
    print(f"{'='*60}")
    print(f"Total images:     {total}")
    print(f"Local available:  {local}")
    print(f"Cached markers:   {cached}")
    print(f"Missing (host):   {missing}")
    print(f"Not in mirror:    {len(not_mirrored)}")
    print(f"Custom (skip):    {len(CUSTOM_IMAGES)}")

    if missing > 0:
        print(f"\n{'─'*60}")
        print("Missing images (host docker):")
        for status in statuses:
            if not status.local_available:
                print(f"  [{status.component}] {status.image}")

    if not_mirrored:
        print(f"\n{'─'*60}")
        print("VERSION GATE — tags absent from the offline mirror")
        print("(nodes pull ONLY via localhost:5000 with skipFallback; these WILL fail):")
        for status in not_mirrored:
            print(f"  [{status.component}] {status.image}")
            print(f"      fix: {remediation_for(status.image)}")

    if mirror_unknown:
        print(f"\nNOTE: registry mirror unreachable — mirror gate skipped "
              f"for {len(mirror_unknown)} image(s). Start hpa-local-registry before bootstrap.")

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

    exit_code = 0

    if args.check:
        print_report(statuses)
        blocked = [
            s for s in statuses
            if s.mirrored is False and s.image not in CUSTOM_IMAGES
        ]
        if blocked:
            print(f"VERSION GATE: {len(blocked)} catalogued image(s) missing from the offline mirror. "
                  f"Fill them (commands above) before bootstrap — nodes cannot fall back to the internet.")
            exit_code = 1

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

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
