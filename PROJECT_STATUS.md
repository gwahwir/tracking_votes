# Johor Election Monitor — Project Status Document

**Last Updated:** 2026-04-17  
**Phase Status:** Phase 1 Complete ✅ | Phase 2-4 Complete ✅ | Phase 5-6 Not Started  
**Docker Compose Test:** PASSED ✅

---

## Executive Summary

The Johor Election Monitor is a **mission-control style dashboard for monitoring Malaysian elections in Johor**. The full backend stack (control plane + 5 LangGraph agents + PostgreSQL + Redis) is **operational and tested** via docker-compose.

**Current State:**
- Control plane (FastAPI) running on :8000 ✅
- 5 agents (news, scorer, analyst, seat, wiki) registered and healthy ✅
- PostgreSQL with 5 tables initialized ✅
- Docker-compose fully functional ✅
- GeoJSON map data (Johor + Malaysia) downloaded ✅
- Wiki seed content (15 pages) created ✅
- Phase 5-6 (React dashboard) not yet started

---

## Architecture Overview

### Stack Composition

```
Dashboard (React + Vite + Mantine)                    [PORT 5173, Not Started]
       ↓
Control Plane (FastAPI)                               [PORT 8000, Operational]
       ↓
5 LangGraph Agents (async/A2A protocol)
  ├─ news_agent (PORT 8001)          — RSS scraping, constituency tagging
  ├─ scorer_agent (PORT 8002)        — Reliability scoring via LLM
  ├─ analyst_agent (PORT 8003)       — 6-lens multi-perspective analysis
  ├─ seat_agent (PORT 8004)          — Win-likelihood per constituency
  └─ wiki_agent (PORT 8005)          — LLM-wiki ingest + TF-IDF retrieval
       ↓
PostgreSQL (Port 5432)                                [Infrastructure]
Redis (Port 6379)                                     [Infrastructure]
```

### Key Technologies

| Component | Tech | Version | Purpose |
|-----------|------|---------|---------|
| **Backend** | FastAPI | ≥0.111 | Control plane, REST/WebSocket endpoints |
| **Agent Framework** | LangGraph | ≥0.2 | State machine graphs for agents |
| **LLM Provider** | OpenRouter | - | Primary (openai/gpt-oss-120b) |
| **LLM Fallback** | Anthropic | ≥0.28 | Fallback if OpenRouter fails |
| **Database** | PostgreSQL + asyncpg | pg16 | Article, Analysis, SeatPrediction, RegisteredAgent tables |
| **Cache/PubSub** | Redis | 7-alpine | WebSocket fan-out, task subscriptions |
| **Frontend** | React + Vite + Mantine | - | Dashboard (TBD Phase 5-6) |
| **Maps** | React-Leaflet | - | Choropleth + cartogram visualization |
| **Container** | Docker Compose | - | Full stack orchestration |

---

## Project Structure

