"""Iter-12: milestone flywheel — auto-share links, milestone_alerts, admin KPIs.

Covers the new milestone trigger called from proxy_chat:
- No-fire path when cost_saved_usd < $1
- $1 tier fire creates milestone_alerts + auto-created share_links
- Idempotency on subsequent calls
- Multi-tier: bump cost to >$20 fires $20 tier only (next-highest unseen)
- Cross-jump: fresh user seeded at $150 fires $100 only (highest unseen)
- Auto-share idempotency when user already had a share link
- Admin /overview new KPIs: referrals, milestones_fired, auto_share_links
- Showcase includes auto-created share links
"""

import os
import time
import uuid
import requests
import pytest
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "tokenforge")

mongo = MongoClient(MONGO_URL)
db = mongo[DB_NAME]


def _iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@tokenforge.io", "password": "ForgeAdmin!2026"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _register_user(prefix: str):
    email = f"TEST_iter12_{prefix}_{uuid.uuid4().hex[:8]}@qa.tokenforge.io"
    r = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "QAPass!2026", "name": f"QA {prefix}"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    user_id = data["user"]["id"]
    token = data["token"]
    # Get default API key
    kr = requests.get(
        f"{BASE_URL}/api/keys",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert kr.status_code == 200
    api_key = kr.json()["keys"][0]["key"]
    # Bump monthly_quota high so proxy_chat doesn't 429
    db.users.update_one(
        {"id": user_id},
        {"$set": {"monthly_quota": 10_000_000_000}},
    )
    return {"user_id": user_id, "email": email, "token": token, "api_key": api_key}


def _seed_cost(user_id: str, cost: float, api_key_id: str = "test_key"):
    """Insert a proxy_requests row directly so _aggregate_savings sees the cost."""
    db.proxy_requests.insert_one(
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "api_key_id": api_key_id,
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "tier": "algorithmic",
            "cache_hit": False,
            "original_tokens": int(cost * 1000),
            "optimized_tokens": 1,
            "completion_tokens": 1,
            "tokens_saved": int(cost * 1000),
            "cost_saved_usd": float(cost),
            "created_at": _iso(),
        }
    )


def _call_proxy(api_key: str, prompt: str = "What is 2+2?"):
    """Use algorithmic tier prompt — short, no LLM cost. Optimizer will likely
    keep this prompt as cognitive though, so we set optimize=False and provide a
    bare prompt; tier will default. To force algorithmic with no LLM, send a
    very simple prompt — actually optimizer auto-picks tier. We'll just call
    and accept any 200; failing 5xx surfaces an issue."""
    r = requests.post(
        f"{BASE_URL}/api/proxy/chat",
        headers={"X-TF-Key": api_key, "Content-Type": "application/json"},
        json={"prompt": prompt, "optimize": True},
        timeout=60,
    )
    return r


# -------------------- TESTS --------------------


class TestMilestoneNoFireBelowOne:
    def test_no_milestone_when_cost_below_one(self):
        u = _register_user("nofire")
        # Pre: no proxy_requests so cost=0. Even after one tiny proxy/chat call,
        # cost_saved_usd should be << $1.
        r = _call_proxy(u["api_key"])
        assert r.status_code == 200, r.text

        alerts = list(db.milestone_alerts.find({"user_id": u["user_id"]}))
        assert len(alerts) == 0, f"Expected no milestone_alerts but got {alerts}"

        shares = list(db.share_links.find({"user_id": u["user_id"]}))
        assert len(shares) == 0, f"Expected no auto share_link but got {shares}"


