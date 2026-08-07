# Story 7-3: Export distributed traces with OpenTelemetry Collector

Status: done

Baseline commit: 3707054

## Story

As a Platform Administrator,
I want distributed traces exported via OpenTelemetry Collector,
so that instrumented services can send OTLP traces to a standard collector endpoint with configurable sampling and a configured backend.

## Acceptance Criteria

1. Given an instrumented service, when it emits traces, then the collector accepts OTLP traces on the standard collector endpoint.
2. Given received traces, when processed, then they are exported to the configured backend (VictoriaMetrics).
3. Given a service, when configured, then trace sampling supports a configurable rate per service.
4. Given the platform contract, when deployed, then the traces component binds `opentelemetry_collector: true`.
5. Given a network request, when it targets the collector, then it is reachable via a stable Service endpoint.

## Implementation Plan

- Add OpenTelemetry Collector component under `gitops/victoria-metrics/base/`.
- Declare the collector ConfigMap (OTLP receiver, VictoriaMetrics exporter, per-service sampling), Deployment, and Service.
- Install script with `--check` / `--dry-run` / `--apply`, step wrapper, and validation test.

## Files

- `gitops/victoria-metrics/base/otel-collector.yaml` (new)
- `scripts/install-otel-collector-dev.py` (new)
- `scripts/steps/37-install-otel-collector-dev.py` (new)
- `tests/test_install_otel_collector_dev.py` (new)
