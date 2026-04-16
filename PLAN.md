# Johor Election Monitoring Dashboard — Implementation Plan

## Context

Build a mission-control style dashboard for monitoring elections in Johor, Malaysia — covering both **Parlimen** (26 federal seats) and **DUN** (56 state seats). The architecture is modelled directly on [gwahwir/mission-control-demo](https://github.com/gwahwir/mission-control-demo):

- **Control Plane** (FastAPI) — central registry, task routing, WebSocket updates
- **Agent Layer** (LangGraph A2A agents) — specialised services that self-register, each implementing a distinct analytical function
- **Dashboard** (React + Vite + Mantine) — cyberpunk HUD, real-time task monitoring, choropleth map

**LLM provider:** OpenRouter primary (`openai/gpt-oss-120b`) via the OpenAI SDK pointed at `https://openrouter.ai/api/v1`. Anthropic SDK as fallback. Env vars follow the reference repo convention: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`.

**LLM-Wiki knowledge layer** (Karpathy's llm-wiki pattern): a git-tracked set of markdown files encoding Johor political knowledge — parties, constituencies, candidates, electoral history. Injected as context into every LLM call to ground analysis in current, project-specific knowledge.

**A2A protocol:** JSON-RPC 2.0 over HTTP with SSE streaming. Agents self-register via `/.well-known/agent-card.json`. Control plane does least-connections load balancing and health polling.

---

## Project Structure

```
johor-election-dashboard/
├── .env                                # All env vars (see section below)
├── .env.template
├── docker-compose.yml                  # Full stack: PostgreSQL, Redis, all services
├── run-local.sh                        # Start all services sequentially
│
├── wiki/                               # LLM-Wiki knowledge base (git-tracked markdown)
│   ├── schema.md                       # Wiki rules, citation format, ingest workflow
│   ├── index.md                        # Content catalog (updated on every ingest)
│   ├── log.md                          # Append-only ingest log (timestamped)
│   ├── entities/
│   │   ├── parties/
│   │   │   ├── bn-umno.md
│   │   │   ├── dap.md
│   │   │   ├── pkr.md
│   │   │   ├── bersatu.md
│   │   │   ├── amanah.md
│   │   │   └── pas.md
│   │   ├── constituencies/
│   │   │   ├── parlimen/               # 26 x .md files (one per seat)
│   │   │   └── dun/                    # 56 x .md files (one per seat)
│   │   └── candidates/                 # LLM-created on ingest
│   ├── concepts/
│   │   ├── johor-political-landscape.md
│   │   ├── iskandar-malaysia.md
│   │   ├── jb-singapore-relations.md
│   │   ├── ge14-ge15-johor.md
│   │   └── johor-state-election-2022.md
│   └── comparisons/
│       └── coalition-positions.md
│
├── public/geojson/
│   ├── johor-parlimen.geojson              # 26 Parlimen seat boundaries (MECO 2018 delimitation)
│   ├── johor-dun.geojson                   # 56 DUN seat boundaries (MECO 2018 delimitation)
│   ├── johor_cartogram_electorate_2022.geojson  # 56 DUN electorate-weighted cartogram (voters_total per seat)
│   ├── johor_cartogram_equal_2022.geojson       # 56 DUN equal-area cartogram
│   └── johor_cartogram_parlimen_2022.geojson    # 26 Parlimen cartogram (dissolved from DUN electorate cartogram)
│
├── control_plane/                      # FastAPI, port 8000
│   ├── server.py                       # App factory, middleware, startup
│   ├── registry.py                     # AgentRegistry: self-registration, health polling, load balancing
│   ├── routes.py                       # REST + WebSocket endpoints
│   ├── task_store.py                   # TaskRecord, TaskState, in-memory + PostgreSQL backends
│   ├── pubsub.py                       # InMemoryBroker / RedisBroker for WebSocket fan-out
│   ├── a2a_client.py                   # HTTP client for dispatching tasks to agents via A2A
│   └── config.py                       # Settings from env vars (AGENT_URLS, DATABASE_URL, etc.)
│
├── agents/
│   ├── base/
│   │   ├── executor.py                 # LangGraphA2AExecutor base class
│   │   ├── cancellation.py             # CancellableMixin
│   │   ├── registration.py             # Self-register with control plane on startup
│   │   ├── server.py                   # build_a2a_app() factory — mounts agent on FastAPI
│   │   └── tracing.py                  # Optional Langfuse integration
│   │
│   ├── news_agent/                     # Port 8001 — RSS scraping + article storage
│   │   ├── executor.py
│   │   ├── graph.py                    # 3-node: fetch → filter → upsert
│   │   ├── scrapers/
│   │   │   ├── rss.py                  # Generic RSS parser (feedparser)
│   │   │   ├── thestar.py
│   │   │   ├── fmt.py                  # Free Malaysia Today
│   │   │   ├── malaysiakini.py
│   │   │   ├── cna.py
│   │   │   └── newsapi.py              # NewsAPI.org wrapper
│   │   ├── constituency_tagger.py      # Keyword-tag articles with constituency codes
│   │   └── server.py
│   │
│   ├── scorer_agent/                   # Port 8002 — reliability scoring
│   │   ├── executor.py
│   │   ├── graph.py                    # 2-node: score → store
│   │   ├── prompts/
│   │   │   └── reliability.txt         # System prompt (references wiki context)
│   │   └── server.py
│   │
│   ├── analyst_agent/                  # Port 8003 — 6-lens multi-perspective analysis
│   │   ├── executor.py
│   │   ├── graph.py                    # 7-stage pipeline (mirrors lead_analyst pattern)
│   │   ├── prompts/
│   │   │   ├── system.txt              # Shared system prompt + wiki context placeholder
│   │   │   ├── political.txt
│   │   │   ├── demographic.txt
│   │   │   ├── historical.txt
│   │   │   ├── strategic.txt
│   │   │   ├── factcheck.txt
│   │   │   └── bridget_welsh.txt       # Welsh analytical framework lens
│   │   └── server.py
│   │
│   ├── seat_agent/                     # Port 8004 — win-likelihood prediction per constituency
│   │   ├── executor.py
│   │   ├── graph.py                    # 4-node: gather signals → baseline → assess → store
│   │   ├── prompts/
│   │   │   └── seat_assessment.txt
│   │   └── server.py
│   │
│   ├── wiki_agent/                     # Port 8005 — LLM-wiki ingest + lint
│   │   ├── executor.py
│   │   ├── graph.py                    # 3-node: retrieve relevant pages → update → log
│   │   ├── loader.py                   # Read wiki/*.md from filesystem
│   │   ├── retriever.py                # TF-IDF keyword scorer for page relevance
│   │   ├── linter.py                   # Contradiction + staleness checker
│   │   └── server.py
│   │
│   └── agent_cards/
│       ├── news_agent.yaml
│       ├── scorer_agent.yaml
│       ├── analyst_agent.yaml
│       ├── seat_agent.yaml
│       └── wiki_agent.yaml
│
├── dashboard/                          # React + Vite + Mantine, port 5173
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.jsx                    # Mantine dark theme, cyberpunk palette (cyan/green/red)
│       ├── App.jsx                     # Layout shell
│       ├── hooks/
│       │   ├── useApi.js               # fetchAgents, dispatchTask, cancelTask, subscribeToTask
│       │   ├── useNews.js              # Poll /api/news, 60s refetch
│       │   └── useConstituencies.js    # Fetch constituency + seat prediction data
│       └── components/
│           ├── layout/
│           │   ├── DashboardShell.jsx  # 3-column grid: feed | map | analysis
│           │   └── TopBar.jsx          # Status, refresh, map toggle, wiki button
│           ├── news/
│           │   ├── NewsFeedPanel.jsx
│           │   ├── ArticleCard.jsx
│           │   └── ReliabilityBadge.jsx
│           ├── map/
│           │   ├── ElectionMap.jsx         # React-Leaflet choropleth + cartogram toggle
│           │   ├── ChoroplethLayer.jsx     # Fill = party colour; border = confidence ring
│           │   ├── CartogramLayer.jsx      # Electorate-weighted or equal-area MECO cartogram
│           │   ├── MapTypeToggle.jsx       # Parlimen / DUN + Choropleth / Cartogram toggles
│           │   ├── ConstituencyPopup.jsx   # Seat prediction + signal breakdown
│           │   └── MapLegend.jsx
│           ├── analysis/
│           │   ├── AnalysisPanel.jsx
│           │   ├── ReliabilityScoreCard.jsx
│           │   ├── PerspectiveTabs.jsx # 6 tabs: Political|Demographic|Historical|Strategic|Fact-check|Bridget Welsh
│           │   └── AnalysisLoader.jsx
│           ├── agents/
│           │   ├── AgentGraph.jsx      # @xyflow/react topology visualisation
│           │   └── TaskMonitor.jsx     # Real-time task status (mirrors mission-control HUD)
│           └── wiki/
│               ├── WikiModal.jsx       # List all wiki pages with last-updated + lint status
│               └── WikiContextBadge.jsx # Shows which pages were used in current analysis
│
└── tests/
    ├── conftest.py
    ├── test_task_lifecycle.py
    ├── test_scorer_agent.py
    ├── test_analyst_agent.py
    └── test_seat_agent.py
```

---

## A2A Protocol (from mission-control-demo)

All inter-agent communication uses **JSON-RPC 2.0 over HTTP POST** with SSE streaming for results:

```python
# Task dispatch (control_plane/a2a_client.py)
payload = {
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "params": {
        "id": task_id,
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": message_text}]
        },
        "metadata": {"task_id": task_id, "source": "control_plane"}
    }
}

