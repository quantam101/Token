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
import jwt
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
)

from optimizer import optimize, estimate_tokens, _embed, cosine, to_dict, TIER_MODEL_HINT
from email_service import (
    send_email,
    render_welcome,
    render_quota_alert,
    render_payment_confirmation,
    render_roi_report_email,
)

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
ACCESS_TTL_MIN = 60 * 24  # 24h
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@tokenforge.io")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")

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
    allow_origins=["*"],
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
    """Raise 429 if caller exceeds max_calls within the rolling window."""
    import time

    ip = (request.client.host if request.client else "?") + ":" + key_suffix
    now_ts = time.time()
    bucket = _RL_BUCKETS.setdefault(ip, [])
    cutoff = now_ts - window_seconds
    # purge old timestamps cheaply
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


def make_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": _now() + timedelta(minutes=ACCESS_TTL_MIN),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_api_key(request: Request) -> dict:
    """For the LLM proxy endpoint. Accepts header X-TF-Key: tf_xxx"""
    api_key = request.headers.get("X-TF-Key") or request.headers.get("x-tf-key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-TF-Key header")
    record = await db.api_keys.find_one({"key": api_key, "active": True}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=401, detail="Invalid API key")
    user = await db.users.find_one({"id": record["user_id"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="API key owner missing")
    return {"user": user, "key": record}


# ------------------------------------------------------------------
# Quota helpers
# ------------------------------------------------------------------
def _period_start_iso() -> str:
    """ISO string for the first day of the current UTC month at 00:00."""
    now = _now()
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    return start.isoformat()


async def get_user_usage(user_id: str) -> dict:
    """Return current calendar month's billable token usage for the user."""
    since = _period_start_iso()
    pipeline = [
        {"$match": {"user_id": user_id, "created_at": {"$gte": since}}},
        {
            "$group": {
                "_id": None,
                "original": {"$sum": "$original_tokens"},
                "optimized": {"$sum": "$optimized_tokens"},
                "completion": {"$sum": "$completion_tokens"},
                "saved": {"$sum": "$tokens_saved"},
                "requests": {"$sum": 1},
            }
        },
    ]
    rows = await db.proxy_requests.aggregate(pipeline).to_list(1)
    if not rows:
        return {"period_start": since, "tokens_used": 0, "requests": 0, "tokens_saved": 0}
    r = rows[0]
    # Billable usage = optimized (sent to provider) + completion (returned by provider).
    used = int(r.get("optimized", 0)) + int(r.get("completion", 0))
    return {
        "period_start": since,
        "tokens_used": used,
        "requests": int(r.get("requests", 0)),
        "tokens_saved": int(r.get("saved", 0)),
    }


# ------------------------------------------------------------------
# Routes — health + waitlist
# ------------------------------------------------------------------
@api.get("/")
async def root():
    return {"service": "TokenForge", "status": "ok", "version": "1.0.0"}


@api.get("/stats/public")
async def public_stats():
    """Aggregated stats for the landing page (cheap, cached enough)."""
    agg = await db.proxy_requests.aggregate(
        [
            {
                "$group": {
                    "_id": None,
                    "saved": {"$sum": "$tokens_saved"},
                    "total": {"$sum": "$original_tokens"},
                    "n": {"$sum": 1},
                }
            }
        ]
    ).to_list(1)
    waitlist_count = await db.waitlist.count_documents({})
    user_count = await db.users.count_documents({})
    if agg:
        a = agg[0]
        return {
            "tokens_saved": int(a.get("saved", 0)),
            "tokens_processed": int(a.get("total", 0)),
            "requests_optimized": int(a.get("n", 0)),
            "waitlist_count": waitlist_count,
            "user_count": user_count,
        }
    return {
        "tokens_saved": 0,
        "tokens_processed": 0,
        "requests_optimized": 0,
        "waitlist_count": waitlist_count,
        "user_count": user_count,
    }


@api.post("/waitlist")
async def waitlist_signup(body: WaitlistIn, request: Request):
    rate_limit(request, "waitlist", max_calls=10, window_seconds=300)
    email = body.email.lower().strip()
    existing = await db.waitlist.find_one({"email": email})
    if existing:
        return {"status": "already_on_waitlist"}
    doc = {
        "id": str(uuid.uuid4()),
        "email": email,
        "company": body.company,
        "use_case": body.use_case,
        "created_at": _iso(),
    }
    await db.waitlist.insert_one(doc)
    return {"status": "joined", "id": doc["id"]}


# ------------------------------------------------------------------
# Auth routes
# ------------------------------------------------------------------
@api.post("/auth/register")
async def register(body: RegisterIn, request: Request):
    rate_limit(request, "auth_register", max_calls=8, window_seconds=600)
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    uid = str(uuid.uuid4())
    doc = {
        "id": uid,
        "email": email,
        "password_hash": hash_password(body.password),
        "name": body.name or email.split("@")[0],
        "role": "user",
        "plan": "free",
        "monthly_quota": FREE_TIER_QUOTA,
        "created_at": _iso(),
    }
    await db.users.insert_one(doc)
    # auto-issue first API key
    default_key = {
        "id": str(uuid.uuid4()),
        "user_id": uid,
        "name": "Default",
        "key": "tf_live_" + secrets.token_urlsafe(24),
        "active": True,
        "created_at": _iso(),
        "last_used_at": None,
    }
    await db.api_keys.insert_one(default_key)
    token = make_token(uid, email)
    # Fire welcome email (best-effort, non-blocking failure)
    origin = (
        request.headers.get("origin")
        or request.headers.get("referer")
        or "https://tokenforge.io"
    ).rstrip("/")
    try:
        await send_email(
            to=email,
            subject="Welcome to TokenForge — your API key is ready",
            html=render_welcome(doc["name"], default_key["key"], f"{origin}/dashboard"),
        )
    except Exception:
        log.exception("welcome email failed")
    return {
        "token": token,
        "user": {"id": uid, "email": email, "name": doc["name"], "plan": "free", "role": "user"},
    }


@api.post("/auth/login")
async def login(body: LoginIn, request: Request):
    rate_limit(request, "auth_login", max_calls=10, window_seconds=300)
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = make_token(user["id"], user["email"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
            "plan": user.get("plan", "free"),
            "role": user.get("role", "user"),
        },
    }


@api.get("/auth/me")
async def me(user=Depends(current_user)):
    usage = await get_user_usage(user["id"])
    quota = int(user.get("monthly_quota") or FREE_TIER_QUOTA)
    pct = round((usage["tokens_used"] / quota) * 100.0, 2) if quota else 0.0
    return {**user, "usage": {**usage, "monthly_quota": quota, "percent_used": pct}}


# ------------------------------------------------------------------
# API key management
# ------------------------------------------------------------------
@api.get("/keys")
async def list_keys(user=Depends(current_user)):
    keys = await db.api_keys.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    return {"keys": keys}


@api.post("/keys")
async def create_key(body: CreateKeyIn, user=Depends(current_user)):
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "name": body.name,
        "key": "tf_live_" + secrets.token_urlsafe(24),
        "active": True,
        "created_at": _iso(),
        "last_used_at": None,
    }
    await db.api_keys.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}


