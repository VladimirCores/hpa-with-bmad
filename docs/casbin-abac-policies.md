# Casbin ABAC Policies

This story configures attribute-based access control for HPDC domain routes.

## Dynamic attributes

- time of day
- location
- device state
- risk
- clearance

## Combined decision

- RBAC + ReBAC + ABAC are evaluated together.
- DENY-wins is enforced.
- Combined evaluation target: under 10ms p99.

## GitOps paths

- Base manifest: `gitops/casbin/base/casbin-abac.yaml`
- Dev overlay: `gitops/casbin/overlays/dev/kustomization.yaml`
