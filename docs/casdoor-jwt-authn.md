# Casdoor JWT AuthN

This story installs Casdoor and configures it as the centralized identity provider for domain routes.

## OIDC/SAML

- OIDC: enabled
- SAML: enabled
- Refresh token expiration: 24 hours
- Session expiration: 12 hours

## Routes

- `/data`
- `/api`
- `/gql`

## GitOps paths

- Base manifest: `gitops/casdoor/base/casdoor.yaml`
- Dev overlay: `gitops/casdoor/overlays/dev/kustomization.yaml`
