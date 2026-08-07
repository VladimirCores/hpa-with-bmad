#!/usr/bin/env python3
"""Step 19: Kafka alert ingestion setup for Epic 5."""

from __future__ import annotations

import sys
from pathlib import Path

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kafka_produce_alert import main as alert_main

STEP_NAME = "19-kafka-alert-ingestion.py"
STEP_DESCRIPTION = "Setup Kafka alert ingestion topics and schema for Epic 5."


def main() -> int:
    return alert_main()


if __name__ == "__main__":
    raise SystemExit(main())