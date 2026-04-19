# Phase E: Polish & Deployment

## Goal

Harden the system for production use: error handling, rate limiting, authentication, CI/CD, and cloud deployment. Make it reliable enough to run unattended during an election cycle.

**Prerequisite:** Phases A-D should be functionally complete. This phase is about operational readiness, not new features.

---

## Context: What Exists Today

### Infrastructure
- **Docker Compose** (`docker-compose.yml`) defines 9 services: postgres, redis, control_plane, 5 agents, dashboard
- **Single Dockerfile** at project root for all Python services
- **Dashboard Dockerfile** at `dashboard/Dockerfile` for React build
- **No CI/CD pipeline** exists
- **No authentication** — all endpoints are public
- **No rate limiting** on news scrapers or LLM calls
- **No health monitoring** beyond the `/health` endpoint and agent registry health polling (30s in `control_plane/registry.py`)
- **LLM calls** via OpenRouter (primary) and Anthropic (fallback) in `agents/base/llm.py` — no retry logic, no rate limit handling beyond the fallback
- **API base URL** hardcoded to `http://localhost:8000` in `dashboard/src/hooks/useApi.js` line 3

### Known Issues
- News scrapers have no retry logic or exponential backoff
- No request timeout on LLM calls beyond what the SDK provides
- WebSocket connections have no authentication
- Dashboard polls APIs at fixed intervals (30s-60s) even when idle
- No database migrations — uses `create_all` which doesn't handle schema changes
- `.env` file not committed (good) but no `.env.template` exists as a reference

---

## Implementation Steps

### Step 1: Environment configuration

**Create `.env.template`:**

```bash
# LLM Provider (OpenRouter primary)
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-4o

# LLM Provider (Anthropic fallback)
ANTHROPIC_API_KEY=sk-ant-...

# Database
DATABASE_URL=postgresql://elections:elections@postgres:5432/elections

# Redis
REDIS_URL=redis://redis:6379

# Control Plane
CONTROL_PLANE_URL=http://control_plane:8000

# Agent URLs (comma-separated type@url pairs)
AGENT_URLS=news_agent@http://news_agent:8001,scorer_agent@http://scorer_agent:8002,analyst_agent@http://analyst_agent:8003,seat_agent@http://seat_agent:8004,wiki_agent@http://wiki_agent:8005

# Election scope
ACTIVE_SCOPES=johor

# Dashboard
VITE_API_URL=http://localhost:8000

# Authentication (production)
# AUTH_SECRET=...
# AUTH_ENABLED=false

# News API (optional)
# NEWSAPI_KEY=...

# Langfuse tracing (optional)
# LANGFUSE_PUBLIC_KEY=...
# LANGFUSE_SECRET_KEY=...
# LANGFUSE_HOST=...
```

**Update `dashboard/src/hooks/useApi.js` line 3:**

```javascript
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
```

### Step 2: Add retry logic and rate limiting to LLM calls

**Modify `agents/base/llm.py`:**

Add retry with exponential backoff for transient failures:

```python
import time
from functools import wraps

def _retry(max_attempts=3, base_delay=1.0, max_delay=30.0):
    """Decorator for retrying LLM calls with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_error = exc
                    # Don't retry on auth errors
                    error_str = str(exc).lower()
                    if "auth" in error_str or "401" in error_str or "403" in error_str:
                        raise
                    # Exponential backoff
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    log.warning("llm.retry", attempt=attempt + 1, delay=delay, error=str(exc))
                    time.sleep(delay)
            raise last_error
        return wrapper
    return decorator

@_retry(max_attempts=3, base_delay=2.0)
def llm_call(messages, **kwargs):
    # ... existing implementation ...
```

Add a simple in-process rate limiter:

```python
import threading

class _RateLimiter:
    """Simple token-bucket rate limiter for LLM calls."""
    def __init__(self, calls_per_minute=30):
        self._lock = threading.Lock()
        self._timestamps: list[float] = []
        self._limit = calls_per_minute

    def acquire(self):
        with self._lock:
            now = time.time()
            # Remove timestamps older than 60 seconds
            self._timestamps = [t for t in self._timestamps if now - t < 60]
            if len(self._timestamps) >= self._limit:
                sleep_time = 60 - (now - self._timestamps[0])
                if sleep_time > 0:
                    log.info("llm.rate_limited", sleep=sleep_time)
                    time.sleep(sleep_time)
            self._timestamps.append(time.time())

_limiter = _RateLimiter(calls_per_minute=30)

def llm_call(messages, **kwargs):
    _limiter.acquire()
    # ... existing implementation ...
```

### Step 3: Add retry logic to news scrapers

**Modify each scraper** in `agents/news_agent/scrapers/` to handle transient failures:

