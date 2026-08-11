#!/usr/bin/env python3
"""Delete the local kind dev cluster (hpa-preview).

The HPDC dev/stage cluster is a kind cluster that accepts all production
(or staging) components. This script tears it down entirely via
`kind delete cluster` — the node container and all cluster state
(workloads, PVCs, configs) are destroyed.

Recreate later with the cluster's create command, e.g.:

    kind create cluster --name hpa-preview

Run modes (mirrors the project's install-* convention):
  --check   report whether the cluster exists (no changes)
  --dry-run show what would be deleted (no changes)
  --apply   actually delete the cluster
"""

from __future__ import annotations

import argparse
import subprocess
import sys

DEFAULT_NAME = "hpa-preview"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True)


def cluster_exists(name: str) -> bool:
    result = _run(["kind", "get", "clusters"])
    if result.returncode != 0:
        raise RuntimeError(f"kind unavailable: {result.stderr.strip() or result.stdout.strip()}")
    return name in result.stdout.split()


def check(name: str) -> int:
    if cluster_exists(name):
        print(f"kind cluster {name!r} exists.")
        return 0
    print(f"kind cluster {name!r} is not present.")
    return 0


def dry_run(name: str) -> int:
    if not cluster_exists(name):
        print(f"kind cluster {name!r} is not present; nothing to delete.")
        return 0
    print(f"Would delete kind cluster {name!r} and its node container "
          f"(`kind delete cluster --name {name}`). All cluster state is lost.")
    return 0


def apply(name: str) -> int:
    if not cluster_exists(name):
        print(f"kind cluster {name!r} is not present; nothing to delete.")
        return 0
    result = _run(["kind", "delete", "cluster", "--name", name])
    if result.returncode != 0:
        print(f"failed to delete cluster {name!r}: {result.stderr.strip() or result.stdout.strip()}")
        return 1
    if cluster_exists(name):
        print(f"kind cluster {name!r} still reported present after delete.")
        return 1
    print(f"kind cluster {name!r} deleted.")
    print(f"Recreate later with: kind create cluster --name {name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete the local kind dev cluster")
    parser.add_argument("--name", default=DEFAULT_NAME, help=f"kind cluster name (default: {DEFAULT_NAME})")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report cluster state, make no changes")
    mode.add_argument("--dry-run", action="store_true", help="show what would be deleted, make no changes")
    mode.add_argument("--apply", action="store_true", help="delete the cluster")
    args = parser.parse_args()

    try:
        if args.check:
            return check(args.name)
        if args.dry_run:
            return dry_run(args.name)
        return apply(args.name)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
