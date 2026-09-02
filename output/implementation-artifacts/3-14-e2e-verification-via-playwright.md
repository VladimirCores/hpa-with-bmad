# 3-14 — E2E verification of EG-exposed services via Playwright (TypeScript/Node)

> **Status:** Authored + verified to compile & skip cleanly in dev. **Live run deferred** pending the
> Gateway-API / cert-manager CRD-install blockers documented below.
> **Epic:** 3 (Envoy Gateway edge routing) · **Follows from:** 3-1, 3-2, 3-3, 3-4, 3-13.

## Context / Goal
Per the stakeholder pivot, the end-to-end harness for every component publicly
exposed through the Envoy Gateway (`hpdc-edge`, ns `envoy-gateway-system`) is now
**Playwright + TypeScript (Node.js)** instead of pytest. One test per EG route:

| # | Route / surface | Hostname / path | Backend |
|---|-----------------|-----------------|---------|
| 1 | Edge infra — Gateway programmed | `hpdc-edge` status.conditions | Gateway API |
| 2 | HTTP(80) → HTTPS(443) redirect | `*` | hpdc-edge http listener |
| 3 | TLS termination for `*.hpdc.local` | 443 | `hpdc-edge-tls` Secret |
| 4 | Route Accepted wiring | all hpdc-edge routes | Gateway API status |
| 5 | CASBANDORA login | `casbandora.hpdc.local /` | `casdoor:8080` |
| 6 | GraphQL introspect | `graphql.hpdc.local /gql` | `graphql-gateway:8080` |
| 7 | Grafana front | `grafana.hpdc.local /` | `grafana:80` |
| 8 | Hubble UI | `hubble.hpdc.local /` | `hubble-ui:80` |
| 9 | Argo CD via tool-ui | `argocd.hpdc.local /argocd` | `argocd-server:80` |
| 10 | Telemetry HTTP ingestion | `telemetry.hpdc.local /telemetry` | `pulsar-standalone:8080` |
| 11 | Telemetry gRPC route attached | `hpdc.telemetry.v1.TelemetryService` | `pulsar-telemetry-ingestion:6669` |
| 12 | Telemetry gRPC backend ready | same | Endpoints |
| 13 | Telemetry gRPC h2/TLS handshake | same | ALPN h2 |
| 14 | Telemetry MQTT TCP route attached | mqtt:1884 | `pulsar-telemetry-ingestion:1884` |
| 15 | Authn gate rejects w/o key | `*.hpdc.local /data` | `couchdb-entity-store` |
| 16 | Authn gate accepts valid key | `*.hpdc.local /data` | + `events-api-key` Secret |

## Nothing hard-coded
`EG address`, every `HTTPRoute/GRPCRoute/TCPRoute` hostname/path/backend, and the
`X-API-Key` values are all resolved **live** via `kubectl` at test time:

* `egAddress()` → svc `envoy-gateway` LB ingress → Gateway `.status.addresses[0].value` →
  `.spec.addresses[0].value` → `HPDC_GATEWAY_IP` env → fallback `10.6.0.1`.
* `routes(kind)` → `kubectl get httproute|grpcroute|tcproute -A -o json`, filters `parentRefs` whose
  `name == hpdc-edge`, parses `hostnames`/`path`/`backendRefs`.
* `routeFor(host,path)` → wildcard `*.hpdc.local` match.
* `svcReady(svc,ns)` → `kubectl get endpoints <svc> -o jsonpath={.subsets[*].addresses[*].ip}`.
* `apiKey('events-api-key','events-key')` → `kubectl get secret events-api-key -n security -o jsonpath={.data.events-key} | base64 -d`.

## Env-gating (the contract)
* **Whole file** skipped when `EG_DEPLOYED` is false, i.e. `kubectl get gatewayclass -o name`
  returns nothing **or** `envoy-gateway-system` namespace is absent:
  ```ts
  const EG_DEPLOYED = !!kubectl('get gatewayclass -o name') && !!kubectl(`get ns ${EG_NS} -o name`);
  test.describe(() => { test.skip(!EG_DEPLOYED, '<deploy instructions>'); ... });
  ```
* **Per-component** tests use `if (!r || !backendReady(r)) test.skip(true, '<reason>')` so a
  partial platform deploy yields **skips**, never false failures.

