# Story 7-4: Configure Grafana dashboards and Alertmanager

Status: done

Baseline commit: c28e2e6

## Story

As a Platform Administrator,
I want Grafana dashboards and AlertManager routing configured,
so that platform health, telemetry throughput, alert statistics, and business metrics are visible, and alerts route to configured channels with stale-metric warnings.

## Acceptance Criteria

1. Given a metrics source, when Grafana is provisioned, then dashboards for platform health, telemetry throughput, and alert statistics are pre-configured.
2. Given business data, when Grafana is provisioned, then business dashboards (alert throughput, device coverage, SLA compliance) are available.
3. Given an alert, when it is raised, then AlertManager routes it per configured routing rules.
4. Given a stale metric, when it stops reporting, then AlertManager raises a stale-metric warning within the configured 5-minute window.
5. Given the platform contract, when deployed, then the dashboards component binds `platform_health: true`, `telemetry_throughput: true`, `alert_statistics: true`, and `business_metrics: true`.

## Implementation Plan

- Add Grafana dashboard provisioning JSON and AlertManager manifests under `gitops/monitoring/base/`.
- Declare the Grafana dashboard config, AlertManager Deployment/Service, and routing ConfigMap.
- Install script with `--check` / `--dry-run` / `--apply`, step wrapper, and validation test.

## Files

- `gitops/monitoring/base/grafana-dashboards.json` (new)
- `gitops/monitoring/base/alertmanager.yaml` (new)
- `scripts/install-grafana-alertmanager-dev.py` (new)
- `scripts/steps/38-install-grafana-alertmanager-dev.py` (new)
- `tests/test_install_grafana_alertmanager_dev.py` (new)
