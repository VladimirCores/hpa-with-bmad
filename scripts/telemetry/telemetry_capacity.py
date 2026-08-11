#!/usr/bin/env python3
"""Validate HPDC telemetry capacity limits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "gitops" / "telemetry-ingestion" / "base" / "telemetry-ingestion.yaml"


def load_capacity(config_path: Path = DEFAULT_CONFIG) -> dict[str, int]:
    data = config_path.read_text(encoding="utf-8")
    capacities: dict[str, int] = {}
    in_device_types = False
    for raw_line in data.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped == "deviceTypes:":
            in_device_types = True
            continue
        if stripped.startswith("default:"):
            capacities["default"] = int(stripped.split(":", 1)[1].strip())
            continue
        if not in_device_types:
            continue
        if not line.startswith("      "):
            in_device_types = False
            continue
        stripped = line.strip()
        if not stripped:
            continue
        key, value = stripped.split(":", 1)
        capacities[key] = int(value.strip())
    return capacities


def capacity_status(device_type: str, count: int, config_path: Path = DEFAULT_CONFIG) -> tuple[int, dict[str, Any]]:
    capacities = load_capacity(config_path)
    capacity = capacities.get(device_type, capacities.get("default", 0))
    if count > capacity:
        return 429, {
            "status": 429,
            "message": "telemetry capacity exceeded",
            "device_type": device_type,
            "count": count,
            "capacity": capacity,
        }
    return 202, {
        "status": 202,
        "message": "telemetry accepted",
        "device_type": device_type,
        "count": count,
        "capacity": capacity,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check HPDC telemetry capacity behavior")
    parser.add_argument("--device-type", default="sensor")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    status, body = capacity_status(args.device_type, args.count, args.config)
    print(json.dumps(body, sort_keys=True))
    return 0 if status == 202 else 2


if __name__ == "__main__":
    raise SystemExit(main())
