#!/usr/bin/env python3
"""Generate a static self-signed wildcard TLS certificate for Envoy Gateway
and apply it as a Kubernetes Secret.

This replaces the cert-manager TLS-termination flow (Epic 1.5 refactor) with a
single offline bootstrap step. ``openssl`` generates a self-signed RSA-2048
X.509 wildcard certificate for ``CN=*.hpdc.local`` / ``SAN=DNS:*.hpdc.local``
with a 3650-day (10-year) validity, stores the cert/key at
``~/.hpdc/certs/tls.crt`` and ``~/.hpdc/certs/tls.key`` (outside the repo, never
committed), and --apply pushes it as ``Secret/hpdc-edge-tls`` of type
``kubernetes.io/tls`` in ``envoy-gateway-system`` -- the Secret consumed by
Envoy Gateway's HTTPS listener (``gitops/envoy-gateway/base/envoy-gateway.yaml``).

Modes (mutually exclusive, one required):
  --check   validate local cert state only (no cluster access, no changes)
  --dry-run report what would be done (no changes, no cluster access)
  --apply   generate the cert (if absent) and apply the Secret to the cluster
  --force   (with --apply) regenerate the cert even if existing files are invalid

Forward-dependency: ``docs/static-tls-termination.md`` is produced in Story 1.5.3. This
script does not require that file.

Note: the ``--offline`` flag is accepted for parity with the gitops installer
convention; this step is always offline (openssl + local cluster kubectl) and
the flag has no effect.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from _provisioned import require
import component_versions

component_versions.load_all_dotenv()
ROOT = Path(__file__).resolve().parents[2]

# ── TLS material parameters (per spec boundaries) ─────────────────────────────
# Stored OUTSIDE the repo at ~/.hpdc/certs/ so these secrets are never committed.
CERT_DIR = Path("~").expanduser() / ".hpdc" / "certs"
CERT_PATH = CERT_DIR / "tls.crt"
KEY_PATH = CERT_DIR / "tls.key"
CERT_CN = "*.hpdc.local"
CERT_SUBJECT = f"/CN={CERT_CN}"
CERT_SAN = "DNS:*.hpdc.local"
CERT_DAYS = 3650
CERT_KEYTYPE = "rsa:2048"

# ── Kubernetes Secret parameters (matching the EG HTTPS listener) ────────────
SECRET_NAMESPACE = "envoy-gateway-system"
SECRET_NAME = "hpdc-edge-tls"
SECRET_TYPE = "kubernetes.io/tls"
ENVOY_MANIFEST = ROOT / "gitops" / "envoy-gateway" / "base" / "envoy-gateway.yaml"

# ── Subprocess timeout (seconds) ──────────────────────────────────────────────
_CMD_TIMEOUT = 600


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command, capturing stdout/stderr (never raises)."""
    return subprocess.run(
        cmd, text=True, capture_output=True, check=False,
        timeout=_CMD_TIMEOUT, errors="replace",
    )


