"""Settings loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class AgentEndpoint:
    name: str
    url: str


@dataclass
class Settings:
    host: str = "0.0.0.0"
    port: int = 8000
    agents: list[AgentEndpoint] = field(default_factory=list)
    health_poll_interval: int = 30  # seconds
    database_url: str | None = None
    redis_url: str | None = None
    log_level: str = "INFO"
    control_plane_url: str = "http://localhost:8000"


def load_settings() -> Settings:
    """Parse env vars into a Settings object."""
    agents: list[AgentEndpoint] = []

    # AGENT_URLS format: "name@http://host:port,name2@http://host:port2"
    raw = os.environ.get("AGENT_URLS", "")
    for entry in raw.split(","):
        entry = entry.strip()
        if "@" in entry:
            name, url = entry.split("@", 1)
            agents.append(AgentEndpoint(name=name.strip(), url=url.strip()))

    return Settings(
        host=os.environ.get("CONTROL_PLANE_HOST", "0.0.0.0"),
        port=int(os.environ.get("CONTROL_PLANE_PORT", "8000")),
        agents=agents,
        health_poll_interval=int(os.environ.get("HEALTH_POLL_INTERVAL", "30")),
        database_url=os.environ.get("DATABASE_URL"),
        redis_url=os.environ.get("REDIS_URL"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        control_plane_url=os.environ.get("CONTROL_PLANE_URL", "http://localhost:8000"),
    )
