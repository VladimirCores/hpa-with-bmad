#!/usr/bin/env python3
"""ATDD fixture infrastructure for HPDC P0 scaffolds (B-002 identity fixtures).

Shared credentials, URLs, role catalog, and helper contracts the tests/atdd/
scaffolds reference. The green-phase implementation must satisfy these
contracts:

- hpdc_test_client: the API test client module the scaffolds import
- pulsar_consumer_harness: message-arrival assertions for internal topics
- clickhouse_probe: latency/round-trip assertions for telemetry
- api_key_fixture: X-API-Key credentials mirroring
  gitops/security/base/api-key-authn.yaml (P0-001..003, P0-016)
- jwt_fixture: real RS256-signed Casdoor-style JWTs for the 7 role->group
  identities (P0-012, P0-013, P0-024) plus a matching JWKS export so the
  tokens are verifiable against the same contract a live cluster serves
  (REG-02: casdoor.hpdc.local/.well-known/jwks.json)

All values here mirror the deployed manifests under gitops/.
"""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

EVENTS_API_KEY = "hpdc-events-dev-key"
TELEMETRY_API_KEY = "hpdc-telemetry-dev-key"

EDGE_URL = "http://hpdc-edge.local"
CLICKHOUSE_URL = "http://clickhouse.local:8123"
PULSAR_URL = "pulsar://pulsar.local:6650"
KAFKA_URL = "kafka.local:9092"

CASDOOR_ROLES = (
    "operator",
    "manager",
    "administrator",
    "technic",
    "developer",
    "CEO",
    "client",
)

CASDOOR_ISSUER = "https://casdoor.hpdc.local"
CASDOOR_JWKS_URI = f"{CASDOOR_ISSUER}/.well-known/jwks.json"
GATEWAY_AUDIENCE = "hpdc-graphql-gateway"
JWT_KID = "hpdc-dev-jwt-key"


def api_key_fixture(kind: str = "events") -> str:
    """X-API-Key credential mirroring gitops/security/base/api-key-authn.yaml.

    ``kind`` is ``events`` (covers /data /api /events) or ``telemetry``
    (covers /telemetry HTTP + gRPC). Used by P0-001..003 and P0-016.
    """
    keys = {
        "events": EVENTS_API_KEY,
        "telemetry": TELEMETRY_API_KEY,
    }
    if kind not in keys:
        raise ValueError(f"unknown api-key kind: {kind!r}")
    return keys[kind]


@dataclass(frozen=True)
class CasdoorUser:
    """A Casdoor principal and the Casbin role its group resolves to."""

    email: str
    group: str
    role: str


# The 7 role->group identities (checklist B-002): one principal per role,
# mirroring scripts/identity-authz-local.py role_for_group() mapping and the
# users exercised by tests/atdd/api/test_p0_identity_auth.py.
CASDOOR_USERS: tuple[CasdoorUser, ...] = (
    CasdoorUser(email="alice@hpdc", group="operator", role="admin"),
    CasdoorUser(email="dave@hpdc", group="manager", role="admin"),
    CasdoorUser(email="carol@hpdc", group="administrator", role="admin"),
    CasdoorUser(email="erin@hpdc", group="technic", role="operator"),
    CasdoorUser(email="frank@hpdc", group="developer", role="operator"),
    CasdoorUser(email="ceo@hpdc", group="CEO", role="manager"),
    CasdoorUser(email="client@hpdc", group="client", role="viewer"),
)


def role_for_group(group: str | None) -> str:
    """Resolve a Casdoor group to the Casbin role (parity with
    scripts/identity-authz-local.py::role_for_group)."""
    normalized = (group or "").lower().replace("_", "-")
    if normalized in ("administrator", "manager", "operator"):
        return "admin"
    if normalized in ("technic", "developer", "platform-engineer"):
        return "operator"
    if normalized in ("ceo", "chief-executive-officer"):
        return "manager"
    return "viewer"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _load_private_key() -> rsa.RSAPrivateKey:
    """Load or lazily generate the dev signing key (deterministic per process).

    The keypair is dev-only; its public part is what jwks_fixture() exposes,
    matching the REG-02 contract that a live cluster serves the public JWKS at
    casdoor.hpdc.local/.well-known/jwks.json. Tests only ever verify against
    the fixture's own public key, never against the private key.
    """
    key = _load_private_key.__dict__.get("_key")
    if key is None:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        _load_private_key.__dict__["_key"] = key
    return key