Create a shared utility `agents/news_agent/scrapers/utils.py`:

```python
"""Shared utilities for news scrapers."""
import time
import httpx
import structlog

log = structlog.get_logger(__name__)

def fetch_with_retry(url: str, max_attempts: int = 3, timeout: float = 15.0) -> httpx.Response:
    """Fetch URL with retry and exponential backoff."""
    last_error = None
    for attempt in range(max_attempts):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.get(url, headers={
                    "User-Agent": "ElectionMonitor/1.0 (research)",
                })
                resp.raise_for_status()
                return resp
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.ConnectError) as exc:
            last_error = exc
            delay = 2 ** attempt
            log.warning("scraper.retry", url=url, attempt=attempt + 1, delay=delay, error=str(exc))
            time.sleep(delay)
    raise last_error
```

### Step 4: Add basic authentication

**Create `control_plane/auth.py`:**

```python
"""Simple API key authentication middleware.

When AUTH_ENABLED=true, all endpoints except /health require an API key
in the Authorization header: `Bearer <key>`.

WebSocket connections pass the key as a query parameter: ?token=<key>
"""
import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.enabled = os.environ.get("AUTH_ENABLED", "false").lower() == "true"
        self.secret = os.environ.get("AUTH_SECRET", "")

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        # Skip auth for health check and CORS preflight
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Check Authorization header
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            if token == self.secret:
                return await call_next(request)

        # Check query parameter for WebSocket
        token = request.query_params.get("token")
        if token == self.secret:
            return await call_next(request)

        raise HTTPException(status_code=401, detail="Unauthorized")
```

**Add to `control_plane/server.py`:**

```python
from .auth import AuthMiddleware
app.add_middleware(AuthMiddleware)
```

**Update dashboard** to include auth token in requests:

```javascript
const API_TOKEN = import.meta.env.VITE_API_TOKEN || ''

// In each fetch call:
const headers = { 'Content-Type': 'application/json' }
if (API_TOKEN) headers['Authorization'] = `Bearer ${API_TOKEN}`

// For WebSocket:
const ws = new WebSocket(`ws://...?token=${API_TOKEN}`)
```

### Step 5: Add database migrations with Alembic

**Install and initialize Alembic:**

```bash
pip install alembic
cd /Users/wil/tracking_votes
alembic init alembic
```

**Configure `alembic/env.py`** to use the existing SQLAlchemy models:

```python
from agents.base.models import Base
target_metadata = Base.metadata
```

**Create initial migration:**

```bash
alembic revision --autogenerate -m "Initial schema"
```

**Add to `requirements.txt`:**

```
alembic>=1.13
```

**Update `control_plane/server.py`** startup to run migrations instead of `create_all`:

```python
# Replace:
# await conn.run_sync(Base.metadata.create_all)
# With:
from alembic.config import Config
from alembic import command
alembic_cfg = Config("alembic.ini")
command.upgrade(alembic_cfg, "head")
```

### Step 6: Add structured error handling

**Create `control_plane/errors.py`:**

```python
"""Centralized error handling for the control plane."""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

log = structlog.get_logger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            log.error("unhandled_error",
                      path=request.url.path,
                      method=request.method,
                      error=str(exc),
                      exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "type": type(exc).__name__},
            )
```

### Step 7: Add health check dashboard endpoint

**Create a `/health/detailed` endpoint** in `control_plane/routes.py`:

```python
@router.get("/health/detailed")
async def detailed_health(request: Request):
    """Detailed health check including all agents, DB, and Redis status."""
    registry = request.app.state.registry
    task_store = request.app.state.task_store
    broker = request.app.state.broker

    agents = registry.get_all()
    healthy_agents = [a for a in agents if a.is_healthy]

    db_ok = False
    try:
        if hasattr(task_store, '_pool') and task_store._pool:
            async with task_store._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_ok = True
    except Exception:
        pass

    redis_ok = False
    try:
        if hasattr(broker, '_redis') and broker._redis:
            await broker._redis.ping()
            redis_ok = True
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
```

### Step 8: Production Docker configuration

**Create `docker-compose.prod.yml`:**

```yaml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    restart: always
    environment:
      POSTGRES_USER: ${DB_USER:-elections}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME:-elections}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-elections}"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 512M

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD:-}
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 128M

  control_plane:
    build:
      context: .
      dockerfile: Dockerfile
    command: uvicorn control_plane.server:app --host 0.0.0.0 --port 8000 --workers 2
    env_file: .env
    environment:
      AUTH_ENABLED: "true"
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: always
    deploy:
      resources:
        limits:
          memory: 512M

  # ... agents with memory limits and restart: always ...

  dashboard:
    build:
      context: ./dashboard
      dockerfile: Dockerfile
      args:
        VITE_API_URL: ${VITE_API_URL}
        VITE_API_TOKEN: ${VITE_API_TOKEN}
    ports:
      - "80:5173"
    restart: always
    deploy:
      resources:
        limits:
          memory: 128M

  # Nginx reverse proxy (optional, for HTTPS)
  # nginx:
  #   image: nginx:alpine
  #   ports:
  #     - "443:443"
  #   volumes:
  #     - ./nginx.conf:/etc/nginx/nginx.conf
  #     - ./certs:/etc/nginx/certs

