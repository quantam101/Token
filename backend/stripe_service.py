"""
TokenForge Stripe Service — drop-in replacement for
emergentintegrations.payments.stripe.checkout.

Wraps the official Stripe Python SDK in async methods. Preserves the
attribute-access response shapes used by server.py:

    session = await stripe_checkout.create_checkout_session(req)
    session.session_id, session.url

    status_resp = await stripe_checkout.get_checkout_status(session_id)
    status_resp.status / payment_status / amount_total / currency / metadata

    ev = await stripe_checkout.handle_webhook(body, sig)
    ev.payment_status, ev.session_id, ev.metadata
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

import stripe
from pydantic import BaseModel, Field

log = logging.getLogger("tokenforge.stripe")


# ---- Request / Response models ---------------------------------------------

class CheckoutSessionRequest(BaseModel):
    """Mirrors the request shape used by server.py — amount (USD float),
    currency, redirect URLs, and free-form metadata."""
    amount: float
    currency: str = "usd"
    success_url: str
    cancel_url: str
    metadata: Dict[str, str] = Field(default_factory=dict)
    # The original emergent flow always produced a single ad-hoc one-time
    # line item — we keep that semantic by default.
    product_name: Optional[str] = None


class _Obj:
    """Lightweight attribute-bag so callers can use dot access exactly as
    they did with the prior SDK."""

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


# ---- Service ----------------------------------------------------------------

class StripeCheckout:
    def __init__(
        self,
        api_key: Optional[str] = None,
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("STRIPE_API_KEY")
        if not self.api_key:
            raise RuntimeError("STRIPE_API_KEY is not configured")
        self.webhook_url = webhook_url
        # webhook_secret may legitimately be unset until the user wires the
        # endpoint in the Stripe Dashboard — we degrade gracefully in
        # handle_webhook() rather than refusing at construct time.
        self.webhook_secret = webhook_secret or os.environ.get("STRIPE_WEBHOOK_SECRET") or ""

    # ---- create -------------------------------------------------------------

    async def create_checkout_session(self, req: CheckoutSessionRequest) -> _Obj:
        amount_cents = int(round(float(req.amount) * 100))
        product_name = req.product_name or req.metadata.get("plan_id", "TokenForge plan")

        def _call_sync():
            stripe.api_key = self.api_key
            return stripe.checkout.Session.create(
                mode="payment",
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": req.currency,
                        "unit_amount": amount_cents,
                        "product_data": {"name": str(product_name)},
                    },
                    "quantity": 1,
                }],
                success_url=req.success_url,
                cancel_url=req.cancel_url,
                metadata=req.metadata or {},
            )

        try:
            session = await asyncio.to_thread(_call_sync)
        except Exception:
            log.exception("stripe.checkout.Session.create failed")
            raise

        return _Obj(
            session_id=session.id,
            url=session.url,
            amount_total=getattr(session, "amount_total", amount_cents),
            currency=getattr(session, "currency", req.currency),
            metadata=dict(getattr(session, "metadata", {}) or {}),
        )

    # ---- poll status --------------------------------------------------------

    async def get_checkout_status(self, session_id: str) -> _Obj:
        def _call_sync():
            stripe.api_key = self.api_key
            return stripe.checkout.Session.retrieve(session_id)

        try:
            session = await asyncio.to_thread(_call_sync)
        except Exception:
            log.exception("stripe.checkout.Session.retrieve failed for %s", session_id)
            raise

        return _Obj(
            session_id=session.id,
            status=getattr(session, "status", None),
            payment_status=getattr(session, "payment_status", None),
            amount_total=getattr(session, "amount_total", 0),
            currency=getattr(session, "currency", "usd"),
            metadata=dict(getattr(session, "metadata", {}) or {}),
        )

    # ---- webhook ------------------------------------------------------------

    async def handle_webhook(self, body: bytes, sig_header: str) -> _Obj:
        if not self.webhook_secret:
            # Without a configured signing secret we MUST refuse — accepting
            # unverified webhooks would let an attacker upgrade arbitrary
            # accounts. Server.py already treats a raised exception here as
            # `{received: False}`, so this is the safe failure mode.
            raise RuntimeError(
                "STRIPE_WEBHOOK_SECRET is not configured — webhook ignored"
            )
        if not sig_header:
            raise ValueError("Missing Stripe-Signature header")

        def _construct():
            stripe.api_key = self.api_key
            return stripe.Webhook.construct_event(
                payload=body if isinstance(body, (bytes, str)) else bytes(body),
                sig_header=sig_header,
                secret=self.webhook_secret,
            )

        event = await asyncio.to_thread(_construct)

        # Normalise into the shape server.py expects.
        data_obj: Dict[str, Any] = (event.get("data") or {}).get("object", {}) if isinstance(event, dict) else {}
        if not data_obj:
            # stripe SDK returns a stripe.Event (dict-like) — try attribute path
            try:
                data_obj = event["data"]["object"]
            except Exception:
                data_obj = {}

        return _Obj(
            event_type=event.get("type") if isinstance(event, dict) else getattr(event, "type", None),
            session_id=data_obj.get("id"),
            payment_status=data_obj.get("payment_status"),
            status=data_obj.get("status"),
            amount_total=data_obj.get("amount_total"),
            currency=data_obj.get("currency"),
            metadata=dict(data_obj.get("metadata") or {}),
        )
