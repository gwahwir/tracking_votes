"""Langfuse v4 tracing integration.

If LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are not set, the @observe
decorators become no-ops because Langfuse itself handles that gracefully.

Public API used by agents:
  - observe_trace(func)   — wraps an async generator as a root trace
  - observe_llm(func)     — wraps a function as a generation observation
"""
from __future__ import annotations

import os
from typing import Any

# Ensure Langfuse picks up keys before any decorator is evaluated
# (env is already loaded by run-local.sh / uvicorn at process start)

def _langfuse_configured() -> bool:
    return bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY")
        and os.environ.get("LANGFUSE_SECRET_KEY")
    )


def _init_env() -> None:
    """Copy LANGFUSE_BASE_URL → LANGFUSE_HOST if only the former is set."""
    base_url = os.environ.get("LANGFUSE_BASE_URL")
    if base_url and not os.environ.get("LANGFUSE_HOST"):
        os.environ["LANGFUSE_HOST"] = base_url


_init_env()

try:
    from langfuse import observe as _observe, get_client as _get_client  # type: ignore
    _HAS_LANGFUSE = True
except ImportError:
    _HAS_LANGFUSE = False


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def observe_trace(name: str | None = None):
    """Decorator: wraps a function as a Langfuse root trace."""
    if not _HAS_LANGFUSE:
        def _noop(fn):
            return fn
        return _noop
    return _observe(name=name)


def observe_llm(name: str | None = None):
    """Decorator: wraps a function as a Langfuse generation observation."""
    if not _HAS_LANGFUSE:
        def _noop(fn):
            return fn
        return _noop
    return _observe(name=name, as_type="generation")


# ---------------------------------------------------------------------------
# Low-level helper for manual generation logging (used by streaming paths)
# ---------------------------------------------------------------------------

def log_generation(
    name: str,
    model: str,
    input: Any,
    output: str,
    usage: dict[str, int] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log a generation inside the currently active Langfuse trace/span."""
    if not _HAS_LANGFUSE or not _langfuse_configured():
        return
    try:
        client = _get_client()
        with client.start_as_current_observation(
            type="generation",
            name=name,
            model=model,
            input=input,
            metadata=metadata or {},
        ) as gen:
            gen.update(output=output)
            if usage:
                gen.update(
                    usage_details={
                        "input": usage.get("prompt_tokens", 0),
                        "output": usage.get("completion_tokens", 0),
                    }
                )
    except Exception:
        pass  # never let tracing break the agent
