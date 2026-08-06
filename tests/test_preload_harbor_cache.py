#!/usr/bin/env python3
"""Validate Harbor cache preload scaffolding."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from preload_harbor_cache import HARBOR_MARKER, IMAGE_LIST, load_image_records, target_for_image  # noqa: E402


def run(command: list[str], check: bool = True, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=check, capture_output=True, text=True)


def image_tags() -> list[tuple[str, str]]:
    records = []
    for line in (ROOT / "output" / "harbor" / "cache-images.txt").read_text(encoding="utf-8").splitlines():
        image = line.strip()
        if not image:
            continue
        name, tag = image.rsplit(":", 1)
        records.append((name, tag))
    return records


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
    for name, tag in image_tags():
        assert f"{name}:{tag} expected_tag={tag}" in result.stdout

    manifest = ROOT / "output" / "harbor" / "harbor-ingestion-manifest.yaml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "offline: true" in manifest_text
    for name, tag in image_tags():
        assert f"expected_tag: {tag}" in manifest_text
        assert f"target: {target_for_image(f'{name}:{tag}')}" in manifest_text


def test_check_mode_records_manifest() -> None:
    result = run([sys.executable, str(SCRIPTS_DIR / "preload_harbor_cache.py"), "--offline", "--check"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Preload Harbor cache validation passed." in result.stdout
    assert (ROOT / "output" / "harbor" / "harbor-ingestion-manifest.yaml").exists()


def test_missing_harbor_cache_marker_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        marker_dir = tmp_root / "output" / "harbor" / "images"
        marker_dir.mkdir(parents=True)
        (marker_dir / "redis-7.2-alpine").write_text("Redis offline image cache marker.", encoding="utf-8")
        (tmp_root / "output" / "harbor" / "cache-images.txt").write_text("redis:7.2-alpine\n", encoding="utf-8")
        result = run([sys.executable, str(SCRIPTS_DIR / "preload_harbor_cache.py"), "--offline", "--dry-run", "--root", str(tmp_root)], check=False, cwd=tmp_root)
    assert result.returncode != 0
    assert "output/harbor/images/harbor-core-v2.11.3" in result.stderr


def test_missing_image_list_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        marker_dir = tmp_root / "output" / "harbor" / "images"
        marker_dir.mkdir(parents=True)
        (marker_dir / "harbor-core-v2.11.3").write_text("Harbor offline image cache marker.", encoding="utf-8")
        result = run([sys.executable, str(SCRIPTS_DIR / "preload_harbor_cache.py"), "--offline", "--dry-run", "--root", str(tmp_root)], check=False, cwd=tmp_root)
    assert result.returncode != 0
    assert "output/harbor/cache-images.txt" in result.stderr


def test_load_image_records_parses_expected_tags() -> None:
    records = load_image_records(ROOT)
    assert [(record.name, record.tag) for record in records] == image_tags()
    assert records[0].target == "harbor.local/harbor/harbor-core:v2.11.3"
    assert records[-2].target == "harbor.local/library/redis:7.2-alpine"
    assert records[-1].target == "harbor.local/library/postgres:15-alpine"


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