def jwt_fixture(
    group: str,
    *,
    email: str | None = None,
    audience: str = GATEWAY_AUDIENCE,
    ttl_s: int = 3600,
    expired: bool = False,
    revoked: bool = False,
) -> str:
    """Sign a real RS256 JWT for a Casdoor group (P0-012/013/024, B-002).

    Claims mirror what a live Casdoor issues: iss, aud, sub, email, group,
    resolved role, iat/nbf/exp, jti. ``expired`` sets exp in the past;
    ``revoked`` adds a revocation claim. Returns a three-part JWT whose
    signature verifies against jwks_fixture().
    """
    role = role_for_group(group)
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": CASDOOR_ISSUER,
        "aud": audience,
        "sub": email or group,
        "email": email or f"{group}@hpdc",
        "group": group,
        "role": role,
        "iat": now,
        "nbf": now - 5,
        "exp": now - 60 if expired else now + ttl_s,
        "jti": uuid.uuid4().hex,
    }
    if revoked:
        claims["revoked"] = True
    header = {"alg": "RS256", "typ": "JWT", "kid": JWT_KID}
    signing_input = (
        _b64url(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + _b64url(json.dumps(claims, separators=(",", ":")).encode())
    )
    signature = _load_private_key().sign(
        signing_input.encode("ascii"), padding.PKCS1v15(), hashes.SHA256()
    )
    return f"{signing_input}.{_b64url(signature)}"


def jwks_fixture() -> dict[str, object]:
    """Public JWKS for the dev signing key (REG-02 groundwork).

    Exposes the same contract a live cluster serves at
    casdoor.hpdc.local/.well-known/jwks.json: a single RS256 key with kid.
    """
    public = _load_private_key().public_key().public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": JWT_KID,
                "alg": "RS256",
                "use": "sig",
                "n": _b64url(public.n.to_bytes((public.n.bit_length() + 7) // 8, "big")),
                "e": _b64url(public.e.to_bytes((public.e.bit_length() + 7) // 8, "big")),
            }
        ]
    }


def verify_jwt(token: str, audience: str = GATEWAY_AUDIENCE) -> dict[str, object]:
    """Verify a fixture JWT against the dev public key; return claims.

    Raises ValueError on bad signature, expired (exp) or revoked tokens —
    the same outcomes a live gateway applies per REG-02.
    """
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise ValueError("malformed JWT") from exc
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = base64.urlsafe_b64decode(signature_b64 + "=" * (-len(signature_b64) % 4))
    _load_private_key().public_key().verify(
        signature, signing_input, padding.PKCS1v15(), hashes.SHA256()
    )
    claims = json.loads(base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)))
    if claims.get("revoked"):
        raise ValueError("token revoked")
    exp = int(claims.get("exp", 0))
    if exp and exp < time.time():
        raise ValueError("token expired")
    if audience and claims.get("aud") != audience:
        raise ValueError(f"audience mismatch: {claims.get('aud')!r}")
    return claims


@dataclass(frozen=True)
class Envelope:
    device_id: str
    device_type: str
    event_type: str
    timestamp: str
    payload: dict
    region_id: str


def envelope(device_id: str = "sensor-93d21f", device_type: str = "sensor") -> Envelope:
    return Envelope(
        device_id=device_id,
        device_type=device_type,
        event_type="temperature.reading",
        timestamp="2026-08-07T13:15:47.123Z",
        payload={"temperature_c": 21.7, "humidity_pct": 48.2},
        region_id="region-1",
    )


def _api_key_manifest_parity_check() -> bool:
    """Confirm fixture API keys still match the gitops manifest (drift guard)."""
    manifest = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "..",
        "..",
        "gitops",
        "security",
        "base",
        "api-key-authn.yaml",
    )
    try:
        import yaml  # noqa: PLC0415

        with open(manifest, encoding="utf-8") as fh:
            docs = list(yaml.safe_load_all(fh))
    except Exception:  # noqa: BLE001 - parity guard must not crash test discovery
        return False
    values: dict[str, str] = {}
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        if doc.get("kind") == "Secret" and doc.get("metadata", {}).get("name") in (
            "events-api-key",
            "telemetry-api-key",
        ):
            data = doc.get("stringData", {}) or {}
            values.update(data)
    return values.get("events-key") == EVENTS_API_KEY and values.get("telemetry-key") == TELEMETRY_API_KEY


@dataclass(frozen=True)
class Envelope:
    device_id: str
    device_type: str
    event_type: str
    timestamp: str
    payload: dict
    region_id: str


def envelope(device_id: str = "sensor-93d21f", device_type: str = "sensor") -> Envelope:
    return Envelope(
        device_id=device_id,
        device_type=device_type,
        event_type="temperature.reading",
        timestamp="2026-08-07T13:15:47.123Z",
        payload={"temperature_c": 21.7, "humidity_pct": 48.2},
        region_id="region-1",
    )
