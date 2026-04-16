"""A2A client — dispatches JSON-RPC 2.0 tasks to agents via HTTP + SSE streaming."""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator

import httpx
import structlog

log = structlog.get_logger(__name__)

_DISPATCH_TIMEOUT = 10.0   # seconds to establish the connection
_STREAM_TIMEOUT = 300.0    # seconds to receive the full streamed response


class A2AClient:
    """Thin HTTP client that speaks the A2A JSON-RPC 2.0 protocol."""

    def __init__(self) -> None:
        # Shared async client — created lazily, reused across requests
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(
                connect=_DISPATCH_TIMEOUT,
                read=_STREAM_TIMEOUT,
                write=_DISPATCH_TIMEOUT,
                pool=_DISPATCH_TIMEOUT,
            ))
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Task dispatch  (returns AsyncGenerator of raw SSE lines)
    # ------------------------------------------------------------------

    async def dispatch(
        self,
        agent_url: str,
        task_id: str,
        message_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Send a task to an agent and stream back SSE lines.

        Yields raw text lines as they arrive.  Callers filter for
        ``NODE_OUTPUT::`` markers or ``data:`` SSE envelopes as needed.
        """
        url = f"{agent_url.rstrip('/')}/tasks/send"
        payload = _build_payload(task_id, message_text, metadata or {})

        log.info("a2a.dispatch", task_id=task_id, agent_url=agent_url)

        async with self._get_client().stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                yield line

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    async def cancel(self, agent_url: str, task_id: str) -> dict[str, Any]:
        """Send tasks/cancel to the agent."""
        url = f"{agent_url.rstrip('/')}/tasks/cancel"
        payload = {
            "jsonrpc": "2.0",
            "id": task_id,
            "method": "tasks/cancel",
            "params": {"id": task_id},
        }
        resp = await self._get_client().post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_payload(task_id: str, message_text: str, metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": task_id,
        "method": "tasks/send",
        "params": {
            "id": task_id,
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": message_text}],
            },
            "metadata": {"task_id": task_id, "source": "control_plane", **metadata},
        },
    }


def parse_sse_event(line: str) -> dict[str, Any] | None:
    """Parse a ``data: {...}`` SSE line into a dict; returns None for comments/blanks."""
    line = line.strip()
    if not line or line.startswith(":"):
        return None
    if line.startswith("data:"):
        data = line[5:].strip()
        if data == "[DONE]":
            return {"type": "done"}
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {"type": "raw", "content": data}
    return None
