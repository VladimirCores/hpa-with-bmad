#!/usr/bin/env python3
"""Record Harbor offline image cache ingestion metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARBOR_MARKER = ROOT / "output" / "harbor" / "images" / "harbor-core-v2.15.2"
IMAGE_LIST = ROOT / "output" / "harbor" / "cache-images.txt"
HARBOR_INGESTION_MANIFEST = ROOT / "output" / "harbor" / "harbor-ingestion-manifest.yaml"
HARBOR_BASE = ROOT / "gitops" / "harbor" / "base"
HARBOR_OVERLAY = ROOT / "gitops" / "harbor" / "overlays" / "preload"
IMAGE_SOURCE_ALIASES = {
    "redis:7.4-alpine": "output/harbor/images/redis-7.4-alpine",
    "postgres:15.19-alpine": "output/harbor/images/postgres-15.19-alpine",
}


@dataclass(frozen=True)
class ParsedImage:
    name: str
    tag: str
    digest: str | None = None


@dataclass(frozen=True)
class ImageRecord:
    name: str
    tag: str
    source: Path
    target: str | None
    digest: str | None = None


def ensure_files(root: Path = ROOT) -> None:
    required_paths = (
        root / "output" / "harbor" / "images" / "harbor-core-v2.15.2",
        root / "output" / "harbor" / "cache-images.txt",
    )
    missing = [path for path in required_paths if not path.exists()]
    if missing:
        missing_text = ", ".join(str(path.relative_to(root)) for path in missing)
        raise RuntimeError(f"Missing Harbor cache prerequisites: {missing_text}")


def validate_manifests(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    required = [
        root / "output" / "harbor" / "images" / "harbor-core-v2.15.2",
        root / "output" / "harbor" / "cache-images.txt",
        root / "gitops" / "harbor" / "base" / "preload-images.yaml",
        root / "gitops" / "harbor" / "base" / "preload-images-job.yaml",
        root / "gitops" / "harbor" / "overlays" / "preload" / "kustomization.yaml",
    ]
    for path in required:
        if not path.exists():
            failures.append(str(path.relative_to(root)))
    if failures:
        return failures

    preload = (root / "gitops" / "harbor" / "base" / "preload-images.yaml").read_text(encoding="utf-8")
    overlay = (root / "gitops" / "harbor" / "overlays" / "preload" / "kustomization.yaml").read_text(encoding="utf-8")

    if "kind: ConfigMap" not in preload or "offline-image-cache" not in preload:
        failures.append("preload-images.yaml missing offline image cache ConfigMap")
    if "kind: Job" not in preload or "preload-offline-image-cache" not in preload:
        failures.append("preload-images.yaml missing preload Job")
    if "docker:29-cli" not in preload:
        failures.append("preload-images.yaml missing preload image")
    job = (root / "gitops" / "harbor" / "base" / "preload-images-job.yaml").read_text(encoding="utf-8")
    if "kind: ConfigMap" not in job or "preload-images-job-config" not in job:
        failures.append("preload-images-job.yaml missing preload job config")
    if "../../base/preload-images.yaml" not in overlay or "../../base/preload-images-job.yaml" not in overlay:
        failures.append("preload overlay missing base manifests")
    return failures


def validate_image_name(name: str) -> None:
    if not name:
        raise ValueError(f"invalid image name: {name}")
    segments = name.split("/")
    if any(
        not segment
        or len(segment) > 128
        or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}", segment)
        or (":" in segment and not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*(?::[0-9]{1,5})?", segment))
        for segment in segments
    ):
        raise ValueError(f"invalid image name: {name}")


def validate_image_tag(tag: str) -> None:
    if not tag:
        raise ValueError(f"invalid image tag: {tag}")
    if tag.startswith("sha256:"):
        if not re.fullmatch(r"sha256:[A-Fa-f0-9]{64}", tag):
            raise ValueError(f"invalid image tag: {tag}")
    elif not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag):
        raise ValueError(f"invalid image tag: {tag}")


def parse_image_reference(image: str) -> ParsedImage:
    digest = None
    if "@" in image:
        name_digest, digest = image.rsplit("@", 1)
    else:
        name_digest = image

    if ":" in name_digest:
        name, tag = name_digest.rsplit(":", 1)
    else:
        if digest is None:
            raise ValueError(f"image reference must include a tag or digest: {image}")
        name, tag = name_digest, digest

    if not name or not tag:
        raise ValueError(f"invalid image reference: {image}")
    validate_image_name(name)
    validate_image_tag(tag)
    return ParsedImage(name=name, tag=tag, digest=digest)


def split_image_name(image: str) -> tuple[str, str]:
    parsed = parse_image_reference(image)
    return parsed.name, parsed.tag


def source_for_image(image: str, root: Path = ROOT) -> Path:
    if image in IMAGE_SOURCE_ALIASES:
        return root / IMAGE_SOURCE_ALIASES[image]
    parsed = parse_image_reference(image)
    slug = parsed.name.rsplit("/", 1)[-1].replace(":", "-")
    return root / "output" / "harbor" / "images" / f"{slug}-{parsed.tag}"


def target_for_image(image: str) -> str:
    parsed = parse_image_reference(image)
    if parsed.digest:
        return f"harbor.local/{parsed.name}@{parsed.digest}"
    if parsed.name.startswith("harbor/"):
        return f"harbor.local/{parsed.name}:{parsed.tag}"
    if parsed.name == "redis":
        return f"harbor.local/library/redis:{parsed.tag}"
    if parsed.name == "postgres":
        return f"harbor.local/library/postgres:{parsed.tag}"
    return f"harbor.local/{parsed.name}:{parsed.tag}"


def load_image_records(root: Path = ROOT) -> list[ImageRecord]:
    ensure_files(root)
    records: list[ImageRecord] = []
    for raw_line in (root / "output" / "harbor" / "cache-images.txt").read_text(encoding="utf-8").splitlines():
        image = raw_line.strip()
        if not image or image.startswith("#"):
            continue
        parsed = parse_image_reference(image)
        source = source_for_image(image, root=root)
        if not source.exists():
            raise RuntimeError(f"Offline image cache marker not found: {source.relative_to(root)}")
        records.append(
            ImageRecord(
                name=parsed.name,
                tag=parsed.tag,
                source=source,
                target=target_for_image(image),
                digest=parsed.digest,
            )
        )
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
        lines.append(f"    - name: {json.dumps(record.name)}")
        lines.append(f"      source: {json.dumps(str(record.source.relative_to(root)))}")
        lines.append(f"      expected_tag: {json.dumps(record.tag)}")
        lines.append(f"      target: {json.dumps(record.target)}")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest_path


def print_image_records(records: list[ImageRecord], root: Path = ROOT) -> None:
    print("Images to record:")
    for record in records:
        reference = f"{record.name}@{record.digest}" if record.digest else f"{record.name}:{record.tag}"
        print(f"- {reference} expected_tag={record.tag}")
        print(f"  target={record.target}")


def main(root: Path = ROOT, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record Harbor offline image cache ingestion metadata")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    root = args.root
    if not args.offline:
        print("--offline is required for Harbor cache metadata generation.", file=sys.stderr)
        return 1
    active_modes = [args.dry_run, args.check, args.apply]
    if sum(active_modes) > 1:
        print("Specify exactly one of --dry-run, --check, or --apply.", file=sys.stderr)
        return 1

    try:
        ensure_files(root)
        failures = validate_manifests(root)
        if failures:
            for failure in failures:
                print(f"- {failure}")
            return 1

        records = load_image_records(root)
        if args.check:
            manifest_path = write_ingestion_manifest(records, root=root)
            print("Preload Harbor cache validation passed.")
            print(f"Harbor ingestion manifest: {manifest_path.relative_to(root)}")
            return 0

        if args.apply:
            manifest_path = write_ingestion_manifest(records, root=root)
            print("Harbor ingestion manifest recorded.")
            print(f"Harbor ingestion manifest: {manifest_path.relative_to(root)}")
            return 0

        if args.dry_run:
            print_image_records(records, root=root)
            return 0
    except (RuntimeError, ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1

    print("Preload Harbor cache requires --dry-run, --check, or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
