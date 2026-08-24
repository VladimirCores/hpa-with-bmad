#!/usr/bin/env python3
"""Smart-HTTP git server: stdlib front for git-http-backend (no extra deps).

Serves every bare repository under MIRROR_DIR so ArgoCD's go-git client can
sync offline via the fully supported smart protocol.
"""

from __future__ import annotations

import os
import subprocess
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

GIT_HTTP_BACKEND = "/usr/libexec/git-core/git-http-backend"
MIRROR_DIR = os.path.expanduser("~/.local/share/hpdc-git-mirror")
PORT = 9418


def _dechunk(payload: bytes) -> bytes:
    """Decode chunked-transfer encoding if present."""
    out = bytearray()
    i = 0
    while i < len(payload):
        j = payload.find(b"\r\n", i)
        if j < 0:
            break
        size = int(payload[i:j].split(b";")[0], 16)
        if size == 0:
            break
        out += payload[j + 2 : j + 2 + size]
        i = j + 2 + size + 2
    return bytes(out)


class GitSmartHTTP(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if method == "POST" else None

        env = os.environ.copy()
        env.update({
            "GIT_PROJECT_ROOT": MIRROR_DIR,
            "GIT_HTTP_EXPORT_ALL": "1",
            "REQUEST_METHOD": method,
            "PATH_INFO": parsed.path,
            "QUERY_STRING": parsed.query,
            "CONTENT_TYPE": self.headers.get("Content-Type") or "",
            "CONTENT_LENGTH": str(length),
            "REMOTE_ADDR": self.client_address[0],
            "GIT_COMMITTER_NAME": "mirror",
            "GIT_COMMITTER_EMAIL": "mirror@hpdc.local",
        })

        proc = subprocess.run(
            [GIT_HTTP_BACKEND],
            input=body,
            capture_output=True,
            env=env,
            check=False,
        )
        raw = proc.stdout
        head, _, payload = raw.partition(b"\r\n\r\n")
        headers: dict[str, str] = {}
        status = 200
        for line in head.split(b"\r\n"):
            name, _, value = line.partition(b":")
            key = name.decode(errors="replace").strip().lower()
            headers[key] = value.decode(errors="replace").strip()
            if key == "status":
                status = int(value.strip().split()[0])

        if headers.get("transfer-encoding", "").lower() == "chunked":
            payload = _dechunk(payload)
            del headers["transfer-encoding"]

        self.send_response(status)
        for key, value in headers.items():
            if key not in ("status",):
                self.send_header(key.title(), value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args: object) -> None:
        print(fmt % args, flush=True)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), GitSmartHTTP).serve_forever()
