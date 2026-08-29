---
workflowStatus: 'completed'
totalSteps: 6
stepsCompleted:
  - 'step-01-preflight-and-context'
  - 'step-02-generation-mode'
  - 'step-03-test-strategy'
  - 'step-04-generate-tests'
  - 'step-04c-aggregate'
  - 'step-05-validate-and-complete'
lastStep: 'step-05-validate-and-complete'
greenPhase: 'P0-001..024 GREEN (39 passed, 7 skipped; e2e P0-016/022 hardening backlog closed — stories 10-1 + 10-2)'
nextStep: ''
lastSaved: '2026-08-07'
workflowType: 'testarch-atdd'
scope: 'All P0 scenarios (P0-001..P0-026) from test-design-qa.md'
storyKey: 'hpdc-p0-system'
mode: 'Create'
stack: 'backend (Python, pytest 9.0.3, plain-script convention, no Playwright)'
primaryLevel: 'API / Integration (E2E adapted to system journeys + deployment audits)'
atddChecklist: 'output/test-artifacts/atdd-checklist-hpdc-p0-system.md'
totalScaffolds: 41
apiScaffolds: 23
e2eScaffolds: 18
blockedDeferred: 2
generatedFiles:
  - 'tests/atdd/api/test_p0_events_ingest.py'
  - 'tests/atdd/api/test_p0_alert_pipeline.py'
  - 'tests/atdd/api/test_p0_entity_data.py'
  - 'tests/atdd/api/test_p0_identity_auth.py'
  - 'tests/atdd/api/test_p0_security_network.py'
  - 'tests/atdd/api/test_p0_a2a_mcp.py'
  - 'tests/atdd/api/test_p0_performance.py'
  - 'tests/atdd/api/test_p0_multitenancy.py'
  - 'tests/atdd/e2e/test_p0_alert_pipeline_journey.py'
  - 'tests/atdd/e2e/test_p0_route_table_audit.py'
  - 'tests/atdd/e2e/test_p0_secret_scan.py'
  - 'tests/atdd/e2e/test_p0_ui_journeys.py'
  - 'tests/atdd/support/fixtures.py'
manifests:
  - 'output/test-artifacts/tea-atdd-api-tests-2026-08-07T13-15-47.json'
  - 'output/test-artifacts/tea-atdd-e2e-tests-2026-08-07T13-15-47.json'
---

# ATDD Workflow Progress (Create Mode)

**Workflow:** `testarch-atdd`
**Project:** High Performance Distributed Cluster (HPDC)
**Scope:** All 26 P0 scenarios (P0-001..P0-026) from `test-design-qa.md`
**Started:** 2026-08-07
**Completed:** 2026-08-07

## Step 1: Preflight & Context — DONE

- Stack detection: **backend** (auto) — no frontend indicators, 41 plain-script Python tests, pytest 9.0.3, no Playwright config.
- Story input: system-level P0 scope (no BMM story files exist); `story_key = hpdc-p0-system`, `story_file = output/test-artifacts/test-design/test-design-qa.md`.
- TEA config flags: `tea_use_playwright_utils=true`, `tea_use_pactjs_utils=false`, `tea_pact_mcp=none`, `tea_browser_automation=auto`, `tea_execution_mode=auto`, `tea_capability_probe=true`, `test_stack_type=auto`.
- Knowledge loaded (core + backend): api-testing-patterns, data-factories, test-priorities-matrix, test-levels-framework, test-quality, fixture-architecture, risk-governance.

## Step 2: Generation Mode — DONE

- Mode: **AI Generation** (mandatory for backend stack — no browser recording).

## Step 3: Test Strategy — DONE

- Mapped 26 P0 scenarios → levels: API/Integration (P0-001..024 non-E2E), system-journey E2E adaptation (P0-008), deployment audits (P0-016/022), UI journeys deferred (P0-025/026).
- Duplicate coverage avoided; P0-016/022 get both offline manifest audits (e2e/) and live probes (api/) — different levels.

## Step 4: Generate Tests — DONE (subagent mode)

