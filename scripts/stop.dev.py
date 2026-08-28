#!/usr/bin/env python3
"""Shut down the HPDC dev cluster (kind or Talos/QEMU).

Detects which cluster type is running and tears it down cleanly:
  - kind clusters: `kind delete cluster`
  - Talos/QEMU clusters: `talosctl cluster destroy` + QEMU process cleanup

All Talos runtime assets live inside the project under resources/ (gitignored):
ISO cache, CNI bundle, registry data, git mirror — these SURVIVE teardown.
VM state/disks are intentionally ephemeral: each destroy wipes them and the
next startup re-provisions from cache (~75s). Use --cleanup to also
remove leftover VM disk images.

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
TALOS_HOME = ROOT / "resources" / "talos" / "home"
TALOS_STATE_DIR = TALOS_HOME / ".talos" / "clusters"
# Short symlink for cluster commands — QEMU unix sockets must stay <108 chars.
TALOS_STATE_LINK = ROOT / "talos-state"
CLUSTER_NAME = "hpdc-talos"
TALOS_CLUSTER_NAME = CLUSTER_NAME
KIND_CLUSTER_NAME = CLUSTER_NAME


def _talos_env() -> dict[str, str]:
    """HOME pinned to resources/talos/home so talosctl sees project-local state."""
    import os
    env = os.environ.copy()
    env["HOME"] = str(TALOS_HOME)
    return env


def _run(args: list[str], *, check: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=check, env=env)


def _has_docker() -> bool:
    return shutil.which("docker") is not None


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
    if _has_docker():
        result = _run(["docker", "ps", "-a", "--filter", f"label=talos.cluster.name={name}", "--format", "{{.Names}}"])
        if result.returncode == 0 and result.stdout.strip():
            return True

    # Check if state directory exists (QEMU - stale or running)
    cluster_state = state_dir / name
    if cluster_state.exists():
        return True

    # Check talosctl cluster show (project-local HOME/state)
    result = _run(["talosctl", "cluster", "show", "--name", name, "--state", str(TALOS_STATE_LINK)], env=_talos_env())
    if result.returncode == 0:
        # Check for actual node entries
        lines = result.stdout.splitlines()
        for line in lines:
            if "controlplane" in line.lower() or "worker" in line.lower():
                return True

    return False


def kill_cluster_qemu() -> int:
    """SIGTERM only QEMU processes referencing this cluster's state path."""
    killed = 0
    seen = set()
    root = str(ROOT)
    for marker in (f"qemu-system.*{root}/talos-state/{TALOS_CLUSTER_NAME}",
                   f"qemu-system.*clusters/{TALOS_CLUSTER_NAME}"):
        result = _run(["pgrep", "-f", marker])
        if result.returncode != 0:
            continue
        for pid in result.stdout.split():
            if not pid.isdigit() or pid in seen:
                continue
            seen.add(pid)
            if _run(["sudo", "-n", "kill", "-15", pid]).returncode == 0:
                killed += 1
    if len(seen) > killed:
        print(f"Warning: {len(seen)-killed} QEMU process(es) could not be signalled "
              "(sudo -n unavailable?)", file=__import__('sys').stderr)
    return killed


def talos_destroy(name: str, state_dir: Path) -> int:
    """Destroy a Talos cluster (Docker or QEMU)."""
    talosctl = shutil.which("talosctl")
    if talosctl is None:
        print("talosctl not found; skipping Talos teardown.")
        return 0

    env = _talos_env()
    env["TALOSCTL_OFFLINE_MODE"] = "1"

    print(f"Destroying Talos cluster {name!r}...")
    result = _run([talosctl, "cluster", "destroy", "--name", name, "--state", str(TALOS_STATE_LINK)], env=env)
    if result.returncode != 0:
        # Non-zero is common on benign tail steps (e.g. bridge already gone after
        # reboot). Success is judged by actual QEMU process death below.
        print(f"Note: talosctl destroy rc={result.returncode}: "
              f"{(result.stderr or result.stdout).strip().splitlines()[-1][:120]}")

    # Clean up Docker containers if they exist
    if not _has_docker():
        return 0
    result = _run(["docker", "ps", "-a", "--filter", f"label=talos.cluster.name={name}", "--format", "{{.Names}}"])
    if result.returncode == 0 and result.stdout.strip():
        containers = result.stdout.strip().split("\n")
        for container in containers:
            if container:
                print(f"Removing container: {container}")
                _run(["docker", "rm", "-f", container])

    # Remove Docker network if it exists
    _run(["docker", "network", "rm", name])

    # Kill any remaining QEMU processes; their death is the real success signal
    killed = kill_cluster_qemu()
    if killed:
        print(f"Killed {killed} QEMU process(es).")
    elif _run(["pgrep", "-f", f"qemu-system.*clusters/{name}"]).returncode == 0:
        print("ERROR: QEMU processes still alive after destroy.", file=sys.stderr)
        return 1

    # Remove leftover cluster state directory (disks included; registry data,
    # ISO cache, and CNI bundle live outside the cluster lifecycle and persist)
    cluster_state = state_dir / name
    if cluster_state.exists():
        print(f"Removing cluster state: {cluster_state.relative_to(ROOT)}")
        result = _run(["sudo", "-n", "rm", "-rf", str(cluster_state)])
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
              f"--state {TALOS_STATE_LINK}`).")
        print(f"Would kill any remaining QEMU processes.")
        print("Project resources under resources/ (registry, ISO cache, git mirror) would be preserved.")
    if not kind_found and not talos_found:
        print("No dev cluster running; nothing to delete.")
    return 0


def apply(cleanup_disks: bool) -> int:
    kind_found = kind_cluster_exists(KIND_CLUSTER_NAME)
    talos_found = talos_cluster_exists(TALOS_CLUSTER_NAME, TALOS_STATE_DIR)

    errors = 0
    if not kind_found and not talos_found:
        print("No dev cluster running; nothing to delete.")
        killed = kill_cluster_qemu()
        if killed:
            print(f"Swept {killed} orphaned cluster QEMU process(es).")

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
            print("Teardown reported failure — inspect output above.", file=sys.stderr)
        else:
            print(f"Talos cluster {TALOS_CLUSTER_NAME!r} destroyed.")

    # Persistent project resources (registry data, ISO cache, CNI bundle,
    # git mirror) live under resources/ outside the cluster lifecycle and
    # survive teardown. --cleanup removes any leftover VM disk images too.
    if cleanup_disks:
        for disk in TALOS_STATE_DIR.rglob("*"):
            if disk.suffix in {".img", ".disk"} and disk.is_file():
                print(f"Removing persistent disk: {disk.relative_to(ROOT)}")
                _run(["sudo", "-n", "rm", "-f", str(disk)])
        print("Leftover VM disk images removed.")
    else:
        print(f"Project resources preserved under resources/ (registry, ISO cache, git mirror).")

    # Always sweep stray QEMU processes (covers orphaned VMs whose state dir
    # was already removed by a prior partial teardown).
    killed = kill_cluster_qemu()
    if killed:
        print(f"Swept {killed} orphaned QEMU process(es).")

    # NOTE: the 'talos' firewalld zone is host infrastructure (like the docker
    # daemon) — created by step 01.5, intentionally NOT removed on teardown so
    # the next startup can reach freshly booted nodes immediately.

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