volumes:
  postgres_data:
```

### Step 9: Add CI/CD with GitHub Actions

**Create `.github/workflows/ci.yml`:**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check .

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_elections
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-asyncio
      - run: pytest tests/
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_elections

  build-dashboard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - working-directory: dashboard
        run: npm ci
      - working-directory: dashboard
        run: npm run build

  docker:
    runs-on: ubuntu-latest
    needs: [lint, test, build-dashboard]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: false  # Set to true when you have a registry configured
          tags: election-monitor:latest
```

### Step 10: Add logging and observability

**Enhance structured logging** across all services:

```python
# In control_plane/log.py — add request correlation IDs
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        structlog.contextvars.unbind_contextvars("request_id")
        return response
```

**Add optional Langfuse tracing** (already stubbed in `agents/base/tracing.py`) — enable via environment variables for production LLM call monitoring.

### Step 11: Add a scheduled news scraping cron

Instead of relying on manual "Refresh" clicks, add a periodic news scraping job.

**Option A — Use a simple asyncio task in the control plane:**

```python
# In control_plane/server.py lifespan:
async def _periodic_scrape():
    """Auto-scrape news every 30 minutes."""
    import httpx
    while True:
        await asyncio.sleep(1800)  # 30 minutes
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    "http://localhost:8000/agents/news_agent/tasks",
                    json={"message": "Periodic scrape", "metadata": {"trigger": "cron"}},
                )
                log.info("cron.scrape_dispatched")
        except Exception as exc:
            log.warning("cron.scrape_error", error=str(exc))

# In lifespan startup:
asyncio.create_task(_periodic_scrape())
```

**Option B — External cron** (more robust for production):

```bash
# crontab entry:
*/30 * * * * curl -s -X POST http://localhost:8000/agents/news_agent/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_SECRET" \
  -d '{"message": "Periodic scrape", "metadata": {"trigger": "cron"}}'
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `.env.template` | Environment variable reference |
| `control_plane/auth.py` | API key authentication middleware |
| `control_plane/errors.py` | Centralized error handling |
| `agents/news_agent/scrapers/utils.py` | Shared retry/backoff utilities |
| `docker-compose.prod.yml` | Production Docker configuration |
| `.github/workflows/ci.yml` | CI/CD pipeline |
| `alembic/` | Database migration directory (via `alembic init`) |

## Files to Modify

| File | Change |
|------|--------|
| `agents/base/llm.py` | Add retry decorator, rate limiter |
| `agents/news_agent/scrapers/*.py` | Use `fetch_with_retry` from utils |
| `control_plane/server.py` | Add AuthMiddleware, ErrorHandlerMiddleware, CorrelationIDMiddleware, periodic scrape task |
| `control_plane/routes.py` | Add `/health/detailed` endpoint |
| `dashboard/src/hooks/useApi.js` | Use `VITE_API_URL` env var, add auth headers |
| `requirements.txt` | Add `alembic>=1.13` |
| `docker-compose.yml` | Reference `.env` for all secrets, add memory limits |

---

## Verification

1. **Auth:** With `AUTH_ENABLED=true`, unauthenticated requests to `/agents` return 401, `/health` returns 200
2. **Retry:** Simulate a transient LLM failure (e.g., temporarily invalid API key) — verify retry kicks in and succeeds on fallback
3. **Rate limiting:** Fire 50 LLM calls rapidly — verify the rate limiter throttles to 30/min
4. **Scraper retry:** Block a scraper URL temporarily — verify it retries 3 times with backoff
5. **Health:** `GET /health/detailed` returns status of all agents, DB, and Redis
6. **CI:** Push to GitHub — verify lint, test, and build jobs pass
7. **Docker prod:** `docker-compose -f docker-compose.prod.yml up` — verify all services start with memory limits
8. **Periodic scrape:** Wait 30 minutes — verify a news_agent task is auto-dispatched
9. **Migrations:** Run `alembic upgrade head` — verify schema is created correctly
10. **Dashboard:** `VITE_API_URL` set to production URL — verify dashboard connects to correct backend
