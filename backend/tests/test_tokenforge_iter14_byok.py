"""TokenForge iter-14 BYOK + plan-gating + regression tests."""
import os
import time
import uuid
import requests
import pytest
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://market-launch-43.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@tokenforge.io"
ADMIN_PASSWORD = "ForgeAdmin!2026"
GOOGLE_KEY = "AIzaSyCVAAmQUhhxCqtIm88w6U6u2cbzzZYn8oc"

API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def free_user():
    rnd = uuid.uuid4().hex[:8]
    email = f"qa+byok_{rnd}@alreadyherellc.com"
    pw = "ForgeQA!2026"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": pw, "name": "QA"}, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    return {"email": email, "password": pw, "token": j["token"], "user": j["user"]}


@pytest.fixture(scope="module")
def free_headers(free_user):
    return {"Authorization": f"Bearer {free_user['token']}"}


# ----- emergentintegrations uninstalled -----
def test_emergentintegrations_not_importable():
    try:
        import emergentintegrations  # noqa: F401
        pytest.fail("emergentintegrations still importable — should have been uninstalled")
    except ImportError:
        pass


# ----- BYOK paywall (free user) -----
def test_byok_free_post_returns_402(free_headers):
    r = requests.post(f"{API}/byok", json={"provider": "google", "api_key": GOOGLE_KEY}, headers=free_headers, timeout=15)
    assert r.status_code == 402, r.text
    assert "BYO Keys is a Pro / Enterprise feature" in r.text


def test_byok_free_get_locked(free_headers):
    r = requests.get(f"{API}/byok", headers=free_headers, timeout=15)
    assert r.status_code == 200
    j = r.json()
    assert j["byok_unlocked"] is False
    assert j["plan"] == "free"
    assert j["keys"] == []


