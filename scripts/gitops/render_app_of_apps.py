#!/usr/bin/env python3
"""Filter ArgoCD app-of-apps manifests by component toggles.

Reads toggle state from component_versions and writes only enabled app
YAMLs to gitops/apps/. Disabled components are excluded from the sync.

The script expects all app YAMLs to live in gitops/apps.all/ (the canonical
source). On first run, if apps.all/ doesn't exist, it moves the current
apps/ contents to apps.all/ to bootstrap the staging directory.

Usage:
    python3 render_app_of_apps.py [--dry-run] [--apps-dir gitops/apps.all]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITOPS = ROOT / "gitops"
APPS_ALL = GITOPS / "apps.all"
APPS_ENABLED = GITOPS / "apps"

sys.path.insert(0, str(ROOT / "scripts" / "gitops"))
import component_versions as cv

# ── App YAML -> toggle variable mapping ──────────────────────────────────────
# Maps gitops/apps/*.yaml filename (stem) -> toggle variable name
# (without HPDC_ prefix). Apps not listed here are always included.

APP_TOGGLE_MAP: dict[str, str] = {
    "alerts": "ALERTMANAGER_ENABLED",
    "backstage": "BACKSTAGE_ENABLED",
    "casbin": "CASBIN_ENABLED",
    "casdoor": "CASDOOR_ENABLED",
    "crds-gateway": "ENVOY_GATEWAY_ENABLED",
    "envoy-gateway": "ENVOY_GATEWAY_ENABLED",
    "infisical": "INFISICAL_ENABLED",
    "observability": "GRAFANA_ENABLED",
    "openapi": "SWAGGER_UI_ENABLED",
    "victoria-metrics": "VICTORIA_METRICS_ENABLED",
    "security": "CILIUM_ENABLED",
}

# Apps that are always included (no toggle or always-on)
ALWAYS_INCLUDED: frozenset[str] = frozenset({
    "crds-hpdc",
    "platform",
})


def is_app_enabled(app_stem: str) -> tuple[bool, str | None]:
    """Check if an ArgoCD app should be included based on its toggle.

    Returns (enabled, reason). Unknown (unmapped) apps are EXCLUDED by
    default (opt-in) and a reason string is returned for warning output.
    """
    if app_stem in ALWAYS_INCLUDED:
        return True, None
    toggle_var = APP_TOGGLE_MAP.get(app_stem)
    if toggle_var is None:
        return False, "no toggle mapping (opt-in: excluded)"
    enabled = cv.is_enabled(toggle_var)
    return enabled, (None if enabled else f"disabled via HPDC_{toggle_var}=false")


def bootstrap_apps_all() -> None:
    """Move current apps/ contents to apps.all/ on first run."""
    if APPS_ALL.exists():
        return
    if not APPS_ENABLED.exists():
        return
    APPS_ALL.mkdir(parents=True, exist_ok=True)
    for app_file in APPS_ENABLED.glob("*.yaml"):
        shutil.move(str(app_file), str(APPS_ALL / app_file.name))
    print(f"Bootstrapped {APPS_ALL} from {APPS_ENABLED}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Filter ArgoCD apps by toggles")
    parser.add_argument("--dry-run", action="store_true", help="show what would be included/excluded without writing")
    parser.add_argument("--apps-dir", type=Path, default=APPS_ALL, help="source directory with all app YAMLs")
    parser.add_argument("--output-dir", type=Path, default=APPS_ENABLED, help="output directory for enabled apps")
    args = parser.parse_args()

    cv.load_dotenv()
    cv.resolve()

    # Bootstrap apps.all/ if it doesn't exist
    bootstrap_apps_all()

    if not args.apps_dir.is_dir():
        print(f"Source apps directory not found: {args.apps_dir}", file=sys.stderr)
        return 1

    app_files = sorted(args.apps_dir.glob("*.yaml"))
    if not app_files:
        print(f"No app YAMLs found in {args.apps_dir}", file=sys.stderr)
        return 1

    included: list[str] = []
    excluded: list[str] = []

    for app_file in app_files:
        stem = app_file.stem
        enabled, reason = is_app_enabled(stem)
        if enabled:
            included.append(stem)
            if not args.dry_run:
                target = args.output_dir / app_file.name
                args.output_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(app_file, target)
        else:
            excluded.append(stem)
            if reason:
                print(f"  [skip] {stem}: {reason}", file=sys.stderr)
            if not args.dry_run:
                target = args.output_dir / app_file.name
                if target.exists():
                    target.unlink()

    # Clean stale files: remove any .yaml in output_dir not sourced from apps.all.
    if not args.dry_run and args.output_dir.is_dir():
        valid_names = {f.name for f in app_files}
        for stale in args.output_dir.glob("*.yaml"):
            if stale.name not in valid_names:
                stale.unlink()

    # Print summary
    mode = "DRY-RUN " if args.dry_run else ""
    print(f"apps {mode}rendered: {len(included)} enabled, {len(excluded)} skipped (disabled via toggle)")
    if excluded:
        print(f"  skipped: {', '.join(excluded)}")
    if included:
        print(f"  enabled: {', '.join(included)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
