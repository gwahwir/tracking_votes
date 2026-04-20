"""Seat agent 4-node LangGraph pipeline."""
from __future__ import annotations

import json
import uuid
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base.llm import llm_call_with_fallback
from agents.base.models import Analysis, Article, ConstituencyDemographics, HistoricalResult, SeatPrediction
from control_plane.db import get_session_maker

log = structlog.get_logger(__name__)


async def gather_signals(state: dict) -> dict:
    """Gather multi-lens analysis signals for the constituency."""
    constituency_code = state.get("constituency_code")
    if not constituency_code:
        state["error"] = "No constituency_code provided"
        return state

    log.info("seat.gather_signals", constituency_code=constituency_code)

    # Get database session
    session_maker = get_session_maker()
    if not session_maker:
        state["error"] = "Database not initialized"
        return state

    signals = {"political": [], "demographic": [], "historical": [], "strategic": [], "factcheck": [], "bridget_welsh": []}

    try:
        async with session_maker() as session:
            # Find all articles tagged to this constituency (last 30 days)
            stmt = select(Article).where(
                Article.constituency_ids.contains([constituency_code])
            ).order_by(Article.scraped_at.desc()).limit(100)

            result = await session.execute(stmt)
            articles = result.scalars().all()

            if not articles:
                log.warning("seat.no_articles", constituency_code=constituency_code)
                state["num_articles"] = 0
                state["signals"] = signals
                state["caveats"] = [f"No articles found for {constituency_code}"]
                return state

            # For each article, gather its lens analyses
            for article in articles:
                stmt_analyses = select(Analysis).where(Analysis.article_id == article.id)
                result_analyses = await session.execute(stmt_analyses)
                analyses = result_analyses.scalars().all()

                for analysis in analyses:
                    lens = analysis.lens_name
                    if lens in signals:
                        signals[lens].append(
                            {
                                "article_id": article.id,
                                "source": article.source,
                                "direction": analysis.direction,
                                "strength": analysis.strength,
                                "summary": analysis.summary,
                            }
                        )

            state["num_articles"] = len(articles)
            state["signals"] = signals
            state["caveats"] = []

            if len(articles) < 5:
                state["caveats"].append(f"Only {len(articles)} article(s) found — low confidence")

            log.info("seat.signals_gathered", constituency_code=constituency_code, num_articles=len(articles), num_lenses=sum(len(v) for v in signals.values()))

    except Exception as e:
        log.error("seat.gather_signals.error", error=str(e), constituency_code=constituency_code)
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
                        "candidates": h.candidates,
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
    caveats = state.get("caveats", [])

    log.info("seat.assess", constituency_code=constituency_code)

    # Prepare signal summary for LLM
    signal_summary = {}
    for lens, analyses in signals.items():
        if analyses:
            avg_strength = sum(a.get("strength", 0) for a in analyses) / len(analyses)
            directions = [a.get("direction") for a in analyses if a.get("direction")]
            leading = max(set(directions), key=directions.count) if directions else None
            signal_summary[lens] = {"direction": leading, "strength": int(avg_strength)}
        else:
            signal_summary[lens] = None

    baseline = state.get("wiki_baseline", {})
    historical_winners = baseline.get("historical_winners", {})
    voter_demographics = baseline.get("voter_demographics", {})
    constituency_name = baseline.get("constituency_name", constituency_code)

    prompt = f"""
You are an election analyst for Johor, Malaysia. Assess constituency {constituency_code} ({constituency_name}).

## Historical Baseline
{json.dumps(historical_winners, indent=2)}

## Voter Demographics
{json.dumps(voter_demographics, indent=2)}

## Current Signals from News Analysis
{json.dumps(signal_summary, indent=2)}

Based on the historical patterns, demographic composition, and current news signals, predict the likely winner.

Return a JSON object:
{{
  "leading_party": "<BN|PH|PN>",
  "confidence": <0-100>,
  "signal_breakdown": {{
    "political": {{"direction": "<party>", "strength": <0-100>, "summary": "..."}},
    "demographic": {{"direction": "<party>", "strength": <0-100>, "summary": "..."}},
    "historical": {{"direction": "<party>", "strength": <0-100>, "summary": "..."}},
    "strategic": {{"direction": "<party>", "strength": <0-100>, "summary": "..."}},
    "factcheck": {{"direction": "<party>", "strength": <0-100>, "summary": "..."}},
    "bridget_welsh": {{"direction": "<party>", "strength": <0-100>, "summary": "..."}}
  }},
  "historical_comparison": "How does the current signal compare to the 2022 baseline?",
  "swing_estimate": "<estimated swing from 2022 in percentage points or 'unknown'>",
  "rationale": "..."
}}

Key guidelines:
- If no current news signals exist, weight historical baseline heavily (confidence 30-50 range)
- If signals contradict history, note this and lower confidence
- Factor in demographic composition when assessing party strength
- Consider three-cornered fight dynamics (BN vs PH vs PN vote splitting)
- Seats with margin_pct < 5% in 2022 are highly marginal — cap confidence at 55

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

        result = json.loads(response)
        state["seat_prediction"] = {
            "constituency_code": constituency_code,
            "leading_party": result.get("leading_party"),
            "confidence": result.get("confidence"),
            "signal_breakdown": result.get("signal_breakdown"),
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
                existing.caveats = prediction.get("caveats")
                existing.num_articles = state.get("num_articles")
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
                    caveats=prediction.get("caveats"),
                    num_articles=state.get("num_articles"),
                )
                session.add(new_pred)
                log.info("seat.prediction.created", constituency_code=constituency_code)

            await session.commit()

    except Exception as e:
        log.error("seat.store.error", error=str(e), constituency_code=constituency_code)
        state["error"] = f"Failed to store prediction: {str(e)}"

    return state
