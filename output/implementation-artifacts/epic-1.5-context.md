# Epic 1.5 Context: Core Gateway Layer

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Establish the core gateway layer in the dev environment so that operator tool UIs (beginning with Hubble) are reachable through `*.hpdc.local` routes immediately after the core substrate is installed — without port-forward and without cert-manager. Envoy Gateway is moved into the core layer (right after Cilium) and a static self-signed wildcard TLS certificate is generated at bootstrap, making downstream HTTPRoutes attachable. This readies the gateway boundary for the domain routes (Epic 3) and the remaining tool-UI routes (Epic 3/Epic 7).

## Stories

- Story 1.5.1: Generate Static Self-Signed Wildcard Cert and Create TLS Secret
- Story 1.5.2: Move Envoy Gateway Installation to Core Layer
- Story 1.5.3: Update Docs and README for Static Cert and Production Requirements
- Story 1.5.4: Validate Core Gateway — Hubble UI and Downstream Route Readiness

## Requirements & Constraints

- FR-36 (partial — Gateway/GatewayClass only): A `GatewayClass` and `Gateway` are created from Kubernetes Gateway API resources; the Gateway serves HTTPS on :443 (referencing the edge TLS secret) and TCP on :1884 for MQTT ingress. Its service address is taken from the Cilium L2 load-balancer pool (`${HPDC_GATEWAY_IP}`), so Cilium networking must precede it.
- FR-37 (modified): Dev TLS termination uses a static self-signed wildcard certificate (`*.hpdc.local`, CN + SAN `DNS:*.hpdc.local`, RSA-2048, 10-year validity) generated at bootstrap; the cert and key persist to `~/.hpdc/certs/{tls.crt,tls.key}` on the local filesystem and are never committed to Git. cert-manager is removed from the core layer entirely; production CA signing (cert-manager or an external CA) is documented, not implemented here.
- The TLS secret `Secret/hpdc-edge-tls` (type `kubernetes.io/tls`) is created in `envoy-gateway-system` from the generated cert/key; the HTTPS listener references it via `certificateRefs` and must report `Programmed=True`.
- Envoy Gateway (pinned 1.8.3) installs in namespace `envoy-gateway-system`; Gateway API CRDs come from `gitops/crds/gateway/crds.yaml`.
- The five domain routes (`/data`, `/api`, `/gql`, `/events`, `/telemetry`) and their authN/authZ (JWT/Casbin on domain routes, API-Key on messaging routes) are explicitly out of scope — they arrive with Epic 3.
- Project-wide: bootstrap/cache/verification scripts are Python 3 and exit non-zero on failure; the core layer bootstraps fully offline (no internet access).
- Validation gate: after install, the GatewayClass reports `Accepted`, the Gateway reports `Programmed=True` with an HTTPS listener accepting connections, and `hubble.hpdc.local` resolves to the gateway IP and is reachable (HTTP 200/302) without port-forward.

## Technical Decisions

- **Early Envoy Gateway placement in the core layer:** Envoy Gateway installs as core-layer step 4 (immediately after Cilium/Hubble), moved up from the original late position; the separate cert-manager step that followed it is eliminated. HTTPRoutes (e.g., Hubble UI) become attachable immediately after core install.
- **Static dev cert, delegated prod cert:** Dev uses a bootstrap-generated static self-signed wildcard cert (no cert-manager) to keep the offline dev flow air-gapped and simple; production defers to cert-manager or an external CA with auto-renewal, documented in `docs/`. This intentionally deviates from the original architecture spine (AD-1), which specified cert-manager for TLS.
- **Gateway identity and listeners:** `GatewayClass/hpdc-envoy-gateway` + `Gateway/hpdc-edge`; HTTPS :443 (`certificateRefs: [hpdc-edge-tls]`) and TCP :1884 (MQTT). The Gateway service address is sourced from the Cilium L2 LoadBalancer IP pool, so this epic depends on Cilium networking (Epic 1, Story 1.3).
- **Route/responsibility boundary:** Epic 1.5 owns the Gateway/GatewayClass + TLS only — not the domain routes or auth wiring. Argo sync-wave ordering still holds: Gateway API CRDs at -10, EG at the platform-core wave (-3) after Network (-5) and Storage (-4).

## UX & Interaction Patterns

- Operator tool UIs (Hubble, Grafana, Argo CD, Kargo, Backstage) are exposed as `*.hpdc.local` subdomains through Envoy Gateway so they are reachable in-browser without port-forward, using each tool's native identity (SSO/RBAC/OIDC); Casdoor/Casbin is NOT applied to tool-UI routes. Epic 1.5 validates this contract for Hubble UI as the readiness gate; the remaining tool-UI routes are delivered by Epic 3/Epic 7 per UX-DR1.

## Cross-Story Dependencies

- Depends on Story 1.2 (healthy Talos dev cluster) and Story 1.3 (Cilium L2 load-balancing) — the Gateway address is sourced from the Cilium L2 LB pool.
- Story 1.5.2 depends on 1.5.1 (TLS secret present) and the Gateway API CRDs at `gitops/crds/gateway/crds.yaml`.
- Story 1.5.4 depends on 1.5.2 (Gateway installed) and 1.5.1 (TLS secret).
- Epic 1.5 is a prerequisite for Epic 3 (domain + tool-UI HTTPRoutes, authN/authZ wiring) and Epic 7 (Grafana/Hubble tool-UI routes); Envoy Gateway is installed early precisely so those routes attach immediately.
