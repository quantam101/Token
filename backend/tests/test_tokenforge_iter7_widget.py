"""Iter-7 smoke — embeddable savings widget (/api/widget.js + /embed/{slug}) +
avg_compression_pct capping bug fix.

Public no-auth read-only endpoints:
  GET /api/widget.js   — loader IIFE
  GET /embed/{slug}    — iframe-targeted HTML (theme=dark|light)

NOTE: /embed/{slug} is mounted on the FastAPI `app` directly (NOT /api).
The platform ingress routes non-/api paths to the React frontend (port 3000),
so /embed/<slug> is intercepted by the frontend BEFORE reaching FastAPI.
We assert what we observe and let the report describe the consequence.
"""
import os
import re
import secrets
import requests
import pytest
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

ADMIN = ("admin@tokenforge.io", "ForgeAdmin!2026")


def _login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _bearer(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def admin_slug():
    tok = _login(*ADMIN)
    r = requests.post(f"{API}/share/savings", headers=_bearer(tok))
    assert r.status_code == 200, r.text
    return r.json()["slug"]


# ---------- widget.js ----------
class TestWidgetJs:
    def test_widget_js_200_and_content_type(self):
        r = requests.get(f"{API}/widget.js", timeout=20)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "javascript" in ct.lower(), f"unexpected CT: {ct}"

    def test_widget_js_body_contains_iife_markers(self):
        r = requests.get(f"{API}/widget.js", timeout=20)
        body = r.text
        assert "data-tf-slug" in body, "loader must read data-tf-slug"
        assert "currentScript" in body, "loader must use document.currentScript"
        assert body.lstrip().startswith("(function"), "loader should be an IIFE"
        # injects iframe pointing at /embed/
        assert "/embed/" in body

    def test_widget_js_cors_allow_all(self):
        r = requests.get(f"{API}/widget.js", timeout=20)
        assert r.headers.get("access-control-allow-origin") == "*"


# ---------- /embed/{slug} via PUBLIC PREVIEW URL (what hosts will iframe) ----------
class TestEmbedPagePublic:
    def test_embed_public_url_returns_fastapi_html(self, admin_slug):
        """After iter-8 fix: route is now @api.get('/embed/{slug}'), public URL = /api/embed/<slug>."""
        r = requests.get(f"{API}/embed/{admin_slug}", timeout=20)
        assert r.status_code == 200, r.text
        assert "text/html" in r.headers.get("content-type", "").lower()
        body = r.text
        assert "TokenForge savings" in body

    def test_embed_contains_live_numbers_and_display_name(self, admin_slug):
        api_data = requests.get(f"{API}/share/savings/{admin_slug}", timeout=20).json()
        r = requests.get(f"{API}/embed/{admin_slug}", timeout=20)
        body = r.text
        assert api_data["display_name"] in body
        assert f"{api_data['tokens_saved']:,}" in body
        assert f"${api_data['cost_saved_usd']:.4f}" in body
        assert f"{api_data['requests']:,}" in body

    def test_embed_iframe_headers(self, admin_slug):
        r = requests.get(f"{API}/embed/{admin_slug}", timeout=20)
        xfo = r.headers.get("x-frame-options", "")
        csp = r.headers.get("content-security-policy", "")
        assert "ALLOWALL" in xfo.upper() or "ALLOW" in xfo.upper(), f"XFO header missing/wrong: {xfo!r}"
        assert "frame-ancestors" in csp.lower(), f"CSP frame-ancestors missing: {csp!r}"

    def test_embed_unknown_slug_returns_404_html(self):
        r = requests.get(f"{API}/embed/__definitely_no_such_slug_zz9__", timeout=20)
        assert r.status_code == 404
        assert "text/html" in r.headers.get("content-type", "").lower()
        assert "no longer active" in r.text.lower()
        assert '"detail"' not in r.text

    def test_embed_theme_light_palette(self, admin_slug):
        r = requests.get(f"{API}/embed/{admin_slug}?theme=light", timeout=20)
        assert r.status_code == 200
        body = r.text
        assert "#FFFFFF" in body, "light theme should use white background"

    def test_embed_avg_pct_never_exceeds_100(self, admin_slug):
        r = requests.get(f"{API}/embed/{admin_slug}", timeout=20)
        body = r.text
        # Find the "Avg compression: <b ...>X%</b>" value
        m = re.search(r"Avg compression:\s*<b[^>]*>([\d.]+)%</b>", body)
        assert m, "avg_pct field not found in embed body (likely served by frontend SPA, not FastAPI)"
        val = float(m.group(1))
        assert val <= 100.0, f"avg_pct {val} exceeds 100"


# ---------- /embed via internal localhost (proves backend code itself is correct) ----------
class TestEmbedPageInternal:
    def test_embed_internal_localhost(self, admin_slug):
        r = requests.get(f"http://localhost:8001/api/embed/{admin_slug}", timeout=20)
        assert r.status_code == 200
        assert "TokenForge savings" in r.text
        assert "ALLOWALL" in r.headers.get("x-frame-options", "").upper()

    def test_embed_internal_unknown_slug(self):
        r = requests.get("http://localhost:8001/api/embed/__no_such__", timeout=20)
        assert r.status_code == 404
        assert "no longer active" in r.text.lower()

    def test_embed_internal_light_palette(self, admin_slug):
        r = requests.get(f"http://localhost:8001/api/embed/{admin_slug}?theme=light", timeout=20)
        assert r.status_code == 200
        assert "#FFFFFF" in r.text

    def test_embed_internal_avg_pct_cap(self, admin_slug):
        r = requests.get(f"http://localhost:8001/api/embed/{admin_slug}", timeout=20)
        m = re.search(r"Avg compression:\s*<b[^>]*>([\d.]+)%</b>", r.text)
        assert m, "avg pct not found"
        assert float(m.group(1)) <= 100.0


# ---------- avg_compression_pct cap on JSON API ----------
class TestAvgPctCap:
    def test_share_savings_json_avg_pct_capped(self, admin_slug):
        r = requests.get(f"{API}/share/savings/{admin_slug}", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "avg_compression_pct" in d
        assert d["avg_compression_pct"] <= 100.0, f"avg_pct {d['avg_compression_pct']} > 100"


# ---------- prior critical-flow smoke (regression) ----------
class TestPriorFlowSmoke:
    def test_auth_me_admin(self):
        tok = _login(*ADMIN)
        r = requests.get(f"{API}/auth/me", headers=_bearer(tok), timeout=20)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN[0]

    def test_register_then_me(self):
        email = f"TEST_iter7_{secrets.token_hex(4)}@example.com".lower()
        r = requests.post(f"{API}/auth/register",
                          json={"email": email, "password": "tfqa12345"}, timeout=20)
        assert r.status_code == 200, r.text
        tok = r.json()["token"]
        r = requests.get(f"{API}/auth/me", headers=_bearer(tok))
        assert r.status_code == 200
        assert r.json()["email"] == email

    def test_optimize_public(self):
        r = requests.post(f"{API}/optimize",
                          json={"text": "Please optimize this text quickly and efficiently."},
                          timeout=30)
        assert r.status_code == 200, r.text

    def test_billing_plans(self):
        r = requests.get(f"{API}/billing/plans", timeout=20)
        assert r.status_code == 200
        assert "plans" in r.json()

    def test_billing_checkout_monthly(self):
        tok = _login(*ADMIN)
        r = requests.post(f"{API}/billing/checkout",
                          json={"plan_id": "starter", "origin_url": BASE,
                                "billing_cycle": "monthly"},
                          headers=_bearer(tok), timeout=20)
        assert r.status_code < 500

    def test_billing_checkout_annual(self):
        tok = _login(*ADMIN)
        r = requests.post(f"{API}/billing/checkout",
                          json={"plan_id": "starter", "origin_url": BASE,
                                "billing_cycle": "annual"},
                          headers=_bearer(tok), timeout=20)
        assert r.status_code < 500

    def test_reports_savings_pdf(self):
        tok = _login(*ADMIN)
        r = requests.get(f"{API}/reports/savings.pdf", headers=_bearer(tok), timeout=30)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_dashboard_overview(self):
        tok = _login(*ADMIN)
        r = requests.get(f"{API}/dashboard/overview", headers=_bearer(tok), timeout=20)
        assert r.status_code == 200

    def test_admin_overview_admin_ok(self):
        tok = _login(*ADMIN)
        r = requests.get(f"{API}/admin/overview", headers=_bearer(tok), timeout=20)
        assert r.status_code == 200

    def test_admin_overview_non_admin_forbidden(self):
        email = f"TEST_iter7_rbac_{secrets.token_hex(4)}@example.com".lower()
        r = requests.post(f"{API}/auth/register",
                          json={"email": email, "password": "tfqa12345"}, timeout=20)
        assert r.status_code == 200
        tok = r.json()["token"]
        r = requests.get(f"{API}/admin/overview", headers=_bearer(tok))
        assert r.status_code in (401, 403)

    def test_share_create_and_get(self):
        tok = _login(*ADMIN)
        r = requests.post(f"{API}/share/savings", headers=_bearer(tok))
        assert r.status_code == 200
        slug = r.json()["slug"]
        pub = requests.get(f"{API}/share/savings/{slug}", timeout=20)
        assert pub.status_code == 200
        for k in ("display_name", "tokens_saved", "cost_saved_usd",
                  "requests", "avg_compression_pct"):
            assert k in pub.json()
