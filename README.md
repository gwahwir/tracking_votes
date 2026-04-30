# Tracking Votes

A Johor state election monitoring dashboard. Scrapes Malaysian news from five outlets, scores each article for source reliability, runs multi-perspective political analysis through six analytical lenses, and produces per-constituency win-likelihood predictions — all displayed on a live, map-driven dashboard.

> For setup on a new machine, see [SETUP.md](SETUP.md).

---

## What it does

The system continuously ingests news about the Johor election, processes each article through a four-stage AI pipeline, and surfaces the results as a live dashboard with a choropleth map, article feed, and per-constituency analysis panels.

The three coalitions tracked are **Barisan Nasional (BN/UMNO)**, **Pakatan Harapan (PH)**, and **Perikatan Nasional (PN)** across all 26 federal parliament seats (P.140–P.165) and 56 state DUN seats (N.01–N.56).

---

## Architecture

```
News (5 sources)
    ↓
[news_agent]      — scrape → filter → tag → store
    ↓
[scorer_agent]    — reliability score (0–100)
    ↓  (score ≥ 60)
[wiki_agent]      — extract facts → update knowledge base
    ↓
[analyst_agent]   — 6-lens analysis per article
    ↓
[seat_agent]      — aggregate signals → win-likelihood per constituency
    ↓
Dashboard         — map, news feed, analysis panels, predictions
```

A **control plane** (FastAPI, port 8000) sits in the middle: it registers agents, dispatches tasks, streams real-time node output via WebSocket, and exposes REST endpoints for the dashboard.

---

## Services

| Service | Host port | Role |
|---|---|---|
| Dashboard (React/Vite/Mantine) | 5175 | UI |
| Control plane (FastAPI) | 8000 | Orchestration, API, WebSocket |
| PostgreSQL (pgvector) | 5434 | Persistent storage |
| Redis | 7379 | Task queue + pub/sub |
| news_agent | 9001 | News scraping |
| scorer_agent | 9002 | Reliability scoring |
| analyst_agent | 7003 | 6-lens analysis |
| seat_agent | 9004 | Seat predictions |
| wiki_agent | 7005 | Knowledge base updates |

---

## Pipeline stages

### Stage 1 — News scraping (news_agent)

Runs automatically every 30 minutes (or on demand via the Scrape button).

**Sources:** TheStarOnline, Free Malaysia Today, Malaysiakini, CNA, NewsAPI

**Nodes:**
1. **fetch** — Concurrent RSS/HTTP scrape of all five sources; returns raw article list
2. **filter** — LLM classifies each article for Johor election relevance; falls back to keyword matching on ~30 Johor-specific terms if LLM is unavailable
3. **tag** — LLM + keyword matcher identifies which constituencies (P.140–P.165, N.01–N.56) each article mentions; stores as JSON list on the article
4. **upsert** — Deduplicates by URL and writes to the `articles` table

---

### Stage 2 — Reliability scoring (scorer_agent)

Triggered manually via the Score button, or automatically after scraping.

Each article is scored 0–100 across three weighted axes:

| Axis | Weight | What it measures |
|---|---|---|
| Source authority | 40% | Outlet tier — Bernama/Star/FMT/Malaysiakini/CNA are Tier 1; blogs and unattributed releases are Tier 3 |
| Accuracy signals | 35% | Named sources, verifiable statistics, datelines, corroboration; penalises unverified claims and missing context |
| Bias indicators | 25% | Coalition framing in headlines, loaded language, missing opposing response, inconsistency with SPR rules |

**Formula:** `score = (sourceAuthority × 0.40) + (accuracySignals × 0.35) + (biasIndicators × 0.25)`

**Score thresholds:**

| Range | Meaning | Downstream effect |
|---|---|---|
| 80–100 | Trustworthy — Tier-1 outlet, named sources, balanced | Feeds wiki ingest |
| 60–79 | Generally reliable — minor bias or partial authority | Feeds wiki ingest |
| 40–59 | Caution — lower-tier outlet or notable accuracy gaps | Used only as state-level baseline in seat predictions |
| 0–39 | Unreliable — anonymous, speculative, or false claims | Stored but excluded from predictions |

