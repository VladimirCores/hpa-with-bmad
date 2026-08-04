#!/usr/bin/env python3
"""Install the HPDC Cilium mTLS service mesh from offline GitOps manifests."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CILIUM_VERSION = "1.19.6"
SPIRE_VERSION = "1.9.6"
CILIUM_IMAGE = ROOT / "output" / "cilium" / "images" / f"cilium-agent-v{CILIUM_VERSION}"
SPIRE_AGENT_IMAGE = ROOT / "output" / "cilium" / "images" / f"spire-agent-v{SPIRE_VERSION}"
SPIRE_SERVER_IMAGE = ROOT / "output" / "cilium" / "images" / f"spire-server-v{SPIRE_VERSION}"
TALOSCONFIG = ROOT / "output" / "talos" / "talosconfig"
ROOK_MARKER = ROOT / "output" / "rook-ceph" / "images" / f"rook-ceph-v1.20.3"
CILIUM_MTLS_BASE = ROOT / "gitops" / "cilium" / "base"
CILIUM_MTLS_OVERLAY = ROOT / "gitops" / "cilium" / "overlays" / "mesh"


def ensure_dirs() -> None:
    for directory in (CILIUM_MTLS_BASE, CILIUM_MTLS_OVERLAY, CILIUM_IMAGE.parent, SPIRE_AGENT_IMAGE.parent, SPIRE_SERVER_IMAGE.parent):
        directory.mkdir(parents=True, exist_ok=True)


def ensure_offline_image_cache() -> None:
    required = [CILIUM_IMAGE, SPIRE_AGENT_IMAGE, SPIRE_SERVER_IMAGE]
    missing = [path for path in required if not path.exists()]
    if not missing:
        return
    raise RuntimeError(
        "Cilium mTLS offline image cache not found. Pre-cache Cilium 1.19.6 and SPIRE "
        f"{SPIRE_VERSION} images before offline bootstrap: {', '.join(str(path.relative_to(ROOT)) for path in missing)}"
    )


def ensure_talosconfig() -> None:
    if TALOSCONFIG.exists():
        return
    raise RuntimeError(f"Talos config not found: {TALOSCONFIG}")


def ensure_rook_ceph() -> None:
    if ROOK_MARKER.exists():
        return
    raise RuntimeError(f"Rook-Ceph offline image cache not found: {ROOK_MARKER}")


def validate_manifests() -> list[str]:
    failures = []
    required_files = [
        CILIUM_MTLS_BASE / "cilium-mtls.yaml",
        CILIUM_MTLS_BASE / "cilium-mtls-test.yaml",
        CILIUM_MTLS_OVERLAY / "kustomization.yaml",
    ]
    for path in required_files:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    cilium = (CILIUM_MTLS_BASE / "cilium-mtls.yaml").read_text(encoding="utf-8")
    test = (CILIUM_MTLS_BASE / "cilium-mtls-test.yaml").read_text(encoding="utf-8")
    overlay = (CILIUM_MTLS_OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")
    if "kind: Cilium" not in cilium:
        failures.append("cilium-mtls.yaml missing Cilium resource")
    if "authentication:" not in cilium or "enabled: true" not in cilium:
        failures.append("cilium-mtls.yaml missing authentication.enabled:true")
    if "mutual:" not in cilium or "enabled: true" not in cilium:
        failures.append("cilium-mtls.yaml missing mutual authentication.enabled:true")
    if "spire:" not in cilium or "enabled: true" not in cilium:
        failures.append("cilium-mtls.yaml missing spire.enabled:true")
    if "serverAddress: spire-server.cilium-spire.svc:8081" not in cilium:
        failures.append("cilium-mtls.yaml missing SPIRE server address")
    if "agentSocketPath: /run/spire/sockets/agent/agent.sock" not in cilium:
        failures.append("cilium-mtls.yaml missing SPIRE agent socket path")
    if "kind: StatefulSet" not in cilium or "name: spire-server" not in cilium:
        failures.append("cilium-mtls.yaml missing SPIRE server StatefulSet")
    if "kind: DaemonSet" not in cilium or "name: spire-agent" not in cilium:
        failures.append("cilium-mtls.yaml missing SPIRE agent DaemonSet")
    if "ghcr.io/spiffe/spire-server:v1.9.6" not in cilium:
        failures.append("cilium-mtls.yaml missing SPIRE server image")
    if "ghcr.io/spiffe/spire-agent:v1.9.6" not in cilium:
        failures.append("cilium-mtls.yaml missing SPIRE agent image")
    if "storageClassName: rook-ceph-rbd" not in cilium:
        failures.append("cilium-mtls.yaml missing Rook-Ceph RBD volume for SPIRE server")
    if "mtls-server" not in test or "mtls-client" not in test:
        failures.append("cilium-mtls-test.yaml missing mTLS test services")
    if "curl -fsS http://mtls-server.hpdc-mtls-test.svc.cluster.local/" not in test:
        failures.append("cilium-mtls-test.yaml missing HTTP service-to-service request")
    if "../../base/cilium-mtls.yaml" not in overlay:
        failures.append("mesh overlay missing cilium-mtls.yaml")
    if "../../base/cilium-mtls-test.yaml" not in overlay:
        failures.append("mesh overlay missing cilium-mtls-test.yaml")
    return failures


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    result = subprocess.run(command, check=False)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def apply_manifests(args: argparse.Namespace) -> None:
    ensure_offline_image_cache()
    ensure_talosconfig()
    ensure_rook_ceph()
    kubectl = args.kubectl
    if shutil.which(kubectl) is None:
        raise RuntimeError(f"kubectl executable not found: {kubectl}")
    env = os.environ.copy()
    env["TALOSCTL_OFFLINE_MODE"] = "1"
    run([kubectl, "apply", "-k", str(CILIUM_MTLS_OVERLAY)], env=env)
    run([kubectl, "rollout", "status", "daemonset/spire-agent", "-n", "cilium-spire"], env=env)
    run([kubectl, "rollout", "status", "statefulset/spire-server", "-n", "cilium-spire"], env=env)
    run([kubectl, "rollout", "status", "deployment/mtls-server", "-n", "hpdc-mtls-test"], env=env)
    run([kubectl, "rollout", "status", "deployment/mtls-client", "-n", "hpdc-mtls-test"], env=env)
    run([kubectl, "get", "service", "spire-server", "-n", "cilium-spire"], env=env)


def check_scaffold() -> list[str]:
    failures = []
    required = [
        ROOT / "scripts" / "install-cilium-mtls-dev.py",
        ROOT / "docs" / "cilium-mtls-service-mesh.md",
        ROOT / "tests" / "test_install_cilium_mtls_dev.py",
    ]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC Cilium mTLS service mesh")
    parser.add_argument("--offline", action="store_true", default=True, help="require offline artifacts")
    parser.add_argument("--dry-run", action="store_true", help="validate and print commands without applying manifests")
    parser.add_argument("--check", action="store_true", help="validate required scaffold files without applying manifests")
    parser.add_argument("--apply", action="store_true", help="apply Cilium mTLS manifests from GitOps overlay")
    parser.add_argument("--kubectl", default="kubectl", help="kubectl executable name")
    args = parser.parse_args()

    if args.check:
        failures = check_scaffold()
        if failures:
            print("Cilium mTLS bootstrap scaffold validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        failures = validate_manifests()
        if failures:
            print("Cilium mTLS manifest validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("Cilium mTLS bootstrap scaffold validation passed.")
        return 0

    ensure_dirs()
    if args.offline:
        ensure_offline_image_cache()
    ensure_talosconfig()
    ensure_rook_ceph()
    failures = validate_manifests()
    if failures:
        print("Cilium mTLS manifest validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    if args.apply:
        apply_manifests(args)
        print("Cilium mTLS service mesh installation complete.")
        return 0

    if args.dry_run:
        print("Cilium mTLS service mesh dry-run passed.")
        print(f"Cilium version: {CILIUM_VERSION}")
        print(f"SPIRE version: {SPIRE_VERSION}")
        print(f"Cilium offline image cache: {CILIUM_IMAGE.relative_to(ROOT)}")
        print(f"SPIRE agent offline image cache: {SPIRE_AGENT_IMAGE.relative_to(ROOT)}")
        print(f"SPIRE server offline image cache: {SPIRE_SERVER_IMAGE.relative_to(ROOT)}")
        print(f"Rook-Ceph cache: {ROOK_MARKER.relative_to(ROOT)}")
        print(f"Talos config: {TALOSCONFIG.relative_to(ROOT)}")
        print(f"GitOps overlay: {CILIUM_MTLS_OVERLAY.relative_to(ROOT)}")
        return 0

    print("Cilium mTLS service mesh install requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
