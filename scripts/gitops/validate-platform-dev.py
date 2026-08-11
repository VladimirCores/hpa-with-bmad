#!/usr/bin/env python3
"""Validate platform offline GitOps scaffolds."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"
DEPLOYMENTS = [
    ROOT / "gitops" / "platform" / "overlays" / overlay / "kustomization.yaml"
    for overlay in ["dev", "staging", "prod"]
]
REQUIRED_FILES = [SCAFFOLD, *DEPLOYMENTS]
REQUIRED_TEXT = [
    "name: telemetry-common-envelope",
    "schema.proto",
    "message CommonEnvelope",
    "idempotency_key",
    "origin",
    "name: pulsar-topic-policy",
    "device_type,region_id",
    "name: telemetry-normalized",
    "topicType: partitioned",
    "partitions: 12",
    "name: hpdc-telemetry-backpressure-policy",
    "max_consumer_lag: 50000",
    "ingestion_dropped_total",
    "name: telemetry-windowed-aggregator",
    "batch_size: 25000",
    "flush_interval_ms: 500",
    "max_retries: 3",
    "name: device_metrics",
    "ENGINE = ReplacingMergeTree",
    "ORDER BY (device_type, processed_timestamp)",
    "retention:",
    "dev: 24h",
    "staging: 7d",
    "prod: configurable",
    "storage_class: hpdc-ceph",
    "name: hot-device-state-and-alert-context",
    "default_ttl_seconds: 300",
    "fallback_stores:",
    "couchdb",
    "clickhouse",
    "yugabytedb",
    "name: event-telemetry-transform",
    "topic: hpdc.telemetry.events",
    "kafka.consumer.lag",
    "latency_budget_ms: 10",
    "name: directed-alert-signals",
    "topic: hpdc.alerts",
    "alert_id",
    "name: alert-state-machine",
    "initial",
    "acknowledged",
    "investigating",
    "resolved",
    "closed",
    "http_status: 409",
    "name: alert-response-engine",
    "device_communication_latency_ms: 200",
    "webhook_delivery_latency_ms: 500",
    "webhook_attempts: 3",
    "name: alert-audit-trail",
    "prevent_same_state_update: true",
    "name: llm-decision-support",
    "execute_without_approval: false",
    "name: entity-hierarchy-store",
    "couchdb",
    "arcadedb",
    "yugabytedb",
    "name: entity-crud-and-bulk-operations",
    "bulk_limit: 1000",
    "name: entity-change-feed",
    "knative: true",
    "restate: true",
    "exactly_once: true",
    "name: cross-store-entity-graphql",
    "endpoint: /gql",
    "latency_budget_ms: 2000",
    "name: platform-observability-pipeline",
    "vmstorage",
    "vminsert",
    "vmselect",
    "vmlog",
    "opentelemetry_collector",
    "name: grafana-hubble-tool-ui-routes",
    "host: grafana.hpdc.local",
    "host: hubble.hpdc.local",
    "casdoor_casbin_ext_authz: false",
    "name: regional-clustermesh",
    "protocol: WireGuard",
    "encrypted: true",
    "name: regional-data-sovereignty",
    "default: disabled",
    "explicit_configuration_required: true",
    "name: regional-apis",
    "region_scoped: true",
    "name: platform-capabilities-mcp-tools",
    "security_policy: required",
    "name: authenticated-agent-communication",
    "unauthorized_prevented: true",
    "kind: Service",
    "name: telemetry-normalizer",
    "name: pulsar-functions",
    "name: clickhouse-sink",
    "name: keydb-cache",
    "name: spin-functions",
    "name: alert-api",
    "name: entity-api",
    "name: observability-ui",
    "name: regional-apis",
    "name: mcp-tools",
    "kind: HorizontalPodAutoscaler",
]


def validate() -> list[str]:
    failures: list[str] = []
    missing_files = [str(path.relative_to(ROOT)) for path in REQUIRED_FILES if not path.exists()]
    if missing_files:
        failures.extend(f"missing file: {path}" for path in missing_files)

    if not SCAFFOLD.exists():
        return failures

    manifest = SCAFFOLD.read_text(encoding="utf-8")
    for item in REQUIRED_TEXT:
        if item not in manifest:
            failures.append(f"platform-scaffold.yaml missing {item}")

    for overlay in DEPLOYMENTS:
        overlay_text = overlay.read_text(encoding="utf-8")
        if "../../base/platform-scaffold.yaml" not in overlay_text:
            failures.append(f"{overlay.relative_to(ROOT)} missing platform base resource")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate platform offline GitOps scaffold")
    parser.add_argument("--offline", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.check:
        failures = validate()
        if failures:
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("Platform offline GitOps scaffold validation passed.")
        return 0

    failures = validate()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1

    if args.apply:
        print("Platform apply requested.")
        for overlay in DEPLOYMENTS:
            print(f"GitOps overlay: {overlay.relative_to(ROOT)}")
        return 0

    if args.dry_run:
        print("Platform dry-run passed.")
        print("Telemetry, alert, entity, observability, regional, and AI-agent GitOps scaffolds are configured.")
        for overlay in DEPLOYMENTS:
            print(f"GitOps overlay: {overlay.relative_to(ROOT)}")
        return 0

    print("Platform validation requires --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
