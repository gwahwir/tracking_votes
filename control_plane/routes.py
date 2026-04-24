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

    # Debounce seat_agent: skip if same constituency was dispatched < 5 min ago
    if type_id == "seat_agent":
        constituency_code = body.metadata.get("constituency_code")
        if constituency_code and hasattr(task_store, "find_recent"):
            recent = await task_store.find_recent(
                type_id=type_id,
                metadata_key="constituency_code",
                metadata_value=constituency_code,
                within_seconds=300,
            )
            if recent:
                log.info("task.deduplicated", task_id=recent.id, constituency_code=constituency_code)
                return {"task_id": recent.id, "state": recent.state.value, "deduplicated": True}

    task_id = str(uuid.uuid4())
    record = TaskRecord(type_id=type_id, input_text=body.message, agent_url=agent.url, task_id=task_id, metadata=body.metadata)
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
            SELECT id, url, title, source, scraped_at, constituency_ids, reliability_score, created_at
            FROM articles
            {where}
            ORDER BY scraped_at DESC NULLS LAST
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
# Database endpoints — articles, analyses, seat predictions
# ---------------------------------------------------------------------------

@router.get("/articles")
async def get_articles(request: Request, limit: int = 100, offset: int = 0, constituency: str | None = None):
    """Return all articles from the database, optionally filtered by constituency code."""
    task_store = request.app.state.task_store

    if not hasattr(task_store, "_pool") or task_store._pool is None:
        return []

    try:
        where = ""
        params: list = [limit, offset]
        if constituency:
            where = "WHERE constituency_ids @> $3::jsonb"
            params.append(json.dumps([constituency]))

        sql = f"""
            SELECT id, url, title, source, content, constituency_ids, reliability_score, created_at, scraped_at
            FROM articles
            {where}
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
        """
        async with task_store._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        return [dict(r) for r in rows]
    except Exception as exc:
        log.error("articles.fetch_error", error=str(exc))
        return []


@router.get("/analyses")
async def get_analyses(request: Request, article_id: str | None = None, limit: int = 100):
    """Return analyses from the database, optionally filtered by article_id."""
    task_store = request.app.state.task_store

    if not hasattr(task_store, "_pool") or task_store._pool is None:
        return []

    try:
        where = ""
        params: list = []
        if article_id:
            where = "WHERE article_id = $1"
            params = [article_id]

        limit_ph = f"${len(params) + 1}"
        sql = f"""
            SELECT id, article_id, lens_name, direction, strength, summary, full_result, created_at, updated_at
            FROM analyses
            {where}
            ORDER BY created_at DESC
            LIMIT {limit_ph}
        """
        async with task_store._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params, limit)
        return [dict(r) for r in rows]
    except Exception as exc:
        log.error("analyses.fetch_error", error=str(exc))
        return []


@router.get("/seat-predictions")
async def get_seat_predictions(request: Request, limit: int = 100):
    """Return all seat predictions from the database."""
    task_store = request.app.state.task_store

    if not hasattr(task_store, "_pool") or task_store._pool is None:
        return []

    try:
        sql = """
            SELECT id, constituency_code, leading_party, confidence, signal_breakdown,
                   caveats, num_articles, created_at, updated_at
            FROM seat_predictions
            ORDER BY updated_at DESC
            LIMIT $1
        """
        async with task_store._pool.acquire() as conn:
            rows = await conn.fetch(sql, limit)
        return [dict(r) for r in rows]
    except Exception as exc:
        log.error("seat_predictions.fetch_error", error=str(exc))
        return []


@router.delete("/seat-predictions")
async def delete_seat_predictions(request: Request):
    """Delete all seat predictions (used to reset before calibration runs)."""
    task_store = request.app.state.task_store
    if not hasattr(task_store, "_pool") or task_store._pool is None:
        return {"deleted": 0}
    try:
        async with task_store._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM seat_predictions")
        deleted = int(result.split()[-1])
        log.info("seat_predictions.cleared", deleted=deleted)
        return {"deleted": deleted}
    except Exception as exc:
        log.error("seat_predictions.clear_error", error=str(exc))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/seat-predictions/{constituency_code}")
async def get_seat_prediction(request: Request, constituency_code: str):
    """Return a single seat prediction for a constituency."""
    task_store = request.app.state.task_store

    if not hasattr(task_store, "_pool") or task_store._pool is None:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        sql = """
            SELECT id, constituency_code, leading_party, confidence, signal_breakdown,
                   caveats, num_articles, created_at, updated_at
            FROM seat_predictions
            WHERE constituency_code = $1
            ORDER BY updated_at DESC
            LIMIT 1
        """
        async with task_store._pool.acquire() as conn:
            row = await conn.fetchrow(sql, constituency_code)

        if not row:
            raise HTTPException(status_code=404, detail="Prediction not found")
        return dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        log.error("seat_prediction.fetch_error", error=str(exc), constituency_code=constituency_code)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/historical/{constituency_code}")