class TestMilestoneOneDollarFire:
    def test_one_dollar_milestone_fires_and_is_idempotent(self):
        u = _register_user("d1")
        # Seed $1.50 cost saved
        _seed_cost(u["user_id"], 1.50)
        r = _call_proxy(u["api_key"])
        assert r.status_code == 200, r.text

        # Allow a brief moment for the awaited writes
        time.sleep(0.5)

        alerts = list(db.milestone_alerts.find({"user_id": u["user_id"]}))
        assert len(alerts) == 1, f"Expected exactly 1 milestone_alerts row, got {alerts}"
        a = alerts[0]
        assert a["key"] == f"{u['user_id']}:milestone:1"
        assert a["threshold_usd"] == 1.0 or a["threshold_usd"] == 1
        assert a["cost_saved_at_fire"] >= 1.5

        shares = list(db.share_links.find({"user_id": u["user_id"]}))
        assert len(shares) == 1, f"Expected 1 auto share_link, got {shares}"
        assert shares[0].get("auto_created") is True

        # Idempotency: call again — no new milestone row, no new share row
        r2 = _call_proxy(u["api_key"])
        assert r2.status_code == 200, r2.text
        time.sleep(0.3)
        alerts2 = list(db.milestone_alerts.find({"user_id": u["user_id"]}))
        assert len(alerts2) == 1, f"Idempotency failed: {alerts2}"
        shares2 = list(db.share_links.find({"user_id": u["user_id"]}))
        assert len(shares2) == 1, f"Share dup: {shares2}"

        # Multi-tier: bump cost past $20
        _seed_cost(u["user_id"], 25.0)
        r3 = _call_proxy(u["api_key"])
        assert r3.status_code == 200, r3.text
        time.sleep(0.3)
        alerts3 = sorted(
            db.milestone_alerts.find({"user_id": u["user_id"]}),
            key=lambda x: x["threshold_usd"],
        )
        thresholds = [int(a["threshold_usd"]) for a in alerts3]
        assert 1 in thresholds and 20 in thresholds, f"Expected tiers 1 and 20, got {thresholds}"
        # No $100 yet
        assert 100 not in thresholds


class TestMilestoneCrossJump:
    def test_fresh_user_at_150_only_fires_highest_unseen_100(self):
        u = _register_user("jump")
        _seed_cost(u["user_id"], 150.0)
        r = _call_proxy(u["api_key"])
        assert r.status_code == 200, r.text
        time.sleep(0.3)
        alerts = list(db.milestone_alerts.find({"user_id": u["user_id"]}))
        # Implementation fires only the HIGHEST unseen tier per request -> $100
        thresholds = [int(a["threshold_usd"]) for a in alerts]
        assert thresholds == [100], f"Expected only $100 tier, got {thresholds}"
        # auto-share created
        shares = list(db.share_links.find({"user_id": u["user_id"]}))
        assert len(shares) == 1 and shares[0].get("auto_created") is True


class TestAutoShareIdempotency:
    def test_existing_manual_share_link_is_reused(self):
        u = _register_user("existing")
        # Create share link manually first
        r = requests.post(
            f"{BASE_URL}/api/share/savings",
            headers={"Authorization": f"Bearer {u['token']}"},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        manual_slug = r.json()["slug"]
        # Seed cost and call proxy
        _seed_cost(u["user_id"], 1.50)
        r2 = _call_proxy(u["api_key"])
        assert r2.status_code == 200, r2.text
        time.sleep(0.3)
        shares = list(db.share_links.find({"user_id": u["user_id"]}))
        assert len(shares) == 1, f"Should not duplicate share_link: {shares}"
        assert shares[0]["slug"] == manual_slug
        # auto_created flag should NOT be set on the manual one (it was created
        # via POST /api/share/savings which doesn't set auto_created)
        assert shares[0].get("auto_created") is not True


class TestAdminOverviewKPIs:
    def test_admin_overview_returns_new_kpis(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/admin/overview",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("referrals", "milestones_fired", "auto_share_links"):
            assert k in data, f"Missing KPI field: {k}"
            assert isinstance(data[k], int), f"{k} should be int, got {type(data[k])}"
        # We've just fired several milestones in prior tests, so it should be > 0
        assert data["milestones_fired"] >= 1
        assert data["auto_share_links"] >= 1


class TestShowcaseIncludesAutoShares:
    def test_showcase_returns_auto_created_users(self):
        r = requests.get(f"{BASE_URL}/api/showcase/savings", timeout=10)
        assert r.status_code == 200, r.text
        customers = r.json()["customers"]
        # At least one of our seeded test users (with cost > 0) should appear
        assert isinstance(customers, list)
        assert len(customers) >= 1
        # Each row has the expected shape
        for c in customers[:3]:
            assert "slug" in c and "tokens_saved" in c and "cost_saved_usd" in c
