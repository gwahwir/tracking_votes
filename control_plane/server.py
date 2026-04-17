"""FastAPI app factory — wires together all control-plane components."""
from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .a2a_client import A2AClient
from .config import load_settings
from .db import close_database, init_database
from .log import CorrelationIdMiddleware, configure_logging
from .pubsub import create_broker
from .registry import AgentRegistry
from .routes import router
from .task_store import create_task_store

log = structlog.get_logger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Start-up and shut-down lifecycle."""
    settings = app.state.settings

    # Initialise database (if configured)
    if settings.database_url:
        await init_database(settings.database_url)

    # Initialise task store (may run DB migrations)
    await app.state.task_store.initialize()

    # Initialise pub/sub broker (may connect to Redis)
    await app.state.broker.initialize()

    # Pre-register agents listed in AGENT_URLS env var (optional boot-time wiring)
    for ep in settings.agents:
        app.state.registry.register(
            {"name": ep.name, "type_id": ep.name, "url": ep.url, "capabilities": {}}
        )

    # Start health polling
    app.state.registry.start_health_polling()

    log.info("control_plane.started", port=settings.port)
    yield

    # Shutdown
    app.state.registry.stop_health_polling()
    await app.state.a2a_client.close()
    await app.state.broker.close()
    if settings.database_url:
        await close_database()
    log.info("control_plane.stopped")


def create_app() -> FastAPI:
    settings = load_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Johor Election Monitor — Control Plane",
        version="0.1.0",
        lifespan=_lifespan,
    )

    # ---- Shared state -------------------------------------------------------
    app.state.settings = settings
    app.state.task_store = create_task_store(settings.database_url)
    app.state.broker = create_broker(settings.redis_url)
    app.state.registry = AgentRegistry(poll_interval=settings.health_poll_interval)
    app.state.a2a_client = A2AClient()

    # ---- Middleware ---------------------------------------------------------
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],       # tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Routes -------------------------------------------------------------
    app.include_router(router)

    return app


# Allow `uvicorn control_plane.server:app`
app = create_app()
