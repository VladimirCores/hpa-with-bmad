#!/usr/bin/env python3
"""Step 01.5: Configure firewalld zone for talosctl QEMU provisioning.

On Fedora with firewalld active, the CNI plugins that talosctl uses to create
TAP→bridge→veth networking get blocked by firewalld's default zone. This step
creates a dedicated 'talos' zone with ACCEPT target and adds the relevant
interfaces so QEMU TAP traffic flows.

Reference: https://github.com/siderolabs/docs/issues/94

Run modes:
  --check   report whether the zone is already configured (no changes)
  --dry-run show what would be done (no changes)
  --apply   create/update the firewalld zone
"""

from __future__ import annotations

import argparse
import subprocess
import sys

STEP_NAME = "01.5-configure-firewalld-talos.py"
STEP_DESCRIPTION = "Configure firewalld zone for talosctl QEMU provisioning."

ZONE_NAME = "talos"
ZONE_INTERFACES = ["talos+", "veth+"]
ZONE_SOURCE = "10.6.0.0/24"


def _run(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=check)


def _has_firewalld() -> bool:
    result = _run(["systemctl", "is-active", "firewalld"])
    return result.returncode == 0 and result.stdout.strip() == "active"


def _zone_exists() -> bool:
    result = _run(["firewall-cmd", "--get-zones"])
    return result.returncode == 0 and ZONE_NAME in result.stdout.split()


def _zone_interfaces() -> list[str]:
    if not _zone_exists():
        return []
    result = _run(["firewall-cmd", "--zone", ZONE_NAME, "--list-interfaces"])
    if result.returncode != 0:
        return []
    return [i for i in result.stdout.strip().split() if i]


def _zone_target() -> str:
    if not _zone_exists():
        return ""
    result = _run(["firewall-cmd", "--permanent", "--zone", ZONE_NAME, "--get-target"])
    return result.stdout.strip() if result.returncode == 0 else ""


def _zone_sources() -> list[str]:
    if not _zone_exists():
        return []
    result = _run(["firewall-cmd", "--permanent", "--zone", ZONE_NAME, "--list-sources"])
    if result.returncode != 0:
        return []
    return [s for s in result.stdout.strip().split() if s]


def check() -> int:
    if not _has_firewalld():
        print("firewalld is not active; skipping.")
        return 0

    if not _zone_exists():
        print(f"Zone '{ZONE_NAME}' does not exist; needs creation.")
        return 1

    target = _zone_target()
    interfaces = _zone_interfaces()
    sources = _zone_sources()
    print(f"Zone '{ZONE_NAME}' exists, target={target}, interfaces={interfaces}, sources={sources}")

    missing_ifaces = [i for i in ZONE_INTERFACES if i not in interfaces]
    missing_source = ZONE_SOURCE not in sources
    if target != "ACCEPT" or missing_ifaces or missing_source:
        print(f"Zone needs update: target={target}, missing interfaces={missing_ifaces}, missing source={missing_source}")
        return 1

    print("firewalld zone is correctly configured.")
    return 0


def dry_run() -> int:
    if not _has_firewalld():
        print("firewalld is not active; nothing to do.")
        return 0

    if not _zone_exists():
        print(f"Would create zone '{ZONE_NAME}' with ACCEPT target.")
        print(f"Would add interfaces: {ZONE_INTERFACES}")
        print(f"Would add source: {ZONE_SOURCE}")
        print("Would reload firewalld.")
        return 0

    target = _zone_target()
    interfaces = _zone_interfaces()
    missing_ifaces = [i for i in ZONE_INTERFACES if i not in interfaces]
    missing_source = ZONE_SOURCE not in _zone_sources()

    pending = bool(target != "ACCEPT" or missing_ifaces or missing_source)
    if target != "ACCEPT":
        print(f"Would set zone '{ZONE_NAME}' target to ACCEPT.")
    if missing_ifaces:
        print(f"Would add interfaces: {missing_ifaces}")
    if missing_source:
        print(f"Would add source: {ZONE_SOURCE}")
    if pending:
        print("Would reload firewalld.")
    else:
        print("Zone already correctly configured; nothing to do.")
    return 0


def apply() -> int:
    if not _has_firewalld():
        print("firewalld is not active; skipping.")
        return 0

    # Create zone if it doesn't exist
    if not _zone_exists():
        print(f"Creating zone '{ZONE_NAME}'...")
        result = _run(["firewall-cmd", "--permanent", "--new-zone=" + ZONE_NAME])
        if result.returncode != 0:
            print(f"Failed to create zone: {result.stderr.strip()}")
            return 1

    # Set target to ACCEPT
    target = _zone_target()
    if target != "ACCEPT":
        print(f"Setting zone '{ZONE_NAME}' target to ACCEPT...")
        result = _run(["firewall-cmd", "--permanent", "--zone", ZONE_NAME, "--set-target=ACCEPT"])
        if result.returncode != 0:
            print(f"Failed to set target: {result.stderr.strip()}")
            return 1

    changed = False

    # Add missing interfaces (best-effort; QEMU tap names vary per run)
    current_ifaces = _zone_interfaces()
    for iface in ZONE_INTERFACES:
        if iface not in current_ifaces:
            print(f"Adding interface '{iface}' to zone '{ZONE_NAME}'...")
            result = _run(["firewall-cmd", "--permanent", "--zone", ZONE_NAME, "--add-interface=" + iface])
            if result.returncode != 0:
                print(f"Warning: could not add interface: {result.stderr.strip()}")
            else:
                changed = True

    # Bind the cluster subnet to this zone (source-based matching is
    # independent of the dynamic bridge/tap interface names QEMU creates).
    if ZONE_SOURCE not in _zone_sources():
        print(f"Adding source {ZONE_SOURCE} to zone '{ZONE_NAME}'...")
        result = _run(["firewall-cmd", "--permanent", "--zone", ZONE_NAME, f"--add-source={ZONE_SOURCE}"])
        if result.returncode != 0:
            print(f"Failed to add source: {result.stderr.strip()}")
            return 1
        changed = True

    if changed:
        print("Reloading firewalld...")
        result = _run(["firewall-cmd", "--reload"])
        if result.returncode != 0:
            print(f"Failed to reload firewalld: {result.stderr.strip()}")
            return 1

    # Verify
    sources = _zone_sources()
    target = _zone_target()
    if target == "ACCEPT" and ZONE_SOURCE in sources:
        print(f"Zone '{ZONE_NAME}' configured successfully: target={target}, sources={sources}")
        return 0
    else:
        print(f"Zone verification failed: target={target}, sources={sources}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=STEP_DESCRIPTION)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report zone state, make no changes")
    mode.add_argument("--dry-run", action="store_true", help="show what would be done, no changes")
    mode.add_argument("--apply", action="store_true", help="create/update the firewalld zone")
    args = parser.parse_args()

    try:
        if args.check:
            return check()
        if args.dry_run:
            return dry_run()
        return apply()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
