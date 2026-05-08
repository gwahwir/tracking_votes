# Control Plane Hygiene — Follow-up Tasks

Two outstanding cleanup items in `control_plane/` identified during a code review on 2026-05-08. Each is independent — work on either, both, or neither.

This file is written for a fresh Claude session that hasn't seen the prior conversation. Read the full task before starting; each option includes pros, cons, and a recommendation, but the user makes the final call.

---

## Task 1 — `/wiki/pages` stub returns hardcoded fake data

### Current state

The endpoint `GET /wiki/pages` at [control_plane/routes.py:528-543](../control_plane/routes.py) returns two hardcoded entries with frozen April 2026 dates:

```python
@router.get("/wiki/pages")
async def get_wiki_pages(request: Request):
    """Return list of wiki pages with metadata."""
    # Placeholder — can be enhanced to read from filesystem or database
    return [
        {"path": "wiki/index.md", "title": "Wiki Index", "updated_at": "2026-04-17T00:00:00Z"},
        {"path": "wiki/schema.md", "title": "Wiki Schema", "updated_at": "2026-04-17T00:00:00Z"}
    ]
```

The actual wiki has ~80+ Markdown files under `wiki/` (concepts, entities/parties, entities/constituencies, entities/people, etc.). The dashboard's WikiModal at [dashboard/src/components/wiki/WikiModal.jsx](../dashboard/src/components/wiki/WikiModal.jsx) calls this endpoint and renders a searchable list. Users see only the two fake entries.

### The problem

The endpoint silently lies. The WikiModal feature looks like it works but shows nothing real. Either fix it or remove the feature — leaving it as a stub is worse than either.

### Options

#### Option A — Implement via wiki_agent proxy (recommended)

`wiki_agent` already mounts `./wiki:/app/wiki` (see `docker-compose.yml`). Have control_plane proxy `GET /wiki/pages` to wiki_agent's URL, which is in the agent registry.

**Steps:**
1. Add a new endpoint to `wiki_agent` (e.g. `GET /pages` on its FastAPI app) that walks `/app/wiki/`, extracts title + mtime per `.md` file, returns JSON.
2. In `control_plane/routes.py`, replace the hardcoded list with a proxy call: `registry.get("wiki_agent")` → fetch from that URL → return the response. Handle 503 if wiki_agent is unhealthy.
3. The WikiModal already expects `[{path, title, updated_at}]` — schema stays the same.

**Pros:** keeps filesystem access in one container (wiki_agent already has it). Doesn't require modifying docker-compose.yml. Single canonical source.

**Cons:** adds a hop. If wiki_agent is down, the modal stops working — worth handling gracefully.

**Implementation hints:**
- Title extraction: first `# heading` line, fall back to filename
- `updated_at`: use `Path.stat().st_mtime`, convert to ISO 8601 with timezone
- Sort by path for stable ordering
- Cap response size to avoid surprises (the wiki currently has ~80 files but could grow)

#### Option B — Remove the feature

Delete:
- `GET /wiki/pages` from [control_plane/routes.py](../control_plane/routes.py)
- `useWikiPages` hook from [dashboard/src/hooks/useApi.js:225-256](../dashboard/src/hooks/useApi.js)
- [dashboard/src/components/wiki/WikiModal.jsx](../dashboard/src/components/wiki/WikiModal.jsx) and the import in [dashboard/src/components/layout/DashboardShell.jsx](../dashboard/src/components/layout/DashboardShell.jsx)
- The button/affordance that opens the WikiModal

**Pros:** ~5 minutes. Removes deception.

**Cons:** loses a useful debugging affordance ("did the wiki agent actually update the Buloh Kasap page?"). Shrinks the product.

#### Option C — Mark as known-broken

Replace the stub with `501 Not Implemented`. WikiModal shows a "feature not implemented" placeholder.

**Pros:** stops lying without committing to either direction.

**Cons:** worst of both worlds. Skip this.

### Recommendation

**Option A**, as long as you have the time (~30 min with testing). The wiki is the system's grounding source — being able to browse it from the dashboard genuinely helps. If you don't have the time, do **Option B** — clean removal beats fake data.

### Verification (Option A)

1. Restart wiki_agent and control_plane after the change.
2. `curl http://localhost:8000/wiki/pages` — should return real entries with current `updated_at` timestamps.
3. Open dashboard at http://localhost:5175, click the wiki affordance, verify the modal lists real pages.
4. Search for "Buloh Kasap" or "DAP" — should match real files.

---

## Task 2 — Schema definitions split between two files

### Current state

PostgreSQL schema is defined in TWO places, which can drift:

**A. [agents/base/models.py](../agents/base/models.py)** — SQLAlchemy ORM models. Used by agents that read/write through SQLAlchemy. Executed by `Base.metadata.create_all()` in [control_plane/db.py:35-40](../control_plane/db.py).

**B. [control_plane/task_store.py:133-180](../control_plane/task_store.py)** — Raw `CREATE TABLE IF NOT EXISTS` SQL strings, plus `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` blocks (added in May 2026 for `seat_predictions.evidence_quality`). Used by `PostgresTaskStore.initialize()`.

The two definitions don't agree. For `seat_predictions` specifically:
- `models.py` declares: `id, constituency_code, leading_party, confidence, signal_breakdown, evidence_quality, caveats, num_articles, num_state_articles, created_at, updated_at`
- `task_store.py` declares only: `id, constituency_code, leading_party, confidence, signal_breakdown, caveats, created_at` plus the ALTER for `evidence_quality`

### Why this works today (accidentally)