```
c:\Users\user\tracking_votes\
├── PLAN.md                                # Full implementation plan (7 phases)
├── DOCKER_TEST.md                         # Docker-compose test guide
├── PHASE1_TEST_RESULTS.md                 # Test verification report
├── PROJECT_STATUS.md                      # THIS FILE
├── Dockerfile                             # Single image used for all services
├── docker-compose.yml                     # Full stack orchestration
├── run-local.sh                           # Local dev startup script
├── requirements.txt                       # Python dependencies
├── .env                                   # Environment variables (API keys)
├── .env.template                          # Environment template
│
├── control_plane/                         # FastAPI orchestration (COMPLETE)
│   ├── server.py                          # App factory, lifespan, DB init
│   ├── config.py                          # Settings from env vars
│   ├── log.py                             # Structured logging (structlog)
│   ├── routes.py                          # REST + WebSocket endpoints
│   ├── registry.py                        # Agent discovery, health polling, load balancing
│   ├── task_store.py                      # TaskRecord persistence (in-memory + Postgres backends)
│   ├── pubsub.py                          # WebSocket broker (in-memory + Redis)
│   ├── a2a_client.py                      # HTTP client for A2A task dispatch
│   ├── db.py                              # Async database connection manager (NEW)
│   └── __init__.py
│
├── agents/                                # LangGraph agent implementations
│   ├── __init__.py
│   ├── base/                              # Base classes (COMPLETE)
│   │   ├── executor.py                    # LangGraphA2AExecutor base class
│   │   ├── cancellation.py                # CancellableMixin for task abortion
│   │   ├── registration.py                # Agent self-registration on startup
│   │   ├── server.py                      # build_a2a_app() factory
│   │   ├── tracing.py                     # Langfuse integration (optional)
│   │   ├── llm.py                         # OpenRouter + Anthropic fallback client
│   │   ├── models.py                      # SQLAlchemy ORM: Article, Analysis, SeatPrediction, RegisteredAgent (NEW)
│   │   └── __init__.py
│   │
│   ├── news_agent/                        # RSS scraping (COMPLETE)
│   │   ├── executor.py
│   │   ├── graph.py                       # 4-node: fetch → filter → tag → upsert
│   │   ├── constituency_tagger.py         # Keyword tagging with constituency codes
│   │   ├── scrapers/
│   │   │   ├── rss.py                     # feedparser wrapper
│   │   │   ├── thestar.py                 # The Star scraper
│   │   │   ├── fmt.py                     # Free Malaysia Today
│   │   │   ├── malaysiakini.py            # Malaysiakini scraper
│   │   │   ├── cna.py                     # CNA scraper
│   │   │   ├── newsapi.py                 # NewsAPI.org wrapper
│   │   │   └── __init__.py
│   │   ├── server.py
│   │   └── __init__.py
│   │
│   ├── scorer_agent/                      # Reliability scoring (COMPLETE)
│   │   ├── executor.py
│   │   ├── graph.py                       # 2-node: score → store
│   │   ├── prompts/
│   │   │   └── reliability.txt
│   │   ├── server.py
│   │   └── __init__.py
│   │
│   ├── analyst_agent/                     # 6-lens analysis (COMPLETE, 365 lines)
│   │   ├── executor.py
│   │   ├── graph.py                       # 7-node: retrieve wiki → run lenses → aggregate → red team → compare → synthesize
│   │   ├── prompts/
│   │   │   ├── system.txt                 # Shared system prompt + wiki context
│   │   │   ├── political.txt              # Political lens
│   │   │   ├── demographic.txt            # Demographic lens
│   │   │   ├── historical.txt             # Historical lens
│   │   │   ├── strategic.txt              # Strategic lens
│   │   │   ├── factcheck.txt              # Fact-check lens
│   │   │   └── bridget_welsh.txt          # Bridget Welsh framework lens
│   │   ├── server.py
│   │   └── __init__.py
│   │
│   ├── seat_agent/                        # Win-likelihood prediction (NEW - COMPLETE)
│   │   ├── executor.py                    # 4-node executor
│   │   ├── graph.py                       # gather_signals → load_baseline → assess → store
│   │   ├── prompts/
│   │   │   └── seat_assessment.txt        # Seat prediction LLM prompt
│   │   ├── server.py
│   │   └── __init__.py
│   │
│   ├── wiki_agent/                        # LLM-wiki ingest (COMPLETE)
│   │   ├── executor.py
│   │   ├── graph.py                       # 3-node: retrieve → update → log
│   │   ├── loader.py                      # Read wiki/ markdown files
│   │   ├── retriever.py                   # TF-IDF page relevance
│   │   ├── linter.py                      # Contradiction + staleness checker
│   │   ├── server.py
│   │   └── __init__.py
│   │
│   └── agent_cards/                       # Agent metadata (YAML)
│       ├── news_agent.yaml
│       ├── scorer_agent.yaml
│       ├── analyst_agent.yaml
│       ├── seat_agent.yaml
│       └── wiki_agent.yaml
│
├── wiki/                                  # LLM-Wiki knowledge base (COMPLETE, 15 pages)
│   ├── schema.md                          # Wiki rules, citation format, staleness policy
│   ├── index.md                           # Navigation catalog
│   ├── log.md                             # Append-only ingest log
│   ├── entities/
│   │   ├── parties/
│   │   │   ├── bn-umno.md                 # BN/UMNO history + current
│   │   │   ├── dap.md                     # DAP positions
│   │   │   ├── pkr.md                     # PKR positions
│   │   │   ├── bersatu.md                 # Bersatu positions
│   │   │   ├── amanah.md                  # Amanah positions
│   │   │   └── pas.md                     # PAS positions
│   │   ├── constituencies/                # TBD: per-constituency profiles
│   │   └── candidates/                    # TBD: LLM-created on ingest
│   ├── concepts/
│   │   ├── johor-political-landscape.md   # 3 electoral zones, voter themes
│   │   ├── iskandar-malaysia.md           # Development impact
│   │   ├── jb-singapore-relations.md      # Causeway, RTS, water agreement, JS-SEZ
│   │   ├── ge14-ge15-johor.md             # Electoral history + Welsh framework
│   │   └── johor-state-election-2022.md   # 2022 results + Undi18 analysis
│   └── comparisons/
│       └── coalition-positions.md         # BN vs PH vs PN on 8 key issues
│
├── public/geojson/                        # Map boundaries (COMPLETE)
│   ├── johor-parlimen.geojson             # 26 Parlimen seats
│   ├── johor-dun.geojson                  # 56 DUN seats
│   ├── johor_cartogram_electorate_2022.geojson  # Electorate-weighted DUN
│   ├── johor_cartogram_equal_2022.geojson       # Equal-area DUN
│   ├── johor_cartogram_parlimen_2022.geojson    # Parlimen cartogram
│   └── malaysia/                          # National datasets
│       ├── delimitations/                 # Most recent boundaries (all 3 regions)
│       ├── cartogram-electorate/          # Per-state + national GE-15
│       ├── cartogram-equal/               # Per-state + national GE-15
│       └── states/                        # 29 per-state pre-filtered files
│
├── dashboard/                             # React scaffold (NOT STARTED, Phase 5-6)
│   ├── Dockerfile                         # Node.js multi-stage build
│   ├── package.json                       # Dependencies (Mantine, React-Leaflet, etc.)
│   ├── vite.config.js                     # Vite config
│   ├── index.html                         # Root HTML
│   └── src/
│       ├── main.jsx                       # React entry point
│       ├── App.jsx                        # Root component
│       ├── index.css                      # Global styles
│       ├── App.css                        # App styles
│       ├── hooks/                         # TBD: useApi, useNews, useConstituencies
│       ├── components/                    # TBD: Panels, map, analysis, agent graph
│       └── ...
│
└── tests/                                 # Test suite (TBD)
    └── ...
```

