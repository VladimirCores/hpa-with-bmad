# Envoy Gateway Edge Routing

This story installs the Envoy Gateway control plane and the HPDC edge routing contract.

## Route table

| Prefix | Backend | Auth |
| --- | --- | --- |
| `/data` | CouchDB | Casdoor JWT + Casbin |
| `/api` | Knative + Restate | Casdoor JWT + Casbin |
| `/gql` | Hasura | Casdoor JWT + Casbin |
| `/events` | Kafka | X-API-Key |
| `/telemetry` HTTP | Pulsar telemetry ingestion | X-API-Key |
| `/telemetry` gRPC | Pulsar telemetry ingestion | X-API-Key |
| `mqtt:1884` | Pulsar telemetry ingestion | Platform-side MQTT auth |

## GitOps paths

- Base manifest: `gitops/envoy-gateway/base/envoy-gateway.yaml`
- Dev overlay: `gitops/envoy-gateway/overlays/dev/kustomization.yaml`
