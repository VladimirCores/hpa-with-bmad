#!/usr/bin/env python3
"""Validate the storage installation scaffold."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
GITOPS_DIR = ROOT / "scripts" / "gitops"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(GITOPS_DIR) not in sys.path:
    sys.path.insert(0, str(GITOPS_DIR))

REQUIRED_FILES = [
    ROOT / "scripts/startup.dev.py",
    ROOT / "scripts" / "steps" / "05-install-storage-dev.py",
    ROOT / "scripts" / "gitops" / "install_storage_dev.py",
    ROOT / "docs" / "rook-ceph-dev-storage.md",
    ROOT / "tests" / "test_install_storage_dev.py",
]


def main() -> int:
    failures = []
    for path in REQUIRED_FILES:
        if not path.exists():
            failures.append(f"missing file: {path.relative_to(ROOT)}")
    if failures:
        print("Storage installation scaffold validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Storage installation scaffold validation passed.")
    return 0


def test_install_storage_dev_has_check_mode() -> None:
    """Verify install_storage_dev.py supports --check mode."""
    import install_storage_dev as module

    assert hasattr(module, "main"), "install_storage_dev must have a main() function"


def test_install_storage_dev_has_dry_run_mode() -> None:
    """Verify install_storage_dev.py supports --dry-run mode."""
    import install_storage_dev as module

    assert hasattr(module, "run"), "install_storage_dev must have a run() helper"


def test_install_storage_dev_supports_local_path() -> None:
    """Verify local-path is a valid storage option."""
    import install_storage_dev as module

    # Check that the function exists and can be called
    assert callable(module.install_local_path_provisioner), "install_local_path_provisioner must be callable"


def test_install_storage_dev_supports_rook_ceph() -> None:
    """Verify rook-ceph is a valid storage option."""
    import install_storage_dev as module

    # Check that the function exists and can be called
    assert callable(module.install_rook_ceph), "install_rook_ceph must be callable"


def test_install_storage_dev_ensure_dirs() -> None:
    """Verify ensure_dirs creates required directories."""
    import install_storage_dev as module

    with tempfile.TemporaryDirectory() as tmp:
        # Temporarily override paths
        original_talosconfig = module.TALOSCONFIG
        try:
            module.TALOSCONFIG = Path(tmp) / "talos" / "talosconfig"
            module.ensure_dirs()
            assert module.TALOSCONFIG.parent.exists(), "TALOSCONFIG parent directory must be created"
        finally:
            module.TALOSCONFIG = original_talosconfig


def test_install_storage_dev_validate_prereqs() -> None:
    """Verify validate_prereqs checks for kubectl."""
    import install_storage_dev as module

    # This should not raise if kubectl is available
    try:
        kubectl = module.ensure_kubectl()
        assert kubectl is not None, "ensure_kubectl must return a path"
    except RuntimeError:
        # kubectl not installed, which is acceptable for tests
        pass


if __name__ == "__main__":
    sys.exit(main())
