# High Performance Distributed Cluster (HPDC)

HPDC is an offline-first, security-focused distributed cluster scaffold for Talos, Cilium, Rook-Ceph, Harbor, GitOps delivery, and offline image distribution.

## Project-wide scripting rule

All project automation scripts must be written in Python 3. Shell wrappers are not allowed in the project `scripts/` directory.

## Prerequisites

- Python 3
- `talosctl` for real Talos bootstrap
- QEMU or `qemu-img`
- Optional: `kubectl` for real cluster apply and readiness checks

## Bootstrap dev repository

Run the scaffold bootstrap once:

```python
python3 scripts/bootstrap_dev.py
```

## Run offline dev setup dry-runs

Run the platform and GitOps setup without applying to a live cluster:

```python
python3 startup.dev.py --offline --dry-run
```

Run one ordered step only:

```python
python3 startup.dev.py --offline --dry-run --step 02-bootstrap-talos-dev.py
```

List all ordered steps:

```python
python3 startup.dev.py --list
```

Each startup run rewrites `output/startup.dev.log` before executing so the selected dry-run, check, or apply flow is reviewable.

## Validate all implemented stories

Run all validation tests:

```python
python3 tests/test_bootstrap_dev.py
python3 tests/test_bootstrap_talos_dev.py
python3 tests/test_install_cilium_dev.py
python3 tests/test_install_rook_ceph_dev.py
python3 tests/test_install_cilium_mtls_dev.py
python3 tests/test_install_harbor_dev.py
python3 tests/test_preload_harbor_cache.py
python3 tests/test_refresh_harbor_cache.py
python3 tests/test_provision_local_git_mirror.py
python3 tests/test_install_spegel_dev.py
python3 tests/test_install_kargo_dev.py
python3 tests/test_install_argocd_dev.py
python3 tests/test_install_argorollouts_dev.py
python3 tests/test_install_argoevents_dev.py
python3 tests/test_install_envoy_gateway_dev.py
python3 tests/test_install_telemetry_ingestion_dev.py
python3 tests/test_telemetry_capacity_dev.py
python3 tests/test_install_cert_manager_dev.py
python3 tests/test_epic3_gateway_stack_dev.py
python3 tests/test_validate_offline_gitops_pipeline.py
python3 tests/test_startup_dev.py
```

Compile all Python scripts and tests:

```python
python3 -m compileall -q startup.dev.py scripts tests
```

## Apply to a real offline Talos cluster

Apply only after the dry-runs pass and `output/talos/talosconfig` exists:

```python
python3 startup.dev.py --offline --apply
```

`--apply` requires `kubectl` and a healthy offline Talos cluster.

## Quick health check

```python
python3 startup.dev.py --offline --dry-run --step 16-install-envoy-gateway-dev.py
python3 startup.dev.py --offline --dry-run --step 17-install-telemetry-ingestion-dev.py
python3 startup.dev.py --offline --dry-run --step 15-validate-offline-gitops-pipeline.py
```

Expected output:

```text
Offline GitOps pipeline validation passed.
Harbor registry, preload cache, digest refresh, Git mirror, Spegel, Kargo, Argo CD, Rollouts, and Argo Events are configured.
```