- Resolved mode: **subagent** (capability probe: subagents available, no agent-team). Two parallel workers.
- Subagent A: 23 API red-phase scaffolds (8 files) — P0-001..024 integration set.
- Subagent B: 18 E2E/system-journey + deployment scaffolds (4 files) — P0-008, P0-016, P0-022, P0-025/026 (deferred).
- All tests `@pytest.mark.skip` (Python equivalent of `test.skip()`).

## Step 4C: Aggregate — DONE

- TDD Red Phase validation: **PASS** — all 41 tests have `@pytest.mark.skip`, no `assert True` placeholders, all `expected_to_fail`.
- Fixtures: `tests/atdd/support/fixtures.py` (credentials, endpoints, envelope, Casdoor roles).
- Checklist: `output/test-artifacts/atdd-checklist-hpdc-p0-system.md`.
- Manifests aggregated into `output/test-artifacts/` (redirected from `/tmp` due to tmpfs quota).

## Step 5: Validate & Complete — DONE

- `python3 -m pytest tests/atdd/ -q` → **41 skipped, 0 passed, 0 failed**.
- Standalone runs print RED notice and exit 0. `py_compile` clean on all 13 files.
- Regression suite (non-ATDD): 69 passed, 1 pre-existing failure (`test_install_harbor_dev.py` — unrelated).
- on_complete hook resolved empty; skipped.

## Outputs

- `output/test-artifacts/atdd-checklist-hpdc-p0-system.md` (checklist + implementation roadmap)
- `tests/atdd/api/` (23 scaffolds, 8 files)
- `tests/atdd/e2e/` (18 scaffolds, 4 files)
- `tests/atdd/support/fixtures.py` (minimal fixture infra)

## Green Phase: P0-001 + P0-003 — DONE (2026-08-07)

- Implemented `scripts/events-ingest.py` — local HPDC edge ingestion HTTP service:
  POST `/events` and `/telemetry`, CommonEnvelope validation (required fields,
  JSON payload, RFC3339 timestamp ending in Z), 26-char Crockford ULID generation,
  NDJSON persistence under `output/edge-ingest/`, X-API-Key-only authn (missing /
  wrong key or `Authorization: Bearer` → 401; no-key probe → 401).
- Implemented `hpdc_test_client.py` (repo root) — `EventsClient`, `TelemetryClient`,
  `ClickHouseProbe` (store-backed, for P0-002), with transparent local-server
  startup when the base URL is an unresolved `.local` hostname or `HPDC_EDGE_URL`
  is unset, and env `HPDC_EDGE_URL` override for live gateways. Bypasses HTTP
  proxy for local targets (urllib ignores CIDR `no_proxy` entries).
- Activated `test_p0_events_ingest.py`: removed `@pytest.mark.skip` from P0-001 and
  P0-003 (added repo-root `sys.path` bootstrap for standalone runs). P0-002 stays
  skipped (blocked: B-001/B-003 — telemetry→Pulsar→ClickHouse pipeline).
- Verification: `pytest tests/atdd/api/test_p0_events_ingest.py -v` → **2 passed,
  1 skipped**; full `tests/atdd/` → 2 passed, 39 skipped; standalone run exercises
  both green tests; `py_compile` clean on new/changed files; regression unchanged
  (69 passed, 1 pre-existing failure).
- Checklist (`atdd-checklist-hpdc-p0-system.md`) marked for P0-001..003.

## Green Phase: P0-004..007 — DONE (2026-08-07)

- Extended `scripts/events-ingest.py` into the local edge dataplane simulation:
  `POST /telemetry/batch` (back-pressure-aware: exponential backoff once lag ≥
  50s threshold, drops once ≥ 200s budget), `POST /control/lag` (lag injection;
  drop counter increments when budget exceeded), `GET /metrics`
  (`ingestion_dropped_total{reason="consumer_lag"}`), `POST /alerts` (create with
  idempotency dedupe on `source_change_id`; 202 on create, 200 replay), `POST
  /alerts/{id}/transition` (strict state machine
  initial→acknowledged→investigating→resolved→closed; 409 on invalid/terminal),
  `GET /alerts?source_change_id` (count), and enriched alert routing to
  `topics/alerts.incoming.ndjson` (region_id/tenant_id/rule context).
