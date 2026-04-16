"""All REST and WebSocket endpoints for the control plane."""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .a2a_client import parse_sse_event
from .task_store import TaskRecord, TaskState

log = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    name: str
    type_id: str
    url: str
    capabilities: dict[str, Any] = {}


class DispatchRequest(BaseModel):
    message: str
    metadata: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Agent registration + graph
# ---------------------------------------------------------------------------

@router.post("/register", status_code=201)
async def register_agent(body: RegisterRequest, request: Request):
    registry = request.app.state.registry
    reg = registry.register(body.model_dump())
    return reg.to_dict()


@router.get("/agents")
async def list_agents(request: Request):
    registry = request.app.state.registry
    return [a.to_dict() for a in registry.get_all()]


@router.get("/graph")
async def get_graph(request: Request):
    registry = request.app.state.registry
    return registry.to_graph()


# ---------------------------------------------------------------------------
# Task dispatch
# ---------------------------------------------------------------------------

@router.post("/agents/{type_id}/tasks", status_code=202)
async def dispatch_task(type_id: str, body: DispatchRequest, request: Request):
    registry = request.app.state.registry
    task_store = request.app.state.task_store
    broker = request.app.state.broker
    a2a = request.app.state.a2a_client

    agent = registry.pick(type_id)
    if agent is None:
        raise HTTPException(status_code=503, detail=f"No healthy agent of type '{type_id}'")

    task_id = str(uuid.uuid4())
    record = TaskRecord(type_id=type_id, input_text=body.message, agent_url=agent.url, task_id=task_id)
    await task_store.create(record)
    registry.increment(type_id)

    # Run the streaming dispatch in the background so the HTTP response returns immediately
    asyncio.create_task(
        _stream_task(a2a, broker, task_store, registry, agent.url, task_id, body.message, body.metadata, type_id)
    )

    log.info("task.dispatched", task_id=task_id, type_id=type_id, agent_url=agent.url)
    return {"task_id": task_id, "state": TaskState.PENDING.value}


async def _stream_task(
    a2a, broker, task_store, registry,
    agent_url: str, task_id: str, message: str, metadata: dict, type_id: str,
) -> None:
    """Background coroutine: stream A2A response, fan-out via pubsub, update task store."""
    output_parts: list[str] = []
    try:
        await task_store.update(task_id, state=TaskState.RUNNING)
        await broker.publish(task_id, {"type": "state", "state": TaskState.RUNNING.value})

        async for raw_line in a2a.dispatch(agent_url, task_id, message, metadata):
            event = parse_sse_event(raw_line)
            if event is None:
                continue

            if event.get("type") == "done":
                break

            # Broadcast every event to WebSocket subscribers
            await broker.publish(task_id, event)

            # Collect NODE_OUTPUT lines into final output
            content = event.get("content", "")
            if content:
                output_parts.append(content)

        final_output = "".join(output_parts)
        await task_store.update(task_id, state=TaskState.COMPLETED, output_text=final_output)
        await broker.publish(task_id, {"type": "state", "state": TaskState.COMPLETED.value})
        log.info("task.completed", task_id=task_id)

    except Exception as exc:
        log.error("task.failed", task_id=task_id, error=str(exc))
        await task_store.update(task_id, state=TaskState.FAILED, error=str(exc))
        await broker.publish(task_id, {"type": "state", "state": TaskState.FAILED.value, "error": str(exc)})
    finally:
        registry.decrement(type_id)


# ---------------------------------------------------------------------------
# Task management
# ---------------------------------------------------------------------------

@router.get("/tasks")
async def list_tasks(request: Request, limit: int = 50):
    task_store = request.app.state.task_store
    tasks = await task_store.list(limit=limit)
    return [t.to_dict() for t in tasks]


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, request: Request):
    task_store = request.app.state.task_store
    record = await task_store.get(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return record.to_dict()


@router.delete("/tasks/{task_id}", status_code=200)
async def cancel_task(task_id: str, request: Request):
    task_store = request.app.state.task_store
    a2a = request.app.state.a2a_client
    broker = request.app.state.broker

    record = await task_store.get(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if record.state not in (TaskState.PENDING, TaskState.RUNNING):
        raise HTTPException(status_code=409, detail=f"Task is already {record.state.value}")

    if record.agent_url:
        try:
            await a2a.cancel(record.agent_url, task_id)
        except Exception as exc:
            log.warning("cancel.agent_error", task_id=task_id, error=str(exc))

    await task_store.update(task_id, state=TaskState.CANCELLED)
    await broker.publish(task_id, {"type": "state", "state": TaskState.CANCELLED.value})
    log.info("task.cancelled", task_id=task_id)
    return {"task_id": task_id, "state": TaskState.CANCELLED.value}


# ---------------------------------------------------------------------------
# News articles (proxied from DB for the dashboard)
# ---------------------------------------------------------------------------

@router.get("/api/news")
async def get_news(request: Request, limit: int = 50, constituency: str | None = None):
    """Return articles from the DB. Falls back to empty list if DB unavailable."""
    task_store = request.app.state.task_store

    # Only PostgresTaskStore has a pool — gracefully degrade in-memory mode
    if not hasattr(task_store, "_pool") or task_store._pool is None:
        return []

    try:
        where = ""
        params: list = [limit]
        if constituency:
            where = "WHERE constituency_ids @> $2::jsonb"
            params.append(json.dumps([constituency]))

        sql = f"""
            SELECT id, url, title, source, published_at, constituency_ids, reliability_score, created_at
            FROM articles
            {where}
            ORDER BY published_at DESC NULLS LAST
            LIMIT $1
        """
        async with task_store._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        return [dict(r) for r in rows]
    except Exception as exc:
        log.error("news.fetch_error", error=str(exc))
        return []


# ---------------------------------------------------------------------------
# WebSocket — real-time task updates
# ---------------------------------------------------------------------------

@router.websocket("/ws/tasks/{task_id}")
async def ws_task(websocket: WebSocket, task_id: str):
    broker = websocket.app.state.broker
    task_store = websocket.app.state.task_store

    await websocket.accept()
    log.info("ws.connected", task_id=task_id)

    # Send current task state immediately on connect
    record = await task_store.get(task_id)
    if record:
        await websocket.send_json({"type": "state", "state": record.state.value, "task": record.to_dict()})

    try:
        async for message in broker.subscribe(task_id):
            await websocket.send_text(message)
            # Auto-close connection once terminal state is reached
            try:
                event = json.loads(message)
                if event.get("type") == "state" and event.get("state") in (
                    TaskState.COMPLETED.value,
                    TaskState.FAILED.value,
                    TaskState.CANCELLED.value,
                ):
                    break
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        log.info("ws.disconnected", task_id=task_id)
    finally:
        await websocket.close()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@router.get("/health")
async def health():
    return {"status": "ok"}
