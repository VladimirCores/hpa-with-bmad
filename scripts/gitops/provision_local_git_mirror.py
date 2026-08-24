#!/usr/bin/env python3
"""Provision a local Git mirror for offline GitOps."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from _provisioned import require, value

ROOT = Path(__file__).resolve().parents[2]
GIT_BASE = ROOT / "gitops" / "git" / "base"
GIT_OVERLAY = ROOT / "gitops" / "git" / "overlays" / "dev"
MIRROR_LOG = ROOT / "output" / "git-mirror.log"
MIRROR_PORT = 9418
MIRROR_DIR = Path.home() / ".local" / "share" / "hpdc-git-mirror"
BARE_REPO = MIRROR_DIR / f"{ROOT.name}.git"
# Nodes reach the host over the Talos docker bridge gateway.
NODE_REPO_URL = f"http://10.6.0.1:{MIRROR_PORT}/{BARE_REPO.name}"


def ensure_files() -> None:
    require("git-mirror")


def validate_manifests() -> list[str]:
    failures = []
    required = [GIT_BASE / "git-mirror.yaml", GIT_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    mirror = (GIT_BASE / "git-mirror.yaml").read_text(encoding="utf-8")
    if "kind: Deployment" not in mirror or "name: git-mirror" not in mirror:
        failures.append("git-mirror.yaml missing Git mirror Deployment")
    if "alpine/git:2.45.2" not in mirror:
        failures.append("git-mirror.yaml missing Git image")
    if "storageClassName: rook-ceph-rbd" not in mirror:
        failures.append("git-mirror.yaml missing Rook-Ceph PVC storageClass")
    return failures


def _ls_remote(url: str) -> bool:
    result = subprocess.run(
        ["git", "ls-remote", url, "HEAD"],
        capture_output=True, text=True, check=False,
    )
    return result.returncode == 0


def refresh_bare_mirror() -> None:
    """Clone/update a bare mirror of this repository for dumb-HTTP serving."""
    if BARE_REPO.exists():
        subprocess.run(
            ["git", "fetch", "--all", "--prune"],
            cwd=BARE_REPO, capture_output=True, text=True, check=False,
        )
    else:
        MIRROR_DIR.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", "--bare", str(ROOT), str(BARE_REPO)],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"bare mirror clone failed: {result.stderr.strip()}")
    # Expose refs/packs for the dumb-HTTP protocol.
    subprocess.run(
        ["git", "update-server-info"],
        cwd=BARE_REPO, capture_output=True, text=True, check=False,
    )


def serve_mirror() -> None:
    """Serve the bare mirror over HTTP (stdlib only); idempotent."""
    local_url = f"http://127.0.0.1:{MIRROR_PORT}/{BARE_REPO.name}"
    if _ls_remote(local_url):
        print(f"mirror already served at {local_url}")
        return

    MIRROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with MIRROR_LOG.open("a", encoding="utf-8") as log:
        subprocess.Popen(
            ["python3", "-m", "http.server", str(MIRROR_PORT), "--bind", "0.0.0.0"],
            cwd=MIRROR_DIR,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )

    for _ in range(30):
        time.sleep(1)
        if _ls_remote(local_url):
            print(f"git mirror served at {NODE_REPO_URL} (log: {MIRROR_LOG.relative_to(ROOT)})")
            return
    raise RuntimeError(
        f"git mirror did not become ready on port {MIRROR_PORT}; inspect {MIRROR_LOG.relative_to(ROOT)}"
    )


def point_argocd_at_mirror(repo_url: str) -> None:
    """Point the argocd-cm repositories list at the host mirror."""
    kubectl = sys.executable and "kubectl"
    patch = (
        '{"data":{"repositories":"- url: ' + repo_url + '\\n  type: git\\n  name: hpdc-git-mirror\\n"}}'
    )
    subprocess.run(
        ["kubectl", "patch", "cm", "argocd-cm", "-n", "argocd",
         "--type=merge", "-p", patch],
        capture_output=True, text=True, check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision local Git mirror for offline GitOps")
    parser.add_argument("--offline", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.check:
        ensure_files()
        failures = validate_manifests()
        if failures:
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("Local Git mirror validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        refresh_bare_mirror()
        serve_mirror()
        point_argocd_at_mirror(NODE_REPO_URL)
        print("Local Git mirror ready; ArgoCD pointed at the offline source.")
        return 0
    if args.dry_run:
        repos = [repo for repo in (value("git-mirror") or "").splitlines() if repo]
        print("Local Git mirror dry-run passed.")
        print(f"Repositories mirrored: {len(repos)}")
        for repo in repos:
            print(f"- {repo}")
        print(f"GitOps overlay: {GIT_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Local Git mirror requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
