# Tool UI Routes via Envoy Gateway

This story exposes Backstage, Argo CD UI, and Kargo UI through Envoy Gateway routes with native tool auth.

## Routes

- `backstage.hpdc.local`
- `argocd.hpdc.local`
- `kargo.hpdc.local`

## Auth behavior

- Native tool auth is enforced.
- Casdoor/Casbin ext_authz is not enforced on tool UI routes.

## GitOps paths

- Base manifest: `gitops/tool-ui/base/tool-ui-routes.yaml`
- Dev overlay: `gitops/tool-ui/overlays/dev/kustomization.yaml`
