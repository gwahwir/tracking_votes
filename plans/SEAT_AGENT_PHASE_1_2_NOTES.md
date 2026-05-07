# Seat Agent Phase 1+2 — Implementation Notes

Landed 2026-05-07. This file documents what shipped, what's still required to fully realize the value, and what was deliberately deferred.

## What shipped

### Phase 1 — Direction Normalization

Problem: the seat agent's `signal_breakdown` was showing analyst-lens vocabulary (e.g. `BN_dominance_restore`, `Malay`, `Urban+Youth`) in the `direction` field, where the dashboard expected a party name (`BN`/`PH`/`PN`). Caused by `_summarise_signals` passing the raw analyst direction straight through to the seat LLM, which then echoed it into the output.

Fix:

- `_summarise_signals` in [agents/seat_agent/graph.py](../agents/seat_agent/graph.py) now emits `{label, strength, article_count}` instead of `{direction, strength}`. The `label` is the raw lens vocabulary; the LLM is responsible for normalizing.
- The seat assess prompt has a new **Direction Normalization Rules** section that maps every non-party label to a party (or null).
- `signal_breakdown[lens]` output schema now has both `direction` (party: BN/PH/PN/null) and `label` (raw lens vocabulary preserved).
- The canonical [agents/seat_agent/prompts/seat_assessment.txt](../agents/seat_agent/prompts/seat_assessment.txt) was updated to match.
- Dashboard [SeatDetailPanel.jsx](../dashboard/src/components/seats/SeatDetailPanel.jsx) renders `direction` (party-colored, primary) with `label` on a small grey second line below — preserves bar alignment across rows.

Backwards compatibility: old prediction rows (only `direction`, no `label`) render via fallback; nothing breaks.

### Phase 2 — Evidence Quality

Problem: confidence scores were vibes-based. A seat backed by 1 partisan article looked the same as 8 reliable ones.

Fix:

- New `evidence_quality` JSON column on `seat_predictions` table. Migration is idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` in **both**:
  - [control_plane/db.py](../control_plane/db.py) — SQLAlchemy `init_database`
  - [control_plane/task_store.py](../control_plane/task_store.py) — asyncpg `_CREATE_TABLES_SQL`
- New `_compute_evidence_quality()` helper in [agents/seat_agent/graph.py](../agents/seat_agent/graph.py) — pure aggregation, no LLM.
- Fields: `specific_article_count`, `state_article_count`, `avg_reliability`, `high/low_reliability_count`, `recency`, `source_diversity`, `scorer_flags`, `lens_coverage`, `agreement` (per-lens fraction agreeing with the leading direction).
- Seat assess prompt has a new **Confidence Calibration Rules** section. Lowest cap wins:
  - `avg_reliability < 50` -> cap 60
  - `specific_article_count < 5` -> cap 50
  - `agreement < 0.5` on dominant journalism lens -> cap 65
  - `source_diversity.count == 1` -> cap 55 (single-source bias risk)
  - `scorer_flags` includes "partisan_framing" or similar -> -5
- Dashboard shows new EVIDENCE section in OVERVIEW tab.
- API endpoints `/seat-predictions` and `/seat-predictions/{code}` return `evidence_quality`.

Backwards compatibility: old rows have `evidence_quality = NULL`; UI hides the section gracefully.

### Verification

- N.01 Buloh Kasap re-scored: confidence went from 0/Unclear to 48/BN, capped by sparse-evidence rules (1 specific article, 1 source).
- `historical.direction = "BN"`, `historical.label = "BN_dominance_restore"`.
- `evidence_quality` populated with all fields.

## What's left

### Re-score existing seats

Most existing `seat_predictions` rows still have:
- `direction = "BN_dominance_restore"` (or similar raw label) — renders via fallback but inconsistent with new seats
- `evidence_quality = NULL` — confidence not calibrated by the new rules

The dashboard handles both cases gracefully, but the new calibration rules only kick in when a seat is re-scored.

**Options:**

1. **Per-Score click** (status quo) — re-scoring happens organically as users click Score. Slow but no risk.
2. **Bulk admin script** — loop all constituencies, POST `/agents/seat_agent/tasks` with debounce-aware rate limiting (5-min debounce per seat already enforced server-side). Run overnight if doing all 82 seats.

The right time to do bulk re-scoring is when there's enough fresh article data that re-running adds value, not just when the schema changes.

### Other potential improvements (not started)

- **Schema source of truth** — currently `models.py` (SQLAlchemy) and `task_store.py` (asyncpg DDL) both define table schemas. Adding a column requires updating both. Worth consolidating before the next schema change. See Phase E (Alembic migrations) in [PHASE_E_POLISH_DEPLOYMENT.md](PHASE_E_POLISH_DEPLOYMENT.md).
- **Inline assess prompt vs. canonical template file** — [agents/seat_agent/graph.py](../agents/seat_agent/graph.py) builds the assess prompt inline; [seat_assessment.txt](../agents/seat_agent/prompts/seat_assessment.txt) is a parallel canonical template. Both were updated to match, but they're not enforced to stay in sync. Worth either consolidating or adding a test.

## Phase 3 — Deferred

**Goal:** surface narrative texture from the analyst lenses (top article summaries per lens, `community_breakdown` aggregation, `welsh_dimensions` union, `tactical_implication` collation, `analogous_events`, factcheck flags).

**Why deferred:**
- ~2-3x token cost increase on the assess LLM call
- Marginal value — the seat LLM already has aggregated direction + strength + evidence_quality
- Should only be undertaken if Phase 1+2 confidence calibration proves insufficient with broader use
- Aggregation logic is non-trivial (`community_breakdown` synthesis across N articles needs heuristic or LLM call)

**When to revisit:**
- If users frequently complain that seat predictions feel ungrounded despite high confidence
- If post-election backtest shows confidence is poorly calibrated even with Phase 2 rules
- If the "rationale" field of predictions is too generic to be useful for debugging

**Outline of approach** (if revisited): see the conversation context that produced this — the plan is to add a `synthesise_signals` node between `gather_signals` and `assess` that pulls top 3 articles per lens by reliability, extracts lens-specific richness from `Analysis.full_result`, and aggregates per-community sentiment heuristically.