async def get_historical(request: Request, constituency_code: str):
    """Return historical election results for a constituency."""
    task_store = request.app.state.task_store

    if not hasattr(task_store, "_pool") or task_store._pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        sql = """
            SELECT constituency_code, seat_type, seat_name, election_year,
                   winner_name, winner_party, winner_coalition, winner_votes,
                   margin, margin_pct, turnout_pct, total_voters, total_votes_cast,
                   num_candidates, candidates
            FROM historical_results
            WHERE constituency_code = $1
            ORDER BY election_year DESC
        """
        async with task_store._pool.acquire() as conn:
            rows = await conn.fetch(sql, constituency_code)
        if not rows:
            raise HTTPException(status_code=404, detail=f"No historical data for {constituency_code}")
        return [dict(r) for r in rows]
    except HTTPException:
        raise
    except Exception as exc:
        log.error("historical.fetch_error", error=str(exc), constituency_code=constituency_code)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/historical")
async def get_all_historical(request: Request, seat_type: str | None = None, year: int | None = None):
    """Return historical results, optionally filtered by seat_type and/or year."""
    task_store = request.app.state.task_store

    if not hasattr(task_store, "_pool") or task_store._pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        conditions = []
        params: list = []
        if seat_type:
            params.append(seat_type)
            conditions.append(f"seat_type = ${len(params)}")
        if year:
            params.append(year)
            conditions.append(f"election_year = ${len(params)}")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT constituency_code, seat_type, seat_name, election_year,
                   winner_name, winner_party, winner_coalition, winner_votes,
                   margin, margin_pct, turnout_pct, total_voters, total_votes_cast,
                   num_candidates, candidates
            FROM historical_results
            {where}
            ORDER BY constituency_code, election_year DESC
        """
        async with task_store._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        return [dict(r) for r in rows]
    except Exception as exc:
        log.error("historical.fetch_all_error", error=str(exc))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/demographics/{constituency_code}")
async def get_demographics(request: Request, constituency_code: str):
    """Return demographic profile for a constituency."""
    task_store = request.app.state.task_store

    if not hasattr(task_store, "_pool") or task_store._pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        sql = """
            SELECT constituency_code, seat_name, state,
                   malay_pct, chinese_pct, indian_pct, others_pct,
                   urban_rural, region
            FROM constituency_demographics
            WHERE constituency_code = $1
        """
        async with task_store._pool.acquire() as conn:
            row = await conn.fetchrow(sql, constituency_code)
        if not row:
            raise HTTPException(status_code=404, detail=f"No demographics for {constituency_code}")
        return dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        log.error("demographics.fetch_error", error=str(exc), constituency_code=constituency_code)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/wiki/pages")
async def get_wiki_pages(request: Request):
    """Return list of wiki pages with metadata."""
    # Placeholder — can be enhanced to read from filesystem or database
    return [
        {
            "path": "wiki/index.md",
            "title": "Wiki Index",
            "updated_at": "2026-04-17T00:00:00Z"
        },
        {
            "path": "wiki/schema.md",
            "title": "Wiki Schema",
            "updated_at": "2026-04-17T00:00:00Z"
        }
    ]


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/detailed")
async def health_detailed(request: Request):
    """Health check including all agents, DB, and Redis."""
    registry = request.app.state.registry
    task_store = request.app.state.task_store
    broker = request.app.state.broker

    agents = registry.get_all()
    healthy_agents = [a for a in agents if a.is_healthy]

    db_ok = False
    try:
        session_maker = request.app.state.settings.database_url and task_store._session_maker if hasattr(task_store, "_session_maker") else None
        if session_maker:
            async with session_maker() as session:
                await session.execute(__import__("sqlalchemy").text("SELECT 1"))
            db_ok = True
        elif task_store is not None:
            db_ok = True  # in-memory store — no DB to check
    except Exception:
        pass

    redis_ok = False
    try:
        if hasattr(broker, "_redis") and broker._redis:
            await broker._redis.ping()
            redis_ok = True
        elif not request.app.state.settings.redis_url:
            redis_ok = True  # Redis not configured — not required
    except Exception:
        pass

    all_ok = db_ok and redis_ok and len(healthy_agents) == len(agents)

    return {
        "status": "ok" if all_ok else "degraded",
        "database": "ok" if db_ok else "down",
        "redis": "ok" if redis_ok else "down",
        "agents": {
            "total": len(agents),
            "healthy": len(healthy_agents),
            "unhealthy": [a.name for a in agents if not a.is_healthy],
        },
    }
