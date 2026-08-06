#!/usr/bin/env python3
"""Preload offline image cache into Harbor."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARBOR_MARKER = ROOT / "output" / "harbor" / "images" / "harbor-core-v2.11.3"
IMAGE_LIST = ROOT / "output" / "harbor" / "cache-images.txt"
HARBOR_INGESTION_MANIFEST = ROOT / "output" / "harbor" / "harbor-ingestion-manifest.yaml"
HARBOR_BASE = ROOT / "gitops" / "harbor" / "base"
HARBOR_OVERLAY = ROOT / "gitops" / "harbor" / "overlays" / "preload"
IMAGE_SOURCE_ALIASES = {
    "redis:7.2-alpine": "output/harbor/images/harbor-redis-v1.23",
    "postgres:15-alpine": "output/harbor/images/harbor-postgresql-v15",
}


@dataclass(frozen=True)
class ImageRecord:
    name: str
    tag: str
    source: Path
    target: str | None


def ensure_files(root: Path = ROOT) -> None:
    missing = [path for path in (root / HARBOR_MARKER.relative_to(root), root / IMAGE_LIST.relative_to(root)) if not path.exists()]
    if missing:
        missing_text = ", ".join(str(path.relative_to(root)) for path in missing)
        raise RuntimeError(f"Missing Harbor cache prerequisites: {missing_text}")


def validate_manifests(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    required = [
        root / HARBOR_MARKER.relative_to(root),
        root / IMAGE_LIST.relative_to(root),
        root / "gitops" / "harbor" / "base" / "preload-images.yaml",
        root / "gitops" / "harbor" / "base" / "preload-images-job.yaml",
        root / "gitops" / "harbor" / "overlays" / "preload" / "kustomization.yaml",
    ]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(root)))

    preload = (root / "gitops" / "harbor" / "base" / "preload-images.yaml").read_text(encoding="utf-8")
    overlay = (root / "gitops" / "harbor" / "overlays" / "preload" / "kustomization.yaml").read_text(encoding="utf-8")

    if "kind: ConfigMap" not in preload or "offline-image-cache" not in preload:
        failures.append("preload-images.yaml missing offline image cache ConfigMap")
    if "kind: Job" not in preload or "preload-offline-image-cache" not in preload:
        failures.append("preload-images.yaml missing preload Job")
    if "docker:2.41-cli" not in preload:
        failures.append("preload-images.yaml missing preload image")
    job = (root / "gitops" / "harbor" / "base" / "preload-images-job.yaml").read_text(encoding="utf-8")
    if "kind: ConfigMap" not in job or "preload-images-job-config" not in job:
        failures.append("preload-images-job.yaml missing preload job config")
    if "../../base/preload-images.yaml" not in overlay or "../../base/preload-images-job.yaml" not in overlay:
        failures.append("preload overlay missing base manifests")
    return failures


def split_image_name(image: str) -> tuple[str, str]:
    if ":" not in image:
        return image, "latest"
    name, tag = image.rsplit(":", 1)
    if not name or not tag:
        raise ValueError(f"invalid image reference: {image}")
    return name, tag


def source_for_image(image: str) -> Path:
    if image in IMAGE_SOURCE_ALIASES:
        return ROOT / IMAGE_SOURCE_ALIASES[image]
    name, tag = split_image_name(image)
    slug = name.rsplit("/", 1)[-1].replace(":", "-")
    return ROOT / "output" / "harbor" / "images" / f"{slug}-{tag}"


def target_for_image(image: str) -> str | None:
    name, tag = split_image_name(image)
    if name.startswith("harbor/"):
        return f"harbor.local/{name}:{tag}"
    return None


def load_image_records(root: Path = ROOT) -> list[ImageRecord]:
    ensure_files(root)
    records: list[ImageRecord] = []
    for raw_line in (root / IMAGE_LIST.relative_to(root)).read_text(encoding="utf-8").splitlines():
        image = raw_line.strip()
        if not image:
            continue
        name, tag = split_image_name(image)
        source = source_for_image(image)
        if not source.exists():
            raise RuntimeError(f"Offline image cache marker not found: {source.relative_to(root)}")
        records.append(ImageRecord(name=name, tag=tag, source=source, target=target_for_image(image)))
    return records


def write_ingestion_manifest(records: list[ImageRecord], root: Path = ROOT) -> Path:
    manifest_path = root / "output" / "harbor" / "harbor-ingestion-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "harbor_ingestion:",
        "  offline: true",
        "  images:",
    ]
    for record in records:
        lines.append(f"    - name: {record.name}:{record.tag}")
        lines.append(f"      source: {record.source.relative_to(root)}")
        lines.append(f"      expected_tag: {record.tag}")
        if record.target:
            lines.append(f"      target: {record.target}")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest_path


def print_image_records(records: list[ImageRecord], root: Path = ROOT) -> None:
    print("Images to preload:")
    for record in records:
        print(f"- {record.name}:{record.tag} expected_tag={record.tag}")
        if record.target:
            print(f"  target={record.target}")
    manifest_path = write_ingestion_manifest(records, root)
    print(f"Harbor ingestion manifest: {manifest_path.relative_to(root)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Preload offline image cache into Harbor")
    parser.add_argument("--offline", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    try:
        ensure_files()
        failures = validate_manifests()
        if failures:
            for failure in failures:
                print(f"- {failure}")
            return 1

        records = load_image_records()
        if args.check:
            write_ingestion_manifest(records)
            print("Preload Harbor cache validation passed.")
            print(f"Harbor ingestion manifest: {HARBOR_INGESTION_MANIFEST.relative_to(ROOT)}")
            return 0

        if args.apply:
            write_ingestion_manifest(records)
            print("Preload Harbor cache apply requested.")
            print(f"Harbor ingestion manifest: {HARBOR_INGESTION_MANIFEST.relative_to(ROOT)}")
            return 0

        if args.dry_run:
            print_image_records(records)
            return 0
    except (RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1

    print("Preload Harbor cache requires --dry-run, --check, or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
