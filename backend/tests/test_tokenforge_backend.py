"""TokenForge backend API tests.
Covers: health, waitlist, auth, optimizer, keys, proxy (LLM round-trip + cache),
dashboard analytics, billing (Stripe Checkout), admin.
"""
import os
import time
import uuid

import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@tokenforge.io"
ADMIN_PASSWORD = "ForgeAdmin!2026"

# unique per test run
RUN_TAG = uuid.uuid4().hex[:8]
USER_EMAIL = f"TEST_qa_{RUN_TAG}@tokenforge.io"
USER_PASSWORD = "qaforge123"
USER2_EMAIL = f"TEST_qa2_{RUN_TAG}@tokenforge.io"


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- session-scoped state ----------
state = {}


# ========== Health & public ==========
def test_health(session):
    r = session.get(f"{API}/")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("status") == "ok"
    assert d.get("service") == "TokenForge"


def test_public_stats(session):
    r = session.get(f"{API}/stats/public")
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("tokens_saved", "tokens_processed", "requests_optimized",
              "waitlist_count", "user_count"):
        assert k in d


# ========== Waitlist ==========
def test_waitlist_join_and_duplicate(session):
    email = f"TEST_wait_{RUN_TAG}@tokenforge.io"
    r1 = session.post(f"{API}/waitlist", json={"email": email, "company": "ACME"})
    assert r1.status_code == 200, r1.text
    assert r1.json().get("status") == "joined"
    r2 = session.post(f"{API}/waitlist", json={"email": email})
    assert r2.status_code == 200
    assert r2.json().get("status") == "already_on_waitlist"


