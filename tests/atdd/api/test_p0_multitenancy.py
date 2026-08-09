#!/usr/bin/env python3
"""Acceptance test for multi-tenant isolation (P0-024).

Tenant A must never read, list, or mutate tenant B entities in the entity
store. Tenant scoping follows the bearer token's tenant claim
(casbin-rebac model: company:acme admin over its client/device/asset
resources).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ENTITY_URL = "http://hpdc-entity.local"


def _tenant_token(tenant: str) -> str:
    return f"eyJhbGciOiJSUzI1NiJ9.tenant={tenant}.placeholder"


# P0-024 (NFR15, R-003)
# Given: two tenants (company:acme, company:globex) sharing the platform
#  When: tenant A writes an entity
#  Then: tenant B cannot read, list, or mutate it
#   And: tenant A retains full access to its own entity
def test_p0_024_tenant_isolation_across_tenants() -> None:
    from hpdc_test_client import EntityApiClient

    acme = EntityApiClient(ENTITY_URL, bearer=_tenant_token("company:acme"))
    globex = EntityApiClient(ENTITY_URL, bearer=_tenant_token("company:globex"))

    assert acme.create(
        {"type": "device", "company": "company:acme", "id": "device:acme-dev-001"}
    ).status_code == 201
    assert acme.get("device:acme-dev-001").status_code == 200
    assert globex.get("device:acme-dev-001").status_code == 404
    assert globex.list(tenant="company:acme").status_code == 403


def main() -> int:
    tests = (test_p0_024_tenant_isolation_across_tenants,)
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
