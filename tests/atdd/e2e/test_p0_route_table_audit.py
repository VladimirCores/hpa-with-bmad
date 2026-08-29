#!/usr/bin/env python3
"""GREEN-PHASE route-table audit: every HTTPRoute in the gitops tree has a SecurityPolicy (P0-016).

Contract source:
  - output/test-artifacts/test-design/test-design-qa.md  (P0-016, FR-38, R-001, R-002, R-009)
  - gitops/envoy-gateway/base/envoy-gateway.yaml         (hpdc-edge Gateway + hpdc-edge-domain-routes)
  - gitops/security/base/api-key-authn.yaml              (api-key SecurityPolicies + split key stores)
  - gitops/security/base/graphql-gateway-authn.yaml      (JWT policy for hpdc-graphql-gateway)
  - gitops/security/base/telemetry-http-api-key-authn.yaml (api-key policy for hpdc-telemetry-http-ingestion)
  - gitops/telemetry-ingestion/base/telemetry-ingestion.yaml
  - gitops/entity-store/base/graphql-gateway.yaml
  - gitops/observability/base/envoy-ui-routes.yaml       (UI routes, native-auth annotations)
  - gitops/tool-ui/base/tool-ui-routes.yaml              (UI routes, native-auth annotations)

GREEN PHASE: every HTTPRoute/GRPCRoute is covered - messaging/telemetry routes carry
explicit api-key SecurityPolicies against key-isolated stores, hpdc-graphql-gateway
carries a JWT SecurityPolicy, and UI routes are authenticated by the gateway
native-auth annotation (documented tolerance, gated to the string-bool "true"/"false").
The casdoor JWKS route is intentionally public (documented tolerance, R-001). Every
overlay kustomization resolves structurally (AC 3), GitOps YAML is valid with
duplicate-key detection, and no route shadowing / dead duplicate matches remain.

Run under pytest or standalone (main() executes all audit bodies).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
GITOPS = ROOT / "gitops"

ROUTE_KINDS = {"HTTPRoute", "GRPCRoute", "TCPRoute"}
SECURITY_POLICY_KIND = "SecurityPolicy"
NATIVE_AUTH_ANNOTATION = "gateway.envoyproxy.io/native-auth"
# Public JWKS discovery endpoint (R-001): must remain unauthenticated so the JWT
# provider's signing keys can be fetched by the graphql gateway policy.
CASDOOR_JWKS_ROUTE = "hpdc-casdoor-jwks"


# YAML loader that rejects duplicate mapping keys instead of safe_load's last-wins
# semantics (AC 7 / Task 4.1).
class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: yaml.SafeLoader, node: yaml.Node, deep: bool = False) -> dict:
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def _load_docs(path: Path) -> list[dict]:
    """Parse a multi-document YAML file, rejecting duplicate mapping keys."""
    return [
        doc
        for doc in yaml.load_all(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
        if doc is not None
    ]


def _gitops_yaml_files() -> list[Path]:
    return sorted(GITOPS.glob("*/base/*.yaml")) + sorted(GITOPS.glob("*/overlays/*/kustomization.yaml"))


def _doc_annotations(doc: str) -> dict[str, str]:
    annotations: dict[str, str] = {}
    in_annotations = False
    for line in doc.splitlines():
        if line.strip() == "annotations:":
            in_annotations = True
            continue
        if in_annotations:
            if line and not line[0].isspace():
                break
            match = re.match(r"\s+([\w./-]+):\s*(.*)", line)
            if match and match.group(1) not in annotations:
                annotations[match.group(1)] = match.group(2).strip().strip("\"'")
    return annotations


def _route_records() -> list[dict]:
    """Structure-aware route collection (Task 4.3): parentRefs, hostnames, path
    matches and backend names come from parsed YAML, not substring scans."""
    records: list[dict] = []
    for path in _gitops_yaml_files():
        for doc in _load_docs(path):
            if doc.get("kind") not in ROUTE_KINDS:
                continue
            meta = doc.get("metadata") or {}
            spec = doc.get("spec") or {}
            annotations = meta.get("annotations") or {}
            native_auth_value = annotations.get(NATIVE_AUTH_ANNOTATION)
            parent_refs: list[dict] = []
            for ref in spec.get("parentRefs") or []:
                parent_refs.append(
                    {
                        "name": ref.get("name"),
                        "namespace": ref.get("namespace"),
                        "sectionName": ref.get("sectionName"),
                    }
                )
            matches: list[tuple[str, str]] = []
            backends: list[str] = []
            for rule in spec.get("rules") or []:
                for match in rule.get("matches") or []:
                    p = match.get("path") or {}
                    matches.append((p.get("type", "PathPrefix"), p.get("value", "")))
                for backend in rule.get("backendRefs") or []:
                    if backend.get("name"):
                        backends.append(backend["name"])
            records.append(
                {
                    "kind": doc["kind"],
                    "name": meta.get("name", ""),
                    "namespace": meta.get("namespace", ""),
                    "file": str(path),
                    "parent_refs": parent_refs,
                    "hostnames": spec.get("hostnames") or [],
                    "matches": matches,
                    "backends": backends,
                    "native_auth_value": native_auth_value,
                    "native_auth": native_auth_value == "true",
                }
            )
    return records


def _policy_records() -> list[dict]:
    """Structure-aware SecurityPolicy collection: targetRefs parsed from YAML.

    EG v1.9 moved from a single `targetRef` to a `targetRefs` list. A targetRef
    without an explicit namespace resolves to the policy's own namespace
    (same-namespace binding); the first targetRef drives the legacy kind/name/
    namespace lookup used by the coverage audits.
    """
    policies: list[dict] = []
    for path in _gitops_yaml_files():
        for doc in _load_docs(path):
            if doc.get("kind") != SECURITY_POLICY_KIND:
                continue
            meta = doc.get("metadata") or {}
            spec = doc.get("spec") or {}
            policy_namespace = meta.get("namespace", "")
            targets = []
            for target in spec.get("targetRefs") or []:
                targets.append(
                    {
                        "group": target.get("group"),
                        "kind": target.get("kind"),
                        "name": target.get("name"),
                        "namespace": target.get("namespace") or policy_namespace,
                    }
                )
            first = targets[0] if targets else {}
            policies.append(
                {
                    "policy_name": meta.get("name", ""),
                    "policy_namespace": policy_namespace,
                    "group": first.get("group"),
                    "kind": first.get("kind"),
                    "name": first.get("name"),
                    "namespace": first.get("namespace"),
                    "targets": targets,
                    "spec": spec,
                    "file": str(path),
                }
            )
    return policies


def _policy_target_routes(policy: dict) -> list[dict]:
    """Resolve a SecurityPolicy's targetRefs to the route records they bind."""
    routes = _route_records()
    resolved = []
    targets = policy.get("targets") or []
    for target in targets:
        for route in routes:
            if (
                route["kind"] == target.get("kind")
                and route["name"] == target.get("name")
                and target.get("namespace") in (route["namespace"], None)
            ):
                resolved.append(route)
    return resolved


