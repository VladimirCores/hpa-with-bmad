---
title: Generate Static Self-Signed Wildcard Cert and Create TLS Secret
type: feature
created: 2026-09-02
status: done
baseline_revision: 985ce31
final_revision: 8a09015
review_loop_iteration: 1
followup_review_recommended: true
context: []
warnings: []
---

## Intent

**Problem:** Envoy Gateway's HTTPS listener on port 443 references a Kubernetes Secret named `hpdc-edge-tls` in `envoy-gateway-system` (see `gitops/envoy-gateway/base/envoy-gateway.yaml`). With cert-manager removed from the core layer (Epic 1.5 refactor), nothing generates that secret — so the Gateway's HTTPS listener can never reach `Programmed=True` and `*.hpdc.local` routes stay unreachable.

**Approach:** Add a new core-layer bootstrap step (between Cilium/step 04 and storage/step 05) that generates a self-signed wildcard cert for `*.hpdc.local` using `openssl` (RSA-2048, CN+SAN, 10-year validity), stores it at `~/.hpdc/certs/` (outside the repo, never committed), and applies it as a `kubernetes.io/tls` Secret named `hpdc-edge-tls` in `envoy-gateway-system`.

## Boundaries & Constraints

**Always:** RSA 2048-bit key; CN=`*.hpdc.local`; SAN=`DNS:*.hpdc.local`; 3650-day validity; cert/key stored at `~/.hpdc/certs/tls.crt` and `~/.hpdc/certs/tls.key`; files must NOT be in git (outside repo or gitignored); Secret named `hpdc-edge-tls`, type `kubernetes.io/tls`, in `envoy-gateway-system`; idempotent (skip generation if cert+key already exist and are valid); exit non-zero on any failure; no internet access required; follows the `scripts/gitops/` + `scripts/steps/` two-file pattern (gitops logic + step wrapper).

