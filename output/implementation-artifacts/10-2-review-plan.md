# Review Plan: Story 10.2 — Dig-in (per-risk-spot)

Persistent plan for the checkpoint review of
`output/implementation-artifacts/10-2-harden-gitops-and-route-policy-live-config.md`
(baseline `9c22da1`). Update status + notes after each dig-in session so the next
session can resume. One dig-in per risk spot, run in order.

Status legend: `pending` → `in-progress` → `cleared` (no issue) | `finding`
(issue found, note it). A `finding` blocks story sign-off until resolved or
explicitly accepted.

## Session status — for the next session (updated 2026-08-08)

- **Plan is COMPLETE.** All 5 dig-ins `cleared`; review verdict recorded below.
  There is **no remaining dig-in work** for story 10.2. If you opened this file
  expecting work, you only need to (a) confirm nothing on these risk spots
  changed since 2026-08-08, and (b) resume the normal sprint flow (next story,
  epic-10 retrospective, or a deferred-work item below).
- **Code changed during the review (all committed to the working tree, story
  work uncommitted, HEAD == baseline `9c22da1`):**
  - Dig-in 1: `tests/atdd/e2e/test_p0_route_table_audit.py`
    `test_api_key_stores_are_key_isolated` — per-store path-ownership assertion.
  - Dig-in 2: `tests/test_install_harbor_dev.py` + `scripts/install_harbor_dev.py`
    — harbor-values embed↔disk parsed-equality drift guard.
  - Dig-in 4: `tests/atdd/e2e/test_p0_secret_scan.py`
    `test_prod_named_secrets_never_bind_dev_slug` — overlay-wide dev-slug guard.
- **Story/sprint state:** story `10-2-harden-gitops-and-route-policy-live-config.md`
  `Status: done`; `sprint-status.yaml` 10-2 → `done`; deferred-work.md updated
  (Dig-in 3 blast-radius amplification + resolved-by-10.2 markers).
- **Re-verify harness expected counts** (verified 2026-08-08, post-review-fixes):
  the harness pytest set below yields **18 passed** (exact command run); the
  wider `tests/atdd/e2e/` run is 20 passed / 6 skipped (skips = deferred
  live-cluster journeys, unrelated). See the harness block for the current green
  commands.

## Baseline facts (verified 2026-08-08)

- HEAD == baseline `9c22da1`; story work is uncommitted. `tests/atdd/` is entirely
  untracked.
- Regression green: route-audit standalone 9/9 exit 0; secret-scan standalone
  7/7 exit 0; affected pytest 19 passed (pre-review-fix count — now 18 on the
  harness set / 20+6 skipped wider, see Session status); all three install
  `--check` scripts +
  offline-gitops validation pass; 34/34 overlays build
  (`kubectl kustomize --load-restrictor=LoadRestrictionsNone`; filter stderr
  `# Warning` — commonLabels deprecation is pre-existing/non-fatal).
- `/tmp` disk quota is exhausted for this user — pipe kustomize output, never
  redirect to `/tmp`.
- Pre-existing unrelated failure: `test_install_harbor_dev.py::test_dry_run_mode`
  (offline image cache missing `harbor-redis-v1.23`).

## Re-verify harness (run at the start of every dig-in session)

```bash
python tests/atdd/e2e/test_p0_route_table_audit.py   # expect 9/9, rc 0
python tests/atdd/e2e/test_p0_secret_scan.py         # expect 7/7, rc 0
python -m pytest tests/test_install_harbor_dev.py::test_check_mode \
  tests/atdd/e2e/test_p0_route_table_audit.py \
  tests/atdd/e2e/test_p0_secret_scan.py \
  tests/test_epic3_gateway_stack_dev.py -q           # expect 18 passed (harness set)
python scripts/install-api-key-auth-dev.py --offline --check
python scripts/install-telemetry-ingestion-dev.py --offline --check
python scripts/install_harbor_dev.py --offline --check   # now also gates values-embed drift
python tests/test_validate_offline_gitops_pipeline.py
```

---

## Dig-in 1 — API-key store split / R-009 isolation

