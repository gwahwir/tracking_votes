"""Seat agent 4-node LangGraph pipeline."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base.llm import llm_call_with_fallback
from agents.base.models import Analysis, Article, ConstituencyDemographics, HistoricalResult, SeatPrediction
from control_plane.db import get_session_maker

log = structlog.get_logger(__name__)


def _extract_analyses(articles, analyses_map: dict) -> dict:
    """Aggregate lens analyses from a list of articles into signal buckets."""
    signals = {"political": [], "demographic": [], "historical": [], "strategic": [], "factcheck": [], "bridget_welsh": [], "social_signal": []}
    for article in articles:
        for analysis in analyses_map.get(article.id, []):
            lens = analysis.lens_name
            if lens in signals:
                signals[lens].append({
                    "article_id": article.id,
                    "source": article.source,
                    "direction": analysis.direction,
                    "strength": analysis.strength,
                    "summary": analysis.summary,
                })
    return signals


def _compute_evidence_quality(specific_articles, state_articles, signals: dict, state_signals: dict) -> dict:
    """Compute evidence quality metrics from articles + per-lens signals.

    Used by the assess node to calibrate confidence — see the calibration rules in the prompt.
    Pure aggregation, no LLM.
    """
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    all_articles = list(specific_articles) + list(state_articles)

    reliabilities = [a.reliability_score for a in all_articles if a.reliability_score is not None]
    avg_reliability = sum(reliabilities) / len(reliabilities) if reliabilities else None
    high_count = sum(1 for r in reliabilities if r >= 75)
    low_count = sum(1 for r in reliabilities if r < 40)

    def _aware(dt):
        if dt is None:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    last_7 = sum(1 for a in all_articles if _aware(a.scraped_at) and _aware(a.scraped_at) >= seven_days_ago)
    last_30 = sum(1 for a in all_articles if _aware(a.scraped_at) and _aware(a.scraped_at) >= thirty_days_ago)
    older = max(0, len(all_articles) - last_30)

    sources = sorted({a.source for a in all_articles if a.source})

    flag_counter: dict = {}
    for a in all_articles:
        for flag in (a.score_flags or []):
            flag_counter[flag] = flag_counter.get(flag, 0) + 1
    top_flags = sorted(flag_counter.items(), key=lambda x: -x[1])[:5]

    combined = {lens: list(signals.get(lens, [])) + list(state_signals.get(lens, [])) for lens in signals}
    lens_coverage = {lens: len(items) for lens, items in combined.items()}

    agreement = {}
    for lens, items in combined.items():
        directions = [it.get("direction") for it in items if it.get("direction")]
        if not directions:
            agreement[lens] = None
            continue
        leading = max(set(directions), key=directions.count)
        agreement[lens] = round(directions.count(leading) / len(directions), 2)

    return {
        "specific_article_count": len(specific_articles),
        "state_article_count": len(state_articles),
        "avg_reliability": round(avg_reliability, 1) if avg_reliability is not None else None,
        "high_reliability_count": high_count,
        "low_reliability_count": low_count,
        "recency": {"last_7_days": last_7, "last_30_days": last_30, "older": older},
        "source_diversity": {"count": len(sources), "sources": sources},
        "scorer_flags": [{"flag": f, "count": c} for f, c in top_flags],
        "lens_coverage": lens_coverage,
        "agreement": agreement,
    }


async def gather_signals(state: dict) -> dict:
    """Gather multi-lens analysis signals for the constituency.

    Produces two buckets:
    - signals: from articles specifically tagged to this constituency
    - state_signals: from Johor-wide articles (no specific constituency tag)
    Both are passed to assess so the LLM has full context.
    """
    constituency_code = state.get("constituency_code")
    if not constituency_code:
        state["error"] = "No constituency_code provided"
        return state

    log.info("seat.gather_signals", constituency_code=constituency_code)

    session_maker = get_session_maker()
    if not session_maker:
        state["error"] = "Database not initialized"
        return state

    empty_signals = {"political": [], "demographic": [], "historical": [], "strategic": [], "factcheck": [], "bridget_welsh": [], "social_signal": []}

    try:
        async with session_maker() as session:
            # Bucket 1: articles specifically tagged to this constituency
            stmt_specific = select(Article).where(
                Article.constituency_ids.contains([constituency_code])
            ).order_by(Article.scraped_at.desc()).limit(100)
            result_specific = await session.execute(stmt_specific)
            specific_articles = result_specific.scalars().all()

            # Bucket 2: state-level articles — Johor-relevant, scored, but no constituency tag
            stmt_state = select(Article).where(
                Article.constituency_ids == [],
                Article.reliability_score >= 40,
            ).order_by(Article.scraped_at.desc()).limit(50)
            result_state = await session.execute(stmt_state)
            state_articles = result_state.scalars().all()

            # Fetch all analyses in one query per article set
            all_article_ids = [a.id for a in specific_articles] + [a.id for a in state_articles]
            analyses_map: dict = {}
            if all_article_ids:
                from sqlalchemy import func, or_, text
                stmt_analyses = select(Analysis).where(
                    Analysis.article_id.in_(all_article_ids),
                    or_(
                        Analysis.lens_name != "social_signal",
                        Analysis.created_at > func.now() - text("INTERVAL '14 days'"),
                    ),
                )
                result_analyses = await session.execute(stmt_analyses)
                for analysis in result_analyses.scalars().all():
                    analyses_map.setdefault(analysis.article_id, []).append(analysis)

            signals = _extract_analyses(specific_articles, analyses_map)
            state_signals = _extract_analyses(state_articles, analyses_map)
            evidence_quality = _compute_evidence_quality(
                specific_articles, state_articles, signals, state_signals
            )

            state["num_articles"] = len(specific_articles)
            state["num_state_articles"] = len(state_articles)
            state["signals"] = signals
            state["state_signals"] = state_signals
            state["evidence_quality"] = evidence_quality
            state["caveats"] = []

            if not specific_articles and not state_articles:
                state["caveats"].append("No articles found — prediction based on historical baseline only")
            elif not specific_articles:
                state["caveats"].append(f"No constituency-specific articles — using {len(state_articles)} state-level articles only")
            elif len(specific_articles) < 5:
                state["caveats"].append(f"Only {len(specific_articles)} constituency-specific article(s) found — low confidence")

            log.info("seat.signals_gathered",
                     constituency_code=constituency_code,
                     specific_articles=len(specific_articles),
                     state_articles=len(state_articles),
                     specific_signals=sum(len(v) for v in signals.values()),
                     state_signals=sum(len(v) for v in state_signals.values()))

    except Exception as e:
        log.error("seat.gather_signals.error", error=str(e), constituency_code=constituency_code)
        state["signals"] = empty_signals
        state["state_signals"] = empty_signals
        state["evidence_quality"] = None
        state["error"] = f"Error gathering signals: {str(e)}"

    return state


async def load_baseline(state: dict) -> dict:
    """Load historical results and demographics for the constituency from the DB."""
    constituency_code = state.get("constituency_code")
    log.info("seat.load_baseline", constituency_code=constituency_code)

    session_maker = get_session_maker()
    if not session_maker:
        state["wiki_baseline"] = {
            "constituency_name": f"Constituency {constituency_code}",
            "historical_winners": {},
            "voter_demographics": {},
        }
        return state

    try:
        async with session_maker() as session:
            # Historical results
            stmt = select(HistoricalResult).where(
                HistoricalResult.constituency_code == constituency_code
            ).order_by(HistoricalResult.election_year.desc())
            result = await session.execute(stmt)
            history = result.scalars().all()

            # Demographics
            stmt_demo = select(ConstituencyDemographics).where(
                ConstituencyDemographics.constituency_code == constituency_code
            )
            result_demo = await session.execute(stmt_demo)
            demographics = result_demo.scalars().first()

            seat_name = history[0].seat_name if history else constituency_code

            state["wiki_baseline"] = {
                "constituency_name": seat_name,
                "historical_winners": {
                    str(h.election_year): {
                        "party": h.winner_party,
                        "coalition": h.winner_coalition,
                        "winner_name": h.winner_name,
                        "margin_pct": h.margin_pct,
                        "turnout_pct": h.turnout_pct,
                        "candidates": json.loads(h.candidates) if isinstance(h.candidates, str) else (h.candidates or []),
                    }
                    for h in history
                },
                "voter_demographics": {
                    "malay_pct": demographics.malay_pct,
                    "chinese_pct": demographics.chinese_pct,
                    "indian_pct": demographics.indian_pct,
                    "others_pct": demographics.others_pct,
                    "urban_rural": demographics.urban_rural,
                    "region": demographics.region,
                } if demographics else {},
            }

            log.info("seat.baseline_loaded", constituency_code=constituency_code,
                     history_years=[h.election_year for h in history],
                     has_demographics=demographics is not None)

    except Exception as e:
        log.error("seat.load_baseline.error", error=str(e), constituency_code=constituency_code)
        state["wiki_baseline"] = {
            "constituency_name": constituency_code,
            "historical_winners": {},
            "voter_demographics": {},
        }

    return state


async def assess(state: dict) -> dict:
    """LLM-based assessment: aggregate signals into SeatPrediction."""
    constituency_code = state.get("constituency_code")
    signals = state.get("signals", {})
    state_signals = state.get("state_signals", {})
    caveats = state.get("caveats", [])

    log.info("seat.assess", constituency_code=constituency_code)

    def _summarise_signals(raw: dict) -> dict:
        summary = {}
        for lens, analyses in raw.items():
            # Flatten any nested lists, keep only dicts
            flat = []
            for a in (analyses or []):
                if isinstance(a, dict):
                    flat.append(a)
                elif isinstance(a, list):
                    flat.extend(x for x in a if isinstance(x, dict))
            if flat:
                avg_strength = sum(a.get("strength", 0) or 0 for a in flat) / len(flat)
                directions = [a.get("direction") for a in flat if a.get("direction")]
                leading = max(set(directions), key=directions.count) if directions else None
                # `label` is the raw lens vocabulary (e.g. "BN_dominance_restore", "Malay").
                # The seat LLM is responsible for normalizing this to a party in its output `direction`.
                summary[lens] = {
                    "label": leading,
                    "strength": int(avg_strength),
                    "article_count": len(flat),
                }
            else:
                summary[lens] = None
        return summary

    signal_summary = _summarise_signals(signals)
    state_signal_summary = _summarise_signals(state_signals)

    baseline = state.get("wiki_baseline", {})
    historical_winners = baseline.get("historical_winners", {})
    voter_demographics = baseline.get("voter_demographics", {})
    constituency_name = baseline.get("constituency_name", constituency_code)

    num_specific = state.get("num_articles", 0)
    num_state = state.get("num_state_articles", 0)
    evidence_quality = state.get("evidence_quality") or {}

    prompt = f"""
