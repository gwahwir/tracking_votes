# Johor Election Monitor — Architecture Reference

## GeoJSON Files (`public/geojson/`)

| File | Features | Key Properties |
|------|----------|----------------|
| `johor-parlimen.geojson` | 26 Parlimen seats | `state`, `parlimen`, `code_parlimen` |
| `johor-dun.geojson` | 56 DUN seats | `state`, `parlimen`, `code_parlimen`, `dun`, `code_dun` |
| `johor_cartogram_electorate_2022.geojson` | 56 DUN seats (electorate-weighted) | + `voters_total` |
| `johor_cartogram_equal_2022.geojson` | 56 DUN seats (equal-area) | same as DUN |
| `johor_cartogram_parlimen_2022.geojson` | 26 Parlimen seats (cartogram) | `state`, `parlimen`, `code_parlimen` |

Parlimen codes: P.140–P.165. DUN codes: N.01–N.56.
Source: [Thevesh/paper-meco-maps](https://github.com/Thevesh/paper-meco-maps), CC0 licence.

---

## API Endpoints

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

---

## Database Access

```bash
# Connect to PostgreSQL (Docker)
docker exec -it tracking_votes-postgres-1 psql -U johor -d johor_elections

# List tables
\dt

# Query articles
SELECT id, title, reliability_score FROM articles LIMIT 5;

# Query predictions
SELECT constituency_code, leading_party, confidence FROM seat_predictions;
```

Tables: `articles`, `analyses`, `seat_predictions`, `registered_agents`, `tasks`

---

## Key Decisions

1. **FastAPI + LangGraph** — async-first, A2A protocol; modelled on mission-control-demo
2. **PostgreSQL + asyncpg** — persistent storage, pgvector support, async driver
3. **OpenRouter primary + Anthropic fallback** — flexible LLM provider; fallback triggered on RateLimitError or APIStatusError
4. **MECO maps (CC0)** — public domain GeoJSON, no licensing issues, includes pre-built cartograms
5. **Bridget Welsh lens** — analyst_agent sixth lens applies Welsh's electoral framework specific to Malaysian elections (generational disaggregation, money politics, voter-authenticity gap)
6. **Cartogram visualisation** — shows electoral distortion (malapportionment) alongside standard choropleth; electorate-weighted variant highlights seats-per-capita inequality
7. **In-memory vs PostgreSQL task store** — code supports both; in-memory for dev, Postgres for prod (controlled via `DATABASE_URL`)
8. **Agent health check** — currently loose (agents functional but registry may show unhealthy); acceptable for MVP, cosmetic fix pending
