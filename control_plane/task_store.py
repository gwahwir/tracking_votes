"""Task persistence — in-memory (default) or PostgreSQL backend."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import structlog

log = structlog.get_logger(__name__)


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRecord:
    __slots__ = (
        "id", "type_id", "state", "input_text",
        "output_text", "error", "agent_url",
        "created_at", "updated_at",
    )

    def __init__(
        self,
        type_id: str,
        input_text: str,
        agent_url: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> None:
        self.id: str = task_id or str(uuid.uuid4())
        self.type_id: str = type_id
        self.state: TaskState = TaskState.PENDING
        self.input_text: str = input_text
        self.output_text: Optional[str] = None
        self.error: Optional[str] = None
        self.agent_url: Optional[str] = agent_url
        now = datetime.now(timezone.utc)
        self.created_at: datetime = now
        self.updated_at: datetime = now

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type_id": self.type_id,
            "state": self.state.value,
            "input_text": self.input_text,
            "output_text": self.output_text,
            "error": self.error,
            "agent_url": self.agent_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# In-memory backend
# ---------------------------------------------------------------------------

class InMemoryTaskStore:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}

    async def create(self, record: TaskRecord) -> TaskRecord:
        self._tasks[record.id] = record
        log.debug("task.created", task_id=record.id, type_id=record.type_id)
        return record

    async def get(self, task_id: str) -> Optional[TaskRecord]:
        return self._tasks.get(task_id)

    async def update(
        self,
        task_id: str,
        *,
        state: Optional[TaskState] = None,
        output_text: Optional[str] = None,
        error: Optional[str] = None,
        agent_url: Optional[str] = None,
    ) -> Optional[TaskRecord]:
        record = self._tasks.get(task_id)
        if record is None:
            return None
        if state is not None:
            record.state = state
        if output_text is not None:
            record.output_text = output_text
        if error is not None:
            record.error = error
        if agent_url is not None:
            record.agent_url = agent_url
        record.updated_at = datetime.now(timezone.utc)
        return record

    async def list(self, limit: int = 100) -> list[TaskRecord]:
        tasks = sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    async def initialize(self) -> None:
        pass  # nothing to set up


# ---------------------------------------------------------------------------
# PostgreSQL backend
# ---------------------------------------------------------------------------

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    type_id     TEXT NOT NULL,
    state       TEXT NOT NULL DEFAULT 'pending',
    input_text  TEXT NOT NULL,
    output_text TEXT,
    error       TEXT,
    agent_url   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS articles (
    id               TEXT PRIMARY KEY,
    url              TEXT UNIQUE NOT NULL,
    title            TEXT NOT NULL,
    content          TEXT,
    source           TEXT,
    published_at     TIMESTAMPTZ,
    constituency_ids JSONB NOT NULL DEFAULT '[]',
    reliability_score INT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analyses (
    id                 TEXT PRIMARY KEY,
    article_id         TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    constituency_code  TEXT NOT NULL,
    lens               TEXT NOT NULL,
    direction          TEXT,
    strength           INT,
    summary            TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS seat_predictions (
    id                 TEXT PRIMARY KEY,
    constituency_code  TEXT NOT NULL,
    leading_party      TEXT NOT NULL,
    confidence         INT NOT NULL,
    signal_breakdown   JSONB NOT NULL DEFAULT '{}',
    caveats            JSONB NOT NULL DEFAULT '[]',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


class PostgresTaskStore:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._pool = None  # asyncpg pool, created in initialize()

    async def initialize(self) -> None:
        import asyncpg  # type: ignore

        self._pool = await asyncpg.create_pool(self._database_url, min_size=2, max_size=10)
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_TABLES_SQL)
        log.info("postgres.initialized")

    async def create(self, record: TaskRecord) -> TaskRecord:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tasks (id, type_id, state, input_text, output_text, error, agent_url, created_at, updated_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                """,
                record.id, record.type_id, record.state.value,
                record.input_text, record.output_text, record.error,
                record.agent_url, record.created_at, record.updated_at,
            )
        log.debug("task.created", task_id=record.id, type_id=record.type_id)
        return record

    async def get(self, task_id: str) -> Optional[TaskRecord]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM tasks WHERE id=$1", task_id)
        if row is None:
            return None
        return self._row_to_record(row)

    async def update(
        self,
        task_id: str,
        *,
        state: Optional[TaskState] = None,
        output_text: Optional[str] = None,
        error: Optional[str] = None,
        agent_url: Optional[str] = None,
    ) -> Optional[TaskRecord]:
        updates: list[str] = ["updated_at = NOW()"]
        params: list[Any] = []
        idx = 1

        if state is not None:
            updates.append(f"state = ${idx}")
            params.append(state.value)
            idx += 1
        if output_text is not None:
            updates.append(f"output_text = ${idx}")
            params.append(output_text)
            idx += 1
        if error is not None:
            updates.append(f"error = ${idx}")
            params.append(error)
            idx += 1
        if agent_url is not None:
            updates.append(f"agent_url = ${idx}")
            params.append(agent_url)
            idx += 1

        params.append(task_id)
        sql = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ${idx} RETURNING *"

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, *params)
        if row is None:
            return None
        return self._row_to_record(row)

    async def list(self, limit: int = 100) -> list[TaskRecord]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT $1", limit
            )
        return [self._row_to_record(r) for r in rows]

    @staticmethod
    def _row_to_record(row) -> TaskRecord:
        r = TaskRecord(
            type_id=row["type_id"],
            input_text=row["input_text"],
            agent_url=row["agent_url"],
            task_id=row["id"],
        )
        r.state = TaskState(row["state"])
        r.output_text = row["output_text"]
        r.error = row["error"]
        r.created_at = row["created_at"]
        r.updated_at = row["updated_at"]
        return r


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_task_store(database_url: Optional[str]) -> InMemoryTaskStore | PostgresTaskStore:
    if database_url:
        log.info("task_store.backend", backend="postgres")
        return PostgresTaskStore(database_url)
    log.info("task_store.backend", backend="in_memory")
    return InMemoryTaskStore()
