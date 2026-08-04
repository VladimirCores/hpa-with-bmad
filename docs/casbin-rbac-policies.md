# Casbin RBAC Policies

This story installs Casbin RBAC enforcement for domain routes.

## Base roles

- administrator
- manager
- operator
- technic
- developer
- CEO
- client

## Policy model

- DENY-wins for invalid or conflicting decisions
- Role hierarchy: admin > manager > operator > viewer
- Policy log level: info

## GitOps paths

- Base manifest: `gitops/casbin/base/casbin-rbac.yaml`
- Dev overlay: `gitops/casbin/overlays/dev/kustomization.yaml`