def _api_key_paths(policy: dict) -> list[str]:
    """Path prefixes scoped by an apiKeyAuth policy, resolved from its target
    route(s). EG v1.9 moved path scoping out of the SecurityPolicy and into the
    route matches themselves, so the covered paths follow the targetRefs."""
    paths: list[str] = []
    for route in _policy_target_routes(policy):
        for _type, value in route["matches"]:
            if _type == "PathPrefix" and value:
                paths.append(value)
    return sorted(set(paths))


def _api_key_headers(spec: dict) -> list[str]:
    headers: set[str] = set()
    auth = spec.get("apiKeyAuth") or {}
    for extract in auth.get("extractFrom") or []:
        for header in extract.get("headers") or []:
            if header:
                headers.add(header)
    return sorted(headers)


def _api_key_secret_refs(spec: dict) -> list[str]:
    refs: list[str] = []
    auth = spec.get("apiKeyAuth") or {}
    for ref in auth.get("credentialRefs") or []:
        if ref.get("name"):
            refs.append(ref["name"])
    return refs


# P0-016 (FR-38, R-002)
# Given: every gateway route must authenticate  When: the gitops tree is audited
# Then:  every HTTPRoute/GRPCRoute has a SecurityPolicy targetRef matching its
#        name and namespace (no unauthenticated route; R-002)
def test_every_http_grpc_route_has_security_policy() -> None:
    routes = _route_records()
    assert routes, "no routes found in gitops tree"
    policies = _policy_records()
    for route in routes:
        if route["kind"] == "TCPRoute":
            continue  # TCP is terminated at the gateway; SecurityPolicy is HTTP/GRPC scoped
        # Documented tolerances: UI routes (observability/tool-ui/grafana-hubble) are
        # authenticated by the gateway's native-auth annotation instead of a
        # SecurityPolicy, and the casdoor JWKS route is intentionally public so the
        # JWT provider signing keys can be discovered. All other routes must carry an
        # explicit SecurityPolicy. The native-auth value is a project-declared marker
        # with no upstream enum, so it is gated to the exact string-bool "true"/"false"
        # (Task 1.4 finding).
        if route["native_auth_value"] is not None:
            assert route["native_auth_value"] in ("true", "false"), (
                f"{NATIVE_AUTH_ANNOTATION} on {route['name']} must be the string-bool "
                f"'true'/'false' (got {route['native_auth_value']!r}). File: {route['file']}"
            )
            if route["native_auth"]:
                continue
        if route["name"] == CASDOOR_JWKS_ROUTE:
            continue
        matched = any(
            policy.get("kind") == route["kind"]
            and policy.get("name") == route["name"]
            and policy.get("namespace") in (route["namespace"], None)
            for policy in policies
        )
        assert matched, (
            f"{route['kind']} {route['name']} in {route['namespace']} has no SecurityPolicy "
            f"targetRef (R-002). File: {route['file']}"
        )


