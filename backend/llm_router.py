"""
TokenForge LLM Router — async multi-provider LLM client.

Provider priority (cost-optimised):
  0. LM Studio       — local OpenAI-compatible server (localhost:1234), highest priority
  1. Groq            — fastest free tier (llama/gemma/mixtral)
  2. HuggingFace     — free cloud inference API, thousands of open models
  3. Google Gemini   — best free quality (gemini-2.0-flash, 1.5-flash)
  4. OpenAI          — paid, highest quality
  5. Anthropic       — paid, highest reasoning
  6. Pollinations    — keyless free fallback (always available)

API:
    chat = LlmChat(session_id=..., system_message=..., byok_keys={...}).with_model(provider, model)
    response_text: str = await chat.send_message(UserMessage(text="..."))

byok_keys: optional dict of customer-supplied provider keys (Pro+ feature).
When present, the matching provider call uses the customer key instead of
the platform env key.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Optional

import httpx
from pydantic import BaseModel
import os as _gw_os
import httpx as _gw_httpx

_GW_URL = _gw_os.environ.get("GATEWAY_URL", "").rstrip("/")
_GW_KEY = _gw_os.environ.get("LITELLM_MASTER_KEY", "")

async def _call_gateway(text: str, system: str = "", max_tokens: int = 1024) -> str | None:
    """Route through LiteLLM hypervisor. Returns None silently if unavailable."""
    if not _GW_URL:
        return None
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": text})
    headers = {"Authorization": f"Bearer {_GW_KEY}"} if _GW_KEY else {}
    try:
        async with _gw_httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{_GW_URL}/v1/chat/completions",
                json={"model": "autonomous-intelligence-mesh", "messages": messages, "max_tokens": max_tokens},
                headers=headers,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None




log = logging.getLogger("tokenforge.llm_router")

# ---------------------------------------------------------------------------
# Lazy provider clients
# ---------------------------------------------------------------------------
_openai_client = None
_anthropic_client = None
_gemini_client = None
_groq_client = None


def _make_openai(api_key: str):
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=api_key)


def _make_groq(api_key: str):
    """Groq uses the OpenAI-compatible SDK with a custom base_url."""
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def _make_lmstudio(base_url: str = ""):
    """LM Studio uses the OpenAI-compatible SDK with a local base_url."""
    from openai import AsyncOpenAI
    url = (base_url or os.environ.get("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")).rstrip("/")
    return AsyncOpenAI(api_key="lm-studio", base_url=url)


def _make_huggingface(model: str, api_key: str):
    """HuggingFace Inference API uses OpenAI-compatible endpoint per model."""
    from openai import AsyncOpenAI
    url = f"https://api-inference.huggingface.co/models/{model}/v1"
    return AsyncOpenAI(api_key=api_key, base_url=url)


def _make_anthropic(api_key: str):
    from anthropic import AsyncAnthropic
    return AsyncAnthropic(api_key=api_key)


def _make_gemini(api_key: str):
    from google import genai
    return genai.Client(api_key=api_key)


def _get_groq():
    global _groq_client
    if _groq_client is None:
        key = os.environ.get("GROQ_API_KEY", "").strip()
        if not key:
            raise RuntimeError("GROQ_API_KEY is not configured on the platform")
        _groq_client = _make_groq(key)
    return _groq_client


def _get_openai():
    global _openai_client
    if _openai_client is None:
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not configured on the platform")
        _openai_client = _make_openai(key)
    return _openai_client


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured on the platform")
        _anthropic_client = _make_anthropic(key)
    return _anthropic_client


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        key = (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or "").strip()
        if not key:
            raise RuntimeError("GOOGLE_API_KEY (or GEMINI_API_KEY) is not configured on the platform")
        _gemini_client = _make_gemini(key)
    return _gemini_client


# ---------------------------------------------------------------------------
# LM Studio helpers
# ---------------------------------------------------------------------------
def _lmstudio_enabled() -> bool:
    """True when LM Studio local server is configured or explicitly enabled."""
    if os.environ.get("LM_STUDIO_BASE_URL", "").strip():
        return True
    return os.environ.get("LM_STUDIO_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")


def _lmstudio_model() -> str:
    """The model name to use with LM Studio (matches what is loaded in the app)."""
    raw = os.environ.get("LM_STUDIO_MODELS", "").strip()
    first = raw.split(",")[0].strip() if raw else ""
    return (
        os.environ.get("LM_STUDIO_MODEL", "").strip()
        or first
        or "local-model"
    )


def _get_lmstudio():
    """LM Studio client - no key needed, just a running local server."""
    return _make_lmstudio()


# ---------------------------------------------------------------------------
# HuggingFace helpers
# ---------------------------------------------------------------------------
def _hf_api_key() -> str:
    """Return HuggingFace API token or empty string."""
    return (
        os.environ.get("HUGGINGFACE_API_KEY", "").strip()
        or os.environ.get("HF_TOKEN", "").strip()
    )


def _hf_llm_models() -> list[str]:
    """Ordered list of HuggingFace LLM models for text inference."""
    raw = os.environ.get("HF_LLM_MODELS", "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    return [
        "meta-llama/Llama-3.2-3B-Instruct",
        "microsoft/Phi-3.5-mini-instruct",
        "mistralai/Mistral-7B-Instruct-v0.3",
        "HuggingFaceH4/zephyr-7b-beta",
    ]


# ---------------------------------------------------------------------------
# Platform provider availability
# ---------------------------------------------------------------------------
def platform_providers_available() -> list[str]:
    """Return list of configured platform providers in cost-priority order."""
    available = []
    if _lmstudio_enabled():
        available.append("lmstudio")
    if os.environ.get("GROQ_API_KEY", "").strip():
        available.append("groq")
    if _hf_api_key():
        available.append("huggingface")
    if (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or "").strip():
        available.append("gemini")
    if os.environ.get("OPENAI_API_KEY", "").strip():
        available.append("openai")
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        available.append("anthropic")
    # Pollinations is always available (keyless free)
    pollinations_enabled = os.environ.get("LLM_POLLINATIONS_FALLBACK", "true").lower() not in {"false", "0", "off"}
    if pollinations_enabled:
        available.append("pollinations")
    return available


# ---------------------------------------------------------------------------
# Model alias tables
# ---------------------------------------------------------------------------
_MODEL_ALIASES = {
    "lmstudio": {
        "default": "local-model",
        "local-model": "local-model",
        "llama-3.2-3b-instruct": "llama-3.2-3b-instruct",
        "gemma-2-2b-it": "gemma-2-2b-it",
        "mistral-7b-instruct-v0.3": "mistral-7b-instruct-v0.3",
    },
    "huggingface": {
        "default": "meta-llama/Llama-3.2-3B-Instruct",
        "llama-3b": "meta-llama/Llama-3.2-3B-Instruct",
        "phi-3.5": "microsoft/Phi-3.5-mini-instruct",
        "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.3",
        "zephyr": "HuggingFaceH4/zephyr-7b-beta",
    },
    "groq": {
        # Prefer the fastest/cheapest Groq models first
        "default": "llama-3.3-70b-versatile",
        "llama-3.3-70b-versatile": "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant": "llama-3.1-8b-instant",
        "gemma2-9b-it": "gemma2-9b-it",
        "mixtral-8x7b": "mixtral-8x7b-32768",
    },
    "anthropic": {
        "claude-sonnet-4-6": "claude-sonnet-4-5",
        "claude-sonnet-4-5": "claude-sonnet-4-5",
        "claude-opus-4-5": "claude-opus-4-5",
        "claude-haiku-4-5": "claude-haiku-4-5",
    },
    "openai": {
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
        "gpt-4.1": "gpt-4.1",
        "gpt-4.1-mini": "gpt-4.1-mini",
        "gpt-5.2": "gpt-5.2",
    },
    "google": {
        "gemini-2.5-pro": "gemini-2.5-pro",
        "gemini-2.5-flash": "gemini-2.5-flash",
        "gemini-2.0-flash": "gemini-2.0-flash",
        "gemini-1.5-pro": "gemini-1.5-pro",
        "gemini-1.5-flash": "gemini-1.5-flash",
    },
    "gemini": {  # alias for google
        "gemini-2.0-flash": "gemini-2.0-flash",
        "gemini-2.5-flash": "gemini-2.5-flash",
        "gemini-1.5-flash": "gemini-1.5-flash",
    },
    "pollinations": {
        "default": "openai",
        "openai": "openai",
        "openai-fast": "openai-fast",
        "mistral": "mistral",
    },
}

# Default Groq models to try in order when model not specified
GROQ_FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "gemma2-9b-it",
    "llama-3.1-8b-instant",
]

# Default Gemini models to try in order
GEMINI_FALLBACK_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
]

# HuggingFace free LLM models to try in order
HF_FALLBACK_MODELS = [
    "meta-llama/Llama-3.2-3B-Instruct",
    "microsoft/Phi-3.5-mini-instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "HuggingFaceH4/zephyr-7b-beta",
]


def _resolve_model(provider: str, model: str) -> str:
    prov = provider.lower()
    table = _MODEL_ALIASES.get(prov, {})
    if model in table:
        return table[model]
    if not model or model == "default":
        return table.get("default", model)
    return model  # pass-through


# ---------------------------------------------------------------------------
# Message models
# ---------------------------------------------------------------------------
class UserMessage(BaseModel):
    """Single-turn user message wrapper."""
    text: str


# ---------------------------------------------------------------------------
# Pollinations (keyless free API)
# ---------------------------------------------------------------------------
POLLINATIONS_URL = "https://text.pollinations.ai/openai"


async def _pollinations_complete(system: str, user_text: str, model: str = "openai") -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
        "max_tokens": 1024,
        "temperature": 0.7,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            POLLINATIONS_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
        return (data.get("choices", [{}])[0].get("message", {}).get("content", "") or "").strip()


# ---------------------------------------------------------------------------
# Main LlmChat class
# ---------------------------------------------------------------------------
class LlmChat:
    """
    Async LLM chat client with automatic failover across free and paid providers.

    Usage:
        chat = LlmChat(session_id=..., system_message=..., byok_keys={...})
        chat = chat.with_model(provider, model_name)
        response = await chat.send_message(UserMessage(text="..."))

    Provider routing:
        - byok_keys override platform keys for Pro+ customers
        - Platform fallback order: groq → gemini → openai → anthropic → pollinations
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        session_id: Optional[str] = None,
        system_message: Optional[str] = None,
        byok_keys: Optional[dict] = None,
    ) -> None:
        self.session_id = session_id
        self.system_message = system_message or "You are a helpful assistant."
        self._provider: Optional[str] = None
        self._model: Optional[str] = None
        self._byok = byok_keys or {}

    def with_model(self, provider: str, model_name: str) -> "LlmChat":
        self._provider = (provider or "").lower()
        self._model = model_name
        return self

    async def send_message(self, msg: UserMessage) -> str:
        if not self._provider:
            # Auto-select cheapest available platform provider
            return await self._auto_route(msg.text)

        provider = self._provider
        model = _resolve_model(provider, self._model or "default")

        if provider == "lmstudio":
            return await self._lmstudio(model, msg.text)
        if provider == "groq":
            return await self._groq(model, msg.text)
        if provider == "huggingface":
            return await self._huggingface(model, msg.text)
        if provider == "openai":
            return await self._openai(model, msg.text)
        if provider == "anthropic":
            return await self._anthropic(model, msg.text)
        if provider in ("google", "gemini"):
            return await self._gemini(model, msg.text)
        if provider == "pollinations":
            return await _pollinations_complete(self.system_message, msg.text, model)

        raise ValueError(f"Unsupported provider: {provider}")

    async def _auto_route(self, user_text: str) -> str:
        # Hypervisor gateway first
        _gw = await _call_gateway(prompt)
        if _gw:
            return _gw
        """Try providers in cost order until one succeeds."""
        providers = platform_providers_available()
        last_error: Exception = RuntimeError("No LLM providers configured")

        for prov in providers:
            try:
                if prov == "lmstudio":
                    try:
                        return await self._lmstudio(_lmstudio_model(), user_text)
                    except Exception as exc:
                        log.warning("LM Studio failed: %s - falling through", str(exc)[:120])
                        continue
                if prov == "groq":
                    for model in GROQ_FALLBACK_MODELS:
                        try:
                            return await self._groq(model, user_text)
                        except Exception:
                            continue
                elif prov == "huggingface":
                    for model in HF_FALLBACK_MODELS:
                        try:
                            return await self._huggingface(model, user_text)
                        except Exception:
                            continue
                elif prov == "gemini":
                    for model in GEMINI_FALLBACK_MODELS:
                        try:
                            return await self._gemini(model, user_text)
                        except Exception:
                            continue
                elif prov == "openai":
                    return await self._openai("gpt-4o-mini", user_text)
                elif prov == "anthropic":
                    return await self._anthropic("claude-haiku-4-5", user_text)
                elif prov == "pollinations":
                    for model in ["openai", "openai-fast", "mistral"]:
                        try:
                            return await _pollinations_complete(self.system_message, user_text, model)
                        except Exception:
                            continue
            except Exception as exc:
                last_error = exc
                log.warning("LLM auto-route: provider=%s failed: %s", prov, str(exc)[:120])
                continue

        raise RuntimeError(f"All LLM providers failed. Last: {last_error}")

    # ── Provider implementations ──────────────────────────────────────────────

    async def _lmstudio(self, model: str, user_text: str) -> str:
        """Call LM Studio local server (OpenAI-compatible API at localhost:1234)."""
        client = _get_lmstudio()
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": user_text},
            ],
            max_tokens=1024,
            temperature=0.7,
        )
        return (resp.choices[0].message.content or "").strip()

    async def _huggingface(self, model: str, user_text: str) -> str:
        """Call HuggingFace Inference API — free, OpenAI-compatible."""
        byok = self._byok.get("huggingface")
        api_key = byok or _hf_api_key()
        if not api_key:
            raise RuntimeError("HUGGINGFACE_API_KEY or HF_TOKEN not set")
        client = _make_huggingface(model, api_key)
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": user_text},
            ],
            max_tokens=1024,
            temperature=0.7,
        )
        return (resp.choices[0].message.content or "").strip()

    async def _groq(self, model: str, user_text: str) -> str:
        byok = self._byok.get("groq")
        client = _make_groq(byok) if byok else _get_groq()
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": user_text},
            ],
            max_tokens=1024,
            temperature=0.7,
        )
        return (resp.choices[0].message.content or "").strip()

    async def _openai(self, model: str, user_text: str) -> str:
        byok = self._byok.get("openai")
        client = _make_openai(byok) if byok else _get_openai()
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": user_text},
            ],
            max_tokens=1024,
            temperature=0.7,
        )
        return (resp.choices[0].message.content or "").strip()

    async def _anthropic(self, model: str, user_text: str) -> str:
        byok = self._byok.get("anthropic")
        client = _make_anthropic(byok) if byok else _get_anthropic()
        resp = await client.messages.create(
            model=model,
            system=self.system_message,
            messages=[{"role": "user", "content": user_text}],
            max_tokens=1024,
            temperature=0.7,
        )
        parts = []
        for block in resp.content:
            txt = getattr(block, "text", None)
            if txt:
                parts.append(txt)
        return "".join(parts).strip()

    async def _gemini(self, model: str, user_text: str) -> str:
        byok = self._byok.get("google") or self._byok.get("gemini")
        client = _make_gemini(byok) if byok else _get_gemini()
        from google.genai import types as genai_types

        prompt = f"{self.system_message}\n\nUser: {user_text}"

        def _call_sync():
            return client.models.generate_content(
                model=model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=1024,
                ),
            )

        resp = await asyncio.to_thread(_call_sync)
        return (getattr(resp, "text", "") or "").strip()
