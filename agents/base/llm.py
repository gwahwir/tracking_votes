"""Shared LLM client — OpenAI SDK → OpenRouter (primary) + Anthropic (fallback).

Usage:
    from agents.base.llm import llm_call, llm_stream

Both functions accept standard OpenAI-style message lists and keyword args.
"""
from __future__ import annotations

import os
import time
from typing import Any, AsyncGenerator, Generator

import structlog

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# OpenRouter client (primary)
# ---------------------------------------------------------------------------

def _make_openai_client():
    from openai import OpenAI  # type: ignore

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(
        api_key=key,
        base_url=os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
        default_headers={
            "HTTP-Referer": os.environ.get("APP_URL", "http://localhost:5173"),
            "X-Title": "Johor Election Dashboard",
        },
    )


def _get_model(override: str | None = None) -> str:
    return override or os.environ.get("OPENAI_MODEL", "openai/gpt-4o")


# ---------------------------------------------------------------------------
# Anthropic fallback
# ---------------------------------------------------------------------------

def _make_anthropic_client():
    import anthropic  # type: ignore

    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def _anthropic_call(messages: list[dict], **kwargs) -> str:
    client = _make_anthropic_client()
    # Convert OpenAI message format → Anthropic format
    system = ""
    anthro_messages = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            anthro_messages.append({"role": m["role"], "content": m["content"]})

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=kwargs.get("max_tokens", 4096),
        system=system,
        messages=anthro_messages,
    )
    return resp.content[0].text


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def _openrouter_call(messages: list[dict[str, Any]], model: str | None = None, **kwargs) -> str:
    """Call OpenRouter with retry (exponential backoff, up to 3 attempts).

    If response_format is passed but the model doesn't support it, retries without it.
    """
    max_attempts = 3
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            client = _make_openai_client()
            resp = client.chat.completions.create(
                model=_get_model(model),
                messages=messages,
                **kwargs,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            last_exc = exc
            error_str = str(exc).lower()
            if any(code in error_str for code in ("401", "403", "invalid api key", "unauthorized")):
                raise
            # Some OSS models don't support response_format — retry without it
            if "response_format" in error_str or "unsupported" in error_str:
                kwargs.pop("response_format", None)
                log.warning("openrouter.dropped_response_format", model=_get_model(model))
                continue
            if attempt < max_attempts - 1:
                delay = 2.0 ** attempt
                log.warning("openrouter.retry", attempt=attempt + 1, delay=delay, error=str(exc))
                time.sleep(delay)
    raise last_exc  # type: ignore[misc]


def llm_call(messages: list[dict[str, Any]], model: str | None = None, **kwargs) -> str:
    """Synchronous LLM call with Anthropic fallback.

    kwargs are forwarded to the OpenAI SDK (e.g. temperature, response_format).
    Pass model= to override the default (e.g. a cheaper/faster model for classification).
    """
    try:
        return _openrouter_call(messages, model=model, **kwargs)
    except Exception as exc:
        _maybe_fallback_log(exc)
        return _anthropic_call(messages, **kwargs)


def llm_stream(messages: list[dict[str, Any]], **kwargs) -> Generator[str, None, None]:
    """Synchronous streaming LLM call; yields text chunks.

    Falls back to a single non-streaming Anthropic call on OpenRouter error.
    """
    try:
        client = _make_openai_client()
        stream = client.chat.completions.create(
            model=_get_model(),
            messages=messages,
            stream=True,
            **kwargs,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as exc:
        _maybe_fallback_log(exc)
        yield _anthropic_call(messages, **kwargs)


async def llm_call_with_fallback(messages: list[dict], **kwargs) -> str:
    """Async wrapper around llm_call for use in async contexts (e.g. seat_agent)."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: llm_call(messages, **kwargs))


def _maybe_fallback_log(exc: Exception) -> None:
    try:
        import openai  # type: ignore
        if isinstance(exc, (openai.RateLimitError, openai.APIStatusError)):
            log.warning("openrouter.failed_fallback", error=str(exc))
            return
    except ImportError:
        pass
    log.warning("llm.failed_fallback", error=str(exc))
