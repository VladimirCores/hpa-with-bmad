## Deferred from: code review of 4-1-build-iot-device-simulator-and-telemetry-acceptance-harness (2026-08-05)

- Resolved: committed local API key placeholder — `output/telemetry-simulator/config.yaml` no longer commits a secret-like value; live HTTP telemetry resolves `api_key` from `${HPDC_TELEMETRY_API_KEY}` with `api_key_env: HPDC_TELEMETRY_API_KEY`.

## Deferred from: code review of story-10.1 (2026-08-07)

- `native-auth` annotation on UI routes is unvalidated by r1 (`gitops/observability/base/envoy-ui-routes.yaml`) — deferred, pre-existing: story Dev Notes explicitly scope this out.
- Path-level auth gaps on `hpdc-edge-domain-routes` (`/data`, `/api`, `/gql`) and `/gql` precedence overlap with `hpdc-graphql-gateway` — deferred, pre-existing: route topology must not be altered; AC 1 is route-level only.
- InfisicalSecret CRD will not reconcile (no operator/CRD definition/`credentialsRef` secret in tree) — deferred, pre-existing infra; AC 5 literally satisfied.
- JWT policy lacks `audiences`/`forwardJWT`; runtime JWKS fetch unverifiable offline — deferred, pre-existing: authz beyond this story's authn AC, needs live cluster (P0-008).
- Secret scan `_base_yamls()` only scans base manifests, not overlays — deferred, pre-existing test-design limitation.

## Deferred from: code review re-run of story-10.1 (2026-08-07)

> Ledger reconciled 2026-08-08 — story 10-2 closed these items. Remaining entries below are still open.

## Resolved by story 10.2 (2026-08-08)

- `/gql` and `/telemetry` shadowing by `hpdc-edge-domain-routes` — **resolved**: 10.2 Task 1.2 removed the duplicated matches (paths owned by `hpdc-graphql-gateway` JWT + `hpdc-telemetry-http-ingestion` api-key policies); route-audit `test_no_route_shadowing` now guards this class.
- JWKS host `https://casdoor.hpdc.local/.well-known/jwks.json` has no in-tree HTTPRoute — **resolved**: 10.2 Task 1.3 added `hpdc-casdoor-jwks` HTTPRoute (public JWKS, documented tolerance); live JWKS fetch still deferred to P0-008.
- Telemetry policy reuses `messaging-api-keys` with no key selection (`events-key`/`telemetry-key` both accepted) — **resolved**: 10.2 Task 3.1/3.2 split into `events-api-key` (only `events-key`, `/data` `/api` `/events`) and `telemetry-api-key` (only `telemetry-key`, `/telemetry` HTTP + gRPC); `test_api_key_stores_are_key_isolated` asserts R-009.
- Harbor overlay lists `../../base/harbor-values.yaml` as a kustomize resource (kustomize build fails) — **resolved**: 10.2 Task 2.4 dropped it from `resources`; kept as the values source via the `harbor-values` ConfigMap; all 34 overlays build.
- InfisicalSecret prod-named with `envSlug: dev` hardcoded in base — **resolved**: 10.2 Task 3.3 base `envSlug: production`, dev overlay injects `dev` via JSON patch; `test_prod_named_secrets_never_bind_dev_slug` asserts it.
- Test robustness (`_api_key_headers`/`_api_key_paths` regex loose, substring route-attachment, duplicate-key miss, no `test_*` tuple guard) — **resolved**: 10.2 Task 4 rewrote route-audit structure-aware (9 checks) + secret-scan (7 checks) with `_UniqueKeyLoader`, structural overlay resolution, effective parentRef resolution, and strict `main()` guards.
- `native-auth` annotation on UI routes unvalidated by r1 — **resolved**: 10.2 Task 1.4 gates the value to exact string-bool `"true"`/`"false"` in the route-audit (project-declared marker, no upstream enum); latent catch-all `/` ambiguity on the two native-auth UI routes recorded below.

## Still open (from 10-1 review)

- Path-level auth gaps on `hpdc-edge-domain-routes` (`/data`, `/api`, `/gql`) — the path-level apiKeyAuth from 10.2 Task 1.1 now covers `/data` `/api` `/events`; `/gql` is owned by `hpdc-graphql-gateway`. Residual: `/gql` is not covered by path-level auth on the domain route itself (defense-in-depth nicety, not required).
- InfisicalSecret CRD will not reconcile (no operator/CRD definition/`credentialsRef` secret in tree) — pre-existing infra; AC 5 literally satisfied.
- JWT policy lacks `audiences`/`forwardJWT`; runtime JWKS fetch unverifiable offline — authz beyond this story's authn AC, needs live cluster (P0-008).
- Secret scan `_base_yamls()` only scans base manifests, not overlays — pre-existing test-design limitation.

## New deferred entry (from story 10.2 Task 4 findings, 2026-08-08)

- The two native-auth UI routes (`hpdc-edge-observability-ui-routes`, `hpdc-edge-tool-ui-routes`) both carry a `*.hpdc.local` PathPrefix `/` catch-all — the sanctioned default-backend group, but Envoy Gateway resolves equal-specificity conflicts non-deterministically; latent pre-existing ambiguity to revisit (revisit when the UI default-backend is made explicit). Blast-radius (review-plan Dig-in 3, 2026-08-08): deterministic cases are (a) hostname-specificity wins for `grafana.hpdc.local` / `hubble.hpdc.local` dedicated routes and (b) longest-path-prefix wins for `/api` `/data` `/events` `/gql` `/telemetry` `/hpdc.telemetry.v1.TelemetryService` `/hubble` `/argocd` `/kargo`; the genuinely nondeterministic set is exactly the root path `/` (and any un-prefixed path) of a `*.hpdc.local` host with no dedicated hostname route (e.g. `argocd.hpdc.local/`, `backstage.hpdc.local/`), which routes to an arbitrary member of `{grafana, hubble-ui, argocd-server, backstage, kargo-ui}`. Mitigation when addressed: drop the `/` catch-all from one UI route or give every UI host a dedicated hostname route.

## Deferred from: code review re-run of story-10.1 (2026-08-07)

- `/gql` and `/telemetry` shadowing by `hpdc-edge-domain-routes` may make the new JWT/api-key SecurityPolicies dead config (identical PathPrefix matches, no path-level auth on domain-routes) — pre-existing overlapping topology; story must not alter route topology.
- JWKS host `https://casdoor.hpdc.local/.well-known/jwks.json` has no in-tree HTTPRoute; gateway fetches keys from a hostname only resolvable out-of-band — JWT fails closed or needs undeclared DNS; unverifiable offline (live cluster).
- Telemetry policy reuses `messaging-api-keys` with no key selection (`events-key`/`telemetry-key` both accepted) — R-009 isolation not enforced; story Subtask 2.2 mandated reuse, key-level selection is a latent enhancement.
- Harbor overlay lists `../../base/harbor-values.yaml` (raw helm values, no apiVersion/kind) as a kustomize resource — `kustomize build` fails for harbor; AC 4 literal holds, wiring predates story.
- InfisicalSecret prod-named (`hpdc-production-secrets`/`hpdc-prod-credentials`) with `envSlug: dev`; envSlug hardcoded in base — future prod overlay would silently pull dev creds; patch per-overlay when prod overlay added.
- Test robustness: `_api_key_headers`/`_api_key_paths` regex loose, route-attachment is substring check, YAML-validity test misses duplicate keys, no guard for `test_*` in `main()` tuples — pre-existing test design, no current false pass.
