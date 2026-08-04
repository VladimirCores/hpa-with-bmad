#!/usr/bin/env python3
"""Bootstrap the HPDC monorepo scaffold.

The bootstrap is intentionally idempotent: it creates missing files and leaves
existing files untouched so reruns are safe.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRS = [
    ROOT / "gitops",
    ROOT / "platform",
    ROOT / "backend",
    ROOT / "specs",
    ROOT / "charts",
    ROOT / "docs",
    ROOT / "scripts",
    ROOT / "tests",
]

REQUIRED_FILES = {
    ROOT / "platform" / "talos" / "machine-config.yaml": """machine:
  install:
    disk: /dev/vda
    extraKernelArgs:
      - talos.platform=metal
  network:
    nameservers: []
  time:
    disabled: false
  kubelet:
    extraArgs:
      protect-kernel-defaults: "true"
  features:
    talos:
      cgroups:
        version: v2
""",
    ROOT / "gitops" / "platform" / "base" / "kustomization.yaml": """apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources: []
""",
    ROOT / "gitops" / "platform" / "overlays" / "dev" / "kustomization.yaml": """apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
namespace: hpdc-platform
commonLabels:
  environment: dev
""",
    ROOT / "gitops" / "platform" / "overlays" / "prod" / "kustomization.yaml": """apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
namespace: hpdc-platform
commonLabels:
  environment: prod
""",
    ROOT / "docs" / "bootstrap.md": """# HPDC Bootstrap

## Purpose

Bootstrap scaffolds the High Performance Distributed Cluster repository so the Talos substrate can be provisioned without manual setup or external dependencies.

## Required tooling

- Python 3
- `talosctl`
- QEMU

## Project-wide scripting rule

All project automation scripts must be written in Python 3. Shell wrappers are not allowed in the project `scripts/` directory.

## Bootstrap command

```python
scripts/bootstrap-dev.py
```

## Expected output

```text
HPDC scaffold created.
Required files:
- scripts/bootstrap-dev.py
- scripts/bootstrap_dev.py
- platform/talos/machine-config.yaml
- gitops/platform/base/kustomization.yaml
- gitops/platform/overlays/dev/kustomization.yaml
- gitops/platform/overlays/prod/kustomization.yaml
- docs/bootstrap.md
- tests/test_bootstrap_dev.py
```

## Next step

Run `scripts/bootstrap-dev.py` from Story 1.1, then continue with Story 1.2 to provision the offline Talos dev cluster.
""",
    ROOT / "README.md": """# High Performance Distributed Cluster (HPDC)

HPDC is an offline-first, security-focused distributed cluster scaffold for Talos, Cilium, and Rook-Ceph.

## Project-wide scripting rule

All project automation scripts must be written in Python 3. Shell wrappers are not allowed in the project `scripts/` directory.

## Bootstrap

Run:

```python
scripts/bootstrap-dev.py
```

Expected output:

```text
HPDC scaffold created.
```

The bootstrap command creates the standard monorepo layout and platform scaffold. Continue with Story 1.2 to provision the offline Talos dev cluster.
""",
    ROOT / "tests" / "test_bootstrap_dev.py": '''#!/usr/bin/env python3
"""Validate the HPDC bootstrap scaffold."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DIRS = [
    ROOT / "gitops",
    ROOT / "platform",
    ROOT / "backend",
    ROOT / "specs",
    ROOT / "charts",
    ROOT / "docs",
    ROOT / "scripts",
    ROOT / "tests",
]
REQUIRED_FILES = [
    ROOT / "scripts" / "bootstrap-dev.py",
    ROOT / "scripts" / "bootstrap_dev.py",
    ROOT / "platform" / "talos" / "machine-config.yaml",
    ROOT / "gitops" / "platform" / "base" / "kustomization.yaml",
    ROOT / "gitops" / "platform" / "overlays" / "dev" / "kustomization.yaml",
    ROOT / "gitops" / "platform" / "overlays" / "prod" / "kustomization.yaml",
    ROOT / "docs" / "bootstrap.md",
    ROOT / "README.md",
    ROOT / "tests" / "test_bootstrap_dev.py",
]

def main() -> int:
    failures = []
    for path in REQUIRED_DIRS:
        if not path.is_dir():
            failures.append(f"missing directory: {path.relative_to(ROOT)}")
    for path in REQUIRED_FILES:
        if not path.is_file():
            failures.append(f"missing file: {path.relative_to(ROOT)}")
    if failures:
        print("HPDC scaffold validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("HPDC scaffold validation passed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
''',
}


def ensure_dirs() -> None:
    for directory in REQUIRED_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    path.write_text(content, encoding="utf-8")


def ensure_script_mode(path: Path) -> None:
    path.chmod(path.stat().st_mode | 0o111)


def validate() -> list[str]:
    failures = []
    for directory in REQUIRED_DIRS:
        if not directory.is_dir():
            failures.append(str(directory.relative_to(ROOT)))
    for path in REQUIRED_FILES:
        if not path.is_file():
            failures.append(str(path.relative_to(ROOT)))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap HPDC repository scaffold")
    parser.add_argument("--check", action="store_true", help="validate required scaffold files without creating them")
    args = parser.parse_args()

    if args.check:
        failures = validate()
        if failures:
            print("HPDC scaffold validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("HPDC scaffold validation passed.")
        return 0

    ensure_dirs()
    for path, content in REQUIRED_FILES.items():
        write_file(path, content)
    ensure_script_mode(ROOT / "scripts" / "bootstrap-dev.py")
    ensure_script_mode(ROOT / "scripts" / "bootstrap_dev.py")

    print("HPDC scaffold created.")
    print("Required files:")
    for path in REQUIRED_FILES:
        print(f"- {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
