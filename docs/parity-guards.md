# Parity Guards — Cross-System Config Equality

**Owner:** Epic 2 (Registry origin). Canonical template for every "one fact, two
representations" guard in HPDC. Apply to any shared config that exists in more
than one representation (kustomize tree, installer script, fixtures, docs).

## Pattern

When a single fact must exist in two representations, assert parsed equality,
not substring equality. Guard both the writer (installer) and the source of truth.

## Canonical Example — Registry values (parsed-equality drift guard)

- Source of truth: `gitops/registry/base/registry.yaml`
- Embed: `gitops/registry/base/registry.yaml` → `ConfigMap registry-values` →
  `data["registry-values.yaml"]`
- Guard:
  - To be implemented for registry configuration
- Anti-pattern it blocks: overlay listing values as a kustomize resource.

## Apply to Any Shared Config

1. Identify the single source of truth.
2. Identify every second representation (embed, fixture, installer literal).
3. Add a parsed-equality assertion in the test AND the writer/installer.
4. Add an absence guard where applicable (see FR-34 no-replication guard in
   `tests/test_install_regional_sovereignty_dev.py`).

## Existing Guards

- Registry values embed == source (Epic 2 origin; template above).
- Identity fixtures vs api-key manifest: `tests/atdd/support/fixtures.py`
  `_api_key_manifest_parity_check` (Epic 9/10, agent-engine shared config).
- Agent-engine (Epic 9, #7): kustomize-to-installer agreement — the
  `install-a2a-dev.py` / `install-mcp-tools-dev.py` installers assert the
  required kinds/fields they consume exist in the tree (`gitops/agent-engine/base/`
  `a2a.yaml`, `mcp-tools.yaml`; platform-scaffold `mcp-tools` contract).
  Currently presence-checked per the template's Step 3; upgrade to parsed-equality
  the moment a shared fact (e.g. a tool-definition list) is embedded in a second
  representation.