- **File:** `gitops/security/base/api-key-authn.yaml` (esp. `:56` apiKeyAuth block)
- **Test anchor:** `tests/atdd/e2e/test_p0_route_table_audit.py:273`
  (`test_api_key_stores_are_key_isolated`)
- **Why it matters:** wrong store→path binding silently weakens R-009; the
  manifest itself has no validator — only the audit test pins it.
- **Checks:**
  1. Enumerate every Secret + every apiKeyAuth block in `gitops/security/base/`.
  2. Verify each method path is under the correct store: `/data` `/api` `/events`
     → `events-api-key` (only key `events-key`); `/telemetry` HTTP + gRPC →
     `telemetry-api-key` (only key `telemetry-key`).
  3. Confirm no leftover `messaging-api-keys` references anywhere
     (`grep -rn "messaging-api-keys" gitops/ scripts/ tests/ docs/`).
  4. Check key values are unchanged vs `tests/atdd/support/fixtures.py` +
     `DEV_ONLY_CREDENTIALS` (no rotation needed).
  5. **Mutation probe (in-memory, do NOT edit+run+revert):** simulate a method
     added under the wrong store (or a store holding both keys) and confirm
     `test_api_key_stores_are_key_isolated` fails.
- **Cleared when:** 1–4 pass and 5 trips the test.
- **Status:** cleared
- **Notes:** Checks 1–4 passed; Probe A caught. Probe B exposed a coverage gap (path→store ownership never asserted) → **fixed 2026-08-08**: `test_api_key_stores_are_key_isolated` now aggregates per-store path ownership across all apiKeyAuth blocks and asserts events store == {/data, /api, /events}, telemetry store == {/telemetry, /hpdc.telemetry.v1.TelemetryService}; unknown store names fail. Re-verified: route-audit standalone 9/9 exit 0, secret-scan 7/7, affected pytest 18 passed; Probe A and Probe B both now caught. (First attempt asserted per-block instead of per-store and red-failed on the gRPC split — fixed to aggregate.)

---

## Dig-in 2 — Harbor values-source drift

- **Files:** `gitops/harbor/base/harbor.yaml` (ConfigMap `harbor-values`,
  `data.harbor-values.yaml` embed), `gitops/harbor/base/harbor-values.yaml`,
  `gitops/harbor/overlays/dev/kustomization.yaml`
- **Test anchors:** `tests/test_install_harbor_dev.py` (check mode),
  `scripts/install_harbor_dev.py` `validate_manifests()`
- **Why it matters:** dropping the blob from `resources` severed the tree's only
  tie between `harbor-values.yaml` on disk and the deployed ConfigMap. Drift
  between the two = silent misconfig (storageClass, Trivy, registry creds).
- **Checks:**
  1. Diff `data.harbor-values.yaml` blob in `harbor.yaml` against
     `harbor-values.yaml` — are they byte-identical today? (Normalize indentation
     if the embed is re-indented.)
  2. Determine the intended single source of truth: is `harbor-values.yaml` a
     template that is rendered into the ConfigMap, or a stale duplicate?
  3. Assess whether a drift guard is warranted (e.g., extend
     `test_install_harbor_dev.py` to assert the embed contains the same
     storageClass/Trivy/cosign keys as the on-disk file), and whether that
     belongs to story 10-2 scope or deferred-work.
- **Cleared when:** drift assessed and either (a) no drift + guard documented, or
  (b) a guard added / deferred-work entry written.
- **Status:** cleared
- **Notes:** Embed and disk file verified byte-identical + parsed-equal (no current drift); embed is a static ConfigMap copy with no linkage to the disk file. **Fixed 2026-08-08**: added parsed-equality drift guard in both `tests/test_install_harbor_dev.py::validate_manifests()` and `scripts/install_harbor_dev.py` `validate_manifests()` (extract `harbor-values` ConfigMap embed from `harbor.yaml`, `yaml.safe_load(embed) == yaml.safe_load(values)`). Probe (storageClass mutated in embed) caught; harbor --check passes, pytest check+missing-cache pass, full affected suite 19 passed.

---

## Dig-in 3 — Native-auth catch-all default-backend (shadowing tolerance)

