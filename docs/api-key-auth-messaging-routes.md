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
- The CouchDB admin/Fauxton route (`admin.hpdc.local/couchdb`, HTTPRoute `hpdc-edge-couchdb-admin`)
  is exempt from API-key auth so browsers can reach CouchDB's own UI and REST API; CouchDB's admin
  session is the auth boundary there. See
  [Exposing component admin/settings UIs](envoy-gateway-edge-routing.md#exposing-component-adminsettings-uis).

## GitOps paths

- Base manifests: `gitops/security/base/api-key-authn.yaml`, `gitops/security/base/telemetry-http-api-key-authn.yaml`
- Dev overlay: `gitops/security/overlays/dev/kustomization.yaml`
- Admin route exception: `gitops/envoy-gateway/base/envoy-gateway.yaml` (`hpdc-edge-couchdb-admin` + `allow-hpdc-edge-data-to-couchdb` ReferenceGrant)
