# Handoff Notes — Apr 30 Evening

## Where we left off

Working on fixing LLM lens timeouts in the analyst agent. The analyst runs 6 lenses per article. Currently 4 of 6 complete — `factcheck` and `bridget_welsh` (the last batch) time out consistently.

**Test article used:** "Biro Politik BN-PH akan bincang calon MB N Sembilan, kata Adun Umno"

---

## What was fixed this session

### 1. Signal breakdown bar alignment (DONE)
`dashboard/src/components/seats/SeatDetailPanel.jsx` — direction label now always renders even when null, so bars align.

### 2. Factcheck display component (DONE)
`dashboard/src/components/analysis/AnalysisPanel.jsx` — added `FactcheckContent` component that renders `verified_claims`, `unverified_claims`, `false_or_misleading`, `flags`, `summary` from `data.full`. Tab renderer uses it when `lens.id === 'factcheck'`.

### 3. Factcheck prompt returning wrapped JSON (DONE)
- `agents/analyst_agent/prompts/factcheck.txt` — explicit "no wrapper" JSON instruction
- `agents/analyst_agent/prompts/system.txt` — added Output Format section: no wrapper keys, no chain-of-thought in JSON, empty lists not null

### 4. LLM timeout fixes (PARTIALLY DONE — still timing out)
Changes made:
- `agents/analyst_agent/graph.py` — lenses now run in batches of 2 (was all 6 at once via `asyncio.gather`)
- `agents/analyst_agent/graph.py` — per-lens `asyncio.wait_for` timeout: 60s → 180s
- `agents/analyst_agent/graph.py` — removed inner retry loop in `_call_lens` (retries were consuming the timeout budget)
- `agents/base/llm.py` — AsyncOpenAI client timeout: 50s → 150s
- `agents/base/llm.py` — `max_attempts`: 3 → 2

**Still failing:** `factcheck` and `bridget_welsh` are always the last batch and still time out. The analyst task completes after ~2 minutes with only 4 lenses persisted.

---

## Next thing to investigate

The lens batch order in `_LENS_PROMPTS` (in `agents/analyst_agent/graph.py`) is: `political, demographic, historical, strategic, factcheck, bridget_welsh`. The last batch is always `factcheck + bridget_welsh`.

Possible causes:
1. **OpenRouter rate limiting** — 4 rapid LLM calls in batches 1+2 exhaust the rate limit, batch 3 gets throttled
2. **API slowness** — OpenRouter just slow at that moment; 150s client timeout still not enough
3. **Prompt size** — bridget_welsh and factcheck prompts may be larger, taking longer

**Suggested next steps:**
- Try fully sequential execution (1 lens at a time) to eliminate rate limit as cause — just change the batch size from 2 to 1 in `graph.py`
- Or check OpenRouter dashboard for rate limit hits
- Or reorder `_LENS_PROMPTS` so factcheck + bridget_welsh run first, to see if it's purely a position/timing issue

---

## DB reset command (for re-testing)
```sql
DELETE FROM analyses an USING articles a WHERE an.article_id = a.id AND a.title ILIKE '%Biro Politik%';
UPDATE articles SET reliability_score = NULL WHERE title ILIKE '%Biro Politik%';
```
Run via: `docker compose exec postgres psql -U johor -d johor_elections -c "<sql>"`

---

## Nothing pushed to GitHub yet
All changes from today's sessions are local only.
