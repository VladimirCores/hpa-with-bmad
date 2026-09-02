# Epic 15 Context: Core Gateway Layer

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Establish the core gateway layer in the dev environment so that operator tool UIs (beginning with Hubble) are reachable through `*.hpdc.local` routes immediately after the core substrate is installed — without port-forward and without cert-manager. Envoy Gateway is moved into the core layer (right after Cilium) and a static self-signed wildcard TLS certificate is generated at bootstrap, making downstream HTTPRoutes attachable. This readies the gateway boundary for domain routes (Epic 3) and remaining tool-UI routes (Epic 3/Epic 7).

## Stories

- Story 15.1: Generate Static Self-Signed Wildcard Cert and Create TLS Secret
- Story 15.2: Move Envoy Gateway Installation to Core Layer
- Story 15.3: Update Docs and README for Static Cert and Production Requirements
- Story 15.4: Validate Core Gateway — Hubble UI and Downstream Route Readiness
- Story 15.5: Enable Cilium L2 LoadBalancer for External Gateway Access
- Story 15.6: Post-Install E2E Accessibility Testing for All Components

## Requirements & Constraints

- FR-36 (partial — Gateway/GatewayClass only): A `GatewayClass` and `Gateway` are created as Kubernetes Gateway API resources; Gateway serves HTTPS on :443 (referencing the edge TLS secret) and TCP on :1884 for MQTT. Service address sourced from the Cilium L2 LB pool (`${HPDC_GATEWAY_IP}`), so Cilium networking must precede this epic.
- FR-37 (modified): Dev TLS uses a static self-signed wildcard cert (`*.hpdc.local`, CN + SAN `DNS:*.hpdc.local`, RSA-2048, 10-year validity) generated at bootstrap; cert/key persist to `~/.hpdc/certs/` on local filesystem, never committed to Git. cert-manager is removed entirely from the core layer. Production CA signing (cert-manager or external CA) is documented, not implemented.
- TLS secret `Secret/hpdc-edge-tls` (type `kubernetes.io/tls`) created in `envoy-gateway-system` from the generated cert/key; HTTPS listener references it via `certificateRefs` and must report `Programmed=True`.
- Envoy Gateway pinned at 1.8.3, installed in `envoy-gateway-system`; Gateway API CRDs from `gitops/crds/gateway/crds.yaml`.
- Domain routes (`/data`, `/api`, `/gql`, `/events`, `/telemetry`) and their authN/authZ are explicitly out of scope — they arrive with Epic 3.
- Project-wide: all scripts are Python 3 and exit non-zero on failure; core layer bootstraps fully offline.
- Validation: GatewayClass reports `Accepted`, Gateway reports `Programmed=True`, HTTPS listener accepting connections, `hubble.hpdc.local` resolves to gateway IP and returns HTTP 200/302 without port-forward.

## Technical Decisions

- **Early EG placement:** Envoy Gateway moves from the original late position to core-layer step 4 (right after Cilium/Hubble); the separate cert-manager step is eliminated. HTTPRoutes (e.g., Hubble UI) become attachable immediately after core install.
- **Static dev cert, delegated prod cert:** Dev uses a bootstrap-generated static self-signed wildcard cert to keep the offline dev flow air-gapped and simple; production defers to cert-manager or external CA with auto-renewal, documented in `docs/`. This intentionally deviates from AD-1 (which specified cert-manager for TLS).
- **Gateway identity and listeners:** `GatewayClass/hpdc-envoy-gateway` + `Gateway/hpdc-edge`; HTTPS :443 (`certificateRefs: [hpdc-edge-tls]`) and TCP :1884 (MQTT). Gateway service address sourced from Cilium L2 LB pool, so this epic depends on Story 1.3.
- **Route/responsibility boundary:** Epic 15 owns Gateway/GatewayClass + TLS only — not domain routes or auth wiring. Argo sync-wave ordering: Gateway API CRDs at -10, EG at platform-core wave (-3) after Network (-5) and Storage (-4).
- **Tool UI routing contract:** Operator tool UIs use `*.hpdc.local` subdomains via Envoy Gateway with each tool's native identity (SSO/RBAC/OIDC); Casdoor/Casbin is NOT applied to tool-UI routes (per UX-DR1). Epic 15 validates this for Hubble UI; remaining routes come from Epic 3/Epic 7.

## Cross-Story Dependencies

- Depends on Story 1.2 (healthy Talos dev cluster) and Story 1.3 (Cilium L2 load-balancing) — the Gateway address is sourced from the Cilium L2 LB pool.
- Story 15.2 depends on 15.1 (TLS secret present) and the Gateway API CRDs at `gitops/crds/gateway/crds.yaml`.
- Story 15.4 depends on 15.2 (Gateway installed) and 15.1 (TLS secret).
- Epic 15 is a prerequisite for Epic 3 (domain + tool-UI HTTPRoutes, authN/authZ wiring) and Epic 7 (Grafana/Hubble tool-UI routes); Envoy Gateway is installed early so those routes attach immediately.
