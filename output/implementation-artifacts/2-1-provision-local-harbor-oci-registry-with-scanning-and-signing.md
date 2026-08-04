# Story 2.1: Provision Local Harbor OCI Registry with Scanning and Signing

Status: done

## Story

As a Platform Engineer,
I want Harbor 2.11.3 installed as a local OCI registry with Trivy/Clair scanning and Cosign signature verification,
so that GitOps workloads can pull trusted images and charts without internet access.

## Acceptance Criteria

1. Given the offline Talos dev cluster is healthy and Harbor images are pre-cached locally, when Harbor is applied from GitOps, then Harbor 2.11.3 is installed as a local OCI registry.
2. Trivy/Clair scanning is enabled on image push.
3. Cosign signature verification is enabled for image pulls.
4. Harbor is available through a ClusterIP service.
5. Offline mode does not require internet access.
6. The installer exits non-zero on any failure.

## Completion Summary

- Harbor was implemented as Story 1.6 and is reused for Epic 2 Story 2.1.
- Validated offline manifests, scripts, docs, and tests.