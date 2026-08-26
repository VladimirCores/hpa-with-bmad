#!/usr/bin/env python3
"""Central component/image version resolution for HPDC dev tooling.

Single source of truth for upstream component versions used across installers,
validators, the offline image cache and GitOps rendering.

Defaults live in ``.env.example`` (committed); local overrides live in ``.env``
(gitignored). Existing environment variables always win over ``.env`` values.

Consumers MUST import versions from here instead of declaring local constants;
``image-preflight.py`` derives its whole image list from :data:`CATALOG`, and
``render_overlays.py`` substitutes rendered image tags name-keyed off it.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ── dotenv loading (THE single implementation — bootstrap_talos_dev imports this) ──

_EXPORT_PREFIX = "export "


def load_dotenv(env_file: Path | None = None) -> None:
    """Seed os.environ from a .env file (existing environment wins).

    Dialect (matches historical bootstrap_talos_dev.load_dotenv):
    blank lines / ``#`` comments skipped; leading ``export `` stripped; split on
    first ``=``; inline comments stripped on space+#; surrounding quotes stripped;
    empty values skipped (variable falls back to its default); last assignment
    wins inside the file.
    Safe under sudo: default path is repo-relative.
    """
    env_file = env_file or ROOT / ".env"
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith(_EXPORT_PREFIX):
            line = line[len(_EXPORT_PREFIX):]
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.split(" #", 1)[0].strip().strip('"').strip("'")
        if key and value:
            os.environ.setdefault(key, value)


# ── Version variables ───────────────────────────────────────────────────────
# var name -> committed default (mirrored in .env.example; keep in sync).

DEFAULTS: dict[str, str] = {
    # Cluster substrate (Talos-managed images stay governed by these two +
    # talosctl regeneration; kubelet/installer/etcd/coredns are NOT catalogued)
    "HPDC_KUBERNETES_VERSION": "1.35.2",
    # CNI / mesh
    "HPDC_CILIUM_VERSION": "1.20.1",
    "HPDC_CILIUM_ENVOY_TAG": "v1.37.5-1786810558-766ccfb37260a43e9d228837aa84ce3faf9f64e7",
    "HPDC_HUBBLE_UI_VERSION": "v0.13.5",
    "HPDC_SPIRE_VERSION": "1.15.3",
    # Storage
    "HPDC_ROOK_CEPH_VERSION": "1.20.6",
    "HPDC_LOCAL_PATH_PROVISIONER_VERSION": "v0.0.37",
    # Registry / cache
    "HPDC_HARBOR_VERSION": "2.15.2",
    "HPDC_HARBOR_CHART_VERSION": "1.19.2",
    "HPDC_HARBOR_REDIS_VERSION": "7.4-alpine",
    "HPDC_HARBOR_POSTGRES_VERSION": "15.19-alpine",
    "HPDC_SPEGEL_VERSION": "0.7.4",
    # GitOps / CD
    "HPDC_ARGOCD_VERSION": "3.5.1",
    "HPDC_ARGOCD_REDIS_VERSION": "8.2.8-alpine",
    "HPDC_KARGO_VERSION": "1.11.2",
    "HPDC_KARGO_CHART_VERSION": "1.11.2",
    "HPDC_CERT_MANAGER_CHART_VERSION": "v1.21.1",
    "HPDC_CERT_MANAGER_VERSION": "1.21.1",
    "HPDC_ARGO_ROLLOUTS_VERSION": "1.9.1",
    "HPDC_ROLLOUTS_NGINX_VERSION": "1.27-alpine",
    "HPDC_ARGO_EVENTS_VERSION": "1.9.11",
    "HPDC_EVENTS_ALPINE_VERSION": "3.20",
    # Edge
    "HPDC_ENVOY_GATEWAY_VERSION": "1.9.0",
    # Auth / secrets
    "HPDC_CASDOOR_VERSION": "3.159.0",
    # NOTE: upstream deleted the historical 0.10.0 tag (scheme now v-prefixed
    # v0.162.x); pinned to newest stable at reconciliation time 2026-08-26.
    "HPDC_INFISICAL_VERSION": "v0.162.24",
    # Observability
    "HPDC_GRAFANA_VERSION": "13.2.0",
    "HPDC_VICTORIA_METRICS_VERSION": "1.150.0",
    "HPDC_VICTORIA_LOGS_VERSION": "v1.52.0",
    "HPDC_OTEL_COLLECTOR_VERSION": "0.159.0",
    "HPDC_ALERTMANAGER_VERSION": "v0.34.0",
    # Portal / docs (ghcr tag lags GitHub releases; 1.54.5 has no image yet)
    "HPDC_BACKSTAGE_VERSION": "1.54.0",
    "HPDC_SWAGGER_UI_VERSION": "v5.32.14",
    # Utilities
    "HPDC_GIT_MIRROR_IMAGE_VERSION": "2.54.0",
    "HPDC_KUBECTL_VERSION": "1.35.2",
}

_VAR_RE = re.compile(r"\{([a-z_]+)\}")


def _resolve_template(template: str) -> str:
    """Expand ``{hpdc_x_version}`` placeholders against resolved vars."""
    def sub(match: re.Match[str]) -> str:
        return _resolved[match.group(1)]
    return _VAR_RE.sub(sub, template)


# ── Image catalog ───────────────────────────────────────────────────────────
# component -> list of (repo_as_written_in_manifests, tag_template, marker_relpath)
# * repo uses EXACTLY the spelling committed manifests use (host prefix or bare)
# * tag templates reference DEFAULTS keys minus the HPDC_/​_VERSION wrapper via
#   {name_version} placeholders (see _resolve_template)
# * marker paths are relative to output/ and follow the historical slug per file

CATALOG: dict[str, list[tuple[str, str, str]]] = {
    "cilium": [
        ("quay.io/cilium/cilium", "v{cilium_version}", "cilium/images/cilium-v{cilium_version}"),
        ("quay.io/cilium/operator-generic", "v{cilium_version}", "cilium/images/operator-generic-v{cilium_version}"),
        ("quay.io/cilium/hubble-ui", "{hubble_ui_version}", "cilium/images/hubble-ui-{hubble_ui_version}"),
        ("quay.io/cilium/cilium-envoy", "{cilium_envoy_tag}", "cilium/images/cilium-envoy-v1.37.5"),
        ("ghcr.io/spiffe/spire-server", "{spire_version}", "cilium/images/spire-server-{spire_version}"),
        ("ghcr.io/spiffe/spire-agent", "{spire_version}", "cilium/images/spire-agent-{spire_version}"),
    ],
    "rook-ceph": [
        ("quay.io/rook/ceph", "v{rook_ceph_version}", "rook-ceph/images/rook-ceph-v{rook_ceph_version}"),
    ],
    "harbor": [
        ("docker.io/goharbor/harbor-core", "v{harbor_version}", "harbor/images/harbor-core-v{harbor_version}"),
        ("docker.io/goharbor/registry-photon", "v{harbor_version}", "harbor/images/registry-photon-v{harbor_version}"),
        ("docker.io/goharbor/harbor-jobservice", "v{harbor_version}", "harbor/images/harbor-jobservice-v{harbor_version}"),
        ("docker.io/goharbor/harbor-registryctl", "v{harbor_version}", "harbor/images/harbor-registryctl-v{harbor_version}"),
        ("docker.io/goharbor/trivy-adapter-photon", "v{harbor_version}", "harbor/images/trivy-adapter-photon-v{harbor_version}"),
        ("redis", "{harbor_redis_version}", "harbor/images/redis-{harbor_redis_version}"),
        ("postgres", "{harbor_postgres_version}", "harbor/images/postgres-{harbor_postgres_version}"),
    ],
    "spegel": [
        ("ghcr.io/spegel-org/spegel", "v{spegel_version}", "spegel/images/spegel-v{spegel_version}"),
    ],
    "local-path-provisioner": [
        ("rancher/local-path-provisioner", "{local_path_provisioner_version}", "storage/images/local-path-provisioner-{local_path_provisioner_version}"),
    ],
    "argocd": [
        ("quay.io/argoproj/argocd", "v{argocd_version}", "argocd/images/argocd-v{argocd_version}"),
        ("docker.io/library/redis", "{argocd_redis_version}", "argocd/images/redis-{argocd_redis_version}"),
    ],
    "kargo": [
        ("ghcr.io/akuity/kargo", "v{kargo_version}", "kargo/images/kargo-v{kargo_version}"),
    ],
    "argo-rollouts": [
        ("quay.io/argoproj/argo-rollouts", "v{argo_rollouts_version}", "argo-rollouts/images/argo-rollouts-v{argo_rollouts_version}"),
        ("nginx", "{rollouts_nginx_version}", "argo-rollouts/images/rollouts-nginx-{rollouts_nginx_version}"),
    ],
    "argo-events": [
        ("quay.io/argoproj/argo-events", "v{argo_events_version}", "argo-events/images/argo-events-v{argo_events_version}"),
        ("alpine", "{events_alpine_version}", "argo-events/images/events-alpine-{events_alpine_version}"),
    ],
    "envoy-gateway": [
        ("docker.io/envoyproxy/gateway", "v{envoy_gateway_version}", "envoy-gateway/images/envoy-gateway-v{envoy_gateway_version}"),
    ],
    "cert-manager": [
        ("quay.io/jetstack/cert-manager-controller", "v{cert_manager_version}", "cert-manager/images/cert-manager-controller-v{cert_manager_version}"),
        ("quay.io/jetstack/cert-manager-webhook", "v{cert_manager_version}", "cert-manager/images/cert-manager-webhook-v{cert_manager_version}"),
        ("quay.io/jetstack/cert-manager-cainjector", "v{cert_manager_version}", "cert-manager/images/cert-manager-cainjector-v{cert_manager_version}"),
    ],
    "casdoor": [
        ("docker.io/casbin/casdoor", "{casdoor_version}", "casdoor/images/casdoor-{casdoor_version}"),
    ],
    "infisical": [
        ("docker.io/infisical/infisical", "{infisical_version}", "infisical/images/infisical-{infisical_version}"),
    ],
    "grafana": [
        ("docker.io/grafana/grafana", "{grafana_version}", "grafana/images/grafana-{grafana_version}"),
    ],
    "victoria-metrics": [
        ("victoriametrics/vmstorage", "v{victoria_metrics_version}-cluster", "victoria-metrics/images/vmstorage-v{victoria_metrics_version}-cluster"),
        ("victoriametrics/vminsert", "v{victoria_metrics_version}-cluster", "victoria-metrics/images/vminsert-v{victoria_metrics_version}-cluster"),
        ("victoriametrics/vmselect", "v{victoria_metrics_version}-cluster", "victoria-metrics/images/vmselect-v{victoria_metrics_version}-cluster"),
        ("victoriametrics/victoria-logs", "{victoria_logs_version}", "victoria-metrics/images/victoria-logs-{victoria_logs_version}"),
        ("otel/opentelemetry-collector-contrib", "{otel_collector_version}", "victoria-metrics/images/otel-collector-{otel_collector_version}"),
    ],
    "alertmanager": [
        ("prom/alertmanager", "{alertmanager_version}", "monitoring/images/alertmanager-{alertmanager_version}"),
    ],
    "backstage": [
        ("ghcr.io/backstage/backstage", "{backstage_version}", "backstage/images/backstage-{backstage_version}"),
    ],
    "swagger-ui": [
        ("docker.io/swaggerapi/swagger-ui", "{swagger_ui_version}", "openapi/images/swagger-ui-{swagger_ui_version}"),
    ],
    "git-mirror-image": [
        ("alpine/git", "{git_mirror_image_version}", "git/images/alpine-git-{git_mirror_image_version}"),
    ],
    "kubectl": [
        ("registry.k8s.io/kubectl", "v{kubernetes_version}", "security/images/kubectl-v{kubernetes_version}"),
    ],
}

# Images built from project sources — never mirrored, never env-driven.
CUSTOM_IMAGES: frozenset[str] = frozenset({
    "hpdc.local/graphql-gateway:0.1.0",
    "hpdc.local/entity-api:0.1.0",
    "hpdc.local/llm-decision-support:0.1.0",
    "hpdc.local/alert-handler:0.1.0",
    "ghcr.io/hpdc/regional-hub-spa:dev",
    "hpdc.local/a2a-broker:dev",
    "hpdc.local/mcp-server:dev",
    "docker.io/casbin/ext-authz:v0.0.1",
})


# ── Resolution API ──────────────────────────────────────────────────────────


def _normalize_var_key(var: str) -> str:
    """HPDC_CILIUM_VERSION -> cilium_version (template key form)."""
    if var.startswith("HPDC_"):
        var = var[len("HPDC_"):]
    return var.lower()


_resolved: dict[str, str] = {}


def resolve() -> dict[str, str]:
    """Re-resolve every variable from os.environ (after load_dotenv)."""
    _resolved.clear()
    for var, default in DEFAULTS.items():
        _resolved[var] = os.environ.get(var) or default
        _resolved[_normalize_var_key(var)] = _resolved[var]
    return dict(_resolved)


def get(var: str) -> str:
    """Return the resolved value for an ``HPDC_*`` variable name."""
    if not _resolved:
        resolve()
    try:
        return _resolved[var]
    except KeyError as exc:
        raise KeyError(f"unknown version variable: {var}; known: {sorted(DEFAULTS)}") from exc


def image_refs() -> list[tuple[str, str]]:
    """All catalogued upstream image refs as (component, fully-qualified-ref)."""
    if not _resolved:
        resolve()
    out: list[tuple[str, str]] = []
    for component, entries in CATALOG.items():
        for repo, tag_template, _marker in entries:
            out.append((component, f"{repo}:{_resolve_template(tag_template)}"))
    return out


def substitution_map() -> dict[str, str]:
    """manifest-repo-spelling -> new ``repo:tag`` for render-time injection."""
    if not _resolved:
        resolve()
    out: dict[str, str] = {}
    for entries in CATALOG.values():
        for repo, tag_template, _marker in entries:
            # first-wins: catalog orders the manifest-visible spelling first
            out.setdefault(repo, f"{repo}:{_resolve_template(tag_template)}")
    return out


def marker_for(repo: str, ref: str) -> Path | None:
    """Historic cache-marker path under output/ for an image ref, if catalogued."""
    if not _resolved:
        resolve()
    for _component, entries in CATALOG.items():
        for c_repo, tag_template, marker in entries:
            if c_repo == repo and f"{c_repo}:{_resolve_template(tag_template)}" == ref:
                if not marker:
                    return None
                return ROOT / "output" / _resolve_template(marker)
    return None


resolve()
