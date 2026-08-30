# Envoy Gateway Edge Routing

This story installs the Envoy Gateway control plane and the HPDC edge routing contract.

## Route table

| Prefix | Host | Backend | Auth |
| --- | --- | --- | --- |
| `/data` | `*.hpdc.local` | CouchDB | X-API-Key |
| `/api` | `*.hpdc.local` | Knative + Restate | X-API-Key |
| `/gql` | `*.hpdc.local` | Hasura | Casdoor JWT + Casbin |
| `/events` | `*.hpdc.local` | Kafka | X-API-Key |
| `/telemetry` HTTP | `*.hpdc.local` | Pulsar telemetry ingestion | X-API-Key |
| `/telemetry` gRPC | `*.hpdc.local` | Pulsar telemetry ingestion | X-API-Key |
| `/couchdb` (Fauxton UI + REST) | `admin.hpdc.local` | CouchDB | CouchDB native login |
| `mqtt:1884` | — | Pulsar telemetry ingestion | Platform-side MQTT auth |

> The `/couchdb` admin route on `admin.hpdc.local` is the only route exposed without a gateway
> `SecurityPolicy`: its rewrite strips `/couchdb` before forwarding to CouchDB, so Fauxton and the
> REST API operate against CouchDB's root, and authorization is CouchDB's own admin session.

## GitOps paths

- Base manifest: `gitops/envoy-gateway/base/envoy-gateway.yaml`
- Dev overlay: `gitops/envoy-gateway/overlays/dev/kustomization.yaml`

## Exposing component admin/settings UIs

When a component behind the edge gateway ships its own admin/settings UI (a web console with its
own login) — e.g. CouchDB Fauxton, Hasura Console, Knative Dashboard — do **not** place it behind
the machine-oriented API-key or JWT policies on `*.hpdc.local`. Browsers cannot attach `X-API-Key`
headers on navigation, so those paths are only reachable from scripts. Instead, expose component
consoles on a dedicated host that keeps the component's own auth as the boundary.

### Pattern (CouchDB Fauxton as the reference case)

1. **Pick a dedicated host** on the wildcard cert. The edge TLS cert covers `*.hpdc.local`, so any
   subdomain works without TLS work. The reference case uses `admin.hpdc.local`.
2. **Add an HTTPRoute with a path-prefix match and a URL rewrite** in
   `gitops/envoy-gateway/base/envoy-gateway.yaml`:

   ```yaml
   apiVersion: gateway.networking.k8s.io/v1
   kind: HTTPRoute
   metadata:
     name: hpdc-edge-couchdb-admin
     namespace: envoy-gateway-system
     labels:
       app.kubernetes.io/name: hpdc-edge-couchdb-admin
       app.kubernetes.io/part-of: hpdc-platform
   spec:
     parentRefs:
       - group: gateway.networking.k8s.io
         kind: Gateway
         name: hpdc-edge
         sectionName: https
     hostnames:
       - "admin.hpdc.local"
     rules:
       - matches:
           - path:
               type: PathPrefix
               value: /couchdb
         filters:
           - type: URLRewrite
             urlRewrite:
               path:
                 type: ReplacePrefixMatch
                 replacePrefixMatch: /
         backendRefs:
           - group: ""
             name: couchdb-entity-store
             namespace: entity-store
             port: 5984
             kind: Service
             weight: 1
   ```

   Keep the `/couchdb` prefix in front of backend requests so the response's own URLs keep working:
   Fauxton computes its API base relative to the page URL (`../`), so serving it at
   `/couchdb/_utils/` drives every API call to `/couchdb/...`; the rewrite maps those back to
   CouchDB's root. The reference route was deployed as config surface to sync waves — see
   `gitops/security/base/api-key-authn.yaml` for how the machine routes stay protected alongside it.

3. **No `SecurityPolicy` on the admin route.** The component's own login (CouchDB admin session) is
   the auth boundary. The route-table audit test
   (`tests/atdd/e2e/test_p0_route_table_audit.py`) skips this route via the
   `COUCHDB_ADMIN_ROUTE` constant — update that constant when mirroring this pattern for another
   component so the audit documents the intentional exception instead of failing.
4. **Cross-namespace backend**: if the backend Service lives in a different namespace than the
   route, add a `ReferenceGrant` (see `allow-hpdc-edge-data-to-couchdb` in the base manifest) and
   reference the backend explicitly with `group: ""`, `kind: Service`, and `namespace:`.
5. **Serve through the rewrite**: give the UI a mount path that can be stripped. If the
   component cannot run under a sub-path, reverse-proxy at the prefix so its relative asset URLs
   resolve correctly.

### Verification

```bash
# page + assets load without any API key
curl -s https://admin.hpdc.local/couchdb/_utils/ -o /dev/null -w "%{http_code}\n"

# relative API base resolves through the rewrite
curl -s https://admin.hpdc.local/couchdb/_up

# full browser flow: login sets AuthSession cookie, then authorized call
COOKIE=$(curl -s -D - -o /dev/null https://admin.hpdc.local/couchdb/_session \
  -X POST -H "Content-Type: application/json" \
  -d '{"name":"admin","password":"password"}' | sed -n 's/^[Ss]et-[Cc]ookie: \([^;]*\).*/\1/p')
curl -s -H "Cookie: $COOKIE" https://admin.hpdc.local/couchdb/_all_dbs -w " [%{http_code}]\n"
```

### Adding a new component admin UI (checklist)

- [ ] HTTPRoute on `admin.hpdc.local` (or the component's own subdomain) with `PathPrefix` match
- [ ] `URLRewrite` stripping the prefix (`ReplacePrefixMatch: /`) so Fauxton-style relative bases work
- [ ] Backend reference with explicit `group`, `kind`, `namespace` (`Service` unless the component only exposes a `Pod`)
- [ ] `ReferenceGrant` in the backend's namespace permitting the edge route
- [ ] No `SecurityPolicy` on the admin route — component's own auth is the boundary
- [ ] Route-table audit tolerance updated in `test_p0_route_table_audit.py`
- [ ] Re-render the dev overlay and sync through Argo CD
- [ ] Host entry added (`<EDGE_IP> admin.hpdc.local` in `/etc/hosts`)
- [ ] Verify page, assets, login, and an authenticated API call per the commands above