---
title: Validate Core Gateway — Hubble UI and Downstream Route Readiness
type: feature
created: '2026-09-02'
status: awaiting-operator
baseline_revision: c4dd5ef528b1bae18dcf8c49e6cd4970b5dbab8d
final_revision: 5e60a73a817dcf36858e532d2b36c8b85ff2ff25
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
operator_actions:
  - "Add hubble.hpdc.local DNS entry: append '${HPDC_GATEWAY_IP} hubble.hpdc.local' to /etc/hosts on the host machine (or configure DNS) so that hubble.hpdc.local resolves to the Envoy Gateway address"
  - "Verify Hubble UI is deployed in the observability namespace: ensure 'kubectl get deploy hubble-ui -n observability' shows a Running deployment before running the validation script"
---

<intent-contract>

## Intent

**Problem:** Epic 15 installs Envoy Gateway and a static self-signed wildcard cert in the core layer, but there is no automated validation that the gateway is actually functional, that the Hubble UI route resolves and responds, or that downstream routes are attachable. Without this validation, a broken gateway could silently block Epic 3 (domain routes) and Epic 7 (Grafana/Hubble UI routes).

**Approach:** Create a standalone Python validation script that programmatically verifies: GatewayClass/hpdc-envoy-gateway exists and is Accepted, Gateway/hpdc-edge exists and has Programmed=True, HTTPS listener on port 443 accepts connections at the gateway IP, hubble.hpdc.local resolves and returns HTTP 200/302 through the gateway, and Hubble UI pods are reachable without port-forward. The script exits non-zero on any failure. An operator must configure DNS (`/etc/hosts`) before the DNS-dependent checks can pass.

## Boundaries & Constraints

**Always:** Validation script must be Python 3, exit non-zero on any failure, and use the standard `_provisioned`/`component_versions` pattern for environment variables. All checks must be idempotent and safe to re-run. The script must not modify cluster state — read-only validation only.

**Block If:** The Gateway API CRDs are not applied, or Envoy Gateway is not installed (no `GatewayClass/hpdc-envoy-gateway` in cluster). These indicate a prerequisite story is incomplete.

**Never:** Modify cluster resources, create routes, deploy Hubble UI, configure DNS, or accept self-signed certs as trusted. DNS configuration is an operator responsibility outside the repo.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path — all checks pass | EG installed, TLS secret exists, Hubble UI deployed, DNS configured | All checks pass, script exits 0 | N/A |
| GatewayClass missing | EG not installed | Script fails with clear error: GatewayClass not found | Exit 1 with diagnostic |
| Gateway not Programmed | TLS secret missing or EG misconfigured | Script fails with clear error: Gateway not Programmed | Exit 1 with diagnostic |
| DNS not configured | hubble.hpdc.local not in /etc/hosts | Script fails with clear error: DNS resolution failed | Exit 1 with guidance |
| Hubble UI not deployed | No hubble-ui pods in observability namespace | Script fails: Hubble UI pods not found | Exit 1 with diagnostic |
| HTTPS port not accepting | Gateway not reachable at :443 | Script fails: HTTPS listener not accepting connections | Exit 1 with diagnostic |

</intent-contract>

## Code Map

- `scripts/gitops/validate-core-gateway.py` -- NEW: standalone core gateway validation script
- `scripts/steps/04.7-validate-core-gateway.py` -- NEW: step wrapper following subprocess dispatch pattern
- `scripts/gitops/install-envoy-gateway-dev.py` -- existing EG installer; reference for `_gateway_programmed()` pattern and `_run()` helper
- `scripts/gitops/gen-edge-cert.py` -- existing cert generator; reference for TLS secret validation pattern
- `gitops/envoy-gateway/base/envoy-gateway.yaml` -- EG manifest defining GatewayClass and Gateway resources
- `gitops/observability/base/grafana-hubble-routes.yaml` -- HTTPRoute for hubble.hpdc.local -> hubble-ui service
- `gitops/observability/base/observability-ui-routes.yaml` -- Hubble UI Deployment and Service definitions
- `_bmad/bmm/config.yaml` -- project config (HPDC_GATEWAY_IP, etc.)
- `.env` -- runtime env vars including HPDC_GATEWAY_IP

## Tasks & Acceptance

