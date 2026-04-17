"""Seat agent 4-node LangGraph pipeline."""
from __future__ import annotations

import json
import uuid
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base.llm import llm_call_with_fallback
from agents.base.models import Analysis, Article, SeatPrediction
from control_plane.db import get_session_maker

log = structlog.get_logger(__name__)


async def gather_signals(state: dict, config: dict) -> dict:
    """Gather multi-lens analysis signals for the constituency."""
    executor = config["configurable"]["executor"]
    task_id = config["configurable"]["task_id"]
    executor.check_cancelled(task_id)

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


async def load_baseline(state: dict, config: dict) -> dict:
    """Load constituency wiki baseline + party pages for context."""
    executor = config["configurable"]["executor"]
    task_id = config["configurable"]["task_id"]
    executor.check_cancelled(task_id)

    constituency_code = state.get("constituency_code")
    log.info("seat.load_baseline", constituency_code=constituency_code)

    # Load from wiki if available (mocked here; in real version, would read from wiki filesystem)
    state["wiki_baseline"] = {
        "constituency_name": f"Constituency {constituency_code}",
        "historical_winners": {},
        "voter_demographics": {},
    }

    return state


async def assess(state: dict, config: dict) -> dict:
    """LLM-based assessment: aggregate signals into SeatPrediction."""
    executor = config["configurable"]["executor"]
    task_id = config["configurable"]["task_id"]
    executor.check_cancelled(task_id)

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

    prompt = f"""
You are an election analyst for Johor, Malaysia. Assess the constituency {constituency_code} based on these signals:

{json.dumps(signal_summary, indent=2)}

Return a JSON object with:
{{
  "leading_party": "<BN|PH|PN>",
  "confidence": <0-100>,
  "signal_breakdown": {{
    "political": {{"direction": "<party>", "strength": <0-100>, "summary": "..."}},
    "demographic": {{"direction": "<party>", "strength": <0-100>, "summary": "..."}},
    ...
  }},
  "rationale": "..."
}}

Base confidence on:
- Number of signals (more = higher confidence)
- Signal agreement (aligned = higher)
- Signal strength

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


async def store(state: dict, config: dict) -> dict:
    """Store SeatPrediction to database."""
    executor = config["configurable"]["executor"]
    task_id = config["configurable"]["task_id"]
    executor.check_cancelled(task_id)

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
