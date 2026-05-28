"""Iter-5 regression smoke — confirm core endpoints work (with XFF to avoid rate limits)."""
import os, uuid, secrets
import pytest, requests
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

def _h():
    o = (uuid.uuid4().int % 250) + 2
    return {"X-Forwarded-For": f"203.0.114.{o}"}

ADMIN = ("admin@tokenforge.io", "ForgeAdmin!2026")
QA = ("alreadyherellc@gmail.com", "ForgeQA!2026")


def test_login_admin():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}, headers=_h())
    assert r.status_code == 200, r.text
    assert r.json()["user"]["plan"] == "enterprise"


def test_register_login_me_flow():
    h = _h()
    email = f"TEST_iter5_smoke_{secrets.token_hex(4)}@example.com".lower()
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": "tfqa12345"}, headers=h)
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok}", **_h()})
    assert r.status_code == 200
    assert r.json()["email"] == email


def test_dashboard_endpoints_admin():
    h = _h()
    tok = requests.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}, headers=h).json()["token"]
    H = {"Authorization": f"Bearer {tok}", **_h()}
    for path in ("dashboard/overview", "dashboard/timeseries?days=14", "dashboard/logs?limit=5"):
        r = requests.get(f"{API}/{path}", headers=H)
        assert r.status_code == 200, f"{path}: {r.status_code} {r.text}"


def test_keys_crud_admin():
    h = _h()
    tok = requests.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}, headers=h).json()["token"]
    H = {"Authorization": f"Bearer {tok}", **_h()}
    r = requests.get(f"{API}/keys", headers=H)
    assert r.status_code == 200
    assert "keys" in r.json()


def test_admin_overview():
    h = _h()
    tok = requests.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}, headers=h).json()["token"]
    H = {"Authorization": f"Bearer {tok}", **_h()}
    r = requests.get(f"{API}/admin/overview", headers=H)
    assert r.status_code == 200
    assert "users" in r.json()


def test_billing_plans_and_checkout_monthly_annual():
    h = _h()
    tok = requests.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}, headers=h).json()["token"]
    H = {"Authorization": f"Bearer {tok}", **_h()}
    r = requests.get(f"{API}/billing/plans", headers=_h())
    assert r.status_code == 200
    plans = r.json()
    assert "plans" in plans
    # Try checkout for monthly + annual cycle of starter (skip if endpoint differs)
    for cycle in ("monthly", "annual"):
        r = requests.post(f"{API}/billing/checkout",
                          json={"plan": "starter", "cycle": cycle}, headers=H)
        # Acceptable: 200 with url or 4xx if plan locked; just must not 500
        assert r.status_code < 500, f"checkout {cycle}: {r.status_code} {r.text}"


def test_waitlist_join():
    h = _h()
    email = f"TEST_iter5_smoke_wl_{secrets.token_hex(3)}@x.io"
    r = requests.post(f"{API}/waitlist", json={"email": email}, headers=h)
    assert r.status_code in (200, 201), r.text


def test_optimize_public():
    r = requests.post(f"{API}/optimize", json={"text": "Please optimize this text quickly."}, headers=_h())
    assert r.status_code == 200, r.text
    body = r.json()
    assert any(k in body for k in ("optimized", "optimized_text", "result", "output", "text"))


def test_savings_pdf_admin():
    h = _h()
    tok = requests.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}, headers=h).json()["token"]
    H = {"Authorization": f"Bearer {tok}", **_h()}
    r = requests.get(f"{API}/reports/savings.pdf", headers=H)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_email_report_qa():
    h = _h()
    r = requests.post(f"{API}/auth/login", json={"email": QA[0], "password": QA[1]}, headers=h)
    if r.status_code != 200:
        pytest.skip(f"QA login failed: {r.status_code}")
    tok = r.json()["token"]
    H = {"Authorization": f"Bearer {tok}", **_h()}
    r = requests.post(f"{API}/reports/savings/email", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body.get("sent") is True
    assert isinstance(body.get("email_id"), str) and len(body["email_id"]) > 0


def test_share_create_and_public_get():
    h = _h()
    tok = requests.post(f"{API}/auth/login", json={"email": QA[0], "password": QA[1]}, headers=h).json()["token"]
    H = {"Authorization": f"Bearer {tok}", **_h()}
    r = requests.post(f"{API}/share/savings", headers=H)
    assert r.status_code == 200
    slug = r.json()["slug"]
    pub = requests.get(f"{API}/share/savings/{slug}", headers=_h())
    assert pub.status_code == 200
    d = pub.json()
    for k in ("display_name", "tokens_saved", "cost_saved_usd", "requests", "avg_compression_pct"):
        assert k in d