**Block If:** Certificate files exist at `~/.hpdc/certs/` but are mismatched (cert/key pair doesn't work), expired, or have wrong CN/SAN — this cannot be auto-resolved safely; HALT with blocking condition `existing cert files are invalid`.

**Never:** Use cert-manager; contact an external CA or internet endpoint; push cert/key files to git; overwrite existing valid certs without reporting "cert already present"; run without `--apply` actually applying changes (only `--check`/`--dry-run`/`--apply` modes).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh bootstrap, cert absent | `~/.hpdc/certs/tls.crt` does not exist | Generates new self-signed cert, creates `envoy-gateway-system` namespace and Secret, prints success | Exit 1 if openssl fails, if file write fails, or if kubectl apply fails |
| Idempotent re-run | `~/.hpdc/certs/tls.crt` + `tls.key` exist and are valid | Reports "cert already present", ensures Secret exists in cluster, reports "secret already present" | Exit 1 if cert/key pair is invalid (mismatched) |
| Invalid cert exists | `~/.hpdc/certs/` has files but pair is broken/expired | Reports what's wrong, lists the issue | Exit 1 with "existing cert files are invalid" — HALT |
| No cluster access | `kubectl` not configured or cluster unreachable | Reports inability to apply Secret | Exit 1 if `--apply` and kubectl fails; `--check` only validates local files |

## Code Map

- `gitops/envoy-gateway/base/envoy-gateway.yaml` -- references `Secret/hpdc-edge-tls` in the HTTPS listener (`certificateRefs: [hpdc-edge-tls]`); the new step must produce this secret before EG can become `Programmed=True`
- `scripts/gitops/install-envoy-gateway-dev.py` -- existing gitops installer pattern (`--check`/`--dry-run`/`--apply`, `component_versions.get(...)`, `from _provisioned import require`); the new `gen-edge-cert.py` follows this pattern
- `scripts/steps/17-install-cert-manager-dev.py` -- the step-wrapper pattern being replaced (thin wrapper calling the gitops script)
- `scripts/steps/01.5-configure-firewalld-talos.py` -- intermediate-step naming + mode-handling pattern (04.5 will follow this)
- `scripts/startup.dev.py:38-71` -- `STEP_TOGGLE_MAP` dict; needs a new `"04.5-gen-edge-cert"` entry (gated on `ENVOY_GATEWAY_ENABLED`, same as EG)
- `scripts/startup.dev.py:89-101` -- `_is_step_number()` regex `\d{1,2}(\.\d)?` already accepts `04.5` format; `step_label()` renders `04.5` → `"04.5"`
- `scripts/startup.dev.py:269-276` -- `discover_steps()` auto-discovers `*.py` in `scripts/steps/`, so no change needed there
- `.env.components` / `.env.components.example` -- `HPDC_ENVOY_GATEWAY_ENABLED=true`; the STEP_TOGGLE_MAP uses the unprefixed `ENVOY_GATEWAY_ENABLED` key
- `docs/cert-manager-tls-termination.md` -- existing TLS doc (being replaced by `docs/static-tls-termination.md` in Story 1.5.3); the new gen script references `docs/static-tls-termination.md` which will exist after 1.5.3 — note as forward-dependency
- `scripts/component_versions.py` -- `load_all_dotenv()` pattern (all scripts call this)

## Tasks & Acceptance

**Execution:**
- [x] `scripts/gitops/gen-edge-cert.py` -- Create cert-generation + Secret-application gitops script with `--check`/`--dry-run`/`--apply` modes, following the `install-envoy-gateway-dev.py` pattern (imports `component_versions`, `_provisioned.require`, argparse with offline/check/dry-run/apply)
- [x] `scripts/steps/04.5-gen-edge-cert.py` -- Create thin step wrapper calling `scripts/gitops/gen-edge-cert.py` with the same `--check`/`--dry-run`/`--apply` interface, following the `17-install-cert-manager-dev.py` pattern
- [x] `scripts/startup.dev.py:42` -- Add `"04.5-gen-edge-cert": ["ENVOY_GATEWAY_ENABLED"]` to `STEP_TOGGLE_MAP` (same toggle as EG step 16)
- [x] `.gitignore` -- Verified cert path resolves outside repo root (no entry needed)

**Acceptance Criteria:**
- Given the offline Talos dev cluster from Story 1.2 is healthy, when the cert generation script runs, then it checks if `~/.hpdc/certs/tls.crt` and `~/.hpdc/certs/tls.key` already exist
- Given the certificates exist and are valid, when the script runs, then it skips generation and reports "cert already present"
- Given the certificates do not exist, when the script runs, then it generates a self-signed X.509 certificate with CN=`*.hpdc.local`, SAN=`DNS:*.hpdc.local`, RSA 2048-bit, 3650-day validity
- Given generation succeeds, when the script finishes, then the cert and key are stored at `~/.hpdc/certs/tls.crt` and `~/.hpdc/certs/tls.key` and are NOT committed to git
- Given the cert exists, when the script runs with `--apply`, then it ensures namespace `envoy-gateway-system` exists and creates `Secret/hpdc-edge-tls` of type `kubernetes.io/tls` from the cert and key
- Given any failure occurs, when the script exits, then it exits with a non-zero status code
- Given the process runs, then it completes without internet access

## Spec Change Log

## Review Triage Log

### 2026-09-02 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 18: (critical 2, high 3, medium 10, low 3)
- defer: 15: (medium 1, low 14)
- reject: 2: (high 1, medium 1)
- addressed_findings:
  - [critical] [patch] A1+A2: Fixed `_has_kubectl_cluster()` — removed invalid `--retries=0` flag (kubectl rejects unknown flags), switched from `kubectl cluster-info` (exits 0 even when unreachable) to `kubectl get --raw=/livez --request-timeout=5s` for a true API-server reachability check
  - [high] [patch] A3+A4: Added `_check_tools()` using `shutil.which()` to verify `openssl` and `kubectl` are on PATH before any work; prevents uncaught `FileNotFoundError` traceback
  - [high] [patch] A5: Broadened `_prep()` exception handling from `RuntimeError` to `Exception` to catch `yaml.YAMLError` (from `_provisioned.require()` reading `provisioned.yaml`)
  - [medium] [patch] A6: Added `errors="replace"` to `ENVOY_MANIFEST.read_text()` and broadened exception handling in `validate_manifests()` to catch `UnicodeDecodeError`
  - [medium] [patch] A8: Added top-level `try/except Exception` in `main()` that prints a clean error and returns exit 1 instead of a raw traceback
  - [medium] [patch] A9: Added `_secret_matches_disk()` content validation; `ensure_secret()` now detects when an existing Secret's cert/key differs from on-disk files (cert/key drift) and recreates it
  - [medium] [patch] A10: Added `--force` flag allowing regeneration of invalid certs without manual file deletion
  - [medium] [patch] A11: `_generate_cert()` now re-runs `_validate_cert_pair()` after generation and checks file sizes are non-zero before proceeding to cluster operations
  - [medium] [patch] A12: `CERT_DIR.mkdir()` now catches `FileExistsError`/`PermissionError` with a clean error message
  - [medium] [patch] B1: `check()` returns 0 for "missing" cert state (actionable, not broken) instead of 1 — fixes false failure in startup `--check` flow on fresh setups
  - [medium] [patch] C1: `validate_manifests()` uses regex (`re.search(r'name:\s*["\']?hpdc-edge-tls...')`) instead of naive substring matching, tolerating YAML quoting
  - [medium] [patch] D1: Added `timeout=600` to `subprocess.run()` in the step wrapper
  - [medium] [patch] F3: Added `_cluster_error_detail()` helper that inspects kubectl stderr/stdout for auth ("Unauthorized"/"Forbidden") vs connectivity ("connection refused"/"timeout") patterns, enabling `ensure_namespace()` and `_secret_exists()` to distinguish "not found" from "auth/cluster-down"
  - [low] [patch] A13: Added non-empty file size check (`st_size == 0`) after cert generation
  - [low] [patch] A14: Changed `_cert_present()` from `.exists()` to `.is_file()` to avoid matching directories
  - [low] [patch] A19: Added `errors="replace"` to `_run()` subprocess calls to handle non-UTF-8 output from openssl/kubectl

## Design Notes

- The `~/.hpdc/` directory was already established as the cert storage location by the story spec — this is an intentional deviation from the repo-rooted `output/` convention because certs must never be committed.
- openssl command: `openssl req -x509 -newkey rsa:2048 -keyout tls.key -out tls.crt -days 3650 -nodes -subj "/CN=*.hpdc.local" -addext "subjectAltName=DNS:*.hpdc.local"` — the `-nodes` flag means no passphrase (required for automated cluster bootstrap).
- The step is numbered `04.5` because it sits between Cilium (04) and Storage (05) — it must run before EG install (which is moving to ~04.6 per Story 1.5.2). The `.5` intermediate-step convention is already established by `01.5-configure-firewalld-talos.py`.
- `ENVOY_GATEWAY_ENABLED` is the correct toggle because the cert's sole consumer is EG's HTTPS listener; if EG is disabled, cert generation is unnecessary.

## Verification

**Commands:**
- `python3 scripts/gitops/gen-edge-cert.py --check` -- expected: exit 0 if cert present & valid; exit 1 with reason if missing/invalid
- `python3 scripts/steps/04.5-gen-edge-cert.py --check` -- expected: delegates to gitops script; exit 0 if healthy
- `openssl x509 -in ~/.hpdc/certs/tls.crt -noout -subject -enddate` -- expected: `subject=CN=*.hpdc.local`, enddate ~10 years out
- `git check-ignore -v ~/.hpdc/certs/tls.crt` or `git status --porcelain --ignored` -- expected: cert/key path is ignored (or outside repo)
- `grep "04.5-gen-edge-cert" scripts/startup.dev.py` -- expected: present in STEP_TOGGLE_MAP
