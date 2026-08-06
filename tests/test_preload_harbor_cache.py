#!/usr/bin/env python3
"""Validate Harbor cache preload scaffolding."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from preload_harbor_cache import IMAGE_LIST, HARBOR_MARKER, load_image_records  # noqa: E402


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=check, capture_output=True, text=True)


def validate() -> None:
    assert (ROOT / "gitops/harbor/base/preload-images.yaml").read_text(encoding="utf-8").count("kind: ConfigMap") >= 1
    assert "offline-image-cache" in (ROOT / "gitops/harbor/base/preload-images.yaml").read_text(encoding="utf-8")
    assert "kind: Job" in (ROOT / "gitops/harbor/base/preload-images.yaml").read_text(encoding="utf-8")
    assert "docker:2.41-cli" in (ROOT / "gitops/harbor/base/preload-images.yaml").read_text(encoding="utf-8")
    assert (ROOT / "gitops/harbor/base/preload-images-job.yaml").read_text(encoding="utf-8").count("kind: ConfigMap") >= 1
    assert (ROOT / "gitops/harbor/overlays/preload/kustomization.yaml").read_text(encoding="utf-8").count("../../base/preload-images.yaml") >= 1
    assert (ROOT / "output/harbor/cache-images.txt").read_text(encoding="utf-8").count("\n") >= 6
    assert (ROOT / "output/harbor/images/harbor-core-v2.11.3").exists()


def test_dry_run_lists_images_and_expected_tags() -> None:
    result = run([sys.executable, str(SCRIPTS_DIR / "preload_harbor_cache.py"), "--offline", "--dry-run"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "harbor/harbor-core:v2.11.3 expected_tag=v2.11.3" in result.stdout
    assert "redis:7.2-alpine expected_tag=7.2-alpine" in result.stdout
    assert "target=harbor.local/harbor/harbor-core:v2.11.3" in result.stdout

    manifest = ROOT / "output" / "harbor" / "harbor-ingestion-manifest.yaml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "offline: true" in manifest_text
    assert "expected_tag: v2.11.3" in manifest_text
    assert "target: harbor.local/harbor/harbor-core:v2.11.3" in manifest_text


def test_check_mode_records_manifest() -> None:
    result = run([sys.executable, str(SCRIPTS_DIR / "preload_harbor_cache.py"), "--offline", "--check"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Preload Harbor cache validation passed." in result.stdout
    assert (ROOT / "output" / "harbor" / "harbor-ingestion-manifest.yaml").exists()


def test_missing_harbor_cache_marker_fails() -> None:
    marker = ROOT / HARBOR_MARKER.relative_to(ROOT)
    original = marker.read_text(encoding="utf-8")
    marker.unlink()
    try:
        result = run([sys.executable, str(SCRIPTS_DIR / "preload_harbor_cache.py"), "--offline", "--dry-run"], check=False)
    finally:
        marker.write_text(original)
    assert result.returncode != 0
    assert "Missing Harbor cache prerequisites" in result.stderr


def test_missing_image_list_fails() -> None:
    image_list = ROOT / IMAGE_LIST.relative_to(ROOT)
    original = image_list.read_text(encoding="utf-8")
    image_list.unlink()
    try:
        result = run([sys.executable, str(SCRIPTS_DIR / "preload_harbor_cache.py"), "--offline", "--dry-run"], check=False)
    finally:
        image_list.write_text(original)
    assert result.returncode != 0
    assert "Missing Harbor cache prerequisites" in result.stderr


def test_load_image_records_parses_expected_tags() -> None:
    records = load_image_records(ROOT)
    assert any(record.name == "harbor/harbor-core" and record.tag == "v2.11.3" for record in records)
    assert any(record.name == "redis" and record.tag == "7.2-alpine" for record in records)
    assert any(record.target == "harbor.local/harbor/harbor-core:v2.11.3" for record in records)


def main() -> int:
    validate()
    run([sys.executable, "startup.dev.py", "--offline", "--check", "--step", "07-preload-harbor-cache.py"])
    run([sys.executable, "startup.dev.py", "--offline", "--dry-run", "--step", "07-preload-harbor-cache.py"])
    test_dry_run_lists_images_and_expected_tags()
    test_check_mode_records_manifest()
    test_missing_harbor_cache_marker_fails()
    test_missing_image_list_fails()
    test_load_image_records_parses_expected_tags()
    print("Harbor cache preload validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
