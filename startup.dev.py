#!/usr/bin/env python3
"""Run the HPDC dev cluster setup steps in order."""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import sys
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
STEPS_DIR = ROOT / "scripts" / "steps"
SCRIPTS_DIR = ROOT / "scripts"
LOG_PATH = ROOT / "output" / "startup.dev.log"

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@dataclass(frozen=True)
class Step:
    path: Path
    number: int
    name: str
    description: str
    module: object


def load_step(path: Path) -> Step:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load step: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(path.stem, module)
    spec.loader.exec_module(module)
    name = getattr(module, "STEP_NAME", path.name)
    description = getattr(module, "STEP_DESCRIPTION", "No description")
    number = int(path.name.split("-", 1)[0])
    return Step(path=path, number=number, name=name, description=description, module=module)


def prepare_log() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("", encoding="utf-8")


def write_log(lines: Iterable[str]) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def discover_steps() -> list[Step]:
    if not STEPS_DIR.is_dir():
        return []
    steps = []
    for path in sorted(STEPS_DIR.iterdir()):
        if path.is_file() and path.name.split("-", 1)[0].isdigit():
            steps.append(load_step(path))
    return sorted(steps, key=lambda step: step.number)


def normalize_selection(selection: str) -> str:
    return selection.removeprefix("./").removeprefix("scripts/steps/")


def step_mode_args(step: Step, mode_args: list[str]) -> list[str]:
    if step.name == "01-bootstrap-dev.py":
        if "--check" in mode_args:
            return ["--check"]
        return []
    if step.name == "02-bootstrap-talos-dev.py":
        if "--check" in mode_args:
            return ["--check"]
        if "--dry-run" in mode_args:
            return ["--dry-run"]
        return []

    args = []
    if "--offline" in mode_args:
        args.append("--offline")
    if "--apply" in mode_args:
        args.append("--apply")
    elif "--check" in mode_args:
        args.append("--check")
    else:
        args.append("--dry-run")
    return args


def step_matches(step: Step, selection: str) -> bool:
    normalized = normalize_selection(selection)
    return (
        normalized == step.name
        or normalized == step.path.name
        or normalized == step.path.stem
        or normalized == str(step.number)
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
    return mode_args


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HPDC dev cluster setup steps")
    parser.add_argument("--offline", action="store_true", default=True, help="pass --offline to each selected step")
    parser.add_argument("--dry-run", action="store_true", help="default mode; pass --dry-run to each selected step")
    parser.add_argument("--apply", action="store_true", help="pass --apply to each selected step")
    parser.add_argument("--check", action="store_true", help="validate each selected step without applying manifests")
    parser.add_argument("--list", action="store_true", help="list ordered setup steps and exit")
    parser.add_argument("--step", action="append", default=[], help="run only the named step; may be repeated")
    args = parser.parse_args()

    if args.list:
        prepare_log()
        write_log(["startup.dev.py --list"])
        for step in discover_steps():
            line = f"{step.number:02d}  {step.name}  {step.description}"
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
    write_log(["HPDC dev startup log", f"command: python3 startup.dev.py {' '.join(sys.argv[1:])}", ""])

    failures: list[tuple[str, int]] = []
    for step in selected:
        try:
            code = run_step(step, mode_args)
        except Exception as error:
            print(f"{step.name} failed: {error}", file=sys.stderr)
            failures.append((step.name, 1))
            continue
        if code != 0:
            failures.append((step.name, code))

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
