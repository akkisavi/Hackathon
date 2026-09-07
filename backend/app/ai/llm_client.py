"""Provider-agnostic LLM client.

Any OpenAI-compatible endpoint works — set `LLM_BASE_URL`, `LLM_MODEL`,
`LLM_API_KEY` in `.env`. Default is Google Gemini; NVIDIA build, Groq,
a local vLLM, etc. are drop-in swaps.

Phase 2 builds the incident-narrative and NL-query-to-PostGIS flows on
top of `chat()` / the raw `client`.
"""
from __future__ import annotations

from functools import lru_cache

from openai import OpenAI

from app.core.config import get_settings


@lru_cache
def get_client() -> OpenAI:
    s = get_settings()
    if not s.llm_api_key:
        raise RuntimeError("LLM_API_KEY is not set (see .env)")
    return OpenAI(api_key=s.llm_api_key, base_url=s.llm_base_url)


def chat(messages: list[dict], **kwargs) -> str:
    """Single-turn convenience wrapper. `kwargs` pass through to the
    chat.completions call (temperature, tools, response_format, ...)."""
    resp = get_client().chat.completions.create(
        model=get_settings().llm_model, messages=messages, **kwargs
    )
    return resp.choices[0].message.content or ""
