#!/usr/bin/env python3
"""Shut down the HPDC dev cluster (kind or Talos/QEMU).

Detects which cluster type is running and tears it down cleanly:
  - kind clusters: `kind delete cluster`
  - Talos/QEMU clusters: `talosctl cluster destroy` + QEMU process cleanup

Persistent QEMU disk images (output/qemu/talos-v*.img) are preserved.
Use --cleanup to explicitly delete them.

Run modes (mirrors the project's install-* convention):
  --check   report whether any cluster exists (no changes)
  --dry-run show what would be deleted (no changes)
  --apply   actually delete the cluster(s)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TALOS_STATE_DIR = ROOT / "output" / "qemu"
TALOS_CLUSTER_NAME = "hpdc-talos"
KIND_CLUSTER_NAME = "hpa-preview"


def _run(args: list[str], *, check: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=check, env=env)


def _has_kind() -> bool:
    return shutil.which("kind") is not None


def _has_talosctl() -> bool:
    return shutil.which("talosctl") is not None


def kind_cluster_exists(name: str) -> bool:
    if not _has_kind():
        return False
    result = _run(["kind", "get", "clusters"])
    return name in result.stdout.split()


def talos_cluster_exists(name: str, state_dir: Path) -> bool:
    """Check if a Talos cluster exists (Docker or QEMU)."""
    if not _has_talosctl():
        return False

    # Check for Docker containers
    result = _run(["docker", "ps", "-a", "--filter", f"label=talos.cluster.name={name}", "--format", "{{.Names}}"])
    if result.returncode == 0 and result.stdout.strip():
        return True

    # Check if state directory exists (QEMU - stale or running)
    cluster_state = state_dir / name
    if cluster_state.exists():
        return True

    # Check talosctl cluster show
    result = _run(["talosctl", "cluster", "show", "--name", name])
    if result.returncode == 0:
        # Check for actual node entries
        lines = result.stdout.splitlines()
        for line in lines:
            if "controlplane" in line.lower() or "worker" in line.lower():
                return True

    return False


def kill_qemu_processes() -> int:
    """Kill any QEMU processes belonging to the Talos cluster."""
    result = _run(["pgrep", "-f", "qemu-system"])
    if result.returncode != 0:
        return 0  # no QEMU processes
    pids = result.stdout.strip().split()
    killed = 0
    for pid in pids:
        if not pid.isdigit():
            continue
        kill_result = _run(["kill", "-15", pid])  # SIGTERM
        if kill_result.returncode == 0:
            killed += 1
    return killed


def talos_destroy(name: str, state_dir: Path) -> int:
    """Destroy a Talos cluster (Docker or QEMU)."""
    talosctl = shutil.which("talosctl")
    if talosctl is None:
        print("talosctl not found; skipping Talos teardown.")
        return 0

    env = os.environ.copy()
    env["TALOSCTL_OFFLINE_MODE"] = "1"

    print(f"Destroying Talos cluster {name!r}...")
    result = _run([talosctl, "cluster", "destroy", "--name", name], env=env)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        print(f"Warning: talosctl cluster destroy returned non-zero: {stderr}")

    # Clean up Docker containers if they exist
    result = _run(["docker", "ps", "-a", "--filter", f"label=talos.cluster.name={name}", "--format", "{{.Names}}"])
    if result.returncode == 0 and result.stdout.strip():
        containers = result.stdout.strip().split("\n")
        for container in containers:
            if container:
                print(f"Removing container: {container}")
                _run(["docker", "rm", "-f", container])

    # Remove Docker network if it exists
    _run(["docker", "network", "rm", name])

    # Kill any remaining QEMU processes
    killed = kill_qemu_processes()
    if killed:
        print(f"Killed {killed} QEMU process(es).")

    # Remove cluster state directory (but preserve disk images)
    cluster_state = state_dir / name
    if cluster_state.exists():
        print(f"Removing cluster state: {cluster_state.relative_to(ROOT)}")
        result = _run(["sudo", "rm", "-rf", str(cluster_state)])
        if result.returncode != 0:
            print(f"Warning: could not remove cluster state: {result.stderr.strip()}")

    return 0


def check() -> int:
    kind_found = kind_cluster_exists(KIND_CLUSTER_NAME)
    talos_found = talos_cluster_exists(TALOS_CLUSTER_NAME, TALOS_STATE_DIR)

    if kind_found:
        print(f"kind cluster {KIND_CLUSTER_NAME!r} exists.")
    if talos_found:
        print(f"Talos cluster {TALOS_CLUSTER_NAME!r} exists.")
    if not kind_found and not talos_found:
        print("No dev cluster running (kind or Talos/QEMU).")
    return 0


def dry_run() -> int:
    kind_found = kind_cluster_exists(KIND_CLUSTER_NAME)
    talos_found = talos_cluster_exists(TALOS_CLUSTER_NAME, TALOS_STATE_DIR)

    if kind_found:
        print(f"Would delete kind cluster {KIND_CLUSTER_NAME!r} "
              f"(`kind delete cluster --name {KIND_CLUSTER_NAME}`).")
    if talos_found:
        print(f"Would destroy Talos cluster {TALOS_CLUSTER_NAME!r} "
              f"(`talosctl cluster destroy --name {TALOS_CLUSTER_NAME} "
              f"--state {TALOS_STATE_DIR}`).")
        print(f"Would kill any remaining QEMU processes.")
        print(f"Persistent disk images in {TALOS_STATE_DIR} would be preserved.")
    if not kind_found and not talos_found:
        print("No dev cluster running; nothing to delete.")
    return 0


def apply(cleanup_disks: bool) -> int:
    kind_found = kind_cluster_exists(KIND_CLUSTER_NAME)
    talos_found = talos_cluster_exists(TALOS_CLUSTER_NAME, TALOS_STATE_DIR)

    if not kind_found and not talos_found:
        print("No dev cluster running; nothing to delete.")
        return 0

    errors = 0

    # Tear down kind cluster
    if kind_found:
        print(f"Deleting kind cluster {KIND_CLUSTER_NAME!r}...")
        result = _run(["kind", "delete", "cluster", "--name", KIND_CLUSTER_NAME])
        if result.returncode != 0:
            print(f"Failed to delete kind cluster: {result.stderr.strip() or result.stdout.strip()}")
            errors += 1
        else:
            print(f"kind cluster {KIND_CLUSTER_NAME!r} deleted.")

    # Tear down Talos/QEMU cluster
    if talos_found:
        rc = talos_destroy(TALOS_CLUSTER_NAME, TALOS_STATE_DIR)
        if rc != 0:
            errors += 1
        else:
            print(f"Talos cluster {TALOS_CLUSTER_NAME!r} destroyed.")

    # Optionally clean up persistent disk images
    if cleanup_disks:
        for img in TALOS_STATE_DIR.glob("talos-v*.img"):
            print(f"Removing persistent disk: {img.relative_to(ROOT)}")
            img.unlink()
        print("Persistent disk images removed.")
    else:
        print(f"Persistent disk images preserved in {TALOS_STATE_DIR.relative_to(ROOT)}/")

    if errors:
        return 1
    print("Dev cluster teardown complete.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Shut down the HPDC dev cluster (kind or Talos/QEMU)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report cluster state, make no changes")
    mode.add_argument("--dry-run", action="store_true", help="show what would be deleted, no changes")
    mode.add_argument("--apply", action="store_true", help="delete the cluster(s)")
    parser.add_argument("--cleanup", action="store_true",
                        help="also delete persistent QEMU disk images (default: preserve)")
    args = parser.parse_args()

    try:
        if args.check:
            return check()
        if args.dry_run:
            return dry_run()
        return apply(args.cleanup)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
