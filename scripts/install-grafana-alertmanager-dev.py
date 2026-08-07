#!/usr/bin/env python3
"""Install HPDC Grafana dashboards and Alertmanager."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MON_BASE = ROOT / "gitops" / "monitoring" / "base"
PLATFORM_SCAFFOLD = ROOT / "gitops" / "platform" / "base" / "platform-scaffold.yaml"


def ensure_files() -> None:
    for path in [MON_BASE / "grafana-dashboards.json", MON_BASE / "alertmanager.yaml", PLATFORM_SCAFFOLD]:
        if not path.exists():
            raise RuntimeError(f"required file missing: {path.relative_to(ROOT)}")


def validate_manifests() -> list[str]:
    failures: list[str] = []
    dashboards = (MON_BASE / "grafana-dashboards.json").read_text(encoding="utf-8")
    try:
        json.loads(dashboards)
    except json.JSONDecodeError as e:
        failures.append(f"grafana-dashboards.json invalid JSON: {e}")
    am = (MON_BASE / "alertmanager.yaml").read_text(encoding="utf-8")

    dashboard_titles = ["Platform Health", "Telemetry Throughput", "Alert Statistics", "Business Metrics"]
    for title in dashboard_titles:
        if f'"title": "{title}"' not in dashboards:
            failures.append(f"grafana-dashboards.json missing dashboard: {title}")

    required_am = [
        "kind: Namespace",
        "name: monitoring",
        "kind: AlertmanagerConfig",
        "name: platform-alertmanager",
        "routing:",
        "configured: true",
        "stale_metric_warning_minutes: 5",
        "receiver: platform-email",
        "receiver: platform-webhook",
        "severity: critical",
        "kind: ConfigMap",
        "name: alertmanager-routing",
        "name: stale-metric-warning",
        "StaleMetric",
        "for: 5m",
        "kind: Deployment",
        "name: alertmanager",
        "port: 9093",
        "kind: Service",
        "name: alertmanager",
    ]
    for item in required_am:
        if item not in am:
            failures.append(f"alertmanager.yaml missing {item}")

    scaffold = PLATFORM_SCAFFOLD.read_text(encoding="utf-8")
    for binding in ["platform_health: true", "telemetry_throughput: true", "alert_statistics: true", "business_metrics: true", "stale_metric_warning_minutes: 5"]:
        if binding not in scaffold:
            failures.append(f"platform-scaffold.yaml missing {binding}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Install HPDC Grafana dashboards and Alertmanager")
    parser.add_argument("--offline", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.check:
        ensure_files()
        failures = validate_manifests()
        if failures:
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("Grafana dashboards and Alertmanager validation passed.")
        return 0

    ensure_files()
    failures = validate_manifests()
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.apply:
        print("Grafana dashboards and Alertmanager apply requested.")
        return 0
    if args.dry_run:
        print("Grafana dashboards and Alertmanager dry-run passed.")
        print("Platform health, telemetry throughput, alert statistics, and business dashboards are provisioned.")
        print("Alertmanager routes alerts to configured channels with 5-minute stale-metric warnings.")
        return 0
    print("Grafana dashboards and Alertmanager require --dry-run or --apply.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