@api.delete("/keys/{key_id}")
async def revoke_key(key_id: str, user=Depends(current_user)):
    res = await db.api_keys.update_one(
        {"id": key_id, "user_id": user["id"]}, {"$set": {"active": False}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"status": "revoked"}


# ------------------------------------------------------------------
# Optimize (public-demo, no key) — for the playground & landing calc
# ------------------------------------------------------------------
@api.post("/optimize")
async def api_optimize(body: OptimizeIn, request: Request):
    rate_limit(request, "optimize", max_calls=30, window_seconds=60)
    result = optimize(body.text)
    return to_dict(result)


# ------------------------------------------------------------------
# LLM proxy — main product
# ------------------------------------------------------------------
async def _semantic_cache_lookup(user_id: str, prompt: str) -> Optional[dict]:
    """Return a cached response if cosine sim >= 0.98 with a previous prompt."""
    vec = _embed(prompt)
    # Only look at the latest 50 cached entries per user.
    cur = db.semantic_cache.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(50)
    async for entry in cur:
        sim = cosine(vec, entry.get("embedding") or [])
        if sim >= 0.98:
            entry["similarity"] = sim
            return entry
    return None


async def _semantic_cache_store(user_id: str, prompt: str, response: str, model: str) -> None:
    vec = _embed(prompt)
    await db.semantic_cache.insert_one(
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "prompt": prompt[:2000],
            "response": response[:4000],
            "model": model,
            "embedding": vec,
            "created_at": _iso(),
        }
    )


