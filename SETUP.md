# Tracking Votes — New Machine Setup

A Johor election monitoring dashboard. Scrapes Malaysian news, scores articles for electoral relevance, and generates per-seat political analysis. Full stack runs entirely in Docker.

## Prerequisites

- Docker + Docker Compose installed
- The project files (git clone or copy of `tracking_votes/`)
- Three API keys (see Step 1)

---

## Step 1 — Create `.env`

Copy `.env.template` to `.env` and fill in these three keys. Everything else can stay as the template defaults.

```
OPENAI_API_KEY=sk-or-...          # OpenRouter key
ANTHROPIC_API_KEY=sk-ant-...      # Anthropic key
NEWSAPI_KEY=...                   # NewsAPI key
```

Leave `OPENAI_BASE_URL`, `OPENAI_MODEL`, `DATABASE_URL`, `REDIS_URL`, `CONTROL_PLANE_URL`, `AGENT_URLS` exactly as the template shows — they are pre-wired for Docker networking.

---

## Step 2 — Build and start

```bash
docker compose up --build -d
```

First build takes 5–10 minutes (Python deps + Node build). Subsequent starts are fast.

---

## Step 3 — Verify it's running

```bash
# All 8 services should show "Up (healthy)"
docker compose ps

# Control plane health check
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# All 5 agents registered
curl http://localhost:8000/agents
# Expected: JSON array with news_agent, scorer_agent, analyst_agent, seat_agent, wiki_agent
```

Dashboard is at **http://localhost:5175**

---

## Services and ports

| Service | Host port | Purpose |
|---|---|---|
| Dashboard (React/Vite) | 5175 | UI |
| Control plane (FastAPI) | 8000 | API + WebSocket |
| PostgreSQL (pgvector) | 5434 | Database |
| Redis | 7379 | Task queue |
| news_agent | 9001 | Scrapes news |
| scorer_agent | 9002 | Scores articles |
| analyst_agent | 7003 | 6-lens analysis |
| seat_agent | 9004 | Seat predictions |
| wiki_agent | 7005 | Wiki/context |

---

## Step 4 (optional) — Restore a data snapshot

The repo includes a pre-built snapshot of analyzed articles, analyses, and seat predictions in `data/snapshots/snapshot.sql.gz`. Restoring it skips the need to re-scrape and re-analyze from scratch.

**Requires:** Docker stack running (`docker compose up -d`)

```bash
bash data/snapshots/restore_snapshot.sh
```

This truncates `articles`, `analyses`, and `seat_predictions` then loads the snapshot. Historical results and demographics are unaffected (they come from `data/historical/` and are seeded at startup).

To take a new snapshot after a scoring run:

```bash
bash data/snapshots/dump_snapshot.sh
```

This overwrites `data/snapshots/snapshot.sql.gz` with only the articles that have been analyzed (keeps the file small). Commit the updated file to persist it.

---

## Important behaviours

- **Database starts empty** on a fresh machine unless you restore a snapshot (Step 4). News scrapes automatically every 30 minutes. To trigger immediately, use the Scrape button on the dashboard.
- **Score button** on the dashboard runs the full pipeline: scorer → analyst → seat agent for the selected constituency. This requires LLM API credits.
- The `wiki/` folder is mounted as a live volume into `wiki_agent` — it contains Johor constituency reference data and must be present.

---

## Troubleshooting

**Services not healthy after 2 minutes:**
```bash
docker compose logs control_plane | tail -20
docker compose logs <agent_name> | tail -20
```

**"No healthy agent of type X":** Agent failed to register. Restart it:
```bash
docker compose restart <agent_name>
```

**Port already in use:** Edit the left-hand port numbers in `docker-compose.yml` (e.g. `5175:5173` → `5176:5173`). Don't change the right-hand numbers.

**LLM calls failing:** Check `.env` API keys are valid and have credit.

**To stop everything (keep data):**
```bash
docker compose down
```

**To wipe everything including the database:**
```bash
docker compose down -v
```

---

## For a Claude instance helping with this project

The full technical context — architecture decisions, agent pipeline, dashboard implementation, known bugs and fixes — is stored in the Claude memory system at `~/.claude/projects/c--Users-user-tracking-votes/memory/`. Ask the user to check if that memory directory transferred across, or brief Claude from the session history. The `DOCKER_TEST.md` in this repo also has a detailed step-by-step verification checklist.
