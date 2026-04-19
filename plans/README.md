# Implementation Plans — Election Monitor

These plans are self-contained, detailed implementation guides designed to be handed to a Claude Sonnet instance for execution. Each phase builds on the previous one.

## Phase Sequence

| Phase | Plan | Summary | Dependencies |
|-------|------|---------|-------------|
| **A** | [PHASE_A_HISTORICAL_DATA.md](PHASE_A_HISTORICAL_DATA.md) | Compile and ingest historical election results (56 DUN + 26 Parlimen seats x 3 elections), create constituency wiki pages, wire real baselines into the seat_agent | None |
| **B** | [PHASE_B_AGENT_CALIBRATION.md](PHASE_B_AGENT_CALIBRATION.md) | Wire auto-chaining (news -> scorer -> analyst -> seat), add debouncing, enrich seat_agent prompts with historical context, backtest against 2022 results | Phase A |
| **C** | [PHASE_C_DASHBOARD_ENHANCEMENTS.md](PHASE_C_DASHBOARD_ENHANCEMENTS.md) | Add SeatDetailPanel with history/demographics/articles tabs, scoreboard, hover tooltips comparing 2022 vs current, swing indicators | Phases A, B |
| **D** | [PHASE_D_GE_EXTENSION.md](PHASE_D_GE_EXTENSION.md) | Generalize from Johor-only to all states + General Election: data-driven tagger, election scopes, state selector, national map, scope-filtered APIs | Phases A-C |
| **E** | [PHASE_E_POLISH_DEPLOYMENT.md](PHASE_E_POLISH_DEPLOYMENT.md) | Production hardening: retry/rate limiting, authentication, Alembic migrations, CI/CD, production Docker, periodic scraping, observability | Phases A-D |

## How to Use These Plans

Each plan is structured for a Claude Sonnet instance to execute independently:

1. **Context section** — Describes what exists today, with exact file paths and line numbers
2. **Implementation steps** — Ordered steps with code snippets showing the pattern to follow
3. **Files to create/modify** — Complete list of affected files
4. **Verification** — Concrete checks to confirm the phase is working

### Giving a plan to Claude

Point Claude at the specific phase file and the project root:

```
Read plans/PHASE_A_HISTORICAL_DATA.md and implement it in the tracking_votes project.
Start with Step 1 and work through each step sequentially.
```

### Important Notes

- **Phase A is the critical path** — without historical data, the system produces ungrounded predictions
- **Phases can be partially parallelized:** Phase C (dashboard) frontend work can start while Phase B (calibration) backend work is in progress
- **Phase D is the largest scope change** — it touches nearly every file. Consider doing it incrementally (one state at a time)
- **Phase E can start early** for non-blocking items like CI/CD and `.env.template`

## Architecture Reference

```
Dashboard (React + Vite + Mantine)
    ↕ HTTP/WebSocket
Control Plane (FastAPI :8000)
    ↕ JSON-RPC 2.0 / SSE
┌───────────────────────────────────────────────┐
│  news_agent :8001 → scorer_agent :8002        │
│                     → analyst_agent :8003      │
│                       → seat_agent :8004       │
│  wiki_agent :8005 (triggered by scorer)       │
└───────────────────────────────────────────────┘
    ↕ PostgreSQL + Redis
Infrastructure (Docker Compose)
```

## Current State (as of 2026-04-20)

- Phases 1-6 of original plan mostly complete
- 5 LangGraph agents operational
- Dashboard with choropleth map, news feed, analysis panel
- GeoJSON for all Malaysian states available
- Wiki with 15 pages (parties, concepts, no constituency pages yet)
- Auto-chaining: news -> scorer only (scorer -> analyst -> seat not wired)
- seat_agent `load_baseline` returns mock data (empty dicts)
