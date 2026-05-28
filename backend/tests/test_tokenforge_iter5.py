"""TokenForge iteration 5 — rate-limit fix verification.

Iter-4 found rate_limit() keyed on request.client.host which behind k8s ingress
rotated across pods. Iter-5 fix: rate_limit() now honors X-Forwarded-For.

These tests inject a UNIQUE X-Forwarded-For per test to ensure each test gets
its own bucket and to avoid cross-test pollution.
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


def _xff(n: int) -> dict:
    # Use TEST-NET-3 (203.0.113.0/24) — reserved for documentation, safe per RFC5737.
    # Append uuid to make it unique even across reruns in the same window.
    suffix = uuid.uuid4().hex[:4]
    return {"X-Forwarded-For": f"203.0.113.{n}.{suffix}".replace(f".{n}.", f".{n & 255}.").replace(f"{suffix}", "") or f"203.0.113.{n & 255}"}


def _xff_clean(n: int) -> dict:
    # simple, unique-ish IP per test
    octet = (n + uuid.uuid4().int) % 250 + 2  # 2..251
    return {"X-Forwarded-For": f"203.0.113.{octet}"}


# ---- rate limit: /optimize  (30/60s) ---------------------------------------
def test_rate_limit_optimize_xff():
    h = _xff_clean(11)
    statuses = []
    retry_after = None
    for i in range(35):
        r = requests.post(f"{API}/optimize", json={"text": "hi"}, headers=h)
        statuses.append(r.status_code)
        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            assert "Rate limit" in r.json().get("detail", "")
            break
    assert 429 in statuses, f"expected 429 from /optimize, got {statuses}"
    # the first 30 must have been 200
    assert statuses[:30].count(200) >= 28, f"first 30 expected mostly 200, got {statuses[:30]}"
    assert retry_after is not None and int(retry_after) >= 0


# ---- rate limit: /auth/register  (8/600s) ----------------------------------
def test_rate_limit_register_xff():
    h = _xff_clean(22)
    statuses = []
    for i in range(10):
        e = f"TEST_iter5_reg_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{API}/auth/register",
                          json={"email": e, "password": "tfqa12345"}, headers=h)
        statuses.append(r.status_code)
        if r.status_code == 429:
            assert "Retry-After" in r.headers
            break
    assert 429 in statuses, f"expected 429 from /auth/register, got {statuses}"
    # at most 8 should be 200
    assert statuses.count(200) <= 8, f"register: more than 8 successes: {statuses}"


# ---- rate limit: /auth/login  (10/300s) -------------------------------------
def test_rate_limit_login_xff():
    h = _xff_clean(33)
    statuses = []
    for i in range(13):
        r = requests.post(f"{API}/auth/login",
                          json={"email": f"nobody{i}@x.io", "password": "x"}, headers=h)
        statuses.append(r.status_code)
        if r.status_code == 429:
            assert "Retry-After" in r.headers
            break
    assert 429 in statuses, f"expected 429 from /auth/login, got {statuses}"


# ---- rate limit: /waitlist  (10/300s) ---------------------------------------
def test_rate_limit_waitlist_xff():
    h = _xff_clean(44)
    statuses = []
    for i in range(13):
        r = requests.post(f"{API}/waitlist",
                          json={"email": f"TEST_iter5_wl_{uuid.uuid4().hex[:6]}@x.io"},
                          headers=h)
        statuses.append(r.status_code)
        if r.status_code == 429:
            assert "Retry-After" in r.headers
            break
    assert 429 in statuses, f"expected 429 from /waitlist, got {statuses}"


# ---- isolation: a second unique XFF gets its OWN bucket ---------------------
def test_rate_limit_buckets_isolated_per_xff():
    """After exhausting one XFF, a DIFFERENT XFF should still be allowed."""
    h1 = _xff_clean(55)
    # exhaust h1
    last = None
    for _ in range(33):
        last = requests.post(f"{API}/optimize", json={"text": "x"}, headers=h1)
        if last.status_code == 429:
            break
    assert last is not None and last.status_code == 429, "did not exhaust first bucket"
    # h2 should still get 200
    h2 = _xff_clean(155)
    r = requests.post(f"{API}/optimize", json={"text": "x"}, headers=h2)
    assert r.status_code == 200, f"second IP bucket polluted: got {r.status_code}, body={r.text[:200]}"


# ---- share 404 endpoint regression (UI displays improved message) ----------
def test_share_unknown_slug_still_404():
    r = requests.get(f"{API}/share/savings/iter5-nope-not-real-zzz")
    assert r.status_code == 404
