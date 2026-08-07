#!/usr/bin/env python3
"""Validate HPDC Grafana dashboards and Alertmanager GitOps manifests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MON_BASE = ROOT / "gitops" / "monitoring" / "base" / "alertmanager.yaml"
DASHBOARDS = ROOT / "gitops" / "monitoring" / "base" / "grafana-dashboards.json"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def main() -> int:
    failures = []
    for path in [MON_BASE, DASHBOARDS, PLATFORM_SCAFFOLD]:
        if not path.is_file():
            failures.append(f"missing file: {path.relative_to(ROOT)}")

    try:
        json.loads(DASHBOARDS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        failures.append(f"grafana-dashboards.json invalid JSON: {e}")

    dashboards = DASHBOARDS.read_text(encoding="utf-8")
    for title in ["Platform Health", "Telemetry Throughput", "Alert Statistics", "Business Metrics"]:
        if f'"title": "{title}"' not in dashboards:
            failures.append(f"grafana-dashboards.json missing dashboard: {title}")

    am = MON_BASE.read_text(encoding="utf-8")
    required = [
        "kind: Namespace",
        "name: monitoring",
        "kind: AlertmanagerConfig",
        "name: platform-alertmanager",
        "stale_metric_warning_minutes: 5",
        "receiver: platform-email",
        "receiver: platform-webhook",
        "severity: critical",
        "name: alertmanager-routing",
        "name: stale-metric-warning",
        "StaleMetric",
        "for: 5m",
        "kind: Deployment",
        "name: alertmanager",
        "port: 9093",
        "kind: Service",
    ]
    for item in required:
        if item not in am:
            failures.append(f"alertmanager.yaml missing {item}")

    scaffold = PLATFORM_SCAFFOLD.read_text(encoding="utf-8")
    for binding in ["platform_health: true", "telemetry_throughput: true", "alert_statistics: true", "business_metrics: true", "stale_metric_warning_minutes: 5"]:
        if binding not in scaffold:
            failures.append(f"platform-scaffold.yaml missing {binding}")

    if failures:
        print("Grafana dashboards and Alertmanager validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Grafana dashboards and Alertmanager validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