def _run_kubectl(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run kubectl with the given args, capturing output (never raises)."""
    return _run(["kubectl", *args])


def _check_tools() -> list[str]:
    """Verify required external tools are available. Returns failure list."""
    failures: list[str] = []
    for tool in ("openssl", "kubectl"):
        if shutil.which(tool) is None:
            failures.append(f"required tool not found on PATH: {tool}")
    return failures


def ensure_files() -> None:
    """Verify provisioning prerequisites before doing any work.

    Mirrors the install-envoy-gateway-dev.py ``ensure_files`` guard: confirm
    envoy-gateway is a registered provisioned component and that the EG manifest
    that *consumes* this secret exists.
    """
    require("envoy-gateway")
    if not ENVOY_MANIFEST.is_file():
        raise RuntimeError(
            f"Envoy Gateway manifest missing: {ENVOY_MANIFEST.relative_to(ROOT)}"
        )


def validate_manifests() -> list[str]:
    """Confirm the EG HTTPS listener consumes the hpdc-edge-tls secret.

    Returns a list of human-readable failure strings (empty == healthy).
    """
    failures: list[str] = []
    try:
        manifest = ENVOY_MANIFEST.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        failures.append(f"envoy-gateway.yaml unreadable: {exc}")
        return failures
    # Use regex to tolerate YAML quoting (e.g. name: "hpdc-edge-tls").
    if not re.search(r'name:\s*["\']?hpdc-edge-tls["\']?', manifest):
        failures.append(f"envoy-gateway.yaml does not reference Secret/{SECRET_NAME}")
    if not re.search(r'protocol:\s*["\']?HTTPS["\']?', manifest):
        failures.append("envoy-gateway.yaml does not configure an HTTPS listener")
    if "envoy-gateway-system" not in manifest:
        failures.append(
            f"envoy-gateway.yaml does not target namespace {SECRET_NAMESPACE}"
        )
    if "certificateRefs" not in manifest:
        failures.append("envoy-gateway.yaml has no certificateRefs on its HTTPS listener")
    return failures


# ── Local cert inspection ────────────────────────────────────────────────────


def _cert_present() -> bool:
    """True when both tls.crt and tls.key exist as regular files."""
    return CERT_PATH.is_file() and KEY_PATH.is_file()


def _validate_cert_pair() -> tuple[bool, str]:
    """Validate an existing cert/key pair.

    Checks: not expired, correct CN, correct SAN, cert and key match.
    Returns (ok, reason).
    """
    # Not expired (checkend 0 => exits non-zero only if already expired).
    r = _run(["openssl", "x509", "-in", str(CERT_PATH), "-checkend", "0", "-noout"])
    if r.returncode != 0:
        return False, "certificate is expired or unreadable"

    # Subject CN.
    r = _run(["openssl", "x509", "-in", str(CERT_PATH), "-noout", "-subject"])
    if r.returncode != 0 or CERT_CN not in r.stdout:
        return False, f"certificate subject missing CN={CERT_CN}"

    # SAN.
    r = _run(["openssl", "x509", "-in", str(CERT_PATH), "-noout", "-ext", "subjectAltName"])
    if r.returncode != 0 or CERT_SAN not in r.stdout:
        return False, f"certificate SAN missing {CERT_SAN}"

    # cert/key pair match (compare derived public keys — algorithm-agnostic).
    cert_pub = _run(["openssl", "x509", "-in", str(CERT_PATH), "-pubkey", "-noout"])
    key_pub = _run(["openssl", "pkey", "-in", str(KEY_PATH), "-pubout"])
    if cert_pub.returncode != 0 or key_pub.returncode != 0:
        return False, "could not extract public key from cert or key"
    if cert_pub.stdout.strip() != key_pub.stdout.strip():
        return False, "certificate and key do not match"

    return True, "ok"


def _cert_state() -> tuple[str, str]:
    """Classify the on-disk cert state.

    Returns (state, detail) where state is one of:
      ``valid``   -- files exist and pass all validation checks
      ``missing`` -- one or both files absent
      ``invalid`` -- files exist but fail validation (wrong CN/SAN, expired,
                     or cert/key mismatch); cannot be auto-resolved safely
    """
    if not _cert_present():
        return "missing", f"cert/key not found under {CERT_DIR}"
    ok, reason = _validate_cert_pair()
    if ok:
        return "valid", "cert already present"
    return "invalid", reason


# ── Cert generation ──────────────────────────────────────────────────────────


def _generate_cert() -> int:
    """Generate the self-signed wildcard cert with openssl. Returns 0/1."""
    try:
        CERT_DIR.mkdir(parents=True, exist_ok=True)
    except (FileExistsError, PermissionError) as exc:
        print(f"error: cannot create cert directory {CERT_DIR}: {exc}",
              file=sys.stderr)
        return 1
    cmd = [
        "openssl", "req", "-x509", "-newkey", CERT_KEYTYPE,
        "-keyout", str(KEY_PATH), "-out", str(CERT_PATH),
        "-days", str(CERT_DAYS), "-nodes",
        "-subj", CERT_SUBJECT,
        "-addext", f"subjectAltName={CERT_SAN}",
    ]
    result = _run(cmd)
    if result.returncode != 0:
        print(f"error: openssl cert generation failed: {result.stderr.strip()}",
              file=sys.stderr)
        return 1
    # Verify files exist, are non-empty, and re-validate the generated pair.
    if not CERT_PATH.is_file() or not KEY_PATH.is_file():
        print("error: openssl exited cleanly but cert/key files are missing",
              file=sys.stderr)
        return 1
    if CERT_PATH.stat().st_size == 0 or KEY_PATH.stat().st_size == 0:
        print("error: openssl produced empty cert/key files", file=sys.stderr)
        return 1
    ok, reason = _validate_cert_pair()
    if not ok:
        print(f"error: generated cert failed validation: {reason}", file=sys.stderr)
        return 1
    # Restrict key file permissions (openssl with -nodes creates 0600 by default,
    # but make it explicit).
    KEY_PATH.chmod(0o600)
    print(f"Generated self-signed wildcard cert at {CERT_PATH}")
    print(f"  CN={CERT_CN}  SAN={CERT_SAN}  validity={CERT_DAYS}d  key={CERT_KEYTYPE}")
    return 0


# ── Kubernetes Secret operations ─────────────────────────────────────────────


def _cluster_error_detail(result: subprocess.CompletedProcess[str]) -> str:
    """Extract a concise, human-readable reason from a failed kubectl result."""
    msg = (result.stderr.strip() or result.stdout.strip()) or "unknown error"
    # Distinguish auth/connectivity failures from object-level errors.
    lower = msg.lower()
    if any(k in lower for k in ("unauthorized", "forbidden", "authentication",
                                "token", "login")):
        return f"authentication/authorization error: {msg}"
    if any(k in lower for k in ("connection", "connect", "timeout", "refused",
                                "no route", "dns", "unreachable")):
        return f"cluster unreachable: {msg}"
    return msg


def _has_kubectl_cluster() -> bool:
    """Lightweight cluster reachability probe (no assumptions about objects)."""
    print("Checking cluster connectivity via kubectl...")
    sys.stdout.flush()
    # ``kubectl get --raw=/livez`` makes a real API-server call and fails
    # (non-zero) when the server is unreachable, down, or auth is rejected.
    # The previous --retries flag was invalid for kubectl and has been removed.
    result = _run_kubectl(["get", "--raw=/livez", "--request-timeout=5s"])
    if result.returncode != 0:
        detail = _cluster_error_detail(result)
        print(f"error: kubectl cluster connectivity check failed: {detail}",
              file=sys.stderr)
        return False
    return True


def _namespace_exists() -> bool:
    result = _run_kubectl(["get", "namespace", SECRET_NAMESPACE])
    return result.returncode == 0


def ensure_namespace() -> int:
    """Ensure the Envoy Gateway namespace exists. Returns 0/1."""
    result = _run_kubectl(["get", "namespace", SECRET_NAMESPACE])
    if result.returncode == 0:
        return 0
    # Distinguish auth/connectivity errors from simple "not found".
    detail = _cluster_error_detail(result)
    if "authentication" in detail or "cluster unreachable" in detail:
        print(f"error: cannot verify namespace (cluster access issue): {detail}",
              file=sys.stderr)
        return 1
    print(f"Creating namespace {SECRET_NAMESPACE}...")
    result = _run_kubectl(["create", "namespace", SECRET_NAMESPACE])
    if result.returncode != 0:
        detail = _cluster_error_detail(result)
        print(f"error: failed to create namespace {SECRET_NAMESPACE}: {detail}",
              file=sys.stderr)
        return 1
    return 0


def _secret_exists() -> bool:
    result = _run_kubectl(["get", "secret", SECRET_NAME, "-n", SECRET_NAMESPACE])
    if result.returncode == 0:
        return True
    # Distinguish auth/connectivity errors from simple "not found".
    detail = _cluster_error_detail(result)
    if "authentication" in detail or "cluster unreachable" in detail:
        print(f"error: cannot verify Secret (cluster access issue): {detail}",
              file=sys.stderr)
        return False
    return False


def _secret_matches_disk() -> bool:
    """Check whether the in-cluster Secret's cert/key matches on-disk files."""
    result = _run_kubectl([
        "get", "secret", SECRET_NAME, "-n", SECRET_NAMESPACE, "-o", "json",
    ])
    if result.returncode != 0:
        return False
    try:
        data = json.loads(result.stdout)
        cluster_cert_b64 = data.get("data", {}).get("tls.crt", "")
        cluster_key_b64 = data.get("data", {}).get("tls.key", "")
    except (json.JSONDecodeError, KeyError):
        return False
    try:
        cluster_cert = base64.b64decode(cluster_cert_b64).decode("utf-8")
    except Exception:
        return False
    try:
        disk_cert = CERT_PATH.read_text(encoding="utf-8")
    except OSError:
        return False
    if cluster_cert != disk_cert:
        return False
    # Also verify the key matches (compare moduli via openssl).
    cert_mod = _run([
        "openssl", "x509", "-in", str(CERT_PATH), "-noout", "-modulus",
    ])
    key_mod = _run([
        "openssl", "pkey", "-in", str(KEY_PATH), "-noout", "-modulus",
    ])
    if cert_mod.returncode != 0 or key_mod.returncode != 0:
        return False
    return cert_mod.stdout.strip() == key_mod.stdout.strip()


def _create_secret() -> int:
    """Create the TLS Secret from the on-disk cert/key. Returns 0/1."""
    result = _run_kubectl([
        "create", "secret", "tls", SECRET_NAME,
        "--cert", str(CERT_PATH), "--key", str(KEY_PATH),
        "-n", SECRET_NAMESPACE,
    ])
    if result.returncode != 0:
        detail = _cluster_error_detail(result)
        print(f"error: kubectl create secret failed: {detail}", file=sys.stderr)
        return 1
    msg = result.stdout.strip() or f"Created Secret/{SECRET_NAME}."
    print(msg)
    return 0


def ensure_secret() -> int:
    """Idempotently ensure the TLS Secret exists and matches on-disk cert/key.

    If the Secret exists but its content differs from the local files, it is
    deleted and recreated (cert/key drift recovery).
    """
    if _secret_exists():
        if _secret_matches_disk():
            print(f"secret already present (Secret/{SECRET_NAME} in {SECRET_NAMESPACE})")
            return 0
        print(f"Secret/{SECRET_NAME} exists but content differs from disk; "
              f"recreating...")
        _run_kubectl(["delete", "secret", SECRET_NAME, "-n", SECRET_NAMESPACE])
        return _create_secret()
    print(f"Applying Secret/{SECRET_NAME} (type={SECRET_TYPE}) "
          f"in namespace {SECRET_NAMESPACE}...")
    return _create_secret()


# ── Mode handlers ─────────────────────────────────────────────────────────────


def _prep() -> list[str]:
    """Run shared prerequisite + manifest validation; return failure list."""
    failures: list[str] = _check_tools()
    if failures:
        return failures
    try:
        ensure_files()
    except Exception as exc:  # broad: _provisioned may raise yaml.YAMLError etc.
        print(f"error: {exc}", file=sys.stderr)
        return ["prerequisite check failed"]
    return validate_manifests()


def check() -> int:
    """Validate local cert state only (no cluster access).

    Returns 0 for known, actionable states (``valid`` or ``missing``).
    Returns 1 only for broken states (``invalid``) or manifest failures.
    """
    failures = _prep()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1

    state, detail = _cert_state()
    if state == "valid":
        print(f"cert already present ({CERT_PATH})")
        return 0
    if state == "missing":
        # Actionable, not broken — --apply will generate it.
        print(f"cert is absent; {detail}")
        print("--apply will generate it with openssl.")
        return 0
    # invalid -> HALT (cannot be auto-resolved safely)
    print(f"error: existing cert files are invalid: {detail}", file=sys.stderr)
    return 1


def dry_run() -> int:
    """Report what would be done without making changes (no cluster access)."""
    failures = _prep()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1

    state, detail = _cert_state()
    if state == "invalid":
        print(f"error: existing cert files are invalid: {detail}", file=sys.stderr)
        return 1

    print("Dry-run: gen-edge-cert")
    print(f"  cert dir: {CERT_DIR}")
    print(f"  cert:     {CERT_PATH}")
    print(f"  key:      {KEY_PATH}")
    print(f"  CN={CERT_CN} SAN={CERT_SAN} validity={CERT_DAYS}d key={CERT_KEYTYPE}")
    if state == "valid":
        print("  cert already present; would skip generation.")
        print(f"  would ensure Secret/{SECRET_NAME} (type={SECRET_TYPE}) "
              f"exists in {SECRET_NAMESPACE}.")
    else:
        print("  cert absent; would generate self-signed wildcard cert.")
        print(f"  would ensure namespace {SECRET_NAMESPACE} exists.")
        print(f"  would create Secret/{SECRET_NAME} (type={SECRET_TYPE}) "
              f"from the cert and key.")
    return 0


def apply(force: bool = False) -> int:
    """Generate the cert (if absent or forced) and apply the Secret to the cluster."""
    failures = _prep()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1

    state, detail = _cert_state()
    if state == "invalid":
        if not force:
            print(f"error: existing cert files are invalid: {detail}", file=sys.stderr)
            print("       HALT: cannot safely overwrite an invalid cert. "
                  "Use --force to regenerate.", file=sys.stderr)
            return 1
        print(f"--force: regenerating invalid cert ({detail})...")

    if state == "valid":
        print(f"cert already present ({CERT_PATH})")
    else:
        print(f"cert absent; generating at {CERT_DIR}...")
        rc = _generate_cert()
        if rc != 0:
            return 1

    # Cluster operations (only --apply reaches here).
    if not _has_kubectl_cluster():
        print("error: kubectl cannot reach the cluster; Secret not applied",
              file=sys.stderr)
        return 1

    rc = ensure_namespace()
    if rc != 0:
        return 1
    return ensure_secret()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a static self-signed wildcard TLS cert for Envoy "
                    "Gateway and apply it as a Kubernetes Secret."
    )
    parser.add_argument("--offline", action="store_true", default=True,
                        help="no-op; this step is always offline")
    parser.add_argument("--force", action="store_true", default=False,
                        help="with --apply: regenerate cert even if existing files are invalid")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true",
                      help="validate local cert state only (no changes, no cluster)")
    mode.add_argument("--dry-run", action="store_true",
                      help="report what would be done (no changes, no cluster)")
    mode.add_argument("--apply", action="store_true",
                      help="generate cert (if absent) and apply the Secret to the cluster")
    args = parser.parse_args()

    try:
        if args.check:
            return check()
        if args.dry_run:
            return dry_run()
        return apply(force=args.force)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
