#!/usr/bin/env python3
"""Validate component_versions resolver, render substitution and version policies."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "gitops"))
sys.path.insert(0, str(ROOT / "scripts" / "services"))

import component_versions as cv  # noqa: E402
import render_overlays as ro  # noqa: E402

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "image_preflight", ROOT / "scripts" / "services" / "image-preflight.py"
)
pf = importlib.util.module_from_spec(_spec)
sys.modules["image_preflight"] = pf
_spec.loader.exec_module(pf)


def _clean_env(monkeypatched: set[str]) -> None:
    """Remove HPDC_* vars so defaults are observable."""
    for key in list(os.environ):
        if key.startswith("HPDC_"):
            del os.environ[key]
            monkeypatched.add(key)


def test_dotenv_dialect(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n"
        "\n"
        "HPDC_SPEGEL_VERSION=\"0.9.9\"  # inline comment\n"
        "export HPDC_KARGO_VERSION='2.0.0'\n"
        "HPDC_EMPTY_VERSION=\n"
        "HPDC_ARGOCD_VERSION=4.4.4\n",
        encoding="utf-8",
    )
    saved: dict[str, str | None] = {}
    for key in ("HPDC_SPEGEL_VERSION", "HPDC_KARGO_VERSION", "HPDC_ARGOCD_VERSION"):
        saved[key] = os.environ.pop(key, None)
    try:
        cv.load_dotenv(env_file)
        assert os.environ["HPDC_SPEGEL_VERSION"] == "0.9.9"  # quotes + inline comment stripped
        assert os.environ["HPDC_KARGO_VERSION"] == "2.0.0"  # export prefix stripped
        assert "HPDC_EMPTY_VERSION" not in os.environ  # empty values skipped
        assert os.environ["HPDC_ARGOCD_VERSION"] == "4.4.4"

        # existing environment wins over .env
        os.environ["HPDC_ARGOCD_VERSION"] = "9.9.9"
        cv.load_dotenv(env_file)
        assert os.environ["HPDC_ARGOCD_VERSION"] == "9.9.9"
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_resolve_defaults_and_env_wins() -> None:
    cv.resolve()
    assert cv.get("HPDC_ARGOCD_VERSION") == "3.5.1"
    old = os.environ.get("HPDC_ARGOCD_VERSION")
    os.environ["HPDC_ARGOCD_VERSION"] = "8.8.8"
    try:
        refs = dict(cv.image_refs())
        argocd_ref = refs["argocd"] if isinstance(refs, dict) else None
        # image_refs returns list; re-resolve instead
        cv.resolve()
        comp_ref = next(r for c, r in cv.image_refs() if c == "argocd" and r.startswith("quay.io/argoproj/argocd"))
        assert comp_ref.endswith(":v8.8.8")
    finally:
        if old is None:
            os.environ.pop("HPDC_ARGOCD_VERSION", None)
        else:
            os.environ["HPDC_ARGOCD_VERSION"] = old
    cv.resolve()


def test_catalog_has_no_latest_and_all_markers() -> None:
    for component, ref in cv.image_refs():
        tag = ref.rsplit(":", 1)[-1]
        assert tag != "latest", f"{component}: {ref} resolves to mutable latest"
        marker = cv.marker_for(ref.rsplit(":", 1)[0], ref)
        assert marker is not None, f"{component}: {ref} has no cache marker mapping"
        assert marker.is_relative_to(cv.ROOT / "output"), f"marker escapes output/: {marker}"


OUTPUT_MARKER_ROOT = cv.ROOT / "output"


def _pf():
    return pf


def test_env_example_documents_every_var() -> None:
    example = (cv.ROOT / ".env.example").read_text(encoding="utf-8")
    missing = [var for var in cv.DEFAULTS if var not in example]
    assert not missing, f".env.example missing variables: {missing}"


def test_substitution_map_rook_plain_tag() -> None:
    sm = cv.substitution_map()
    assert sm["quay.io/rook/ceph"] == f"quay.io/rook/ceph:v{cv.get('HPDC_ROOK_CEPH_VERSION')}"


def test_render_substitution_unit() -> None:
    sample = (
        "        - image: quay.io/argoproj/argocd:v0.0.0\n"
        "        image: \"docker.io/casbin/casdoor:latest\"\n"
        "        image: victoriametrics/vmstorage:latest # side comment\n"
        "        image: ghcr.io/hpdc/regional-hub-spa:dev\n"
    )
    out, changes = ro.substitute_images(sample)
    assert f"quay.io/argoproj/argocd:v{cv.get('HPDC_ARGOCD_VERSION')}" in out
    assert f"docker.io/casbin/casdoor:{cv.get('HPDC_CASDOOR_VERSION')}" in out
    assert f"victoriametrics/vmstorage:v{cv.get('HPDC_VICTORIA_METRICS_VERSION')}-cluster # side comment" in out
    assert "regional-hub-spa:dev" in out  # custom image passes through
    assert len(changes) == 3
    # idempotent: second pass changes nothing
    out2, changes2 = ro.substitute_images(out)
    assert out2 == out and changes2 == []


def test_preflight_images_derive_from_catalog() -> None:
    expected = {ref for _, ref in cv.image_refs()}
    listed = {ref for entries in pf.IMAGES.values() for ref, _ in entries}
    assert listed <= expected, f"preflight lists refs outside catalog: {listed - expected}"
    assert len(listed) >= 30, "preflight lost catalog coverage"
    # spot-check: no stale pre-11-7 drift values may return
    all_refs = " ".join(listed)
    assert ":latest" not in all_refs
    assert not any(ref.startswith("quay.io/rook/ceph:v1.20.3") for ref in listed)
    assert not any(ref.endswith("backstage:1.42.0") for ref in listed)
    assert not any(ref.endswith("casdoor:latest") for ref in listed)
    assert pf.CUSTOM_IMAGES >= {"hpdc.local/entity-api:0.1.0"}


def test_mirror_repo_path_host_stripping() -> None:
    assert pf.mirror_repo_path("quay.io/argoproj/argocd:v3.5.1") == "argoproj/argocd"
    assert pf.mirror_repo_path("docker.io/library/redis:8.2.8-alpine") == "library/redis"
    assert pf.mirror_repo_path("victoriametrics/vmstorage:v1.148.0-cluster") == "victoriametrics/vmstorage"
    assert pf.mirror_repo_candidates("etcd:v3.6.12") == ["etcd", "library/etcd"]
    assert "library/redis" in pf.mirror_repo_candidates("redis:7.4-alpine")


def test_remediation_format() -> None:
    fix = pf.remediation_for("quay.io/rook/ceph:v1.20.6")
    assert fix.startswith("skopeo copy --all docker://quay.io/rook/ceph:v1.20.6 docker://localhost:5000/rook/ceph:v1.20.6")
    assert "mirror-image.py quay.io/rook/ceph:v1.20.6 rook/ceph:v1.20.6" in fix


def test_no_latest_image_lines_in_committed_gitops() -> None:
    offenders = []
    for yaml_path in sorted((ROOT / "gitops").rglob("*.yaml")):
        for line in yaml_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("- image:") or stripped.startswith("image:"):
                if ":latest" in stripped or stripped.endswith(":latest"):
                    offenders.append(f"{yaml_path.relative_to(ROOT)}: {stripped}")
    assert not offenders, f"mutable :latest image refs committed: {offenders}"


def main() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_dotenv_dialect(Path(tmp))
    test_resolve_defaults_and_env_wins()
    test_catalog_has_no_latest_and_all_markers()
    test_env_example_documents_every_var()
    test_substitution_map_rook_plain_tag()
    test_render_substitution_unit()
    test_preflight_images_derive_from_catalog()
    test_mirror_repo_path_host_stripping()
    test_remediation_format()
    test_no_latest_image_lines_in_committed_gitops()
    print("component versions validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
