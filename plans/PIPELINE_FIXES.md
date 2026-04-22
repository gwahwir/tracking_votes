# Pipeline Fixes — Handoff Note

**Context:** The full stack is running via Docker Compose with remapped ports (800x → 900x). The pipeline ran but stalled at the analyst stage. This note captures the exact issues and fixes needed to get a full end-to-end run.

---

## Current State (as of 2026-04-22)

| Stage | Status |
|---|---|
| News Agent | Working — 9 articles in DB |
| Wiki Agent | Working — 18 pages ingested |
| Scorer Agent | Partial — 3/9 articles scored, all returned 0 (parse error) |
| Analyst Agent | Failing — crashes at `red_team`/`aggregate`/`final_synthesis` nodes |
| Seat Predictions | Never triggered |

---

## Issue 1 — Anthropic fallback key is a placeholder

**File:** `.env`  
**Problem:** `ANTHROPIC_API_KEY=sk-ant-...` is not a real key. The LLM code (`agents/base/llm.py`) tries OpenRouter first, then falls back to Anthropic on failure. When OpenRouter hits a rate limit or quota mid-task, the fallback to Anthropic crashes with 401, killing the analyst task.  
**Fix:** Either:
- Add a real Anthropic key to `.env`, OR
- Change `OPENAI_MODEL` in `.env` to a cheaper model like `openai/gpt-4o-mini` so OpenRouter doesn't exhaust mid-task

After updating `.env`, rebuild and restart the agents:
```bash
docker compose up -d --force-recreate scorer_agent analyst_agent seat_agent
```

---

## Issue 2 — Scorer returning score=0 (JSON parse error)

**File:** `agents/scorer_agent/graph.py` (look for `scorer.parse_error` log)  
**Problem:** The scorer LLM (`openai/gpt-oss-120b`) is returning malformed JSON. The scorer silently defaults to score=0 on parse failure. Score=0 means articles fail the `score_above_40` chain condition and analyst tasks still get dispatched (threshold is actually 40, not 0) but with bad signal quality.  
**Fix:** Look at the prompt in `agents/scorer_agent/graph.py` and add stricter JSON output instructions, or switch the scorer to use `OPENAI_SMALL_MODEL` (`openai/gpt-4o-mini`) which follows JSON formatting more reliably.

---

## Issue 3 — Constituency tagging not working (most articles get `[]`)

**File:** `agents/news_agent/graph.py` (the `tag` node)  
**Problem:** 8/9 articles came back with `constituency_ids: []`. Only one article got tagged with `["P.160"]`. The tagger LLM is not matching articles to Johor constituency codes.  
**Impact:** The seat agent never auto-triggers because `_chain_to_seat_node` in `agents/analyst_agent/graph.py` skips dispatch when `constituency_codes` is empty.  
**Fix options:**
- Improve the tagging prompt in `agents/news_agent/graph.py` to be more aggressive about inferring Johor relevance
- OR manually trigger seat predictions for all known Johor constituencies after analyst completes:
  ```bash
  # Trigger seat agent for all Johor state seats
  for code in N01 N02 N03 N04 N05 N06 N07 N08 N09 N10; do
    curl -s -X POST http://localhost:9000/agents/seat_agent/tasks \
      -H "Content-Type: application/json" \
      -d "{\"message\": \"{\\\"constituency_code\\\": \\\"$code\\\"}\", \"metadata\": {\"constituency_code\": \"$code\"}}"
    echo "queued $code"
  done
  ```

---

## Issue 4 — Schema mismatches already fixed (for reference)

These were fixed during this session and are already in the code:

| File | Fix |
|---|---|
| `agents/news_agent/graph.py:205` | `published_at` → `scraped_at` in INSERT |
| `agents/analyst_agent/graph.py:357` | Removed `constituency_code` column from analyses INSERT, `lens` → `lens_name` |
| `control_plane/routes.py:208,279` | `published_at` → `scraped_at` in both `/api/news` and `/articles` queries |
| `dashboard/.dockerignore` | Added to fix `vite: Permission denied` on Docker build |
| `docker-compose.yml` | Remapped all host ports to 900x/6380/5175 to avoid conflict with `mission-control` stack |

---

## How to kick off a clean run (once API keys are sorted)

```bash
# 1. Update .env with working keys
# 2. Restart agents
docker compose up -d --force-recreate scorer_agent analyst_agent seat_agent wiki_agent news_agent

# 3. Trigger the pipeline
curl -X POST http://localhost:9000/agents/news_agent/tasks \
  -H "Content-Type: application/json" \
  -d '{"message": "Scrape latest Johor election news"}'

# 4. Monitor
curl -s http://localhost:9000/tasks | python3 -c "
import sys, json
tasks = json.load(sys.stdin)
by_type = {}
for t in tasks:
    k = t['type_id']
    by_type.setdefault(k, {})
    by_type[k][t['state']] = by_type[k].get(t['state'], 0) + 1
for k, v in sorted(by_type.items()): print(f'{k}: {v}')
"

# 5. Check DB results
docker exec tracking_votes-postgres-1 psql -U johor -d johor_elections -c "
SELECT
  (SELECT count(*) FROM articles) as articles,
  (SELECT count(*) FROM articles WHERE reliability_score IS NOT NULL) as scored,
  (SELECT count(*) FROM analyses) as analyses,
  (SELECT count(*) FROM seat_predictions) as predictions;
"
```

---

## Port reference (remapped from original)

| Service | URL |
|---|---|
| Dashboard | http://localhost:5175 |
| Control Plane API | http://localhost:9000 |
| News Agent | http://localhost:9001 |
| Scorer Agent | http://localhost:9002 |
| Analyst Agent | http://localhost:9003 |
| Seat Agent | http://localhost:9004 |
| Wiki Agent | http://localhost:9005 |
| Postgres | localhost:5434 |
| Redis | localhost:6380 |
