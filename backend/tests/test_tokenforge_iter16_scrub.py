"""TokenForge iter-16 — Pre-sale Emergent-scrub validation + regression spine.

Validates:
  (A) Shipped code contains zero Emergent / PostHog references.
  (B) Served HTML at / is clean.
  (C) emergentintegrations is uninstalled.
  (D) Full backend regression spine still works (register, login, /auth/me,
      keys, /proxy/chat with Gemini, dashboard/overview, billing/checkout,
      reports/savings.pdf, /webhook/stripe).
  (E) BYOK still works for admin (list + provider/test).
  (F) BYOK negative test: store bogus Gemini key -> /proxy/chat with
      provider=google MUST fail with 502 (proves customer key is used).
      Restore real key at end.
  (G) Mongo db.byok_keys docs do NOT contain raw 'AIza' substring (encryption-at-rest).
"""
import os
import re
import subprocess
import uuid
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://market-launch-43.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@tokenforge.io"
ADMIN_PASSWORD = "ForgeAdmin!2026"
REAL_GOOGLE_KEY = "AIzaSyCVAAmQUhhxCqtIm88w6U6u2cbzzZYn8oc"
BOGUS_GOOGLE_KEY = "AIzaBOGUS_FAKE_KEY_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

SHIPPED_FILES = [
    "/app/backend/server.py",
    "/app/backend/llm_router.py",
    "/app/backend/stripe_service.py",
    "/app/backend/byok_service.py",
    "/app/backend/email_service.py",
    "/app/frontend/public/index.html",
    "/app/frontend/craco.config.js",
    "/app/frontend/package.json",
]


# ---------------- (A) Static scrub on shipped backend + select frontend files ----------------
class TestEmergentScrubShippedFiles:
    @pytest.mark.parametrize("path", SHIPPED_FILES)
    def test_no_emergent_or_posthog_in_shipped_file(self, path):
        assert os.path.exists(path), f"file missing: {path}"
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
        bad = re.findall(r"(?i)emergent|posthog", content)
        assert not bad, f"{path} contains forbidden tokens: {set(bad)}"

    def test_no_emergent_in_frontend_src(self):
        # Grep /app/frontend/src recursively (skip node_modules — N/A under src)
        res = subprocess.run(
            ["grep", "-rIn", "-iE", r"emergent|posthog", "/app/frontend/src"],
            capture_output=True, text=True,
        )
        hits = [
            ln for ln in res.stdout.splitlines()
            if ln.strip()
        ]
        assert not hits, "Found Emergent/PostHog refs in frontend/src:\n" + "\n".join(hits[:20])

    def test_emergentintegrations_uninstalled(self):
        res = subprocess.run(
            ["python3", "-c", "import emergentintegrations"],
            capture_output=True, text=True,
        )
        assert res.returncode != 0, "emergentintegrations should NOT be importable"
        assert "ModuleNotFoundError" in res.stderr or "ImportError" in res.stderr


# ---------------- (B) Served HTML scrub ----------------
class TestServedHtmlScrub:
    def test_served_html_clean(self):
        r = requests.get(f"{BASE_URL}/", timeout=20)
        assert r.status_code == 200
        body = r.text
        forbidden = [
            "emergent.sh", "emergent-main.js", "emergent-badge",
            "Made with Emergent", "posthog", "PostHog",
        ]
        found = [f for f in forbidden if f.lower() in body.lower()]
        assert not found, f"forbidden tokens in served HTML: {found}"


# ---------------- Auth fixtures ----------------
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                      timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def admin_tf_key(admin_token):
    r = requests.get(f"{API}/keys",
                     headers={"Authorization": f"Bearer {admin_token}"},
                     timeout=15)
    assert r.status_code == 200
    return r.json()["keys"][0]["key"]


@pytest.fixture(scope="module")
def new_free_user():
    rnd = uuid.uuid4().hex[:8]
    email = f"qa+iter16_{rnd}@alreadyherellc.com"
    pw = "ForgeQA!2026"
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "password": pw, "name": "Iter16 QA"},
                      timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    return {"email": email, "password": pw, "token": j["token"], "user": j["user"]}


