## Deferred from: code review of 4-1-build-iot-device-simulator-and-telemetry-acceptance-harness (2026-08-05)

- Resolved: committed local API key placeholder — `output/telemetry-simulator/config.yaml` no longer commits a secret-like value; live HTTP telemetry resolves `api_key` from `${HPDC_TELEMETRY_API_KEY}` with `api_key_env: HPDC_TELEMETRY_API_KEY`.
