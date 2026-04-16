"""Optional Langfuse tracing integration.

If LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are not set, all functions
are no-ops so agents require no code changes to run without tracing.
"""
from __future__ import annotations

import os
from typing import Any

_langfuse = None


def _get_langfuse():
    global _langfuse
    if _langfuse is not None:
        return _langfuse

    pub = os.environ.get("LANGFUSE_PUBLIC_KEY")
    sec = os.environ.get("LANGFUSE_SECRET_KEY")
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not pub or not sec:
        return None

    try:
        from langfuse import Langfuse  # type: ignore

        _langfuse = Langfuse(public_key=pub, secret_key=sec, host=host)
    except ImportError:
        pass

    return _langfuse


class Trace:
    """Thin wrapper around a Langfuse trace; no-ops if Langfuse is unavailable."""

    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        lf = _get_langfuse()
        self._trace = lf.trace(name=name, metadata=metadata or {}) if lf else None

    def span(self, name: str, input: Any = None) -> "Span":
        return Span(self._trace, name, input)

    def score(self, name: str, value: float, comment: str = "") -> None:
        if self._trace:
            self._trace.score(name=name, value=value, comment=comment)

    def update(self, output: Any = None, metadata: dict[str, Any] | None = None) -> None:
        if self._trace:
            self._trace.update(output=output, metadata=metadata or {})


class Span:
    def __init__(self, trace, name: str, input: Any = None) -> None:
        self._span = trace.span(name=name, input=input) if trace else None

    def end(self, output: Any = None) -> None:
        if self._span:
            self._span.end(output=output)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.end()
