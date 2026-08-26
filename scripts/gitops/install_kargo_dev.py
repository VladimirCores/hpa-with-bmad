#!/usr/bin/env python3
"""Install Kargo Warehouse, Stage, and Freight promotion."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from _provisioned import require
import component_versions

component_versions.load_dotenv()
ROOT = Path(__file__).resolve().parents[2]
KARGO_VERSION = component_versions.get("HPDC_KARGO_VERSION")
KARGO_IMAGE = ROOT / "output" / "kargo" / "images" / f"kargo-v{KARGO_VERSION}"
KARGO_BASE = ROOT / "gitops" / "kargo" / "base"
KARGO_OVERLAY = ROOT / "gitops" / "kargo" / "overlays" / "dev"


def ensure_files() -> None:
    require("kargo")
    if not KARGO_IMAGE.exists():
        raise RuntimeError(
            f"Kargo offline image cache marker not found. Pre-cache Kargo v{KARGO_VERSION} before offline bootstrap: "
            f"{KARGO_IMAGE.relative_to(ROOT)}"
        )


def validate_manifests() -> list[str]:
    failures = []
    required = [KARGO_BASE / "kargo.yaml", KARGO_OVERLAY / "kustomization.yaml"]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(ROOT)))
    kargo = (KARGO_BASE / "kargo.yaml").read_text(encoding="utf-8")
    if "kind: Warehouse" not in kargo or "name: offline-gitops" not in kargo:
        failures.append("kargo.yaml missing Warehouse")
    if "kind: Stage" not in kargo or "name: dev" not in kargo:
        failures.append("kargo.yaml missing Stage")
    if "kind: Freight" not in kargo or "name: offline-dev" not in kargo:
        failures.append("kargo.yaml missing Freight")
    if "git://git-mirror/git-mirror" not in kargo:
        failures.append("kargo.yaml missing local Git mirror repoURL")
    if "kind: Deployment" not in kargo or "name: kargo-controller" not in kargo:
        failures.append("kargo.yaml missing kargo-controller Deployment")
    if f"ghcr.io/akuity/kargo:v{KARGO_VERSION}" not in kargo:
        failures.append(f"kargo.yaml missing Kargo v{KARGO_VERSION} image")
    if "kind: ServiceAccount" not in kargo or "name: kargo-controller" not in kargo:
        failures.append("kargo.yaml missing kargo-controller ServiceAccount")
    return failures


def run(command: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> int:
    print("$", " ".join(command))
    result = subprocess.run(command, check=False, env=env)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result.returncode


# Official Kargo chart (OCI); chart 1.11.x tracks app 1.11.x. Requires
# cert-manager CRDs for its internal Certificate/Issuer resources.
KARGO_CHART_VERSION = component_versions.get("HPDC_KARGO_CHART_VERSION")
KARGO_OCI_CHART = "oci://ghcr.io/akuity/kargo-charts/kargo"
KARGO_CHART_LOCAL = ROOT / "platform" / "charts" / f"kargo-{KARGO_CHART_VERSION}.tgz"
CERT_MANAGER_CHART_VERSION = component_versions.get("HPDC_CERT_MANAGER_CHART_VERSION")
CERT_MANAGER_CHART_LOCAL = ROOT / "platform" / "charts" / f"cert-manager-{CERT_MANAGER_CHART_VERSION}.tgz"


def apply_manifests() -> None:
    helm = shutil.which("helm")
    if helm is None:
        raise RuntimeError("helm is required for Kargo install")
    kubectl = shutil.which("kubectl")
    if kubectl is None:
        raise RuntimeError("kubectl is required for Kargo install")

    # cert-manager is a hard prerequisite of the Kargo chart
    cm_vendored = CERT_MANAGER_CHART_LOCAL.exists()
    cm_chart = str(CERT_MANAGER_CHART_LOCAL) if cm_vendored else "jetstack/cert-manager"
    cm_cmd = [helm, "upgrade", "--install", "cert-manager", cm_chart,
              "--namespace", "cert-manager", "--create-namespace"]
    if not cm_vendored:
        cm_cmd.extend(["--version", CERT_MANAGER_CHART_VERSION])
    cm_cmd.extend(["--set", "crds.enabled=true"])
    run(cm_cmd)
    run([kubectl, "wait", "--for=condition=Available", "deploy/cert-manager",
         "-n", "cert-manager", "--timeout=300s"])

    # Dev admin account: password 'admin' (bcrypt), throwaway signing key
    kargo_vendored = KARGO_CHART_LOCAL.exists()
    kargo_chart = str(KARGO_CHART_LOCAL) if kargo_vendored else KARGO_OCI_CHART
    kargo_cmd = [helm, "upgrade", "--install", "kargo", kargo_chart,
                 "--namespace", "kargo", "--create-namespace"]
    if not kargo_vendored:
        kargo_cmd.extend(["--version", KARGO_CHART_VERSION])
    kargo_cmd.extend([
        "--set", f"image.tag=v{KARGO_VERSION}",
        "--set", "api.adminAccount.passwordHash=$2a$10$Zrhhie4vLz5ygtVSaif6o.qN36jgs6vjtMBdM6yrU1FOeiAAMMxOm",
        "--set", "api.adminAccount.tokenSigningKey=hpdc-dev-signing-key",
    ])
    run(kargo_cmd)
    run([kubectl, "rollout", "status", "deploy/kargo-controller", "-n", "kargo", "--timeout=600s"])
    run([kubectl, "rollout", "status", "deploy/kargo-api", "-n", "kargo", "--timeout=600s"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Kargo Warehouse, Stage, and Freight promotion")
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
        print("Kargo validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        apply_manifests()
        print("Kargo installation complete.")
        return 0
    if args.dry_run:
        print("Kargo dry-run passed.")
        print(f"Kargo version: {KARGO_VERSION}")
        print(f"Kargo image cache: {KARGO_IMAGE.relative_to(ROOT)}")
        print("Warehouse, Stage, and Freight are configured.")
        print(f"GitOps overlay: {KARGO_OVERLAY.relative_to(ROOT)}")
        return 0
    print("Kargo requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
