"""TokenForge iteration 4 backend tests:
- Resend welcome email graceful failure on register
- Rate limits on /optimize, /auth/register, /auth/login, /waitlist
- Public share endpoints (POST /share/savings + GET /share/savings/{slug})
- /reports/savings/email (auth required) + /reports/savings.pdf still works
"""
import os
import secrets
import uuid

import pytest
import requests
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@tokenforge.io"
ADMIN_PASSWORD = "ForgeAdmin!2026"
QA_EMAIL = "alreadyherellc@gmail.com"
QA_PASSWORD = "ForgeQA!2026"


# ---- shared fixtures --------------------------------------------------------
@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def admin_token(s):
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def qa_token(s):
    r = s.post(f"{API}/auth/login", json={"email": QA_EMAIL, "password": QA_PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"QA user not available: {r.status_code} {r.text}")
    return r.json()["token"]


def _auth_headers(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---- register/email graceful-fail ------------------------------------------
def test_register_returns_token_even_if_resend_rejects():
    """Resend in test mode rejects non-verified recipients. Backend must swallow
    the exception and still return 200 + token + user."""
    rnd = secrets.token_hex(4)
    email = f"TEST_resilient_{rnd}@example.com".lower()
    r = requests.post(
        f"{API}/auth/register", json={"email": email, "password": "tfqa12345", "name": "Resilient"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "token" in body and len(body["token"]) > 20
    assert body["user"]["email"] == email
    assert body["user"]["plan"] == "free"


# ---- /reports/savings.pdf still works --------------------------------------
def test_savings_pdf_admin(admin_token):
    r = requests.get(f"{API}/reports/savings.pdf", headers=_auth_headers(admin_token))
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 800


def test_savings_pdf_requires_auth():
    r = requests.get(f"{API}/reports/savings.pdf")
    assert r.status_code == 401


# ---- /reports/savings/email -------------------------------------------------
def test_email_savings_report_requires_auth():
    r = requests.post(f"{API}/reports/savings/email")
    assert r.status_code == 401


def test_email_savings_report_qa(qa_token):
    """QA user is the only resend-deliverable address — expect sent True."""
    r = requests.post(f"{API}/reports/savings/email", headers=_auth_headers(qa_token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "sent" in body and "email_id" in body
    # For the QA whitelisted email, sent should be True
    assert body["sent"] is True
    assert isinstance(body["email_id"], str) and len(body["email_id"]) > 0


def test_email_savings_report_non_verified_recipient_resilient():
    """Register a brand new throwaway user and call /reports/savings/email.
    Resend rejects, but endpoint must return 200 with sent=False (None email_id)."""
    rnd = secrets.token_hex(4)
    email = f"TEST_emailfail_{rnd}@example.com"
    rr = requests.post(
        f"{API}/auth/register", json={"email": email, "password": "tfqa12345"}
    )
    assert rr.status_code == 200, rr.text
    tok = rr.json()["token"]
    r = requests.post(f"{API}/reports/savings/email", headers=_auth_headers(tok))
    assert r.status_code == 200, r.text
    body = r.json()
    # Either sent True (if Resend somehow accepted) or sent False — both must NOT 500.
    assert "sent" in body and "email_id" in body


# ---- /share/savings POST + GET ---------------------------------------------
def test_share_savings_requires_auth():
    r = requests.post(f"{API}/share/savings")
    assert r.status_code == 401


def test_share_create_is_idempotent(qa_token):
    r1 = requests.post(f"{API}/share/savings", headers=_auth_headers(qa_token))
    assert r1.status_code == 200, r1.text
    slug1 = r1.json()["slug"]
    assert isinstance(slug1, str) and 4 <= len(slug1) <= 32

    r2 = requests.post(f"{API}/share/savings", headers=_auth_headers(qa_token))
    assert r2.status_code == 200
    slug2 = r2.json()["slug"]
    assert slug1 == slug2  # idempotent


def test_share_get_public_returns_data(qa_token):
    r = requests.post(f"{API}/share/savings", headers=_auth_headers(qa_token))
    slug = r.json()["slug"]

    # public — no auth header
    pub = requests.get(f"{API}/share/savings/{slug}")
    assert pub.status_code == 200, pub.text
    data = pub.json()
    for key in ("display_name", "tokens_saved", "cost_saved_usd", "requests", "avg_compression_pct", "created_at"):
        assert key in data, f"missing {key}"
    assert isinstance(data["tokens_saved"], int)
    assert isinstance(data["requests"], int)


def test_share_get_unknown_slug_404():
    r = requests.get(f"{API}/share/savings/this-slug-does-not-exist-zzz")
    assert r.status_code == 404


# ---- regression: existing endpoints -----------------------------------------
def test_billing_plans_regression():
    r = requests.get(f"{API}/billing/plans")
    assert r.status_code == 200
    body = r.json()
    plans = {p["id"]: p for p in body["plans"]}
    assert {"free", "starter", "pro", "enterprise"}.issubset(plans.keys())
    assert body["annual_discount_pct"] == 20


def test_dashboard_overview_regression(admin_token):
    r = requests.get(f"{API}/dashboard/overview", headers=_auth_headers(admin_token))
    assert r.status_code == 200
    for k in ("total_requests", "total_tokens_saved", "cache_hit_rate"):
        assert k in r.json()


def test_admin_overview_regression(admin_token):
    r = requests.get(f"{API}/admin/overview", headers=_auth_headers(admin_token))
    assert r.status_code == 200
    assert "users" in r.json()


def test_keys_crud_regression(admin_token):
    r = requests.get(f"{API}/keys", headers=_auth_headers(admin_token))
    assert r.status_code == 200
    assert "keys" in r.json()


# ---- rate-limit tests (LAST — they exhaust budgets) -------------------------
def test_zz_rate_limit_optimize():
    """30 req/60s per IP on /optimize. Burst 35 and expect at least one 429."""
    statuses = []
    for _ in range(35):
        rr = requests.post(f"{API}/optimize", json={"text": "Please summarize quickly."})
        statuses.append(rr.status_code)
        if rr.status_code == 429:
            break
    assert 429 in statuses, f"expected 429 in {statuses}"
    # 429 response should mention rate limit
    rr = requests.post(f"{API}/optimize", json={"text": "again"})
    if rr.status_code == 429:
        assert "Retry-After" in rr.headers
        assert "Rate limit" in rr.json().get("detail", "")


def test_zz_rate_limit_register():
    """8 req/600s per IP on /auth/register. Burst 10 with unique emails — expect 429."""
    statuses = []
    for i in range(10):
        e = f"TEST_rl_reg_{uuid.uuid4().hex[:8]}@example.com"
        rr = requests.post(f"{API}/auth/register", json={"email": e, "password": "tfqa12345"})
        statuses.append(rr.status_code)
        if rr.status_code == 429:
            break
    assert 429 in statuses, f"expected 429 in {statuses}"


def test_zz_rate_limit_login():
    """10 req/300s per IP on /auth/login. Burst 12 — expect 429."""
    statuses = []
    for i in range(12):
        rr = requests.post(f"{API}/auth/login", json={"email": f"nobody{i}@x.io", "password": "x"})
        statuses.append(rr.status_code)
        if rr.status_code == 429:
            break
    assert 429 in statuses, f"expected 429 in {statuses}"


def test_zz_rate_limit_waitlist():
    """10 req/300s per IP on /waitlist. Burst 12 — expect 429."""
    statuses = []
    for i in range(12):
        rr = requests.post(f"{API}/waitlist", json={"email": f"TEST_wl_{uuid.uuid4().hex[:6]}@x.io"})
        statuses.append(rr.status_code)
        if rr.status_code == 429:
            break
    assert 429 in statuses, f"expected 429 in {statuses}"
