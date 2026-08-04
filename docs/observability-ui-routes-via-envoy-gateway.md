# Observability UI Routes via Envoy Gateway

This story exposes Grafana and Hubble UI through Envoy Gateway routes with native tool auth.

## Routes

- `grafana.hpdc.local`
- `hubble.hpdc.local`

## Auth behavior

- Native tool auth is enforced.
- Casdoor/Casbin ext_authz is not enforced on tool UI routes.
- Story is deferred until Epic 7 tools are installed.

## GitOps paths

- Base manifest: `gitops/observability/base/observability-ui-routes.yaml`
- Envoy route manifest: `gitops/observability/base/envoy-ui-routes.yaml`
- Dev overlay: `gitops/observability/overlays/dev/kustomization.yaml`
