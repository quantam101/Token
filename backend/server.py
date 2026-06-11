"""TokenForge backend.

A compact FastAPI service for public health checks, prompt optimization, waitlist capture,
plan metadata, and guarded billing handoff. It is designed to run safely even when paid
provider integrations are not configured.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

APP_ENV = os.getenv("APP_ENV") or os.getenv("ENV") or "development"
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "https://forge.alreadyherellc.com")
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", FRONTEND_ORIGIN).split(",") if origin.strip()]
if APP_ENV == "production" and (not CORS_ORIGINS or "*" in CORS_ORIGINS):
    raise RuntimeError("Production CORS_ORIGINS must be explicit.")

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "tokenforge")
client = AsyncIOMotorClient(MONGO_URL) if MONGO_URL else None
db = client[DB_NAME] if client is not None else None

app = FastAPI(title="TokenForge API", version="1.0.2")
api = APIRouter(prefix="/api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

memory_waitlist: List[Dict[str, Any]] = []
memory_usage: List[Dict[str, Any]] = []

PLANS = {
    "free": {"name": "Free", "amount": 0, "currency": "usd", "monthlyQuota": 50_000},
    "starter": {"name": "Starter", "amount": 19, "currency": "usd", "monthlyQuota": 1_000_000},
    "pro": {"name": "Pro", "amount": 99, "currency": "usd", "monthlyQuota": 10_000_000},
    "enterprise": {"name": "Enterprise", "amount": 499, "currency": "usd", "monthlyQuota": 100_000_000},
}


class WaitlistIn(BaseModel):
    email: EmailStr
    company: Optional[str] = Field(default=None, max_length=160)
    use_case: Optional[str] = Field(default=None, max_length=1000)


class OptimizeIn(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)
    goal: Optional[str] = Field(default=None, max_length=500)


class CheckoutIn(BaseModel):
    plan_id: str = Field(min_length=1, max_length=40)
    origin_url: str = Field(min_length=1, max_length=500)
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|annual)$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) * 1.35))


def optimize_prompt(text: str, goal: Optional[str] = None) -> Dict[str, Any]:
    lines = [line.strip() for line in text.replace("\r", "").split("\n")]
    cleaned = "\n".join(line for line in lines if line)
    instruction = goal.strip() if goal else "Return a concise, correct, actionable answer."
    optimized = f"Goal: {instruction}\n\nPrompt:\n{cleaned}"
    original_tokens = estimate_tokens(text)
    optimized_tokens = estimate_tokens(optimized)
    savings = 0 if original_tokens == 0 else round(max(0, original_tokens - optimized_tokens) / original_tokens * 100, 2)
    return {
        "optimized": optimized,
        "originalTokens": original_tokens,
        "optimizedTokens": optimized_tokens,
        "estimatedSavingsPercent": savings,
        "hash": hashlib.sha256(optimized.encode("utf-8")).hexdigest(),
    }


@api.get("/health")
async def health() -> Dict[str, Any]:
    database = "disabled"
    if db is not None:
        try:
            await db.command("ping")
            database = "connected"
        except Exception:
            database = "degraded"
    return {
        "ok": database != "degraded",
        "service": "tokenforge-api",
        "status": "ready" if database != "degraded" else "degraded",
        "environment": APP_ENV,
        "database": database,
        "timestamp": now_iso(),
    }


@api.get("/plans")
async def plans() -> Dict[str, Any]:
    return {"ok": True, "plans": PLANS}


@api.post("/waitlist")
async def waitlist(payload: WaitlistIn) -> Dict[str, Any]:
    item = payload.model_dump()
    item["email"] = item["email"].lower().strip()
    item["createdAt"] = now_iso()
    if db is not None:
        await db.waitlist.update_one({"email": item["email"]}, {"$set": item}, upsert=True)
    else:
        memory_waitlist.append(item)
    return {"ok": True, "entry": item}


@api.post("/optimize")
async def optimize_route(payload: OptimizeIn) -> Dict[str, Any]:
    result = optimize_prompt(payload.text, payload.goal)
    memory_usage.append({"kind": "optimize", "tokens": result["optimizedTokens"], "timestamp": now_iso()})
    return {"ok": True, "result": result}


@api.post("/proxy")
async def proxy(payload: OptimizeIn) -> Dict[str, Any]:
    result = optimize_prompt(payload.text, payload.goal)
    return {
        "ok": True,
        "provider": "local",
        "model": "local-distiller",
        "result": result,
        "message": "Local TokenForge route is active. External model execution is disabled until provider configuration is supplied."
    }


@api.post("/checkout")
async def checkout(payload: CheckoutIn, request: Request) -> Dict[str, Any]:
    if payload.plan_id not in PLANS or payload.plan_id == "free":
        raise HTTPException(status_code=400, detail="Invalid paid plan")
    if not os.getenv("STRIPE_API_KEY"):
        raise HTTPException(status_code=503, detail="Billing is not configured for this deployment")
    return {
        "ok": False,
        "status": "manual-review-required",
        "plan": PLANS[payload.plan_id],
        "origin": payload.origin_url,
        "client": request.client.host if request.client else "unknown",
    }


@api.get("/usage")
async def usage() -> Dict[str, Any]:
    return {"ok": True, "events": len(memory_usage), "estimatedTokens": sum(item["tokens"] for item in memory_usage)}


app.include_router(api)


@app.get("/")
async def root() -> Dict[str, Any]:
    return {"ok": True, "service": "tokenforge-api", "health": "/api/health", "docs": "/docs"}
