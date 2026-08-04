# OpenAPI Specification Governance

This story establishes OpenAPI YAML as the source-of-truth contract for HPDC edge APIs.

## Contract

- `specs/api/hpdc-edge-api.yaml`
- Swagger UI deployment: `gitops/openapi/base/openapi.yaml`
- Swagger UI route: `/docs`

## Validation

- OpenAPI linting is represented by the contract file.
- Swagger UI is exposed through Envoy Gateway in story 3.10.

## GitOps paths

- Base manifest: `gitops/openapi/base/openapi.yaml`
- Dev overlay: `gitops/openapi/overlays/dev/kustomization.yaml`