# P0-016 (FR-38, R-002)
# Given: messaging routes /events and /telemetry must authenticate via X-API-Key
#        natively at Envoy Gateway (FR-38, credential isolation R-009)
# When:  the SecurityPolicy set is inspected
# Then:  hpdc-messaging-api-key-authn covers the hpdc-edge-domain-routes HTTPRoute
#        (/data /api /events via the events store) and hpdc-telemetry-grpc-api-key-authn
#        covers the gRPC ingestion route (telemetry store)
def test_messaging_routes_covered_by_api_key_policy() -> None:
    policies = _policy_records()
    messaging = next((p for p in policies if p["policy_name"] == "hpdc-messaging-api-key-authn"), None)
    assert messaging is not None, "hpdc-messaging-api-key-authn SecurityPolicy missing"
    assert messaging["kind"] == "HTTPRoute"
    assert messaging["name"] == "hpdc-edge-domain-routes"
    assert messaging["namespace"] == "envoy-gateway-system"
    assert set(_api_key_paths(messaging)) >= {"/data", "/api", "/events"}
    assert set(_api_key_headers(messaging["spec"])) >= {"X-API-Key"}

    telemetry_http = next((p for p in policies if p["policy_name"] == "hpdc-telemetry-http-api-key-authn"), None)
    assert telemetry_http is not None, "hpdc-telemetry-http-api-key-authn SecurityPolicy missing"
    assert set(_api_key_paths(telemetry_http)) >= {"/telemetry"}
    assert set(_api_key_headers(telemetry_http["spec"])) >= {"X-API-Key"}

    grpc = next((p for p in policies if p["policy_name"] == "hpdc-telemetry-grpc-api-key-authn"), None)
    assert grpc is not None, "hpdc-telemetry-grpc-api-key-authn SecurityPolicy missing"
    assert grpc["kind"] == "GRPCRoute"
    assert grpc["name"] == "hpdc-telemetry-grpc-ingestion"
    assert grpc["namespace"] == "telemetry-ingestion"