async def _check_quota_alert(user: dict, request: Request) -> None:
    """If user just crossed 80% or 100% of their monthly quota, send an email
    (deduplicated per period)."""
    quota = int(user.get("monthly_quota") or FREE_TIER_QUOTA)
    if quota <= 0:
        return
    usage = await get_user_usage(user["id"])
    pct = (usage["tokens_used"] / quota) * 100.0
    if pct < 80:
        return
    threshold = 100 if pct >= 100 else 80
    period_start = usage["period_start"][:10]  # YYYY-MM-DD of month start
    dedupe_key = f"{user['id']}:{period_start}:{threshold}"
    existing = await db.email_alerts.find_one({"key": dedupe_key})
    if existing:
        return
    await db.email_alerts.insert_one(
        {"key": dedupe_key, "user_id": user["id"], "threshold": threshold, "created_at": _iso()}
    )
    origin = (
        request.headers.get("origin")
        or request.headers.get("referer")
        or "https://tokenforge.io"
    ).rstrip("/")
    await send_email(
        to=user["email"],
        subject=(
            "[TokenForge] Monthly quota exceeded"
            if threshold == 100
            else "[TokenForge] You're at 80% of your monthly quota"
        ),
        html=render_quota_alert(
            user_name=user.get("name") or user["email"].split("@")[0],
            percent=pct,
            used=usage["tokens_used"],
            quota=quota,
            exceeded=(threshold == 100),
            billing_url=f"{origin}/dashboard/billing",
        ),
    )


@api.post("/proxy/chat")
async def proxy_chat(body: ProxyIn, request: Request, auth=Depends(require_api_key)):
    user = auth["user"]
    key = auth["key"]
    original = body.prompt
    original_tokens = estimate_tokens(original)

    # 0. Quota enforcement
    quota = int(user.get("monthly_quota") or FREE_TIER_QUOTA)
    usage = await get_user_usage(user["id"])
    if usage["tokens_used"] >= quota:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Monthly quota exceeded ({usage['tokens_used']}/{quota} tokens). "
                f"Upgrade your plan to continue."
            ),
        )

    # 1. Optimize
    opt = optimize(original) if body.optimize else None
    prompt_to_send = opt.optimized_text if opt else original
    tier = opt.tier if opt else "cognitive"

    # 2. Cache check
    cached = await _semantic_cache_lookup(user["id"], prompt_to_send)
    cache_hit = bool(cached)

    if cache_hit:
        response_text = cached["response"]
        provider = "cache"
        model_used = cached["model"]
    else:
        # 3. If tier is algorithmic, short-circuit with deterministic response
        if tier == "algorithmic":
            response_text = f"[algorithmic-tier] {prompt_to_send.strip()}"
            provider = "algorithmic"
            model_used = "no-model"
        else:
            # 4. Call LLM
            session_id = f"{user['id']}:{uuid.uuid4()}"
            try:
                chat = LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=session_id,
                    system_message=body.system or "You are a helpful assistant.",
                ).with_model(body.provider, body.model)
                msg = UserMessage(text=prompt_to_send)
                response_text = await chat.send_message(msg)
                if not isinstance(response_text, str):
                    response_text = str(response_text)
                provider = body.provider
                model_used = body.model
            except Exception as e:
                log.exception("LLM call failed")
                raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")
            # store cache
            await _semantic_cache_store(user["id"], prompt_to_send, response_text, model_used)

    optimized_tokens = estimate_tokens(prompt_to_send)
    completion_tokens = estimate_tokens(response_text)
    tokens_saved = max(0, original_tokens - optimized_tokens)
    if cache_hit:
        # full prompt+completion saved — count cognitive tokens saved too
        tokens_saved += optimized_tokens + completion_tokens

    # cost calc (based on input pricing)
    price_per_1k = MODEL_PRICING_USD_PER_1K.get(model_used, 0.002)
    cost_saved_usd = round((tokens_saved / 1000.0) * price_per_1k, 6)

    log_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "api_key_id": key["id"],
        "provider": provider,
        "model": model_used,
        "tier": tier,
        "cache_hit": cache_hit,
        "original_tokens": original_tokens,
        "optimized_tokens": optimized_tokens,
        "completion_tokens": completion_tokens,
        "tokens_saved": tokens_saved,
        "cost_saved_usd": cost_saved_usd,
        "created_at": _iso(),
    }
    await db.proxy_requests.insert_one(log_doc)
    await db.api_keys.update_one({"id": key["id"]}, {"$set": {"last_used_at": _iso()}})

    # Quota-crossing email alerts (80% and 100%)
    try:
        await _check_quota_alert(user, request)
    except Exception:
        log.exception("quota alert check failed")

    return {
        "response": response_text,
        "provider": provider,
        "model": model_used,
        "tier": tier,
        "cache_hit": cache_hit,
        "tokens": {
            "original": original_tokens,
            "optimized": optimized_tokens,
            "completion": completion_tokens,
            "saved": tokens_saved,
        },
        "cost_saved_usd": cost_saved_usd,
        "pillars_applied": opt.pillars_applied if opt else [],
    }


