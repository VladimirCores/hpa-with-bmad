---
title: Move Envoy Gateway Installation to Core Layer
type: feature
created: '2026-09-02'
status: done
baseline_revision: 267c072d
final_revision: 7bbd898
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Envoy Gateway currently installs at step 16 (late in the pipeline), but the core-layer refactor (Epic 1.5) requires it to be available immediately after Cilium so downstream HTTPRoutes (Hubble UI, tool UIs) are attachable right away. The static self-signed TLS cert from Story 15-1 generates the `hpdc-edge-tls` Secret, but the Gateway never installs early enough to use it.

**Approach:** Renumber the Envoy Gateway installer from step 16 to step 04.6 (after Cilium step 04 and cert step 04.5). Add Gateway API CRD application as a prerequisite within the installer. Remove the standalone cert-manager step 17 from the core-layer sequence. Update `startup.dev.py` toggle mapping and step references accordingly.

## Boundaries & Constraints

**Always:** Gateway API CRDs from `gitops/crds/gateway/crds.yaml` must be applied before any Gateway/GatewayClass/HTTPRoute resources; `Gateway/hpdc-edge` must have HTTPS listener on :443 with `certificateRefs: [hpdc-edge-tls]` and TCP listener on :1884 for MQTT; Gateway address must use `${HPDC_GATEWAY_IP}` from Cilium L2 LB pool; Envoy Gateway version pinned at 1.8.3; namespace `envoy-gateway-system`; scripts are Python 3 and exit non-zero on failure; no internet access required; follows the two-file pattern (gitops installer + step wrapper).

**Block If:** Gateway API CRDs at `gitops/crds/gateway/crds.yaml` are missing or empty — the installer cannot proceed without them.

**Never:** Use cert-manager for dev TLS (already replaced by static cert in Story 15-1); apply domain routes or authN/authZ wiring (Epic 3 scope); change the Gateway name `hpdc-edge` or the secret name `hpdc-edge-tls`; modify the envoy-gateway base manifest structure (routes, listeners) beyond what the story requires.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh install, CRDs present | CRDs applied, EG not installed | GatewayClass + Gateway + HTTPRoutes created, Gateway Programmed=True | Exit 1 if kubectl apply fails |
| Idempotent re-run | EG already installed | Reports resources exist, validates Programmed=True | Exit 0 if healthy, exit 1 if stuck |
| CRDs missing | `gitops/crds/gateway/crds.yaml` absent or empty | Block with clear error message | Exit 1 with "Gateway API CRDs not found" |
| TLS secret missing | `hpdc-edge-tls` not in `envoy-gateway-system` | Gateway installs but HTTPS listener won't reach Programmed=True | Exit 1 on validation; warn about missing secret |

</intent-contract>

## Code Map

- `scripts/steps/16-install-envoy-gateway-dev.py` -- current step wrapper being renumbered; thin shell-out to gitops installer
- `scripts/gitops/install-envoy-gateway-dev.py` -- core installer logic: validates manifests, applies Gateway API CRDs + EG resources
- `scripts/startup.dev.py` -- orchestration: STEP_TOGGLE_MAP, discover_steps(), step_mode_args(); needs new 04.6 entry + old 16 entry removed
- `gitops/envoy-gateway/base/envoy-gateway.yaml` -- base manifest: Namespace, SA, RBAC, Deployment, GatewayClass, Gateway, HTTPRoutes
- `gitops/envoy-gateway/overlays/dev/kustomization.yaml` -- dev overlay merging base + telemetry-ingestion
- `gitops/crds/gateway/crds.yaml` -- Gateway API CRDs (20 CRDs, v1.6.1); must be applied before EG resources
- `scripts/steps/04.5-gen-edge-cert.py` -- existing cert step (runs before 04.6); no changes needed
- `scripts/steps/17-install-cert-manager-dev.py` -- cert-manager step to be removed from core sequence
- `.env.components` -- `HPDC_ENVOY_GATEWAY_ENABLED=true` toggle

## Tasks & Acceptance

**Execution:**
- [x] `scripts/gitops/install-envoy-gateway-dev.py` -- Add Gateway API CRD application step using `kubectl apply -f gitops/crds/gateway/crds.yaml` before applying EG resources; add `--apply` mode that actually runs `kubectl apply` (currently only prints "apply requested"); gate CRD application on file existence check
- [x] `scripts/steps/04.6-install-envoy-gateway-dev.py` -- Create new step wrapper at 04.6 (copy pattern from 16-install-envoy-gateway-dev.py, update STEP_NAME/STEP_DESCRIPTION); delete `scripts/steps/16-install-envoy-gateway-dev.py`
- [x] `scripts/startup.dev.py` -- Add `"04.6-install-envoy-gateway-dev": ["ENVOY_GATEWAY_ENABLED"]` to STEP_TOGGLE_MAP; remove `"16-install-envoy-gateway-dev"` entry
- [x] `scripts/steps/17-install-cert-manager-dev.py` -- Delete the step file and remove its STEP_TOGGLE_MAP entry from startup.dev.py so it no longer runs in core sequence

