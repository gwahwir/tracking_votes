"""Scorer agent LangGraph — retrieve_wiki → score → store.

Inputs (via state):
  article_id   — DB row id (optional; skipped if not set)
  article_text — full article text to score
  source       — outlet name (e.g. "The Star")

Output:
  score_result — dict matching the reliability.txt JSON schema
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, TypedDict

import httpx
import structlog
from langgraph.graph import END, StateGraph

from agents.base.llm import llm_call
from agents.wiki_agent.retriever import TFIDFRetriever
from agents.wiki_agent.loader import load_all_pages

log = structlog.get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "reliability.txt"
_PROMPT_TEMPLATE = _PROMPT_PATH.read_text(encoding="utf-8")

_retriever: TFIDFRetriever | None = None


def _get_retriever() -> TFIDFRetriever:
    global _retriever
    if _retriever is None:
        _retriever = TFIDFRetriever(load_all_pages())
    return _retriever


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class ScorerState(TypedDict):
    input: str               # JSON string with {article_id, article_text, source}
    metadata: dict[str, Any]
    article_id: str
    article_text: str
    source: str
    wiki_context: str
    score_result: dict[str, Any]
    output: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def _retrieve_wiki_node(state: ScorerState) -> ScorerState:
    """Parse input and fetch top-3 wiki excerpts relevant to the article."""
    # Parse input — accept JSON string or plain text
    try:
        data = json.loads(state["input"])
        state["article_id"] = data.get("article_id", str(uuid.uuid4()))
        state["article_text"] = data.get("article_text", state["input"])
        state["source"] = data.get("source", "Unknown")
    except (json.JSONDecodeError, TypeError):
        state["article_id"] = str(uuid.uuid4())
        state["article_text"] = state["input"]
        state["source"] = state["metadata"].get("source", "Unknown")

    retriever = _get_retriever()
    results = retriever.query(state["article_text"], top_k=3)
    excerpts = []
    for r in results:
        excerpts.append(f"### {r.page.title}\n{r.excerpt}")
    state["wiki_context"] = "\n\n---\n\n".join(excerpts) if excerpts else "(no relevant wiki context found)"

    log.debug("scorer.wiki_retrieved", pages=len(results))
    return state


def _score_node(state: ScorerState) -> ScorerState:
    """Call LLM with article + wiki context to produce a reliability score."""
    prompt = _PROMPT_TEMPLATE.replace("{{WIKI_CONTEXT}}", state["wiki_context"])

    article_block = f"Source outlet: {state['source']}\n\n{state['article_text'][:4000]}"

    raw = llm_call(
        [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Score this article:\n\n{article_block}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    try:
        result = json.loads(raw)
        # Validate required top-level keys
        for key in ("score", "sourceAuthority", "accuracySignals", "biasIndicators", "justification"):
            if key not in result:
                raise ValueError(f"Missing key: {key}")
        state["score_result"] = result
        log.info("scorer.scored", article_id=state["article_id"], score=result["score"])
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning("scorer.parse_error", error=str(exc))
        state["score_result"] = {
            "score": 0,
            "sourceAuthority": {"tier": 3, "outlet": state["source"], "score": 0},
            "accuracySignals": {"score": 0, "positives": [], "negatives": ["LLM parse error"]},
            "biasIndicators": {"score": 0, "flags": []},
            "justification": f"Scoring failed: {exc}",
            "flags": ["SCORING_ERROR"],
        }

    return state


def _store_node(state: ScorerState) -> ScorerState:
    """Persist score to DB and emit wiki ingest task if score >= 60."""
    score = state["score_result"].get("score", 0)
    database_url = os.environ.get("DATABASE_URL")

    if database_url and state.get("article_id"):
        import asyncio
        import asyncpg  # type: ignore

        async def _persist():
            conn = await asyncpg.connect(database_url)
            try:
                await conn.execute(
                    "UPDATE articles SET reliability_score=$1 WHERE id=$2",
                    score,
                    state["article_id"],
                )
            finally:
                await conn.close()

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(asyncio.run, _persist()).result(timeout=10)
            else:
                loop.run_until_complete(_persist())
        except Exception as exc:
            log.warning("scorer.db_error", error=str(exc))

    # Emit wiki ingest task if article scored well
    if score >= 60:
        _emit_wiki_task(state["article_text"], state["article_id"])

    state["output"] = json.dumps(state["score_result"])
    return state


def _emit_wiki_task(article_text: str, article_id: str) -> None:
    """POST a wiki ingest task to the control plane (fire-and-forget)."""
    control_plane = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8000")
    url = f"{control_plane.rstrip('/')}/agents/wiki_agent/tasks"
    try:
        httpx.post(
            url,
            json={"message": article_text[:3000], "metadata": {"article_id": article_id, "mode": "ingest"}},
            timeout=5.0,
        )
        log.info("scorer.wiki_task_emitted", article_id=article_id)
    except Exception as exc:
        log.warning("scorer.wiki_emit_error", error=str(exc))


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_scorer_graph():
    g = StateGraph(ScorerState)
    g.add_node("retrieve_wiki", _retrieve_wiki_node)
    g.add_node("score", _score_node)
    g.add_node("store", _store_node)

    g.set_entry_point("retrieve_wiki")
    g.add_edge("retrieve_wiki", "score")
    g.add_edge("score", "store")
    g.add_edge("store", END)

    return g.compile()
