# Casbin ReBAC Policies

This story configures relationship-based access control for HPDC domain routes.

## Relationship model

- company admins inherit client and device access
- relationships are persisted in PostgreSQL-compatible storage
- policy updates hot-reload into the ext-authz service

## GitOps paths

- Base manifest: `gitops/casbin/base/casbin-rebac.yaml`
- Dev overlay: `gitops/casbin/overlays/dev/kustomization.yaml`
