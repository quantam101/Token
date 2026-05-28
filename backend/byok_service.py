"""
TokenForge BYOK (Bring Your Own Key) service.

Lets Pro+ customers store their own OpenAI / Anthropic / Google Gemini API
keys in TokenForge. Keys are encrypted at rest with Fernet (AES-128-CBC + HMAC)
using a key derived from JWT_SECRET — so platform operators with DB access
cannot read customer keys without the server's JWT secret.

Public surface:
    - encrypt(plaintext: str) -> str
    - decrypt(ciphertext: str) -> str
    - mask(plaintext: str) -> str   # display-safe "sk-…last4"
    - SUPPORTED_PROVIDERS = ("openai", "anthropic", "google")
    - BYOK_PLANS = ("pro", "enterprise")  # which plans unlock BYOK
"""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

SUPPORTED_PROVIDERS = ("openai", "anthropic", "google")
BYOK_PLANS = ("pro", "enterprise")


def _fernet() -> Fernet:
    """Derive a stable 32-byte Fernet key from JWT_SECRET so we don't have to
    manage a second secret. Customers' encrypted keys will fail to decrypt if
    JWT_SECRET is rotated — which is the correct safety property (rotate
    intentionally; force users to re-paste their keys)."""
    jwt_secret = os.environ.get("JWT_SECRET", "")
    if not jwt_secret:
        raise RuntimeError("JWT_SECRET is required for BYOK encryption")
    digest = hashlib.sha256(jwt_secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(ciphertext: str) -> Optional[str]:
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return None


def mask(plaintext: str) -> str:
    """Return a display-safe redacted form: keeps first 4 + last 4 chars."""
    if not plaintext:
        return ""
    if len(plaintext) <= 12:
        return "…" + plaintext[-4:]
    return f"{plaintext[:4]}…{plaintext[-4:]}"


def looks_valid(provider: str, plaintext: str) -> bool:
    """Lightweight sanity check — reject obvious garbage before saving."""
    if not plaintext or len(plaintext) < 20:
        return False
    p = provider.lower()
    if p == "openai":
        return plaintext.startswith(("sk-", "sk-proj-"))
    if p == "anthropic":
        return plaintext.startswith("sk-ant-")
    if p == "google":
        return plaintext.startswith("AIza")
    return True