# ------------------------------------------------------------------
# Dashboard analytics
# ------------------------------------------------------------------
@api.get("/dashboard/overview")
async def dashboard_overview(user=Depends(current_user)):
    pipeline = [
        {"$match": {"user_id": user["id"]}},
        {
            "$group": {
                "_id": None,
                "total_requests": {"$sum": 1},
                "total_original": {"$sum": "$original_tokens"},
                "total_optimized": {"$sum": "$optimized_tokens"},
                "total_saved": {"$sum": "$tokens_saved"},
                "total_cost_saved": {"$sum": "$cost_saved_usd"},
                "cache_hits": {"$sum": {"$cond": ["$cache_hit", 1, 0]}},
            }
        },
    ]
    res = await db.proxy_requests.aggregate(pipeline).to_list(1)
    if res:
        r = res[0]
        avg_pct = 0.0
        if r["total_original"]:
            avg_pct = round((r["total_saved"] / r["total_original"]) * 100.0, 2)
        return {
            "total_requests": r["total_requests"],
            "total_original_tokens": int(r["total_original"]),
            "total_optimized_tokens": int(r["total_optimized"]),
            "total_tokens_saved": int(r["total_saved"]),
            "total_cost_saved_usd": round(r["total_cost_saved"], 4),
            "cache_hit_rate": round((r["cache_hits"] / r["total_requests"]) * 100.0, 2),
            "avg_percent_saved": avg_pct,
        }
    return {
        "total_requests": 0,
        "total_original_tokens": 0,
        "total_optimized_tokens": 0,
        "total_tokens_saved": 0,
        "total_cost_saved_usd": 0.0,
        "cache_hit_rate": 0.0,
        "avg_percent_saved": 0.0,
    }