# Agent self-registration (agents/base/registration.py)
# On startup: POST /register with agent card
# Health check: GET /.well-known/agent-card.json every 30s

# Streaming response uses SSE with NODE_OUTPUT:: markers
# for intermediate node results visible in the dashboard task monitor
```

**Agent card format** (`agents/agent_cards/*.yaml`):
```yaml
name: "Johor Scorer Agent"
type_id: "scorer_agent"
description: "Reliability scoring for Johor election news articles"
url: "http://localhost:8002"
capabilities:
  streaming: true
  cancellation: true
```

---

## LLM Call Format (OpenAI SDK → OpenRouter)

All LLM calls use the OpenAI Python SDK pointed at OpenRouter:

```python
# agents/base/llm.py  (shared utility)
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],       # OpenRouter key
    base_url=os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
    default_headers={
        "HTTP-Referer": os.environ.get("APP_URL", "http://localhost:5173"),
        "X-Title": "Johor Election Dashboard",
    }
)
MODEL = os.environ.get("OPENAI_MODEL", "openai/gpt-oss-120b")

# Standard call
response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message}
    ],
    temperature=0.5,
    response_format={"type": "json_object"},  # for scorer
)

# Streaming call (analyst, seat assessor)
stream = client.chat.completions.create(model=MODEL, messages=messages, stream=True)
for chunk in stream:
    yield chunk.choices[0].delta.content or ""
```

**Anthropic fallback** (`agents/base/llm.py`):
```python
import anthropic
_anthropic = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def llm_call_with_fallback(messages, **kwargs):
    try:
        return openrouter_call(messages, **kwargs)
    except (openai.RateLimitError, openai.APIStatusError) as e:
        logger.warning(f"OpenRouter failed ({e.status_code}), falling back to Anthropic")
        return anthropic_call(messages, **kwargs)
```

---

## Agent Designs

### news_agent (Port 8001)
**LangGraph nodes:** `fetch` → `filter` → `tag` → `upsert`
- `fetch`: calls all scrapers (feedparser RSS + NewsAPI fallback) in parallel
- `filter`: keyword filter — `["Johor","Parlimen","DUN","UMNO","BN","PKR","DAP","Bersatu","PRU","pilihanraya","calon","GE","Iskandar","Johor Bahru"]`
- `tag`: `constituency_tagger.py` matches article text against constituency name lookup → stores JSON array of matched codes
- `upsert`: dedup by URL, write to PostgreSQL
- Triggered by: control plane cron every 5 min, or manual dispatch from dashboard

### scorer_agent (Port 8002)
**LangGraph nodes:** `retrieve_wiki` → `score` → `store`
- `retrieve_wiki`: TF-IDF retriever fetches top-3 wiki excerpts relevant to the article
- `score`: LLM call with wiki context injected → JSON output `{ score, sourceAuthority, accuracySignals, biasIndicators, justification, flags }`
- `store`: persist to `articles` table; if score ≥ 60, emit A2A task to `wiki_agent`
- Triggered by: article selection in dashboard OR batch after news scrape

### analyst_agent (Port 8003)
**LangGraph nodes (7-stage, mirrors lead_analyst):**
1. `retrieve_wiki` — fetch relevant wiki pages for this article
2. `run_lenses` — call LLM for each of 6 lenses in parallel (Political, Demographic, Historical, Strategic, Fact-check, Bridget Welsh)
3. `peripheral_scan` — catch weak signals / blind spots before aggregation
4. `aggregate` — synthesise across all 6 lenses
5. `red_team` — ACH challenge: what alternative interpretations were missed?
6. `baseline_compare` — compare to stored wiki baselines if available
7. `final_synthesis` — balanced summary with confidence indicators
- Streams `NODE_OUTPUT::` markers so dashboard task monitor shows live progress
- Each lens result cached in PostgreSQL `analyses` table

### seat_agent (Port 8004)
**LangGraph nodes:** `gather_signals` → `load_baseline` → `assess` → `store`
- `gather_signals`: retrieve all `analyses` rows for articles tagged to this constituency (last 30 days) — one signal per lens per article
- `load_baseline`: load constituency wiki page + party pages for historical baseline
- `assess`: LLM aggregates signals into `SeatPrediction { leadingParty, confidence, signalBreakdown[6], caveats }`
- `store`: write to `seat_predictions` table
- Auto-triggered (non-blocking) after each article is scored, for all tagged constituencies

### wiki_agent (Port 8005)
**LangGraph nodes:** `retrieve` → `update_pages` → `append_log`
- `retrieve`: load existing wiki pages relevant to the article (retriever.py)
- `update_pages`: LLM identifies which pages to update, what facts to add, flags `[CONTRADICTION]` entries — writes updated .md files
- `append_log`: timestamped entry added to `wiki/log.md`
- Lint mode (separate graph): reads all pages, checks for contradictions/staleness/orphans — returns lint report
- **Never silently overwrites contradictions** — these are flagged in log.md and surfaced in WikiModal

---

## Dashboard Design (React + Vite + Mantine)

Follows mission-control-demo's cyberpunk HUD aesthetic:
- **Colour palette:** dark background `#0a0a0f`, neon cyan `#00d4ff`, neon green `#39ff14`, red `#ff3131`
- **Font:** JetBrains Mono (monospace throughout)
- **Mantine v8** component library

**Layout:** 3-column grid
```
┌────────────────────────────────────────────────────────────┐
│  TopBar: JOHOR ELECTION MONITOR | status | toggle | refresh │
├─────────────────┬──────────────────────┬───────────────────┤
│  NEWS FEED      │     MAP              │  ANALYSIS         │
│  (320px)        │     (flex-grow)      │  (400px)          │
│                 │                      │                   │
│  ArticleCards   │  Leaflet Choropleth  │  Score card       │
│  with score     │  Parlimen / DUN      │  6 lens tabs      │
│  badges         │  toggle              │  Wiki context     │
│                 │                      │                   │
├─────────────────┴──────────────────────┴───────────────────┤
│  Agent Graph (collapsible): @xyflow topology + TaskMonitor  │
└────────────────────────────────────────────────────────────┘
```

**Map — source data (MECO, CC0):**
All boundary and cartogram files are sourced from [Thevesh/paper-meco-maps](https://github.com/Thevesh/paper-meco-maps) (Thevananthan & Chacko 2025, arXiv:2512.24211), released under CC0. Pre-processed files live in `public/geojson/`:
- `johor-parlimen.geojson` — 26 Parlimen seats; properties: `state`, `parlimen`, `code_parlimen`
- `johor-dun.geojson` — 56 DUN seats; properties: `state`, `parlimen`, `code_parlimen`, `dun`, `code_dun`
- `johor_cartogram_electorate_2022.geojson` — 56 DUN seats distorted by `voters_total` (electorate-weighted)
- `johor_cartogram_equal_2022.geojson` — 56 DUN seats equal-area cartogram
- `johor_cartogram_parlimen_2022.geojson` — 26 Parlimen seats dissolved from DUN electorate cartogram

**Map toggle states (2 axes = 4 combinations):**
- Axis 1: **Parlimen** (26 seats) | **DUN** (56 seats)
- Axis 2: **Choropleth** (geographic boundaries) | **Cartogram** (electorate-weighted; highlights malapportionment per Welsh framework)

**Choropleth / Cartogram styling:**
- Fill colour = `PARTY_COLORS[seatPrediction.leadingParty]`
- Border ring = confidence: green ≥70%, amber 40–69%, red <40% (border weight 2–4px)
- Click → `ConstituencyPopup` with full 6-lens signal breakdown table + caveats
- Cartogram note in MapLegend: "Area proportional to electorate size — highlights voter weight inequality"

**Agent Graph panel** (bottom, collapsible):
- `@xyflow/react` renders the live agent topology pulled from `GET /graph`
- Each node shows agent name, health status (green/red), current task count
- Mirrors the mission-control-demo HUD pattern exactly

---

## Environment Variables

```bash
# LLM — OpenAI SDK → OpenRouter (matches mission-control-demo convention)
OPENAI_API_KEY=sk-or-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-oss-120b

# LLM fallback
ANTHROPIC_API_KEY=sk-ant-...

# News
NEWSAPI_KEY=...

# Infrastructure
DATABASE_URL=postgresql://user:pass@localhost/johor_elections
REDIS_URL=redis://localhost:6379

# Control plane + agents
CONTROL_PLANE_URL=http://localhost:8000
AGENT_URLS=news_agent@http://localhost:8001,scorer_agent@http://localhost:8002,analyst_agent@http://localhost:8003,seat_agent@http://localhost:8004,wiki_agent@http://localhost:8005

# App
APP_URL=http://localhost:5173
CRON_SECRET=...

# Optional observability
LANGFUSE_PUBLIC_KEY=...
LOG_LEVEL=INFO
```

---

## Python Dependencies (requirements.txt)

```
fastapi>=0.111
uvicorn[standard]>=0.29
langgraph>=0.2
langchain-openai>=0.1
openai>=1.30
anthropic>=0.28
feedparser>=6.0
httpx>=0.27
asyncpg>=0.29
redis>=5.0
psycopg2-binary>=2.9
pgvector>=0.2
sqlalchemy>=2.0
pydantic>=2.7
pyyaml>=6.0
python-dotenv>=1.0
```

## Dashboard Dependencies (package.json)

```json
{
  "@mantine/core": "^8.3",
  "@mantine/hooks": "^8.3",
  "@xyflow/react": "^12",
  "react-leaflet": "^4",
  "leaflet": "^1.9",
  "react": "^18",
  "vite": "^5"
}
```

---

## LLM-Wiki Design Principles

| Layer | Contents | Mutability |
|-------|----------|------------|
| Raw sources | Incoming articles (PostgreSQL) | Immutable after ingest |
| Wiki | `wiki/**/*.md` — synthesized knowledge | LLM-updated on each ingest |
| Schema | `wiki/schema.md` | Human-controlled only |

- Citations required: `[Source: {outlet}, {date}]`
- `wiki/log.md` is append-only; every ingest adds a timestamped record of what changed
- Pages capped at ~300 lines; older content moves to archive section
- `[CONTRADICTION]` markers logged but never auto-overwritten — surfaced in WikiModal for human review
- Wiki context injected into every LLM call: top-3 excerpts by TF-IDF relevance to the article

---

## Seat Prediction: Signal → Confidence Flow

```
Articles tagged to constituency X
     │
     ▼ (analyst_agent runs 6 lenses per article)
