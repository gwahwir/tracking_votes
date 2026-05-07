"""Signals analyser LangGraph — analyse → store.

Single LLM call per signal article. Writes one analyses row with
lens_name='social_signal'. Strength is capped at 30 at write time.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, TypedDict

import structlog
from langgraph.graph import END, StateGraph

from agents.base.llm import llm_call

log = structlog.get_logger(__name__)

_PROMPT = (Path(__file__).parent / "prompts" / "signal_analysis.txt").read_text(encoding="utf-8")

_STRENGTH_MAP = {"low": 10, "medium": 20, "high": 30}


class SignalState(TypedDict):
    input: str
    metadata: dict[str, Any]
    article_id: str
    article_text: str
    source: str
    engagement: dict[str, Any]   # score, num_comments from Reddit metadata
    analysis: dict[str, Any]
    output: str


def _analyse_node(state: SignalState) -> SignalState:
    """Parse input and run the single LLM analysis call."""
    state["article_id"] = state["metadata"].get("article_id", str(uuid.uuid4()))
    state["source"] = state["metadata"].get("source", "Unknown")
    state["engagement"] = state["metadata"].get("engagement", {})

    # Parse input — accept JSON or framed plain text ("Analyse this signal:\n\n...")
    try:
        data = json.loads(state["input"])
        state["article_text"] = data.get("article_text", state["input"])
    except (json.JSONDecodeError, TypeError):
        raw = state["input"]
        if raw.lower().startswith("analyse this signal"):
            parts = raw.split("\n\n", maxsplit=4)
            state["article_text"] = parts[-1] if len(parts) >= 2 else raw
        else:
            state["article_text"] = raw

    engagement = state["engagement"]
    engagement_line = ""
    if engagement.get("score") is not None:
        engagement_line = f"\nEngagement: {engagement.get('score', 0)} upvotes, {engagement.get('num_comments', 0)} comments"

    user_content = (
        f"Source: {state['source']}{engagement_line}\n\n"
        f"Post:\n{state['article_text'][:3000]}"
    )

    default = {
        "tone": "neutral",
        "claim": "Unable to analyse — parse error",
        "implication": "unclear",
        "signal_strength": "low",
    }

    for attempt in range(2):
        try:
            raw = llm_call(
                messages=[
                    {"role": "system", "content": _PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            result = json.loads(cleaned)
            for key in ("tone", "claim", "implication", "signal_strength"):
                if key not in result:
                    raise ValueError(f"Missing key: {key}")
            state["analysis"] = result
            log.info("signals_analyser.analysed",
                     article_id=state["article_id"],
                     tone=result["tone"],
                     implication=result["implication"],
                     strength=result["signal_strength"])
            break
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("signals_analyser.parse_error", attempt=attempt + 1, error=str(exc))
            if attempt == 1:
                state["analysis"] = default
    else:
        state["analysis"] = default

    return state


def _store_node(state: SignalState) -> SignalState:
    """Write one analyses row with lens_name='social_signal', strength capped at 30."""
    analysis = state["analysis"]
    database_url = os.environ.get("DATABASE_URL")

    if not database_url or not state.get("article_id"):
        state["output"] = json.dumps(analysis)
        return state

    strength = _STRENGTH_MAP.get(analysis.get("signal_strength", "low"), 10)
    direction = analysis.get("implication", "unclear")
    if direction == "unclear":
        direction = None   # excluded from seat agent majority vote

    summary = f"{analysis.get('tone', 'neutral')}: {analysis.get('claim', '')}"
    full_result = json.dumps(analysis)
    analysis_id = str(uuid.uuid4())

    import asyncio
    import asyncpg  # type: ignore

    async def _persist():
        conn = await asyncpg.connect(database_url)
        try:
            await conn.execute(
                """
                INSERT INTO analyses
                    (id, article_id, lens_name, direction, strength, summary, full_result, source_type)
                VALUES ($1, $2, 'social_signal', $3, $4, $5, $6::json, 'signal')
                ON CONFLICT (article_id, lens_name)
                DO UPDATE SET
                    direction   = EXCLUDED.direction,
                    strength    = EXCLUDED.strength,
                    summary     = EXCLUDED.summary,
                    full_result = EXCLUDED.full_result
                """,
                analysis_id,
                state["article_id"],
                direction,
                float(strength),
                summary[:2000],
                full_result,
            )
            log.info("signals_analyser.stored", article_id=state["article_id"], strength=strength)
        finally:
            await conn.close()

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_persist())
        finally:
            loop.close()
    except Exception as exc:
        log.warning("signals_analyser.db_error", error=str(exc))

    state["output"] = json.dumps(analysis)
    return state


def build_signals_graph():
    g = StateGraph(SignalState)
    g.add_node("analyse", _analyse_node)
    g.add_node("store", _store_node)
    g.set_entry_point("analyse")
    g.add_edge("analyse", "store")
    g.add_edge("store", END)
    return g.compile()