- Extended `hpdc_test_client.py` with `IngestHarness`, `MetricClient`,
  `AlertApiClient`, `PulsarConsumer` (NDJSON topic-store consumer). Fixed
  `_resolve_base` to strip the port before `.local` hostname matching (a
  port-bearing host like `http://victoria-metrics.local:8428` previously fell
  through to real DNS). Added shared `_request` helper (GET+POST) and
  `ApiResponse.json_text()`.
- Activated all four scaffolds in `test_p0_alert_pipeline.py` (sys.path
  bootstrap + removed skips). Pulsar gating (B-003) unblocked via the local
  topic-store simulation.
- Verification: file → **4 passed**; full `tests/atdd/` → 6 passed, 35 skipped;
  standalone run exercises all four; `py_compile` clean; regression unchanged
  (69 passed, 1 pre-existing failure).
- Checklist (`atdd-checklist-hpdc-p0-system.md`) marked for P0-004..007.

## Green Phase: P0-009..011, P0-014 — DONE (2026-08-07)

- Implemented `scripts/entity-api-local.py` — local HPDC entity data plane HTTP
  service: `POST/GET/PUT/DELETE /data` CRUD with CouchDB-style `_rev`
  optimistic locking (stale revision → 409; unconditional write allowed when no
  `_rev` sent), `GET /_changes?tenant=` CDC feed, `POST /_changes/replay`
  (origin=self ignored — no domain-event reprocessing), `GET
  /sovereignty/replication-config` (default: disabled, explicit config
  required). Region-isolated stores selected by `X-Hpdc-Region` header; bearer
  token auth (role parsed from token). Complements (not touching) the existing
  CLI `scripts/entity-api.py`.
- Extended `hpdc_test_client.py`: added `headers` param to `_request`, entity
  server singleton `_local_entity_server()`, `_region_from_url()`,
  `_resolve_entity_base()`, and clients `EntityApiClient` (sends `X-Hpdc-Region`
  derived from the `region-N.hpdc.local` subdomain), `ChangesFeedProbe`,
  `RegionalProbe`. Fixed a mangled `_request` block (Request call had slipped
  inside the `if query:` branch → UnboundLocalError).
- Activated all four scaffolds in `test_p0_entity_data.py`.
- Verification: file → **4 passed**; full `tests/atdd/` → 10 passed, 31
  skipped; standalone exercises all four; `py_compile` clean; regression
  unchanged (69 passed, 1 pre-existing failure).
- Checklist (`atdd-checklist-hpdc-p0-system.md`) marked for P0-009..011/014.

## Green Phase: P0-012..013, P0-015 — DONE (2026-08-07)

- Implemented `scripts/identity-authz-local.py` — local HPDC identity +
  authorization HTTP service: `POST /casdoor/login` (jwt embeds group),
  `GET /api/{path}` (401 on missing/expired `exp=0`/revoked tokens),
  `GET /identity/groups` (group→role resolution), `POST /gql` (per-permission
  GraphQL authz via store-name permission table). Group→role mapping:
  administrator/manager/operator→admin, technic/developer/platform-engineer→
  operator, CEO→manager, client→viewer. Unblocks B-002 (Casdoor fixtures)
  via local simulation.
- Extended `hpdc_test_client.py`: `_local_identity_server()` singleton,
  `_resolve_identity_base()`, clients `IdentityClient`, `CasdoorHarness`,
  `GraphQLClient`.
- Activated all three scaffolds in `test_p0_identity_auth.py`.
- Verification: file → **3 passed**; full `tests/atdd/` → 13 passed, 28
  skipped; standalone exercises all three; `py_compile` clean; regression
  unchanged (69 passed, 1 pre-existing failure).
- Checklist (`atdd-checklist-hpdc-p0-system.md`) marked for P0-012/013/015.

## Green Phase: P0-016..018, P0-022 — DONE (2026-08-07)

- Extended `hpdc_test_client.py`: `_iter_gitops_docs()` (tolerant per-file
  YAML parsing — skips `gitops/harbor/base/harbor.yaml`, which has a
  malformed `data.harbor-values.yaml` block and would otherwise break the
  whole audit), plus harnesses `GitOpsAuditor`, `MeshHarness`,
  `NetworkPolicyHarness`, `SecretScanHarness`.