# P0-016 (R-009)
# Given: api-key stores must enforce key-level isolation  When: the api-key
#        SecurityPolicies are inspected  Then: the events store holds only
#        events-key, the telemetry store holds only telemetry-key, and no policy
#        accepts a store holding the other path's key
def test_api_key_stores_are_key_isolated() -> None:
    stores: dict[str, dict] = {}
    for path in (GITOPS / "security/base/api-key-authn.yaml",):
        for doc in _load_docs(path):
            if doc.get("kind") == "Secret":
                stores[doc["metadata"]["name"]] = doc

    events_store = stores.get("events-api-key")
    assert events_store is not None, "events-api-key Secret store missing"
    assert list((events_store.get("stringData") or {}).keys()) == ["events-key"], (
        "events store must hold exactly events-key (key-level isolation, R-009)"
    )
    telemetry_store = stores.get("telemetry-api-key")
    assert telemetry_store is not None, "telemetry-api-key Secret store missing"
    assert list((telemetry_store.get("stringData") or {}).keys()) == ["telemetry-key"], (
        "telemetry store must hold exactly telemetry-key (key-level isolation, R-009)"
    )

    policies = {p["policy_name"]: p for p in _policy_records()}
    domain = policies.get("hpdc-messaging-api-key-authn")
    grpc = policies.get("hpdc-telemetry-grpc-api-key-authn")
    telemetry_http = policies.get("hpdc-telemetry-http-api-key-authn")
    assert domain is not None and grpc is not None and telemetry_http is not None

    domain_refs = _api_key_secret_refs(domain["spec"])
    assert domain_refs == ["events-api-key"], (
        f"domain policy must authenticate via the events store only, got {domain_refs} (R-009)"
    )
    assert "telemetry-api-key" not in domain_refs, (
        "domain policy must not reference the telemetry store (R-009)"
    )
    assert set(_api_key_secret_refs(grpc["spec"])) == {"telemetry-api-key"}
    assert set(_api_key_secret_refs(telemetry_http["spec"])) == {"telemetry-api-key"}

    expected_paths = {
        "events-api-key": {"/data", "/api", "/events"},
        "telemetry-api-key": {"/telemetry", "/hpdc.telemetry.v1.TelemetryService"},
    }
    store_paths: dict[str, set[str]] = {}
    for policy in (domain, grpc, telemetry_http):
        store = _api_key_secret_refs(policy["spec"])
        assert len(store) == 1, f"policy {policy['policy_name']} must reference exactly one api-key store (R-009)"
        assert store[0] in expected_paths, f"unknown api-key store {store[0]!r} (R-009)"
        store_paths.setdefault(store[0], set()).update(_api_key_paths(policy))
    for store, paths in store_paths.items():
        assert paths == expected_paths[store], (
            f"store {store} must own exactly {sorted(expected_paths[store])}, "
            f"got {sorted(paths)} (path-to-store ownership, R-009)"
        )


# P0-016 (FR-38, R-002)
# Given: a SecurityPolicy targetRef must reference a real route  When: the audit runs
# Then:  every SecurityPolicy targetRef resolves to an existing route in the tree
def test_no_dangling_security_policy_targets() -> None:
    routes = _route_records()
    route_keys = {(route["kind"], route["name"], route["namespace"]) for route in routes}
    for policy in _policy_records():
        key = (policy.get("kind"), policy.get("name"), policy.get("namespace"))
        assert key in route_keys, (
            f"SecurityPolicy {policy.get('policy_name')} targetRef dangles: "
            f"{policy.get('kind')}/{policy.get('name')}/{policy.get('namespace')}"
        )


# P0-016 (FR-38, R-002)
# Given: the hpdc-edge Gateway is the single ingress  When: routes are audited
# Then:  every HTTPRoute/GRPCRoute attaches to hpdc-edge in envoy-gateway-system,
#        and the gateway never exposes plaintext HTTP to the data plane (80 redirects
#        to 443; 1884 is the mTLS-scoped MQTT listener). parentRef namespace defaults
#        to the Route's own namespace, so cross-namespace routes must pin it to
#        envoy-gateway-system explicitly.
def test_all_routes_attach_to_hpdc_edge_gateway() -> None:
    for route in _route_records():
        if route["kind"] == "TCPRoute":
            continue
        refs = route["parent_refs"]
        assert refs, f"{route['name']} must declare parentRefs"
        for ref in refs:
            assert ref.get("name") == "hpdc-edge", f"{route['name']} must attach to the hpdc-edge gateway"
            effective_ns = ref.get("namespace") or route["namespace"]
            assert effective_ns == "envoy-gateway-system", (
                f"{route['name']} parentRef must resolve to envoy-gateway-system "
                f"(got {effective_ns}); cross-namespace routes must pin namespace explicitly"
            )
            assert ref.get("sectionName") == "https", f"{route['name']} must attach to the https listener"

    gateway = next(
        doc
        for path in _gitops_yaml_files()
        for doc in _load_docs(path)
        if doc.get("kind") == "Gateway" and doc.get("metadata", {}).get("name") == "hpdc-edge"
    )
    listeners = {listener["name"]: listener for listener in gateway["spec"]["listeners"]}
    https = listeners.get("https")
    http = listeners.get("http-redirect")
    mqtt = listeners.get("mqtt")
    assert https and https.get("protocol") == "HTTPS" and https.get("port") == 443, (
        "https listener must terminate 443"
    )
    assert http and http.get("protocol") == "HTTP" and http.get("port") == 80
    redirects = http.get("redirects") or {}
    assert redirects.get("toPort") == 443 and redirects.get("scheme") == "HTTPS", (
        "port 80 must redirect to 443 and never serve the data plane"
    )
    assert mqtt and mqtt.get("protocol") == "TCP" and mqtt.get("port") == 1884, (
        "MQTT TCP listener (1884) must be declared for the telemetry ingress"
    )


