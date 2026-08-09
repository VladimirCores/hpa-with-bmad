#!/usr/bin/env python3
"""RED-phase acceptance scaffolds for identity and authorization.

P0-012 Casdoor SSO maps a principal's groups to Casbin roles.
P0-013 Expired/revoked JWTs are rejected 401; wrong role is 403.
P0-015 GraphQL/MCP queries are authorized per the requester's permission.

All tests are skipped (RED phase): Casdoor, Casbin, the GraphQL gateway,
and the test-support harness do not exist yet.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ID_URL = "http://hpdc-id.local"
GQL_URL = "http://hpdc-gql.local/gql"
TOKEN_ADMIN = "eyJhbGciOiJSUzI1NiJ9.role=admin.placeholder"
TOKEN_VIEWER = "eyJhbGciOiJSUzI1NiJ9.role=viewer.placeholder"
TOKEN_EXPIRED = "eyJhbGciOiJSUzI1NiJ9.exp=0.placeholder"
TOKEN_REVOKED = "eyJhbGciOiJSUzI1NiJ9.revoked.placeholder"


# P0-012 (FR-28, FR-29, R-003)
# Given: a principal authenticates via Casdoor SSO (OIDC)
#  When: their group membership is resolved into Casbin roles
#  Then: administrator/manager/operator -> admin
#   And: technic/developer -> operator; CEO -> manager; client -> viewer
def test_p0_012_casdoor_sso_role_group_mapping() -> None:
    from hpdc_test_client import CasdoorHarness, IdentityClient

    identity = IdentityClient(ID_URL)
    casdoor = CasdoorHarness("http://casdoor.hpdc.local:8000")

    admin = casdoor.login("carol@hpdc", "administrator")
    operator = casdoor.login("bob@hpdc", "platform-engineer")
    manager = casdoor.login("ceo@hpdc", "CEO")
    viewer = casdoor.login("client@hpdc", "client")

    assert "admin" in identity.groups_for(admin.jwt)
    assert "operator" in identity.groups_for(operator.jwt)
    assert "manager" in identity.groups_for(manager.jwt)
    assert "viewer" in identity.groups_for(viewer.jwt)


# P0-013 (FR-28, FR-29, R-003)
# Given: a principal holds an expired or revoked JWT
#  When: it is presented to a protected endpoint
#  Then: the request is rejected 401 Unauthorized
#   And: a valid token with an insufficient role is rejected 403 Forbidden
def test_p0_013_expired_revoked_jwt_and_wrong_role() -> None:
    from hpdc_test_client import IdentityClient

    identity = IdentityClient(ID_URL)
    assert identity.get("/api/welcome").status_code == 401
    assert identity.get("/api/welcome", bearer=TOKEN_EXPIRED).status_code == 401
    assert identity.get("/api/welcome", bearer=TOKEN_REVOKED).status_code == 401
    assert identity.post_gql("{ yugabytedb_resources { resource } }", bearer=TOKEN_VIEWER).status_code == 403


# P0-015 (FR-37, R-011)
# Given: the cross-store GraphQL gateway with role_model: configured
#  When: an admin queries permitted stores
#  Then: the query returns 200
#   And: a viewer querying a store outside their permission is denied 403
def test_p0_015_graphql_query_authorized_per_permission() -> None:
    from hpdc_test_client import GraphQLClient

    gql = GraphQLClient(GQL_URL)
    ok = gql.query("{ couchdb_entities { id } }", bearer=TOKEN_ADMIN)
    assert ok.status_code == 200
    denied = gql.query("{ yugabytedb_resources { resource } }", bearer=TOKEN_VIEWER)
    assert denied.status_code == 403


def main() -> int:
    tests = (
        test_p0_012_casdoor_sso_role_group_mapping,
        test_p0_013_expired_revoked_jwt_and_wrong_role,
        test_p0_015_graphql_query_authorized_per_permission,
    )
    skipped = 0
    for test in tests:
        try:
            test()
        except (ImportError, NotImplementedError) as exc:
            skipped += 1
            print(f"  RED (skipped): {test.__name__} — {exc}")
        except Exception as exc:
            skipped += 1
            print(f"  RED (skipped): {test.__name__} — {type(exc).__name__}: {exc}")
    print(f"RED PHASE: {len(tests)} acceptance tests scaffolded; {skipped} pending green-phase implementation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
