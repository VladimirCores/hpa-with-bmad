#!/usr/bin/env python3
"""Validate offline GitOps pipeline scaffolding."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def validate() -> None:
    required = [
        "gitops/harbor/base/harbor.yaml",
        "gitops/harbor/base/harbor-values.yaml",
        "gitops/harbor/base/harbor-pvcs.yaml",
        "gitops/harbor/base/preload-images.yaml",
        "gitops/harbor/base/preload-images-job.yaml",
        "gitops/harbor/base/image-cache-refresh.yaml",
        "gitops/git/base/git-mirror.yaml",
        "gitops/spegel/base/spegel.yaml",
        "gitops/kargo/base/kargo.yaml",
        "gitops/argo-cd/base/argocd.yaml",
        "gitops/argo-rollouts/base/argorollouts.yaml",
        "gitops/argo-events/base/argoevents.yaml",
        "gitops/envoy-gateway/base/envoy-gateway.yaml",
        "gitops/envoy-gateway/overlays/dev/kustomization.yaml",
        "gitops/cert-manager/base/cert-manager.yaml",
        "gitops/cert-manager/overlays/dev/kustomization.yaml",
        "output/harbor/cache-images.txt",
        "output/harbor/image-cache-metadata.yaml",
        "output/git/mirror-repositories.txt",
        "output/spegel/images/spegel-v0.4.0",
        "output/kargo/kargo-workspaces.txt",
        "output/argo-cd/applicationsets.txt",
        "output/argo-rollouts/rollouts.txt",
        "output/argo-events/events.txt",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert not missing, missing
    assert "kind: Rollout" in (ROOT / "gitops/argo-rollouts/base/argorollouts.yaml").read_text(encoding="utf-8")
    assert "kind: Workflow" in (ROOT / "gitops/argo-events/base/argoevents.yaml").read_text(encoding="utf-8")
    assert "kind: HTTPRoute" in (ROOT / "gitops/envoy-gateway/base/envoy-gateway.yaml").read_text(encoding="utf-8")
    assert "kind: Certificate" in (ROOT / "gitops/cert-manager/base/cert-manager.yaml").read_text(encoding="utf-8")


def main() -> int:
    validate()
    run([sys.executable, "startup.dev.py", "--offline", "--dry-run", "--step", "15-validate-offline-gitops-pipeline.py"])
    print("Offline GitOps pipeline validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
