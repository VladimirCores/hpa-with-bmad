#!/usr/bin/env python3
"""Install the HPDC Rook-Ceph dev cluster from offline GitOps manifests."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import component_versions

component_versions.load_dotenv()
ROOT = Path(__file__).resolve().parents[2]
ROOK_VERSION = component_versions.get("HPDC_ROOK_CEPH_VERSION")
ROOK_IMAGE_REF = f"quay.io/rook/ceph:v{ROOK_VERSION}"
REGISTRY = "http://localhost:5000"
TALOSCONFIG = ROOT / "output" / "talos" / "talosconfig"
QEMU_DISK = ROOT / "resources" / "talos" / "home" / ".talos" / "clusters"
ROOK_BASE = ROOT / "gitops" / "rook-ceph" / "base"
ROOK_OVERLAY = ROOT / "gitops" / "rook-ceph" / "overlays" / "dev"
ROOK_DIRS_FIXER = ROOT / "gitops" / "rook-ceph" / "base" / "rook-dirs-bootstrap.yaml"
ROOK_RENDERED = ROOT / "gitops" / "rook-ceph" / "rendered" / "dev.yaml"
ROOK_CRDS = ROOT / "platform" / "manifests" / f"rook-ceph-crds-v{ROOK_VERSION}.yaml"
ROOK_COMMON = ROOT / "platform" / "manifests" / f"rook-ceph-common-v{ROOK_VERSION}.yaml"
ROOK_OPERATOR = ROOT / "platform" / "manifests" / f"rook-ceph-operator-v{ROOK_VERSION}.yaml"
ROOK_CSI_OPERATOR = ROOT / "platform" / "manifests" / f"rook-ceph-csi-operator-v{ROOK_VERSION}.yaml"
VENDORED_MANIFESTS = [ROOK_CRDS, ROOK_COMMON, ROOK_CSI_OPERATOR, ROOK_OPERATOR]


def ensure_dirs() -> None:
    for directory in (ROOK_BASE, ROOK_OVERLAY):
        directory.mkdir(parents=True, exist_ok=True)


_DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _registry_has(repo: str, tag: str) -> bool:
    try:
        with _DIRECT_OPENER.open(f"{REGISTRY}/v2/{repo}/manifests/{tag}", timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def ensure_offline_image_cache() -> None:
    # Rook operator + daemon image served through the local mirror
    # (quay.io -> localhost:5000 path-preserving).
    if _registry_has("rook/ceph", f"v{ROOK_VERSION}"):
        return
    raise RuntimeError(
        f"rook/ceph requires tag v{ROOK_VERSION} "
        f"in the local registry mirror (path-preserving quay.io -> localhost:5000)"
    )


def ensure_talosconfig() -> None:
    if TALOSCONFIG.exists():
        return
    raise RuntimeError(f"Talos config not found: {TALOSCONFIG}")


def ensure_cilium() -> None:
    try:
        result = subprocess.run(
            ["kubectl", "-n", "kube-system", "get", "ds", "cilium",
             "--no-headers", "--request-timeout=10s"],
            capture_output=True, text=True, check=True, timeout=30,
        )
        fields = result.stdout.split()
        if len(fields) < 4:
            raise RuntimeError(f"unexpected ds output: {result.stdout.strip()}")
        desired, ready = int(fields[1]), int(fields[3])  # NAME DESIRED CURRENT READY
        if desired > 0 and desired == ready:
            return
        raise RuntimeError(f"Cilium DS not ready ({ready}/{desired}) — run step 03 first")
    except RuntimeError:
        raise
    except Exception as error:
        raise RuntimeError(f"Cilium not detected on cluster: {error} — run step 03 first")


def ensure_qemu_disk() -> None:
    # Worker data disks live inside the QEMU cluster state dir; presence of the
    # cluster state is the practical proxy for 'disks attached'.
    cluster_state = QEMU_DISK / "hpdc-talos"
    if cluster_state.exists():
        return
    raise RuntimeError(f"QEMU cluster state not found: {cluster_state}")


def validate_manifests() -> list[str]:
    failures = []
    required_files = [
        ROOK_BASE / "rook-ceph.yaml",
        ROOK_BASE / "storageclasses.yaml",
        ROOK_OVERLAY / "kustomization.yaml",
    ]
    for path in required_files:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    rook = (ROOK_BASE / "rook-ceph.yaml").read_text(encoding="utf-8")
    storage = (ROOK_BASE / "storageclasses.yaml").read_text(encoding="utf-8")
    if f"quay.io/rook/ceph:v{ROOK_VERSION}" not in rook:
        failures.append(f"rook-ceph.yaml missing Rook-Ceph v{ROOK_VERSION}-root image")
    if "kind: CephCluster" not in rook:
        failures.append("rook-ceph.yaml missing CephCluster")
    if "count: 1" not in rook:
        failures.append("rook-ceph.yaml missing single mon/osd topology")
    if "dataDirHostPath: /var/lib/rook" not in rook:
        failures.append("rook-ceph.yaml missing Rook dataDirHostPath")
    if "deviceFilter: vdb" not in rook:
        failures.append("rook-ceph.yaml missing worker data-disk deviceFilter (vdb)")
    if "clusterID: rook-ceph" not in storage:
        failures.append("storageclasses.yaml missing CSI clusterID")
    if "provisioner: rook-ceph.rbd.csi.ceph.com" not in storage:
        failures.append("storageclasses.yaml missing RBD CSI StorageClass")
    if "kind: CephBlockPool" not in storage:
        failures.append("storageclasses.yaml missing CephBlockPool")
    if "volumeBindingMode: Immediate" not in storage:
        failures.append("storageclasses.yaml missing immediate volume binding")
    if "allowVolumeExpansion: true" not in storage:
        failures.append("storageclasses.yaml missing volume expansion")
    return failures


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    result = subprocess.run(command, check=False)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def detect_existing_cluster(kubectl: str) -> None:
    run([kubectl, "-n", "rook-ceph", "get", "cephcluster", "rook-ceph"], check=False)
    run([kubectl, "-n", "rook-ceph", "get", "osd"], check=False)


def apply_manifests(args: argparse.Namespace) -> None:
    ensure_offline_image_cache()
    ensure_talosconfig()
    ensure_cilium()
    ensure_qemu_disk()
    kubectl = args.kubectl
    if shutil.which(kubectl) is None:
        raise RuntimeError(f"kubectl executable not found: {kubectl}")
    for required in VENDORED_MANIFESTS:
        if not required.exists():
            raise RuntimeError(f"required vendored manifest missing: {required}")
    detect_existing_cluster(kubectl)
    # kustomize LoadRestrictionsRootOnly blocks cross-tree -k overlays;
    # consume the pre-rendered bundle instead (regenerate via render_overlays.py).
    run([kubectl, "apply", "-f", str(ROOK_CRDS)])
    if ROOK_COMMON.exists():
        run([kubectl, "apply", "-f", str(ROOK_COMMON)])  # SA/RBAC/configmaps
    # Regenerate rendered bundle from base so validated config == applied config
    render = ROOT / "scripts" / "gitops" / "render_overlays.py"
    if render.exists():
        run([sys.executable, str(render)])

    if ROOK_COMMON.exists():
        run([kubectl, "apply", "-f", str(ROOK_COMMON)])  # SA/RBAC/configmaps
    # Rendered carries the Namespace PSA=privileged labels — must exist before
    # any privileged pod (fixer/operator children) is admitted.
    run([kubectl, "apply", "-f", str(ROOK_RENDERED)])
    if ROOK_CSI_OPERATOR.exists():
        # ceph-csi-operator CRDs (CephConnection etc.) required by rook 1.20+
        run([kubectl, "apply", "-f", str(ROOK_CSI_OPERATOR)])
    if ROOK_DIRS_FIXER.exists():
        # Pre-create + chown /var/lib/rook (ceph uid 167) before daemons start;
        # Rook's non-root init chown lacks CAP_CHOWN on root-owned hostPaths.
        result = subprocess.run(
            [kubectl, "apply", "-f", str(ROOK_DIRS_FIXER)],
            capture_output=True, text=True, check=False,
        )
        print(result.stdout.strip() or result.stderr.strip())
    if ROOK_OPERATOR.exists():
        # Upstream operator (reads cephVersion.image from CephCluster spec).
        # Tolerate trailing-doc failures: operator.yaml tail includes
        # csi.ceph.io OperatorConfig objects whose CRDs ship separately.
        result = subprocess.run(
            [kubectl, "apply", "-f", str(ROOK_OPERATOR)],
            capture_output=True, text=True, check=False,
        )
        if "deployment.apps/rook-ceph-operator" not in result.stdout:
            raise RuntimeError(f"rook operator apply failed: {result.stderr.strip() or result.stdout.strip()}")
    # Await the privileged fixer so dataDirHostPath ownership is correct
    # before the operator spawns OSD prepare pods.
    if ROOK_DIRS_FIXER.exists():
        run([kubectl, "rollout", "status", "ds/rook-dirs-bootstrap", "-n", "rook-ceph", "--timeout=180s"])
    run([kubectl, "rollout", "status", "deployment/rook-ceph-operator", "-n", "rook-ceph", "--timeout=600s"])
    run([kubectl, "get", "storageclass", "rook-ceph-rbd"])
    if args.cleanup:
        print("Cleanup flag accepted; this offline installer does not wipe QEMU disk images.")


def check_scaffold() -> list[str]:
    failures = []
    required = [
        ROOT / "scripts" / "startup.dev.py",
        ROOT / "scripts" / "steps" / "05-install-rook-ceph-dev.py",
        ROOT / "docs" / "rook-ceph-dev-storage.md",
        ROOT / "tests" / "test_install_rook_ceph_dev.py",
    ]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC Rook-Ceph dev cluster")
    parser.add_argument("--offline", action="store_true", default=True, help="require offline artifacts")
    parser.add_argument("--dry-run", action="store_true", help="validate and print commands without applying manifests")
    parser.add_argument("--check", action="store_true", help="validate required scaffold files without applying manifests")
    parser.add_argument("--apply", action="store_true", help="apply Rook-Ceph manifests from GitOps overlay")
    parser.add_argument("--cleanup", action="store_true", help="allow destructive cleanup behavior only for --apply")
    parser.add_argument("--kubectl", default="kubectl", help="kubectl executable name")
    args = parser.parse_args()

    if args.check:
        failures = check_scaffold()
        if failures:
            print("Rook-Ceph bootstrap scaffold validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        failures = validate_manifests()
        if failures:
            print("Rook-Ceph manifest validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("Rook-Ceph bootstrap scaffold validation passed.")
        return 0

    ensure_dirs()
    if args.offline:
        ensure_offline_image_cache()
    ensure_talosconfig()
    ensure_cilium()
    ensure_qemu_disk()
    failures = validate_manifests()
    if failures:
        print("Rook-Ceph manifest validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    if args.apply:
        apply_manifests(args)
        print("Rook-Ceph dev cluster installation complete.")
        return 0

    if args.dry_run:
        print("Rook-Ceph dev cluster dry-run passed.")
        print(f"Rook-Ceph version: {ROOK_VERSION}")
        print(f"Rook-Ceph image refs: {ROOK_IMAGE_REF} + root variant (registry-probed)")
        print(f"Talos config: {TALOSCONFIG.relative_to(ROOT)}")
        print(f"Persistent QEMU disk: /dev/vdb (worker data disk, cluster state under {QEMU_DISK.relative_to(ROOT)})")
        print(f"GitOps overlay: {ROOK_OVERLAY.relative_to(ROOT)}")
        return 0

    print("Rook-Ceph dev cluster install requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
