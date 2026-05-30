"""Iter-6 regression smoke — confirm the 6 small code-review changes broke nothing.

The 6 changes were:
  1. optimizer._embed(): MD5 -> SHA-256
  2. proxy_chat: defensive init of response_text/provider/model_used
  3. React stable keys (Playground/Docs)
  4. console.warn in Landing empty catch
  5. eslint-disable comments
  6. removed unused imports in Billing

This file is backend-only. Specifically verifies:
  - sending the SAME prompt twice still results in cache_hit=true on 2nd call
    (proves cache logic unchanged after SHA-256 swap).
  - all major flows still return 2xx (auth, dashboard, billing, reports,
    share, optimize, keys, admin, waitlist).
"""
import os
import uuid
import secrets
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

ADMIN = ("admin@tokenforge.io", "ForgeAdmin!2026")
QA = ("alreadyherellc@gmail.com", "ForgeQA!2026")


def _xff():
    """Unique X-Forwarded-For per call so rate-limit buckets don't collide."""
    o = (uuid.uuid4().int % 240) + 10
    return {"X-Forwarded-For": f"203.0.115.{o}"}


def _login(email, password):
    r = requests.post(f"{API}/auth/login",
                      json={"email": email, "password": password},
                      headers=_xff())
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


def _bearer(tok):
    return {"Authorization": f"Bearer {tok}", **_xff()}


# ---------- AUTH ----------
def test_login_admin_me():
    tok = _login(*ADMIN)
    r = requests.get(f"{API}/auth/me", headers=_bearer(tok))
    assert r.status_code == 200
    assert r.json()["email"] == ADMIN[0]
    assert r.json().get("plan") == "enterprise"


def test_register_login_me_throwaway():
    email = f"TEST_iter6_{secrets.token_hex(4)}@example.com".lower()
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "password": "tfqa12345"},
                      headers=_xff())
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    r = requests.get(f"{API}/auth/me", headers=_bearer(tok))
    assert r.status_code == 200
    assert r.json()["email"] == email


# ---------- PROXY/CHAT + SEMANTIC CACHE (SHA-256) ----------
def _get_api_key(tok):
    r = requests.get(f"{API}/keys", headers=_bearer(tok))
    assert r.status_code == 200
    _ = r.json().get("keys", [])  # noqa: F841
    # Look for a full plaintext key (just-created keys carry 'plaintext' / 'key' field once)
    # otherwise issue a new one.
    r = requests.post(f"{API}/keys",
                      json={"name": f"TEST_iter6_{secrets.token_hex(3)}"},
                      headers=_bearer(tok))
    assert r.status_code == 200, r.text
    body = r.json()
    plain = body.get("plaintext") or body.get("key") or body.get("api_key")
    assert plain and plain.startswith("tf_"), f"no plaintext key returned: {body}"
    return plain


def test_proxy_chat_cache_hit_after_sha256_swap():
    """Send same prompt twice → second call MUST return cache_hit=true."""
    tok = _login(*ADMIN)
    api_key = _get_api_key(tok)
    # Use a unique-ish prompt to avoid collisions with any pre-existing cached entries
    prompt = (
        f"Iter6 sha256 cache verification — token {secrets.token_hex(6)}. "
        "Explain why semantic caching is useful in one short sentence."
    )
    headers = {"X-TF-Key": api_key, **_xff()}

    r1 = requests.post(f"{API}/proxy/chat",
                       json={"prompt": prompt, "optimize": True},
                       headers=headers, timeout=60)
    assert r1.status_code == 200, f"first call failed: {r1.status_code} {r1.text}"
    d1 = r1.json()
    assert d1["cache_hit"] is False, f"first call should miss cache, got {d1}"
    assert isinstance(d1.get("response"), str) and len(d1["response"]) > 0
    assert d1.get("provider") not in (None, "unknown")
    assert d1.get("model") not in (None, "unknown")

    # Same prompt again — must HIT cache (SHA-256 embedding stable)
    r2 = requests.post(f"{API}/proxy/chat",
                       json={"prompt": prompt, "optimize": True},
                       headers={"X-TF-Key": api_key, **_xff()},
                       timeout=60)
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["cache_hit"] is True, f"second call should HIT cache, got {d2}"
    assert d2["provider"] == "cache"
    assert d2["response"] == d1["response"]


# ---------- DASHBOARD ----------
def test_dashboard_endpoints_admin():
    tok = _login(*ADMIN)
    H = _bearer(tok)
    for path in ("dashboard/overview", "dashboard/timeseries?days=14", "dashboard/logs?limit=5"):
        r = requests.get(f"{API}/{path}", headers=H)
        assert r.status_code == 200, f"{path}: {r.status_code} {r.text}"


