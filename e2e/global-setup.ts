/** globalSetup (Playwright) — run once before the suite starts.
 * Resolves the kubectl context against the dev Talos cluster and clears the
 * local discovery cache so fresh-cluster resource-type lookups don't lie. */
import { execSync } from 'child_process';
import type { FullConfig } from '@playwright/test';

export default async function globalSetup(_config: FullConfig): Promise<void> {
  const root = process.env.HPDC_REPO_ROOT || process.cwd();
  const talosconfig = process.env.TALOSCONFIG || `${root}/output/talos/talosconfig`;
  process.env.TALOSCONFIG = talosconfig;
  const talosBin = process.env.TALOS_BIN || `${process.env.HOME}/.local/bin`;
  const PATH_WITH_TALOS = `${talosBin}:${process.env.PATH || ''}`;
  for (const cmd of ['talosctl kubeconfig', 'rm -rf ~/.kube/cache']) {
    try {
      execSync(cmd, { stdio: 'ignore', timeout: 30_000, env: { ...process.env, PATH: PATH_WITH_TALOS } });
    } catch { /* talosctl/cluster already configured or absent in CI — tolerable. */ }
  }
}
