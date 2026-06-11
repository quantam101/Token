"""TokenForge backend — FastAPI app.

Modules:
  - Auth (JWT email/password)
  - Optimization engine endpoints
  - LLM proxy (Universal Key: openai/anthropic/gemini)
  - API key management for users
  - Stripe Checkout for paid plans
  - Waitlist capture
  - Dashboard analytics
"""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

import bcrypt
import httpx
import jwt
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, status
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from llm_router import LlmChat, UserMessage
from stripe_service import StripeCheckout, CheckoutSessionRequest
from byok_service import (
    SUPPORTED_PROVIDERS as BYOK_PROVIDERS,
    BYOK_PLANS,
    encrypt as byok_encrypt,
    decrypt as byok_decrypt,
    mask as byok_mask,
    looks_valid as byok_looks_valid,
)

from optimizer import optimize, estimate_tokens, _embed, cosine, to_dict, TIER_MODEL_HINT
from email_service import (
    send_email,
    render_welcome,
    render_quota_alert,
    render_payment_confirmation,
    render_roi_report_email,
    render_milestone_email,
)

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
ACCESS_TTL_MIN = 60 * 24  # 24h
STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@tokenforge.io")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD") or secrets.token_urlsafe(32)
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "https://forge.alreadyherellc.com")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "https://api.alreadyherellc.com/api/auth/google/callback")

MODEL_PRICING_USD_PER_1K = {  # rough public list pricing (input tokens)
    "gpt-5.4": 0.005,
    "gpt-5.4-mini": 0.0015,
    "gpt-4o": 0.005,
    "gpt-4o-mini": 0.00015,
    "claude-sonnet-4-6": 0.003,
    "claude-haiku-4-5-20251001": 0.0008,
    "gemini-3-flash-preview": 0.0003,
    "gemini-3.1-pro-preview": 0.00125,
}

PLAN_PACKAGES = {
    "starter": {"name": "Starter", "amount": 19.00, "annual_amount": 182.40, "currency": "usd", "monthly_quota": 1_000_000},
    "pro": {"name": "Pro", "amount": 99.00, "annual_amount": 950.40, "currency": "usd", "monthly_quota": 10_000_000},
    "enterprise": {"name": "Enterprise", "amount": 499.00, "annual_amount": 4790.40, "currency": "usd", "monthly_quota": 100_000_000},
}
ANNUAL_DISCOUNT_PCT = 20

# Free tier quota — also used as default for new users
FREE_TIER_QUOTA = 50_000

# ------------------------------------------------------------------
# DB
# ------------------------------------------------------------------
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

# ------------------------------------------------------------------
# App
# ------------------------------------------------------------------
app = FastAPI(title="TokenForge API", version="1.0.0")
api = APIRouter(prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("tokenforge")


# ------------------------------------------------------------------
# Lightweight in-memory rate limiter (sliding-window per-IP+path).
# Suitable for the public /optimize endpoint to prevent abuse.
# ------------------------------------------------------------------
_RL_BUCKETS: Dict[str, List[float]] = {}


def rate_limit(request: Request, key_suffix: str, max_calls: int, window_seconds: int) -> None:
    """Raise 429 if caller exceeds max_calls within the rolling window.
    Honors X-Forwarded-For (first hop) for accurate per-client identification
    behind a k8s/CDN/proxy ingress; falls back to request.client.host."""
    import time

    xff = request.headers.get("x-forwarded-for", "") or request.headers.get("x-real-ip", "")
    if xff:
        ip = xff.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "?"
    bucket_key = ip + ":" + key_suffix
    now_ts = time.time()
    bucket = _RL_BUCKETS.setdefault(bucket_key, [])
    cutoff = now_ts - window_seconds
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= max_calls:
        retry_after = int(window_seconds - (now_ts - bucket[0])) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({max_calls} req / {window_seconds}s). Retry in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )
    bucket.append(now_ts)
    # opportunistic cleanup: prevent unbounded dict growth
    if len(_RL_BUCKETS) > 5000:
        # drop empty / fully-expired buckets
        for k in list(_RL_BUCKETS.keys())[:1000]:
            b = _RL_BUCKETS[k]
            while b and b[0] < cutoff:
                b.pop(0)
            if not b:
                _RL_BUCKETS.pop(k, None)


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------
def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or datetime.now(timezone.utc)).isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)
    name: Optional[str] = None
    ref: Optional[str] = None  # referrer's user id


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class WaitlistIn(BaseModel):
    email: EmailStr
    company: Optional[str] = None
    use_case: Optional[str] = None


class OptimizeIn(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)


class ProxyIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=50_000)
    system: Optional[str] = "You are a helpful assistant."
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-6"
    optimize: bool = True


class CreateKeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class CheckoutIn(BaseModel):
    plan_id: str
    origin_url: str
    billing_cycle: str = "monthly"  # "monthly" | "annual"


# ------------------------------------------------------------------
# Auth helpers
# ------------------------------------------------------------------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False
