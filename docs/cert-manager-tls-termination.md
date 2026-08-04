# cert-manager TLS Termination

This story installs cert-manager in the HPDC dev GitOps pipeline and provisions the Envoy Gateway edge certificate.

## Issuer

- `ClusterIssuer/hpdc-selfsigned`

## Certificate

- `Certificate/hpdc-edge-tls` in namespace `envoy-gateway-system`
- `Secret/hpdc-edge-tls` is issued from the self-signed issuer
- DNS names:
  - `*.hpdc.local`

## Envoy Gateway integration

- `Gateway/hpdc-edge` references `Secret/hpdc-edge-tls`
- HTTP listener `http-redirect` redirects `80` to `443` over HTTPS

## GitOps paths

- Base manifest: `gitops/cert-manager/base/cert-manager.yaml`
- Dev overlay: `gitops/cert-manager/overlays/dev/kustomization.yaml`