**Execution:**
- [x] `scripts/gitops/validate-core-gateway.py` -- Create standalone validation script with: `_run()` helper (reuse pattern from install-envoy-gateway-dev.py), `check_gateway_class()` (kubectl get GatewayClass hpdc-envoy-gateway, assert Accepted condition), `check_gateway_programmed()` (kubectl get Gateway hpdc-edge -o jsonpath Programmed=True), `check_https_listener()` (nc or kubectl to verify port 443 accepting), `check_dns_resolution()` (resolve hubble.hpdc.local, fail if not configured), `check_hubble_route()` (curl -k -I https://hubble.hpdc.local, expect 200 or 302), `check_hubble_ui_pods()` (kubectl get pods in observability namespace with app=hubble-ui label, assert Running), `main()` with argparse (--check flag, default mode runs all checks). Exit non-zero on any failure.
- [x] `scripts/steps/04.7-validate-core-gateway.py` -- Create step wrapper following subprocess dispatch pattern (Pattern B), calling validate-core-gateway.py with --check mode. Define STEP_NAME and STEP_DESCRIPTION constants.
- [x] `output/implementation-artifacts/spec-15-4-validate-core-gateway-hubble-ui-and-downstream-route-readiness.md` -- Create spec with intent-contract, code map, tasks, and operator_actions for DNS configuration

**Acceptance Criteria:**
- Given the validation script exists, when `python3 scripts/gitops/validate-core-gateway.py --check` is run, then it checks all 6 acceptance criteria from the story (GatewayClass Accepted, Gateway Programmed, HTTPS accepting, DNS resolving, HTTP 200/302, Hubble UI pods reachable)
- Given the validation script runs without --check flag, when any check fails, then the script exits with non-zero status and prints a clear diagnostic message
- Given DNS is not configured, when the DNS check runs, then it fails with a clear message indicating hubble.hpdc.local does not resolve
- Given Hubble UI is not deployed, when the pod check runs, then it fails with a clear message indicating no Running hubble-ui pods found
- Given all checks pass, when the script runs, then it prints success for each check and exits 0
- Given the step wrapper exists, when `python3 scripts/steps/04.7-validate-core-gateway.py --check` is run, then it invokes the validation script and passes through the exit code

## Spec Change Log

## Review Triage Log

## Design Notes

- The validation script reuses the `_run()` helper pattern from `install-envoy-gateway-dev.py` for subprocess execution with timeout and encoding error handling
- DNS check uses `socket.getaddrinfo()` which respects /etc/hosts — if hubble.hpdc.local is not configured, it raises `socket.gaierror` and the script reports a clear operator action needed
- HTTPS connectivity check uses `urllib.request.urlopen()` with `ssl_context` set to accept self-signed certs (matching the `curl -k` behavior in the AC)
- Hubble UI pod check uses `kubectl get pods` with label selector `app.kubernetes.io/name=hubble-ui` in the `observability` namespace (the actual deployment location per `observability-ui-routes.yaml`)
- The step wrapper follows Pattern B (subprocess dispatch) matching the pattern of `04.5-gen-edge-cert.py` and `04.6-install-envoy-gateway-dev.py`

## Verification

**Commands:**
- `python3 scripts/gitops/validate-core-gateway.py --check` -- expected: exits 0 if all checks pass, exits 1 with diagnostics if any fail
- `python3 scripts/steps/04.7-validate-core-gateway.py --check` -- expected: exits 0 or 1 matching the validation script
- `python3 -m py_compile scripts/gitops/validate-core-gateway.py` -- expected: compiles without errors
- `python3 -m py_compile scripts/steps/04.7-validate-core-gateway.py` -- expected: compiles without errors

**Manual checks (if no CLI):**
- Verify the validation script checks all 6 acceptance criteria from the story
- Verify DNS failure produces a clear operator action message
- Verify Hubble UI pod check uses the correct namespace (observability, not kube-system)

## Auto Run Result

Status: awaiting-operator

Implemented standalone core gateway validation script (`scripts/gitops/validate-core-gateway.py`) with 6 programmatic checks: GatewayClass Accepted, Gateway Programmed, HTTPS listener accepting, DNS resolution, Hubble UI route HTTP response, and Hubble UI pod status. Created step wrapper (`scripts/steps/04.7-validate-core-gateway.py`) following subprocess dispatch pattern. Both scripts compile successfully.

**Files created:**
- `scripts/gitops/validate-core-gateway.py` -- Core gateway validation script (6 checks, exit non-zero on failure)
- `scripts/steps/04.7-validate-core-gateway.py` -- Step wrapper for integration with boot sequence

**Operator actions required:**
1. Add DNS entry: append `${HPDC_GATEWAY_IP} hubble.hpdc.local` to `/etc/hosts` on the host machine
2. Verify Hubble UI deployment: ensure `kubectl get deploy hubble-ui -n observability` shows a Running deployment

After completing both operator actions, run: `python3 scripts/gitops/validate-core-gateway.py --check`