**Acceptance Criteria:**
- Given the TLS secret from Story 1.5.1 exists in `envoy-gateway-system`, when the installer runs, then Gateway API CRDs from `gitops/crds/gateway/crds.yaml` are applied before EG resources
- Given CRDs are applied, when EG resources are applied, then `GatewayClass/hpdc-envoy-gateway` exists and is `Accepted`
- Given GatewayClass is accepted, when Gateway is created, then `Gateway/hpdc-edge` exists with HTTPS listener on :443 (`certificateRefs: [hpdc-edge-tls]`) and TCP listener on :1884 for MQTT
- Given Gateway exists with TLS secret present, when validation runs, then Gateway reports `Programmed=True`
- Given the install completes, when step numbering is verified, then step 04.6 runs after 04.5 (cert) and before 05 (storage)
- Given the install completes, when startup.dev.py is checked, then the old step 16 entry is absent and the new 04.6 entry is present with `ENVOY_GATEWAY_ENABLED` toggle
- Given any failure occurs, when the script exits, then it exits with a non-zero status code
- Given the process runs, then it completes without internet access

## Spec Change Log

## Review Triage Log

### 2026-09-02 — Review pass
- intent_gap: 1: (high 1)
- bad_spec: 0
- patch: 4: (medium 3, low 1)
- defer: 1: (low 1)
- reject: 2: (medium 2)
- addressed_findings:
  - [high] [patch] A1: Deleted `scripts/steps/17-install-cert-manager-dev.py` — removed toggle map entry caused step to run unconditionally (opposite of intent); file deleted
  - [medium] [patch] A2: Added exception handling to `_run()` — catches `FileNotFoundError` (kubectl not on PATH), `TimeoutExpired` (600s limit), `UnicodeDecodeError` (non-UTF-8 output) with clean error messages
  - [medium] [patch] A3: Added CRD establishment wait — `kubectl wait --for condition=Established` with 120s timeout after CRD apply, preventing race condition where EG resources apply before CRDs are ready
  - [medium] [patch] A4: Added stderr logging on successful applies — kubectl warnings (deprecation notices, CRD upgrade info) now visible in output instead of silently discarded
  - [low] [defer] D1: Idempotency guard for CRD re-apply — deferred; kubectl apply is inherently idempotent, version-check gate is a hardening concern for future EG upgrades

## Design Notes

- Step 04.6 follows the intermediate-step naming convention established by 01.5 (firewalld) and 04.5 (cert gen). The `.6` suffix places it immediately after cert generation (04.5) and before storage (05).
- The Gateway API CRD application is folded into the EG installer rather than a separate step because: (a) CRDs are a prerequisite only for EG, (b) a separate step would add orchestration complexity without benefit, (c) the installer already validates manifests — it should also ensure prerequisites are met.
- The `--apply` mode in the current gitops installer only prints "apply requested" without actually running kubectl. This story makes it functional by adding `subprocess.run(["kubectl", "apply", "-f", ...])` calls, following the pattern from `gen-edge-cert.py` (Story 15-1).
- cert-manager step 17 was deleted during review (file + STEP_TOGGLE_MAP entry removed). Production users who need cert-manager can restore the step file from git history or recreate it manually.

## Verification

**Commands:**
- `python3 scripts/gitops/install-envoy-gateway-dev.py --check` -- expected: exit 0 if CRDs present and manifests valid
- `python3 scripts/steps/04.6-install-envoy-gateway-dev.py --check` -- expected: exit 0, delegates to gitops installer
- `grep "04.6-install-envoy-gateway-dev" scripts/startup.dev.py` -- expected: present in STEP_TOGGLE_MAP
- `grep -c "16-install-envoy-gateway-dev" scripts/startup.dev.py` -- expected: 0 (removed)
- `ls scripts/steps/16-install-envoy-gateway-dev.py 2>&1` -- expected: "No such file" (deleted)
- `grep "17-install-cert-manager-dev" scripts/startup.dev.py` -- expected: absent from STEP_TOGGLE_MAP

**Manual checks (if no CLI):**
- Verify step ordering in `discover_steps()` output: 04.5 < 04.6 < 05
- Verify `Gateway/hpdc-edge` has `Programmed=True` condition when TLS secret exists

## Auto Run Result

Status: done

Moved Envoy Gateway installation from step 16 to step 04.6 in the core layer (after Cilium + cert, before storage). Added Gateway API CRD application as a prerequisite in the gitops installer. Made `--apply` mode functional with actual kubectl apply, CRD establishment wait, exception handling, and stderr logging. Deleted cert-manager step 17 from the core sequence (file + toggle map). Updated `startup.dev.py` STEP_TOGGLE_MAP. 6 files changed across 2 commits.