# P0-016 (FR-38, R-002)
# Given: GitOps is the only source of truth (R-001)  When: route manifests are audited
# Then:  every base file defining a route kind is referenced by its component overlay
#        kustomization, otherwise the route is never deployed (drift)
def test_route_manifests_referenced_by_overlays() -> None:
    for base in sorted(GITOPS.glob("*/base/*.yaml")):
        text = base.read_text(encoding="utf-8")
        if not any(f"kind: {kind}" in text for kind in ROUTE_KINDS):
            continue
        component = base.parents[1].name
        overlays = sorted((GITOPS / component / "overlays").glob("*/kustomization.yaml"))
        assert overlays, f"no overlay kustomization for component {component} (routes would never deploy)"
        ks_text = "".join(ks.read_text(encoding="utf-8") for ks in overlays)
        referenced = base.name in ks_text or f"../../{component}/base" in ks_text
        assert referenced, f"route manifest {base} not referenced by any {component} overlay kustomization (R-001)"


# P0-016 / P0-022 (R-001, R-008)
# Given: GitOps is the only source of truth  When: every gitops YAML is parsed
# Then:  no file is malformed and no mapping repeats a key (safe_load's last-wins
#        would silently hide the duplicate)
def test_all_gitops_yaml_is_valid() -> None:
    malformed: list[str] = []
    for path in _gitops_yaml_files():
        try:
            _load_docs(path)
        except Exception as exc:
            malformed.append(f"{path}: {type(exc).__name__}: {exc}")
    assert not malformed, "malformed YAML in gitops tree:\n" + "\n".join(malformed)


# P0-016 (R-001, AC 3)
# Given: every overlay must deploy real resources  When: every overlay kustomization
#        is structurally validated (pure-Python, no kustomize binary)  Then: each
#        resources entry resolves to a file whose documents all carry apiVersion+kind
#        or to a directory containing kustomization.yaml, and malformed labels blocks
#        (includeExpressions instead of pairs) are rejected
def test_overlay_kustomizations_resolve() -> None:
    errors: list[str] = []
    overlays = sorted(GITOPS.glob("*/overlays/*/kustomization.yaml"))
    assert overlays, "no overlay kustomizations found"
    for ks in overlays:
        try:
            kustomization = _load_docs(ks)[0]
        except Exception as exc:
            errors.append(f"{ks}: cannot parse kustomization.yaml: {exc}")
            continue
        assert kustomization.get("kind") == "Kustomization", f"{ks}: kind != Kustomization"
        for entry in kustomization.get("labels", []):
            if not isinstance(entry, dict):
                errors.append(f"{ks}: malformed labels entry {entry!r}")
                continue
            if "includeExpressions" in entry:
                errors.append(f"{ks}: labels entry uses includeExpressions (must be pairs:): {entry}")
            if "pairs" not in entry:
                errors.append(f"{ks}: labels entry missing pairs: {entry}")
        for resource in kustomization.get("resources", []):
            target = (ks.parent / resource).resolve()
            if target.is_dir():
                if not (target / "kustomization.yaml").is_file():
                    errors.append(f"{ks}: resources {resource!r} is a dir without kustomization.yaml")
                continue
            if not target.is_file():
                errors.append(f"{ks}: resources {resource!r} does not resolve to a file ({target})")
                continue
            try:
                docs = _load_docs(target)
            except Exception as exc:
                errors.append(f"{ks}: resources {resource!r} not valid YAML: {exc}")
                continue
            for doc in docs:
                if not isinstance(doc, dict) or "apiVersion" not in doc or "kind" not in doc:
                    errors.append(
                        f"{ks}: resources {resource!r} contains a document without apiVersion/kind: "
                        f"{sorted(doc) if isinstance(doc, dict) else doc!r}"
                    )
    assert not errors, "overlay kustomizations do not resolve:\n" + "\n".join(errors)


