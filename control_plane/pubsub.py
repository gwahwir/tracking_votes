"""Pub/sub broker for WebSocket fan-out.

InMemoryBroker  — default; asyncio.Queue per task channel.
RedisBroker     — used when REDIS_URL is set; uses redis-py async pub/sub.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator, Optional

import structlog

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# In-memory broker
# ---------------------------------------------------------------------------

class InMemoryBroker:
    def __init__(self) -> None:
        # task_id -> set of subscriber queues
        self._subscribers: dict[str, set[asyncio.Queue]] = {}

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        queues = self._subscribers.get(channel, set())
        payload = json.dumps(message)
        for q in queues:
            await q.put(payload)

    async def subscribe(self, channel: str) -> AsyncGenerator[str, None]:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(channel, set()).add(q)
        log.debug("pubsub.subscribed", channel=channel)
        try:
            while True:
                msg = await q.get()
                yield msg
        finally:
            self._subscribers.get(channel, set()).discard(q)
            log.debug("pubsub.unsubscribed", channel=channel)

    async def initialize(self) -> None:
        pass

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Redis broker
# ---------------------------------------------------------------------------

class RedisBroker:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._redis = None  # redis.asyncio.Redis, set in initialize()

    async def initialize(self) -> None:
        import redis.asyncio as aioredis  # type: ignore

        self._redis = await aioredis.from_url(
            self._redis_url, encoding="utf-8", decode_responses=True
        )
        log.info("redis.connected", url=self._redis_url)

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        await self._redis.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str) -> AsyncGenerator[str, None]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        log.debug("redis.subscribed", channel=channel)
        try:
            async for raw in pubsub.listen():
                if raw["type"] == "message":
                    yield raw["data"]
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            log.debug("redis.unsubscribed", channel=channel)

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_broker(redis_url: Optional[str]) -> InMemoryBroker | RedisBroker:
    if redis_url:
        log.info("pubsub.backend", backend="redis")
        return RedisBroker(redis_url)
    log.info("pubsub.backend", backend="in_memory")
    return InMemoryBroker()
