"""build_a2a_app() — mounts a LangGraphA2AExecutor onto a FastAPI app.

Every agent calls this factory in its own server.py:

    from agents.base.server import build_a2a_app
    from .executor import MyAgentExecutor

    app = build_a2a_app(MyAgentExecutor())
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .registration import register_with_control_plane

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# A2A request models
# ---------------------------------------------------------------------------

class A2AMessage(BaseModel):
    role: str
    parts: list[dict[str, Any]]


class A2ATaskParams(BaseModel):
    id: str
    message: A2AMessage
    metadata: dict[str, Any] = {}


class A2ARequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    method: str
    params: A2ATaskParams


class A2ACancelParams(BaseModel):
    id: str


class A2ACancelRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    method: str
    params: A2ACancelParams


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_a2a_app(executor, lifespan_override=None) -> FastAPI:
    """Create a FastAPI app that wraps *executor* with the A2A protocol."""

    # Active task_id → asyncio.Task map for cancellation
    _active: dict[str, asyncio.Task] = {}

    @asynccontextmanager
    async def _default_lifespan(app: FastAPI):
        await register_with_control_plane(executor.agent_card())
        log.info("agent.started", type_id=executor.AGENT_TYPE_ID)
        yield
        log.info("agent.stopped", type_id=executor.AGENT_TYPE_ID)

    app = FastAPI(
        title=executor.AGENT_NAME,
        version="0.1.0",
        lifespan=lifespan_override or _default_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # /.well-known/agent-card.json
    # ------------------------------------------------------------------

    @app.get("/.well-known/agent-card.json")
    async def agent_card():
        return executor.agent_card()

    # ------------------------------------------------------------------
    # POST /tasks/send  (A2A dispatch — SSE streaming response)
    # ------------------------------------------------------------------

    @app.post("/tasks/send")
    async def tasks_send(body: A2ARequest):
        task_id = body.params.id
        text = _extract_text(body.params.message)
        meta = body.params.metadata

        # Create a fresh executor instance per task so state is isolated
        from copy import deepcopy
        task_executor = deepcopy(executor)

        async def _generate():
            try:
                async for chunk in task_executor.execute(task_id, text, meta):
                    yield chunk
            finally:
                _active.pop(task_id, None)

        # Store executor reference for cancellation support
        _active[task_id] = task_executor

        return StreamingResponse(
            _generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # ------------------------------------------------------------------
    # POST /tasks/cancel
    # ------------------------------------------------------------------

    @app.post("/tasks/cancel")
    async def tasks_cancel(body: A2ACancelRequest):
        task_id = body.params.id
        task_executor = _active.get(task_id)
        if task_executor is None:
            raise HTTPException(status_code=404, detail="Task not found or already complete")
        task_executor.cancel()
        _active.pop(task_id, None)
        log.info("task.cancelled", task_id=task_id)
        return {"jsonrpc": "2.0", "id": task_id, "result": {"status": "cancelled"}}

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @app.get("/health")
    async def health():
        return {"status": "ok", "type_id": executor.AGENT_TYPE_ID}

    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_text(message: A2AMessage) -> str:
    for part in message.parts:
        if part.get("type") == "text":
            return part["text"]
    return ""


