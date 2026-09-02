---
title: "Story 15-6: Post-Install E2E Accessibility Testing for All Components"
type: feature
created: '2026-09-02'
status: backlog
context: []
warnings: []
---

# Story 15-6: Post-Install E2E Accessibility Testing for All Components

## Intent

**Problem:** The Hubble UI E2E test pattern (Playwright headless Chromium testing connectivity, UI elements, backend resources, and API flows) was implemented as a standalone step 40, disconnected from the component it tests. This pattern should be the standard for every installable component — E2E accessibility tests run immediately after installation, as part of the component's install step, not as a separate post-hoc step.

**Approach:** Generalize the Hubble UI E2E test pattern into a reusable testing strategy. Each component's install step gets an embedded E2E test sub-step that validates the component is accessible and functional immediately after installation. This provides instant feedback during boot and prevents broken components from silently blocking later steps.

## Boundaries & Constraints

**Always:** E2E tests must be non-destructive (read-only), idempotent, and safe to re-run. Tests must not modify cluster state. Each component's E2E tests must be self-contained and not depend on other components' test state.

**Block If:** The component is disabled via toggle (e.g., `HPDC_GRAFANA_ENABLED=false`). E2E tests should be skipped when the component is not installed.

**Never:** E2E tests should not deploy components, configure DNS, modify cluster resources, or accept self-signed certs as trusted.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path — all tests pass | Component installed, healthy, reachable | All E2E tests pass, step exits 0 | N/A |
| Component not healthy | Pods not Running, service not ready | E2E tests skip gracefully with clear message | Skip (not fail) — component may still be starting |
| Gateway unreachable | Network issue, DNS not configured | Browser tests skip, kubectl tests still run | Partial pass — backend resource checks still validate |
| Component disabled via toggle | Toggle var is false | Step skipped entirely (existing behavior) | No tests run |
| Playwright not installed | `bunx playwright` fails | Clear error message about missing dependency | Exit 1 with install instructions |

## Testing Strategy Per Component

### Tier 1: Gateway-Exposed Components (browser + kubectl + API)

These components have HTTP routes via Envoy Gateway and should have full browser E2E tests.

| Component | Route | Test Focus |
|-----------|-------|------------|
| Hubble UI | `hubble.hpdc.local` | Page load, UI elements, namespace selector, flows tab, backend pods, Hubble API via port-forward |
| Grafana | `grafana.hpdc.local` | Login page, dashboard list, datasource health, alert rules |
| Argo CD | `argocd.hpdc.local` | Login page, application list, sync status, health |
| Backstage | `backstage.hpdc.local` | Catalog page, plugin list, techdocs |
| Swagger UI | `swagger.hpdc.local` | API list, try-it-out functionality |
| Kargo | `kargo.hpdc.local` | Pipeline list, stage status |

### Tier 2: Cluster-Internal Components (kubectl + API only)

These components are ClusterIP services and can only be tested via kubectl and port-forward.

| Component | Test Focus |
|-----------|------------|
| Harbor | Pod health, service endpoints, registry API via port-forward |
| Cilium | DaemonSet rollout, Hubble relay health, CNI pods Running |
| Casdoor | Pod health, service endpoints, OIDC discovery via port-forward |
| Casbin | Pod health, policy enforcement via port-forward |
| Infisical | Pod health, service endpoints, secrets API via port-forward |
| Entity Store | Pod health, CouchDB/ArcadeDB/YugabyteDB endpoints via port-forward |
| Telemetry Ingestion | Pod health, route configuration |
| Victoria Metrics | Pod health, service endpoints, PromQL query via port-forward |
| OTEL Collector | Pod health, service endpoints |

### Tier 3: Validation-Only Components (no E2E needed)

These components are validated by existing scripts and don't need additional E2E tests.

| Component | Validation Method |
|-----------|------------------|
| Cilium mTLS | Existing validation scripts |
| Cert generation | Existing validation (gen-edge-cert.py) |
| Storage (local-path) | Existing validation |
| Git mirror | Existing validation |

## Implementation Pattern

Each component's E2E tests follow the Hubble UI pattern:

1. **Connectivity tests** (browser): Page loads without error, title correct, no error overlay
2. **UI element tests** (browser): Navigation present, key elements accessible
3. **Backend resource tests** (kubectl): Pods Running, services exist, endpoints ready, no restart storms
4. **API flow tests** (port-forward or direct): Health endpoint responds, key APIs return valid data

### File Structure

```
tests/e2e/{component}.spec.ts    # Playwright test file
scripts/gitops/validate-{component}.py  # Python validation script (optional)
```

### Integration into Install Steps

Each install step's `--apply` mode runs E2E tests as the final sub-step:

```python
# In install-{component}-dev.py
print("\nStep N/N: Running {component} E2E accessibility tests...")
rc = _run_e2e_tests()
if rc != 0:
    print("{component} E2E tests failed.", file=sys.stderr)
    return rc
```

## Tasks & Acceptance

**Execution:**
- [ ] Document the E2E testing strategy (this spec)
- [ ] Refactor Hubble UI E2E tests into the standard pattern (already done in step 04)
- [ ] Create E2E test file for Argo CD (`tests/e2e/argocd.spec.ts`)
- [ ] Create E2E test file for Grafana (`tests/e2e/grafana.spec.ts`)
- [ ] Create E2E test file for Harbor (`tests/e2e/harbor.spec.ts`)
- [ ] Create E2E test file for Casdoor (`tests/e2e/casdoor.spec.ts`)
- [ ] Embed E2E tests into each component's install step
- [ ] Update playwright.config.ts if needed for component-specific configs
- [ ] Update docs with E2E testing strategy

**Acceptance Criteria:**
- Given a component is installed via its install step, when the step completes, then E2E accessibility tests run automatically
- Given E2E tests pass, when the step completes, then the component is confirmed accessible
- Given E2E tests fail, when the step completes, then the step fails with clear diagnostic messages
- Given a component is disabled via toggle, when the install step runs, then E2E tests are skipped
- Given Playwright is not installed, when E2E tests attempt to run, then a clear error message is shown
- Given the Hubble UI E2E pattern exists, when a new component needs E2E tests, then the pattern can be replicated in <30 minutes

## Spec Change Log

## Review Triage Log

## Design Notes

- The Hubble UI E2E test (step 04) serves as the reference implementation
- Browser tests use Playwright with headless Chromium, `ignoreHTTPSErrors: true` for self-signed certs
- kubectl tests use `execSync` with the project's kubeconfig path
- Port-forward tests spawn a background kubectl process and clean up in `afterAll`
- Tests that can't reach the gateway skip gracefully rather than fail (graceful degradation)
- Each component's test file is self-contained — no shared fixtures across components

## Verification

**Commands:**
- `python3 scripts/steps/04-install-envoy-gateway-dev.py --dry-run` — should show E2E test as step 4/4
- `bunx playwright test --config playwright.config.ts --list` — should list all E2E test files
- `python3 -m py_compile scripts/steps/04-install-envoy-gateway-dev.py` — should compile

**Manual checks:**
- Verify Hubble UI E2E tests run as part of step 04 --apply
- Verify step 40 is no longer in STEP_TOGGLE_MAP
- Verify each new E2E test file follows the Hubble UI pattern
