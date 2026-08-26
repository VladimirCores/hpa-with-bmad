#!/usr/bin/env python3
"""Validate offline GitOps pipeline scaffolding."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from _provisioned import record  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts" / "gitops"))
import component_versions  # noqa: E402

component_versions.load_dotenv()
SPEGEL_VERSION = component_versions.get("HPDC_SPEGEL_VERSION")
ARGOCD_VERSION = component_versions.get("HPDC_ARGOCD_VERSION")
KARGO_VERSION = component_versions.get("HPDC_KARGO_VERSION")
HARBOR_VERSION = component_versions.get("HPDC_HARBOR_VERSION")

PROVISIONED_COMPONENTS = ["git-mirror", "kargo", "argocd", "argo-rollouts", "argo-events"]


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
        f"output/spegel/images/spegel-v{SPEGEL_VERSION}",
        f"output/argocd/images/argocd-v{ARGOCD_VERSION}",
        f"output/kargo/images/kargo-v{KARGO_VERSION}",
        "output/argo-rollouts/images/argo-rollouts-v1.9.1",
        "output/argo-events/images/argo-events-v1.9.11",
        "output/provisioned.yaml",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert not missing, missing

    data = yaml.safe_load((ROOT / "output/provisioned.yaml").read_text(encoding="utf-8"))
    provisioned = data["provisioned"]
    assert set(PROVISIONED_COMPONENTS) <= set(provisioned), "provisioned.yaml missing components"
    for component in PROVISIONED_COMPONENTS:
        assert provisioned[component].get("value"), f"provisioned.yaml: {component} has no value"
    assert provisioned["argocd"].get("version") == ARGOCD_VERSION
    assert provisioned["kargo"].get("version") == KARGO_VERSION
    assert provisioned["argo-rollouts"].get("version") == "1.9.1"
    assert provisioned["argo-events"].get("version") == "1.9.11"
    images = (record("harbor-image-cache") or {}).get("images") or []
    assert any(image.get("name") == f"harbor/harbor-core:v{HARBOR_VERSION}" for image in images), "provisioned.yaml: harbor-image-cache missing core"
    assert "kind: Rollout" in (ROOT / "gitops/argo-rollouts/base/argorollouts.yaml").read_text(encoding="utf-8")
    assert "kind: Workflow" in (ROOT / "gitops/argo-events/base/argoevents.yaml").read_text(encoding="utf-8")
    assert "kind: HTTPRoute" in (ROOT / "gitops/envoy-gateway/base/envoy-gateway.yaml").read_text(encoding="utf-8")
    assert "kind: Certificate" in (ROOT / "gitops/cert-manager/base/cert-manager.yaml").read_text(encoding="utf-8")


def main() -> int:
    validate()
    run([sys.executable, "scripts/startup.dev.py", "--offline", "--dry-run", "--step", "15-validate-offline-gitops-pipeline.py"])
    print("Offline GitOps pipeline validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