SQLAlchemy's `create_all()` runs first (control_plane startup, in `init_database`). Then `task_store.initialize()` runs — but its `CREATE TABLE IF NOT EXISTS` becomes a no-op because the tables already exist. The ALTER blocks DO run, but they're idempotent.

**The trap:** when adding a new column, you have to remember to update both files. The May 2026 evidence_quality migration touched both — easy to miss next time.

**The deeper issue:** `create_all` doesn't add columns to existing tables, doesn't drop columns, doesn't rename. ALTER blocks only ADD COLUMN. Any other schema change is manual SQL.

### Options

#### Option A — Drop asyncpg DDL from task_store.py (recommended)

Delete `_CREATE_TABLES_SQL` from [task_store.py](../control_plane/task_store.py) entirely. Have `PostgresTaskStore.initialize()` skip schema setup — rely on `init_database()` (SQLAlchemy `create_all` + ALTER blocks) to do it.

**Steps:**
1. Move the `ALTER TABLE seat_predictions ADD COLUMN IF NOT EXISTS evidence_quality JSONB` from `task_store.py` into `control_plane/db.py` (it's already there as `evidence_quality JSON`; verify both behave identically — `JSON` and `JSONB` differ in storage and indexing).
2. Delete `_CREATE_TABLES_SQL` and the `await conn.execute(_CREATE_TABLES_SQL)` line from `PostgresTaskStore.initialize()`.
3. Verify: in the codebase, `PostgresTaskStore.initialize()` is only called from `control_plane/server.py:54`, AFTER `init_database()` runs. So removing its DDL doesn't break anything as long as the FastAPI lifespan order is preserved.
4. Test: full restart with empty DB. Verify all tables exist with correct columns.

**Pros:** smallest change that genuinely fixes the dual-source trap. No new dependencies. ~20 minutes of work.

**Cons:** task_store no longer self-bootstraps if used outside the FastAPI lifecycle. Audit the codebase to confirm nothing else calls it standalone — the search to verify is `grep -rn "task_store.initialize\|PostgresTaskStore(.*).initialize" .`

#### Option B — Consolidate to a single schema.sql file

Pull all DDL into one canonical place (versioned SQL or a Python module imported by both). Both `task_store.py` and `db.py` execute the same statements at startup.

**Pros:** explicit single source of truth without framework overhead. Readable.

**Cons:** still no support for DROP/RENAME, data migrations, or version tracking. Cleaner than today but doesn't fix the deeper limitation. Mid-effort (~1 hour).

#### Option C — Adopt Alembic (Phase E in [plans/PHASE_E_POLISH_DEPLOYMENT.md](PHASE_E_POLISH_DEPLOYMENT.md))

Proper migration framework. Versioned migration files, up/down operations, autogeneration from SQLAlchemy, CI-friendly diff checks.

**Pros:** the right answer for production. Single source of truth (SQLAlchemy models). Each schema change is a reviewed file. Supports DROP, RENAME, data migrations, multi-environment.

**Cons:** real setup effort — initialise alembic env, write baseline migration capturing current DB state, retire `create_all` and ALTER blocks, learn `alembic revision` / `upgrade head`. Half a day to a day of work, plus a dependency.

#### Option D — Add a startup self-check (cheap mitigation)

Keep both files. Add a startup check: SQLAlchemy introspects the live DB, compares to ORM models, logs drift.

**Pros:** very cheap. Catches drift early without restructuring.

**Cons:** still relies on humans remembering. Doesn't fix the root cause. Easy to ignore warnings.

### Recommendation

**Option A** — drop the asyncpg DDL. It's the smallest change that genuinely fixes the trap, no new dependencies, and the code being removed is already redundant in practice (create_all runs first and creates everything).

Adopt **Option C (Alembic)** later, when you actually need real migrations — column renames, type changes, data backfills. Right now the schema only grows, so `IF NOT EXISTS` semantics are fine. The trigger for Alembic adoption is the first time you need to *change* schema in an incompatible way.

### Verification (Option A)

1. Wipe local DB volume (`docker compose down postgres -v && docker compose up -d postgres`).
2. Restart control_plane. Watch logs for any schema errors.
3. `docker compose exec postgres psql -U johor -d johor_elections -c "\d seat_predictions"` — verify all columns exist (id, constituency_code, leading_party, confidence, signal_breakdown, evidence_quality, caveats, num_articles, num_state_articles, created_at, updated_at).
4. Run `python scripts/rescore_seats.py --limit 1` to confirm a write/read round-trip works.
5. (Optional) restore a snapshot via `bash data/snapshots/restore_snapshot.sh` and verify queries still work.

### Risks to watch

- `JSON` vs `JSONB` — task_store.py used JSONB, db.py uses JSON. They behave differently for indexing and operators. The `signal_breakdown` and `caveats` columns may already have data; check what column type the live DB actually has (`\d seat_predictions`) and align accordingly.
- Other tables may have similar splits — `articles`, `analyses`. Check the schema in both files for differences before consolidating.

---

## Background context for the new Claude session

The repo is a Johor election monitoring dashboard. Key context:

- Postgres 16 + pgvector running in Docker (port 5434 host, 5432 container).
- Control plane is FastAPI on port 8000, runs SQLAlchemy `create_all` + ALTER blocks at startup.
- Task store can be in-memory (dev) or Postgres (prod). When Postgres, it's `PostgresTaskStore` using asyncpg directly.
- Recent context: in May 2026 a separate effort added `evidence_quality` column to `seat_predictions`. That's when the dual-source trap was rediscovered. See `plans/SEAT_AGENT_PHASE_1_2_NOTES.md`.
- See `README.md` for full architecture overview, including the cascade topology decision in `docs/ADR-001-cascade-topology.md`.

When done, update this file or delete it.
