#!/usr/bin/env python3
"""Resilient single-arch image mirror into the local registry.

Defeats flaky CDN edges: every blob is downloaded in 4MB Range chunks with
per-chunk retry+resume, sha256-verified, then pushed to the local registry
via its HTTP API. Only the linux/amd64 child of a manifest list is mirrored
(dev hosts are amd64); a plain image manifest is taken as-is.

Usage:
  mirror-image.py <source-ref> <dest-repo:tag>
    e.g. mirror-image.py registry.k8s.io/coredns/coredns:v1.14.4 coredns/coredns:v1.14.4

Env: HTTPS_PROXY honored for source; destination is always local/direct.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

SOURCE = sys.argv[1]
DEST = sys.argv[2]
DEST_REPO, DEST_TAG = DEST.split(":")
LOCAL = "http://127.0.0.1:5000"
CHUNK = 4 * 1024 * 1024
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def http(url: str, *, method: str = "GET", data=None, headers=None, timeout: int = 60):
    req = urllib.request.Request(url, method=method, data=data, headers=headers or {})
    return urllib.request.urlopen(req, timeout=timeout)


def fetch(url: str, headers=None) -> bytes:
    """GET with manual redirect-following (preserving Accept) + retries."""
    last_body = b""
    for _ in range(10):
        try:
            req = urllib.request.Request(url, headers=headers or {})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                if e.status in (301, 302, 303, 307, 308):
                    loc = e.headers.get("Location")
                    url = loc if loc.startswith("http") else urllib.parse.urljoin(url, loc)
                    last_body = e.read()
                    continue
                raise
        except urllib.error.HTTPError:
            raise
        except Exception:
            pass
    raise RuntimeError(f"fetch failed {url}: {last_body[:200]!r}")


def download_blob_resumable(url: str, digest: str, depth: int = 0) -> bytes:
    """Download with 4MB range chunks; each chunk retried independently."""
    with http(url, method="HEAD") as r:
        cl = r.headers.get("Content-Length")
    if not cl:
        with http(url) as r:
            return r.read()
    total = int(cl)
    expected = digest.split(":", 1)[1]
    path = os.path.join(tempfile.gettempdir(), f"hpdc-mirror-{expected[:16]}-{os.getpid()}.part")
    have = os.path.getsize(path) if os.path.exists(path) else 0
    while have < total:
        end = min(have + CHUNK, total) - 1
        ok = False
        for _ in range(12):
            try:
                req = urllib.request.Request(url, headers={"Range": f"bytes={have}-{end}"})
                with urllib.request.urlopen(req, timeout=90) as r:
                    data = r.read()
                assert len(data) == end - have + 1
                with open(path, "ab") as f:
                    f.write(data)
                have += len(data)
                ok = True
                break
            except Exception:
                have = os.path.getsize(path) if os.path.exists(path) else 0
        if not ok:
            raise RuntimeError(f"chunk stuck at {have}/{total} for {digest}")
    data = open(path, "rb").read()
    if hashlib.sha256(data).hexdigest() != expected:
        os.remove(path)
        if depth >= 1:
            raise RuntimeError(f"digest mismatch persists for {digest}")
        print(f"digest mismatch for {digest}; re-downloading once…", flush=True)
        return download_blob_resumable(url, digest, depth + 1)
    os.remove(path)
    return data


def push_blob(repo: str, data: bytes) -> None:
    with _DIRECT.open(f"{LOCAL}/v2/{repo}/blobs/uploads/", method="POST") as r:
        loc = r.headers["Location"]
        if loc.startswith("/"):
            loc = LOCAL + loc
    with _DIRECT.open(loc, method="PATCH", data=data,
                      headers={"Content-Type": "application/octet-stream"}) as r:
        loc = r.headers["Location"]
        if loc.startswith("/"):
            loc = LOCAL + loc
    sep = "&" if "?" in loc else "?"
    with _DIRECT.open(f"{loc}{sep}digest=sha256:{hashlib.sha256(data).hexdigest()}", method="PUT") as r:
        if r.status not in (200, 201):
            raise RuntimeError(f"blob put failed: {r.status}")


def push_manifest(repo: str, tag: str, raw: bytes, media_type: str) -> None:
    with _DIRECT.open(f"{LOCAL}/v2/{repo}/manifests/{tag}", method="PUT", data=raw,
                      headers={"Content-Type": media_type}) as r:
        if r.status not in (200, 201):
            raise RuntimeError(f"manifest push failed: {r.status}")


def main() -> int:
    # Already present?
    try:
        with _DIRECT.open(f"{LOCAL}/v2/{DEST_REPO}/manifests/{DEST_TAG}") as r:
            print(f"already mirrored: {DEST}")
            return 0
    except Exception:
        pass

    src_base = f"https://{SOURCE.split('/')[0]}/v2/{'/'.join(SOURCE.split('/')[1:])}"
    raw = fetch(f"{src_base}/manifests/{DEST_TAG.split(':')[-1]}",
                headers={"Accept": "application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json,application/vnd.docker.distribution.manifest.list.v2+json,application/vnd.oci.image.index.v1+json"})
    mtype = "application/vnd.oci.image.index.v1+json"
    doc = json.loads(raw)
    if "manifests" in doc:  # index/list -> pick linux/amd64
        child = next((m for m in doc["manifests"]
                      if m.get("platform", {}).get("architecture") == "amd64"
                      and m.get("platform", {}).get("os") == "linux"), None)
        if child is None:
            raise RuntimeError(f"no linux/amd64 variant in manifest list for {SOURCE}")
        accept_child = "application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json"
        raw = fetch(f"{src_base}/manifests/{child['digest']}", headers={"Accept": accept_child})
        doc = json.loads(raw)
        mtype = child["mediaType"] or accept_child.split(",")[0]

    mtype = doc.get("mediaType") or (
        "application/vnd.docker.distribution.manifest.v2+json"
        if "config" in doc else mtype
    )
    blobs = [doc["config"]["digest"]] + [l["digest"] for l in doc["layers"]]
    seen = set()
    for dig in blobs:
        if dig in seen:
            continue
        seen.add(dig)
        print(f"blob {dig[:19]}…", flush=True)
        data = download_blob_resumable(f"{src_base}/blobs/{dig}", dig)
        push_blob(DEST_REPO, data)

    push_manifest(DEST_REPO, DEST_TAG.split(":")[-1], raw, mtype)
    print(f"✓ mirrored {SOURCE} -> {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