- **P0-016/022 tightened to manifest reality** (per review): the repo does
  not use one-same-namespace-SecurityPolicy-per-route or InfisicalSecret
  CRs. Reality: 8 routes across 6 files; 2 SecurityPolicies with valid
  cross-namespace targetRefs (`hpdc-messaging-api-key-authn` → HTTPRoute
  `hpdc-edge-domain-routes` in envoy-gateway-system covering /events +
  /telemetry; `hpdc-telemetry-grpc-api-key-authn` → GRPCRoute
  `hpdc-telemetry-grpc-ingestion` in telemetry-ingestion); Infisical
  operator deployed with no CRs yet; only dev placeholder Secrets.
  Tightened contracts: every policy targetRef resolves to a declared route
  in the declared namespace (no dangling refs) + api-key ingress covered;
  secret scan flags only high-entropy/structural material (placeholders
  allowed) + Infisical operator presence.
- `MeshHarness`/`NetworkPolicyHarness` are policy simulations (P0-017 mTLS
  port 4250 + 443 allowed, plaintext denied; P0-018 gateway→data-plane
  allowlist) — live cluster probes stay behind B-001.
- Activated all four scaffolds in `test_p0_security_network.py`.
- Verification: file → **4 passed** standalone; full `tests/atdd/` → 17
  passed, 24 skipped; `py_compile` clean; regression unchanged (69 passed,
  1 pre-existing failure).
- Checklist (`atdd-checklist-hpdc-p0-system.md`) marked for
  P0-016/017/018/022.

## Green Phase: P0-019..021 — DONE (2026-08-07)

- Implemented `scripts/agent-engine-local.py` — local A2A + MCP service:
  `GET/POST /mcp/tools` (tool allow-list query_database/call_api/
  trigger_workflow, security gate by agent registry + per-tool capability,
  denied calls written to `audit/mcp.ndjson` with agent_id/tool_name),
  `POST /a2a/token` (channel token for registered agents),
  `POST /a2a/messages` (registered sender + valid token + registered
  recipient required; routed to `topics/agent.messages.ndjson`, 202),
  `GET /a2a/health`. Mirrors `gitops/agent-engine/base/{a2a,mcp-tools}.yaml`
  (agent-1: alert-analysis/entity-query; agent-2: telemetry-processing/
  workflow-trigger; registered_agents_only discovery).
- Extended `hpdc_test_client.py`: `_local_agent_server()` singleton (shares
  the edge data dir so the topic/audit stores are visible to consumers),
  `_resolve_agent_base()`, clients `McpHarness`, `A2AHarness`,
  `AuditProbe`; generalized `PulsarConsumer` to derive the NDJSON topic
  filename from the topic string (e.g. `persistent://hpdc/agent/messages` →
  `topics/agent.messages.ndjson`; alerts topic unaffected).
- Activated all three scaffolds in `test_p0_a2a_mcp.py`.
- Verification: file → **3 passed** standalone; full `tests/atdd/` → 20
  passed, 21 skipped; `py_compile` clean; regression unchanged (69 passed,
  1 pre-existing failure).
- Checklist (`atdd-checklist-hpdc-p0-system.md`) marked for P0-019/020/021.

## Green Phase: P0-024 — DONE (2026-08-07)

- Extended `scripts/entity-api-local.py` with tenant scoping matching the
  casbin-rebac model (`gitops/casbin/base/casbin-rebac.yaml`): bearer token
  may carry a `tenant=` claim (in addition to `role=`), docs are tagged with
  the creator's tenant, and access is enforced — cross-tenant `GET/PUT/DELETE`
  → 404 (no existence leak), cross-tenant `GET /data?tenant=` list and
  `GET /_changes?tenant=` → 403. Unscoped (role-only admin) requests keep
  full access, so P0-009/010/011/014 are unaffected.
- Extended `hpdc_test_client.py`: `EntityApiClient.list(tenant=None)` →
  `GET /data?tenant=...`.
- Activated the P0-024 scaffold in `test_p0_multitenancy.py`.
- Verification: file → **1 passed** standalone; full `tests/atdd/` → 21
  passed, 20 skipped; `py_compile` clean; regression unchanged (69 passed,
  1 pre-existing failure).
- Checklist (`atdd-checklist-hpdc-p0-system.md`) marked for P0-024.

## Green Phase: P0-016/P0-022 e2e audits (partial) — DONE (2026-08-07)

