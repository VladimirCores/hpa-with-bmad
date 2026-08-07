#!/usr/bin/env python3
"""Validate entity change feed processing, Epic 6 story 6-3."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "entity-change-processor.py"
FEED_DEF = ROOT / "gitops/entity-store/base/entity-change-feed.yaml"


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, HPDC_ENTITY_DATA_DIR=str(cwd))
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


def validate_manifests() -> None:
    feed = FEED_DEF.read_text(encoding="utf-8")
    overlay = (ROOT / "gitops/entity-store/overlays/dev/kustomization.yaml").read_text(encoding="utf-8")

    assert "kind: EntityChangeFeed" in feed
    assert "name: entity-change-feed" in feed
    assert "couchdb._changes" in feed
    assert "yugabytedb.cdc" in feed
    assert "reaction_time_ms: 500" in feed
    assert "knative: true" in feed
    assert "restate: true" in feed
    assert "exactly_once: true" in feed
    assert "source_change_id" in feed
    assert "hpdc.entity.dead.letter" in feed
    assert "kind: EntityChangeDedupe" in feed
    assert "entity-change-feed.yaml" in overlay


def test_process_couchdb_change() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        event = '{"source":"couchdb._changes","source_change_id":"c1","entity_id":"acme","change":{"doc_id":"acme","rev":"1-abc"}}'
        result = run(["process", event], cwd=cwd)
        assert result.returncode == 0
        processed = [json.loads(l) for l in (cwd / "processed.ndjson").read_text().splitlines()]
        assert processed[0]["source_change_id"] == "c1"
        assert processed[0]["processing"] == "knative+restate"
        assert processed[0]["exactly_once"] is True


def test_process_yugabyte_cdc() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        event = '{"source":"yugabytedb.cdc","source_change_id":"yb-1","entity_id":"dev-001","change":{"table":"entity_state"}}'
        result = run(["process", event], cwd=cwd)
        assert result.returncode == 0
        assert "processed" in result.stdout


def test_exactly_once_deduplication() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        event = '{"source":"couchdb._changes","source_change_id":"dup-1","entity_id":"acme","change":{}}'
        first = run(["process", event], cwd=cwd)
        assert first.returncode == 0
        second = run(["process", event], cwd=cwd)
        assert second.returncode == 0
        assert "already processed" in second.stdout
        processed = [json.loads(l) for l in (cwd / "processed.ndjson").read_text().splitlines()]
        assert len(processed) == 1


def test_unknown_source_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        event = '{"source":"pulsar","source_change_id":"p1","entity_id":"acme","change":{}}'
        result = run(["process", event], cwd=cwd)
        assert result.returncode != 0
        assert "Unknown change source" in result.stderr


def test_failure_routes_to_dlq() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        event = '{"source":"couchdb._changes","source_change_id":"fail-1","entity_id":"acme","change":{}}'
        result = run(["process", event, "--force-failure"], cwd=cwd)
        assert result.returncode != 0
        assert "dead letter" in result.stdout
        dlq = [json.loads(l) for l in (cwd / "dead_letter.ndjson").read_text().splitlines()]
        assert dlq[0]["result"] == "failed"


def main() -> int:
    validate_manifests()
    test_process_couchdb_change()
    test_process_yugabyte_cdc()
    test_exactly_once_deduplication()
    test_unknown_source_rejected()
    test_failure_routes_to_dlq()
    print("Entity change feed validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