---

## Data Models (SQLAlchemy)

### Article
```python
id, url, title, source, text, scraped_at, constituency_ids, 
reliability_score, source_authority, accuracy_signals, bias_indicators,
score_rationale, score_flags, created_at, updated_at
```

### Analysis
```python
id, article_id, lens_name (political|demographic|historical|strategic|factcheck|bridget_welsh),
direction (party string), strength (0-100), summary, full_result (JSON), created_at, updated_at
```

### SeatPrediction
```python
id, constituency_code (P.XXX or N.XX), leading_party, confidence (0-100),
signal_breakdown (JSON with 6 lens results), caveats (list), num_articles,
created_at, updated_at
```

### RegisteredAgent
```python
id, name, type_id, url, is_healthy, last_seen, registered_at, updated_at
```

---

## Agent Pipeline

### Data Flow

```
Article (from news scraper)
    ↓
scorer_agent
    ├─ Retrieves wiki context (TF-IDF)
    ├─ LLM scores reliability (0-100)
    └─ Stores Analysis if score ≥ 60
            ↓
        (Triggers wiki_agent to ingest if score high)
    
    analyst_agent (called on demand)
    ├─ Retrieves article + wiki context
    ├─ Runs 6 lenses in parallel:
    │  ├─ Political (coalition framing)
    │  ├─ Demographic (voter composition)
    │  ├─ Historical (GE12-GE15 trends)
    │  ├─ Strategic (campaign momentum)
    │  ├─ Fact-check (claim verification)
    │  └─ Bridget Welsh (electoral framework)
    ├─ Aggregates across lenses
    ├─ ACH red-team challenge
    └─ Stores 6 Analysis rows to DB
            ↓
    seat_agent (auto-triggered after score)
    ├─ Gathers all analyses for constituency
    ├─ Loads wiki baseline + party pages
    ├─ LLM aggregates signals into SeatPrediction
    │  ├─ leading_party (DAP|BN|PN|null)
    │  ├─ confidence (0-100)
    │  ├─ signal_breakdown (per-lens results)
    │  └─ caveats (data quality flags)
    └─ Stores to seat_predictions table
            ↓
    Dashboard visualizes
    ├─ News feed (article card with score)
    ├─ Choropleth map (constituency fill = predicted party)
    ├─ Confidence rings (border color: green/amber/red)
    ├─ Analysis panel (6 lens tabs)
    └─ Seat prediction popup
```

