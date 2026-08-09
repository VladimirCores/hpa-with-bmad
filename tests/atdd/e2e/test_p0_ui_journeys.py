#!/usr/bin/env python3
"""RED-PHASE (BLOCKED/DEFERRED) UI journey scaffolds: P0-025 login and P0-026 Casdoor SSO.

Contract source:
  - output/test-artifacts/test-design/test-design-qa.md  (P0-025, P0-026)
  - gitops/casdoor/base/casdoor.yaml                     (OIDC/SAML, applicationName "HPDC",
                                                          sessionMaxLifetimeHours 12)
  - gitops/backstage/base/backstage.yaml                 (casdoor auth provider,
                                                          issuerUrl https://casdoor.hpdc.local)
  - gitops/tool-ui/base/tool-ui-routes.yaml, gitops/observability/base/envoy-ui-routes.yaml

BLOCKED/DEFERRED: this repo has NO UI test harness - no Playwright install and no
frontend contract to drive (test-design-qa.md P0-025/P0-026; blocker B-002 identity
fixtures). These scaffolds document the EXPECTED UI login / SSO contract for the
future green phase and stay @pytest.mark.skip with a blocker reason.

Run under pytest (all tests are skipped). main() does NOT run the journey bodies.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]

GATEWAY_URL = os.environ.get("HPDC_GATEWAY_URL", "https://edge.hpdc.local")
CASDOOR_ISSUER = os.environ.get("HPDC_CASDOOR_ISSUER", "https://casdoor.hpdc.local")

UI_BLOCKER = (
    "RED PHASE - BLOCKED: no UI test harness (B-002 identity fixtures, "
    "Playwright not installed) - deferred"
)

_TLS = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
_TLS.check_hostname = False
_TLS.verify_mode = ssl.CERT_NONE


def _request(method: str, url: str, payload=None, headers=None):
    data = None
    request_headers = dict(headers or {})
    if payload is not None:
        if isinstance(payload, bytes):
            data = payload
        elif isinstance(payload, str):
            data = payload.encode()
        else:
            data = json.dumps(payload).encode()
            request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, context=_TLS, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace"), resp.headers
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace"), exc.headers


def _session_cookie(headers) -> str | None:
    for value in (headers.get_all("Set-Cookie") or []) + [headers.get("Set-Cookie") or ""]:
        cookie = value.split(";", 1)[0].strip()
        if cookie.lower().startswith("session") or "session" in cookie.lower():
            return cookie
    return None


# P0-025 (UI login)
# Given: an unauthenticated client reaches the portal gateway  When: it requests /login
# Then:  the route answers the login UI (200) or redirects to Casdoor (302), and the
#        dashboard renders with the HPDC portal markers once authenticated
@pytest.mark.skip(reason=UI_BLOCKER)
def test_ui_login_dashboard_renders() -> None:
    status, html, headers = _request("GET", f"{GATEWAY_URL}/login")
    assert status in (200, 302), f"/login must answer the login UI, got HTTP {status}"
    if status == 302:
        assert "casdoor" in headers.get("Location", "").lower(), "login must redirect to Casdoor"
    else:
        assert "hpdc" in html.lower() and "login" in html.lower()
    status2, html2, _ = _request("GET", f"{GATEWAY_URL}/")
    assert status2 == 200, "dashboard must render after authentication"
    assert "hpdc" in html2.lower()
    assert any(marker in html2.lower() for marker in ("dashboard", "alerts", "portal", "catalog")), (
        "dashboard HTML must contain expected HPDC portal markers"
    )


# P0-026 (UI SSO)
# Given: an unauthenticated user opens the portal  When: navigating to a protected page
# Then:  the flow redirects to Casdoor (/casdoor), the login form accepts the B-002
#        fixture credentials, the callback issues a session cookie, and subsequent
#        requests are authenticated (session lifetime capped at 12h per casdoor config)
@pytest.mark.skip(reason=UI_BLOCKER)
def test_ui_casdoor_sso_journey() -> None:
    status, _, headers = _request("GET", f"{GATEWAY_URL}/")
    assert status == 302, f"unauthenticated request must redirect, got HTTP {status}"
    location = headers.get("Location", "")
    assert "casdoor" in location.lower(), f"SSO redirect to Casdoor expected, got {location}"

    auth_status, auth_html, _ = _request("GET", f"{CASDOOR_ISSUER}/login")
    assert auth_status in (200, 302)
    assert "hpdc" in (auth_html or "").lower(), "Casdoor login page must render the HPDC app"

    login_status, _, login_headers = _request(
        "POST",
        f"{CASDOOR_ISSUER}/login",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        payload=urllib.parse.urlencode(
            {
                "username": os.environ.get("HPDC_SSO_USER", "operator@hpdc.local"),
                "password": os.environ.get("HPDC_SSO_PASSWORD", "<fixture-password>"),
            }
        ).encode(),
    )
    assert login_status in (200, 302), f"Casdoor login must be accepted, got HTTP {login_status}"

    callback_status, _, callback_headers = _request("GET", f"{CASDOOR_ISSUER}/callback")
    assert callback_status in (200, 302), "SSO callback must complete the OIDC exchange"
    assert _session_cookie(callback_headers) or _session_cookie(login_headers), (
        "SSO flow must set a session cookie"
    )

    portal_status, _, _ = _request("GET", f"{GATEWAY_URL}/", headers={"Cookie": _session_cookie(callback_headers) or ""})
    assert portal_status == 200, "authenticated portal request must succeed"


def main() -> int:
    # RED PHASE (BLOCKED/DEFERRED): all tests carry @pytest.mark.skip with a blocker
    # reason; the journey bodies must not run standalone (skip markers are honoured
    # by pytest only).
    print("RED PHASE - skipped (BLOCKED/DEFERRED: run under pytest; all tests carry @pytest.mark.skip)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
