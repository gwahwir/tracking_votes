"""Agent registry — self-registration, health polling, least-connections load balancing."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import structlog

log = structlog.get_logger(__name__)

_HEALTH_TIMEOUT = 5.0  # seconds per health check request


@dataclass
class AgentRegistration:
    name: str
    type_id: str
    url: str
    capabilities: dict[str, Any] = field(default_factory=dict)
    healthy: bool = True
    task_count: int = 0
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type_id": self.type_id,
            "url": self.url,
            "capabilities": self.capabilities,
            "healthy": self.healthy,
            "task_count": self.task_count,
            "last_seen": self.last_seen.isoformat(),
        }


class AgentRegistry:
    def __init__(self, poll_interval: int = 30) -> None:
        self._agents: dict[str, AgentRegistration] = {}  # type_id -> registration
        self._poll_interval = poll_interval
        self._poll_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, card: dict[str, Any]) -> AgentRegistration:
        """Register or update an agent from its agent card."""
        type_id = card["type_id"]
        reg = AgentRegistration(
            name=card["name"],
            type_id=type_id,
            url=card["url"],
            capabilities=card.get("capabilities", {}),
            healthy=True,
            last_seen=datetime.now(timezone.utc),
        )
        # Preserve task_count if agent is re-registering
        if type_id in self._agents:
            reg.task_count = self._agents[type_id].task_count
        self._agents[type_id] = reg
        log.info("agent.registered", type_id=type_id, url=reg.url)
        return reg

    def deregister(self, type_id: str) -> None:
        if type_id in self._agents:
            del self._agents[type_id]
            log.info("agent.deregistered", type_id=type_id)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_all(self) -> list[AgentRegistration]:
        return list(self._agents.values())

    def get(self, type_id: str) -> Optional[AgentRegistration]:
        return self._agents.get(type_id)

    def pick(self, type_id: str) -> Optional[AgentRegistration]:
        """Least-connections selection across all healthy instances of type_id.

        Currently there is one instance per type_id, but the interface is
        forward-compatible with multiple replicas once we key by (type_id, url).
        """
        candidates = [
            a for a in self._agents.values()
            if a.type_id == type_id and a.healthy
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda a: a.task_count)

    # ------------------------------------------------------------------
    # Task count tracking (called by routes on dispatch / completion)
    # ------------------------------------------------------------------

    def increment(self, type_id: str) -> None:
        if type_id in self._agents:
            self._agents[type_id].task_count += 1

    def decrement(self, type_id: str) -> None:
        if type_id in self._agents:
            self._agents[type_id].task_count = max(
                0, self._agents[type_id].task_count - 1
            )

    # ------------------------------------------------------------------
    # Health polling
    # ------------------------------------------------------------------

    def start_health_polling(self) -> None:
        self._poll_task = asyncio.create_task(self._poll_loop())
        log.info("health_poll.started", interval=self._poll_interval)

    def stop_health_polling(self) -> None:
        if self._poll_task:
            self._poll_task.cancel()

    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(self._poll_interval)
            await self._check_all()

    async def _check_all(self) -> None:
        async with httpx.AsyncClient(timeout=_HEALTH_TIMEOUT) as client:
            tasks = [
                self._check_one(client, reg)
                for reg in list(self._agents.values())
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_one(self, client: httpx.AsyncClient, reg: AgentRegistration) -> None:
        url = f"{reg.url.rstrip('/')}/.well-known/agent-card.json"
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            was_healthy = reg.healthy
            reg.healthy = True
            reg.last_seen = datetime.now(timezone.utc)
            if not was_healthy:
                log.info("agent.recovered", type_id=reg.type_id)
        except Exception as exc:
            if reg.healthy:
                log.warning("agent.unhealthy", type_id=reg.type_id, error=str(exc))
            reg.healthy = False

    # ------------------------------------------------------------------
    # Graph representation (for GET /graph)
    # ------------------------------------------------------------------

    def to_graph(self) -> dict[str, Any]:
        """Return nodes/edges for the dashboard AgentGraph panel."""
        nodes = []
        for reg in self._agents.values():
            nodes.append({
                "id": reg.type_id,
                "data": {
                    "label": reg.name,
                    "type_id": reg.type_id,
                    "url": reg.url,
                    "healthy": reg.healthy,
                    "task_count": reg.task_count,
                    "last_seen": reg.last_seen.isoformat(),
                },
                "position": {"x": 0, "y": 0},  # dashboard lays out automatically
            })

        # Edges: control_plane → each agent
        edges = [
            {
                "id": f"cp->{reg.type_id}",
                "source": "control_plane",
                "target": reg.type_id,
            }
            for reg in self._agents.values()
        ]

        # Add control_plane node itself
        nodes.insert(0, {
            "id": "control_plane",
            "data": {"label": "Control Plane", "type_id": "control_plane", "healthy": True},
            "position": {"x": 0, "y": 0},
        })

        return {"nodes": nodes, "edges": edges}
