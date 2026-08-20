# Parity Guards — Cross-System Config Equality

**Owner:** Epic 2 (Harbor origin). Canonical template for every "one fact, two
representations" guard in HPDC. Apply to any shared config that exists in more
than one representation (kustomize tree, installer script, fixtures, docs).

## Pattern

When a single fact must exist in two representations, assert parsed equality,
not substring equality. Guard both the writer (installer) and the source of truth.

## Canonical Example — Harbor values (parsed-equality drift guard)

- Source of truth: `gitops/harbor/base/harbor-values.yaml`
- Embed: `gitops/harbor/base/harbor.yaml` → `ConfigMap harbor-values` →
  `data["harbor-values.yaml"]`
- Guard:
  - `tests/test_install_harbor_dev.py:59`
    `yaml.safe_load(embed["data"]["harbor-values.yaml"]) == yaml.safe_load(values)`
  - `scripts/gitops/install_harbor_dev.py:111` (installer-side, same assertion)
- Anti-pattern it blocks: overlay listing `harbor-values.yaml` as a kustomize
  resource (values treated as a deployable rather than an embed source).

## Apply to Any Shared Config

1. Identify the single source of truth.
2. Identify every second representation (embed, fixture, installer literal).
3. Add a parsed-equality assertion in the test AND the writer/installer.
4. Add an absence guard where applicable (see FR-34 no-replication guard in
   `tests/test_install_regional_sovereignty_dev.py`).

## Existing Guards

- Harbor values embed == source (Epic 2 origin; template above).
- Identity fixtures vs api-key manifest: `tests/atdd/support/fixtures.py`
  `_api_key_manifest_parity_check` (Epic 9/10, agent-engine shared config).
- Agent-engine (Epic 9, #7): kustomize-to-installer agreement — the
  `install-a2a-dev.py` / `install-mcp-tools-dev.py` installers assert the
  required kinds/fields they consume exist in the tree (`gitops/agent-engine/base/`
  `a2a.yaml`, `mcp-tools.yaml`; platform-scaffold `mcp-tools` contract).
  Currently presence-checked per the template's Step 3; upgrade to parsed-equality
  the moment a shared fact (e.g. a tool-definition list) is embedded in a second
  representation.