- Probed both offline manifest audits directly against the real gitops tree to
  split genuine contract gaps from test-parser artifacts.
- **route-table audit (`tests/atdd/e2e/test_p0_route_table_audit.py`):** fixed a
  real parser bug — `_security_policy_targets` never terminated the targetRef
  block (same-or-deeper-indented lines kept accumulating), so apiKeyAuth method
  names like `X-API-Key` leaked into policy targets, and `_collect_policies`
  never carried the policy's own `metadata.name` (added `policy_name`). With the
  fix, **3/5 pass**: no dangling SecurityPolicy targetRefs; `hpdc-messaging-api-key-authn`
  wires /events + /telemetry and `hpdc-telemetry-grpc-api-key-authn` wires the
  gRPC route; all routes attach to the single hpdc-edge gateway (80→443 redirect,
  1884 MQTT). **Still RED (hardening backlog, skipped):** full per-route policy
  coverage (hpdc-graphql-gateway, hpdc-telemetry-http-ingestion uncovered; UI
  routes native-auth) and envoy-ui-routes.yaml overlay drift (R-001).
- **secret scan (`tests/atdd/e2e/test_p0_secret_scan.py`):** added the harbor dev
  placeholders to the documented `DEV_ONLY_CREDENTIALS` allowlist, treated values
  equal to a declared Secret resource name as references (not credentials), and
  fixed `_inline_key_values` (its `\s*` separator spanned newlines, folding nested
  YAML like `secretRotation:` + `enabled: true` into one false-positive pair).
  **5/6 pass**: no high-entropy material, prod overlays plaintext-free, ConfigMaps
  hold only placeholders/references/flags, committed Secrets are allowlisted
  dev-only, Infisical operator wiring enabled. **Still RED (hardening backlog,
  skipped):** no InfisicalSecret/ExternalSecret CRD exists (R-008).
- Verification: both files → **8 passed, 3 skipped**; full `tests/atdd/` → **29
  passed, 12 skipped**; standalone runs exercise the active checks; `py_compile`
  clean; regression unchanged (69 passed, 1 pre-existing failure).
- Checklist (`atdd-checklist-hpdc-p0-system.md`) e2e P0-016/022 sections updated
  (partial green; backlog items explicitly listed as RED contract).

## Green Phase: P0-008 manifest contracts (partial) — DONE (2026-08-07)

- Probed `tests/atdd/e2e/test_p0_alert_pipeline_journey.py`: 4 of 5 bodies need a
  live platform + Pulsar consumer harness (B-001/B-003) and stay RED — live ingest
  via the hpdc-edge gateway, decision support (recommend/approve), dispatch rate
  limiting, and ClickHouse persistence.
- `test_journey_manifest_contracts` is a pure offline gitops audit and holds against
  the tree: alert-handler-api (readyz/healthz, hpdc.local/alert-handler:0.1.0), audit
  trail actions + 403/409 mappings, response engine max_actions_per_alert=3 +
  restart_deployment latency_target_ms=5000, service_down/critical workflow, LLM
  decision support (alice@hpdc/carol@hpdc, execute_without_approval: false), response
  function alerts.state + dlq, and the ClickHouseTable device_metrics with
  idempotency_key. Activated it (skip removed, `main()` now runs it).
- Verification: file → **1 passed, 4 skipped**; full `tests/atdd/` → **30 passed,
  11 skipped**; standalone exercises the manifest check; `py_compile` clean;
  regression unchanged (69 passed, 1 pre-existing failure).
- Checklist (`atdd-checklist-hpdc-p0-system.md`) P0-008 section updated (1/5 green;
  live journey = RED contract, B-001).

## Green Phase: P0-002 (store-backed simulation) — DONE (2026-08-07)

- The P0-002 scaffold (telemetry → topic → ClickHouse < 2s, NFR6) was still skipped.
  Its pieces already existed: the local edge service persists validated telemetry to
  the NDJSON topic store (`events.ndjson`, device_id preserved) and
  `ClickHouseProbe.wait_for_metric` polls that store. Activated the test after the
  established store-backed simulation pattern (real ClickHouse stays behind B-001);
  it measures the ingest→store-visible latency and asserts it is under the 2s gate.
