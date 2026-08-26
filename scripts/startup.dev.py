#!/usr/bin/env python3
"""Run the HPDC dev cluster setup steps in order.

Idempotent startup lifecycle: before provisioning (step 02), any existing
dev cluster (kind or Talos/QEMU) is torn down cleanly. Persistent QEMU
disk images are preserved across recreate cycles.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
STEPS_DIR = ROOT / "scripts" / "steps"
SCRIPTS_DIR = ROOT / "scripts"
GITOPS_DIR = ROOT / "scripts" / "gitops"
LOG_PATH = ROOT / "output" / "startup.dev.log"

for entry in (SCRIPTS_DIR, GITOPS_DIR):
    if entry not in sys.path:
        sys.path.insert(0, str(entry))


@dataclass(frozen=True)
class Step:
    path: Path
    number: float
    name: str
    description: str
    module: object


def step_label(number: float) -> str:
    if number % 1:
        return f"{int(number):02d}.{int((number % 1) * 10):.0f}"
    return f"{int(number):02d}"


def _is_step_number(s: str) -> bool:
    return bool(re.fullmatch(r"\d{1,2}(\.\d)?", s))


def load_step(path: Path) -> Step:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load step: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(path.stem, module)
    spec.loader.exec_module(module)
    name = getattr(module, "STEP_NAME", path.name)
    description = getattr(module, "STEP_DESCRIPTION", "No description")
    number = float(path.name.split("-", 1)[0])
    return Step(path=path, number=number, name=name, description=description, module=module)


def prepare_log() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("", encoding="utf-8")


def write_log(lines: Iterable[str]) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def parse_last_run(log_path: Path) -> dict[str, int]:
    """Map step name -> exit code from the most recent startup.dev.log."""
    results: dict[str, int] = {}
    if not log_path.exists():
        return results
    current: str | None = None
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("== ") and ": " in line:
            current = line[3:].split(": ", 1)[0].strip()
        elif line.startswith("exit code:") and current is not None:
            try:
                results[current] = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
            current = None
    return results


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    sep = "-+-".join("-" * w for w in widths)
    head = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    body = "\n".join(" | ".join(c.ljust(w) for c, w in zip(row, widths)) for row in rows)
    return "\n".join([head, sep, body]) if body else head


def cluster_summary() -> str:
    try:
        result = subprocess.run(
            ["kubectl", "get", "nodes", "--no-headers", "--request-timeout=5s"],
            capture_output=True, text=True, check=True,
        )
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        ready = sum(1 for l in lines if l.split()[1] == "Ready")
        return f"{ready}/{len(lines)} nodes Ready"
    except Exception:
        return "unreachable"


def registry_summary() -> str:
    import json
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:5000/v2/_catalog", timeout=3) as resp:
            repos = json.load(resp).get("repositories", [])
        return f"{len(repos)} image repos cached"
    except Exception:
        return "offline (hpa-local-registry not reachable)"


def print_status() -> int:
    steps = discover_steps()
    last_run = parse_last_run(LOG_PATH)

    step_rows = []
    for step in steps:
        if step.name in last_run:
            code = last_run[step.name]
            state = "ok" if code == 0 else f"FAIL({code})"
        else:
            state = "never-run"
        desc = step.description if len(step.description) <= 46 else step.description[:43] + "..."
        step_rows.append([step_label(step.number), state, desc])

    components: dict[str, dict] = {}
    try:
        sys.path.insert(0, str(GITOPS_DIR))
        import _provisioned
        components = _provisioned.load()
    except Exception:
        pass
    comp_rows = []
    for name, entry in sorted(components.items()):
        version = ""
        if isinstance(entry, dict):
            version = str(entry.get("version") or entry.get("value") or "")
            if len(version) > 24:
                version = version[:21] + "..."
        comp_rows.append([name, version])

    print(f"Cluster : {cluster_summary()}")
    print(f"Registry: {registry_summary()}")
    print()
    print("Setup steps (last run recorded in output/startup.dev.log):")
    print(render_table(["STEP", "LAST-RUN", "DESCRIPTION"], step_rows))
    print()
    if comp_rows:
        print("Provisioned components (output/provisioned.yaml):")
        print(render_table(["COMPONENT", "VERSION"], comp_rows))
    else:
        print("Provisioned components: none recorded.")
    return 0


def discover_steps() -> list[Step]:
    if not STEPS_DIR.is_dir():
        return []
    steps = []
    for path in sorted(STEPS_DIR.iterdir()):
        if path.is_file() and _is_step_number(path.name.split("-", 1)[0]):
            steps.append(load_step(path))
    return sorted(steps, key=lambda step: step.number)


def normalize_selection(selection: str) -> str:
    return selection.removeprefix("./").removeprefix("scripts/steps/")


def step_mode_args(step: Step, mode_args: list[str]) -> list[str]:
    if step.name == "01-bootstrap-dev.py":
        if "--check" in mode_args:
            return ["--check"]
        return []
    if step.name == "01.5-configure-firewalld-talos.py":
        # Host-level step: accepts mode flags only, never --offline
        if "--check" in mode_args:
            return ["--check"]
        if "--apply" in mode_args:
            return ["--apply"]
        return ["--dry-run"]
    if step.name == "02-bootstrap-talos-dev.py":
        if "--check" in mode_args:
            return ["--check"]
        if "--dry-run" in mode_args:
            return ["--dry-run"]
        # Pass storage and provider options to bootstrap
        args = []
        if "--storage" in mode_args:
            idx = mode_args.index("--storage")
            if idx + 1 < len(mode_args):
                args.extend(["--storage", mode_args[idx + 1]])
        if "--provider" in mode_args:
            idx = mode_args.index("--provider")
            if idx + 1 < len(mode_args):
                args.extend(["--provider", mode_args[idx + 1]])
        return args

    args = []
    if "--offline" in mode_args:
        args.append("--offline")
    if "--apply" in mode_args:
        args.append("--apply")
    elif "--check" in mode_args:
        args.append("--check")
    else:
        args.append("--dry-run")
    # Pass storage option to steps that need it
    STORAGE_AWARE_STEPS = {"02-bootstrap-talos-dev.py", "05-install-storage-dev.py"}
    if "--storage" in mode_args and step.name in STORAGE_AWARE_STEPS:
        idx = mode_args.index("--storage")
        if idx + 1 < len(mode_args):
            args.extend(["--storage", mode_args[idx + 1]])
    return args


def step_matches(step: Step, selection: str) -> bool:
    normalized = normalize_selection(selection)
    return (
        normalized == step.name
        or normalized == step.path.name
        or normalized == step.path.stem
        or normalized == str(step.number)
        or normalized == step_label(step.number)
    )


def selected_steps(steps: Iterable[Step], selections: list[str]) -> list[Step]:
    if not selections:
        return list(steps)
    selected = []
    for selection in selections:
        matches = [step for step in steps if step_matches(step, selection)]
        if not matches:
            raise ValueError(f"unknown step: {selection}")
        selected.extend(matches)
    return selected


def run_step(step: Step, mode_args: list[str]) -> int:
    stdout = StringIO()
    stderr = StringIO()
    original_argv = sys.argv[:]
    sys.argv = [str(step.path), *step_mode_args(step, mode_args)]
    code = 0
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = int(step.module.main())
    except SystemExit as error:
        code = int(error.code or 0)
    except Exception as error:
        code = 1
    finally:
        sys.argv = original_argv

    lines = [f"== {step.name}: {step.description} ==", f"exit code: {code}"]
    stdout_text = stdout.getvalue().rstrip()
    stderr_text = stderr.getvalue().rstrip()
    if stdout_text:
        lines.append(stdout_text)
    if stderr_text:
        lines.extend(["[stderr]", stderr_text])
    write_log(lines)
    return code


def build_mode_args(args: argparse.Namespace) -> list[str]:
    mode_args = []
    if args.offline:
        mode_args.append("--offline")
    if args.apply:
        if args.dry_run:
            raise ValueError("--apply and --dry-run cannot be used together")
        mode_args.append("--apply")
    elif args.check:
        if args.dry_run:
            raise ValueError("--check and --dry-run cannot be used together")
        mode_args.append("--check")
    else:
        mode_args.append("--dry-run")
    if hasattr(args, 'storage') and args.storage:
        mode_args.extend(["--storage", args.storage])
    if hasattr(args, 'provider') and args.provider:
        mode_args.extend(["--provider", args.provider])
    return mode_args


def teardown_existing_cluster() -> int:
    """Tear down any existing dev cluster before provisioning.

    Calls stop.dev.py --check to detect clusters, then --apply to tear down.
    Returns 0 on success (or nothing to tear down), 1 on critical failure.

    Note: talosctl cluster destroy may return non-zero due to network cleanup
    issues even when the cluster is effectively destroyed. We treat the teardown
    as successful if stop.dev.py reports the cluster as gone after teardown.
    """
    import subprocess

    stop_script = SCRIPTS_DIR / "stop.dev.py"

    # Check if any cluster exists
    result = subprocess.run(
        [sys.executable, str(stop_script), "--check"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Warning: cluster check failed: {result.stderr.strip()}", file=sys.stderr)
        return 1

    if "No dev cluster running" in result.stdout:
        print("No existing dev cluster to tear down.")
        return 0

    # Tear down the cluster
    print("Tearing down existing dev cluster before provisioning...")
    result = subprocess.run(
        [sys.executable, str(stop_script), "--apply"],
        capture_output=False,  # let output flow to user
    )

    # Verify teardown succeeded (check is more reliable than return code)
    verify = subprocess.run(
        [sys.executable, str(stop_script), "--check"],
        capture_output=True, text=True,
    )
    if verify.returncode != 0 or "No dev cluster running" not in verify.stdout:
        print(f"Cluster teardown may have failed (exit code {result.returncode}).", file=sys.stderr)
        print(f"Check output: {verify.stdout.strip()}", file=sys.stderr)
        return 1

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HPDC dev cluster setup steps")
    parser.add_argument("--offline", action="store_true", default=True, help="pass --offline to each selected step")
    parser.add_argument("--dry-run", action="store_true", help="default mode; pass --dry-run to each selected step")
    parser.add_argument("--apply", action="store_true", help="pass --apply to each selected step")
    parser.add_argument("--check", action="store_true", help="validate each selected step without applying manifests")
    parser.add_argument("--list", action="store_true", help="list ordered setup steps and exit")
    parser.add_argument("--status", action="store_true", help="show per-step and per-component installation status")
    parser.add_argument("--step", action="append", default=[], help="run only the named step; may be repeated")
    parser.add_argument("--storage", choices=["rook-ceph", "local-path"], default="rook-ceph", help="storage backend for the cluster")
    parser.add_argument("--provider", choices=["docker", "qemu"], default="qemu", help="Talos provisioner (default: qemu)")
    args = parser.parse_args()

    if args.status:
        print_status()
        return 0

    if args.list:
        prepare_log()
        write_log(["startup.dev.py --list"])
        for step in discover_steps():
            line = f"{step_label(step.number)}  {step.name}  {step.description}"
            print(line)
            write_log([line])
        return 0

    steps = discover_steps()
    if not steps:
        prepare_log()
        message = "No HPDC dev steps found under scripts/steps/."
        print(message, file=sys.stderr)
        write_log([message])
        return 2

    try:
        mode_args = build_mode_args(args)
        selected = selected_steps(steps, args.step)
    except ValueError as error:
        prepare_log()
        print(error, file=sys.stderr)
        write_log([str(error)])
        return 2

    prepare_log()
    write_log(["HPDC dev startup log", f"command: python3 scripts/startup.dev.py {' '.join(sys.argv[1:])}", ""])

    # Idempotent lifecycle: tear down any existing cluster before provisioning
    is_apply = "--apply" in mode_args
    registry_service = SCRIPTS_DIR / "services" / "image-registry.py"
    if is_apply and registry_service.exists() and any(step.number in (2, 5) for step in selected):
        print("[pre] ensuring offline image registry ...", flush=True)
        rc = subprocess.run([sys.executable, str(registry_service)]).returncode
        if rc != 0:
            message = "image registry ensure failed; aborting."
            print(message, file=sys.stderr)
            write_log([message])
            return 1
    if is_apply and any(s.number == 2 for s in selected):
        teardown_rc = teardown_existing_cluster()
        if teardown_rc != 0:
            message = "Cluster teardown failed; aborting before provisioning."
            print(message, file=sys.stderr)
            write_log([message])
            return 1
        write_log(["Cluster teardown complete; proceeding with provisioning."])

    failures: list[tuple[str, int]] = []
    summary_rows: list[list[str]] = []
    total = len(selected)
    for idx, step in enumerate(selected, 1):
        print(f"[{idx}/{total}] {step.name} - {step.description} ...", flush=True)
        started = time.monotonic()
        try:
            code = run_step(step, mode_args)
        except Exception as error:
            print(f"{step.name} failed: {error}", file=sys.stderr)
            failures.append((step.name, 1))
            continue
        elapsed = time.monotonic() - started
        verdict = "OK" if code == 0 else f"FAILED(exit {code})"
        print(f"[{idx}/{total}] {step.name}: {verdict} in {elapsed:.1f}s", flush=True)
        summary_rows.append([step_label(step.number), verdict, f"{elapsed:.1f}s", step.description])
        if code != 0:
            failures.append((step.name, code))

    if summary_rows:
        table = render_table(["STEP", "RESULT", "TIME", "DESCRIPTION"], summary_rows)
        print("", flush=True)
        print("Run summary:", flush=True)
        print(table, flush=True)
        write_log(["", "Run summary:", table])

    if failures:
        print("HPDC dev step run failed:")
    write_log([""])
    if failures:
        write_log(["HPDC dev step run failed:"])
        for name, code in failures:
            write_log([f"- {name}: exit code {code}"])
            print(f"- {name}: exit code {code}")
        return 1

    write_log([""])
    write_log(["HPDC dev setup completed."])
    print("HPDC dev setup completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
