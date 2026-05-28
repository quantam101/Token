"""Iter-13: email-delivery verification with domain-verified Resend.

Goals:
- Register a NEW user with a recipient on the verified domain
  (alreadyherellc.com) and confirm Resend log shows `resend.send ok` for the
  welcome email (NOT sandbox-rejected).
- Force the $1 milestone via seeded cost and call /api/proxy/chat, then
  confirm milestone email logs `resend.send ok` AND that an auto-share-link +
  milestone_alerts row are created. Verify idempotency on re-fire.
- Sanity-check PDF report endpoint, OG image, widget.js.
- Regression: login/me/keys/logs/dashboard still 200.

Note: Resend is in "verified domain" mode. Sends to recipients on the verified
domain `alreadyherellc.com` (e.g., `qa+<rand>@alreadyherellc.com`) are
guaranteed deliverable. Sends to OTHER arbitrary recipients may still be
sandbox-rejected until the API key is taken out of test mode at the Resend
account level — that is a Resend-account state, NOT a TokenForge code bug.
"""
import os
import time
import uuid
import re
import requests
import pytest
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "tokenforge")
BACKEND_ERR_LOG = "/var/log/supervisor/backend.err.log"
BACKEND_OUT_LOG = "/var/log/supervisor/backend.out.log"

mongo = MongoClient(MONGO_URL)
db = mongo[DB_NAME]


def _iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _grep_logs(pattern: str, since_ts: float) -> list[str]:
    """Return matching lines added to backend logs since `since_ts` epoch."""
    hits: list[str] = []
    for log_path in (BACKEND_ERR_LOG, BACKEND_OUT_LOG):
        if not os.path.exists(log_path):
            continue
        try:
            mtime = os.path.getmtime(log_path)
            if mtime < since_ts - 5:
                continue
            with open(log_path, "r", errors="ignore") as fh:
                for line in fh.readlines()[-3000:]:
                    if re.search(pattern, line):
                        hits.append(line.rstrip())
        except Exception:
            continue
    return hits


# Use the verified domain so Resend will actually deliver and log `resend.send ok`.
def _deliverable_email(prefix: str) -> str:
    return f"qa+{prefix}_{uuid.uuid4().hex[:10]}@alreadyherellc.com"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@tokenforge.io", "password": "ForgeAdmin!2026"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _register(prefix: str):
    email = _deliverable_email(prefix)
    t0 = time.time()
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "QAPass!2026", "name": f"QA {prefix}"},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    user_id = data["user"]["id"]
    token = data["token"]
    kr = requests.get(
        f"{BASE_URL}/api/keys",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert kr.status_code == 200, kr.text
    api_key = kr.json()["keys"][0]["key"]
    db.users.update_one(
        {"id": user_id},
        {"$set": {"monthly_quota": 10_000_000_000}},
    )
    return {
        "user_id": user_id,
        "email": email,
        "token": token,
        "api_key": api_key,
        "t0": t0,
    }


def _seed_cost(user_id: str, cost: float):
    db.proxy_requests.insert_one(
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "api_key_id": "test_iter13",
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "tier": "algorithmic",
            "cache_hit": True,
            "original_tokens": int(cost * 1000),
            "optimized_tokens": 1,
            "completion_tokens": 1,
            "tokens_saved": int(cost * 1000),
            "cost_saved_usd": float(cost),
            "created_at": _iso(),
        }
    )


def _call_proxy(api_key: str, prompt: str = "What is 2+2?"):
    return requests.post(
        f"{BASE_URL}/api/proxy/chat",
        headers={"X-TF-Key": api_key, "Content-Type": "application/json"},
        json={"prompt": prompt, "optimize": True},
        timeout=60,
    )


# ----------------------------------------------------------------------
# Welcome email
# ----------------------------------------------------------------------
class TestWelcomeEmailVerifiedDomain:
    def test_register_to_verified_domain_logs_resend_send_ok(self):
        u = _register("welcome")
        # Email send is best-effort, fire-and-forget — give it a few seconds.
        time.sleep(4.0)
        # Look specifically for the welcome subject in the resend.send ok line
        ok_hits = _grep_logs(
            r"resend\.send ok .*to=" + re.escape(u["email"]),
            u["t0"],
        )
        reject_hits = _grep_logs(
            r"resend\.send rejected.*to=" + re.escape(u["email"]),
            u["t0"],
        )
        assert ok_hits, (
            f"Expected `resend.send ok` for {u['email']} but found none. "
            f"Reject lines: {reject_hits}"
        )
        # Confirm it's the welcome email subject
        assert any("Welcome to TokenForge" in h for h in ok_hits), ok_hits


