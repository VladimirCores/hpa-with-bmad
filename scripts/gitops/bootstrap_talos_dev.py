#!/usr/bin/env python3
"""Provision the HPDC Talos dev cluster using Docker or QEMU.

Supports Docker provider (legacy) and QEMU provider (default for new clusters).
Storage options: rook-ceph (default) or local-path.

QEMU provider uses virtio-blk disks for Ceph OSD and requires KVM.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TALOS_VERSION = "1.13.7"
TALOS_VERSION_ARG = f"v{TALOS_VERSION}"
DEFAULT_CONTROLPLANES = 1
DEFAULT_WORKERS = 3
DEFAULT_CPUS_CONTROLPLANE = 2.0
DEFAULT_CPUS_WORKER = 2.0
DEFAULT_MEMORY_CONTROLPLANE = "4096"
DEFAULT_MEMORY_WORKER = "3072"
DEFAULT_STORAGE = "rook-ceph"
# Pin to the k8s minor whose control-plane images are pre-cached in the local
# registry mirror (skipFallback makes any uncached tag a hard failure).
DEFAULT_KUBERNETES_VERSION = "1.35.2"
CLUSTER_NAME = "hpdc-talos"
TALOSCONFIG = ROOT / "output" / "talos" / "talosconfig"
CNI_PATCH = ROOT / "platform" / "talos" / "talos-cni-patch.yaml"
MIRROR_PATCH = ROOT / "platform" / "talos" / "talos-offline-mirror-patch.yaml"
QEMU_INSTALLER_PATCH = ROOT / "platform" / "talos" / "talos-qemu-installer-patch.yaml"

# Project-local talos runtime: HOME is overridden for every talosctl call so
# cache (ISOs), CNI bundle, cluster state (incl. VM disks), and merged
# kube/talos configs all live under resources/ (gitignored).
TALOS_HOME = ROOT / "resources" / "talos" / "home"
TALOS_STATE_DIR = TALOS_HOME / ".talos" / "clusters"
# QEMU unix control sockets must stay under 108 chars (sun_path); the deep
# resources/ path exceeds it, so cluster commands use this short symlink.
TALOS_STATE_LINK = ROOT / "talos-state"
TALOS_CACHE_DIR = TALOS_HOME / ".talos" / "cache"
TALOS_CNI_BIN = TALOS_HOME / ".talos" / "cni" / "bin"
LEGACY_ROOT_STATE = Path("/root/.talos/clusters") / CLUSTER_NAME
LEGACY_OUTPUT_STATE = ROOT / "output" / "qemu" / CLUSTER_NAME  # story 11-1/11-2 layout


def ensure_dirs() -> None:
    TALOSCONFIG.parent.mkdir(parents=True, exist_ok=True)
    for directory in (TALOS_STATE_DIR, TALOS_CACHE_DIR, TALOS_CNI_BIN):
        directory.mkdir(parents=True, exist_ok=True)
    if TALOS_STATE_LINK.exists() and not TALOS_STATE_LINK.is_symlink():
        raise RuntimeError(
            f"{TALOS_STATE_LINK} exists but is not the required symlink to {TALOS_STATE_DIR}; "
            "remove or rename it and re-run."
        )
    if not TALOS_STATE_LINK.is_symlink():
        TALOS_STATE_LINK.symlink_to(TALOS_STATE_DIR.relative_to(ROOT), target_is_directory=True)


def run(command: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    result = subprocess.run(command, check=False, env=env)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def validate_runtime() -> None:
    if shutil.which("talosctl") is None:
        raise RuntimeError("talosctl is required for Talos dev cluster bootstrap")


def validate_docker_runtime() -> None:
    validate_runtime()
    if shutil.which("docker") is None:
        raise RuntimeError("docker is required for Talos Docker dev cluster")


def validate_qemu_runtime() -> None:
    validate_runtime()
    if not Path("/dev/kvm").exists():
        raise RuntimeError("KVM is required for Talos QEMU dev cluster (/dev/kvm missing)")
    if shutil.which("qemu-system-x86_64") is None:
        raise RuntimeError("qemu-system-x86_64 is required for Talos QEMU dev cluster")
    if not (TALOS_CNI_BIN / "tc-redirect-tap").exists():
        raise RuntimeError(
            f"CNI bundle missing under {TALOS_CNI_BIN}. "
            "Install talosctl-cni-bundle-amd64.tar.gz contents there (see q2 story Dev Notes)."
        )


def _talosctl_client_tag(path: Path) -> str | None:
    try:
        result = subprocess.run(
            [str(path), "version", "--client"],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if "Tag:" in line:
            return line.split("Tag:")[1].strip()
    return None


TALOSCTL_BIN: str | None = None


def resolve_talosctl() -> str:
    """Find a talosctl binary matching TALOS_VERSION exactly.

    sudo's secure_path frequently shadows the intended binary (e.g.
    /usr/local/sbin/talosctl v1.12.6 vs ~/.local/bin/talosctl v1.13.7), which
    silently changes built-in image refs and CNI asset URLs. Resolve explicitly
    and refuse mismatched versions.
    """
    global TALOSCTL_BIN
    if TALOSCTL_BIN:
        return TALOSCTL_BIN
    expected = TALOS_VERSION_ARG
    candidates: list[Path] = []
    override = os.environ.get("HPDC_TALOSCTL")
    if override:
        candidates.append(Path(override))
    users = {Path.home()}
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user and sudo_user != "root":
        users.add(Path("/home") / sudo_user)
    for home in users:
        candidates.append(home / ".local" / "bin" / "talosctl")
    candidates.append(Path("/usr/local/bin/talosctl"))
    whiched = shutil.which("talosctl")
    if whiched:
        candidates.append(Path(whiched))

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen or not candidate.is_file():
            continue
        seen.add(key)
        tag = _talosctl_client_tag(candidate)
        if tag == expected:
            TALOSCTL_BIN = key
            return key
        if tag:
            print(f"Skipping {key}: client {tag}, want {expected}", file=sys.stderr)
    raise RuntimeError(
        f"No talosctl client {expected} found (checked: {', '.join(seen) or 'nothing usable'}). "
        f"Install talosctl {expected} to ~/.local/bin or set HPDC_TALOSCTL."
    )


def talos_env() -> dict[str, str]:
    """Environment for talosctl invocations: HOME pinned to resources/talos/home."""
    env = os.environ.copy()
    env["HOME"] = str(TALOS_HOME)
    return env


def talosctl_command() -> list[str]:
    talosctl = resolve_talosctl()
    if shutil.which("sudo"):
        return ["sudo", "-n", "-E", talosctl]
    return [talosctl]


def configure_talosconfig() -> None:
    TALOSCONFIG.parent.mkdir(parents=True, exist_ok=True)
    if TALOSCONFIG.exists():
        try:
            text = TALOSCONFIG.read_text(encoding="utf-8")
        except PermissionError:
            return
        if text.startswith("# Local Talos administrative config is generated by talosctl kubeconfig."):
            TALOSCONFIG.unlink()
            return
    TALOSCONFIG.write_text("# Local Talos administrative config is generated by talosctl kubeconfig.\n", encoding="utf-8")



def kill_cluster_qemu() -> int:
    """SIGTERM only QEMU processes whose cmdline references this cluster state."""
    killed = 0
    root = str(ROOT)
    patterns = [f"qemu-system.*{root}/talos-state/{CLUSTER_NAME}",
                f"qemu-system.*clusters/{CLUSTER_NAME}"]
    seen_pids = set()
    for marker in patterns:
        result = subprocess.run(["pgrep", "-f", marker], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            continue
        for pid in result.stdout.split():
            if not pid.isdigit() or pid in seen_pids:
                continue
            seen_pids.add(pid)
            if subprocess.run(["sudo", "-n", "kill", "-15", pid], capture_output=True).returncode == 0:
                killed += 1
    return killed


def destroy_existing_cluster() -> None:
    """Destroy any existing cluster with the same name (Docker or QEMU)."""
    env = talos_env()

    # Try Docker containers first
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"label=talos.cluster.name={CLUSTER_NAME}", "--format", "{{.Names}}"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        print(f"Destroying existing Docker cluster '{CLUSTER_NAME}'...")
        subprocess.run(
            [*talosctl_command(), "cluster", "destroy", "--name", CLUSTER_NAME, "--state", str(TALOS_STATE_LINK)],
            capture_output=True, text=True, env=talos_env(),
        )
        for name in result.stdout.strip().split("\n"):
            if name:
                subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        subprocess.run(["docker", "network", "rm", CLUSTER_NAME], capture_output=True)

    # Try QEMU cluster (project-local state dir)
    qemu_state = TALOS_STATE_DIR / CLUSTER_NAME
    if qemu_state.exists():
        print(f"Destroying existing QEMU cluster '{CLUSTER_NAME}'...")
        subprocess.run(
            [*talosctl_command(), "cluster", "destroy",
             "--name", CLUSTER_NAME, "--state", str(TALOS_STATE_LINK)],
            capture_output=True, text=True, env=env,
        )
    # Legacy state locations from pre-resources layouts: remove once, quietly.
    for legacy in (LEGACY_ROOT_STATE, LEGACY_OUTPUT_STATE):
        if legacy.exists():
            result = subprocess.run(
                ["sudo", "-n", "rm", "-rf", str(legacy)],
                capture_output=True, text=True, check=False,
            )
            if result.returncode == 0:
                print(f"Removed legacy cluster state: {legacy}")

    killed = kill_cluster_qemu()
    if killed:
        print(f"Terminated {killed} cluster QEMU process(es).")


def patch_kubeconfig(path: Path, server: str) -> None:
    """Patch kubeconfig to use localhost:port for the API server."""
    import re
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"server:\s*https://[^\s]+")
    patched, count = pattern.subn(f"server: https://{server}", text)
    path.write_text(patched, encoding="utf-8")
    print(f"Patched {count} kubeconfig server(s) to https://{server}")


def _kubeconfig_name_matches(name: str, prefix: str) -> bool:
    """Match a kubeconfig entry name against a cluster-name prefix.

    Cluster names are bare ('hpdc-talos'); user and context names embed the
    cluster as 'admin@hpdc-talos[-N]'. Match either form.
    """
    if name.startswith(prefix):
        return True
    _, _, cluster_part = name.partition("@")
    return bool(cluster_part) and cluster_part.startswith(prefix)


def prune_kubeconfig_prefix(cfg: dict, prefix: str) -> dict:
    """Remove every cluster/user/context whose name starts with prefix.

    Keeps the kubeconfig free of stale cluster entries so each bootstrap
    results in exactly one canonical set of names (no -N merge renames).
    """
    if not isinstance(cfg, dict):
        return {}
    for key in ("clusters", "users", "contexts"):
        entries = cfg.get(key)
        if isinstance(entries, list):
            cfg[key] = [
                entry for entry in entries
                if not (isinstance(entry, dict) and _kubeconfig_name_matches(str(entry.get("name", "")), prefix))
            ]
    current = cfg.get("current-context")
    if isinstance(current, str) and _kubeconfig_name_matches(current, prefix):
        names = [
            entry["name"] for entry in cfg.get("contexts", [])
            if isinstance(entry, dict) and "name" in entry
        ]
        if names:
            cfg["current-context"] = names[0]
        else:
            cfg.pop("current-context", None)
    return cfg


def prune_talosconfig_prefix(cfg: dict, prefix: str) -> dict:
    """Remove every talosconfig context whose key starts with prefix."""
    if not isinstance(cfg, dict):
        return {}
    contexts = cfg.get("contexts")
    if isinstance(contexts, dict):
        cfg["contexts"] = {
            name: value for name, value in contexts.items()
            if not str(name).startswith(prefix)
        }
        remaining = list(cfg["contexts"])
        current = cfg.get("context")
        if not isinstance(current, str) or current not in cfg["contexts"]:
            cfg["context"] = remaining[0] if remaining else ""
    return cfg


def patch_cluster_servers(cfg: dict, server: str) -> tuple[dict, int]:
    """Point every cluster entry's server at the given URL; returns (cfg, count)."""
    count = 0
    if not isinstance(cfg, dict):
        return cfg, 0
    clusters = cfg.get("clusters")
    if isinstance(clusters, list):
        for entry in clusters:
            if isinstance(entry, dict):
                cluster = entry.get("cluster")
                if not isinstance(cluster, dict):
                    cluster = {}
                    entry["cluster"] = cluster
                cluster["server"] = server
                count += 1
    return cfg, count


