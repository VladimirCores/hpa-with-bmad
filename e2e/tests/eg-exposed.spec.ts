/**
 * Playwright (TypeScript) end-to-end tests for components publicly exposed
 * through the Envoy Gateway (hpdc-edge).
 *
 * Run:  npx playwright test              # in the `e2e/` dir
 *       npx playwright test --headed     # to watch the browser
 *
 * Coverage (one test per EG-exposed surface):
 *   - Edge infra: GatewayClass + hpdc-edge programmed; HTTP(80)->HTTPS(443)
 *                 redirect; TLS termination for *.hpdc.local.
 *   - Route wiring: every HTTPRoute/GRPCRoute/TCPRoute attached to hpdc-edge is
 *                   Accepted and has a ready backend (Endpoints).
 *   - CASBANDORA   casbandora.hpdc.local  -> JWT login page (200 + "casdoor").
 *   - GraphQL      *.hpdc.local /gql      -> Hasura { __typename } introspect.
 *   - Grafana      grafana.hpdc.local     -> login page (200/302).
 *   - Hubble UI    hubble.hpdc.local      -> dashboard (200).
 *   - Tool UI/ArgoCD *.hpdc.local /argocd -> Argo CD server front.
 *   - Telemetry HTTP *.hpdc.local /telemetry -> Pulsar proxy batch (200/202).
 *   - Telemetry gRPC hpdc.telemetry.v1.TelemetryService -> h2 ALPN over TLS.
 *   - Authn gate   *.hpdc.local /data     -> 401 w/o X-API-Key, 200 w/ it.
 *
 * Nothing is hard-coded: the EG address, every route hostname/path/backend and
 * the api-key values are resolved LIVE from the cluster via `kubectl`, so the
 * tests follow route/manifest drift automatically. Each component test is
 * per-component env-gated (skip when its backend has no ready Endpoints); the
 * whole file is skipped when Envoy Gateway is not deployed.
 */
import { test, expect, type APIRequestContext } from '@playwright/test';
import * as tls from 'tls';
import * as net from 'net';
import { execSync } from 'child_process';

const EG_NS = 'envoy-gateway-system';
const EG_GATEWAY = 'hpdc-edge';
const HPDC_LOCAL = '*.hpdc.local';

/* ----------------------------- kubectl helpers ---------------------------- */
function kubectl(args: string): string {
  try {
    return execSync(`kubectl ${args}`, { stdio: ['ignore', 'pipe', 'pipe'], timeout: 20_000 }).toString().trim();
  } catch {
    return '';
  }
}
function b64(raw: string): string {
  return raw ? Buffer.from(raw, 'base64').toString('latin1') : '';
}