## Files
| Path | Purpose |
|------|---------|
| `e2e/tests/eg-exposed.spec.ts` | The canonical Playwright suite (16 tests). |
| `e2e/playwright.config.ts` | `testDir`, `ignoreHTTPSErrors`, `trace: on-first-retry`, `globalSetup`. |
| `e2e/global-setup.ts` | Refreshes Talos kubeconfig + wipes `~/.kube/cache` (stale-discovery guard). |
| `e2e/package.json` | `@playwright/test ^1.62`, `typescript ^5.6`, `@types/node`. |
| `e2e/tsconfig.json` | ES2022 / CommonJS / strict. |
| `tests/test_eg_exposed_e2e.py` | **DELETED** — obsolete pytest sibling, superseded by the TS suite. |

## Verification — dev (EG absent)
```
$ cd e2e && npx tsc --noEmit          # TSC_CLEAN
$ npx playwright test --list          # 16 tests in 1 file
$ npx playwright test
Running 16 tests using 1 worker
  16 skipped       # whole file skipped — EG not deployed (correct dev behaviour)
```
Toolchain: `node v24.12.0`, `npm 11.6.2`, `@playwright/test` 1.62.1 (browser binaries NOT required —
the suite uses `request` + Node `tls`/`net`, not the `page` fixture). `npm install` succeeded in `e2e/`.

## Blockers to a live (passing) run — DO NOT REDO the blind retry
The dev `startup.py` is intentionally **offline / dry-run**; EG + components are NOT deployed in dev.
A live run requires resolving these, in order:

1. **Gateway-API + Envoy-Gateway CRDs won't apply.**
   `gitops/crds/gateway/crds.yaml` (21 CRDs) embeds a **>256 KB `metadata.annotation`** on the
   Envoy-Gateway CRDs (`envoyproxies.gateway.envoyproxy.io`,
   `securitypolicies.gateway.envoyproxy.io`) — the API server rejects server-side with
   `metadata.annotations: Too long: may not be more than 262144 bytes`. Stripping **all**
   annotations additionally breaks the Kubernetes Gateway-API CRDs (`udproutes`,
   `httproutes`, …) which require `api-approved.kubernetes.io`.  **Fix:** strip every
   annotation *except* `api-approved.kubernetes.io`, then `kubectl apply -f`.

2. **cert-manager CRDs are absent from gitops.**
   `gitops/crds/{gateway,hpdc,pulsar}` + `gitops/cert-manager/base/cert-manager.yaml` (0 CRDs)
   → no `cert-manager.io/v1` CRD → `Certificate`/`ClusterIssuer` for `hpdc-edge-tls` can’t be
   admitted → EG HTTPS listener has no cert. **Fix:** either install `jetstack/cert-manager`
   CRDs (`helm pull oci://.../jetstack/cert-manager --include-crds` / the upstream CRDs manifest),
   **or** mint a static self-signed `*.hpdc.local` Secret as `hpdc-edge-tls` (already proven —
   see `secret/hpdc-edge-tls` created in the attempt below).

3. **The install scripts are validators, not appliers.**
   `scripts/steps/NN-install-*-dev.py` and `scripts/gitops/install-*-dev.py --apply` only
   `print("apply requested"); return 0`. Do NOT call them with `--apply` expecting a deploy.

4. **App-of-Apps is blocked by the git-mirror service gap.**
   `gitops/app-of-apps/root-application.yaml` hard-codes `repoURL http://git-mirror.git-mirror.svc.cluster.local:9418/...`,
   but `provision_local_git_mirror.py` only runs a *host* daemon (`10.6.0.1:9418`) and patches
   `argocd-cm` with the host repoURL. Bridge the svc↔host-daemon repoURL gap before re-enabling.

## What was done to attempt a live run (then reverted)
` /tmp/deploy_final.sh` (ephemeral scratch — **not** saved to repo; reproduce via the
"How to run live" steps below):

1. Refreshed Talos kubeconfig (`talosctl kubeconfig`); `rm -rf ~/.kube/cache`.
2. Stripped `metadata.annotations` from `gitops/crds/gateway/crds.yaml` → `/tmp/crds_clean.yaml`,
   `kubectl apply -f`. **Result:** `gatewayclasses`/`gateways` CRDs registered; but
   `udproutes`/`httproutes`/EG CRDs (`envoyproxies`, `securitypolicies`) still rejected
   (`api-approved` missing for GA; `Too long` for EG — the naive strip was incomplete).