**Nodes:**
1. **retrieve_wiki** — TF-IDF match against the knowledge base; fetches top-3 relevant excerpts as grounding context for the LLM
2. **score** — LLM evaluates the three axes and returns a structured JSON breakdown
3. **store** — Persists score and breakdown to `articles`; if score ≥ 60, triggers wiki_agent ingest automatically

---

### Stage 3 — Multi-lens analysis (analyst_agent)

Triggered when an article is selected for analysis (or automatically after scoring completes).

Six analytical lenses run in parallel, each producing a directional signal and strength score for the article.

**Output per lens:** `{ direction: "BN" | "PH" | "PN" | "mixed", strength: 0–100, summary: "..." }`

| Lens | What it analyses |
|---|---|
| **Political** | Coalition narrative, urban vs. rural implications, three-way competitive dynamics, seat-specific implications |
| **Demographic** | Which demographic group (Malay, Chinese, Indian, urban/rural) is addressed; signal strength for that group |
| **Historical** | Compares the article's signal to GE14/GE15/2022 state results; identifies alignment or divergence with historical swing patterns |
| **Strategic** | Campaign positioning, party strategy signals, ground mobilisation, long-term coalition viability |
| **Fact-check** | Verifies claims against the wiki (SPR boundaries, historical results); flags unverified statistics or contradictions |
| **Bridget Welsh** | Expert-analyst perspective on Johor electoral dynamics — coalition fragility, swing voter behaviour, regional volatility |

**Direction semantics:**
- **BN** — UMNO machinery strength, Malay voter consolidation, incumbent advantage
- **PH** — DAP urban dominance, PKR mixed-seat recovery, anti-incumbent sentiment
- **PN** — Malay voter fragmentation from BN, Bersatu/PAS local organising
- **mixed** — Cross-cutting implications (e.g. DAP strong in JB urban, UMNO dominant in rural Johor)

**Strength 0–100:**
- 0–33: Weak signal — few articles, contradictory lenses
- 34–66: Moderate — multiple articles, partial lens agreement
- 67–100: Strong — consistent across lenses, high-reliability sources

**Nodes:**
1. **retrieve_wiki** — Fetches 4 wiki excerpts: electoral structure, constituency demographics, historical results, key figures
2. **run_lenses** — 6 concurrent LLM calls (GPT-4o via OpenRouter, temperature 0.3), each returning strict JSON
3. **chain_to_seat** — Dispatches seat_agent tasks for all constituencies tagged on the article

---

### Stage 4 — Seat predictions (seat_agent)

Triggered automatically by analyst_agent, or manually per constituency. Same constituency requests within 5 minutes return a cached result.

**Nodes:**
1. **gather_signals** — Fetches all 6-lens analyses for articles tagged to this constituency (up to 100), plus state-level Johor articles with score ≥ 40 as a baseline (up to 50)
2. **load_baseline** — Loads historical results (GE14/GE15/2022 state) and demographic profile for the constituency
3. **assess** — LLM aggregates lens signals + historical baseline into a SeatPrediction with leading party, confidence, per-lens breakdown, and caveats
4. **store** — Persists prediction to `seat_predictions`; latest prediction per constituency overwrites the previous

**Confidence interpretation:**

| Range | Meaning |
|---|---|
| 70–100 | High — 5+ constituency-specific articles, 4–6 lenses agree, historical baseline aligned |
| 40–69 | Moderate — 2–4 articles, mixed lens signals, or light baseline divergence |
| 0–39 | Low — sparse coverage, early-stage prediction based mainly on historical baseline |

**Example caveats:** "Only 1 article found — prediction based on historical baseline only", "Candidate unannounced — demographic signals may shift post-announcement", "State-level only — no constituency-specific coverage"

---

### Stage 5 — Wiki ingest (wiki_agent)

Triggered automatically when scorer_agent produces a score ≥ 60.

The wiki is a Markdown knowledge base under `wiki/` covering Johor constituency data, historical election results, party profiles, and key figures. It is mounted as a live volume into the wiki_agent container.

