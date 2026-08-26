---
story_key: 11-6-tighten-hpdc-crd-schemas
epic: 11
status: backlog
baseline_commit: TBD
completion_commit: TBD
---

# Story 11.6: Tighten hpdc.io CRD Schemas

## Story

As a Platform Engineer,
I want the 25 placeholder `hpdc.io/v1` CRDs replaced with validated openAPIV3Schema definitions,
So that controllers, admission validation, and tooling can safely rely on the custom resource contracts.

## Acceptance Criteria

**Given** `gitops/crds/hpdc/hpdc-crds.yaml` currently declares 25 kinds with preserve-unknown-fields placeholder schemas
**When** each kind's schema is authored against its intended design
**Then** every kind has a real openAPIV3Schema (required fields, types, constraints) — no preserve-unknown-fields placeholders remain except where intentionally justified and documented

**Given** the tightened schemas are committed
**When** validation runs
**Then** all existing manifest usages validate cleanly (server-side dry-run or kubeconform)
**And** the crds-hpdc Application syncs without regression across the App-of-Apps tree

## Tasks / Subtasks

- [ ] Task 1: Inventory kinds and intended designs (AC: #1)
  - [ ] Map each of the 25 kinds to its source manifests and consuming components
  - [ ] Flag kinds whose intended design is unclear → route to architecture review before authoring
- [ ] Task 2: Author schemas per kind (AC: #1)
  - [ ] Required fields, property types, enums/constraints per intended semantics
  - [ ] Document any intentionally permissive schema with a YAML comment justification
- [ ] Task 3: Validate (AC: #2)
  - [ ] Dry-run apply existing usages against new schemas; fix schema or manifest mismatches
  - [ ] Regenerate rendered artifacts if needed; commit; refresh mirror; sync crds-hpdc
- [ ] Task 4: Regression check (AC: #2)
  - [ ] Full `kubectl get pods -A` + ArgoCD app health unchanged post-sync
  - [ ] Update sprint-status.yaml: 11-6 done

## Dev Notes

- Origin: NEXT.md §A.3 follow-up-story candidate (2026-08-24 session) — schemas were generated from kinds used across manifests as minimal placeholders purely to let App-of-Apps children sync.
- Sequencing: run AFTER 11-5 (convergence) and AFTER 11-4 (live verification) — nothing in verification depends on strict schemas; tightening earlier would churn a moving tree.
- Reference `output/planning-artifacts/architecture/architecture-HPDC-2026-07-30/SOLUTION-DESIGN.md` for intended resource semantics where documented.
- Keep bundle structure: single `gitops/crds/hpdc/hpdc-crds.yaml` consumed by the wave-0 crds-hpdc child Application.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
