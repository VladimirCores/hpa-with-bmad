---
title: Update Docs and README for Static Cert and Production Requirements
type: feature
created: '2026-09-02'
status: done
baseline_revision: 6a39bfe8193b2eb3013e1df4d0fa92eb2f191049
final_revision: 9d451539b6acdf34ea5333917ffeae17b8984c99
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** The documentation still references cert-manager as the active TLS mechanism for the dev cluster, but cert-manager has been removed from the core layer and replaced by a static self-signed wildcard certificate (Story 15-1). The README and docs contain stale information that contradicts the actual implementation.

**Approach:** Update documentation to reflect the current state: dev uses static self-signed certs via `gen-edge-cert.py`, production requires cert-manager or external CA. Create `docs/static-tls-termination.md` to document the static cert approach, update `README.md` to remove cert-manager as a core dependency, and ensure no stale cert-manager references remain in core-layer documentation.

## Boundaries & Constraints

**Always:** Documentation must accurately reflect the current implementation; dev TLS uses static self-signed certs via `gen-edge-cert.py`; production TLS requires cert-manager or external CA (not implemented); all cert-manager references in core-layer docs must be removed; `docs/static-tls-termination.md` must exist and be accurate.

**Block If:** The `gen-edge-cert.py` script or its step wrapper `04.5-gen-edge-cert.py` are missing or non-functional — documentation cannot be written without a working implementation to document.

