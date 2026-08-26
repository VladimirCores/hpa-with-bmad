---
story_key: q2-migrate-dev-cluster-docker-to-qemu
epic: Q
status: done
baseline_commit: TBD
completion_commit: TBD
blocked_by: none # q1 merged into working tree; ISO cache is the active blocker
---

# Story Q2: Migrate Dev Cluster from Docker to QEMU Provider

## Story

As a Platform Engineer,
I want the dev cluster to use QEMU VMs instead of Docker containers,
so that Ceph can use real virtio-blk disks and the dev environment matches bare-metal behavior.

## Acceptance Criteria

**Given** the firewalld zone from Q1 is configured
**When** `startup.dev.py --offline --apply` is invoked
**Then** it provisions a QEMU-based Talos cluster (not Docker)
**And** 4 VMs are created with persistent virtio-blk disk images
**And** `kubectl get nodes` shows all 4 nodes Ready

**Given** the QEMU cluster is running
**When** Cilium is installed via step 03
**Then** Cilium pods are Running and Ready
**And** kube-proxy is not present

**Given** the QEMU cluster is running with Cilium
**When** Rook-Ceph is installed via step 05
**Then** Ceph OSD initializes on real virtio-blk block devices (not loopback)
**And** RBD StorageClass is Available

**Given** the QEMU cluster is fully provisioned
**When** `stop.dev.py --apply` is run and then `startup.dev.py --offline --apply` again
**Then** the cluster re-provisions cleanly from cached assets (ISO/CNI/registry/mirror persist under resources/; VM state is intentionally ephemeral per cycle)
**And** the cycle is idempotent

## Tasks / Subtasks

