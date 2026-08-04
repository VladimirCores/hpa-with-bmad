# API-Key Auth for Messaging Routes

This story configures Envoy Gateway API-key authentication for machine-only messaging routes.

## Routes

- `/events` requires `X-API-Key` from `security/messaging-api-keys`
- `/telemetry` requires `X-API-Key` from `security/messaging-api-keys`

## Exclusions

- Casdoor and Casbin are not used for `/events` or `/telemetry`.

## GitOps paths

- Base manifest: `gitops/security/base/api-key-authn.yaml`
- Dev overlay: `gitops/security/overlays/dev/kustomization.yaml`
