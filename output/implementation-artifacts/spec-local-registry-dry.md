---
title: DRY the local registry URL into HPDC_LOCAL_REGISTRY_URL
type: refactor
created: 2026-09-01
status: done
route: one-shot
---

# DRY the local registry URL into HPDC_LOCAL_REGISTRY_URL

## Intent

**Problem:** `http://localhost:5000` (and the `http://127.0.0.1:5000` variant in
`mirror-image.py`) was hard-coded in 5 code sites across
`scripts/gitops/install_rook_ceph_dev.py`, `scripts/services/{image-preflight,image-registry,mirror-image}.py`,
and `scripts/startup.dev.py`. Any registry change required edits in 5 places.

**Approach:** Introduce a single source of truth —
`HPDC_LOCAL_REGISTRY_URL=http://localhost:5000` in `.env` / `.env.example` — and
replace every hard-coded literal with
`os.getenv("HPDC_LOCAL_REGISTRY_URL", "http://localhost:5000")`.
`image-preflight.py` resolves the var *after* `load_all_dotenv()` so the `.env`
value is respected, and derives the skopeo target host via
`urlparse(MIRROR).netloc`. All sites keep the original `localhost:5000` as the
default, so behavior is identical when the var is unset (zero blast radius).

## Suggested Review Order

- `.env.example:42` and `.env:43` — the single source of truth (the value every site falls back to).
- `scripts/gitops/install_rook_ceph_dev.py:20` — `REGISTRY` (full-URL form, used in `f"{REGISTRY}/v2/..."`).
- `scripts/services/image-preflight.py:39` — `MIRROR` resolved after `.env` load; `:126` skopeo host via `urlparse`.
- `scripts/services/image-registry.py:55` — health probe.
- `scripts/services/mirror-image.py:30` — `LOCAL` (was `127.0.0.1:5000`).
- `scripts/startup.dev.py:162` — `registry_summary()` probe.
- `tests/test_component_versions.py:162` — unchanged; asserts the default `localhost:5000` host, still valid.

## Adversarial notes (self-review)

- **Defaults preserve behavior:** every site falls back to `http://localhost:5000`;
  unset-var path is byte-identical to before → zero blast radius.
- **dotenv ordering:** `MIRROR` is assigned *after* `load_all_dotenv()` (moved
  below it) so an `.env` override is actually respected — true DRY, not cosmetic.
- **skopeo host form:** `urlparse(MIRROR).netloc` yields `localhost:5000` for the
  default and for `http://<host>:<port>` variants; the test assertion still holds.
- **127.0.0.1 → localhost:** Harbor binds `0.0.0.0:5000`; `localhost` resolves
  via 127.0.0.1/::1 — no regression, aligned with the project-wide convention.
- **standalone invocation:** `image-registry.py` / `mirror-image.py` do not load
  `.env` themselves; they rely on inherited env from `startup.dev.py` and the
  default otherwise.
