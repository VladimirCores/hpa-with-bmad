# Envoy Gateway Edge Routing

This story installs the Envoy Gateway control plane and the HPDC edge routing contract.

## Route table

| Prefix | Backend | Auth |
| --- | --- | --- |
| `/data` | CouchDB | Casdoor JWT + Casbin |
| `/api` | Knative + Restate | Casdoor JWT + Casbin |
| `/gql` | Hasura | Casdoor JWT + Casbin |
| `/events` | Kafka | X-API-Key |
| `/telemetry` | Pulsar | X-API-Key |

## GitOps paths

- Base manifest: `gitops/envoy-gateway/base/envoy-gateway.yaml`
- Dev overlay: `gitops/envoy-gateway/overlays/dev/kustomization.yaml`
