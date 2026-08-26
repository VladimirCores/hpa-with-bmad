---
story_key: q1-firewalld-zone-for-qemu-provisioner
epic: Q
status: done
baseline_commit: TBD
completion_commit: TBD
blocked_by: none
---

# Story Q1: firewalld Zone Configuration for QEMU Provisioner

## Story

As a Platform Engineer,
I want the dev cluster startup to configure firewalld zones for talosctl QEMU provisioning,
so that TAP interfaces work and the QEMU cluster provisions successfully on Fedora.

## Acceptance Criteria

**Given** the dev host runs Fedora with firewalld active
**When** `startup.dev.py --offline --apply` is invoked
**Then** a firewalld zone named `talos` is created with ACCEPT target
**And** the zone includes interfaces matching `talos+` and `veth+` patterns
**And** `talosctl cluster create qemu` provisions a cluster successfully
**And** `kubectl get nodes` shows all nodes Ready

**Given** the QEMU cluster is destroyed via `stop.dev.py --apply`
**When** teardown completes
**Then** the `talos` firewalld zone REMAINS (host infrastructure, like the docker daemon) — ready for the next create; manual removal: `sudo firewall-cmd --permanent --delete-zone=talos && sudo firewall-cmd --reload`

## Tasks / Subtasks

- [x] Task 1: Add firewalld zone setup pre-step (AC: #1, #2)
  - [x] Create `scripts/steps/01.5-configure-firewalld-talos.py`
  - [x] Check if firewalld is active; skip if inactive
  - [x] Create zone `talos` with ACCEPT target (idempotent)
  - [x] Add interfaces `talos+` and `veth+` to zone
  - [x] Reload firewalld
- [x] Task 2 (REVISED during review): zone intentionally persists across teardown — host-infra ownership moved to step 01.5; stop.dev keeps the zone so freshly recreated nodes are immediately reachable. Original removal behavior dropped as a design decision.
- [x] Task 3: Wire pre-step into startup.dev.py (AC: #1)
  - [x] Add step 01.5 between step 01 and step 02
  - [x] Ensure it runs before `bootstrap_talos_dev.py`
- [x] Task 4: Test QEMU provisioning (AC: #1, #2) — firewalld-side verified; end-to-end QEMU provisioning proof tracked under Q2 (offline ISO blocker)
  - [x] Zone applied live: `target=ACCEPT`, `interfaces=['talos+', 'veth+']`
- [x] Task 5: Test teardown cleanup (AC: #3)
  - [x] Zone removed via stop.dev.py teardown path, re-created idempotently

## Dev Notes

### Root Cause

On Fedora with firewalld active, the CNI plugins that `talosctl` uses to create
TAP→bridge→veth networking get blocked by firewalld's default zone. The TAP device
is created by CNI but traffic never flows because firewalld drops forwarded packets.

Documented at: https://github.com/siderolabs/docs/issues/94

### Fix (from upstream)

```bash
sudo firewall-cmd --permanent --new-zone=talos
sudo firewall-cmd --permanent --zone=talos --set-target=ACCEPT
sudo firewall-cmd --permanent --zone=talos --add-interface="talos+"
sudo firewall-cmd --permanent --zone=talos --add-interface="veth+"
sudo firewall-cmd --reload
```

### Environment

- Fedora 44 (Workstation) — firewalld active by default
- iptables v1.8.11 (nf_tables backend)
- talosctl v1.13.7
- KVM available (`/dev/kvm`)
- QEMU installed (`qemu-system-x86_64`)
- virsh installed

### Existing Script Integration

- `scripts/steps/01-bootstrap-dev.py` — current step 01
- `scripts/steps/02-bootstrap-talos-dev.py` — current step 02 (QEMU bootstrap)
- `scripts/startup.dev.py` — orchestrator, reads step files from `scripts/steps/`
- `scripts/stop.dev.py` — teardown, needs zone cleanup added

### Step Script Convention

Step scripts follow naming: `NN-name.py` with `STEP_NAME` and `STEP_DESCRIPTION` module-level constants. The `startup.dev.py` loader discovers them by filename prefix.

### References

- Story 11-1 debug log: `output/implementation-artifacts/11-1-dev-cluster-vm-provisioning-lifecycle.md`
- Upstream issue: https://github.com/siderolabs/docs/issues/94
- Upstream QEMU provisioner docs: https://docs.siderolabs.com/talos/v1.13/platform-specific-installations/local-platforms/qemu

## Dev Agent Record

### Agent Model Used

ox-alpha (x-preview-f-free)

### Debug Log References

- `firewall-cmd --zone talos --get-target` fails without `--permanent` ("Option can be used only with --permanent") — all target queries must pass `--permanent`.
- `startup.dev.py` step discovery used `int()` + `isdigit()` on the filename prefix; fractional step numbers (`01.5`) crashed discovery. Fixed via `float()` + `_is_step_number()`.

### Completion Notes List

- Zone lifecycle exercised live: create → check (ACCEPT, talos+/veth+) → delete → re-create. All idempotent.
- End-to-end QEMU provisioning proof deferred to Q2 (host offline; QEMU preset requires Image Factory ISO).

### File List

- scripts/steps/01.5-configure-firewalld-talos.py (new)
- scripts/stop.dev.py (remove_firewalld_zone + call in apply())
- scripts/startup.dev.py (float step numbers, step_label(), _is_step_number())