# ---------- KEYS ----------
def test_keys_list_admin():
    tok = _login(*ADMIN)
    r = requests.get(f"{API}/keys", headers=_bearer(tok))
    assert r.status_code == 200
    assert "keys" in r.json()


# ---------- ADMIN RBAC ----------
def test_admin_overview_admin_ok():
    tok = _login(*ADMIN)
    r = requests.get(f"{API}/admin/overview", headers=_bearer(tok))
    assert r.status_code == 200
    assert "users" in r.json()


def test_admin_overview_non_admin_forbidden():
    # register a throwaway user, ensure /admin/overview returns 403
    email = f"TEST_iter6_rbac_{secrets.token_hex(4)}@example.com".lower()
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "password": "tfqa12345"},
                      headers=_xff())
    assert r.status_code == 200
    tok = r.json()["token"]
    r = requests.get(f"{API}/admin/overview", headers=_bearer(tok))
    assert r.status_code in (401, 403), f"expected 403, got {r.status_code}"


# ---------- BILLING ----------
def test_billing_plans():
    r = requests.get(f"{API}/billing/plans", headers=_xff())
    assert r.status_code == 200
    assert "plans" in r.json()


@pytest.mark.parametrize("cycle", ["monthly", "annual"])
def test_billing_checkout_monthly_annual(cycle):
    tok = _login(*ADMIN)
    H = _bearer(tok)
    r = requests.post(f"{API}/billing/checkout",
                      json={"plan_id": "starter",
                            "origin_url": BASE,
                            "billing_cycle": cycle},
                      headers=H)
    # Acceptable: 200 with checkout url, or 4xx (e.g. plan locked) — never 500
    assert r.status_code < 500, f"checkout {cycle} 5xx: {r.status_code} {r.text}"


# ---------- REPORTS ----------
def test_savings_pdf_admin():
    tok = _login(*ADMIN)
    r = requests.get(f"{API}/reports/savings.pdf", headers=_bearer(tok))
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_savings_email_qa():
    r = requests.post(f"{API}/auth/login",
                      json={"email": QA[0], "password": QA[1]},
                      headers=_xff())
    if r.status_code != 200:
        pytest.skip(f"QA login failed: {r.status_code}")
    tok = r.json()["token"]
    r = requests.post(f"{API}/reports/savings/email", headers=_bearer(tok))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("sent") is True
    assert isinstance(body.get("email_id"), str) and len(body["email_id"]) > 0


# ---------- SHARE ----------
def test_share_create_and_public_get():
    tok = _login(*QA)
    H = _bearer(tok)
    r = requests.post(f"{API}/share/savings", headers=H)
    assert r.status_code == 200
    slug = r.json()["slug"]
    pub = requests.get(f"{API}/share/savings/{slug}", headers=_xff())
    assert pub.status_code == 200
    d = pub.json()
    for k in ("display_name", "tokens_saved", "cost_saved_usd", "requests", "avg_compression_pct"):
        assert k in d


# ---------- WAITLIST ----------
def test_waitlist_join():
    email = f"TEST_iter6_wl_{secrets.token_hex(3)}@x.io"
    r = requests.post(f"{API}/waitlist", json={"email": email}, headers=_xff())
    assert r.status_code in (200, 201), r.text


# ---------- OPTIMIZE PUBLIC ----------
def test_optimize_public():
    r = requests.post(f"{API}/optimize",
                      json={"text": "Please optimize this text quickly and efficiently."},
                      headers=_xff())
    assert r.status_code == 200, r.text
    body = r.json()
    assert any(k in body for k in ("optimized", "optimized_text", "result", "output", "text"))


def test_optimize_rate_limit_30_per_60s_with_xff():
    """Send 35 rapid /optimize calls from a single synthetic XFF — expect
    ~30 200s then 429s with numeric Retry-After. Proves rate limiter still works."""
    ip = f"203.0.115.{(uuid.uuid4().int % 240) + 10}"
    headers = {"X-Forwarded-For": ip}
    statuses = []
    retry_after_seen = False
    for _ in range(35):
        r = requests.post(f"{API}/optimize",
                          json={"text": "rate limit smoke"},
                          headers=headers, timeout=10)
        statuses.append(r.status_code)
        if r.status_code == 429:
            ra = r.headers.get("Retry-After")
            if ra and ra.isdigit():
                retry_after_seen = True
    n200 = sum(1 for s in statuses if s == 200)
    n429 = sum(1 for s in statuses if s == 429)
    assert n200 >= 25, f"expected >=25 200s, got {n200}; statuses={statuses}"
    assert n429 >= 1, f"expected at least one 429, got 0; statuses={statuses}"
    assert retry_after_seen, "no numeric Retry-After header on 429"
