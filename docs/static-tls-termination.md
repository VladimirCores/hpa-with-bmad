# Static TLS Termination

> **Note:** This document supersedes the previous `docs/cert-manager-tls-termination.md` which described the cert-manager approach removed in Epic 1.5.

This document describes the static self-signed wildcard certificate approach used for Envoy Gateway TLS termination in the HPDC dev cluster.

## Overview

The dev cluster uses a static self-signed wildcard TLS certificate for Envoy Gateway edge routing. This replaces the previous cert-manager approach (removed in Epic 1.5 refactor) with a single offline bootstrap step that generates the cert and applies it as a Kubernetes Secret. cert-manager remains available in the codebase for other purposes but is not used for dev TLS.

## Certificate Parameters

| Parameter | Value |
|-----------|-------|
| Common Name (CN) | `*.hpdc.local` |
| Subject Alternative Name (SAN) | `DNS:*.hpdc.local` |
| Key Type | RSA-2048 |
| Validity | 3650 days (10 years) |
| Format | X.509 self-signed |

> **Warning:** The 10-year validity is chosen for dev convenience. Set a calendar reminder or cron job to re-run `--apply` before expiry. Expired certs will cause all HTTPS routes to fail.

## Storage Location

Certificate and key files are stored outside the repository at:

```
~/.hpdc/certs/tls.crt
~/.hpdc/certs/tls.key
```

These files are **never committed to git** — the `~/.hpdc/` directory is user-local and should be added to `.gitignore` if not already covered. The script creates the `~/.hpdc/certs/` directory if it doesn't exist. Ensure the directory is writable before running `--apply`.

## Kubernetes Secret

The cert/key pair is applied as a Kubernetes Secret consumed by the Envoy Gateway HTTPS listener:

| Field | Value |
|-------|-------|
| Secret Name | `hpdc-edge-tls` |
| Secret Type | `kubernetes.io/tls` |
| Namespace | `envoy-gateway-system` |

The Secret is referenced by the Envoy Gateway HTTPS listener in `gitops/envoy-gateway/base/envoy-gateway.yaml`. When the cert is regenerated with `--force`, the Secret is updated and Envoy Gateway automatically reloads it (no pod restart required).

## Idempotency Behavior

The cert generation script (`scripts/gitops/gen-edge-cert.py`) is idempotent:

- **Cert missing**: Generates a new self-signed cert and applies the Secret to the cluster
- **Cert valid**: Skips generation, ensures Secret exists and matches on-disk files
- **Cert invalid** (wrong CN/SAN, expired, or cert/key mismatch): HALTs with an error. Use `--force` to regenerate

"Invalid" means any of: expired cert, CN/SAN mismatch with expected values, cert/key file mismatch, or unreadable files. The `--force` flag bypasses validation and regenerates the cert even if existing files are invalid.

## Run Modes

The script supports four mutually exclusive modes. If no mode flag is passed, the default is `--check`.

| Mode | Description |
|------|-------------|
| `--check` | Validate local cert state only (no cluster access, no changes). Checks: validity period, CN/SAN match, key type, file readability |
| `--dry-run` | Report what would be done (no changes, no cluster access) |
| `--apply` | Generate cert (if absent) and apply the Secret to the cluster |
| `--force` (with `--apply`) | Regenerate cert even if existing files are invalid |

> **Note:** `--apply` requires a running Kubernetes cluster. If the cluster is unreachable, the script generates the cert on disk but cannot apply the Secret. The Envoy Gateway installer will then fail with a missing TLS Secret error.

## Boot Sequence Integration

The cert generation runs as step **04.5-gen-edge-cert.py** in the boot sequence, executed by `startup.dev.py` when `ENVOY_GATEWAY_ENABLED=true`. This step runs before the Envoy Gateway installer (step 04.6) to ensure the TLS Secret exists when the Gateway starts. If `ENVOY_GATEWAY_ENABLED` is unset or false, the step is skipped and Envoy Gateway will not have a TLS Secret.

## GitOps Paths

| Artifact | Path |
|----------|------|
| Cert generation script | `scripts/gitops/gen-edge-cert.py` |
| Step wrapper | `scripts/steps/04.5-gen-edge-cert.py` |
| Envoy Gateway manifest (consumes Secret) | `gitops/envoy-gateway/base/envoy-gateway.yaml` |

## Production Requirements

The static self-signed cert approach is suitable for **dev clusters only**. Production TLS is **not implemented** in this project.

For production deployments, you must implement one of:

- **cert-manager**: Install cert-manager with a proper issuer (e.g. Let's Encrypt, internal CA) and use `Certificate` resources to manage TLS Secrets with automated renewal
- **External CA**: Pre-provision certificates from an external CA and inject them as Kubernetes Secrets via CI/CD or secrets management (e.g. Infisical, Vault)

The production architecture should define certificate rotation, revocation, and renewal policies appropriate to the deployment environment.

## CA Trust Distribution

A self-signed cert without a proper CA hierarchy means every client must individually trust it. For development:

- Browser: Click "proceed anyway" when prompted about the self-signed cert
- curl: Use `-k` flag to skip certificate verification
- CI/CD: Configure the CI runner to trust the CA cert or skip verification

For production with a proper CA, distribute the CA certificate to developer machines and CI environments via your organization's standard trust distribution mechanism.

## Verification

```bash
# Check local cert state (default mode)
python3 scripts/gitops/gen-edge-cert.py --check

# Dry-run to see what would happen
python3 scripts/gitops/gen-edge-cert.py --dry-run

# Generate and apply
python3 scripts/gitops/gen-edge-cert.py --apply

# Verify the Secret exists in the cluster
kubectl get secret hpdc-edge-tls -n envoy-gateway-system
```

If the secret is missing after `--apply`, check kubectl permissions and ensure the `envoy-gateway-system` namespace exists.
