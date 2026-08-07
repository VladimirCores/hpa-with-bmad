#!/usr/bin/env python3
"""Validate cross-store GraphQL gateway, Epic 6 story 6-4."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "graphql-gateway.py"
GATEWAY_DEF = ROOT / "gitops/entity-store/base/graphql-gateway.yaml"


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, HPDC_ENTITY_DATA_DIR=str(cwd))
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


def validate_manifests() -> None:
    gateway = GATEWAY_DEF.read_text(encoding="utf-8")
    overlay = (ROOT / "gitops/entity-store/overlays/dev/kustomization.yaml").read_text(encoding="utf-8")

    assert "kind: HasuraGraphQL" in gateway
    assert "name: cross-store-entity-graphql" in gateway
    assert "endpoint: /gql" in gateway
    assert "couchdb_entities: true" in gateway
    assert "yugabytedb_resources: true" in gateway
    assert "clickhouse_telemetry: true" in gateway
    assert "latency_budget_ms: 2000" in gateway
    assert "role_model: configured" in gateway
    assert "kind: Deployment" in gateway
    assert "name: graphql-gateway" in gateway
    assert "kind: Service" in gateway
    assert "kind: HTTPRoute" in gateway
    assert "value: /gql" in gateway
    assert "graphql-gateway.yaml" in overlay


def test_cross_store_query_admin() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        query = "{ couchdb_entities { id } yugabytedb_resources { resource } }"
        result = run(["query", query, "--role", "admin"], cwd=cwd)
        assert result.returncode == 0
        assert "couchdb_entities, yugabytedb_resources" in result.stdout
        logged = [json.loads(l) for l in (cwd / "graphql_queries.ndjson").read_text().splitlines()]
        assert logged[0]["result"] == "success"


def test_clickhouse_federation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        query = "{ couchdb_entities { id } clickhouse_telemetry { metric } }"
        result = run(["query", query, "--role", "admin"], cwd=cwd)
        assert result.returncode == 0
        assert "clickhouse_telemetry" in result.stdout


def test_viewer_blocked_from_yugabyte_resources() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        query = "{ yugabytedb_resources { resource } }"
        result = run(["query", query, "--role", "viewer"], cwd=cwd)
        assert result.returncode != 0
        assert "Unauthorized" in result.stderr
        logged = [json.loads(l) for l in (cwd / "graphql_queries.ndjson").read_text().splitlines()]
        assert logged[0]["result"] == "unauthorized"


def test_unknown_store_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        query = "{ pulsar_topics { name } }"
        result = run(["query", query, "--role", "admin"], cwd=cwd)
        assert result.returncode != 0
        assert "no known cross-store sources" in result.stderr


def test_latency_budget_enforced() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        query = "{ couchdb_entities { id } }"
        result = run(["query", query, "--role", "admin", "--simulate-slow"], cwd=cwd)
        assert result.returncode != 0
        assert "exceeded" in result.stderr


def main() -> int:
    validate_manifests()
    test_cross_store_query_admin()
    test_clickhouse_federation()
    test_viewer_blocked_from_yugabyte_resources()
    test_unknown_store_rejected()
    test_latency_budget_enforced()
    print("GraphQL gateway validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