You are an election analyst for Johor, Malaysia. Assess constituency {constituency_code} ({constituency_name}).

## Historical Baseline
{json.dumps(historical_winners, indent=2)}

## Voter Demographics
{json.dumps(voter_demographics, indent=2)}

## Constituency-Specific Signals  ({num_specific} articles tagged directly to {constituency_code})
For each lens: `label` = raw lens vocabulary (e.g. "BN_dominance_restore", "Malay", "Urban+Youth");
`strength` = average analyst confidence; `article_count` = articles contributing.
You MUST normalize each `label` to a party in your output `direction` field — see Direction Normalization Rules below.
Weight these heavily when available.
{json.dumps(signal_summary, indent=2)}

## State-Level Signals  ({num_state} Johor-wide articles, no specific constituency tag)
These signals reflect broader Johor political trends. Apply them as background context
for all seats — weight them at roughly half the importance of constituency-specific signals.
{json.dumps(state_signal_summary, indent=2)}

## Evidence Quality
{json.dumps(evidence_quality, indent=2)}

## Direction Normalization Rules
The output `direction` for each lens MUST be one of: "BN", "PH", "PN", or null.
Map non-party `label` values using these rules; preserve the original `label` in the output:
- historical: "BN_dominance_restore"->BN; "PH_resurgence"->PH; "PN_growth"->PN; "three_way_fragmentation"/"unclear"->null
- demographic: "Malay"/"Rural" typically->BN; "Chinese"/"Urban" typically->PH; "Indian"->null unless context indicates; "Youth" alone->null (volatile); compounds like "Urban+Youth"->lean PH but consider seat profile
- bridget_welsh: "complex"->null; "BN"/"PH"/"PN"->same
- political/strategic: "mixed"->null; "BN"/"PH"/"PN"->same
- factcheck: always null (factcheck has no party direction)
- social_signal: "BN"/"PH"/"PN"->same; "unclear"->null

