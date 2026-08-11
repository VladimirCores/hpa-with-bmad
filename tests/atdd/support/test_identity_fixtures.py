#!/usr/bin/env python3
"""B-002 identity fixtures: api_key_fixture, jwt_fixture, JWKS, role catalog.

Validates the tests/atdd/support/fixtures.py identity contracts that unblock
P0-012/013/024 and the REG-02 live JWKS path once a cluster exists:

- api_key_fixture mirrors gitops/security/base/api-key-authn.yaml (parity guard)
- jwt_fixture signs real RS256 tokens with Casdoor claims and a JWKS that
  verifies them (REG-02: casdoor.hpdc.local/.well-known/jwks.json)
- the 7 role->group identities resolve to the Casbin roles a live Casdoor maps
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SUPPORT = Path(__file__).resolve().parent
if str(SUPPORT) not in sys.path:
    sys.path.insert(0, str(SUPPORT))

from fixtures import (  # noqa: E402
    CASDOOR_ISSUER,
    CASDOOR_ROLES,
    CASDOOR_USERS,
    GATEWAY_AUDIENCE,
    JWT_KID,
    api_key_fixture,
    jwt_fixture,
    jwks_fixture,
    role_for_group,
    verify_jwt,
)


def test_api_key_fixture_kinds() -> None:
    assert api_key_fixture("events") == "hpdc-events-dev-key"
    assert api_key_fixture("telemetry") == "hpdc-telemetry-dev-key"


def test_api_key_fixture_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError):
        api_key_fixture("nonexistent")


def test_api_key_fixture_parity_with_manifest() -> None:
    from fixtures import _api_key_manifest_parity_check

    assert _api_key_manifest_parity_check(), (
        "api_key_fixture values drifted from gitops/security/base/api-key-authn.yaml"
    )


def test_seven_roles_catalog() -> None:
    assert len(CASDOOR_USERS) == 7
    assert tuple(user.group for user in CASDOOR_USERS) == CASDOOR_ROLES


def test_role_for_group_mapping() -> None:
    mapping = {
        "administrator": "admin",
        "manager": "admin",
        "operator": "admin",
        "technic": "operator",
        "developer": "operator",
        "platform-engineer": "operator",
        "CEO": "manager",
        "client": "viewer",
        "unknown": "viewer",
    }
    for group, expected in mapping.items():
        assert role_for_group(group) == expected


def test_casdoor_users_roles_match_mapping() -> None:
    for user in CASDOOR_USERS:
        assert user.role == role_for_group(user.group)


def test_jwt_fixture_signs_and_verifies() -> None:
    token = jwt_fixture("administrator", email="carol@hpdc")
    claims = verify_jwt(token)
    assert claims["group"] == "administrator"
    assert claims["role"] == "admin"
    assert claims["iss"] == CASDOOR_ISSUER
    assert claims["aud"] == GATEWAY_AUDIENCE
    assert claims["sub"] == "carol@hpdc"


def test_jwt_fixture_expired_rejected() -> None:
    token = jwt_fixture("client", expired=True)
    with pytest.raises(ValueError):
        verify_jwt(token)


def test_jwt_fixture_revoked_rejected() -> None:
    token = jwt_fixture("CEO", revoked=True)
    with pytest.raises(ValueError):
        verify_jwt(token)


def test_jwt_fixture_audience_mismatch_rejected() -> None:
    token = jwt_fixture("operator", audience="some-other-audience")
    with pytest.raises(ValueError):
        verify_jwt(token, audience=GATEWAY_AUDIENCE)


def test_jwks_fixture_serves_signing_key() -> None:
    jwks = jwks_fixture()
    keys = jwks["keys"]
    assert len(keys) == 1
    key = keys[0]
    assert key["kty"] == "RSA"
    assert key["kid"] == JWT_KID
    assert key["alg"] == "RS256"
    assert key["use"] == "sig"
    assert key["n"]
    assert key["e"]


def test_all_seven_roles_issue_verifiable_tokens() -> None:
    for user in CASDOOR_USERS:
        token = jwt_fixture(user.group, email=user.email)
        claims = verify_jwt(token)
        assert claims["role"] == user.role