# ========== Auth ==========
def test_register(session):
    r = session.post(f"{API}/auth/register",
                     json={"email": USER_EMAIL, "password": USER_PASSWORD, "name": "QA"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert "token" in d and d["user"]["email"] == USER_EMAIL.lower()
    state["token"] = d["token"]
    state["user_id"] = d["user"]["id"]


def test_register_duplicate(session):
    r = session.post(f"{API}/auth/register",
                     json={"email": USER_EMAIL, "password": USER_PASSWORD})
    assert r.status_code == 400


def test_login_invalid(session):
    r = session.post(f"{API}/auth/login",
                     json={"email": USER_EMAIL, "password": "wrong"})
    assert r.status_code == 401


def test_login_valid(session):
    r = session.post(f"{API}/auth/login",
                     json={"email": USER_EMAIL, "password": USER_PASSWORD})
    assert r.status_code == 200
    state["token"] = r.json()["token"]


def test_me_requires_token(session):
    r = session.get(f"{API}/auth/me")
    assert r.status_code == 401


def test_me_valid(session):
    r = session.get(f"{API}/auth/me",
                    headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    assert r.json()["email"] == USER_EMAIL.lower()


# ========== Optimize public ==========
def test_optimize_public(session):
    payload = {"text": "Could you please, in order to help me, summarize the following information about machine learning?"}
    r = session.post(f"{API}/optimize", json=payload)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["original_tokens"] > 0
    assert d["optimized_tokens"] <= d["original_tokens"]
    assert isinstance(d["pillars_applied"], list)
    assert len(d["pillars_applied"]) >= 1


# ========== API keys ==========
def test_list_keys_auto_created(session):
    r = session.get(f"{API}/keys",
                    headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    keys = r.json()["keys"]
    assert len(keys) >= 1
    state["api_key"] = keys[0]["key"]
    state["default_key_id"] = keys[0]["id"]


def test_create_key(session):
    r = session.post(f"{API}/keys", json={"name": "TEST_extra"},
                     headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    d = r.json()
    assert d["key"].startswith("tf_live_")
    state["extra_key_id"] = d["id"]


def test_revoke_key(session):
    r = session.delete(f"{API}/keys/{state['extra_key_id']}",
                       headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    # verify revoked
    r2 = session.get(f"{API}/keys",
                     headers={"Authorization": f"Bearer {state['token']}"})
    revoked = [k for k in r2.json()["keys"] if k["id"] == state["extra_key_id"]]
    assert revoked and revoked[0]["active"] is False


# ========== Proxy / chat ==========
def test_proxy_missing_key(session):
    r = session.post(f"{API}/proxy/chat",
                     json={"prompt": "hi"})
    assert r.status_code == 401


def test_proxy_invalid_key(session):
    r = session.post(f"{API}/proxy/chat",
                     json={"prompt": "hi"},
                     headers={"X-TF-Key": "tf_live_invalid"})
    assert r.status_code == 401


PROXY_PROMPT = "Please summarize in 2 sentences: artificial intelligence is changing software development by automating tasks."


def test_proxy_first_call_no_cache(session):
    r = session.post(
        f"{API}/proxy/chat",
        json={"prompt": PROXY_PROMPT,
              "provider": "openai", "model": "gpt-4o-mini", "optimize": True},
        headers={"X-TF-Key": state["api_key"]},
        timeout=90,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["cache_hit"] is False
    assert isinstance(d["response"], str) and len(d["response"]) > 0
    assert "tokens" in d and {"original", "optimized", "saved", "completion"} <= set(d["tokens"].keys())
    assert "cost_saved_usd" in d
    assert isinstance(d["pillars_applied"], list)
    state["first_response"] = d["response"]


def test_proxy_second_call_cache_hit(session):
    # Send identical prompt, expect cache_hit
    time.sleep(1)
    r = session.post(
        f"{API}/proxy/chat",
        json={"prompt": PROXY_PROMPT,
              "provider": "openai", "model": "gpt-4o-mini", "optimize": True},
        headers={"X-TF-Key": state["api_key"]},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["cache_hit"] is True, f"Expected cache hit, got {d}"
    assert d["tokens"]["saved"] > 0


def test_proxy_third_call_different_prompt(session):
    r = session.post(
        f"{API}/proxy/chat",
        json={"prompt": "Translate hello to French.",
              "provider": "openai", "model": "gpt-4o-mini", "optimize": True},
        headers={"X-TF-Key": state["api_key"]},
        timeout=90,
    )
    assert r.status_code == 200, r.text


# ========== Dashboard ==========
def test_dashboard_overview(session):
    r = session.get(f"{API}/dashboard/overview",
                    headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    d = r.json()
    assert d["total_requests"] >= 3
    assert d["total_tokens_saved"] >= 0
    assert d["total_cost_saved_usd"] >= 0
    assert 0 <= d["cache_hit_rate"] <= 100
    assert d["cache_hit_rate"] > 0  # at least one cache hit expected


def test_dashboard_timeseries(session):
    r = session.get(f"{API}/dashboard/timeseries?days=14",
                    headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    d = r.json()
    assert "series" in d and isinstance(d["series"], list)
    assert len(d["series"]) >= 1


def test_dashboard_logs(session):
    r = session.get(f"{API}/dashboard/logs?limit=10",
                    headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 200
    logs = r.json()["logs"]
    assert len(logs) >= 3
    for fld in ("provider", "model", "cache_hit", "tokens_saved", "cost_saved_usd"):
        assert fld in logs[0]


# ========== Billing ==========
def test_billing_plans(session):
    r = session.get(f"{API}/billing/plans")
    assert r.status_code == 200
    plans = r.json()["plans"]
    ids = {p["id"] for p in plans}
    assert {"starter", "pro", "enterprise"} <= ids


def test_billing_checkout(session):
    r = session.post(f"{API}/billing/checkout",
                     json={"plan_id": "starter", "origin_url": BASE_URL},
                     headers={"Authorization": f"Bearer {state['token']}"},
                     timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "url" in d and d["url"].startswith("http")
    assert "session_id" in d
    state["session_id"] = d["session_id"]


def test_billing_status_own(session):
    if not state.get("session_id"):
        pytest.skip("no session id")
    r = session.get(f"{API}/billing/status/{state['session_id']}",
                    headers={"Authorization": f"Bearer {state['token']}"},
                    timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "status" in d and "payment_status" in d


def test_billing_status_forbidden_other_user(session):
    # Register second user, attempt to fetch first user's session
    r = session.post(f"{API}/auth/register",
                     json={"email": USER2_EMAIL, "password": USER_PASSWORD})
    assert r.status_code == 200
    tok2 = r.json()["token"]
    r2 = session.get(f"{API}/billing/status/{state['session_id']}",
                     headers={"Authorization": f"Bearer {tok2}"},
                     timeout=60)
    assert r2.status_code == 403, r2.text


# ========== Admin ==========
def test_admin_non_admin_forbidden(session):
    r = session.get(f"{API}/admin/overview",
                    headers={"Authorization": f"Bearer {state['token']}"})
    assert r.status_code == 403


def test_admin_login_and_overview(session):
    r = session.post(f"{API}/auth/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    assert r.json()["user"]["role"] == "admin"
    r2 = session.get(f"{API}/admin/overview",
                     headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 200
    d = r2.json()
    for k in ("users", "waitlist", "requests", "paid_transactions",
              "revenue_usd", "total_tokens_saved", "recent_waitlist"):
        assert k in d
    assert isinstance(d["recent_waitlist"], list)