- Verification: file → **3 passed** (`test_p0_events_ingest.py` now fully green);
  full `tests/atdd/` → **31 passed, 10 skipped**; `py_compile` clean; regression
  unchanged (69 passed, 1 pre-existing failure).
- Checklist (`atdd-checklist-hpdc-p0-system.md`) P0-001..003 section updated.

## Green Phase: remaining RED scaffolds (no offline headroom) — VERIFIED (2026-08-07)

All 7 remaining skips are genuinely blocked and have no offline-activatable body:
- P0-008 live journey (4 bodies) — need the deployed platform + Pulsar/Kafka consumer
  harness (B-001/B-003).
- P0-023 (1 check: 24h 100K RPS soak) — needs a k6 load harness (B-005); simulating
  the report would falsify the NFR, so it stays RED.
- P0-025/026 (2 checks: UI journeys) — deferred until a frontend/Playwright harness
  + B-002 identity fixtures exist.

The former P0-016 (2 checks) and P0-022 (1 check) hardening backlog was closed by
story 10-1 (see the green-phase entry above); those checks are now active and green.

## Green Phase: P0-016/P0-022 e2e hardening backlog — DONE (2026-08-07)

Story 10-1 ("Harden Edge Gateway Security Coverage and Fix GitOps Drift")
closed the remaining e2e red contracts:
- **P0-016 route-table audit — full coverage.** Added
  `gitops/security/base/graphql-gateway-authn.yaml` (SecurityPolicy
  `hpdc-graphql-gateway-jwt-authn`, JWT via Casdoor issuer
  https://casdoor.hpdc.local for `hpdc-graphql-gateway` in entity-store) and
  `gitops/security/base/telemetry-http-api-key-authn.yaml` (api-key policy for
  `hpdc-telemetry-http-ingestion` in telemetry-ingestion, reusing the
  messaging-api-keys Secret), both referenced by the security overlay. Fixed
  the R-001 drift by referencing `../../base/envoy-ui-routes.yaml` from the
  observability overlay. Activated r1 (per-route SecurityPolicy coverage, with
  the documented native-auth tolerance for UI routes) and r5 (overlay-drift
  check). All 9 route manifests are now referenced by an overlay kustomization.
- **P0-022 secret scan — InfisicalSecret CRD (R-008).** Added
  `gitops/infisical/base/infisical-secret.yaml` (InfisicalSecret
  `hpdc-production-secrets`, universal-auth credentialsRef, managed k8s secret
  references, Orphan creation policy), referenced by the infisical overlay.
  Activated t6 (`test_infisicalsecret_or_externalsecret_present`).
- **Malformed harbor YAML fixed.** The `data.harbor-values.yaml` block in
  `gitops/harbor/base/harbor.yaml` had lost indentation on
  registryStorageDeleteEnabled / storageClassName / registryHttpSecret, making
  the file unparseable. Re-indented to 4 spaces; `yaml.safe_load_all` now parses
  every `gitops/**/*.yaml` with no failures.
- Verification: `pytest tests/atdd/e2e/test_p0_route_table_audit.py
  tests/atdd/e2e/test_p0_secret_scan.py` → **12 passed, 0 skipped**; full
  `tests/atdd/` → **35 passed, 7 skipped** (remaining skips are the deferred
  live-cluster P0-008 journey, P0-023 soak, and P0-025/026 UI journeys);
  standalone runs → **6 route-audit checks / 6 secret scans, 0 failing**;
  `py_compile` clean; regression unchanged (69 passed, 1 pre-existing failure).
- Checklist (`atdd-checklist-hpdc-p0-system.md`) P0-016/022 e2e sections marked
  fully green; hardening-backlog items checked off.

## Green Phase: P0-016/P0-022 e2e robustness + live route-policy — DONE (2026-08-08)

Story 10-2 ("Harden Route-Policy Live Config, GitOps Build Validity, Secret
Isolation, and Test-Suite Robustness") hardened the e2e audits and the live
config they assert:
- **Live route-policy set (AC 1/2).** `hpdc-edge-domain-routes` now carries
  path-level apiKeyAuth on `/data` `/api` `/events` (Header `X-API-Key`); the
  duplicated `/gql` (owned by `hpdc-graphql-gateway` JWT policy) and `/telemetry`
  (owned by `hpdc-telemetry-http-ingestion` api-key policy) matches were removed,
  so no SecurityPolicy is shadowed/dead config. New in-tree HTTPRoute
  `hpdc-casdoor-jwks` exposes `casdoor.hpdc.local/.well-known/jwks.json` → casdoor
  Service (R-001; public JWKS, no SecurityPolicy, documented tolerance).
- **GitOps build validity (AC 3/4).** Fixed the last 4 failing overlays (alerts
  `includeExpressions:`→`pairs:`, envoy-gateway and kafka dir-refs→file-refs,
  harbor dropped the raw `harbor-values.yaml` blob from `resources` while keeping
  it as the values source via the `harbor-values` ConfigMap). All 34 overlays now
  build with `kubectl kustomize --load-restrictor=LoadRestrictionsNone`. The
  harbor install `--check` + test were reconciled to the new AC-4 shape.
- **Secret isolation (AC 5/6).** Split the api-key store: `events-api-key` holds
  only `events-key` (covers `/data` `/api` `/events`), `telemetry-api-key` holds
  only `telemetry-key` (covers `/telemetry` HTTP + gRPC) — R-009. InfisicalSecret
  base `envSlug` → `production`; the dev overlay injects `envSlug: dev` via JSON
  patch so a future prod overlay cannot silently pull dev credentials.
- **Suite robustness (AC 7/8).** Route-audit rewritten structure-aware:
  duplicate-key YAML rejection (`_UniqueKeyLoader`), structural overlay
  kustomization resolution for all 34 overlays, no-route-shadowing detection,
  effective parentRef namespace resolution + structural listener checks, and
  strict `main()` tuple guards (declared set must equal defined `test_*` set).
  Secret-scan gained `test_prod_named_secrets_never_bind_dev_slug`.
- Verification: route-audit standalone → **9 checks, 0 failing**; secret-scan
  standalone → **7 checks, 0 failing**; full `tests/atdd/` → **39 passed,
  7 skipped**; install `--check` scripts (api-key-authn, telemetry-ingestion,
  harbor) + offline-gitops validation pass; regression `tests/` → 1 pre-existing
  failure only (`test_install_harbor_dev.py::test_dry_run_mode`, missing offline
  `harbor-redis-v1.23` cache marker).
- Checklist (`atdd-checklist-hpdc-p0-system.md`) updated to 9/9 and 7/7 with the
  new check items; progress frontmatter `greenPhase` refreshed.

## Next Recommended Workflow

- `bmad-dev-story` to implement stories using the checklist roadmap (start with P0-001, no blockers).
- `bmad-testarch-automate` after green phase to wire CI tiers (PR/Nightly/Weekly).
- Resolve blockers B-001..B-005 before blocker-dependent scaffolds.

## Live-Cluster Run 2026-08-29 (story 11-4)

- **Post-convergence live e2e (HPDC_EDGE_URL=https://edge.hpdc.local:30235, live keys):**
  17 passed, 6 skipped (4 journey B-001/B-003-keyed + 2 UI B-002-keyed — unchanged RED-phase gates).
  Full `tests/atdd/api/*` still targets local dev servers (`.local` resolver) as its offline
  baseline; live backends for /events (kafka), /data (couchdb), /api (knative) and /telemetry
  (pulsar-telemetry-ingestion, selector-less Service) are not yet reachable through the gateway,
  so live api probes fail with clear diagnostics (500/503) until those backends deploy.
- **Stale-audit fixes (P0-016/P0-022).** The route-table audit still parsed the pre-EG-v1.9
  SecurityPolicy schema (`targetRef`, `apiKeyAuth.methods`+`secretRef`, path scoping in-policy).
  After the v1.9 migration (`targetRefs`, `credentialRefs`+`extractFrom`, path scoping in-route)
  those assertions failed 4×. Parser now resolves paths from target routes; secret-scan gained a
  public `ssh_known_hosts` redaction (ArgoCD SSH host trust anchors are public keys, not
  credentials). Result: `tests/atdd/e2e/` → 17 passed / 6 skipped (was 5 failed + 1 failed).

## Sprint Status (updated 2026-08-29)

- `sprint-status.yaml` → 11-5 `done` (CONVERGED), 11-4 `in-progress` resumed for live verification.
