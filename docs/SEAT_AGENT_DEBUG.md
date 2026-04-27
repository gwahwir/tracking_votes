# Seat Agent — Debug Notes

## What you're investigating

The seat agent is running but producing no useful predictions. All 63 rows in the
`seat_predictions` table have `leading_party = NULL`, `confidence = 0`, and
`caveats = ["Assessment failed"]`. There are 309 completed tasks and 54 failed tasks
for the seat agent in the `tasks` table.

The database is running in Docker. The app is started with `docker compose up`.

---

## Current state of the data

```
tasks table (type_id = 'seat_agent'):
  completed : 309
  failed    :  54

seat_predictions table:
  total rows            : 63
  successful predictions:  0   (leading_party is NULL or empty on every row)
  "Assessment failed"   : 63
```

---

## Two distinct bug categories

### Bug 1 — Timezone mismatch in the `store` node (affects completed tasks)

Tasks that reach the `store` node (state = `completed`) still write
`"Assessment failed"` because the INSERT crashes with:

```
asyncpg.exceptions.DataError: invalid input for query argument $8:
datetime.datetime(2026, 4, 21, 6, 29, 33 ... (can't subtract offset-naive
and offset-aware datetimes)

SQL: INSERT INTO seat_predictions (..., created_at, updated_at)
     VALUES ($1::VARCHAR, ..., $8::TIMESTAMP WITHOUT TIME ZONE, ...)
```

The `SeatPrediction` ORM model sets `created_at` / `updated_at` using
`datetime.datetime.utcnow()` (timezone-naive), but the column is declared as
`TIMESTAMP WITH TIME ZONE` (or the DB driver is treating it as such), causing
asyncpg to reject the value.

**Where to look:**
- `agents/base/models.py` — `SeatPrediction` model, `created_at` / `updated_at`
  column definitions and defaults
- `agents/seat_agent/graph.py` lines 303–355 — the `store()` function

**Likely fix:** Change the `datetime.utcnow()` default to `datetime.now(timezone.utc)`
(timezone-aware), or align the column type to `TIMESTAMP WITHOUT TIME ZONE`.

**Evidence:** The LLM call itself succeeds — you can see a fully populated
`seat_prediction` dict in the task's `output_text` (e.g. N.22 correctly predicted BN
with confidence 60 and a complete 6-lens signal breakdown). The crash happens only
during the INSERT.

---

### Bug 2 — Network / connection errors (affects failed tasks)

54 tasks never complete at all. Their `error` fields are:

```
peer closed connection without sending complete message body (incomplete chunked read)
All connection attempts failed
[Errno -5] No address associated with hostname
```

These look like transient network errors between the seat agent and the OpenRouter
API (or the Anthropic fallback), likely during the `assess` node's LLM call.

**Where to look:**
- `agents/base/llm.py` — `_openrouter_call()` and `_anthropic_call()` — the retry
  logic currently retries up to 3 times but only on specific error codes; network
  errors may not be caught
- `agents/seat_agent/graph.py` lines 266–298 — the `assess()` function's try/except

**Likely fix:** Widen the retry logic in `_openrouter_call` to catch connection-level
errors (not just HTTP status codes), or add a retry wrapper around the `assess` node.

---

## Key files

| File | What it does |
|---|---|
| `agents/seat_agent/graph.py` | All 4 graph nodes: `gather_signals`, `load_baseline`, `assess`, `store` |
| `agents/base/models.py` | ORM models including `SeatPrediction` — check `created_at`/`updated_at` |
| `agents/base/llm.py` | `llm_call_with_fallback`, `_openrouter_call` retry logic |
| `agents/seat_agent/executor.py` | Executor wiring the graph together |
| `control_plane/db.py` | `get_session_maker()` used by the store node |

---

## Pipeline context

The seat agent is triggered automatically as part of a cascade:

```
control_plane (every 30 min)
  → news_agent (scrape + LLM filter)
    → scorer_agent (LLM reliability score)
      → analyst_agent (6 parallel LLM lens calls)
        → seat_agent (LLM assessment + store)
```

It receives tasks like `{"constituency_code": "N.22"}` via POST to
`/agents/seat_agent/tasks`. It is not triggered directly by the user.

---

## What a successful prediction looks like

From task `ed3eb7b8` (N.22 — Parit Raja), the LLM correctly produced:

```json
{
  "leading_party": "BN",
  "confidence": 60,
  "signal_breakdown": {
    "political":      {"direction": "BN", "strength": 30, "summary": "..."},
    "demographic":    {"direction": "BN", "strength": 60, "summary": "..."},
    "historical":     {"direction": "BN", "strength": 85, "summary": "..."},
    "strategic":      {"direction": "BN", "strength": 60, "summary": "..."},
    "factcheck":      {"direction": "BN", "strength": 50, "summary": "..."},
    "bridget_welsh":  {"direction": "BN", "strength": 20, "summary": "..."}
  },
  "caveats": []
}
```

The LLM output is correct. It just never made it into the database.

---

## Suggested approach

1. Fix Bug 1 first — it's the blocking issue for all 309 completed tasks. Change the
   timezone handling in the `SeatPrediction` model defaults and confirm the column type
   in the DB matches.
2. Then check Bug 2 — look at what error types the retry logic in `llm.py` catches and
   whether network-level exceptions are included.
3. After fixing, you can re-trigger seat agent tasks manually by POSTing to
   `http://localhost:8000/agents/seat_agent/tasks` with body
   `{"message": "{\"constituency_code\": \"N.22\"}", "metadata": {"constituency_code": "N.22"}}`.
   The control plane is at port 8000.