## Confidence Calibration Rules
Use evidence_quality to bound confidence — apply the LOWEST applicable cap:
- avg_reliability < 50 -> cap confidence at 60
- specific_article_count < 5 -> cap confidence at 50
- agreement on the dominant journalism lens < 0.5 -> cap confidence at 65
- source_diversity.count == 1 -> cap confidence at 55 (single-source bias risk)
- scorer_flags includes "partisan_framing" or similar concerning flag -> reduce confidence by 5
- Seats with margin_pct < 5% in 2022 are highly marginal -> cap confidence at 55

Based on all of the above, predict the likely winner of this constituency.

Return a JSON object:
{{
  "leading_party": "<BN|PH|PN>",
  "confidence": <0-100>,
  "signal_breakdown": {{
    "political":     {{"direction": "<BN|PH|PN|null>", "label": "<raw lens label>", "strength": <0-100>, "summary": "..."}},
    "demographic":   {{"direction": "<BN|PH|PN|null>", "label": "<raw lens label>", "strength": <0-100>, "summary": "..."}},
    "historical":    {{"direction": "<BN|PH|PN|null>", "label": "<raw lens label>", "strength": <0-100>, "summary": "..."}},
    "strategic":     {{"direction": "<BN|PH|PN|null>", "label": "<raw lens label>", "strength": <0-100>, "summary": "..."}},
    "factcheck":     {{"direction": null, "label": "<raw lens label>", "strength": <0-100>, "summary": "..."}},
    "bridget_welsh": {{"direction": "<BN|PH|PN|null>", "label": "<raw lens label>", "strength": <0-100>, "summary": "..."}},
    "social_signal": {{"direction": "<BN|PH|PN|null>", "label": "<raw lens label>", "strength": <0-30>,  "summary": "..."}}
  }},
  "historical_comparison": "How does the current signal compare to the 2022 baseline?",
  "swing_estimate": "<estimated swing from 2022 in percentage points or 'unknown'>",
  "rationale": "..."
}}