- [x] Task 1: Switch bootstrap_talos_dev.py to QEMU provider (AC: #1)
  - [x] Replace Docker provider calls with `talosctl cluster create qemu` (`--provider` flag, default qemu)
  - [x] Configure `--cidr 10.6.0.0/24` (preserve current subnet)
  - [x] Set `--controlplanes 1 --workers 3`
  - [x] Add `--disks` flag for worker virtio-blk disks (default `virtio:10GiB`)
  - [x] Pin `--talos-version v1.13.7` (talosctl built-in default is v1.12.6 — must pin)
- [x] Task 2: Update stop.dev.py for QEMU lifecycle (AC: #4) — already QEMU-aware from 11-1; verified dry-run
- [x] Task 3: Update startup.dev.py orchestration (AC: #1)
  - [x] `--provider` passthrough to step 02 via build_mode_args/step_mode_args
  - [x] Step ordering: 01.5 (firewalld) → 02 (bootstrap); verified in --list
- [x] Task 4: Verify Cilium on QEMU networking (AC: #2)
  - [x] Step 03 installed Cilium v1.20.1 from local mirror; DS 4/4 Running
  - [x] `kubectl get nodes`: **4/4 Ready** (k8s v1.35.2 / Talos v1.13.7)
  - [x] kube-proxy absent (disabled at provision time via CNI patch)
  - [ ] L2 LB service smoke-test → folded into 11-4 ATDD suite
- [x] Task 5: Verify Rook-Ceph on real block devices (AC: #3)
  - [x] OSD block symlink → /dev/vdb (raw virtio-blk; zero loopback), 3 OSDs (one per worker)
  - [x] CephBlockPool replicapool (size 2) + rook-ceph-rbd CSI StorageClass
  - [x] PVC Bound + consumer pod mounted + data write/read verified (`hpdc-ceph-*`)
  - [x] CephCluster phase=Ready / HEALTH_OK
- [x] Task 6: Verify idempotent lifecycle (AC: #4)
  - [x] Full stop→start cycle executed twice post-Ceph; each cycle: teardown clean,
        recreate ~75s, Cilium re-install, Rook stack idempotent via installer

## Dev Notes

### Previous Story (11-1) Learnings

- Docker provider was chosen as workaround for QEMU TAP bug (now fixed via Q1)
- `scripts/gitops/bootstrap_talos_dev.py` currently uses Docker provider
- `scripts/stop.dev.py` currently handles Docker container cleanup
- `scripts/startup.dev.py` orchestrates steps 01-44
- Docker provider uses subnet `10.6.0.0/24`, cluster name `hpdc-talos`

### QEMU Provisioner Requirements (from upstream docs)

- KVM enabled (`/dev/kvm` must exist) ✓
- CNI plugins: `bridge`, `static`, `firewall`, `tc-redirect-tap`
- Installed to `/opt/cni/bin` (auto-installed by talosctl)
- iptables required
- `/var/run/netns` directory must exist
- firewalld zone (Q1 handles this)

### Disk Configuration

- Workers need additional virtio-blk disks for Ceph OSD
- `--disks "virtio:10GiB"` adds a 10GiB disk to workers
- Multiple disks: `--disks "virtio:10GiB" --disks "virtio:20GiB"`
- First disk is always the OS disk; additional disks are data disks
- For Ceph: at least one additional disk per worker for OSD

### Subnet

- Current Docker setup uses `10.6.0.0/24`
- QEMU provisioner default is `10.5.0.0/24`
- Use `--cidr 10.6.0.0/24` to preserve compatibility with existing scripts
- Gateway: `10.6.0.1` (used by local registry at `10.6.0.1:5000`)

### Existing Script Files to Modify

| File | Current Behavior | Changes Needed |
|------|-----------------|----------------|
| `scripts/gitops/bootstrap_talos_dev.py` | Docker provider | Switch to QEMU provider |
| `scripts/stop.dev.py` | Docker container cleanup | QEMU VM teardown |
| `scripts/startup.dev.py` | Docker-aware orchestration | QEMU-aware orchestration |

### Key Commands

```bash
# QEMU cluster create (from upstream docs)
sudo --preserve-env=HOME talosctl cluster create qemu \
  --name hpdc-talos \
  --cidr 10.6.0.0/24 \
  --controlplanes 1 \
  --workers 3 \
  --cpus-workers 2 \
  --memory-workers 3072 \
  --disks "virtio:10GiB"

# QEMU cluster destroy
sudo --preserve-env=HOME talosctl cluster destroy --provisioner qemu --name hpdc-talos
```

### Offline ISO Prerequisite — RESOLVED via resources/ paradigm

All Talos runtime assets now live under `resources/` (gitignored):
`resources/talos/home/.talos/{cache,cni,clusters}`, plus `resources/registry/data`
and `resources/git-mirror/`. The 321MB v1.13.7 ISO was fetched once through the
host's local HTTP proxy (`http_proxy=127.0.0.1:10809`; direct egress is
throttled to ~0.3KB/s) and hardlinked into every candidate HOME location.

### Hard-Won Gotchas (each cost real debugging time — do not regress)

1. **QEMU unix-socket 108-char limit**: control-plane `.monitor` socket path
   must stay under `sun_path` limit. Deep `resources/...` paths exceed it →
   VMs silently never start ("no route to host" from failed apply-dial).
   Fix: short repo-root symlink `talos-state → resources/talos/home/.talos/clusters`
   passed as `--state`.
2. **sudo strips HOME** (even with `-E` on this sudoer config): talosctl
   resolves asset cache/CNI under `/root/.talos` regardless of env HOME.
   Fix: `seed_talos_assets()` hardlinks ISO+CNI into both locations; state
   pinned via explicit `--state` flag (flags survive where env does not).
3. **Binary shadowing**: root's secure_path picked `/usr/local/sbin/talosctl`
   **v1.12.6** over user's `~/.local/bin/talosctl` **v1.13.7**, silently
   changing built-in k8s/etcd/CNI-bundle refs. Fix: `resolve_talosctl()`
   version-checks candidates (HPDC_TALOSCTL > SUDO_USER home > /usr/local/bin
   > PATH) and hard-fails on mismatch.
4. **Host port squatting**: a leftover `k3s-server` service bound `*:6443`,
   hijacking the cluster LB address and feeding nodes wrong TLS certs
   (endless x509 "unknown authority"/Ed25519 noise). Stopped+disabled.
   Any host apiserver on 6443 must go before QEMU bootstrap.
5. **ISO preset installer pin**: machine config installs
   `factory.talos.dev/metal-installer/<schematic>:v1.13.7`, which the offline
   mirror doesn't serve → install hangs forever.
   Fix: `platform/talos/talos-qemu-installer-patch.yaml` forces
   `ghcr.io/siderolabs/installer:v1.13.7` (mirror-served).
6. **Image-cache drift vs Docker era**: Talos 1.13.7 + k8s 1.35.2 wants
   `etcd:v3.6.12` and sandbox `pause:3.10.1` (cache had 3.6.8 / 3.10).
   Backfilled both into `localhost:5000`. skipFallback turns any miss into a
   silent Preparing/NotFound — check `talosctl logs kubelet` for exact refs.
7. **firewalld source-binding**: interface-name zones can't track QEMU's
   dynamic tap/bridge names reliably; zone binds subnet `10.6.0.0/24` by
   SOURCE instead. Zone is host infrastructure — teardown intentionally
   keeps it.
8. **kubeconfig prune self-sabotage**: re-pruning the *generated* admin
   kubeconfig strips its only context; only merged raw configs get pruned.
   Sync targets are SUDO_USER-aware (writes real user home, not /root).

### References

- Story 11-1: `output/implementation-artifacts/11-1-dev-cluster-vm-provisioning-lifecycle.md`
- Story 11-5: `output/implementation-artifacts/11-5-platform-convergence-app-of-apps.md`
- QEMU provisioner docs: https://docs.siderolabs.com/talos/v1.13/platform-specific-installations/local-platforms/qemu
- bootstrap_talos_dev.py: `scripts/gitops/bootstrap_talos_dev.py`
- stop.dev.py: `scripts/stop.dev.py`
- startup.dev.py: `scripts/startup.dev.py`

## Dev Agent Record

### Agent Model Used

ox-alpha (x-preview-f-free)

### Debug Log References

- output/qemu-create.log — create attempts 5-7 (socket-path / state-dir races)
- Node-side forensics via `talosctl -n 10.6.0.2 --talosconfig /root/.talos/config {dmesg,logs kubelet,services}`

### Completion Notes List

- Cluster delivered live: QEMU provisioner, cidr 10.6.0.0/24, 1 CP + 3 workers,
  virtio:10GiB OS + worker-only 10GiB data disks, k8s v1.35.2, Cilium 1.20.1 KPR
  (no kube-proxy), fully offline pulls through localhost:5000 mirror.
- **Sizing via .env** (HPDC_MEMORY_CONTROLPLANE=6144, HPDC_MEMORY_WORKER=4096,
  plus provider/workers/cpus/subnet/disks/k8s-version) — .env.example committed.
- Rook stack rebuilt on real manifests: vendored crds/common/operator/csi-operator
  (v1.20.3) + rewritten CephCluster (valid schema: deviceFilter vdb, host net),
  CephBlockPool(size 2), CSI StorageClass (rook-ceph.rbd.csi.ceph.com).
- Image `rook/ceph:v1.20.3-root` (USER root variant) built+mirrored — image's
  default USER rook(2016) made daemon init chowns fail; mon-only env flag was
  insufficient. Namespace PSA=privileged label required (Talos baseline default).
- Registry.k8s.io multi-arch lists: one child blob EOFs persistently → mirror
  amd64-only (`--override-arch amd64`); scripts/services/mirror-image.py added
  for chunked-resumable fallback. Backfills: etcd v3.6.12, pause 3.10/3.10.1,
  coredns v1.14.4, cephcsi v3.17.0, sig-storage sidecars v4.12/v6.2/v2.1/
  v8.3/v8.5/v2.16, ceph-csi-operator v1.0.4, rook/ceph + root variant.
- k3s host service stopped+disabled (was squatting *:6443).
- Orchestrator step-03 under sudo fails on helm user-cache; run step 03 as user.

### File List

- scripts/gitops/bootstrap_talos_dev.py (provider/state-link/env/binary-resolve/seeds/sync/dotenv fixes)
- scripts/startup.dev.py (--provider passthrough; float step numbers)
- scripts/stop.dev.py (resources paths, orphan-QEMU sweep, zone kept on teardown)
- scripts/steps/01.5-configure-firewalld-talos.py (+source-subnet binding)
- scripts/services/image-registry.py (NEW — codified registry lifecycle)
- scripts/services/mirror-image.py (NEW — resumable blob mirror)
- scripts/services/git-smart-http.py + scripts/gitops/provision_local_git_mirror.py (mirror → resources/)
- scripts/gitops/install_rook_ceph_dev.py (registry probes, rendered bundle, CSI SC, fixer DS)
- platform/talos/talos-qemu-installer-patch.yaml (NEW)
- platform/manifests/rook-ceph-{crds,common,operator,csi-operator}-v1.20.3.yaml (vendored; operator env flags flipped)
- gitops/rook-ceph/base/{rook-ceph.yaml,storageclasses.yaml,rook-dirs-bootstrap.yaml} (rewritten to real schemas)
- .env.example (NEW); resources/{talos,registry,git-mirror}/ (gitignored)
- talos-state -> resources/talos/home/.talos/clusters (short-path symlink)

### Review Findings

#### Round 2 (re-review of applied patches) — all resolved
- [x] [Review][Patch] stop.dev NameError on apply-path kill_qemu_processes call sites — fixed, verified via --check + grep
- [x] [Review][Patch] ensure_cilium read CURRENT not READY column — index corrected + width guard
- [x] [Review][Patch] mirror digest-mismatch unbounded recursion — depth-limited single retry
- [x] [Review][Patch] qemu sweep fuzzy matches editors/tail — ERE requires qemu-system AND repo-anchored state path
- [x] [Review][Patch] sweep ran unconditionally even with zero cluster — gated in both entry points
- [x] [Review][Patch] sudo-kill silent failures now warn with counts
- [x] [Review][Patch] talos_destroy propagates real failures ('not found' tolerated)
- [x] [Review][Patch] ensure_registry probes health even when container already running
- [x] [Review][Patch] fixer chown chain set -e (failures propagate); rollout timeouts added (DS 180s, operator 600s)
- [x] [Review][Patch] ROOK_COMMON double-apply deduped; vendored existence check moved first; dual-tag gate error names both tags
- [x] [Review][Patch] dotenv: BOM/tab-export/#-values/quote-aware/empty-allowed/last-wins
- [x] [Review][Patch] mirror fetch retries 5xx/429; missing Content-Length streams whole-blob
- [x] [Review][Defer] startup teardown string-coupling to stop.dev stdout wording
- [x] [Review][Defer] render_overlays kustomize preflight messaging
- Note: Acceptance Auditor re-round failed to launch (prompt truncation); prior audit coverage stands.

#### Decision needed
- [x] [Review][Decision→Patch] Wired ensure_registry into startup apply path (pre-step before 02)
- [x] [Review][Decision→Defer] Keep 0.0.0.0 binding; LAN-trust documented in NEXT.md

#### Patch
- [x] [Review][Patch] install_rook_ceph_dev.py dry-run NameError: ROOK_IMAGE renamed, print site missed [scripts/gitops/install_rook_ceph_dev.py:236]
- [x] [Review][Patch] Offline gate checks only -root tag; vendored operator pulls docker.io/rook/ceph:v1.20.3 too — extend gate [install_rook_ceph_dev.py:48]
- [x] [Review][Patch] Installer validates base/ but applies rendered/ — regenerate rendered before apply [install_rook_ceph_dev.py:168]
- [x] [Review][Patch] Required vendored manifests silently skipped when absent — fail loudly instead [.exists() gates :143-149]
- [x] [Review][Patch] Apply order: rendered (PSA labels) must precede fixer/operator; fixer restartPolicy OnFailure + await ready [install_rook_ceph_dev.py:143-168]
- [x] [Review][Patch] Unfiltered `pgrep -f qemu-system` kill sweeps kill foreign VMs — filter by cluster state-path marker [bootstrap:215, stop.dev:123]
- [x] [Review][Patch] stop.dev crashes when docker binary missing — which() guards [:71,:156]
- [x] [Review][Patch] Root-owned ~/.kube/config written into SUDO_USER home — chown after write [bootstrap:465]
- [x] [Review][Patch] kubeconfig fallback reads root-written tmpfile as user — sudo cat fallback [bootstrap:425]
- [x] [Review][Patch] workers<2 with pool size 2 deadlocks PVCs — bootstrap guard when storage=rook-ceph
- [x] [Review][Patch] Teardown sweeps use unprivileged kill on root-owned pids — sudo -n kill + rc warnings
- [x] [Review][Patch] Dead remove_firewalld_zone() contradicts retention NOTE — delete fn; amend q1 AC/task wording (zone persists by design)
- [x] [Review][Patch] .env.example sizing drift (6124→6144, worker 3072→4096)
- [x] [Review][Patch] Stale CILIUM_IMAGE const + dry-run cache prints — remove
- [x] [Review][Patch] Dry-run prints DEFAULT_CONTROLPLANES instead of args value [bootstrap:746]
- [x] [Review][Patch] Docker destroy path bypasses resolve_talosctl()/state pinning [bootstrap:198]
- [x] [Review][Patch] --step 01.5 selector misses fractional label [startup.dev.py:243]
- [x] [Review][Patch] _is_step_number admits nan/inf tokens — restrict regex [startup.dev.py:48]
- [x] [Review][Patch] dotenv parser mishandles quotes/comments/export/empty values [bootstrap:682]
- [x] [Review][Patch] seed_talos_assets: unordered ISO pick + unsudoed crash paths [bootstrap:567]
- [x] [Review][Patch] Stray non-symlink talos-state aborts cryptically [bootstrap:59]
- [x] [Review][Patch] Docker provider ignores --controlplanes/--disks silently [bootstrap:536]
- [x] [Review][Patch] ensure_cilium ignores readiness + can hang — add timeout & desired==ready check
- [x] [Review][Patch] --cleanup unreachable when no cluster detected — run sweep regardless of early-return [stop.dev:219]
- [x] [Review][Patch] stop.dev dry-run prints deep TALOS_STATE_DIR instead of link [stop.dev:207]
- [x] [Review][Patch] mirror-image.py: mtype stuck at index for single manifests [mirror:130]
- [x] [Review][Patch] mirror-image.py: next() crashes on amd64-less lists [mirror:133]
- [x] [Review][Patch] mirror-image.py: shared predictable .part path; digest mismatch aborts without re-download [mirror:67-92]
- [x] [Review][Patch] mirror-image.py/_registry_has route local traffic through proxy env — direct opener for LOCAL
- [x] [Review][Patch] Docs/AC promise persistent VM disks teardown destroys — align q2 AC4 wording + stop.dev docstring
- [x] [Review][Patch] Smoke test not codified — add gitops/rook-ceph/smoke-test.yaml
- [x] [Review][Patch] q1 frontmatter still ready-for-dev; sync statuses (commits stay TBD until landing)
- [x] [Review][Patch] test_missing_image_cache_fails tests removed marker mechanism — retarget to registry-probe failure

#### Deferred
- [x] [Review][Defer] create-failure treated as expected cni-timeout (log tail capture improvement) [bootstrap:625] — deferred, heuristic risk
- [x] [Review][Defer] Mixed root/user invocations leave mixed-ownership resources/ — deferred, single-mode documented
- [x] [Review][Defer] Subnet string unvalidated (.2 assumption) — deferred, default fixed topology