**Nodes:**
1. **retrieve_wiki** — TF-IDF match to find the most relevant existing pages for the new article
2. **update_pages** — LLM extracts verifiable facts from the article and appends them to the appropriate wiki pages
3. **write_updates** — Persists changes; logs the update to `wiki/log.md`

The wiki also powers the **retrieve_wiki** node in scorer_agent and analyst_agent — it is both a product of the pipeline and an input to it, growing more useful as more high-reliability articles are ingested.

---

## Knowledge base (wiki)

```
wiki/
  concepts/
    johor-political-landscape.md
    johor-state-election-2022.md
    ge14-ge15-johor.md
    iskandar-malaysia.md
    jb-singapore-relations.md
  entities/
    parties/
      bn-umno.md, dap.md, pkr.md, bersatu.md, amanah.md, pas.md
    constituencies/
      parlimen/   p-140-segamat.md … p-165-*.md  (26 files)
      dun/        n01-buloh-kasap.md … n56-*.md   (56 files)
  comparisons/
    coalition-positions.md
  log.md          (append-only ingest history)
```

---

## Database schema

| Table | Key columns |
|---|---|
| `articles` | id, url (unique), title, source, content, constituency_ids (JSON), reliability_score, score_breakdown (JSON), scraped_at |
| `analyses` | id, article_id, lens_name, direction, strength, summary, full_result (JSON) |
| `seat_predictions` | id, constituency_code (unique), leading_party, confidence, signal_breakdown (JSON), caveats (JSON), num_articles, num_state_articles |
| `historical_results` | constituency_code, election_year, winner_party, margin_pct, turnout_pct, candidates (JSON) |
| `constituency_demographics` | constituency_code, malay_pct, chinese_pct, indian_pct, urban_rural, region |
| `registered_agents` | name, type_id, url, is_healthy, last_seen |

---

## Dashboard

The React/Vite/Mantine frontend at **http://localhost:5175** has:

- **Choropleth map** — constituencies colour-coded by leading party; click a seat to open its detail panel
- **Scoreboard** — live BN/PH/PN seat counts vs. majority line
- **News feed** — articles sorted by date with reliability badges (green ≥ 80, yellow 60–79, red < 60)
- **Analysis panel** — 6-lens breakdown for the selected article, with per-lens direction, strength, and summary
- **Seat detail panel** — historical results table, demographics, article count, GE15 baseline, and latest prediction with caveats
- **Agent monitor** — real-time NODE_OUTPUT streaming for running tasks (LangGraph node timings)

**User actions:**
- **Scrape** — triggers news_agent immediately
- **Score** (on article) — runs scorer_agent → analyst_agent → seat_agent for tagged constituencies
- **Refresh seat** (on constituency panel) — re-runs seat_agent (5-minute debounce)

All task output streams live via WebSocket — no polling required.

---

## LLM stack

| Component | Model | Why |
|---|---|---|
| filter (news_agent) | GPT-4o-mini via OpenRouter | Fast, cheap; binary relevance decision |
| score (scorer_agent) | GPT-4o via OpenRouter | Structured JSON reasoning over three axes |
| run_lenses (analyst_agent) | GPT-4o via OpenRouter | 6 concurrent calls; needs reasoning depth |
| assess (seat_agent) | GPT-4o via OpenRouter | Complex signal aggregation |
| Fallback (all agents) | Anthropic Claude | Resilience if OpenRouter is unavailable |

Temperature: 0.3 across all analytical calls. Retry: 2 attempts on JSON parse failure.

---

## Tech stack

- **Backend:** FastAPI, LangGraph, LangChain, asyncpg, structlog
- **LLM routing:** OpenRouter (OpenAI-compatible), Anthropic
- **Database:** PostgreSQL 16 + pgvector
- **Queue / pub-sub:** Redis 7
- **Frontend:** React 18, Vite, Mantine v8, react-leaflet
- **Deployment:** Docker Compose (9 services)
- **Observability:** Langfuse tracing (wired into executor and LLM calls)