- **File:** `tests/atdd/e2e/test_p0_route_table_audit.py:453`
  (`test_no_route_shadowing`), UI routes
  (`gitops/envoy-gateway/base/envoy-gateway.yaml` or
  `gitops/observability/base/envoy-ui-routes.yaml`)
- **Why it matters:** two UI routes carry identical `*.hpdc.local` PathPrefix `/`
  catch-alls; Envoy Gateway resolves equal-specificity conflicts
  non-deterministically. The audit sanctions this as the default-backend group.
- **Checks:**
  1. Re-read the sanctioning logic — confirm it only permits the catch-all on
     native-auth UI routes (exact string-bool `"true"`), not on any route with
     an annotation.
  2. Verify the two UI routes actually exist with equal hostname+path and record
     what Envoy Gateway's documented resolution is for equal-specificity.
  3. Assess blast radius of a misroute: what traffic actually reaches the catch-all
     (anything not matched by domain/graphql/telemetry routes)? Is the mismatch
     observable (different UI apps)? Does any auth'd path fall through to it?
  4. Decide: accept-and-defer (current), or tighten (e.g., require distinct
     hostnames per UI backend). If defer, confirm the deferred-work entry exists
     (`output/implementation-artifacts/deferred-work.md`, "New deferred entry").
- **Cleared when:** tolerance correctly scoped, blast radius assessed, decision
  recorded (accept+defer or tightened with test update).
- **Status:** cleared (accept-and-defer — existing deferred-work entry amplified)
- **Notes:** Sanction gate verified tight: catch-all `/` only permitted when `native_auth == "true"` (exact string-bool, `test_no_route_shadowing` lines 501–507); pair-wise same-hostname/same-path different-backend conflict check (lines 489–500). Mutation probe (native-auth flipped to `"false"` on `envoy-ui-routes.yaml`) CAUGHT — probe harness must patch `_load_docs` (not a nonexistent `_read_file`). Topology enumerated (10 hpdc-edge routes): 2 sanctioned wildcard `/` catch-alls (observability `{grafana,hubble-ui}`, tool `{argocd,backstage,kargo-ui}`) + dedicated hostname catch-alls for grafana/hubble (win by hostname specificity). Blast radius: deterministic longest-prefix wins cover `/api /data /events /gql /telemetry /hpdc.telemetry.v1.TelemetryService /hubble /argocd /kargo`; only the root `/` of a wildcard host with no dedicated route (argocd.hpdc.local/, backstage.hpdc.local/) is genuinely nondeterministic across `{grafana, hubble-ui, argocd-server, backstage, kargo-ui}`. Deferred (entry amplified at `deferred-work.md` line 36 with blast radius + mitigation); no code change — sanctioned design tolerance, not a check gap.

---

## Dig-in 4 — envSlug patch / dev-creds-in-prod guard

- **Files:** `gitops/infisical/base/infisical-secret.yaml:18`,
  `gitops/infisical/overlays/dev/kustomization.yaml:9`,
  `tests/atdd/e2e/test_p0_secret_scan.py:203`
  (`test_prod_named_secrets_never_bind_dev_slug`)
- **Why it matters:** base `envSlug: production` + dev-inject patch is the only
  guard against a future prod overlay silently pulling dev credentials. The test
  covers base + dev overlay only.
- **Checks:**
  1. Verify the JSON patch is correctly targeted (kind `InfisicalSecret`, name
     `hpdc-production-secrets`) and that `kubectl kustomize` on the dev overlay
     outputs `envSlug: dev` (pipe output — no `/tmp`).
  2. Confirm the base builds to `envSlug: production` (no overlay).
  3. Probe: would a staging overlay inherit `production` (safe) without a patch?
     Would a future prod overlay necessarily inherit `production`? Is the test's
     coverage window (base+dev) the right contract?
  4. Check whether other prod-named secrets exist
     (`grep -rn "prod-credentials\|production-secrets" gitops/`) and whether
     `hpdc-prod-credentials` appears anywhere.
- **Cleared when:** patch targets verified, build output confirms `dev` only in
  dev overlay, and the coverage-window decision is recorded (accept as-is or
  extend test to assert any overlay with a prod-named InfisicalSecret injects
  its own slug).