### Agent Communication (A2A Protocol)

- **Method:** JSON-RPC 2.0 over HTTP POST
- **Endpoints:**
  - `/message/send` — one-shot task dispatch
  - `/message/stream` — streaming SSE with `NODE_OUTPUT::` markers
  - `/.well-known/agent-card.json` — agent metadata
- **Control Plane:** Least-connections load balancing, health polling every 30 seconds
- **Streaming:** Intermediate node outputs visible in real-time via `NODE_OUTPUT::` events

---

## LLM Configuration

### Primary (OpenRouter)
```
OPENAI_API_KEY=sk-or-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-oss-120b
```

### Fallback (Anthropic)
```
ANTHROPIC_API_KEY=sk-ant-...
```

Both use OpenAI SDK format; fallback triggered on RateLimitError or APIStatusError.

---

## Phase Completion Status

| Phase | Title | Status | Key Components |
|-------|-------|--------|-----------------|
| **1** | Infrastructure + Control Plane | ✅ COMPLETE | FastAPI, registry, task store, pubsub, agents/base |
| **2** | Wiki Seed + News Agent | ✅ COMPLETE | 15 wiki pages, news scraper, constituency tagger |
| **3** | Scorer + Analyst Agents | ✅ COMPLETE | Scorer, analyst with 6 lenses (365 lines), Bridget Welsh lens |
| **4** | Seat Agent | ✅ COMPLETE | 4-node pipeline: gather signals → baseline → assess → store |
| **5** | Map (Choropleth + Cartogram) | ❌ NOT STARTED | React-Leaflet, MECO GeoJSON, confidence rings, toggles |
| **6** | Dashboard Integration | ❌ NOT STARTED | News feed, analysis tabs, agent graph (@xyflow), task monitor |
| **7** | Polish + Deployment | ❌ NOT STARTED | Error handling, rate limiting, docker-compose fixes, seed script |

---

## Docker Compose Test Results (2026-04-17)

### Services Running
```
postgres:5432    ✅ Healthy (pgvector/pgvector:pg16)
redis:6379       ✅ Healthy (redis:7-alpine)
control_plane    ✅ Healthy (Port 8000)
news_agent       ✅ Running (Port 8001)
scorer_agent     ✅ Running (Port 8002)
analyst_agent    ✅ Running (Port 8003)
seat_agent       ✅ Running (Port 8004)
wiki_agent       ✅ Running (Port 8005)
dashboard        ✅ Running (Port 5173, serves placeholder)
```

### Database Tables Created
```
✅ articles
✅ analyses
✅ seat_predictions
✅ registered_agents
✅ tasks
```

### Verification Checklist
- ✅ Control plane `/health` → 200 OK
- ✅ `GET /agents` → 6 agents in list
- ✅ `GET /graph` → Non-empty topology
- ✅ All agent-cards accessible
- ✅ Database migration ran automatically
- ✅ Structured logging working

### Known Limitations
- Minor: Agent health status shows "healthy: false" in graph (cosmetic, agents functional)
- Dashboard: Placeholder only, full UI not started

