"""
TokenForge LLM Router — drop-in replacement for emergentintegrations.llm.chat.

Routes async LLM calls to OpenAI, Anthropic, or Google Gemini using their
official Python SDKs. No Emergent runtime dependency.

API parity with the previous LlmChat:
    chat = LlmChat(api_key=..., session_id=..., system_message=...).with_model(provider, model)
    response_text: str = await chat.send_message(UserMessage(text="..."))
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from pydantic import BaseModel

log = logging.getLogger("tokenforge.llm_router")

# Lazy provider clients — module-level singletons.
_openai_client = None
_anthropic_client = None
_gemini_client = None


def _get_openai():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        _openai_client = AsyncOpenAI(api_key=key)
    return _openai_client


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        _anthropic_client = AsyncAnthropic(api_key=key)
    return _anthropic_client


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY (or GEMINI_API_KEY) is not configured")
        _gemini_client = genai.Client(api_key=key)
    return _gemini_client


# Map Emergent-style aliases to real provider model identifiers.
_MODEL_ALIASES = {
    "anthropic": {
        # Emergent used these short tags — map to current Anthropic SDK strings.
        "claude-sonnet-4-6": "claude-sonnet-4-5",
        "claude-sonnet-4-5": "claude-sonnet-4-5",
        "claude-opus-4-5": "claude-opus-4-5",
        "claude-haiku-4-5": "claude-haiku-4-5",
    },
    "openai": {
        # Pass-through; included for explicit allow-list semantics.
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
        "gpt-4.1": "gpt-4.1",
        "gpt-4.1-mini": "gpt-4.1-mini",
        "gpt-5.2": "gpt-5.2",
    },
    "google": {
        "gemini-2.5-pro": "gemini-2.5-pro",
        "gemini-2.5-flash": "gemini-2.5-flash",
        "gemini-1.5-pro": "gemini-1.5-pro",
        "gemini-1.5-flash": "gemini-1.5-flash",
    },
}


def _resolve_model(provider: str, model: str) -> str:
    table = _MODEL_ALIASES.get(provider.lower(), {})
    return table.get(model, model)  # pass-through if not in alias table


class UserMessage(BaseModel):
    """Compatibility wrapper — mirrors emergentintegrations.llm.chat.UserMessage."""
    text: str


class LlmChat:
    """
    Async LLM chat client routed to OpenAI / Anthropic / Google Gemini.

    Drop-in for emergentintegrations.llm.chat.LlmChat:
        - constructor takes api_key, session_id, system_message (api_key is ignored;
          provider-specific keys come from env)
        - .with_model(provider, model_name) selects the provider
        - .send_message(UserMessage(text=...)) returns plain str
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        session_id: Optional[str] = None,
        system_message: Optional[str] = None,
    ) -> None:
        self.session_id = session_id
        self.system_message = system_message or "You are a helpful assistant."
        self._provider: Optional[str] = None
        self._model: Optional[str] = None

    def with_model(self, provider: str, model_name: str) -> "LlmChat":
        self._provider = (provider or "").lower()
        self._model = model_name
        return self

    async def send_message(self, msg: UserMessage) -> str:
        if not self._provider or not self._model:
            raise RuntimeError("provider/model not set — call .with_model() first")
        text = msg.text
        resolved_model = _resolve_model(self._provider, self._model)
        if self._provider == "openai":
            return await self._openai(resolved_model, text)
        if self._provider == "anthropic":
            return await self._anthropic(resolved_model, text)
        if self._provider in ("google", "gemini"):
            return await self._gemini(resolved_model, text)
        raise ValueError(f"unsupported provider: {self._provider}")

    async def _openai(self, model: str, user_text: str) -> str:
        client = _get_openai()
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
        client = _get_anthropic()
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
        client = _get_gemini()
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
