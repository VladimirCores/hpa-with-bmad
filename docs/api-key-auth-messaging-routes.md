# API-Key Auth for Messaging Routes

This story configures Envoy Gateway API-key authentication for machine-only messaging routes.

## Routes

- `/data`, `/api`, `/events` require `X-API-Key` from `security/events-api-key` (`events-key`, dev value `hpdc-events-dev-key`)
- `/telemetry` requires `X-API-Key` from `security/telemetry-api-key` (`telemetry-key`, dev value `hpdc-telemetry-dev-key`)
- The gRPC route (`hpdc.telemetry.v1.TelemetryService`) and its MQTT TCP route are intentionally dropped from the base
  manifests (Pulsar gap, 325c8cb) — gRPC/MQTT ingestion is documented but not wired until Pulsar topics exist.

## Key-level isolation (R-009)

- `events-key` authenticates the messaging/domain route (`/data`, `/api`, `/events`) only.
- `telemetry-key` authenticates the telemetry HTTP route (`/telemetry`) only.
- No shared store accepts either key on both paths: the events store holds only `events-key`, the telemetry store holds only `telemetry-key`.

## Exclusions

- Casdoor and Casbin are not used for `/events`, `/telemetry`, `/data`, or `/api`.

## GitOps paths

- Base manifests: `gitops/security/base/api-key-authn.yaml`, `gitops/security/base/telemetry-http-api-key-authn.yaml`
- Dev overlay: `gitops/security/overlays/dev/kustomization.yaml`