# ----- BYOK admin store/validate/list/delete -----
def test_byok_admin_store_valid_google(admin_headers):
    r = requests.post(f"{API}/byok", json={"provider": "google", "api_key": GOOGLE_KEY}, headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["provider"] == "google"
    assert j["ok"] is True
    assert j["masked"].startswith("AIza") and "…" in j["masked"]


def test_byok_admin_invalid_openai_key(admin_headers):
    r = requests.post(f"{API}/byok", json={"provider": "openai", "api_key": "not-a-real-key-xxxxxxxxxx"}, headers=admin_headers, timeout=15)
    assert r.status_code == 400, r.text
    assert "sk-" in r.json().get("detail", "")


def test_byok_admin_list_keys(admin_headers):
    r = requests.get(f"{API}/byok", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    j = r.json()
    assert j["byok_unlocked"] is True
    assert j["plan"] == "enterprise"
    assert set(j["supported_providers"]) == {"openai", "anthropic", "google"}
    google_keys = [k for k in j["keys"] if k["provider"] == "google"]
    assert len(google_keys) == 1
    assert google_keys[0]["masked"].startswith("AIza")
    assert google_keys[0]["created_at"]


def test_byok_encryption_at_rest():
    """Directly inspect Mongo doc — raw key must NOT appear."""
    mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = mongo[os.environ.get("DB_NAME", "tokenforge")]
    doc = db.byok_keys.find_one({"provider": "google"})
    assert doc is not None, "no byok_keys doc found"
    enc = doc.get("encrypted_key", "")
    assert "AIza" not in enc, f"raw key leaked in encrypted_key: {enc}"
    assert "sk-" not in enc
    # Fernet tokens are urlsafe-base64 and start with 'gAAAAA'
    assert enc.startswith("gAAAAA"), f"not Fernet ciphertext: {enc[:20]}"


def test_byok_admin_delete_google(admin_headers):
    # Re-store first to ensure present
    requests.post(f"{API}/byok", json={"provider": "google", "api_key": GOOGLE_KEY}, headers=admin_headers, timeout=15)
    r = requests.delete(f"{API}/byok/google", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    j = r.json()
    assert j["deleted"] == 1
    assert j["provider"] == "google"
    # Confirm gone
    r2 = requests.get(f"{API}/byok", headers=admin_headers, timeout=15)
    j2 = r2.json()
    googles = [k for k in j2["keys"] if k["provider"] == "google"]
    assert googles == []


# ----- Plan gating on /api/proxy/chat -----
def _get_first_key(token):
    r = requests.get(f"{API}/keys", headers={"Authorization": f"Bearer {token}"}, timeout=15)
    assert r.status_code == 200
    return r.json()["keys"][0]["key"]


def test_proxy_chat_free_user_force_routed_to_gemini(free_user):
    tf_key = _get_first_key(free_user["token"])
    r = requests.post(
        f"{API}/proxy/chat",
        json={"prompt": "Say PONG in one word.", "provider": "openai", "model": "gpt-4o", "optimize": False},
        headers={"X-TF-Key": tf_key},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["provider"] == "google"
    assert j["model"] == "gemini-2.5-flash"
    assert j.get("platform_note")
    assert "Free/Starter" in j["platform_note"]
    assert "Upgrade to Pro" in j["platform_note"]


def test_proxy_chat_admin_with_byok_real_gemini(admin_headers, admin_token):
    # Re-store BYOK google key
    requests.post(f"{API}/byok", json={"provider": "google", "api_key": GOOGLE_KEY}, headers=admin_headers, timeout=15)
    tf_key = _get_first_key(admin_token)
    r = requests.post(
        f"{API}/proxy/chat",
        json={"prompt": "Reply with the single word PONG.", "provider": "google", "model": "gemini-2.5-flash", "optimize": False},
        headers={"X-TF-Key": tf_key},
        timeout=90,
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["provider"] == "google"
    assert j["model"] == "gemini-2.5-flash"
    assert isinstance(j["response"], str) and len(j["response"]) > 0
    assert j.get("platform_note") in (None, "")


# ----- Regression happy path -----
def test_regression_full_happy_path():
    rnd = uuid.uuid4().hex[:8]
    email = f"qa+regress_{rnd}@alreadyherellc.com"
    pw = "ForgeQA!2026"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": pw}, timeout=30)
    assert r.status_code == 200
    token = r.json()["token"]
    h = {"Authorization": f"Bearer {token}"}

    # /auth/me
    me = requests.get(f"{API}/auth/me", headers=h, timeout=15)
    assert me.status_code == 200
    assert me.json()["email"] == email

    # /keys
    keys = requests.get(f"{API}/keys", headers=h, timeout=15)
    assert keys.status_code == 200
    karr = keys.json()["keys"]
    assert len(karr) >= 1
    tf_key = karr[0]["key"]

    # proxy chat — gemini force-routed
    pc = requests.post(
        f"{API}/proxy/chat",
        json={"prompt": "ping", "provider": "google", "model": "gemini-2.5-flash", "optimize": True},
        headers={"X-TF-Key": tf_key},
        timeout=60,
    )
    assert pc.status_code == 200, pc.text

    # dashboard overview
    ov = requests.get(f"{API}/dashboard/overview", headers=h, timeout=15)
    assert ov.status_code == 200

    # billing checkout (LIVE)
    co = requests.post(
        f"{API}/billing/checkout",
        json={"plan_id": "starter", "origin_url": BASE_URL, "billing_cycle": "monthly"},
        headers=h, timeout=30,
    )
    assert co.status_code == 200, co.text
    url = co.json()["url"]
    assert "cs_live_" in url or "checkout.stripe.com" in url

    # savings PDF
    pdf = requests.get(f"{API}/reports/savings.pdf", headers=h, timeout=30)
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"

    # webhook bogus sig
    wh = requests.post(f"{API}/webhook/stripe", data=b"{}", headers={"stripe-signature": "bogus"}, timeout=15)
    # Endpoint should accept call gracefully and return received:false (per problem statement)
    assert wh.status_code in (200, 400)
    if wh.status_code == 200:
        assert wh.json().get("received") is False
