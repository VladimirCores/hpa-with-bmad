#!/usr/bin/env python3
"""Validate Epic 4 offline GitOps scaffold."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "gitops/epic4/base/epic4-offline-scaffold.yaml",
    "gitops/epic4/overlays/dev/kustomization.yaml",
    "gitops/epic4/overlays/staging/kustomization.yaml",
    "gitops/epic4/overlays/prod/kustomization.yaml",
    "scripts/validate-epic4-dev.py",
    "scripts/steps/29-install-epic4-dev.py",
    "scripts/steps/30-validate-epic4-dev.py",
]


def validate() -> None:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    assert not missing, missing

    manifest = (ROOT / "gitops/epic4/base/epic4-offline-scaffold.yaml").read_text(encoding="utf-8")
    for required in [
        "message CommonEnvelope",
        "topicType: partitioned",
        "partitions: 12",
        "ingestion_dropped_total",
        "batch_size: 25000",
        "flush_interval_ms: 500",
        "ORDER BY (device_type, processed_timestamp)",
        "default_ttl_seconds: 300",
        "kafka.consumer.lag",
        "topic: hpdc.alerts",
        "http_status: 409",
        "couchdb",
        "arcadedb",
        "yugabytedb",
        "vminsert",
        "vmlog",
        "opentelemetry_collector",
        "host: grafana.hpdc.local",
        "host: hubble.hpdc.local",
        "protocol: WireGuard",
        "default: disabled",
        "region_scoped: true",
        "security_policy: required",
        "unauthorized_prevented: true",
        "kind: Service",
        "name: mcp-tools",
        "kind: HorizontalPodAutoscaler",
    ]:
        assert required in manifest, required

    for overlay in ["dev", "staging", "prod"]:
        overlay_text = (ROOT / f"gitops/epic4/overlays/{overlay}/kustomization.yaml").read_text(encoding="utf-8")
        assert "../../base/epic4-offline-scaffold.yaml" in overlay_text, overlay


def test_validate_epic4_dev() -> None:
    validate()


def main() -> int:
    validate()
    subprocess.run([sys.executable, "scripts/validate-epic4-dev.py", "--offline", "--dry-run", "--check"], cwd=ROOT, check=True)
    print("Epic 4 offline GitOps scaffold validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