- **Status:** cleared (tightened — overlay-wide guard)
- **Notes:** Patch target verified (kind `InfisicalSecret`, name `hpdc-production-secrets`); `kubectl kustomize --load-restrictor=LoadRestrictionsNone` on the dev overlay outputs `envSlug: dev`, base stays `envSlug: production`. Note: `gitops/infisical/base/` has no kustomization.yaml (raw resource dir consumed by overlays) and plain `kubectl kustomize` fails on the `../../base/...` refs — must pass `--load-restrictor=LoadRestrictionsNone` (matches route-audit overlay resolution). Coverage gap found + **fixed 2026-08-08**: base-only scan missed a future non-dev overlay binding the prod-named secret to `envSlug: dev`; `test_prod_named_secrets_never_bind_dev_slug` now also scans all `*/overlays/*/kustomization.yaml` and fails any non-dev overlay containing `hpdc-production-secrets` + `envSlug` + `value: dev`. Probe (simulated staging overlay) CAUGHT; real tree passes (7/7). Only the dev overlay references the prod-named secret; `hpdc-prod-credentials` managed ref is base-only.

---

## Dig-in 5 — JWKS tolerance / per-route policy coverage

- **Files:** `tests/atdd/e2e/test_p0_route_table_audit.py:204`
  (`test_every_http_grpc_route_has_security_policy`),
  `gitops/casdoor/base/casdoor.yaml:116`
- **Why it matters:** `hpdc-casdoor-jwks` is tolerated with no SecurityPolicy by
  name-match. A future route whose name resembles the tolerance list could slip
  past coverage.
- **Checks:**
  1. Read the tolerance implementation — exact name match vs substring vs
     hostname match (`casdoor.hpdc.local`)? Prefer hostname-based tolerance over
     name-based if that is stronger.
  2. Confirm the JWKS route cannot be shadowed by the `*.hpdc.local` wildcard
     (most-specific-hostname rule) and that its parentRef/namespace pin is
     correct.
  3. Probe: rename a real protected route to a name containing the tolerance
     token and confirm the check still fails for it (in-memory mutation).
  4. Decide: keep name-based tolerance (documented) or tighten to hostname-based.
- **Cleared when:** tolerance scope verified tight (or tightened), shadowing
  confirmed impossible, mutation probe fails correctly.
- **Status:** cleared (no change — exact-name gate is already the strongest option)
- **Notes:** Tolerance is exact equality (`route["name"] == CASDOOR_JWKS_ROUTE`, line 225), NOT substring — a renamed protected route (`hpdc-casdoor-jwks-graphql`) still fails the policy-coverage check (mutation probe CAUGHT). Shadowing impossible: JWKS route pins hostname `casdoor.hpdc.local` (specific, beats all `*.hpdc.local` wildcards by most-specific-hostname) + `parentRefs[].namespace: envoy-gateway-system`, sectionName `https` (cross-namespace pin correct); path `/.well-known/jwks.json` exists only on that route, so even path-longest-prefix is unambiguous. Hostname-based tolerance would be WEAKER (would tolerate any future route on `casdoor.hpdc.local`); exact-name equality is the tightest practical gate. Kept as-is, documented.

---

## Wrap-up (after all five)

- [x] All dig-ins cleared (or findings accepted/resolved)
- [x] Story `Status:` stays `done` or moves per findings
- [x] Any new findings written to `output/implementation-artifacts/deferred-work.md`
- [x] `sprint-status.yaml` story → `done` (if no blocking findings)
- [x] This plan marked complete / archived

## Review verdict (2026-08-08)

All five dig-ins cleared. Two findings fixed (Dig-in 1 path-ownership in
`test_api_key_stores_are_key_isolated`; Dig-in 2 harbor values-source drift
guard; Dig-in 4 overlay-wide dev-slug guard). Two accept-and-defer (Dig-in 3
native-auth catch-all blast radius amplified at `deferred-work.md`; Dig-in 5
JWKS exact-name tolerance verified tight, no change). Full regression green:
route-audit 9/9, secret-scan 7/7, affected pytest 18 passed, harbor --check
passes. No blocking findings; story stays `done`.