Analysis rows in DB [political, demographic, historical,
                      strategic, factcheck, bridget_welsh]
     │
     ▼ (seat_agent aggregates)
SeatPrediction {
  leadingParty: "DAP",
  confidence: 74,           # 0–100
  signalBreakdown: {
    political:     { direction: "DAP", strength: 80, summary: "..." },
    demographic:   { direction: "DAP", strength: 70, summary: "..." },
    historical:    { direction: "DAP", strength: 85, summary: "..." },
    strategic:     { direction: "BN",  strength: 40, summary: "..." },
    factcheck:     { flags: 2,         summary: "2 unverified claims" },
    bridgetWelsh:  { direction: "DAP", strength: 65, summary: "..." }
  },
  caveats: ["Only 3 articles tagged", "BN candidate unannounced"]
}
     │
     ▼
ChoroplethLayer: fill=DAP blue, border=amber (74% = moderate confidence)
ConstituencyPopup: full breakdown table
```

---

## Claude Prompt Outlines

### Reliability Scorer (scorer_agent — JSON output)
System prompt instructs the LLM as a Malaysian media analyst. Defines source tiers:
- High: The Star, NST, FMT, Malaysiakini, Bernama, CNA
- Partial: Malay Mail, The Vibes, Malaysia Gazette
- Lower: anonymous blogs, social media reposts

Three scoring axes: source authority (40%), accuracy signals (35%), bias indicators (25%).
Response format: strict JSON `{ score, sourceAuthority, accuracySignals, biasIndicators, justification, flags }`.

### Multi-Perspective Analyser (analyst_agent — 6 lenses)
System prompt provides Johor political context: GRC/DUN system, BN UMNO dominance history, GE14/GE15/2022 state election outcomes, key voter themes, Iskandar Malaysia, JB-Singapore cross-border dynamics, Undi18.

Per-lens instructions:
- **Political** — coalition framing, how urban JB vs rural Johor voters would read it
- **Demographic** — Malay/Chinese/Indian, commuters, youth, Iskandar beneficiaries
- **Historical** — compare to GE12–GE15 and 2022 state election Johor trends
- **Strategic** — campaign tactics, which coalition benefits, mobilisation signals
- **Fact-check** — list claims, flag uncited statistics, identify SPR/DOSM data that would confirm/deny
- **Bridget Welsh** — apply Welsh's framework: electoral distortions, generational disaggregation, money politics, women's agency, voter-authenticity gap. Cite her Johor-specific works (`bridgetwelsh.com`).

### Seat Assessor (seat_agent — JSON output)
Given all lens signals for articles tagged to a constituency + wiki historical baseline, output `SeatPrediction` JSON (schema above). Include explicit caveats when article volume is low (<5 articles) or key information is missing (unannounced candidates, no recent polling data).

---

## Phases

### Phase 1 — Infrastructure and Control Plane (Days 1–2)
1. Set up monorepo: `control_plane/`, `agents/`, `dashboard/`, `wiki/`, `public/geojson/`
2. Implement `control_plane/` in full (server, registry, routes, task_store, pubsub, a2a_client, config) — port directly from mission-control-demo
3. Set up PostgreSQL via docker-compose; implement `TaskRecord` + `Article` + `Analysis` + `SeatPrediction` tables with SQLAlchemy
4. Create `agents/base/` — `LangGraphA2AExecutor`, `CancellableMixin`, `registration.py`, `build_a2a_app()`
5. Create `agents/base/llm.py` — OpenAI SDK → OpenRouter client + Anthropic fallback
6. Implement `run-local.sh` to start all services in order

**Verify:** Control plane starts on :8000. `GET /graph` returns empty topology. `GET /.well-known/agent-card.json` pattern works.

### Phase 2 — Wiki Seed and News Agent (Days 3–4)
1. Hand-author seed wiki pages (must precede LLM integration):
   - Party pages (BN/UMNO, DAP, PKR, Bersatu, Amanah, PAS)
   - `johor-political-landscape.md`, `ge14-ge15-johor.md`, `johor-state-election-2022.md`
   - `coalition-positions.md`, `jb-singapore-relations.md`, `iskandar-malaysia.md`
   - `wiki/schema.md` (rules), `wiki/index.md` and `wiki/log.md` stubs
2. Implement `wiki_agent` — `loader.py`, `retriever.py` (TF-IDF), ingest graph, lint graph; register with control plane
3. Implement `news_agent` — all scrapers, constituency tagger, LangGraph nodes, A2A server
4. Test: dispatch a scrape task via `POST /agents/news_agent/tasks`; articles appear in DB tagged with constituency codes

**Verify:** Agent graph shows `wiki_agent` + `news_agent`. Scrape task completes with `NODE_OUTPUT::` stream. DB has articles with `constituency_ids`.

### Phase 3 — Scorer and Analyst Agents (Days 5–7)
1. Implement `scorer_agent` — retrieves wiki context, LLM call with JSON output, stores score, emits wiki ingest task if score ≥ 60
2. Implement `analyst_agent` — 7-stage LangGraph pipeline for 6 lenses, streaming with `NODE_OUTPUT::` markers, DB caching
3. Wire the agent pipeline: score → wiki ingest → analyst (on demand)
4. Implement all 6 lens prompt files under `agents/analyst_agent/prompts/`; include Bridget Welsh framework

**Verify:** Scoring a test article returns structured JSON with score. Analyst tab streams lens-by-lens with node progress visible in task monitor. Wiki `log.md` updated.

### Phase 4 — Seat Agent (Days 8–9)
1. Implement `seat_agent` — gather signals, load wiki baseline, assess, store `SeatPrediction`
2. Auto-trigger after scorer completes: for each constituency in `article.constituency_ids`, dispatch seat assessment task (non-blocking)
3. Wire `constituency_tagger.py` so parlimen vs DUN seats are distinguished in tagging

**Verify:** After scoring an article tagged to P157, `seat_predictions` table has a new row. Confidence and signal breakdown populate correctly. Caveats fire when article count < 5.

### Phase 5 — Map (Days 10–11)
*GeoJSON/cartogram files already downloaded to `public/geojson/` from MECO (CC0). No sourcing needed.*
1. Build React + Vite + Mantine dashboard scaffold with cyberpunk theme (dark `#0a0a0f`, cyan `#00d4ff`)
2. Implement `ElectionMap.jsx` — React-Leaflet, CartoDB Dark Matter tiles, Johor bounds `[[1.2,102.9],[2.0,104.5]]`; loads the correct GeoJSON file based on both toggle axes
3. Implement `ChoroplethLayer.jsx` — fill by `leadingParty`, confidence ring border (green/amber/red)
4. Implement `CartogramLayer.jsx` — loads `johor_cartogram_electorate_2022.geojson` (DUN) or `johor_cartogram_parlimen_2022.geojson` (Parlimen); same fill/ring styling as choropleth
5. Implement `MapTypeToggle.jsx` — 2-axis toggle: [Parlimen | DUN] × [Choropleth | Cartogram]
6. Implement `ConstituencyPopup.jsx` with full 6-lens signal breakdown table and caveats
7. Implement `MapLegend.jsx` — includes cartogram note when cartogram mode is active

