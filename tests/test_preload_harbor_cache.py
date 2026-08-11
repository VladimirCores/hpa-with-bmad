#!/usr/bin/env python3
"""Validate Harbor cache metadata scaffolding."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
GITOPS_DIR = SCRIPTS_DIR / "gitops"
for entry in (SCRIPTS_DIR, GITOPS_DIR):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from preload_harbor_cache import load_image_records, split_image_name, target_for_image  # noqa: E402


def run(command: list[str], check: bool = True, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=check, capture_output=True, text=True)


def image_tags() -> list[tuple[str, str]]:
    records = []
    for line in (ROOT / "output" / "harbor" / "cache-images.txt").read_text(encoding="utf-8").splitlines():
        image = line.strip()
        if not image:
            continue
        name, tag = split_image_name(image)
        records.append((name, tag))
    return records


def test_split_image_name_accepts_harbor_repo_path() -> None:
    assert split_image_name("harbor/harbor-core:v2.11.3") == ("harbor/harbor-core", "v2.11.3")


def test_split_image_name_accepts_digest_only_reference() -> None:
    digest = "sha256:" + "a" * 64
    assert split_image_name(f"redis@{digest}") == ("redis", digest)


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
    manifest = ROOT / "output" / "harbor" / "harbor-ingestion-manifest.yaml"
    before_mtime = manifest.stat().st_mtime_ns
    result = run([sys.executable, str(GITOPS_DIR / "preload_harbor_cache.py"), "--offline", "--dry-run"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert manifest.stat().st_mtime_ns == before_mtime

    manifest_text = manifest.read_text(encoding="utf-8")
    for name, tag in image_tags():
        assert f"{name}:{tag} expected_tag={tag}" in result.stdout
        assert f"source: \"output/harbor/images/{name.rsplit('/', 1)[-1].replace(':', '-')}-{tag}\"" in manifest_text

    assert "offline: true" in manifest_text
    for name, tag in image_tags():
        assert f"expected_tag: \"{tag}\"" in manifest_text
        assert f"target: \"{target_for_image(f'{name}:{tag}')}\"" in manifest_text


def test_check_mode_records_manifest() -> None:
    result = run([sys.executable, str(GITOPS_DIR / "preload_harbor_cache.py"), "--offline", "--check"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Preload Harbor cache validation passed." in result.stdout
    manifest = ROOT / "output" / "harbor" / "harbor-ingestion-manifest.yaml"
    assert manifest.exists()
    manifest_text = manifest.read_text(encoding="utf-8")
    for name, tag in image_tags():
        assert f"source: \"output/harbor/images/{name.rsplit('/', 1)[-1].replace(':', '-')}-{tag}\"" in manifest_text
        assert f"expected_tag: \"{tag}\"" in manifest_text
        assert f"target: \"{target_for_image(f'{name}:{tag}')}\"" in manifest_text


def test_apply_mode_records_manifest() -> None:
    result = run([sys.executable, str(GITOPS_DIR / "preload_harbor_cache.py"), "--offline", "--apply"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Harbor ingestion manifest recorded." in result.stdout
    manifest_text = (ROOT / "output" / "harbor" / "harbor-ingestion-manifest.yaml").read_text(encoding="utf-8")
    for name, tag in image_tags():
        assert f"target: \"{target_for_image(f'{name}:{tag}')}\"" in manifest_text


def test_cli_requires_offline_and_single_mode() -> None:
    missing_offline = run([sys.executable, str(GITOPS_DIR / "preload_harbor_cache.py"), "--dry-run"], check=False)
    assert missing_offline.returncode != 0
    assert "--offline is required" in missing_offline.stderr

    multiple_modes = run(
        [sys.executable, str(GITOPS_DIR / "preload_harbor_cache.py"), "--offline", "--dry-run", "--check"],
        check=False,
    )
    assert multiple_modes.returncode != 0
    assert "Specify exactly one" in multiple_modes.stderr


def test_load_image_records_accepts_custom_root() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        marker_dir = tmp_root / "output" / "harbor" / "images"
        marker_dir.mkdir(parents=True)
        (marker_dir / "harbor-core-v2.11.3").write_text("Harbor offline image cache marker.", encoding="utf-8")
        (marker_dir / "redis-7.2-alpine").write_text("Redis offline image cache marker.", encoding="utf-8")
        (tmp_root / "output" / "harbor" / "cache-images.txt").write_text("redis:7.2-alpine\n", encoding="utf-8")
        records = load_image_records(tmp_root)
    assert [(record.name, record.tag) for record in records] == [("redis", "7.2-alpine")]
    assert records[0].source == tmp_root / "output" / "harbor" / "images" / "redis-7.2-alpine"
    assert records[0].target == "harbor.local/library/redis:7.2-alpine"


def test_load_image_records_rejects_missing_source_marker() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        marker_dir = tmp_root / "output" / "harbor" / "images"
        marker_dir.mkdir(parents=True)
        (marker_dir / "harbor-core-v2.11.3").write_text("Harbor offline image cache marker.", encoding="utf-8")
        (tmp_root / "output" / "harbor" / "cache-images.txt").write_text("redis:7.2-alpine\n", encoding="utf-8")
        try:
            load_image_records(tmp_root)
        except RuntimeError as error:
            assert "redis-7.2-alpine" in str(error)
        else:
            raise AssertionError("missing source marker should fail")


def test_load_image_records_rejects_missing_tag() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        marker_dir = tmp_root / "output" / "harbor" / "images"
        marker_dir.mkdir(parents=True)
        (marker_dir / "harbor-core-v2.11.3").write_text("Harbor offline image cache marker.", encoding="utf-8")
        (tmp_root / "output" / "harbor" / "cache-images.txt").write_text("redis\n", encoding="utf-8")
        try:
            load_image_records(tmp_root)
        except ValueError as error:
            assert "must include a tag or digest" in str(error)
        else:
            raise AssertionError("missing tag should fail")


def test_load_image_records_rejects_empty_tag() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        marker_dir = tmp_root / "output" / "harbor" / "images"
        marker_dir.mkdir(parents=True)
        (marker_dir / "harbor-core-v2.11.3").write_text("Harbor offline image cache marker.", encoding="utf-8")
        (tmp_root / "output" / "harbor" / "cache-images.txt").write_text("redis:\n", encoding="utf-8")
        try:
            load_image_records(tmp_root)
        except ValueError as error:
            assert "invalid image reference" in str(error)
        else:
            raise AssertionError("empty tag should fail")


def test_load_image_records_skips_empty_and_comments() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        marker_dir = tmp_root / "output" / "harbor" / "images"
        marker_dir.mkdir(parents=True)
        (marker_dir / "harbor-core-v2.11.3").write_text("Harbor offline image cache marker.", encoding="utf-8")
        (marker_dir / "redis-7.2-alpine").write_text("Redis offline image cache marker.", encoding="utf-8")
        (tmp_root / "output" / "harbor" / "cache-images.txt").write_text("\n# comment\nredis:7.2-alpine\n", encoding="utf-8")
        records = load_image_records(tmp_root)
    assert [(record.name, record.tag) for record in records] == [("redis", "7.2-alpine")]


def test_load_image_records_accepts_empty_cache_list() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        marker_dir = tmp_root / "output" / "harbor" / "images"
        marker_dir.mkdir(parents=True)
        (marker_dir / "harbor-core-v2.11.3").write_text("Harbor offline image cache marker.", encoding="utf-8")
        (tmp_root / "output" / "harbor" / "cache-images.txt").write_text("", encoding="utf-8")
        records = load_image_records(tmp_root)
    assert records == []


def test_missing_harbor_cache_marker_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        marker_dir = tmp_root / "output" / "harbor" / "images"
        marker_dir.mkdir(parents=True)
        (marker_dir / "redis-7.2-alpine").write_text("Redis offline image cache marker.", encoding="utf-8")
        (tmp_root / "output" / "harbor" / "cache-images.txt").write_text("redis:7.2-alpine\n", encoding="utf-8")
        result = run([sys.executable, str(GITOPS_DIR / "preload_harbor_cache.py"), "--offline", "--dry-run", "--root", str(tmp_root)], check=False, cwd=tmp_root)
    assert result.returncode != 0
    assert "output/harbor/images/harbor-core-v2.11.3" in result.stderr


def test_missing_image_list_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        marker_dir = tmp_root / "output" / "harbor" / "images"
        marker_dir.mkdir(parents=True)
        (marker_dir / "harbor-core-v2.11.3").write_text("Harbor offline image cache marker.", encoding="utf-8")
        result = run([sys.executable, str(GITOPS_DIR / "preload_harbor_cache.py"), "--offline", "--dry-run", "--root", str(tmp_root)], check=False, cwd=tmp_root)
    assert result.returncode != 0
    assert "output/harbor/cache-images.txt" in result.stderr


def test_load_image_records_parses_expected_tags() -> None:
    records = load_image_records(ROOT)
    assert [(record.name, record.tag) for record in records] == image_tags()
    for record, (name, tag) in zip(records, image_tags()):
        assert record.target == target_for_image(f"{name}:{tag}")
    assert records[0].target == "harbor.local/harbor/harbor-core:v2.11.3"
    assert records[-2].target == "harbor.local/library/redis:7.2-alpine"
    assert records[-1].target == "harbor.local/library/postgres:15-alpine"


def main() -> int:
    validate()
    run([sys.executable, "scripts/startup.dev.py", "--offline", "--check", "--step", "07-preload-harbor-cache.py"])
    run([sys.executable, "scripts/startup.dev.py", "--offline", "--dry-run", "--step", "07-preload-harbor-cache.py"])
    test_split_image_name_accepts_harbor_repo_path()
    test_split_image_name_accepts_digest_only_reference()
    test_dry_run_lists_images_and_expected_tags()
    test_check_mode_records_manifest()
    test_apply_mode_records_manifest()
    test_cli_requires_offline_and_single_mode()
    test_load_image_records_accepts_custom_root()
    test_load_image_records_rejects_missing_source_marker()
    test_load_image_records_rejects_missing_tag()
    test_load_image_records_rejects_empty_tag()
    test_load_image_records_skips_empty_and_comments()
    test_load_image_records_accepts_empty_cache_list()
    test_split_image_name_accepts_harbor_repo_path()
    test_split_image_name_accepts_digest_only_reference()
    test_missing_harbor_cache_marker_fails()
    test_missing_image_list_fails()
    test_load_image_records_parses_expected_tags()
    print("Harbor cache preload validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