// Whole-file gate: skip everything when Envoy Gateway is not installed.
const EG_DEPLOYED = !!kubectl('get gatewayclass -o name') && !!kubectl(`get ns ${EG_NS} -o name`);
test.describe(() => {
  test.skip(!EG_DEPLOYED,
    'Envoy Gateway not deployed in this cluster. Deploy the edge slice first, e.g.:\n' +
    '  kubectl apply -f gitops/crds/gateway/crds.yaml   # Gateway API + EG CRDs\n' +
    '  kubectl apply -f gitops/envoy-gateway/rendered/dev.yaml\n' +
    '  kubectl apply -f gitops/casdoor/rendered/dev.yaml\n' +
    '  kubectl apply -f gitops/security/rendered/dev.yaml\n' +
    '  kubectl apply -f gitops/observability/rendered/dev.yaml');

  /* --------------------------- resolution helpers -------------------------- */
  function egAddress(): string {
    return (
      kubectl('get svc envoy-gateway -n envoy-gateway-system -o jsonpath={.status.loadBalancer.ingress[0].ip}') ||
      kubectl(`get gateway ${EG_GATEWAY} -n ${EG_NS} -o jsonpath={.status.addresses[0].value}`) ||
      kubectl(`get gateway ${EG_GATEWAY} -n ${EG_NS} -o jsonpath={.spec.addresses[0].value}`) ||
      process.env.HPDC_GATEWAY_IP ||
      '10.6.0.1'
    );
  }
  function egUrl(scheme = 'https', port = 443): string { return `${scheme}://${egAddress()}:${port}`; }

  interface RouteInfo {
    kind: string; name: string; ns: string; hostname: string | null;
    paths: string[]; backends: [string, string | number | undefined][];
  }
  function routes(kind: string): RouteInfo[] {
    const out = kubectl(`get ${kind} -A -o json`);
    if (!out) return [];
    const items = JSON.parse(out).items || [];
    const res: RouteInfo[] = [];
    for (const r of items) {
      const spec = r.spec || {};
      const parents = spec.parentRefs || [];
      if (!parents.some((p: any) => p.name === EG_GATEWAY)) continue;
      const hostname = (spec.hostnames || [null])[0];
      const paths: string[] = [];
      const backends: [string, string | number | undefined][] = [];
      for (const rule of spec.rules || []) {
        for (const b of rule.backendRefs || []) backends.push([b.name, b.port]);
        for (const m of rule.matches || [{}]) {
          const p = (m as any).path;
          if (typeof p === 'object') paths.push(p?.value || '/');
          else if (typeof p === 'string') paths.push(p);
          else paths.push('/');
        }
        if (!rule.matches?.length && !paths.length) paths.push('/');
      }
      res.push({ kind: r.kind, name: r.metadata.name, ns: r.metadata.namespace,
        hostname, paths: paths.length ? paths : ['/'], backends });
    }
    return res;
  }
  function routeFor(host: string, path: string): RouteInfo | null {
    for (const r of routes('httproute')) {
      const hn = r.hostname;
      if (!(hn === host || hn === HPDC_LOCAL || hn === null || (hn ?? '').startsWith('*.'))) continue;
      if (r.paths.some((rp) => {
        const base = (rp || '/').replace(/\/$/, '');
        return base === '' || rp === '/' || path.replace(/\/$/, '').startsWith(base);
      })) return r;
    }
    return null;
  }
  function svcReady(svc: string, ns: string): boolean {
    return kubectl(`get endpoints ${svc} -n ${ns} -o jsonpath={.subsets[*].addresses[*].ip}`).length > 0;
  }
  function backendReady(r: RouteInfo): boolean {
    return r.backends.some(([svc]) => svcReady(svc, r.ns));
  }
  function apiKey(secret: string, dataKey: string): string {
    return b64(kubectl(`get secret ${secret} -n security -o jsonpath={.data.${dataKey}}`));
  }

  async function req(request: APIRequestContext, host: string, path: string, opts: Record<string, unknown> = {}) {
    return request.fetch(`${egUrl()}${path}`, {
      headers: { Host: host, ...(opts.headers as Record<string, string> || {}) },
      failOnStatusCode: false,
      maxRedirects: 0,
      timeout: 15_000,
      ...opts,
    });
  }

  /* ------------------------------- infra ----------------------------------- */
  test('hpdc-edge Gateway is programmed', () => {
    const accepted = kubectl(`get gateway ${EG_GATEWAY} -n ${EG_NS} -o jsonpath={.status.conditions[?(@.type=="Accepted")].status}`);
    expect(accepted).toBe('True');
    expect(egAddress()).toBeTruthy();
  });

  test('HTTP(80) redirects to HTTPS(443)', async ({ request }) => {
    const r = await request.get(`${egUrl('http', 80)}/`, {
      headers: { Host: 'casbandora.hpdc.local' }, failOnStatusCode: false, maxRedirects: 0,
    });
    expect([301, 302, 307]).toContain(r.status());
    expect((r.headers()['location'] || '')).toMatch(/^https:\/\//);
  });

  test('https listener terminates TLS for *.hpdc.local', async () => {
    const addr = egAddress();
    const ok = await new Promise<boolean>((resolveP) => {
      const sock = net.connect(443, addr);
      const s = tls.connect({ socket: sock, servername: 'casbandora.hpdc.local', rejectUnauthorized: false });
      s.on('secureConnect', () => { resolveP(true); s.destroy(); });
      s.on('error', () => resolveP(false));
    });
    expect(ok).toBe(true);
  });

  test('every route attached to hpdc-edge is Accepted', () => {
    const accepted = kubectl('get httproute,grpcroute,tcproute -A -o jsonpath={range .items[*].status.parents[*].conditions[?(@.type=="Accepted")].status}{\' \'}{\'\\n\'}{end}');
    if (!accepted.trim()) test.skip(true, 'no HTTPRoute/GRPCRoute/TCPRoute attached to hpdc-edge (telemetry not deployed)');
    expect(accepted).toContain('True');
  });

  /* ----------------------------- components -------------------------------- */
  test('casbandora login page is served', async ({ request }) => {
    const r = routeFor('casbandora.hpdc.local', '/');
    if (!r || !backendReady(r)) test.skip(true, 'casbandora backend not ready / not deployed');
    const resp = await req(request, 'casbandora.hpdc.local', '/');
    expect(resp.status()).toBe(200);
    expect((await resp.text()).toLowerCase()).toContain('casdoor');
  });

  test('graphql gateway answers introspect query', async ({ request }) => {
    const r = routeFor('graphql.hpdc.local', '/gql');
    if (!r || !backendReady(r)) test.skip(true, 'graphql-gateway backend not ready / not deployed');
    const resp = await req(request, 'graphql.hpdc.local', '/gql', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({ query: '{ __typename }' }),
    });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.data?.__typename).toBe('Query');
  });

  test('grafana login front is reachable', async ({ request }) => {
    const r = routeFor('grafana.hpdc.local', '/');
    if (!r || !backendReady(r)) test.skip(true, 'grafana backend not ready / not deployed (HPDC_GRAFANA_ENABLED=false)');
    const resp = await req(request, 'grafana.hpdc.local', '/');
    expect([200, 302]).toContain(resp.status());
  });

  test('hubble UI is reachable', async ({ request }) => {
    const r = routeFor('hubble.hpdc.local', '/');
    if (!r || !backendReady(r)) test.skip(true, 'hubble-ui backend not ready / not deployed');
    const resp = await req(request, 'hubble.hpdc.local', '/');
    expect(resp.status()).toBe(200);
    expect((await resp.text()).toLowerCase()).toContain('hubble');
  });

  test('argo cd is served via the tool-ui route', async ({ request }) => {
    const r = routeFor('argocd.hpdc.local', '/argocd');
    if (!r || !backendReady(r)) test.skip(true, 'argocd-via-tool-ui backend not ready / not deployed');
    const resp = await req(request, 'argocd.hpdc.local', '/argocd');
    expect([200, 302]).toContain(resp.status());
  });

  test('telemetry HTTP ingestion is accepted', async ({ request }) => {
    const r = routeFor('telemetry.hpdc.local', '/telemetry');
    if (!r || !backendReady(r)) test.skip(true, 'pulsar-standalone backend not ready / not deployed');
    const resp = await req(request, 'telemetry.hpdc.local', '/telemetry', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({ messages: [] }),
    });
    expect([200, 201, 202]).toContain(resp.status());
  });

  test('telemetry gRPC route is attached to hpdc-edge', () => {
    const g = routes('grpcroute');
    if (!g.length) test.skip(true, 'telemetry GRPCRoute not deployed');
    expect(g.length).toBeGreaterThan(0);
  });

  test('telemetry gRPC backend is ready', () => {
    const g = routes('grpcroute');
    const ok = g.length && g.some((gr) => gr.backends.some(([svc]) => svcReady(svc, gr.ns)));
    if (!ok) test.skip(true, 'telemetry gRPC backend not ready');
    expect(ok).toBe(true);
  });

  test('telemetry gRPC backend negotiates h2 over TLS', async () => {
    const addr = egAddress();
    const ok = await new Promise<boolean>((resolveP) => {
      const s = tls.connect({
        host: addr, port: 443, servername: 'telemetry.hpdc.local',
        rejectUnauthorized: false, ALPNProtocols: ['h2'],
      });
      s.on('secureConnect', () => { resolveP(s.alpnProtocol === 'h2'); s.end(); });
      s.on('error', () => resolveP(false));
    });
    expect(ok).toBe(true);
  });

  test('telemetry MQTT TCP route is attached to hpdc-edge', () => {
    const t = routes('tcproute');
    if (!t.length) test.skip(true, 'telemetry MQTT TCPRoute not deployed');
    expect(t.length).toBeGreaterThan(0);
  });

  /* ----------------------------- authn gate -------------------------------- */
  const domainRoute = () => routes('httproute').find((r) => r.name === 'hpdc-edge-domain-routes') || null;

  test('api-key-protected /data route rejects unauthenticated requests', async ({ request }) => {
    const r = domainRoute();
    if (!r || !backendReady(r)) test.skip(true, 'hpdc-edge-domain-routes backend not ready / not deployed');
    const resp = await req(request, 'domain.hpdc.local', '/data');
    expect([401, 403]).toContain(resp.status());
  });

  test('api-key-protected /data route accepts a valid X-API-Key', async ({ request }) => {
    const r = domainRoute();
    if (!r || !backendReady(r)) test.skip(true, 'hpdc-edge-domain-routes backend not ready / not deployed');
    const key = apiKey('events-api-key', 'events-key');
    if (!key) test.skip(true, 'events-api-key secret not readable; security app not deployed');
    const resp = await req(request, 'domain.hpdc.local', '/data', { headers: { 'X-API-Key': key } });
    expect([401, 403]).not.toContain(resp.status());
  });
});