**Verify:** Map renders Johor, constituencies coloured by predicted party with confidence rings. All 4 toggle combinations load the correct file and render correctly. Popup shows seat prediction with signal breakdown.

### Phase 6 — Dashboard Integration (Days 12–13)
1. Implement `NewsFeedPanel`, `ArticleCard`, `ReliabilityBadge` — connected to control plane via `useApi.js`
2. Implement `AnalysisPanel` with 6 lens tabs and streaming display
3. Implement `AgentGraph.jsx` (bottom panel) — `@xyflow/react` topology pulled from `GET /graph`, real-time health status
4. Implement `TaskMonitor.jsx` — WebSocket `ws://localhost:8000/ws/tasks/{task_id}` showing live `NODE_OUTPUT::` events
5. Implement `WikiModal.jsx` and `WikiContextBadge.jsx`
6. Wire `TopBar`: scrape trigger, map toggle, wiki button, status indicator (LIVE/STALE)
7. Wire cross-panel interactions: article click → trigger score task → show analysis; constituency click → popup

**Verify:** Full user journey — article selected → score streams → wiki ingest fires → analysis tabs populate → map updates → popup shows prediction. Agent graph shows all 5 agents healthy.

### Phase 7 — Polish and Deployment (Day 14)
1. `docker-compose.yml` — PostgreSQL, Redis, all 5 agents + control plane + dashboard with health checks
2. Error handling: each agent returns structured error in A2A response; dashboard shows agent-specific error states
3. Retry logic (3 attempts, exponential backoff) on all A2A calls — already in `LangGraphA2AExecutor`
4. Rate limiting: 10 LLM calls/min per agent via token bucket in `agents/base/llm.py`
5. Seed script: populate constituency metadata so map is never blank on cold start
6. `.env.template` with all required vars documented