# ---------------- (D) Regression spine ----------------
class TestRegressionSpine:
    def test_public_stats(self):
        r = requests.get(f"{API}/stats/public", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["user_count"] > 0
        assert d["tokens_saved"] > 0

    def test_register_login_me(self, new_free_user):
        # register already happened in fixture; verify login + /auth/me
        r = requests.post(f"{API}/auth/login",
                          json={"email": new_free_user["email"],
                                "password": new_free_user["password"]},
                          timeout=20)
        assert r.status_code == 200
        tok = r.json()["token"]
        me = requests.get(f"{API}/auth/me",
                          headers={"Authorization": f"Bearer {tok}"}, timeout=15)
        assert me.status_code == 200
        assert me.json()["email"] == new_free_user["email"]

    def test_admin_keys_list(self, admin_headers):
        r = requests.get(f"{API}/keys", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        assert "keys" in r.json()

    def test_dashboard_overview(self, admin_headers):
        r = requests.get(f"{API}/dashboard/overview", headers=admin_headers, timeout=20)
        assert r.status_code == 200

    def test_billing_checkout_returns_live_cs(self, admin_headers):
        r = requests.post(f"{API}/billing/checkout",
                          headers=admin_headers,
                          json={"plan_id": "pro",
                                "origin_url": BASE_URL}, timeout=30)
        # Either 200 with cs_live or 400/409 if admin already enterprise.
        if r.status_code == 200:
            j = r.json()
            url = j.get("url") or j.get("checkout_url", "")
            sid = j.get("session_id", "")
            assert ("cs_live_" in url) or ("cs_live_" in sid) or ("checkout.stripe.com" in url), j
        else:
            assert r.status_code in (400, 409), r.text

    def test_reports_savings_pdf(self, admin_headers):
        r = requests.get(f"{API}/reports/savings.pdf",
                         headers=admin_headers, timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").lower().startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_stripe_webhook_bogus_sig(self):
        r = requests.post(f"{API}/webhook/stripe",
                          headers={"stripe-signature": "bogus"},
                          data=b"{}", timeout=15)
        assert r.status_code == 200
        assert r.json().get("received") is False


# ---------------- (E) BYOK admin + provider/test ----------------
class TestBYOKAdmin:
    def test_byok_list_admin(self, admin_headers):
        r = requests.get(f"{API}/byok", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json().get("keys"), list)

    def test_byok_free_user_paywalled(self, new_free_user):
        r = requests.post(
            f"{API}/byok",
            headers={"Authorization": f"Bearer {new_free_user['token']}"},
            json={"provider": "google", "api_key": REAL_GOOGLE_KEY},
            timeout=15,
        )
        assert r.status_code == 402, r.text


# ---------------- (F) Critical BYOK negative test ----------------
class TestBYOKNegativeRouting:
    def test_proxy_chat_with_bogus_google_key_fails_502(self, admin_headers, admin_tf_key):
        # Save current real key
        store_bogus = requests.post(
            f"{API}/byok",
            headers=admin_headers,
            json={"provider": "google", "api_key": BOGUS_GOOGLE_KEY},
            timeout=20,
        )
        assert store_bogus.status_code in (200, 201), store_bogus.text

        try:
            chat = requests.post(
                f"{API}/proxy/chat",
                headers={"X-TF-Key": admin_tf_key, "Content-Type": "application/json"},
                json={
                    "provider": "google",
                    "model": "gemini-2.5-flash",
                    "prompt": "say PONG",
                    "optimize": False,
                },
                timeout=60,
            )
            assert chat.status_code == 502, (
                f"Expected 502 with bogus customer key; got {chat.status_code}: {chat.text[:200]}"
            )
        finally:
            # Restore real key
            restore = requests.post(
                f"{API}/byok",
                headers=admin_headers,
                json={"provider": "google", "api_key": REAL_GOOGLE_KEY},
                timeout=20,
            )
            assert restore.status_code in (200, 201), restore.text

    def test_proxy_chat_with_real_google_key_succeeds(self, admin_headers, admin_tf_key):
        chat = requests.post(
            f"{API}/proxy/chat",
            headers={"X-TF-Key": admin_tf_key, "Content-Type": "application/json"},
            json={
                "provider": "google",
                "model": "gemini-2.5-flash",
                "prompt": f"Echo: {uuid.uuid4().hex[:6]}",
                "optimize": False,
            },
            timeout=90,
        )
        if chat.status_code == 502 and ("RESOURCE_EXHAUSTED" in chat.text or "UNAVAILABLE" in chat.text or "503" in chat.text):
            pytest.skip("Google upstream transient (quota/503) — env-only failure")
        assert chat.status_code == 200, chat.text[:300]
        j = chat.json()
        assert j.get("provider") in ("google", "cache"), j


# ---------------- (G) Encryption-at-rest check ----------------
class TestEncryptionAtRest:
    def test_mongo_byok_keys_no_raw_aiza(self):
        # Use mongo CLI via subprocess
        try:
            from pymongo import MongoClient
        except ImportError:
            pytest.skip("pymongo not available")
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        db = client[db_name]
        docs = list(db.byok_keys.find({}))
        for d in docs:
            # Stringify every value except _id and look for raw 'AIza'
            for k, v in d.items():
                if k == "_id":
                    continue
                if isinstance(v, str) and "AIza" in v:
                    pytest.fail(f"Raw 'AIza' substring found in byok_keys.{k}: doc id={d.get('_id')}")