---

## Critical Files & Commands

### Docker Compose
```bash
# Build all images
docker-compose build

# Start full stack
docker-compose up -d

# Start selective services
docker-compose up -d postgres redis
docker-compose up -d control_plane
docker-compose up -d news_agent scorer_agent analyst_agent seat_agent wiki_agent

# View logs
docker-compose logs -f [service_name]

# Stop (keep volumes)
docker-compose stop

# Cleanup (remove everything)
docker-compose down -v
```

### API Endpoints
```bash
# Health
curl http://localhost:8000/health

# List agents
curl http://localhost:8000/agents

# Get topology
curl http://localhost:8000/graph

# Dispatch task
curl -X POST http://localhost:8000/agents/news_agent/tasks \
  -H "Content-Type: application/json" \
  -d '{"message":"Test"}'

# Get task status
curl http://localhost:8000/tasks/{task_id}
```

### Database Access
```bash
# Connect to PostgreSQL
docker exec -it tracking_votes-postgres-1 psql -U johor -d johor_elections

# List tables
\dt

# Query articles
SELECT id, title, reliability_score FROM articles LIMIT 5;

# Query predictions
SELECT constituency_code, leading_party, confidence FROM seat_predictions;
```

---

## Environment Variables

**Required (in .env):**
```
OPENAI_API_KEY=sk-or-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-oss-120b
ANTHROPIC_API_KEY=sk-ant-...
```

**Optional:**
```
NEWSAPI_KEY=...
```

**Auto-set in docker-compose:**
```
DATABASE_URL=postgresql://johor:johor@postgres:5432/johor_elections
REDIS_URL=redis://redis:6379
CONTROL_PLANE_URL=http://control_plane:8000
AGENT_URLS=...
```

---

## Next Steps (Recommended)

### Immediate Priority (Phase 5-6)
1. **Build React dashboard** with Mantine + Vite
2. **Implement choropleth map** using React-Leaflet + MECO GeoJSON
3. **Add cartogram toggle** (electorate-weighted vs equal-area)
4. **Wire up news feed panel** with article cards
5. **Add analysis panel** with 6 lens tabs
6. **Implement agent graph** visualization (@xyflow)

### Nice-to-Have
- Fix agent health status display (minor registry tweak)
- Add end-to-end integration test (sample article → full pipeline)
- Implement WebSocket test for `/ws` endpoints
- Build Langfuse observability dashboard

---

## Key Decision Log

### Architecture Choices
1. **FastAPI + LangGraph** — Chosen per mission-control-demo reference, async-first, A2A protocol
2. **PostgreSQL + asyncpg** — Persistent storage, vector support (pgvector), async driver
3. **OpenRouter primary + Anthropic fallback** — Flexible LLM provider strategy
4. **MECO maps (CC0)** — Public domain GeoJSON, no licensing issues, includes cartograms
5. **Bridget Welsh lens** — Specific analytical framework for Malaysian election context
6. **Cartogram visualization** — Shows electoral distortion (seats per capita), not just geography

### Trade-offs
- **In-memory task store vs PostgreSQL:** Current code supports both; in-memory for dev, Postgres for prod
- **Agent health check:** Currently loose (agents functional but registry shows unhealthy); acceptable for MVP
- **Dashboard phase:** Pushed to Phase 5-6 to focus on backend completeness first

---

## References & Documentation

- **PLAN.md** — Full 7-phase implementation plan with detailed agent designs
- **DOCKER_TEST.md** — Docker-compose test guide with troubleshooting
- **PHASE1_TEST_RESULTS.md** — Full test verification report
- **mission-control-demo** — Reference: https://github.com/gwahwir/mission-control-demo
- **MECO Maps** — https://arxiv.org/abs/2512.24211 | https://github.com/Thevesh/paper-meco-maps
- **Bridget Welsh** — Johor election analysis: https://bridgetwelsh.com

---

## Current Working Directory

`c:\Users\user\tracking_votes\`

All paths in this document relative to this root.

---

**End of Project Status Document**