**Never:** Implement cert-manager for production (that's a separate epic); modify the cert generation scripts themselves; remove cert-manager GitOps manifests or env toggles (those are for future production use); add documentation about domain routes or authN/authZ wiring (Epic 3 scope).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dev cluster setup | Fresh clone, no certs | `docs/static-tls-termination.md` explains cert generation flow, README reflects static cert approach | Documentation is accurate and complete |
| Production deployment | Real domain, CA-signed certs needed | README documents production cert requirements, `docs/static-tls-termination.md` has production section | Clear guidance on what production needs |
| Stale cert-manager references | Existing docs mention cert-manager | All core-layer cert-manager references removed or updated | No confusion about which approach is active |

</intent-contract>

## Code Map

- `README.md` -- Main project README; needs TLS note update (line 353) and production considerations section
- `docs/cert-manager-tls-termination.md` -- Stale cert-manager documentation; rewrite as `docs/static-tls-termination.md` or update in-place
- `docs/access-tool-uis-guide.md` -- References cert-manager for TLS (lines 8, 71); needs update to static cert
- `docs/envoy-gateway-edge-routing.md` -- Could reference cert generation step; optional enhancement
- `scripts/gitops/gen-edge-cert.py` -- The actual cert generation logic; documentation must match this implementation
- `scripts/steps/04.5-gen-edge-cert.py` -- Step wrapper; documentation should reference this step
- `scripts/gitops/install-envoy-gateway-dev.py` -- EG installer; documentation should note cert prerequisite

## Tasks & Acceptance

**Execution:**
- [x] `docs/static-tls-termination.md` -- Create new file documenting: static cert generation via `gen-edge-cert.py`, cert parameters (CN=*.hpdc.local, SAN=DNS:*.hpdc.local, RSA-2048, 3650-day validity), storage location (`~/.hpdc/certs/`), Kubernetes Secret creation (`hpdc-edge-tls` in `envoy-gateway-system`), idempotency behavior, and production requirements section
- [x] `docs/cert-manager-tls-termination.md` -- Delete or redirect to `docs/static-tls-termination.md` (this file is stale and describes cert-manager as active)
- [x] `README.md` -- Update TLS note (line 353) to describe static self-signed cert approach; add "Production Considerations" section documenting cert-manager or external CA requirements; remove cert-manager as a core-layer dependency
- [x] `docs/access-tool-uis-guide.md` -- Update line 8 to reference static self-signed cert instead of cert-manager; update line 71 GitOps sources table to reference `scripts/gitops/gen-edge-cert.py` instead of cert-manager
- [x] `docs/envoy-gateway-edge-routing.md` -- Optional: add note about cert generation step 04.5 in the boot sequence

**Acceptance Criteria:**
- Given the dev cluster uses static self-signed certs, when `docs/static-tls-termination.md` is read, then it accurately describes the cert generation flow, parameters, storage, and production requirements
- Given cert-manager is removed from the core layer, when core-layer documentation is read, then no references to cert-manager as the active TLS mechanism remain
- Given the README is updated, when a new user reads it, then they understand dev uses static self-signed certs and production requires cert-manager or external CA
- Given `docs/access-tool-uis-guide.md` is updated, when a user reads it, then TLS is correctly attributed to static self-signed certs, not cert-manager
- Given documentation is complete, when `gen-edge-cert.py` is referenced, then the documentation matches the actual implementation (CN, SAN, validity, key type, storage location)

## Spec Change Log

## Review Triage Log

### 2026-09-02 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 13: (medium 8, low 5)
- defer: 8: (medium 5, low 3)
- reject: 2: (medium 2)
- addressed_findings:
  - [medium] [patch] Deleted file without deprecation notice — add redirect note to `docs/static-tls-termination.md` referencing old path
  - [medium] [patch] Production Considerations section could be clearer — reword to explicitly state "not implemented" before listing options
  - [medium] [patch] Idempotency behavior unclear on what "invalid" means — expand definition to include expired, wrong CN/SAN, key mismatch
  - [medium] [patch] Storage location assumes directory exists — add note about directory creation and permissions
  - [medium] [patch] Unclear if cert-manager still installed — add clarification that cert-manager remains available for other purposes
  - [medium] [patch] --check mode unclear on what it checks — expand to list validity period, CN/SAN match, key type
  - [medium] [patch] No mode flag behavior undefined — document default behavior when no mode flag passed
  - [medium] [patch] Cert expires silently — add warning about setting calendar reminder or cron
  - [low] [patch] ~/.hpdc/certs/ unwritable — add note about ensuring directory exists and is writable
  - [low] [patch] .gitignore doesn't cover ~/.hpdc/ — add note about adding to .gitignore
  - [low] [patch] kubectl verify shows secret missing — add troubleshooting note
  - [low] [patch] External references to deleted doc — search codebase for references
  - [low] [patch] No CA trust distribution mechanism — add note about distributing CA cert to developer machines

## Design Notes

- The `docs/static-tls-termination.md` file should follow the same structure as the existing `docs/cert-manager-tls-termination.md` but with updated content reflecting the static cert approach
- Production requirements should be documented but not implemented — this is a documentation-only story
- The cert-manager GitOps manifests and env toggles remain in the codebase for future production use; documentation should clarify this distinction

## Verification

**Commands:**
- `grep -r "cert-manager" docs/ README.md` -- expected: no references to cert-manager as active TLS mechanism in core-layer docs
- `grep -r "static" docs/static-tls-termination.md` -- expected: references to static self-signed cert approach
- `grep -r "gen-edge-cert" docs/ README.md` -- expected: references to cert generation script
- `ls docs/static-tls-termination.md` -- expected: file exists

**Manual checks (if no CLI):**
- Verify `docs/static-tls-termination.md` accurately describes the cert generation flow
- Verify README.md correctly distinguishes dev vs. production TLS approaches
- Verify no stale cert-manager references remain in core-layer documentation

## Auto Run Result

Status: done

Updated documentation to reflect the static self-signed cert approach for dev TLS. Created `docs/static-tls-termination.md` with cert parameters, storage, idempotency, and production requirements. Deleted stale `docs/cert-manager-tls-termination.md`. Updated `README.md` with Production Considerations section. Updated `docs/access-tool-uis-guide.md` and `docs/envoy-gateway-edge-routing.md` to reference static cert approach. All cert-manager references in core-layer docs now correctly describe production requirements rather than active dev mechanism.

## Review Triage Summary

- **13 patches applied**: Added deprecation notice, expanded idempotency definition, added cert expiry warning, documented directory creation, clarified cert-manager availability, expanded --check mode, documented default mode, added Secret reload note, added troubleshooting guidance, added CA trust distribution, and more
- **8 items deferred**: Script-level issues (concurrent invocations, namespace creation, cluster reachability, --force in production, boot sequence failure handling) and out-of-scope items (CA trust distribution mechanism, ENVOY_GATEWAY_ENABLED behavior)
- **2 items rejected**: Production requirements hand-wave (correctly documented as not implemented), missing relationship between cert script and Cilium (clear from boot sequence)
- **Follow-up review recommended**: false — all patches are localized documentation improvements with low behavior/API/security impact
