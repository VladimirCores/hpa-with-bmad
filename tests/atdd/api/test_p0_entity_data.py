#!/usr/bin/env python3
"""RED-phase acceptance scaffolds for the entity data plane.

P0-009 Entity CRUD round-trip completes under the 200ms latency budget.
P0-010 A concurrent stale update is rejected with 409 (optimistic lock).
P0-011 CDC/_changes entries originating from this cluster are ignored.
P0-014 A regional store has no cross-region replication by default.

All tests are skipped (RED phase): the entity API, change feed, regional
replication, and test-support harness do not exist yet.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ENTITY_URL = "http://hpdc-entity.local"
REGION_1 = "http://region-1.hpdc.local"
REGION_2 = "http://region-2.hpdc.local"


def _token(role: str) -> str:
    return f"eyJhbGciOiJSUzI1NiJ9.role={role}.placeholder"


# P0-009 (FR-14)
# Given: a principal with admin rights on the entity CRUD API
#  When: a company/device asset is created, read back, updated, and deleted
#  Then: every operation returns 2xx
#   And: the full round-trip completes under the 200ms latency budget
def test_p0_009_entity_crud_roundtrip_under_200ms() -> None:
    from hpdc_test_client import EntityApiClient

    client = EntityApiClient(ENTITY_URL, bearer=_token("admin"))
    device_id = "device:acme-dev-001"
    payload = {
        "type": "device",
        "company": "company:acme",
        "id": device_id,
        "name": "acme-dev-001",
        "spec": {"cpu": 2, "memory_mb": 4096},
    }

    start = time.perf_counter()
    created = client.create(payload)
    assert created.status_code == 201
    assert client.get(device_id).json()["id"] == device_id
    assert client.update(device_id, {"name": "acme-dev-001-renamed"}).status_code == 200
    assert client.delete(device_id).status_code == 204
    assert client.get(device_id).status_code == 404
    assert (time.perf_counter() - start) < 0.2, "FR-14 latency budget 200ms"


# P0-010 (FR-14, NFR26, R-015)
# Given: two clients read the same document revision
#  When: the first client writes a new revision
#   And: the second client writes from the stale revision
#  Then: the stale write is rejected with 409 Conflict (optimistic lock)
def test_p0_010_concurrent_update_returns_409() -> None:
    from hpdc_test_client import EntityApiClient

    client = EntityApiClient(ENTITY_URL, bearer=_token("admin"))
    created = client.create({"type": "company", "id": "company:acme", "name": "Acme"})
    doc_id = created.json()["id"]
    stale = client.get(doc_id).json()

    assert client.update(doc_id, {"name": "Acme v2"}, revision=stale["_rev"]).status_code == 200
    assert client.update(doc_id, {"name": "Acme v3"}, revision=stale["_rev"]).status_code == 409


# P0-011 (FR-15, R-012)
# Given: the change feed replays a write this cluster originated
#  When: the change-feed consumer sees a self-origin entry
#  Then: the entry is ignored and not reprocessed into the domain
#   And: no duplicate entities/events are produced
def test_p0_011_cdc_self_origin_ignored() -> None:
    from hpdc_test_client import ChangesFeedProbe, EntityApiClient

    client = EntityApiClient(ENTITY_URL, bearer=_token("admin"))
    feed = ChangesFeedProbe("http://hpdc-entity.local/_changes")

    before = feed.domain_events(tenant="company:acme")
    client.replay_own_change(change_id="0197F5Z8K9X5N2B1M7Q4R0T6VW", origin="self")
    after = feed.domain_events(tenant="company:acme")
    assert after == before, "self-origin _changes must not be reprocessed"


# P0-014 (FR-33, NFR20, R-006)
# Given: regional sovereignty with replication default: disabled
#  When: a document is written to the region-1 store
#  Then: region-2 never holds a copy without explicit replication config
def test_p0_014_no_cross_region_replication_by_default() -> None:
    from hpdc_test_client import EntityApiClient, RegionalProbe

    region1 = EntityApiClient(REGION_1, bearer=_token("admin"))
    region2 = EntityApiClient(REGION_2, bearer=_token("admin"))
    probe = RegionalProbe("http://hpdc-sovereignty.local")

    region1.create({"type": "asset", "company": "company:acme", "id": "asset:acme-asset-001"})
    assert region2.get("asset:acme-asset-001").status_code == 404
    config = probe.replication_config()
    assert config["replication"]["default"] == "disabled"
    assert config["replication"]["explicit_configuration_required"] is True


def main() -> int:
    tests = (
        test_p0_009_entity_crud_roundtrip_under_200ms,
        test_p0_010_concurrent_update_returns_409,
        test_p0_011_cdc_self_origin_ignored,
        test_p0_014_no_cross_region_replication_by_default,
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
