# Docker Compose Full Stack Test Guide

This guide walks you through bringing up the entire Johor Election Monitor stack locally using Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- .env file configured with API keys (see below)
- ~5-10 minutes for full startup

## Step 1: Verify .env Configuration

Ensure your `.env` file has these critical keys set:

```bash
# Required LLM API keys
OPENAI_API_KEY=sk-or-...          # OpenRouter key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-oss-120b

ANTHROPIC_API_KEY=sk-ant-...      # Anthropic fallback

# Optional but recommended
NEWSAPI_KEY=...                   # For news scraping

# Database (auto-wired in docker-compose)
DATABASE_URL=postgresql://johor:johor@postgres:5432/johor_elections
REDIS_URL=redis://redis:6379

# Control plane
CONTROL_PLANE_URL=http://control_plane:8000
AGENT_URLS=news_agent@http://news_agent:8001,scorer_agent@http://scorer_agent:8002,analyst_agent@http://analyst_agent:8003,seat_agent@http://seat_agent:8004,wiki_agent@http://wiki_agent:8005
```

Check your .env:
```bash
cat .env | grep "OPENAI_API_KEY\|ANTHROPIC_API_KEY\|OPENAI_MODEL"
```

## Step 2: Build the Docker Image

```bash
cd /path/to/tracking_votes
docker-compose build
```

**Expected output:**
```
Successfully built xyz123456
Successfully tagged tracking_votes_control_plane:latest
Successfully tagged tracking_votes_news_agent:latest
...
```

This may take 2-3 minutes the first time (installs Python + dependencies).

## Step 3: Start Infrastructure (PostgreSQL + Redis)

```bash
docker-compose up -d postgres redis
```

**Verify they're healthy:**
```bash
docker-compose ps
```

You should see:
```
NAME                    STATUS
tracking_votes-postgres-1   Up (healthy)
tracking_votes-redis-1      Up (healthy)
```

Wait 10-15 seconds for PostgreSQL to fully initialize.

## Step 4: Start the Control Plane

```bash
docker-compose up -d control_plane
```

Wait for it to be healthy:
```bash
docker-compose ps
```

Should show:
```
tracking_votes-control_plane-1   Up (healthy)
```

**Verify it started:**
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"ok"}
```

Check the logs to see database initialization:
```bash
docker-compose logs control_plane | tail -20
```

You should see:
```
control_plane.started port=8000
database.initialized
```

## Step 5: Start All Agents

```bash
docker-compose up -d wiki_agent news_agent scorer_agent analyst_agent seat_agent
```

**Wait for all to be healthy:**
```bash
docker-compose ps
```

All should show `Up (healthy)` within 30 seconds.

**Verify agents registered:**
```bash
curl http://localhost:8000/agents
```

Expected: JSON array with 5 agents:
```json
[
  {"name": "wiki_agent", "type_id": "wiki_agent", "url": "http://wiki_agent:8005", ...},
  {"name": "news_agent", "type_id": "news_agent", "url": "http://news_agent:8001", ...},
  ...
]
```

Check control plane logs for registration:
```bash
docker-compose logs control_plane | grep "register\|Agent"
```

## Step 6: Verify Graph Topology

Query the agent graph:
```bash
curl http://localhost:8000/graph | python3 -m json.tool
```

Expected: Non-empty graph with nodes + edges for all 5 agents.

## Step 7: Test Task Dispatch

### Test 1: Health Check

```bash
curl http://localhost:8000/health
```

### Test 2: Get Agent List

```bash
curl http://localhost:8000/agents | python3 -m json.tool
```

### Test 3: Dispatch a Task to Wiki Agent

```bash
curl -X POST http://localhost:8000/agents/wiki_agent/tasks \
  -H "Content-Type: application/json" \
  -d '{"message": "Test wiki ingest"}'
```

Expected: `202 Accepted` response with task_id.

### Test 4: Check Task Status

Use the task_id from Test 3:
```bash
curl http://localhost:8000/tasks/<task_id>
```

Should show task state (PENDING → RUNNING → COMPLETED).

## Step 8: View Logs

Watch real-time logs for all services:
```bash
docker-compose logs -f
```

To watch specific service:
```bash
docker-compose logs -f control_plane
docker-compose logs -f news_agent
```

## Step 9: Database Inspection

Connect to PostgreSQL to verify tables were created:

```bash
docker exec -it tracking_votes-postgres-1 psql -U johor -d johor_elections -c "\dt"
```

Expected: Tables `articles`, `analyses`, `seat_predictions`, `registered_agents`.

## Cleanup

### Stop all services but keep volumes:
```bash
docker-compose stop
```

### Stop and remove containers (keep volumes):
```bash
docker-compose down
```

### Stop and remove everything (including database):
```bash
docker-compose down -v
```

---

## Troubleshooting

### Service won't start: "Connection refused"

**Issue:** Control plane can't connect to PostgreSQL
**Solution:** Wait 20-30 seconds, PostgreSQL takes time to initialize. Check:
```bash
docker-compose logs postgres | tail -10
```

### "No healthy agent of type 'X'"

**Issue:** Agent didn't register with control plane
**Solution:** 
1. Check agent logs: `docker-compose logs <agent_name>`
2. Verify CONTROL_PLANE_URL in .env is correct
3. Restart the agent: `docker-compose restart <agent_name>`

### LLM API call fails: "Invalid API key"

**Issue:** OPENAI_API_KEY or ANTHROPIC_API_KEY invalid
**Solution:**
1. Check .env has valid keys
2. Restart services: `docker-compose restart`

### Database tables not created

**Issue:** Tables missing from PostgreSQL
**Solution:**
1. Check control_plane logs: `docker-compose logs control_plane | grep database`
2. Manually run init: `docker-compose exec control_plane python -c "from control_plane.db import init_database; import asyncio; asyncio.run(init_database('postgresql://...'))"`

### Port conflict (e.g., "Address already in use")

**Issue:** Port 8000/5432/6379 already in use
**Solution:**
```bash
# Find what's using port 8000
lsof -i :8000
# Kill the process or change docker-compose.yml ports
```

---

## Phase 1 Verification Checklist

After full startup, verify all Phase 1 requirements:

- [ ] Control plane starts on :8000
  - `curl http://localhost:8000/health` → 200 OK
  
- [ ] GET /graph returns non-empty topology
  - `curl http://localhost:8000/graph | jq .`
  
- [ ] GET /.well-known/agent-card.json works on each agent
  - `curl http://localhost:8001/.well-known/agent-card.json` (news_agent)
  
- [ ] All 5 agents appear in /agents list
  - `curl http://localhost:8000/agents | jq ".[].name"`
  - Expected: news_agent, scorer_agent, analyst_agent, seat_agent, wiki_agent
  
- [ ] Database tables created
  - `docker-compose exec postgres psql -U johor -d johor_elections -c "\dt"`
  - Expected: articles, analyses, seat_predictions, registered_agents

If all checks pass: **Phase 1 is complete!** ✅

---

## Next Steps (Phase 2-6)

Once Phase 1 verification passes:
- Test end-to-end task dispatch (article → score → analyse → seat predict)
- Build dashboard (Phase 5-6)
- Run integration tests
