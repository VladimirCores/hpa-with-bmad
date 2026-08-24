#!/usr/bin/env python3
"""Install the HPDC Harbor offline registry from GitOps manifests."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
HARBOR_VERSION = "2.15.2"
HARBOR_IMAGE = ROOT / "output" / "harbor" / "images" / f"harbor-core-v{HARBOR_VERSION}"
TALOSCONFIG = ROOT / "output" / "talos" / "talosconfig"
ROOK_MARKER = ROOT / "output" / "rook-ceph" / "images" / f"rook-ceph-v1.20.6"
HARBOR_BASE = ROOT / "gitops" / "harbor" / "base"
HARBOR_OVERLAY = ROOT / "gitops" / "harbor" / "overlays" / "dev"


def ensure_dirs() -> None:
    for directory in (HARBOR_BASE, HARBOR_OVERLAY, HARBOR_IMAGE.parent):
        directory.mkdir(parents=True, exist_ok=True)


def ensure_offline_image_cache() -> None:
    required = [
        HARBOR_IMAGE,
        ROOT / "output" / "harbor" / "images" / f"registry-photon-v{HARBOR_VERSION}",
        ROOT / "output" / "harbor" / "images" / f"harbor-jobservice-v{HARBOR_VERSION}",
        ROOT / "output" / "harbor" / "images" / f"trivy-adapter-photon-v{HARBOR_VERSION}",
        ROOT / "output" / "harbor" / "images" / "redis-7.4-alpine",
        ROOT / "output" / "harbor" / "images" / "postgres-15.19-alpine",
    ]
    missing = [path for path in required if not path.exists()]
    if not missing:
        return
    raise RuntimeError(
        "Harbor offline image cache not found. Pre-cache Harbor 2.15.2 and supporting images before offline bootstrap: "
        f"{', '.join(str(path.relative_to(ROOT)) for path in missing)}"
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
        HARBOR_BASE / "harbor.yaml",
        HARBOR_BASE / "harbor-values.yaml",
        HARBOR_BASE / "harbor-pvcs.yaml",
        HARBOR_OVERLAY / "kustomization.yaml",
    ]
    for path in required_files:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    harbor = (HARBOR_BASE / "harbor.yaml").read_text(encoding="utf-8")
    values = (HARBOR_BASE / "harbor-values.yaml").read_text(encoding="utf-8")
    pvcs = (HARBOR_BASE / "harbor-pvcs.yaml").read_text(encoding="utf-8")
    overlay = (HARBOR_OVERLAY / "kustomization.yaml").read_text(encoding="utf-8")
    if f"goharbor/harbor-core:v{HARBOR_VERSION}" not in harbor:
        failures.append("harbor.yaml missing Harbor core image")
    if f"goharbor/registry-photon:v{HARBOR_VERSION}" not in harbor:
        failures.append("harbor.yaml missing Harbor registry image")
    if f"goharbor/trivy-adapter-photon:v{HARBOR_VERSION}" not in harbor:
        failures.append("harbor.yaml missing Harbor Trivy adapter image")
    if "trivy:" not in values or "enabled: true" not in values:
        failures.append("harbor-values.yaml missing Trivy scanning enabled:true")
    if "clair" not in values.lower():
        failures.append("harbor-values.yaml missing Clair scanning configuration")
    if "cosign" not in values.lower() and "signature" not in values.lower():
        failures.append("harbor-values.yaml missing Cosign/signature verification configuration")
    if "storageClassName: local-path" not in values and "storageClass: local-path" not in values:
        failures.append("harbor-values.yaml missing local-path storageClass")
    if "kind: PersistentVolumeClaim" not in pvcs:
        failures.append("harbor-pvcs.yaml missing PVCs")
    if "storageClassName: local-path" not in pvcs:
        failures.append("harbor-pvcs.yaml missing local-path PVC storageClass")
    if "../../base/harbor.yaml" not in overlay:
        failures.append("Harbor overlay missing harbor.yaml")
    if "../../base/harbor-values.yaml" in overlay:
        failures.append("Harbor overlay still lists harbor-values.yaml as a kustomize resource (AC 4: values source is not a resource)")
    if "kind: ConfigMap" not in harbor or "name: harbor-values" not in harbor or "harbor-values.yaml: |" not in harbor:
        failures.append("harbor.yaml missing the harbor-values ConfigMap values source")
    embed = next(
        (
            d
            for d in yaml.safe_load_all(harbor)
            if isinstance(d, dict)
            and d.get("kind") == "ConfigMap"
            and d.get("metadata", {}).get("name") == "harbor-values"
        ),
        None,
    )
    if embed is None:
        failures.append("harbor-values ConfigMap missing from harbor.yaml")
    elif yaml.safe_load(embed["data"]["harbor-values.yaml"]) != yaml.safe_load(values):
        failures.append(
            "harbor-values ConfigMap embed drifted from gitops/harbor/base/harbor-values.yaml (single source of truth)"
        )
    if "../../base/harbor-pvcs.yaml" not in overlay:
        failures.append("Harbor overlay missing harbor-pvcs.yaml")
    return failures


def run(command: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    result = subprocess.run(command, check=False, env=env)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


# Official Harbor Helm chart; chart 1.19.x tracks app 2.15.x.
HARBOR_CHART_VERSION = "1.19.2"
HARBOR_CHART_LOCAL = ROOT / "platform" / "charts" / f"harbor-{HARBOR_CHART_VERSION}.tgz"
HARBOR_HELM_VALUES: list[tuple[str, str]] = [
    ("expose.type", "clusterIP"),
    ("expose.tls.enabled", "false"),
    ("externalURL", "http://harbor.harbor.svc.cluster.local"),
    ("persistence.enabled", "true"),
    ("persistence.resourcePolicy", "keep"),
    ("persistence.persistentVolumeClaim.registry.storageClass", "local-path"),
    ("persistence.persistentVolumeClaim.registry.size", "20Gi"),
    ("persistence.persistentVolumeClaim.jobservice.storageClass", "local-path"),
    ("persistence.persistentVolumeClaim.jobservice.size", "5Gi"),
    ("persistence.persistentVolumeClaim.database.storageClass", "local-path"),
    ("persistence.persistentVolumeClaim.database.size", "5Gi"),
    ("persistence.persistentVolumeClaim.redis.storageClass", "local-path"),
    ("persistence.persistentVolumeClaim.redis.size", "2Gi"),
    ("persistence.persistentVolumeClaim.trivy.storageClass", "local-path"),
    ("persistence.persistentVolumeClaim.trivy.size", "10Gi"),
    # ChartMuseum was removed upstream in Harbor 2.x recent releases
    ("chartmuseum.enabled", "false"),
    ("trivy.enabled", "true"),
    ("harborAdminPassword", "HarborAdmin12345"),
    ("secretKey", "harbor-secretkey-for-offline-dev"),
]


def apply_manifests(args: argparse.Namespace) -> None:
    ensure_offline_image_cache()
    ensure_talosconfig()
    ensure_rook_ceph()
    kubectl = args.kubectl
    if shutil.which(kubectl) is None:
        raise RuntimeError(f"kubectl executable not found: {kubectl}")
    helm = args.helm
    if shutil.which(helm) is None:
        raise RuntimeError(f"helm executable not found: {helm}")
    env = os.environ.copy()
    env["TALOSCTL_OFFLINE_MODE"] = "1"

    vendored = HARBOR_CHART_LOCAL.exists()
    chart = str(HARBOR_CHART_LOCAL) if vendored else "harbor/harbor"
    cmd = [
        helm, "upgrade", "--install", "harbor", chart,
        "--namespace", "harbor",
        "--create-namespace",
    ]
    if not vendored:
        cmd.extend(["--version", HARBOR_CHART_VERSION])
    for key, value in HARBOR_HELM_VALUES:
        cmd.extend(["--set", f"{key}={value}"])
    run(cmd)

    run([kubectl, "rollout", "status", "deployment/harbor-core", "-n", "harbor", "--timeout=600s"], env=env)
    run([kubectl, "rollout", "status", "deployment/harbor-registry", "-n", "harbor", "--timeout=600s"], env=env)
    run([kubectl, "rollout", "status", "deployment/harbor-jobservice", "-n", "harbor", "--timeout=600s"], env=env)
    health = subprocess.run(
        [kubectl, "run", "harbor-health-check", "--rm", "-i", "--restart=Never",
         "--image=curlimages/curl:8.11.1", "-n", "harbor", "--quiet", "--",
         "curl", "-fsS", "http://harbor.harbor.svc.cluster.local/api/v2.0/health"],
        capture_output=True, text=True, check=False, env=env,
    )
    print(health.stdout.strip())
    if health.returncode != 0 or '"status":"healthy"' not in health.stdout:
        raise RuntimeError("Harbor health check failed after install")
    run([kubectl, "get", "service", "harbor", "-n", "harbor"], env=env)


def check_scaffold() -> list[str]:
    failures = []
    required = [
        ROOT / "scripts" / "startup.dev.py",
        ROOT / "scripts" / "steps" / "06-install-harbor-dev.py",
        ROOT / "docs" / "harbor-dev-registry.md",
        ROOT / "tests" / "test_install_harbor_dev.py",
    ]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC Harbor offline registry")
    parser.add_argument("--offline", action="store_true", default=True, help="require offline artifacts")
    parser.add_argument("--dry-run", action="store_true", help="validate and print commands without applying manifests")
    parser.add_argument("--check", action="store_true", help="validate required scaffold files without applying manifests")
    parser.add_argument("--apply", action="store_true", help="install Harbor via official Helm chart")
    parser.add_argument("--kubectl", default="kubectl", help="kubectl executable name")
    parser.add_argument("--helm", default="helm", help="helm executable name")
    args = parser.parse_args()

    if args.check:
        failures = check_scaffold()
        if failures:
            print("Harbor bootstrap scaffold validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        failures = validate_manifests()
        if failures:
            print("Harbor manifest validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("Harbor bootstrap scaffold validation passed.")
        return 0

    ensure_dirs()
    if args.offline:
        ensure_offline_image_cache()
    ensure_talosconfig()
    ensure_rook_ceph()
    failures = validate_manifests()
    if failures:
        print("Harbor manifest validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    if args.apply:
        apply_manifests(args)
        print("Harbor offline registry installation complete.")
        return 0

    if args.dry_run:
        print("Harbor offline registry dry-run passed.")
        print(f"Harbor version: {HARBOR_VERSION}")
        print(f"Harbor offline image cache: {HARBOR_IMAGE.relative_to(ROOT)}")
        print(f"Rook-Ceph cache: {ROOK_MARKER.relative_to(ROOT)}")
        print(f"Talos config: {TALOSCONFIG.relative_to(ROOT)}")
        print(f"GitOps overlay: {HARBOR_OVERLAY.relative_to(ROOT)}")
        return 0

    print("Harbor offline registry install requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
