#!/usr/bin/env python3
"""Shared access to the single provisioning-footprint registry.

Consolidates the per-component ``output/<component>/*-workspaces.txt``
markers into ``output/provisioned.yaml``. Install scripts call
:func:`require` to gate on a component being provisioned and
:func:`value` to read a recorded scalar.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FOOTPRINTS = ROOT / "output" / "provisioned.yaml"


def load() -> dict:
    """Return the ``provisioned`` map from the footprint registry."""
    if not FOOTPRINTS.exists():
        raise RuntimeError(f"provisioning footprint registry not found: {FOOTPRINTS}")
    data = yaml.safe_load(FOOTPRINTS.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}
    return data.get("provisioned", {}) if isinstance(data.get("provisioned"), dict) else {}


def require(component: str) -> None:
    """Raise if ``component`` has no recorded provisioning footprint."""
    if component not in load():
        raise RuntimeError(f"{component} workspace footprint not found: {FOOTPRINTS.relative_to(ROOT)}")


def value(component: str) -> str | None:
    """Return the scalar ``value`` recorded for ``component``, if any."""
    entry = load().get(component)
    if isinstance(entry, dict):
        return entry.get("value")
    return None