Key guidelines:
- If no constituency-specific signals exist, rely on state-level signals + historical baseline
- If no signals exist at all, rely on historical baseline and demographics alone to assess certainty
- If signals contradict history, note this and lower confidence
- Factor in demographic composition when assessing party strength
- Consider three-cornered fight dynamics (BN vs PH vs PN vote splitting)
- social_signal: treat as weak corroborating evidence only (strength capped at 30). Do NOT let it override journalism lenses. Use it only to nudge confidence +/-3-5 points when it aligns or contradicts the dominant signal.

Return ONLY valid JSON, no markdown.
"""

    try:
        response = await llm_call_with_fallback(
            messages=[
                {"role": "system", "content": "You are an election analyst for Johor, Malaysia."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        cleaned = response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(cleaned)
        if isinstance(result, list):
            result = result[0]
        signal_breakdown = result.get("signal_breakdown")
        if not isinstance(signal_breakdown, dict):
            signal_breakdown = signal_summary
        state["seat_prediction"] = {
            "constituency_code": constituency_code,
            "leading_party": result.get("leading_party"),
            "confidence": result.get("confidence"),
            "signal_breakdown": signal_breakdown,
            "evidence_quality": evidence_quality or None,
            "caveats": caveats,
        }

        log.info("seat.assessed", constituency_code=constituency_code, party=result.get("leading_party"), confidence=result.get("confidence"))

    except Exception as e:
        log.error("seat.assess.error", error=str(e), constituency_code=constituency_code)
        state["error"] = f"LLM assessment failed: {str(e)}"
        state["seat_prediction"] = {
            "constituency_code": constituency_code,
            "leading_party": None,
            "confidence": 0,
            "signal_breakdown": signal_summary,
            "evidence_quality": evidence_quality or None,
            "caveats": caveats + ["Assessment failed"],
        }

    return state


async def store(state: dict) -> dict:
    """Store SeatPrediction to database."""
    prediction = state.get("seat_prediction")
    if not prediction:
        log.warning("seat.store.no_prediction")
        return state

    constituency_code = prediction.get("constituency_code")

    if not prediction.get("leading_party"):
        prediction["leading_party"] = "Unclear"
        log.warning("seat.store.unclear", constituency_code=constituency_code)

    log.info("seat.store", constituency_code=constituency_code)

    # Get database session
    session_maker = get_session_maker()
    if not session_maker:
        state["error"] = "Database not initialized"
        return state

    try:
        async with session_maker() as session:
            # Check if prediction already exists for this constituency
            stmt = select(SeatPrediction).where(SeatPrediction.constituency_code == constituency_code)
            result = await session.execute(stmt)
            existing = result.scalars().first()

            if existing:
                # Update
                existing.leading_party = prediction.get("leading_party")
                existing.confidence = prediction.get("confidence")
                existing.signal_breakdown = prediction.get("signal_breakdown")
                existing.evidence_quality = prediction.get("evidence_quality")
                existing.caveats = prediction.get("caveats")
                existing.num_articles = state.get("num_articles")
                existing.num_state_articles = state.get("num_state_articles")
                await session.merge(existing)
                log.info("seat.prediction.updated", constituency_code=constituency_code)
            else:
                # Create new
                new_pred = SeatPrediction(
                    id=str(uuid.uuid4()),
                    constituency_code=constituency_code,
                    leading_party=prediction.get("leading_party"),
                    confidence=prediction.get("confidence"),
                    signal_breakdown=prediction.get("signal_breakdown"),
                    evidence_quality=prediction.get("evidence_quality"),
                    caveats=prediction.get("caveats"),
                    num_articles=state.get("num_articles"),
                    num_state_articles=state.get("num_state_articles"),
                )
                session.add(new_pred)
                log.info("seat.prediction.created", constituency_code=constituency_code)

            await session.commit()

    except Exception as e:
        log.error("seat.store.error", error=str(e), constituency_code=constituency_code)
        state["error"] = f"Failed to store prediction: {str(e)}"

    return state