@api.get("/dashboard/timeseries")
async def dashboard_timeseries(days: int = 14, user=Depends(current_user)):
    """Return daily totals for the last N days."""
    since = (_now() - timedelta(days=days)).isoformat()
    pipeline = [
        {"$match": {"user_id": user["id"], "created_at": {"$gte": since}}},
        {
            "$group": {
                "_id": {"$substr": ["$created_at", 0, 10]},
                "saved": {"$sum": "$tokens_saved"},
                "original": {"$sum": "$original_tokens"},
                "requests": {"$sum": 1},
                "cost_saved": {"$sum": "$cost_saved_usd"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = await db.proxy_requests.aggregate(pipeline).to_list(100)
    return {
        "series": [
            {
                "date": r["_id"],
                "tokens_saved": int(r["saved"]),
                "tokens_original": int(r["original"]),
                "requests": int(r["requests"]),
                "cost_saved_usd": round(r["cost_saved"], 4),
            }
            for r in rows
        ]
    }


@api.get("/dashboard/logs")
async def dashboard_logs(limit: int = 25, user=Depends(current_user)):
    cur = db.proxy_requests.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(limit)
    return {"logs": await cur.to_list(limit)}


# ------------------------------------------------------------------
# ROI Savings Report (PDF) — shared generator
# ------------------------------------------------------------------
async def _aggregate_savings(user_id: str) -> dict:
    """Return month, lifetime, and per-model aggregates for a user."""
    lifetime_pipe = [
        {"$match": {"user_id": user_id}},
        {
            "$group": {
                "_id": None,
                "requests": {"$sum": 1},
                "saved": {"$sum": "$tokens_saved"},
                "original": {"$sum": "$original_tokens"},
                "cost_saved": {"$sum": "$cost_saved_usd"},
                "cache_hits": {"$sum": {"$cond": ["$cache_hit", 1, 0]}},
            }
        },
    ]
    lt = await db.proxy_requests.aggregate(lifetime_pipe).to_list(1)
    lt = lt[0] if lt else {"requests": 0, "saved": 0, "original": 0, "cost_saved": 0.0, "cache_hits": 0}

    since = _period_start_iso()
    month_pipe = [
        {"$match": {"user_id": user_id, "created_at": {"$gte": since}}},
        {
            "$group": {
                "_id": None,
                "requests": {"$sum": 1},
                "saved": {"$sum": "$tokens_saved"},
                "original": {"$sum": "$original_tokens"},
                "cost_saved": {"$sum": "$cost_saved_usd"},
            }
        },
    ]
    mo = await db.proxy_requests.aggregate(month_pipe).to_list(1)
    mo = mo[0] if mo else {"requests": 0, "saved": 0, "original": 0, "cost_saved": 0.0}

    model_pipe = [
        {"$match": {"user_id": user_id}},
        {
            "$group": {
                "_id": "$model",
                "requests": {"$sum": 1},
                "saved": {"$sum": "$tokens_saved"},
                "cost_saved": {"$sum": "$cost_saved_usd"},
            }
        },
        {"$sort": {"cost_saved": -1}},
    ]
    model_rows = await db.proxy_requests.aggregate(model_pipe).to_list(20)
    return {"month": mo, "lifetime": lt, "models": model_rows, "period_start": since}


def _render_savings_pdf_bytes(user: dict, agg: dict) -> bytes:
    """Render the branded savings PDF and return raw bytes."""
    from io import BytesIO
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas

    mo = agg["month"]
    lt = agg["lifetime"]
    model_rows = agg["models"]
    since = agg["period_start"]

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    W, H = LETTER
    margin = 0.6 * inch

    c.setFillColor(colors.HexColor("#0A0A0A"))
    c.rect(0, H - 1.4 * inch, W, 1.4 * inch, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#FF4500"))
    c.rect(margin, H - 0.85 * inch, 0.34 * inch, 0.34 * inch, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin + 0.07 * inch, H - 0.74 * inch, "TF")
    c.setFont("Helvetica-Bold", 22)
    c.drawString(margin + 0.55 * inch, H - 0.7 * inch, "TokenForge")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#A1A1AA"))
    c.drawString(margin + 0.55 * inch, H - 0.88 * inch, "ROI SAVINGS REPORT")
    c.setFont("Helvetica", 8)
    c.drawRightString(W - margin, H - 0.7 * inch, datetime.now(timezone.utc).strftime("%B %Y"))
    c.drawRightString(W - margin, H - 0.85 * inch, user["email"])

    y = H - 1.9 * inch
    c.setFillColor(colors.HexColor("#0A0A0A"))
    c.setFont("Helvetica-Bold", 26)
    c.drawString(margin, y, "Monthly Savings Summary")
    y -= 0.16 * inch
    c.setFillColor(colors.HexColor("#71717A"))
    c.setFont("Helvetica", 10)
    c.drawString(
        margin,
        y,
        f"Period: {since[:10]} → today  ·  Account: {user.get('name') or user['email']}  ·  Plan: {user.get('plan', 'free')}",
    )

    y -= 0.5 * inch
    box_w = (W - margin * 2 - 0.2 * inch) / 2
    box_h = 1.1 * inch
    kpis = [
        ("TOKENS SAVED (MONTH)", f"{int(mo['saved']):,}", "#00E676"),
        ("$ SAVED (MONTH)", f"${float(mo['cost_saved']):.4f}", "#FF4500"),
        ("TOKENS SAVED (LIFETIME)", f"{int(lt['saved']):,}", "#FAFAFA"),
        ("$ SAVED (LIFETIME)", f"${float(lt['cost_saved']):.4f}", "#FAFAFA"),
    ]
    for i, (label, value, color) in enumerate(kpis):
        col = i % 2
        row = i // 2
        bx = margin + col * (box_w + 0.2 * inch)
        by = y - (row + 1) * box_h - row * 0.15 * inch
        c.setStrokeColor(colors.HexColor("#27272A"))
        c.setLineWidth(0.6)
        c.rect(bx, by, box_w, box_h, fill=0, stroke=1)
        c.setFillColor(colors.HexColor("#71717A"))
        c.setFont("Helvetica", 8)
        c.drawString(bx + 0.18 * inch, by + box_h - 0.28 * inch, label)
        c.setFillColor(colors.HexColor(color))
        c.setFont("Helvetica-Bold", 24)
        c.drawString(bx + 0.18 * inch, by + 0.28 * inch, value)

    y -= box_h * 2 + 0.55 * inch
    avg_pct = round((lt["saved"] / lt["original"]) * 100.0, 2) if lt["original"] else 0
    cache_pct = round((lt["cache_hits"] / lt["requests"]) * 100.0, 2) if lt["requests"] else 0
    c.setFillColor(colors.HexColor("#0A0A0A"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, "Efficiency")
    y -= 0.25 * inch
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#27272A"))
    c.drawString(
        margin,
        y,
        f"Average compression:  {avg_pct}%   ·   Semantic cache hit rate:  {cache_pct}%   ·   Total requests:  {int(lt['requests']):,}",
    )

    y -= 0.4 * inch
    c.setFillColor(colors.HexColor("#0A0A0A"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, "Savings by Model (Lifetime)")
    y -= 0.25 * inch
    c.setStrokeColor(colors.HexColor("#27272A"))
    c.line(margin, y + 0.05 * inch, W - margin, y + 0.05 * inch)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#71717A"))
    c.drawString(margin, y - 0.18 * inch, "MODEL")
    c.drawString(margin + 3.0 * inch, y - 0.18 * inch, "REQUESTS")
    c.drawString(margin + 4.3 * inch, y - 0.18 * inch, "TOKENS SAVED")
    c.drawRightString(W - margin, y - 0.18 * inch, "$ SAVED")
    y -= 0.42 * inch
    if not model_rows:
        c.setFont("Helvetica-Oblique", 10)
        c.setFillColor(colors.HexColor("#71717A"))
        c.drawString(margin, y, "No proxy calls recorded yet.")
    else:
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.HexColor("#0A0A0A"))
        for r in model_rows[:8]:
            c.drawString(margin, y, str(r.get("_id") or "—")[:48])
            c.drawString(margin + 3.0 * inch, y, f"{int(r.get('requests', 0)):,}")
            c.drawString(margin + 4.3 * inch, y, f"{int(r.get('saved', 0)):,}")
            c.drawRightString(W - margin, y, f"${float(r.get('cost_saved', 0.0)):.4f}")
            y -= 0.22 * inch
            c.setStrokeColor(colors.HexColor("#F0F0F0"))
            c.line(margin, y + 0.08 * inch, W - margin, y + 0.08 * inch)

    c.setFillColor(colors.HexColor("#A1A1AA"))
    c.setFont("Helvetica", 8)
    c.drawString(margin, 0.5 * inch, "Generated by TokenForge — distill or perish.  ·  tokenforge.io")
    c.drawRightString(W - margin, 0.5 * inch, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


@api.get("/reports/savings.pdf")
async def savings_report_pdf(user=Depends(current_user)):
    """Generates a branded ROI Savings Report PDF for the current calendar month."""
    agg = await _aggregate_savings(user["id"])
    pdf_bytes = _render_savings_pdf_bytes(user, agg)
    fname = f"tokenforge-savings-{datetime.now(timezone.utc).strftime('%Y%m')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@api.post("/reports/savings/email")
async def email_savings_report(request: Request, user=Depends(current_user)):
    """Email the ROI Savings Report PDF to the current user (and BCC operator)."""
    agg = await _aggregate_savings(user["id"])
    pdf_bytes = _render_savings_pdf_bytes(user, agg)
    origin = (
        request.headers.get("origin")
        or request.headers.get("referer")
        or "https://tokenforge.io"
    ).rstrip("/")
    email_id = await send_email(
        to=user["email"],
        subject=f"[TokenForge] Your ROI Savings Report — {datetime.now(timezone.utc).strftime('%B %Y')}",
        html=render_roi_report_email(
            user.get("name") or user["email"].split("@")[0],
            int(agg["month"]["saved"]),
            float(agg["month"]["cost_saved"]),
            f"{origin}/dashboard",
        ),
        attachment={
            "filename": f"tokenforge-savings-{datetime.now(timezone.utc).strftime('%Y%m')}.pdf",
            "content_bytes": pdf_bytes,
        },
    )
    return {"sent": bool(email_id), "email_id": email_id}


# ------------------------------------------------------------------
# Shareable savings receipt — public read-only page data
# ------------------------------------------------------------------
@api.post("/share/savings")
async def create_share_link(user=Depends(current_user)):
    """Create (or rotate) a public, anonymized shareable link for this user's lifetime savings."""
    existing = await db.share_links.find_one({"user_id": user["id"]}, {"_id": 0})
    if existing:
        return {"slug": existing["slug"]}
    slug = secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:12]
    await db.share_links.insert_one(
        {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "slug": slug,
            "display_name": user.get("name") or "A TokenForge customer",
            "created_at": _iso(),
        }
    )
    return {"slug": slug}


@api.get("/share/savings/{slug}")
async def get_share_data(slug: str):
    rec = await db.share_links.find_one({"slug": slug}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Share link not found")
    agg = await _aggregate_savings(rec["user_id"])
    return {
        "display_name": rec.get("display_name"),
        "created_at": rec.get("created_at"),
        "tokens_saved": int(agg["lifetime"].get("saved", 0)),
        "cost_saved_usd": round(float(agg["lifetime"].get("cost_saved", 0.0)), 4),
        "requests": int(agg["lifetime"].get("requests", 0)),
        "avg_compression_pct": (
            round((agg["lifetime"]["saved"] / agg["lifetime"]["original"]) * 100.0, 2)
            if agg["lifetime"].get("original")
            else 0
        ),
    }


# ------------------------------------------------------------------
# Billing (Stripe Checkout)
# ------------------------------------------------------------------
@api.get("/billing/plans")
async def list_plans():
    plans = []
    # Always expose free tier for FE (no Stripe).
    plans.append({
        "id": "free",
        "name": "Free",
        "amount": 0.0,
        "annual_amount": 0.0,
        "monthly_quota": FREE_TIER_QUOTA,
    })
    for pid, p in PLAN_PACKAGES.items():
        plans.append({
            "id": pid,
            "name": p["name"],
            "amount": p["amount"],
            "annual_amount": p["annual_amount"],
            "monthly_quota": p["monthly_quota"],
        })
    return {"plans": plans, "annual_discount_pct": ANNUAL_DISCOUNT_PCT}


@api.post("/billing/checkout")
async def create_checkout(body: CheckoutIn, request: Request, user=Depends(current_user)):
    plan = PLAN_PACKAGES.get(body.plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")
    cycle = body.billing_cycle if body.billing_cycle in ("monthly", "annual") else "monthly"
    amount = float(plan["annual_amount"] if cycle == "annual" else plan["amount"])
    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/pricing"
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    req = CheckoutSessionRequest(
        amount=amount,
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user["id"],
            "user_email": user["email"],
            "plan_id": body.plan_id,
            "billing_cycle": cycle,
            "source": "tokenforge_dashboard",
        },
    )
    session = await stripe_checkout.create_checkout_session(req)
    await db.payment_transactions.insert_one(
        {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "user_email": user["email"],
            "session_id": session.session_id,
            "plan_id": body.plan_id,
            "billing_cycle": cycle,
            "amount": amount,
            "currency": "usd",
            "payment_status": "pending",
            "status": "open",
            "metadata": {"plan_id": body.plan_id, "billing_cycle": cycle},
            "created_at": _iso(),
        }
    )
    return {"url": session.url, "session_id": session.session_id, "amount": amount, "billing_cycle": cycle}


@api.get("/billing/status/{session_id}")
async def checkout_status(session_id: str, request: Request, user=Depends(current_user)):
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    status_resp = await stripe_checkout.get_checkout_status(session_id)
    tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    # update only once
    if status_resp.payment_status == "paid" and tx.get("payment_status") != "paid":
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "paid", "status": status_resp.status}},
        )
        plan_id = tx.get("plan_id", "starter")
        new_quota = PLAN_PACKAGES.get(plan_id, {}).get("monthly_quota", FREE_TIER_QUOTA)
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"plan": plan_id, "monthly_quota": new_quota}},
        )
        # Payment confirmation email (best-effort)
        try:
            plan_meta = PLAN_PACKAGES.get(plan_id, {})
            origin = (
                request.headers.get("origin")
                or request.headers.get("referer")
                or "https://tokenforge.io"
            ).rstrip("/")
            await send_email(
                to=user["email"],
                subject=f"[TokenForge] Payment received — {plan_meta.get('name', plan_id)} plan active",
                html=render_payment_confirmation(
                    user.get("name") or user["email"].split("@")[0],
                    plan_meta.get("name", plan_id),
                    float(tx.get("amount") or plan_meta.get("amount", 0)),
                    tx.get("billing_cycle", "monthly"),
                    f"{origin}/dashboard",
                ),
            )
        except Exception:
            log.exception("payment confirmation email failed")
    elif status_resp.status == "expired" and tx.get("status") != "expired":
        await db.payment_transactions.update_one(
            {"session_id": session_id}, {"$set": {"status": "expired"}}
        )
    return {
        "status": status_resp.status,
        "payment_status": status_resp.payment_status,
        "amount_total": status_resp.amount_total,
        "currency": status_resp.currency,
        "metadata": status_resp.metadata,
    }


@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    try:
        ev = await stripe_checkout.handle_webhook(body, sig)
    except Exception as e:
        log.warning(f"webhook parse failed: {e}")
        return {"received": False}
    if ev.payment_status == "paid" and ev.session_id:
        tx = await db.payment_transactions.find_one({"session_id": ev.session_id})
        if tx and tx.get("payment_status") != "paid":
            await db.payment_transactions.update_one(
                {"session_id": ev.session_id},
                {"$set": {"payment_status": "paid", "status": "complete"}},
            )
            plan_id = (ev.metadata or {}).get("plan_id", "starter")
            user_id = (ev.metadata or {}).get("user_id")
            if user_id:
                new_quota = PLAN_PACKAGES.get(plan_id, {}).get("monthly_quota", FREE_TIER_QUOTA)
                await db.users.update_one(
                    {"id": user_id},
                    {"$set": {"plan": plan_id, "monthly_quota": new_quota}},
                )
                # Send confirmation email
                try:
                    u = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
                    if u:
                        plan_meta = PLAN_PACKAGES.get(plan_id, {})
                        await send_email(
                            to=u["email"],
                            subject=f"[TokenForge] Payment received — {plan_meta.get('name', plan_id)} plan active",
                            html=render_payment_confirmation(
                                u.get("name") or u["email"].split("@")[0],
                                plan_meta.get("name", plan_id),
                                float(tx.get("amount") or plan_meta.get("amount", 0)),
                                (ev.metadata or {}).get("billing_cycle", "monthly"),
                                "https://tokenforge.io/dashboard",
                            ),
                        )
                except Exception:
                    log.exception("webhook payment confirmation email failed")
    return {"received": True}


# ------------------------------------------------------------------
# Admin
# ------------------------------------------------------------------
async def require_admin(user=Depends(current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


@api.get("/admin/overview")
async def admin_overview(user=Depends(require_admin)):
    users = await db.users.count_documents({})
    waitlist = await db.waitlist.count_documents({})
    requests = await db.proxy_requests.count_documents({})
    paid_tx = await db.payment_transactions.count_documents({"payment_status": "paid"})
    revenue_pipeline = [
        {"$match": {"payment_status": "paid"}},
        {"$group": {"_id": None, "rev": {"$sum": "$amount"}}},
    ]
    rev = await db.payment_transactions.aggregate(revenue_pipeline).to_list(1)
    revenue = round(rev[0]["rev"], 2) if rev else 0.0
    saved_pipeline = [
        {"$group": {"_id": None, "saved": {"$sum": "$tokens_saved"}}},
    ]
    sv = await db.proxy_requests.aggregate(saved_pipeline).to_list(1)
    tokens_saved = int(sv[0]["saved"]) if sv else 0
    waitlist_list = await db.waitlist.find({}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return {
        "users": users,
        "waitlist": waitlist,
        "requests": requests,
        "paid_transactions": paid_tx,
        "revenue_usd": revenue,
        "total_tokens_saved": tokens_saved,
        "recent_waitlist": waitlist_list,
    }


# ------------------------------------------------------------------
# Startup
# ------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    # Indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.api_keys.create_index("key", unique=True)
    await db.api_keys.create_index("user_id")
    await db.proxy_requests.create_index("user_id")
    await db.proxy_requests.create_index("created_at")
    await db.waitlist.create_index("email", unique=True)
    await db.semantic_cache.create_index([("user_id", 1), ("created_at", -1)])
    await db.payment_transactions.create_index("session_id", unique=True)
    await db.share_links.create_index("slug", unique=True)
    await db.share_links.create_index("user_id")
    await db.email_alerts.create_index("key", unique=True)
    # Seed admin
    existing = await db.users.find_one({"email": ADMIN_EMAIL.lower()})
    if not existing:
        uid = str(uuid.uuid4())
        await db.users.insert_one(
            {
                "id": uid,
                "email": ADMIN_EMAIL.lower(),
                "password_hash": hash_password(ADMIN_PASSWORD),
                "name": "TokenForge Admin",
                "role": "admin",
                "plan": "enterprise",
                "monthly_quota": 100_000_000,
                "created_at": _iso(),
            }
        )
        await db.api_keys.insert_one(
            {
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "name": "Admin Default",
                "key": "tf_live_" + secrets.token_urlsafe(24),
                "active": True,
                "created_at": _iso(),
                "last_used_at": None,
            }
        )
        log.info("Seeded admin user")
    else:
        if not verify_password(ADMIN_PASSWORD, existing["password_hash"]):
            await db.users.update_one(
                {"email": ADMIN_EMAIL.lower()},
                {"$set": {"password_hash": hash_password(ADMIN_PASSWORD)}},
            )


@app.on_event("shutdown")
async def shutdown():
    client.close()


app.include_router(api)
