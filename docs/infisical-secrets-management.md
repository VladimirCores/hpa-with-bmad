# Infisical Secrets Management

This story installs Infisical and configures secret injection semantics for HPDC workloads.

## Secret policy

- Secrets are injected through volume mounts.
- Secrets are never stored in Git, ConfigMaps, or environment variables.
- Default rotation interval: 90 days.
- Audit logging is enabled.

## GitOps paths

- Base manifest: `gitops/infisical/base/infisical.yaml`
- Dev overlay: `gitops/infisical/overlays/dev/kustomization.yaml`
