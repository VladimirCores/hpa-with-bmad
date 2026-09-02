import { defineConfig } from '@playwright/test';

/* E2E suite for every component publicly exposed through the Envoy Gateway.
 * Nothing is hard-coded: the EG address, every route hostname/path/backend
 * and the api-key secret values are resolved live from the cluster via
 * `kubectl`. Each component test is per-component env-gated (skip when its
 * backend has no ready Endpoints) — a partial platform deploy yields skips,
 * never false failures. The whole file is skipped when Envoy Gateway is not
 * deployed at all (see the in-spec `test.skip(!EG_DEPLOYED, ...)`). */
export default defineConfig({
  testDir: 'tests',
  timeout: 40_000,
  expect: { timeout: 8_000 },
  retries: 0,
  reporter: [['list'], ['html']],
  // global-setup.ts refreshes the Talos kubeconfig so `kubectl` below points at
  // the dev cluster, and wipes ~/.kube/cache (avoids stale-discovery false hits
  // like "no resource type 'gateway'" on a freshly provisioned Talos control plane).
  globalSetup: './global-setup',
  use: {
    // EG terminates with a wildcard *.hpdc.local cert; tolerate SNI/IP mismatch.
    ignoreHTTPSErrors: true,
    baseURL: undefined,
    trace: 'on-first-retry',
    // The suite uses Playwright's `request` API (no browser). The browser
    // fixture is not exercised, so no Chromium binary is required.
  },
});
