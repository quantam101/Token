"""TokenForge enhancement tests (iteration 3):
- /auth/me returns usage{}
- /proxy/chat quota enforcement (HTTP 429) via MongoDB quota mutation
- /billing/plans includes 'free' + annual_amount + 20% discount
- /billing/checkout accepts billing_cycle='annual' and stores annual price + cycle in payment_transactions
- /reports/savings.pdf 401 w/o auth, 200 + %PDF magic bytes w/ admin token
"""
import os
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@tokenforge.io"
ADMIN_PASSWORD = "ForgeAdmin!2026"

RUN_TAG = uuid.uuid4().hex[:8]
QA_EMAIL = f"TEST_qa_quota_{RUN_TAG}@tokenforge.io"
QA_PASSWORD = "qaforge123"


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def mongo_db():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = MongoClient(mongo_url)
    try:
        yield client[db_name]
    finally:
        client.close()


@pytest.fixture(scope="session")
def admin_token(session):
    r = session.post(f"{API}/auth/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def qa_user(session):
    r = session.post(f"{API}/auth/register",
                     json={"email": QA_EMAIL, "password": QA_PASSWORD, "name": "QA Quota"})
    assert r.status_code == 200, r.text
    d = r.json()
    # get api key
    rk = session.get(f"{API}/keys",
                     headers={"Authorization": f"Bearer {d['token']}"})
    assert rk.status_code == 200
    keys = rk.json()["keys"]
    assert len(keys) >= 1
    return {"token": d["token"], "id": d["user"]["id"], "email": d["user"]["email"], "api_key": keys[0]["key"]}


# ---------------- /auth/me usage object ----------------
def test_me_returns_usage_object(session, qa_user):
    r = session.get(f"{API}/auth/me",
                    headers={"Authorization": f"Bearer {qa_user['token']}"})
    assert r.status_code == 200
    d = r.json()
    assert "usage" in d, f"missing usage on /auth/me: {d}"
    u = d["usage"]
    for k in ("period_start", "tokens_used", "requests", "tokens_saved",
              "monthly_quota", "percent_used"):
        assert k in u, f"usage missing {k}: {u}"
    assert isinstance(u["tokens_used"], int)
    assert isinstance(u["requests"], int)
    assert isinstance(u["monthly_quota"], int)
    assert isinstance(u["percent_used"], (int, float))


# ---------------- Billing plans ----------------
def test_billing_plans_includes_free_and_annual(session):
    r = session.get(f"{API}/billing/plans")
    assert r.status_code == 200
    body = r.json()
    plans = body["plans"]
    assert body.get("annual_discount_pct") == 20
    by_id = {p["id"]: p for p in plans}
    assert "free" in by_id, f"expected 'free' plan: {by_id.keys()}"
    assert by_id["free"]["amount"] == 0
    for pid in ("starter", "pro", "enterprise"):
        assert pid in by_id
        assert "annual_amount" in by_id[pid]
        # 20% discount sanity check (annual ~= monthly*12*0.8)
        expected = round(by_id[pid]["amount"] * 12 * 0.8, 2)
        assert abs(by_id[pid]["annual_amount"] - expected) < 0.5, \
            f"{pid} annual mismatch: {by_id[pid]['annual_amount']} vs {expected}"


# ---------------- Billing checkout annual ----------------
def test_billing_checkout_annual_stores_cycle(session, qa_user, mongo_db):
    r = session.post(f"{API}/billing/checkout",
                     json={"plan_id": "pro", "origin_url": BASE_URL,
                           "billing_cycle": "annual"},
                     headers={"Authorization": f"Bearer {qa_user['token']}"},
                     timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("billing_cycle") == "annual"
    assert abs(d.get("amount", 0) - 950.40) < 0.5, f"unexpected pro annual amount: {d}"
    sid = d["session_id"]
    # Verify persistence
    rec = mongo_db.payment_transactions.find_one({"session_id": sid})
    assert rec is not None, "payment_transactions record missing"
    assert rec.get("billing_cycle") == "annual"
    assert abs(rec.get("amount", 0) - 950.40) < 0.5


# ---------------- Proxy quota 429 ----------------
def test_proxy_chat_quota_exceeded(session, qa_user, mongo_db):
    # First make 1 cheap call to bump usage above future tiny quota
    r1 = session.post(f"{API}/proxy/chat",
                      json={"prompt": "Say hi in one word.",
                            "provider": "openai", "model": "gpt-4o-mini",
                            "optimize": True},
                      headers={"X-TF-Key": qa_user["api_key"]},
                      timeout=90)
    assert r1.status_code == 200, r1.text

    # Now shrink quota to 1 token in MongoDB
    res = mongo_db.users.update_one({"id": qa_user["id"]},
                                    {"$set": {"monthly_quota": 1}})
    assert res.matched_count == 1, "user not found in mongo"

    # Next call should hit 429
    r2 = session.post(f"{API}/proxy/chat",
                      json={"prompt": "Another short prompt to test quota.",
                            "provider": "openai", "model": "gpt-4o-mini",
                            "optimize": True},
                      headers={"X-TF-Key": qa_user["api_key"]},
                      timeout=60)
    # Restore quota immediately to avoid cascading test pollution
    mongo_db.users.update_one({"id": qa_user["id"]},
                              {"$set": {"monthly_quota": 50_000}})
    assert r2.status_code == 429, f"expected 429, got {r2.status_code}: {r2.text}"
    detail = r2.json().get("detail", "")
    assert "Monthly quota exceeded" in detail, detail


# ---------------- ROI PDF report ----------------
def test_savings_pdf_requires_auth(session):
    r = session.get(f"{API}/reports/savings.pdf")
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"


def test_savings_pdf_with_admin(session, admin_token):
    r = session.get(f"{API}/reports/savings.pdf",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    timeout=60)
    assert r.status_code == 200, r.text[:200]
    ct = r.headers.get("Content-Type", "")
    assert "application/pdf" in ct, f"Content-Type: {ct}"
    cd = r.headers.get("Content-Disposition", "")
    assert "attachment" in cd.lower(), f"Content-Disposition: {cd}"
    body = r.content
    assert body[:4] == b"%PDF", f"bad magic: {body[:8]!r}"
    assert len(body) > 1024, f"PDF too small: {len(body)} bytes"
