# Telemetry Ingestion Route

This story adds the GitOps route and capacity scaffold for HPDC telemetry ingestion.

## Routes

| Protocol | External path/listener | Internal backend | Auth |
| --- | --- | --- | --- |
| HTTP | `POST /telemetry` on HTTPS | `pulsar-telemetry-ingestion:8080` | `X-API-Key` |
| gRPC | `/hpdc.telemetry.v1.TelemetryService/*` on HTTPS | `pulsar-telemetry-ingestion:6669` | `X-API-Key` |
| MQTT | TCP listener `mqtt:1884` | `pulsar-telemetry-ingestion:1884` | Platform-side MQTT auth is outside this Story 4.2 scope |

## Capacity

`gitops/telemetry-ingestion/base/telemetry-ingestion.yaml` defines `telemetry-ingestion-capacity`:

- default: `5000`
- `sensor`: `25000`
- `actuator`: `25000`
- `gateway`: `10000`

HTTP capacity failures must return `429 Too Many Requests` when the device-type limit is exceeded.

## GitOps paths

- Base manifest: `gitops/telemetry-ingestion/base/telemetry-ingestion.yaml`
- Dev overlay: `gitops/telemetry-ingestion/overlays/dev/kustomization.yaml`
- Envoy Gateway overlay: `gitops/envoy-gateway/overlays/dev/kustomization.yaml`

## Offline validation

```python
python3 tests/test_install_telemetry_ingestion_dev.py
python3 scripts/gitops/install-telemetry-ingestion-dev.py --offline --dry-run
python3 scripts/startup.dev.py --offline --dry-run --step 17-install-telemetry-ingestion-dev.py
```
