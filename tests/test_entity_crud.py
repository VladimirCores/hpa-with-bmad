#!/usr/bin/env python3
"""Validate entity CRUD and bulk operations, Epic 6 story 6-2."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "services" / "entity-api.py"
CRUD_DEF = ROOT / "gitops/entity-store/base/entity-crud.yaml"


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, HPDC_ENTITY_DATA_DIR=str(cwd))
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


def validate_manifests() -> None:
    crud = CRUD_DEF.read_text(encoding="utf-8")
    overlay = (ROOT / "gitops/entity-store/overlays/dev/kustomization.yaml").read_text(encoding="utf-8")

    assert "kind: EntityCrud" in crud
    assert "name: entity-crud-and-bulk-operations" in crud
    assert "bulk_limit: 1000" in crud
    assert "latency_budget_ms: 200" in crud
    assert "- company" in crud
    assert "- client" in crud
    assert "- device" in crud
    assert "- asset" in crud
    assert "actor: required" in crud
    assert "timestamp: required" in crud
    assert "change_diff: required" in crud
    assert "kind: EntityMutationAudit" in crud
    assert "name: entity-api" in crud
    assert "kind: Service" in crud
    assert "kind: Deployment" in crud
    assert "entity-crud.yaml" in overlay


def test_create_and_read() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        result = run(["create", "company", "acme", "--data", '{"name":"Acme Corp","region":"eu-central"}', "--actor", "alice@hpdc"], cwd=cwd)
        assert result.returncode == 0
        result = run(["read", "company", "acme", "--actor", "alice@hpdc"], cwd=cwd)
        assert result.returncode == 0
        entity = json.loads(result.stdout)
        assert entity["entity_type"] == "company"
        assert entity["name"] == "Acme Corp"

        mutations = [json.loads(l) for l in (cwd / "mutations.ndjson").read_text().splitlines()]
        create_log = mutations[0]
        assert create_log["operation"] == "create"
        assert create_log["actor"] == "alice@hpdc"
        assert create_log["change_diff"]["name"]["to"] == "Acme Corp"


def test_update_logs_change_diff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        run(["create", "device", "dev-001", "--data", '{"status":"online"}', "--actor", "alice@hpdc"], cwd=cwd)
        result = run(["update", "device", "dev-001", "--data", '{"status":"offline"}', "--actor", "bob@hpdc"], cwd=cwd)
        assert result.returncode == 0

        mutations = [json.loads(l) for l in (cwd / "mutations.ndjson").read_text().splitlines()]
        update_log = mutations[-1]
        assert update_log["operation"] == "update"
        assert update_log["change_diff"]["status"] == {"from": "online", "to": "offline"}


def test_delete() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        run(["create", "client", "client-1", "--data", '{"name":"Widgets"}', "--actor", "alice@hpdc"], cwd=cwd)
        result = run(["delete", "client", "client-1", "--actor", "carol@hpdc"], cwd=cwd)
        assert result.returncode == 0
        result = run(["read", "client", "client-1", "--actor", "alice@hpdc"], cwd=cwd)
        assert result.returncode != 0


def test_unauthorized_delete_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        run(["create", "asset", "asset-1", "--data", '{"name":"Rig"}', "--actor", "alice@hpdc"], cwd=cwd)
        result = run(["delete", "asset", "asset-1", "--actor", "bob@hpdc"], cwd=cwd)
        assert result.returncode != 0
        mutations = [json.loads(l) for l in (cwd / "mutations.ndjson").read_text().splitlines()]
        assert mutations[-1]["result"] == "unauthorized"


def test_bulk_within_limit() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        operations = [
            {"operation": "create", "entity_type": "device", "entity_id": f"dev-{i}", "data": {"status": "provisioned"}}
            for i in range(5)
        ]
        result = run(["bulk", "--operations", json.dumps(operations), "--actor", "alice@hpdc"], cwd=cwd)
        assert result.returncode == 0
        mutations = [json.loads(l) for l in (cwd / "mutations.ndjson").read_text().splitlines()]
        creates = [m for m in mutations if m["operation"] == "create"]
        assert len(creates) == 5


def test_bulk_over_limit_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        operations = [{"operation": "create", "entity_type": "device", "entity_id": f"dev-{i}", "data": {}} for i in range(1001)]
        result = run(["bulk", "--operations", json.dumps(operations), "--actor", "alice@hpdc"], cwd=cwd)
        assert result.returncode != 0


def main() -> int:
    validate_manifests()
    test_create_and_read()
    test_update_logs_change_diff()
    test_delete()
    test_unauthorized_delete_rejected()
    test_bulk_within_limit()
    test_bulk_over_limit_rejected()
    print("Entity CRUD validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