3. Created static `hpdc-edge-tls` (`*.hpdc.local`, 365d) in `envoy-gateway-system`.
4. `kubectl apply -f` of `envoy-gateway`, `casdoor`, `security`, `observability` rendered manifests
   — EG GatewayClass/Gateway Deployment + casdoor/grafana/hubble-ui pods came up, but
   **Gateway never reached `Ready`** (missing `httproute` CRD → routes not admitted) and the
   casbandora/hubble routes couldn't attach.

**Revert performed to restore the green minimal dev cluster:**
`kubectl delete gatewayclass hpdc-envoy-gateway`; `kubectl delete -f /tmp/crds_clean.yaml`
(the Gateway-API + EG CRDs); deleted namespaces `envoy-gateway-system`, `casbandora`,
`casdoor`, `observability`, `cert-manager`, `security`. The dev cluster is back to the
documented minimal state: 4/4 Talos nodes Ready, `local-path (default)` SC, API `401`,
Harbor (8 pods) + Cilium + Argo CD Running, **no** rook-ceph, **no** EG.

## How to run live (resume)
Once the blockers above are cleared:
```bash
# 0. point kubectl at dev Talos cluster
talosctl kubeconfig && rm -rf ~/.kube/cache
# 1. Gateway-API + Envoy-Gateway CRDs (strip giant annotation, KEEP api-approved.k8s.io)
python3 - <<'PY' | kubectl apply -f -
import yaml,sys
docs=[d for d in yaml.safe_load_all(open('gitops/crds/gateway/crds.yaml')) if d]
for d in docs:
    ann=(d.get('metadata') or {}).get('annotations') or {}
    keep={k:v for k,v in ann.items() if k=='api-approved.kubernetes.io'}
    (d.setdefault('metadata',{}) if False else d['metadata'])['annotations']=keep or None
yaml.safe_dump_all(docs,sys.stdout,default_flow_style=False,sort_keys=False)
PY
# 2. TLS cert (static bypass of missing cert-manager CRDs)
kubectl create ns envoy-gateway-system --ignore-not-found
openssl req -x509 -newkey rsa:2048 -nodes -keyout /tmp/tls.key -out /tmp/tls.crt -days 365 \
  -subj "/CN=*.hpdc.local" -addext "subjectAltName=DNS:*.hpdc.local,DNS:hpdc.local"
kubectl create secret tls hpdc-edge-tls -n envoy-gateway-system --cert=/tmp/tls.crt --key=/tmp/tls.key --dry-run=client -o yaml | kubectl apply -f -
# 3. edge slice
kubectl apply -f gitops/envoy-gateway/rendered/dev.yaml
kubectl apply -f gitops/casdoor/rendered/dev.yaml
kubectl apply -f gitops/security/rendered/dev.yaml
kubectl apply -f gitops/observability/rendered/dev.yaml   # grafana + hubble-ui
#    (casbandora, grafana, hubble are the only live backends in dev; graphql/telemetry/entity-store
#     are NOT deployed -> tests 6,10-14,15,16 will SKIP even with EG up.)
# 4. wait for Gateway + backends
kubectl wait --for=jsonpath='{.status.conditions[?(@.type=="Ready")].status}=True' \
  gateway/hpdc-edge -n envoy-gateway-system --timeout=180s
kubectl wait --for=jsonpath='{.subsets[*].addresses[*].ip}!={}' \
  endpoints/casdoor -n casbandora --timeout=120s
# 5. run
cd e2e && npx playwright test        # expect infra + casbandora + grafana + hubble PASS, rest SKIP
# 6. tear down (restore minimal dev)
kubectl delete -f gitops/envoy-gateway/rendered/dev.yaml gitops/casdoor/rendered/dev.yaml \
  gitops/security/rendered/dev.yaml gitops/observability/rendered/dev.yaml --ignore-not-found
kubectl delete gatewayclass hpdc-envoy-gateway --ignore-not-found
kubectl delete ns envoy-gateway-system casbandora observability security --ignore-not-found
```

## Deferral note
Deliverable per the stakeholder request: the **env-gated Playwright + TS suite** (the file-level
skip is verified; per-component skips are implemented). A *live passing* run is blocked by the
repo's CRD-install + cert-manager gaps (items 1–2 above) which are out of scope for the e2e
story itself — track those as follow-ups on stories 3-1 / 3-2 (TLS/cert-manager CRD sourcing) and
the `gitops/crds/gateway/crds.yaml` annotation-bloat cleanup.