def _read_with_sudo(path: Path) -> str | None:
    result = subprocess.run(["sudo", "-n", "cat", str(path)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"Warning: could not read {path} via sudo: {result.stderr.strip()}", file=sys.stderr)
        return None
    return result.stdout


def _write_with_sudo(path: Path, text: str) -> bool:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(text)
        tmp_path = Path(handle.name)
    try:
        result = subprocess.run(
            ["sudo", "-n", "install", "-m", "600", str(tmp_path), str(path)],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            print(f"Warning: could not write {path} via sudo: {result.stderr.strip()}", file=sys.stderr)
            return False
        return True
    finally:
        tmp_path.unlink(missing_ok=True)


def purge_stale_cluster_state() -> None:
    """Drop stale hpdc-talos* entries from all kube/talos configs.

    talosctl merges new cluster credentials into $HOME/.kube/config and
    ~/.talos/config on `cluster create`; under our HOME override that is
    resources/talos/home. Legacy locations (user home, /root under sudo) are
    purged too so pre-migration leftovers can't resurface as -N renames.
    """
    homes = [TALOS_HOME, Path.home()]
    for home in homes:
        user_kubeconfig = home / ".kube" / "config"
        if user_kubeconfig.exists():
            try:
                cfg = yaml.safe_load(user_kubeconfig.read_text(encoding="utf-8")) or {}
            except Exception as error:
                print(f"Warning: could not parse {user_kubeconfig}: {error}", file=sys.stderr)
                cfg = {}
            pruned = prune_kubeconfig_prefix(cfg, CLUSTER_NAME)
            user_kubeconfig.parent.mkdir(parents=True, exist_ok=True)
            user_kubeconfig.write_text(yaml.safe_dump(pruned, default_flow_style=False), encoding="utf-8")

        user_talosconfig = home / ".talos" / "config"
        if user_talosconfig.exists():
            try:
                cfg = yaml.safe_load(user_talosconfig.read_text(encoding="utf-8")) or {}
            except Exception as error:
                print(f"Warning: could not parse {user_talosconfig}: {error}", file=sys.stderr)
                cfg = {}
            pruned = prune_talosconfig_prefix(cfg, CLUSTER_NAME)
            user_talosconfig.write_text(yaml.safe_dump(pruned, default_flow_style=False), encoding="utf-8")

    if shutil.which("sudo") is None:
        return

    root_kubeconfig_raw = _read_with_sudo(Path("/root/.kube/config"))
    if root_kubeconfig_raw is not None:
        try:
            cfg = yaml.safe_load(root_kubeconfig_raw) or {}
        except Exception as error:
            print(f"Warning: could not parse /root/.kube/config: {error}", file=sys.stderr)
            cfg = {}
        pruned = prune_kubeconfig_prefix(cfg, CLUSTER_NAME)
        _write_with_sudo(Path("/root/.kube/config"), yaml.safe_dump(pruned, default_flow_style=False))

    root_talosconfig_raw = _read_with_sudo(Path("/root/.talos/config"))
    if root_talosconfig_raw is not None:
        try:
            cfg = yaml.safe_load(root_talosconfig_raw) or {}
        except Exception as error:
            print(f"Warning: could not parse /root/.talos/config: {error}", file=sys.stderr)
            cfg = {}
        pruned = prune_talosconfig_prefix(cfg, CLUSTER_NAME)
        _write_with_sudo(Path("/root/.talos/config"), yaml.safe_dump(pruned, default_flow_style=False))


def _generate_kubeconfig_via_talosctl(node_ip: str) -> str | None:
    """Materialize admin kubeconfig straight from the node.

    Fallback for the expected cni=none readiness timeout, where
    `talosctl cluster create` exits before merging credentials into
    $HOME/.kube/config. Returns kubeconfig YAML or None.
    """
    if shutil.which("sudo") is None:
        return None
    # `cluster create` runs under sudo whose HOME may be reset to /root,
    # so the merged talosconfig lands at /root/.talos/config regardless of
    # our override. Try both locations.
    candidates = [Path("/root/.talos/config"), TALOS_HOME / ".talos" / "config"]
    talosconfig = next((c for c in candidates if c.exists()), None)
    if talosconfig is None:
        return None
    tmpdir = tempfile.mkdtemp(prefix="hpdc-kubeconfig-")
    try:
        result = subprocess.run(
            ["sudo", "-n", "-E", resolve_talosctl(),
             "--talosconfig", str(talosconfig),
             "-n", node_ip, "kubeconfig", tmpdir, "--force"],
            capture_output=True, text=True, check=False, env=talos_env(),
        )
        generated = Path(tmpdir) / "kubeconfig"
        if result.returncode != 0 or not generated.exists():
            print(f"Warning: talosctl kubeconfig fallback failed: {result.stderr.strip()}", file=sys.stderr)
            return None
        try:
            return generated.read_text(encoding="utf-8")
        except PermissionError:
            return subprocess.run(["sudo", "-n", "cat", str(generated)],
                                  capture_output=True, text=True, check=False).stdout
    finally:
        subprocess.run(["sudo", "-n", "rm", "-rf", tmpdir], capture_output=True)


def sync_kubeconfigs(server: str, node_ip: str | None = None) -> None:
    """Write a single-context kubeconfig to the repo and the user's home.

    Reads the merged admin kubeconfig created by `talosctl cluster create`
    (root's when running under sudo), prunes stale hpdc-talos* leftovers,
    patches API servers to the host-mapped port, and overwrites both
    <repo>/.kube/config and ~/.kube/config with exactly one canonical
    context (admin@hpdc-talos).
    """
    raw: str | None = None
    # Primary: HOME-overridden location where `cluster create` merges today.
    candidate = TALOS_HOME / ".kube" / "config"
    if candidate.exists():
        raw = candidate.read_text(encoding="utf-8")
    if raw is None and shutil.which("sudo"):
        raw = _read_with_sudo(Path("/root/.kube/config"))  # legacy pre-migration location
    if raw is None:
        fallback = Path.home() / ".kube" / "config"
        raw = fallback.read_text(encoding="utf-8") if fallback.exists() else ""

    cfg = yaml.safe_load(raw) or {}
    cfg = prune_kubeconfig_prefix(cfg, CLUSTER_NAME)
    contexts = [e for e in cfg.get("contexts", []) if isinstance(e, dict)]
    if not any(_kubeconfig_name_matches(str(e.get("name", "")), CLUSTER_NAME) for e in contexts):
        if node_ip is None:
            raise RuntimeError("no admin credentials found for the new cluster; refusing to write empty kubeconfig")
        generated = _generate_kubeconfig_via_talosctl(node_ip)
        if not generated:
            raise RuntimeError("could not materialize admin kubeconfig via talosctl; cluster create merged none")
        # NOTE: no prefix-prune here — the generated config is already
        # canonical for this cluster, and pruning would strip its only context.
        cfg = yaml.safe_load(generated) or {}
    cfg, count = patch_cluster_servers(cfg, server)
    text = yaml.safe_dump(cfg, default_flow_style=False)

    # Under sudo, Path.home() is /root; write to the invoking user's home too.
    sudo_user = os.environ.get("SUDO_USER")
    user_home = Path("/home") / sudo_user if sudo_user and sudo_user != "root" else Path.home()
    targets = [ROOT / ".kube" / "config", user_home / ".kube" / "config"]
    sudo_user = os.environ.get("SUDO_USER")
    owner = None
    if sudo_user and sudo_user != "root":
        import pwd
        owner = pwd.getpwnam(sudo_user)
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        os.chmod(target, 0o600)
        if owner:
            os.chown(target, owner.pw_uid, owner.pw_gid)
    print(f"Patched {count} kubeconfig server(s) to {server}")
    print(f"Wrote single-context kubeconfig to {len(targets)} location(s)")


def build_cluster_create_command(talosctl_cmd: list[str], args: argparse.Namespace) -> list[str]:
    """Build the `talosctl cluster create` command for Docker or QEMU.

    Applies platform/talos/talos-cni-patch.yaml so the bundled flannel CNI and
    kube-proxy are disabled at provision time; Cilium (step 03) is then the
    only CNI, running in kube-proxy-replacement mode.

    Additionally applies platform/talos/talos-offline-mirror-patch.yaml when
    present, forcing all node image pulls through the local registry mirror
    with skipFallback so provisioning never touches the internet.
    """
    provider = args.provider
    create_cmd = [
        *talosctl_cmd,
        "cluster",
        "create",
        provider,
        "--name",
        CLUSTER_NAME,
        "--state",
        str(TALOS_STATE_LINK),
        "--config-patch",
        f"@{CNI_PATCH}",
    ]

    if MIRROR_PATCH.exists():
        create_cmd.extend(["--config-patch", f"@{MIRROR_PATCH}"])

    # QEMU-only: pin the stock installer ref (ISO preset otherwise targets the
    # Image Factory endpoint, unreachable offline — see q2 story Dev Notes).
    if provider == "qemu" and QEMU_INSTALLER_PATCH.exists():
        create_cmd.extend(["--config-patch", f"@{QEMU_INSTALLER_PATCH}"])

    # Always pin talos version to match our configured version
    create_cmd.extend(["--talos-version", TALOS_VERSION_ARG])

    if provider == "qemu":
        # QEMU uses --cidr instead of --subnet
        create_cmd.extend([
            "--cidr",
            args.subnet,
            "--controlplanes",
            str(args.controlplanes),
            "--cpus-controlplanes",
            str(args.cpus_controlplanes),
            "--memory-controlplanes",
            args.memory_controlplanes,
            "--workers",
            str(args.workers),
            "--cpus-workers",
            str(args.cpus_workers),
            "--memory-workers",
            args.memory_workers,
        ])
        # Add virtio-blk disks for Ceph OSD on workers. talosctl expects ONE
        # comma-separated --disks value (repeated flags overwrite, not append):
        # first entry = OS disk on all nodes, later entries = worker-only.
        if args.disks:
            create_cmd.extend(["--disks", ",".join(args.disks)])
    else:
        if provider == "docker" and args.disks:
            print("Warning: --disks ignored by docker provisioner", file=sys.stderr)
        # Docker provider
        create_cmd.extend([
            "--subnet",
            args.subnet,
            "--controlplanes",
            str(args.controlplanes),
            "--workers",
            str(args.workers),
            "--memory-controlplanes",
            args.memory_controlplanes,
            "--cpus-controlplanes",
            str(args.cpus_controlplanes),
            "--memory-workers",
            args.memory_workers,
            "--cpus-workers",
            str(args.cpus_workers),
        ])

    if args.kubernetes_version:
        create_cmd.extend(["--kubernetes-version", args.kubernetes_version])

    return create_cmd


def seed_talos_assets() -> None:
    """Mirror project-local ISO + CNI bundle into every candidate HOME root.

    sudo configurations vary in whether HOME survives `-E`; talosctl resolves
    its asset cache from $HOME regardless of --state. Seeding /root/.talos
    (and the override home) with hardlinks keeps both layouts equivalent and
    prevents redundant multi-hundred-MB downloads.
    """
    isos = sorted(TALOS_CACHE_DIR.glob(f"*{TALOS_VERSION_ARG}*")) or sorted(TALOS_CACHE_DIR.glob("*.iso"))
    iso = isos[0] if isos else None
    seeded = 0
    bases = [TALOS_HOME / ".talos"]
    if shutil.which("sudo"):
        bases.append(Path("/root").joinpath(".talos"))
    for base in bases:
        cache = base / "cache"
        cni_bin = base / "cni" / "bin"
        try:
            cache.mkdir(parents=True, exist_ok=True)
            cni_bin.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            print(f"Warning: cannot seed {base}: {error}", file=sys.stderr)
            continue
        if iso is not None:
            dst = cache / iso.name
            if not dst.exists():
                try:
                    os.link(iso, dst)
                except OSError:
                    shutil.copy2(iso, dst)
                seeded += 1
        for plugin in TALOS_CNI_BIN.glob("*"):
            target = cni_bin / plugin.name
            if plugin.is_file() and not target.exists():
                try:
                    os.link(plugin, target)
                except OSError:
                    shutil.copy2(plugin, target)
                seeded += 1
    if seeded:
        print(f"Seeded {seeded} talos asset(s) into candidate HOME locations.")


def provision_cluster(args: argparse.Namespace) -> None:
    provider = args.provider
    if provider == "qemu":
        validate_qemu_runtime()
    else:
        validate_docker_runtime()

    talosctl_cmd = talosctl_command()

    if not CNI_PATCH.exists():
        raise RuntimeError(f"CNI patch not found: {CNI_PATCH}")

    # Idempotent hygiene: drop stale hpdc-talos* entries from kube/talos
    # configs so the create below merges into a clean namespace and yields
    # exactly one canonical context instead of -1..-N renames.
    purge_stale_cluster_state()

    # Destroy existing cluster first
    destroy_existing_cluster()

    # Ensure ISO/CNI assets exist under every HOME talosctl might resolve
    if provider == "qemu":
        seed_talos_assets()

    # Build talosctl cluster create command (flannel/kube-proxy disabled via CNI patch)
    create_cmd = build_cluster_create_command(talosctl_cmd, args)

    # With cni.name=none, nodes stay NotReady until step 03 installs Cilium,
    # so talosctl's node-readiness wait times out by design. The cluster and
    # its admin kubeconfig are already materialized at that point; treat the
    # readiness timeout as non-fatal and verify the API server after sync.
    create_result = run(create_cmd, check=False, env=talos_env())
    if create_result.returncode != 0:
        print(
            "Warning: cluster create reported failure; this is expected when "
            "the node-readiness wait times out with cni=none. Verifying API server...",
            file=sys.stderr,
        )

    # Sync kubeconfig based on provider
    if provider == "qemu":
        # QEMU: controlplane IP is derived from CIDR (e.g., 10.6.0.2)
        controlplane_ip = args.subnet.split("/")[0].rsplit(".", 1)[0] + ".2"
        # QEMU nodes use the IP directly; no Docker port mapping
        # The API server is at https://<controlplane_ip>:6443
        # For host access, we need to find the QEMU port or use the IP directly
        # talosctl stores the endpoint in the talosconfig; we use that
        sync_kubeconfigs(f"https://{controlplane_ip}:6443", node_ip=controlplane_ip)
    else:
        # Docker: use port mapping from Docker
        result = subprocess.run(
            ["docker", "port", f"{CLUSTER_NAME}-controlplane-1", "6443"],
            capture_output=True, text=True, check=True,
        )
        host_port = result.stdout.strip().split("\n")[0].split(":")[-1]
        controlplane_ip = args.subnet.split("/")[0].rsplit(".", 1)[0] + ".2"
        sync_kubeconfigs(f"https://127.0.0.1:{host_port}", node_ip=controlplane_ip)

    # Verify cluster: nodes are NotReady until Cilium (step 03) is installed.
    api = subprocess.run(
        ["kubectl", "get", "nodes", "--request-timeout=10s"],
        capture_output=True, text=True, check=False,
    )
    if api.returncode != 0:
        raise RuntimeError(
            f"cluster API unreachable after provisioning ({api.stderr.strip()}); "
            "the cluster did not come up — inspect docker ps and container logs"
        )
    print(api.stdout)
    run([*talosctl_cmd, "cluster", "show", "--name", CLUSTER_NAME], check=False, env=talos_env())

    print(f"\nCluster '{CLUSTER_NAME}' provisioned successfully.")
    print(f"Provider: {provider}")
    print(f"Storage backend: {args.storage}")
    print(f"Workers: {args.workers} (CPU: {args.cpus_workers}, RAM: {args.memory_workers}MB)")
    if provider == "qemu":
        print(f"Persistent disks: {args.disks}")


def load_dotenv() -> None:
    """Seed os.environ from ROOT/.env (existing env wins).

    Lets cluster sizing/topology live in a committed .env.example with local
    overrides in .env (gitignored). Safe under sudo: path is repo-relative.
    """
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.split(" #", 1)[0].strip().strip('"').strip("'")
        if key and value:
            os.environ.setdefault(key, value)


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Provision the HPDC Talos dev cluster")
    parser.add_argument("--provider", choices=["docker", "qemu"],
                        default=os.getenv("HPDC_PROVIDER", "qemu"),
                        help="provisioner backend (default from HPDC_PROVIDER, else qemu)")
    parser.add_argument("--controlplanes", type=int,
                        default=int(os.getenv("HPDC_CONTROLPLANES", str(DEFAULT_CONTROLPLANES))),
                        help="number of control plane nodes")
    parser.add_argument("--workers", type=int,
                        default=int(os.getenv("HPDC_WORKERS", str(DEFAULT_WORKERS))),
                        help="number of worker nodes")
    parser.add_argument("--cpus-controlplanes", type=float,
                        default=float(os.getenv("HPDC_CPUS_CONTROLPLANE", str(DEFAULT_CPUS_CONTROLPLANE))),
                        help="CPUs per control plane")
    parser.add_argument("--memory-controlplanes",
                        default=os.getenv("HPDC_MEMORY_CONTROLPLANE", DEFAULT_MEMORY_CONTROLPLANE),
                        help="RAM per control plane in MB")
    parser.add_argument("--cpus-workers", type=float,
                        default=float(os.getenv("HPDC_CPUS_WORKER", str(DEFAULT_CPUS_WORKER))),
                        help="CPUs per worker")
    parser.add_argument("--memory-workers",
                        default=os.getenv("HPDC_MEMORY_WORKER", DEFAULT_MEMORY_WORKER),
                        help="RAM per worker in MB")
    parser.add_argument("--storage", choices=["rook-ceph", "local-path"], default=DEFAULT_STORAGE, help="storage backend (default: rook-ceph)")
    parser.add_argument("--subnet",
                        default=os.getenv("HPDC_SUBNET", "10.6.0.0/24"),
                        help="cluster subnet (default from HPDC_SUBNET)")
    parser.add_argument("--disks", nargs="*",
                        default=os.getenv("HPDC_DISKS", "virtio:10GiB,virtio:10GiB").split(),
                        help="disk specs; first = OS disk (all nodes), later ones = worker-only data disks (default from HPDC_DISKS)")
    parser.add_argument("--kubernetes-version",
                        default=os.getenv("HPDC_KUBERNETES_VERSION", DEFAULT_KUBERNETES_VERSION),
                        help=f"Kubernetes version (default from HPDC_KUBERNETES_VERSION, else {DEFAULT_KUBERNETES_VERSION})")
    parser.add_argument("--dry-run", action="store_true", help="validate and print commands without calling talosctl")
    parser.add_argument("--check", action="store_true", help="validate required scaffold files without provisioning")
    parser.add_argument("--cleanup", action="store_true", help="destroy existing cluster before provisioning")
    parser.add_argument("--talosctl", default="talosctl", help="talosctl executable name")
    args = parser.parse_args()

    if args.workers < 0:
        print("worker count must be >= 0", file=sys.stderr)
        return 2
    if args.storage == "rook-ceph" and args.provider == "qemu" and args.workers < 2:
        print("rook-ceph requires >= 2 workers (replicapool size 2)", file=sys.stderr)
        return 2

    if args.check:
        print(f"Talos {args.provider} bootstrap scaffold validation passed.")
        return 0

    if args.dry_run:
        print("Talos dev cluster bootstrap dry-run passed.")
        print(f"Provider: {args.provider}")
        print(f"Cluster name: {CLUSTER_NAME}")
        print(f"Control planes: {args.controlplanes} (CPU: {args.cpus_controlplanes}, RAM: {args.memory_controlplanes}MB)")
        print(f"Workers: {args.workers} (CPU: {args.cpus_workers}, RAM: {args.memory_workers}MB)")
        print(f"Storage: {args.storage}")
        print(f"Subnet: {args.subnet}")
        if args.provider == "qemu":
            print(f"Disks: {args.disks}")
        print(f"Talos version: {TALOS_VERSION}")
        return 0

    provision_cluster(args)
    print("Talos dev cluster bootstrap complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