# ----------------------------------------------------------------------
# Milestone celebration flow
# ----------------------------------------------------------------------
class TestMilestoneFlowEmailDeliverable:
    def test_one_dollar_milestone_fires_and_emails(self):
        u = _register("milestone")
        # Seed >$1 savings then fire the proxy call
        _seed_cost(u["user_id"], 1.50)
        # Reset t0 to capture milestone email only
        t_ms = time.time()
        r = _call_proxy(u["api_key"])
        assert r.status_code == 200, r.text
        body = r.json()
        # Iter-12 response shape: keys include cost_saved_usd, tokens_saved, cache_hit
        assert "cost_saved_usd" in body, body
        time.sleep(4.0)

        # (a) milestone_alerts row
        alerts = list(db.milestone_alerts.find({"user_id": u["user_id"]}))
        assert len(alerts) == 1, f"Expected 1 alert, got {alerts}"
        assert alerts[0]["key"] == f"{u['user_id']}:milestone:1"
        assert float(alerts[0]["threshold_usd"]) == 1.0

        # (b) auto-share link
        shares = list(db.share_links.find({"user_id": u["user_id"]}))
        assert len(shares) == 1 and shares[0].get("auto_created") is True

        # (c) resend.send ok for the milestone email
        ok_hits = _grep_logs(
            r"resend\.send ok .*to=" + re.escape(u["email"]),
            t_ms,
        )
        assert ok_hits, f"No resend.send ok line for milestone email to {u['email']}"
        assert any(
            "saved $1" in h or "milestone" in h.lower() or "share your receipt" in h
            for h in ok_hits
        ), ok_hits

    def test_milestone_idempotent_on_repeat_proxy_call(self):
        u = _register("idempot")
        _seed_cost(u["user_id"], 1.50)
        r1 = _call_proxy(u["api_key"])
        assert r1.status_code == 200
        time.sleep(2.0)
        alerts1 = list(db.milestone_alerts.find({"user_id": u["user_id"]}))
        assert len(alerts1) == 1

        # Second call must NOT create a duplicate alert
        r2 = _call_proxy(u["api_key"])
        assert r2.status_code == 200
        time.sleep(2.0)
        alerts2 = list(db.milestone_alerts.find({"user_id": u["user_id"]}))
        assert len(alerts2) == 1, f"Duplicate alerts: {alerts2}"


# ----------------------------------------------------------------------
# PDF / OG / widget
# ----------------------------------------------------------------------
class TestStaticEndpoints:
    def test_savings_pdf_returns_pdf(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/reports/savings.pdf",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]
        ctype = r.headers.get("content-type", "")
        assert "application/pdf" in ctype.lower(), ctype
        # Validate PDF magic bytes
        assert r.content[:4] == b"%PDF", r.content[:32]

    def test_og_image_endpoint_returns_png(self):
        # Use a guaranteed-existing slug if any; otherwise placeholder PNG is
        # still 200 PNG per iter-11 design.
        # Try admin's slug if available
        # Real endpoint is /api/share/savings/{slug}/og.png; unknown slug → placeholder 200 PNG (by design)
        r = requests.get(
            f"{BASE_URL}/api/share/savings/market-launch-43/og.png",
            timeout=15,
        )
        assert r.status_code == 200, r.text[:300]
        assert "image/png" in r.headers.get("content-type", "").lower()
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n", r.content[:16]

    def test_widget_js_returns_javascript(self):
        r = requests.get(f"{BASE_URL}/api/widget.js", timeout=10)
        assert r.status_code == 200, r.text[:300]
        ctype = r.headers.get("content-type", "").lower()
        assert "javascript" in ctype, ctype
        assert b"TokenForge" in r.content or b"tokenforge" in r.content.lower()


# ----------------------------------------------------------------------
# Regression spine
# ----------------------------------------------------------------------
class TestRegressionCore:
    def test_login_admin(self):
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@tokenforge.io", "password": "ForgeAdmin!2026"},
            timeout=15,
        )
        assert r.status_code == 200
        assert "token" in r.json()

    def test_auth_me(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["email"] == "admin@tokenforge.io"

    def test_keys_list(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/keys",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10,
        )
        assert r.status_code == 200
        assert "keys" in r.json()

    def test_logs(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/dashboard/logs",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10,
        )
        assert r.status_code == 200

    def test_dashboard(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/dashboard/overview",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10,
        )
        assert r.status_code == 200
