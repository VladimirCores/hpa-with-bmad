# Backstage Developer Portal

This story installs Backstage with Software Catalog and Golden Path templates.

## Features

- Software Catalog
- Golden Path templates
- Dockerfile, Helm chart, catalog-info.yaml, Kargo, and Argo CD scaffolding
- Native auth through Casdoor

## GitOps paths

- Base manifest: `gitops/backstage/base/backstage.yaml`
- Dev overlay: `gitops/backstage/overlays/dev/kustomization.yaml`
