# Deferred Work Ledger

## Deferred from: provider switch kind -> QEMU (2026-08-30)

- **kind (Docker) cluster setup deferred** — the kind provider hit a pre-existing,
  cluster-wide kube-proxy failure (`too many open files` crash-loop on workers →
  in-cluster service networking to the apiserver `10.96.0.1:443` broken → ArgoCD
  controller/repo-server/server degraded, no app-of-apps sync). Instead of debugging
  the kind network stack, the dev cluster is being switched to the already-implemented,
  code-reviewed QEMU provider (story q2). QEMU uses Talos + Cilium (no kube-proxy, so the
  crash-loop root cause is eliminated) + Rook-Ceph on real virtio-blk disks.
  **Resume path / left undone:** finish/validate the kind (Docker) provisioning story
  (Epic 12 landing) later — the kind path (`HPDC_PROVIDER=kind`) remains implemented in
  `scripts/` and selected via `.env`; it was failing only because of the environment
  (kube-proxy fd exhaustion + argocd outage), not a code defect. Kind remains the fast,
  resource-light local default for non-storage-sensitive work; QEMU is the prod-eval
  topology. Both coexist; `.env` selects. See epic-12 + q2 story records.

## Deferred from: code review of 11-5-platform-convergence-app-of-apps (2026-08-29)

- RWO local-path PVC pins broker to its node — pod Pending if it reschedules to a different node. Pre-existing cluster storage posture (same as git-mirror).
- Bookie journal replay after unclean kill could exceed 600s startupProbe ceiling and default 30s termination grace. Operational tuning; observed recovery well within window.
- No backlogQuota/msgTTL on PulsarNamespace — a stalled consumer could fill the 10Gi PV despite 24h retention. Operational hardening for dev budget.
- Topic partition/policy mismatch is unrecoverable (partitions immutable) → operator retries until exhaustion. Documented operator limitation.
- Pulsar image size (~multi-GB) not re-validated against 8GB qemu/Talos node disks — kind/local-path target OK, qemu target unproven. Topology-specific.

## Resolved / dispositions by live verification (story 11-4, 2026-08-29)

Live cluster verification (Task 3) dispositioned the register entries that were previously
gated only on B-001 (live cluster). Evidence recorded in
`output/test-artifacts/live-cluster-verification-register.md` (Live-Cluster Evidence
2026-08-29).

- **REG-06 PromQL range SLO** — **resolved**: 5 live 24h-range queries on vmselect, all
  success in ≤0.01s (SLO 2s). Entry `verified`.
- **REG-07 entity-store mutation SLO** — **resolved**: live CouchDB CRUD round-trip
  create 7.6ms / read 2.0ms / update 0.5ms (SLO p99 200ms). Entry `verified`.
- **REG-01 Infisical / REG-02 JWT+JWKS / REG-04 log-search / REG-05 stale-metric /
  REG-08 change-reaction / REG-09 Restate / REG-10 Hasura / REG-03 ClusterMesh** —
  **dispositioned** (not silently deferred): each marked `blocked` with a concrete
  missing-component evidence tuple (no Infisical operator; casdoor/casbin
  ImagePullBackOff; no vmlogs pod; telemetry-ingestion selector-less, no vmalert; no
  Restate/Knative; no Hasura; B-004 single cluster). These are now actionable
  deployment gaps, not B-001 gates.
- **Duplicate ArgoCD install in `default` ns** (ImagePullBackOff, full component set) —
  stale bootstrap leftover; healthy ArgoCD lives in `argocd` ns. Recorded in register +
  sprint-status for cleanup.
- **Stale e2e audits** — the route-table audit parsed the pre-EG-v1.9 SecurityPolicy
  schema and the secret-scan flagged public SSH host keys. Fixed in commit `c793231`
  (v1.9 `targetRefs`/`credentialRefs`/`extractFrom`, in-route path scoping; public
  `ssh_known_hosts` redaction). `tests/atdd/e2e/` now 17 passed / 6 skipped.

## Deferred from: code review of story-11.8 (2026-08-26)

- AC#4 spec inconsistency — known components use `ENABLED_DEFAULTS`; only unknown defaults False. Documented user decision (opt-in for unknown). (deferred, spec clarification)
- `gitops/apps/` not gitignored — generated output committable. (deferred, pre-existing pattern issue)
- Core-toggle guard fragile — tuple vs `CORE_TOGGLES` duplication. (deferred, low risk)
- Duplicate mTLS step 24 not gated separately — same as step 04. (deferred, intentional)
- Unknown component name silently returns False (typo mask). (deferred, low risk)
- Test pollution: storage vars leak between tests. (deferred, tests pass but fragile)

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
  - **RESOLVED 2026-08-17:** `/` catch-all dropped from `hpdc-edge-observability-ui-routes` (`gitops/observability/base/envoy-ui-routes.yaml`) — grafana/hubble have dedicated hostname routes, so the tool-ui route is now the sole `/` default-backend. Route-audit `test_no_route_shadowing` now flags any two native-auth routes sharing a wildcard `/` catch-all. Closed items #1/#11/#19.

