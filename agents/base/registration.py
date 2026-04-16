"""Self-registration with the control plane on agent startup."""
from __future__ import annotations

import os
from typing import Any

import httpx
import structlog

log = structlog.get_logger(__name__)

_REGISTER_TIMEOUT = 10.0
_RETRY_ATTEMPTS = 5
_RETRY_DELAY = 2.0  # seconds


async def register_with_control_plane(card: dict[str, Any]) -> None:
    """POST the agent card to the control plane /register endpoint.

    Retries up to _RETRY_ATTEMPTS times to tolerate startup ordering races
    (e.g. agent boots before control plane is fully up).
    """
    import asyncio

    control_plane_url = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8000")
    url = f"{control_plane_url.rstrip('/')}/register"

    async with httpx.AsyncClient(timeout=_REGISTER_TIMEOUT) as client:
        for attempt in range(1, _RETRY_ATTEMPTS + 1):
            try:
                resp = await client.post(url, json=card)
                resp.raise_for_status()
                log.info(
                    "agent.registered",
                    type_id=card["type_id"],
                    control_plane=control_plane_url,
                )
                return
            except Exception as exc:
                log.warning(
                    "agent.register_failed",
                    attempt=attempt,
                    error=str(exc),
                    retrying=attempt < _RETRY_ATTEMPTS,
                )
                if attempt < _RETRY_ATTEMPTS:
                    await asyncio.sleep(_RETRY_DELAY * attempt)

    log.error("agent.register_give_up", type_id=card["type_id"])
