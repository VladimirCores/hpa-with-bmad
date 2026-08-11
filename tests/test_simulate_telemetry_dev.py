#!/usr/bin/env python3
"""Validate the HPDC telemetry simulator harness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TELEMETRY_DIR = SCRIPTS / "telemetry"
for entry in (SCRIPTS, TELEMETRY_DIR):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from telemetry_simulator import (  # noqa: E402
    TelemetryConfigError,
    TelemetrySchemaError,
    generate_envelope,
    generate_payload,
    load_config,
    parse_simple_yaml,
    run_simulation,
    validate_common_envelope,
)


def write_config(path: Path, *, output_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "device_count: 3",
                "message_rate: 6",
                "device_types:",
                "  - sensor",
                "  - actuator",
                "region_ids:",
                "  - us-east-1",
                "  - eu-west-1",
                "protocol_targets:",
                "  http:",
                "    url: \"http://localhost:9/telemetry\"",
                "    enabled: true",
                    "  mqtt:",
                    "    broker: \"localhost:1883\"",
                    "    topic: \"hpdc/telemetry\"",
                    "    enabled: false",
                    "  grpc:",
                    "    endpoint: \"localhost:50051\"",
                    "    enabled: false",
                    "api_key: \"${HPDC_TELEMETRY_API_KEY}\"",
                    "api_key_env: \"HPDC_TELEMETRY_API_KEY\"",

                f"output_path: \"{output_path.as_posix()}\"",
                "seed: 7",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_parse_simple_yaml() -> None:
    parsed = parse_simple_yaml(ROOT / "output" / "telemetry-simulator" / "config.yaml")
    assert parsed["device_count"] == 10
    assert parsed["protocol_targets"]["http"]["url"].endswith("/telemetry")


def test_generate_payload_and_envelope() -> None:
    payload = generate_payload(device_index=0, device_type="sensor", region_id="us-east-1", sequence=0, seed=42)
    envelope = generate_envelope(
        device_id="sensor_us_east_1_00000",
        device_type="sensor",
        region_id="payload-region",
        sequence=0,
        payload=payload,
        seed=42,
    )
    assert envelope.payload == payload
    assert envelope.device_id == "sensor_us_east_1_00000"
    assert envelope.region_id == "payload-region"
    assert envelope.idempotency_key == "sensor_us_east_1_00000:0"
    assert envelope.timestamp == "1970-01-01T00:00:00Z"
    validate_common_envelope(envelope)


def test_dry_run_writes_summary() -> None:
    with tempfile.TemporaryDirectory(prefix="hpdc-telemetry-", dir=ROOT / "output") as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        output_path = Path(temp_dir) / "summary.json"
        write_config(config_path, output_path=output_path)
        metrics = run_simulation(load_config(config_path), "dry-run")
        summary = metrics.to_summary()
        assert summary["messages_generated"] == 6
        assert summary["device_count"] == 3
        assert summary["region_count"] == 2
        assert summary["total_messages"] == 6
        assert summary["protocol_counts"]["http"]["planned"] == 6
        assert summary["exit_status"] == 0
        assert summary["throughput_messages_per_second"] > 0
        assert json.loads(output_path.read_text(encoding="utf-8"))["total_messages"] == 6


def test_missing_config_returns_config_error() -> None:
    try:
        load_config(Path("/tmp/does-not-exist-hpdc-config.yaml"))
    except TelemetryConfigError:
        return
    raise AssertionError("missing config should raise TelemetryConfigError")


def test_invalid_envelope_rejected() -> None:
    try:
        validate_common_envelope({"device_id": "sensor", "payload": {}})
    except TelemetrySchemaError:
        return
    raise AssertionError("invalid envelope should be rejected")


def test_invalid_config_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="hpdc-telemetry-", dir=ROOT / "output") as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        output_path = Path(temp_dir) / "summary.json"
        write_config(config_path, output_path=output_path)
        config_path.write_text(
            "\n".join(
                [
                    "device_count: 1",
                    "message_rate: 1",
                    "device_types:",
                    "  - sensor",
                    "region_ids:",
                    "  - us-east-1",
                    "protocol_targets:",
                    "  http:",
                    "    url: \"http://localhost:9/telemetry\"",
                    "    enabled: false",
                    "  mqtt:",
                    "    broker: \"localhost:1883\"",
                    "    topic: \"hpdc/telemetry\"",
                    "    enabled: false",
                    "  grpc:",
                    "    endpoint: \"localhost:50051\"",
                    "    enabled: false",
                    "api_key: \"${HPDC_TELEMETRY_API_KEY}\"",
                    "api_key_env: \"HPDC_TELEMETRY_API_KEY\"",
                    f"output_path: \"{output_path.as_posix()}\"",
                    "seed: 7",
                    "unknown_key: true",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        try:
            load_config(config_path)
        except TelemetryConfigError as error:
            assert "unknown simulator config key" in str(error)
            return
        raise AssertionError("unknown config key should be rejected")


def test_oversized_envelope_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="hpdc-telemetry-", dir=ROOT / "output") as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        output_path = Path(temp_dir) / "summary.json"
        write_config(config_path, output_path=output_path)
        config_path.write_text(
            "\n".join(
                [
                    "device_count: 1",
                    "message_rate: 1",
                    "device_types:",
                    "  - sensor",
                    "region_ids:",
                    "  - us-east-1",
                    "protocol_targets:",
                    "  http:",
                    "    url: \"http://localhost:9/telemetry\"",
                    "    enabled: true",
                    "  mqtt:",
                    "    broker: \"localhost:1883\"",
                    "    topic: \"hpdc/telemetry\"",
                    "    enabled: false",
                    "  grpc:",
                    "    endpoint: \"localhost:50051\"",
                    "    enabled: false",
                    "api_key: \"${HPDC_TELEMETRY_API_KEY}\"",
                    "api_key_env: \"HPDC_TELEMETRY_API_KEY\"",
                    f"output_path: \"{output_path.as_posix()}\"",
                    "seed: 7",
                    "payload_size_limit_bytes: 10",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        try:
            run_simulation(load_config(config_path), "dry-run")
        except TelemetrySchemaError:
            return
        raise AssertionError("oversized envelope should be rejected")


def test_live_connection_failure_exits_non_zero() -> None:
    with tempfile.TemporaryDirectory(prefix="hpdc-telemetry-", dir=ROOT / "output") as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        output_path = Path(temp_dir) / "summary.json"
        write_config(config_path, output_path=output_path)
        env = os.environ.copy()
        env["HPDC_TELEMETRY_API_KEY"] = "test-api-key"
        result = subprocess.run(
            [sys.executable, str(TELEMETRY_DIR / "simulate-telemetry-dev.py"), "--config", str(config_path), "--apply"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode != 0
        assert "Protocol error" in result.stderr
        summary = json.loads(output_path.read_text(encoding="utf-8"))
        assert summary["exit_status"] == 1
        assert summary["connection_failures"] == 1


def test_alias_delegates_to_same_entrypoint() -> None:
    with tempfile.TemporaryDirectory(prefix="hpdc-telemetry-", dir=ROOT / "output") as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        output_path = Path(temp_dir) / "alias-summary.json"
        write_config(config_path, output_path=output_path)
        result = subprocess.run(
            [
                sys.executable,
                str(TELEMETRY_DIR / "simulate_telemetry_dev.py"),
                "--config",
                str(config_path),
                "--offline",
                "--dry-run",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(output_path.read_text(encoding="utf-8"))["messages_generated"] == 6


def main() -> int:
    test_parse_simple_yaml()
    test_generate_payload_and_envelope()
    test_dry_run_writes_summary()
    test_missing_config_returns_config_error()
    test_invalid_envelope_rejected()
    test_invalid_config_rejected()
    test_oversized_envelope_rejected()
    test_live_connection_failure_exits_non_zero()
    test_alias_delegates_to_same_entrypoint()
    subprocess.run([sys.executable, "-m", "py_compile", str(TELEMETRY_DIR / "telemetry_simulator.py")], check=True)
    subprocess.run([sys.executable, "-m", "py_compile", str(TELEMETRY_DIR / "simulate-telemetry-dev.py")], check=True)
    subprocess.run([sys.executable, "-m", "py_compile", str(TELEMETRY_DIR / "simulate_telemetry_dev.py")], check=True)
    print("telemetry simulator harness validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