## Resolved 2026-08-17 (route-topology close-out)

- `/gql` route ownership (#13): `hpdc-graphql-gateway` (Hasura) owns `/gql`. The entity-store owns the `/gql` backends it exposes; `hpdc-edge-domain-routes` must NOT carry a path-level match for `/gql` (it belongs to the gateway route, enforced by `test_no_route_shadowing`). Contract recorded here for the route-topology review.
- Native-auth lineage (#19): the `casdoor_casbin_ext_authz: false` native tool-auth pattern from 3-12/3-13 (observability + tool UI routes) is the root family of the `/` catch-all; resolved by C5 above (single default-backend rule).

## Deferred from: code review re-run of story-10.1 (2026-08-07)

- `/gql` and `/telemetry` shadowing by `hpdc-edge-domain-routes` may make the new JWT/api-key SecurityPolicies dead config (identical PathPrefix matches, no path-level auth on domain-routes) — pre-existing overlapping topology; story must not alter route topology.
- JWKS host `https://casdoor.hpdc.local/.well-known/jwks.json` has no in-tree HTTPRoute; gateway fetches keys from a hostname only resolvable out-of-band — JWT fails closed or needs undeclared DNS; unverifiable offline (live cluster).
- Telemetry policy reuses `messaging-api-keys` with no key selection (`events-key`/`telemetry-key` both accepted) — R-009 isolation not enforced; story Subtask 2.2 mandated reuse, key-level selection is a latent enhancement.
- Harbor overlay lists `../../base/harbor-values.yaml` (raw helm values, no apiVersion/kind) as a kustomize resource — `kustomize build` fails for harbor; AC 4 literal holds, wiring predates story.
- InfisicalSecret prod-named (`hpdc-production-secrets`/`hpdc-prod-credentials`) with `envSlug: dev`; envSlug hardcoded in base — future prod overlay would silently pull dev creds; patch per-overlay when prod overlay added.
- Test robustness: `_api_key_headers`/`_api_key_paths` regex loose, route-attachment is substring check, YAML-validity test misses duplicate keys, no guard for `test_*` in `main()` tuples — pre-existing test design, no current false pass.

## Deferred from: code review of 11-7-centralize-component-image-versions-in-env (2026-08-26)
- Repo-spelling inconsistency in component_versions.py catalog: harbor uses bare `redis` while argocd uses `docker.io/library/redis`. Safe today (distinct strings, both governed), but a future bare-`redis` argocd manifest would collide with harbor's first-wins substitution. Pre-existing design, not introduced by 11-7.

## Deferred from: code review of q2-migrate-dev-cluster-docker-to-qemu (with-bmad 2026-08-25)
- create-failure heuristics: distinguish real create errors from designed cni=none timeout; log captured stderr tail
- root/user invocation ownership normalization for resources/ tree
- subnet validation beyond default 10.6.0.0/24 topology

## Deferred from: code review of story 12-1-docker-kind-default-dev-provisioning-with-local-path (2026-08-28)
- configure_talosconfig() (bootstrap_talos_dev.py:184) is dead code — defined but never called; its guarantee (placeholder output/talos/talosconfig) never runs. Pre-existing; entangled with step-05 kind crash but not caused by this diff.
- bootstrap_talos_dev --provider default "qemu" disagrees with stack default "kind" (bootstrap_talos_dev.py:742 falls back to qemu, step 02/startup default to kind); reconciled only because step 02 guards provider membership first. Direct/imported talos_main calls with no env silently default to qemu. Pre-existing latent inconsistency.
- build_mode_args adds dead weight — bootstrap_kind_dev.py:114 puts `--provider` into mode_args list, but step 02 never reads it (routes purely on env). Cosmetic only, no functional impact. Pre-existing.
- sys.argv side-effect coupling in step 02 — run_step mutates sys.argv before calling step_main, so step 02's argparse defaults run against modified sys.argv. Works but fragile. Pre-existing.
- stop.dev.py not dispatched by HPDC_PROVIDER — tears down ALL cluster types unconditionally (deviates from spec Task 3). Pre-existing; stop.dev.py not modified in this diff.
- Task 4 "Size kind node backing store" not implemented — kind ignores HPDC_WORKERS, HPDC_CPUS_*, HPDC_MEMORY_*. Pre-existing kind sizing.
- DEFAULT_STORAGE="rook-ceph" disagrees with docker expectation — documented; kind/docker path gates on storage flag, not default.
- HPDC_DISKS in .env.example shadows capacity knobs for qemu — documented precedence: HPDC_DISKS wins over capacity knobs.