**Verify:** `docker compose up` brings full stack. All 5 agents register. Scrape → score → analyse → seat predict pipeline completes end-to-end. Agent graph shows healthy topology.

---

## Map Data — MECO (Resolved)

**Source:** [Thevesh/paper-meco-maps](https://github.com/Thevesh/paper-meco-maps) — Thevananthan & Chacko (2025), arXiv:2512.24211. **License: CC0 (public domain).**

All files pre-downloaded and committed to `public/geojson/`:

| File | Features | Properties | Notes |
|------|----------|------------|-------|
| `johor-parlimen.geojson` | 26 | `state`, `parlimen`, `code_parlimen` | 2018 delimitation |
| `johor-dun.geojson` | 56 | + `dun`, `code_dun` | 2018 delimitation |
| `johor_cartogram_electorate_2022.geojson` | 56 | + `voters_total` | Electorate-weighted DUN cartogram |
| `johor_cartogram_equal_2022.geojson` | 56 | same as DUN | Equal-area DUN cartogram |
| `johor_cartogram_parlimen_2022.geojson` | 26 | `state`, `parlimen`, `code_parlimen` | Dissolved from DUN electorate cartogram |

**Parlimen codes:** P.140–P.165 (Johor). **DUN codes:** N.01–N.56.

---

## Verification Checklist

| Phase | Check |
|-------|-------|
| 1 | Control plane on :8000. `GET /graph` returns `{nodes:[], edges:[]}`. Base executor importable. |
| 2 | `GET /graph` shows 2 agent nodes. Scrape task dispatched + completed. Articles in DB with `constituency_ids`. Wiki `log.md` writable. |
| 3 | Score task returns JSON with numeric score. Analyst streams 7 `NODE_OUTPUT::` events. 6 lens rows in `analyses` table. `log.md` updated. |
| 4 | `seat_predictions` row created after scoring an article. Signal breakdown has 6 entries. Caveats present for low-data seats. |
| 5 | Map renders Johor. Fill by predicted party. Confidence rings visible. All 4 toggle combinations (Parlimen/DUN × Choropleth/Cartogram) load and render correctly. Popup shows signal breakdown. |
| 6 | Article click triggers score WebSocket stream visible in TaskMonitor. All 5 agents shown in AgentGraph. Wiki context badge shows sourced pages. |
| 7 | `docker compose up` succeeds. All agents self-register within 10s. End-to-end pipeline completes. Rate limit returns 429. |

**Critical path (start Day 1 in parallel):**
1. **GeoJSON sourcing** — RESOLVED. All 5 files downloaded from MECO (CC0) to `public/geojson/`. No external dependencies.
2. **Wiki seed content** — RESOLVED. 15 seed pages written to `wiki/`. Quality of all downstream LLM analysis depends on this baseline.
