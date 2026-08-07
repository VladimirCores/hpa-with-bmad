# Story 7-5: Expose Grafana and Hubble tool UIs via Envoy Gateway

Status: done

Baseline commit: 0a5ac61

## Story

As a Platform User,
I want Grafana and Hubble tool UIs exposed via the Envoy Gateway,
so that I can access grafana.hpdc.local and hubble.hpdc.local with native authentication.

## Acceptance Criteria

1. Given a request to `grafana.hpdc.local`, when routed through the Envoy Gateway, then it reaches the Grafana service with native authentication.
2. Given a request to `hubble.hpdc.local`, when routed through the Envoy Gateway, then it reaches the Hubble UI service with native authentication.
3. Given the platform contract, when deployed, then the routes bind `host: grafana.hpdc.local` and `host: hubble.hpdc.local`.
4. Given a route, when configured, then TLS termination is handled by the Envoy Gateway and `casdoor_casbin_ext_authz` is disabled.
5. Given a host route, when created, then it is host-based (not path-based) routing per the ToolUIRoute contract.

## Implementation Plan

- Add host-based HTTPRoute and `ToolUIRoute` contract binding under `gitops/observability/base/`.
- Install script with `--check` / `--dry-run` / `--apply`, step wrapper, and validation test.

## Files

- `gitops/observability/base/grafana-hubble-routes.yaml` (new)
- `scripts/install-grafana-hubble-routes-dev.py` (new)
- `scripts/steps/39-install-grafana-hubble-routes-dev.py` (new)
- `tests/test_install_grafana_hubble_routes_dev.py` (new)