# P0-016 (R-002, AC 1)
# Given: no two routes may silently shadow each other  When: HTTPRoutes on the same
#        gateway listener are paired  Then: no two routes sharing a hostname pattern
#        route the same PathPrefix to different backends, and a catch-all PathPrefix /
#        is only permitted on the native-auth UI routes (the sanctioned default-backend
#        group). Equal-prefix duplicates are dead config; catch-all-vs-specific is the
#        sanctioned longest-prefix pattern, so it is not flagged.
def test_no_route_shadowing() -> None:
    groups: dict[tuple[str, str], list[dict]] = {}
    for route in _route_records():
        if route["kind"] != "HTTPRoute":
            continue
        for ref in route["parent_refs"]:
            if ref.get("name") != "hpdc-edge":
                continue
            effective_ns = ref.get("namespace") or route["namespace"]
            groups.setdefault((effective_ns, ref.get("sectionName") or ""), []).append(route)

    conflicts: list[str] = []
    for (gateway_ns, listener), routes in sorted(groups.items()):
        for i in range(len(routes)):
            for j in range(i + 1, len(routes)):
                a, b = routes[i], routes[j]
                if not any(h1 == h2 for h1 in a["hostnames"] for h2 in b["hostnames"]):
                    continue
                paths_a = {value for mtype, value in a["matches"] if mtype == "PathPrefix" and value}
                paths_b = {value for mtype, value in b["matches"] if mtype == "PathPrefix" and value}
                for path in sorted(paths_a & paths_b):
                    # The native-auth UI routes are a sanctioned default-backend group,
                    # but at most one may carry a wildcard catch-all PathPrefix /. Two
                    # equal-specificity `/` catch-alls on *.hpdc.local resolve
                    # non-deterministically (deferred-work ledger, 2026-08-08).
                    if a["native_auth"] and b["native_auth"] and path != "/":
                        continue
                    if set(a["backends"]) != set(b["backends"]):
                        conflicts.append(
                            f"{a['name']} and {b['name']} both match {path} on hostnames "
                            f"{sorted(set(a['hostnames']) & set(b['hostnames']))} "
                            f"(gateway {gateway_ns}/{listener}) but route to different backends"
                        )
        for route in routes:
            if "/" in {value for mtype, value in route["matches"] if mtype == "PathPrefix" and value}:
                if not route["native_auth"]:
                    conflicts.append(
                        f"{route['name']} carries a catch-all PathPrefix / without the native-auth "
                        "annotation (would shadow every dedicated route)"
                    )
    assert not conflicts, "route shadowing:\n" + "\n".join(conflicts)


def main() -> int:
    # GREEN: all P0-016 route-table audit checks run standalone. UI routes are
    # authenticated via the gateway native-auth annotation (documented tolerance);
    # all other routes carry an explicit SecurityPolicy.
    tests = (
        test_every_http_grpc_route_has_security_policy,
        test_messaging_routes_covered_by_api_key_policy,
        test_api_key_stores_are_key_isolated,
        test_no_dangling_security_policy_targets,
        test_all_routes_attach_to_hpdc_edge_gateway,
        test_route_manifests_referenced_by_overlays,
        test_all_gitops_yaml_is_valid,
        test_overlay_kustomizations_resolve,
        test_no_route_shadowing,
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
        f"GREEN PHASE: {len(tests)} route-audit checks declared; {executed} executed; "
        f"{len(failures)} failing."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
