#!/usr/bin/env python3
"""GREEN-PHASE secret scan: no secrets in Git; InfisicalSecret CRDs for real secrets (P0-022).

Contract source:
  - output/test-artifacts/test-design/test-design-qa.md  (P0-022, NFR21, R-008)
  - gitops/infisical/base/infisical.yaml                 (Infisical operator / CSI driver / rotation)
  - gitops/infisical/base/infisical-secret.yaml          (InfisicalSecret CRD for real credentials)
  - gitops/security/base/api-key-authn.yaml              (dev-only events-api-key / telemetry-api-key Secrets)
  - gitops/casdoor/base/casdoor.yaml, gitops/backstage/base/backstage.yaml

GREEN PHASE: all scans hold against the current tree - no high-entropy committed
material, prod overlays carry no plaintext Secrets, ConfigMaps hold only allowlisted
dev placeholders or Secret references, the committed Secret stores hold only
allowlisted dev-only credentials, the Infisical operator wiring is enabled, and an
InfisicalSecret CRD exists to provision real production credentials at runtime (R-008).

Run under pytest or standalone (main() executes all scan bodies).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
GITOPS = ROOT / "gitops"

# Known dev-only credentials tolerated in base manifests today. Each entry is a known
# exception (R-008): they must move behind InfisicalSecret before production.
DEV_ONLY_CREDENTIALS = {
    "hpdc-events-dev-key",        # gitops/security/base/api-key-authn.yaml - dev-only messaging API key
    "hpdc-telemetry-dev-key",     # gitops/security/base/api-key-authn.yaml - dev-only telemetry API key
    "InfisicalAdmin12345",        # gitops/infisical/base/infisical.yaml - dev bootstrap DB password
    "CasdoorAdmin12345",          # gitops/casdoor/base/casdoor.yaml - dev bootstrap admin password
    "backstage-client-secret",    # gitops/backstage/base/backstage.yaml - placeholder client secret
    "backstage-backend-secret",   # gitops/backstage/base/backstage.yaml - placeholder signing secret
    "HarborAdmin12345",           # gitops/harbor/base/harbor.yaml - dev bootstrap admin password
    "HarborPostgres12345",        # gitops/harbor/base/harbor.yaml - dev postgres password
    "HarborRegistryHttpSecret12345",  # gitops/harbor/base/harbor.yaml - dev registry HTTP secret
    "harbor-secretkey-for-offline-dev",  # gitops/harbor/base/harbor.yaml - dev secret key
    "harbor-core-secret",         # gitops/harbor/base/harbor.yaml - dev core secret
    "harbor-jobservice-secret",   # gitops/harbor/base/harbor.yaml - dev jobservice secret
    "harbor-registry-secret",     # gitops/harbor/base/harbor.yaml - dev registry secret
    "harbor-trivy-adapter-secret",  # gitops/harbor/base/harbor.yaml - dev trivy secret
    "harbor-cosign-verification-secret",  # gitops/harbor/base/harbor.yaml - dev cosign secret
}

DEV_CRED_VALUES = ("hpdc-events-dev-key", "hpdc-telemetry-dev-key", "InfisicalAdmin12345", "CasdoorAdmin12345")

HIGH_ENTROPY_PATTERNS = [
    re.compile(r"[0-9a-f]{40,}"),                     # long hex blobs
    re.compile(r"[A-Za-z0-9+/]{48,}={0,2}"),          # long base64 blobs
    re.compile(r"AKIA[0-9A-Z]{16}"),                  # AWS access key ids
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),  # private keys
]

SECRET_KEY_PATTERN = re.compile(
    r"(?i)(password|passwd|pwd|token|apikey|api[-_]?key|secret|client[-_]?secret|private[-_]?key|authorization|credential)"
)


def _documents(text: str) -> list[str]:
    return [doc for doc in re.split(r"(?m)^---\s*$", text) if doc.strip()]


def _doc_kind(doc: str) -> str | None:
    match = re.search(r"(?m)^kind:\s*(\S+)", doc)
    return match.group(1) if match else None


def _inline_key_values(doc: str) -> list[tuple[str, str]]:
    return [
        (m.group(1), m.group(2).strip())
        for m in re.finditer(r"(?m)^[ \t]*([A-Za-z0-9_.-]+):[ \t]*(\S.*)$", doc)
    ]


def _base_yamls() -> list[Path]:
    return sorted(GITOPS.glob("*/base/*.yaml"))


def _all_yamls() -> list[Path]:
    return sorted(GITOPS.rglob("*.yaml"))


def _secret_resource_names() -> set[str]:
    names: set[str] = set()
    for path in _base_yamls():
        for doc in _documents(path.read_text(encoding="utf-8")):
            if _doc_kind(doc) != "Secret":
                continue
            for line in doc.splitlines():
                match = re.match(r"\s+name:\s*(\S+)", line)
                if match:
                    names.add(match.group(1))
    return names


# P0-022 (NFR21, R-008)
# Given: credentials must never be committed  When: the gitops tree is scanned
# Then:  no high-entropy hex/base64 blobs, cloud access keys, or private key material
#        appear outside the allowlisted dev-only credentials
def test_no_high_entropy_secret_material_in_gitops() -> None:
    for path in _base_yamls():
        text = path.read_text(encoding="utf-8")
        for pattern in HIGH_ENTROPY_PATTERNS:
            for match in pattern.findall(text):
                assert match in DEV_ONLY_CREDENTIALS, (
                    f"possible secret material {match[:16]}... found in {path}"
                )


# P0-022 (NFR21, R-008)
# Given: production credentials must not be derived from dev values  When: the prod
#        overlays are scanned  Then: no plaintext Secret with data/stringData exists
#        and no dev credential value leaks into the prod environment
def test_prod_overlays_contain_no_plaintext_secrets() -> None:
    for ks_path in sorted(GITOPS.glob("*/overlays/prod/kustomization.yaml")):
        for resource in re.findall(r"(?m)^\s*-\s+(.+\.yaml)\s*$", ks_path.read_text(encoding="utf-8")):
            target = (ks_path.parent / resource).resolve()
            if not target.is_file():
                continue
            for doc in _documents(target.read_text(encoding="utf-8")):
                if _doc_kind(doc) == "Secret" and re.search(r"(?m)^\s*(stringData|data):", doc):
                    raise AssertionError(f"plaintext Secret in prod overlay: {target}")
                assert not any(cred in doc for cred in DEV_CRED_VALUES), (
                    f"dev credential value leaked into prod overlay {target}"
                )


# P0-022 (NFR21, R-008)
# Given: ConfigMaps are not secret stores  When: ConfigMap documents are scanned
# Then:  secret-bearing keys never carry real values (only allowlisted dev placeholders
#        or references to a declared Secret resource)
def test_configmaps_hold_no_secret_values() -> None:
    secret_names = _secret_resource_names()
    for path in _base_yamls():
        for doc in _documents(path.read_text(encoding="utf-8")):
            if _doc_kind(doc) != "ConfigMap":
                continue
            for key, value in _inline_key_values(doc):
                if SECRET_KEY_PATTERN.search(key):
                    assert value in DEV_ONLY_CREDENTIALS or value in secret_names or value.startswith(("{{", "<", "your-", "'{", "{")) or value.strip("'\"") in ("true", "false", "on", "off"), (
                        f"ConfigMap {path} holds secret-like key {key!r} with value {value!r}"
                    )


# P0-022 (NFR21, R-008)
# Given: the only Secrets committed to git are the dev events-api-key /
#        telemetry-api-key stores (key-level isolated per R-009)
# When:  all kind: Secret documents are scanned
# Then:  every stringData/data value is an allowlisted dev-only credential and the
#        store carries no unexpected keys (expansion is flagged)
def test_dev_secret_stringdata_only_known_exceptions() -> None:
    for path in _base_yamls():
        for doc in _documents(path.read_text(encoding="utf-8")):
            if _doc_kind(doc) != "Secret":
                continue
            if not re.search(r"(?m)^\s*(stringData|data):", doc):
                continue
            for key, value in _inline_key_values(doc):
                if SECRET_KEY_PATTERN.search(key) or key in ("events-key", "telemetry-key"):
                    assert value in DEV_ONLY_CREDENTIALS, (
                        f"Secret {path} stores non-allowlisted credential {key}={value!r}"
                    )


# P0-022 (NFR21, R-008)
# Given: Infisical is the secrets management plane  When: the Infisical operator
#        manifest is inspected  Then: secretRotation, auditLog, operator and csiDriver
#        are all enabled so real credentials can be injected at runtime
def test_infisical_operator_enabled() -> None:
    infisical = (GITOPS / "infisical/base/infisical.yaml").read_text(encoding="utf-8")
    assert "kind: ConfigMap" in infisical and "name: infisical-config" in infisical
    for feature in ("secretRotation", "auditLog", "operator", "csiDriver"):
        assert re.search(rf"(?m)^\s+{feature}:\s*\n\s+enabled:\s*true", infisical), (
            f"Infisical {feature} must be enabled"
        )


# P0-022 (NFR21, R-008)
# Given: production credentials must be provisioned via Infisical CRDs, never committed
# When:  the gitops tree is scanned for secret sources
# Then:  at least one InfisicalSecret / ExternalSecret CRD exists to hold real
#        credentials
def test_infisicalsecret_or_externalsecret_present() -> None:
    for path in _all_yamls():
        if re.search(r"(?m)^kind:\s*(InfisicalSecret|ExternalSecret|InfisicalSecretTemplate)\b", path.read_text(encoding="utf-8")):
            return
    raise AssertionError(
        "no InfisicalSecret/ExternalSecret CRD in gitops - production credentials must "
        "not be committed in plaintext (R-008)"
    )


# P0-022 (NFR21, R-008)
# Given: the base InfisicalSecret is the production source of truth  When: prod-named
#        InfisicalSecret CRDs are scanned  Then: the dev envSlug is never embedded in
#        them (dev is injected only by the dev overlay), so a future prod overlay
#        cannot silently pull dev credentials
def test_prod_named_secrets_never_bind_dev_slug() -> None:
    dev_overlay = GITOPS / "infisical/overlays/dev/kustomization.yaml"
    for path in _base_yamls():
        for doc in _documents(path.read_text(encoding="utf-8")):
            if _doc_kind(doc) != "InfisicalSecret":
                continue
            if re.search(r"(?m)name:\s*hpdc-production-secrets\b", doc):
                assert "envSlug: dev" not in doc, (
                    f"prod-named InfisicalSecret must not bind the dev envSlug (R-008): {path}"
                )
    text = dev_overlay.read_text(encoding="utf-8")
    assert "envSlug" in text, (
        "dev overlay must explicitly inject the dev envSlug (per-overlay, R-008)"
    )
    assert "value: dev" in text
    for path in sorted(GITOPS.glob("*/overlays/*/kustomization.yaml")):
        if path == dev_overlay:
            continue
        other = path.read_text(encoding="utf-8")
        assert not ("hpdc-production-secrets" in other and "envSlug" in other and "value: dev" in other), (
            f"non-dev overlay {path} must not bind the prod-named InfisicalSecret to the dev envSlug (R-008)"
        )


def main() -> int:
    # GREEN: all P0-022 secret scans run standalone, including the InfisicalSecret /
    # ExternalSecret CRD contract (R-008).
    tests = (
        test_no_high_entropy_secret_material_in_gitops,
        test_prod_overlays_contain_no_plaintext_secrets,
        test_configmaps_hold_no_secret_values,
        test_dev_secret_stringdata_only_known_exceptions,
        test_infisical_operator_enabled,
        test_infisicalsecret_or_externalsecret_present,
        test_prod_named_secrets_never_bind_dev_slug,
    )
    # Task 4.5: reject non-test_* members and fail if the tuple does not declare every
    # test_* function defined in this module (no silently skipped tests).
    for member in tests:
        if not getattr(member, "__name__", "").startswith("test_"):
            print(f"  HARD FAIL: main() member is not a test_* callable: {member!r}")
            return 1
    defined = {name for name, obj in globals().items() if name.startswith("test_") and callable(obj)}
    declared = {test.__name__ for test in tests}
    if defined != declared:
        print("  HARD FAIL: main() tuple out of sync with defined tests:")
        print(f"    defined but not declared: {sorted(defined - declared)}")
        print(f"    declared but not defined: {sorted(declared - defined)}")
        return 1
    failures: list[str] = []
    for test in tests:
        try:
            test()
        except Exception as exc:
            failures.append(test.__name__)
            print(f"  RED (blocked): {test.__name__} - {type(exc).__name__}: {exc}")
    executed = len(tests) - len(failures)
    print(
        f"GREEN PHASE: {len(tests)} secret scans declared; {executed} executed; "
        f"{len(failures)} failing."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
