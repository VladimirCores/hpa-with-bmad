# Story 7-2: Collect logs with VMLogs

Status: done

Baseline commit: 854d6f7

## Story

As a Platform Administrator,
I want logs collected by VMLogs with searchable within-seconds freshness,
so that platform and workload logs are queryable centrally with sub-5-second search freshness.

## Acceptance Criteria

1. Given a log source, when emitted, then VMLogs ingests it via the vmagent/vmsingle-compatible log endpoint.
2. Given a log query, when issued, then results are searchable within 5 seconds of ingestion.
3. Given a log stream, when it contains structured fields, then fields are indexed for filtering.
4. Given the platform contract, when deployed, then the logs component binds `vmlog: true`.
5. Given a network request, when it targets VMLogs, then it is reachable via a stable Service endpoint.

## Implementation Plan

- Add VMLogs component under `gitops/victoria-metrics/base/`.
- Declare the vmlogs ConfigMap (search_within_seconds 5, indexed fields), Deployment, and Service.
- Install script with `--check` / `--dry-run` / `--apply`, step wrapper, and validation test.

## Files

- `gitops/victoria-metrics/base/vmlogs.yaml` (new)
- `scripts/install-vmlogs-dev.py` (new)
- `scripts/steps/36-install-vmlogs-dev.py` (new)
- `tests/test_install_vmlogs_dev.py` (new)
