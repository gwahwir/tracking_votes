"""Analyst agent — 7-stage LangGraph pipeline.

Stages:
  1. retrieve_wiki       — fetch relevant wiki pages
  2. run_lenses          — 6 lens analyses in parallel (Political, Demographic, Historical,
                           Strategic, Fact-check, Bridget Welsh)
  3. peripheral_scan     — catch weak signals / blind spots before aggregation
  4. aggregate           — synthesise across all 6 lenses
  5. red_team            — ACH challenge: alternative interpretations missed?
  6. baseline_compare    — compare to stored wiki baselines
  7. final_synthesis     — balanced summary with confidence indicators

Each node emits enough state for NODE_OUTPUT:: markers to be meaningful.
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any, TypedDict

import structlog
from langgraph.graph import END, StateGraph

from agents.base.llm import llm_call
from agents.wiki_agent.retriever import TFIDFRetriever
from agents.wiki_agent.loader import load_all_pages

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Load prompts
# ---------------------------------------------------------------------------

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


_SYSTEM_TEMPLATE = _load("system.txt")
_LENS_PROMPTS = {
    "political":     _load("political.txt"),
    "demographic":   _load("demographic.txt"),
    "historical":    _load("historical.txt"),
    "strategic":     _load("strategic.txt"),
    "factcheck":     _load("factcheck.txt"),
    "bridget_welsh": _load("bridget_welsh.txt"),
}

_retriever: TFIDFRetriever | None = None


def _get_retriever() -> TFIDFRetriever:
    global _retriever
    if _retriever is None:
        _retriever = TFIDFRetriever(load_all_pages())
    return _retriever


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AnalystState(TypedDict):
    input: str                    # JSON or plain text with article content
    metadata: dict[str, Any]
    article_id: str
    article_text: str
    constituency_codes: list[str]
    wiki_context: str
    system_prompt: str
    lenses: dict[str, Any]        # lens_name -> {direction, strength, summary, ...}
    peripheral_notes: str
    aggregation: str
    red_team_notes: str
    baseline_notes: str
    final_summary: str
    output: str                   # JSON of full analysis


# ---------------------------------------------------------------------------
# Node 1: retrieve_wiki
# ---------------------------------------------------------------------------

def _retrieve_wiki_node(state: AnalystState) -> AnalystState:
    try:
        data = json.loads(state["input"])
        state["article_id"] = data.get("article_id", str(uuid.uuid4()))
        state["article_text"] = data.get("article_text", state["input"])
        state["constituency_codes"] = data.get("constituency_codes", [])
    except (json.JSONDecodeError, TypeError):
        state["article_id"] = str(uuid.uuid4())
        state["article_text"] = state["input"]
        state["constituency_codes"] = []

    retriever = _get_retriever()
    results = retriever.query(state["article_text"], top_k=4)
    excerpts = [f"### {r.page.title}\n{r.excerpt}" for r in results]
    wiki_ctx = "\n\n---\n\n".join(excerpts) if excerpts else "(no relevant wiki context)"

    state["wiki_context"] = wiki_ctx
    state["system_prompt"] = _SYSTEM_TEMPLATE.replace("{{WIKI_CONTEXT}}", wiki_ctx)
    log.debug("analyst.wiki_retrieved", pages=len(results))
    return state


# ---------------------------------------------------------------------------
# Node 2: run_lenses  (6 LLM calls — run concurrently via threads)
# ---------------------------------------------------------------------------

def _run_lenses_node(state: AnalystState) -> AnalystState:
    system = state["system_prompt"]
    article = state["article_text"][:4000]

    def _call_lens(name: str, lens_prompt: str) -> tuple[str, Any]:
        raw = llm_call(
            [
                {"role": "system", "content": f"{system}\n\n{lens_prompt}"},
                {"role": "user", "content": f"Analyse this article:\n\n{article}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        try:
            return name, json.loads(raw)
        except json.JSONDecodeError:
            return name, {"direction": "unclear", "strength": 0, "summary": raw[:200], "parse_error": True}

    import concurrent.futures
    results: dict[str, Any] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_call_lens, name, prompt): name for name, prompt in _LENS_PROMPTS.items()}
        for future in concurrent.futures.as_completed(futures):
            name, result = future.result()
            results[name] = result
            log.debug("analyst.lens_done", lens=name)

    state["lenses"] = results
    return state


# ---------------------------------------------------------------------------
# Node 3: peripheral_scan
# ---------------------------------------------------------------------------

def _peripheral_scan_node(state: AnalystState) -> AnalystState:
    system = state["system_prompt"]
    lenses_summary = "\n".join(
        f"**{k}**: {v.get('summary', '')}" for k, v in state["lenses"].items()
    )

    raw = llm_call(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": (
                f"Six analysts have reviewed this article:\n\n{lenses_summary}\n\n"
                "Original article:\n\n" + state["article_text"][:2000] + "\n\n"
                "Identify any WEAK SIGNALS, BLIND SPOTS, or UNDER-EXAMINED ANGLES "
                "that none of the six analyses adequately addressed. "
                "Keep this to 2–4 bullet points. Be specific to Johor."
            )},
        ],
        temperature=0.4,
    )
    state["peripheral_notes"] = raw.strip()
    return state


# ---------------------------------------------------------------------------
# Node 4: aggregate
# ---------------------------------------------------------------------------

def _aggregate_node(state: AnalystState) -> AnalystState:
    system = state["system_prompt"]
    lenses_json = json.dumps(state["lenses"], indent=2)

    raw = llm_call(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": (
                f"Six lens analyses and peripheral scan notes:\n\n{lenses_json}\n\n"
                f"Peripheral notes:\n{state['peripheral_notes']}\n\n"
                "Synthesise these into a 3–4 paragraph aggregated analysis of this article's "
                "implications for Johor election dynamics. Identify the dominant signal, "
                "note tensions between lenses, and highlight the 1–2 constituencies most affected."
            )},
        ],
        temperature=0.4,
    )
    state["aggregation"] = raw.strip()
    return state


# ---------------------------------------------------------------------------
# Node 5: red_team
# ---------------------------------------------------------------------------

def _red_team_node(state: AnalystState) -> AnalystState:
    system = state["system_prompt"]

    raw = llm_call(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": (
                f"Aggregated analysis:\n\n{state['aggregation']}\n\n"
                "Play devil's advocate using Analysis of Competing Hypotheses (ACH):\n"
                "1. What is the single most plausible ALTERNATIVE interpretation the analysis missed?\n"
                "2. What evidence would FALSIFY the dominant interpretation?\n"
                "3. What Johor-specific factor might reverse the predicted outcome?\n"
                "Keep responses to 3–5 sentences per question."
            )},
        ],
        temperature=0.5,
    )
    state["red_team_notes"] = raw.strip()
    return state


# ---------------------------------------------------------------------------
# Node 6: baseline_compare
# ---------------------------------------------------------------------------

def _baseline_compare_node(state: AnalystState) -> AnalystState:
    """Compare against wiki baseline knowledge for the tagged constituencies."""
    retriever = _get_retriever()
    baseline_excerpts: list[str] = []

    for code in state["constituency_codes"][:3]:
        results = retriever.query(f"constituency {code} historical results baseline", top_k=1)
        if results:
            baseline_excerpts.append(f"**{code}**: {results[0].excerpt[:300]}")

    if not baseline_excerpts:
        state["baseline_notes"] = "No constituency-specific baseline data available in wiki."
        return state

    baseline_block = "\n\n".join(baseline_excerpts)
    raw = llm_call(
        [
            {"role": "system", "content": state["system_prompt"]},
            {"role": "user", "content": (
                f"Current analysis:\n{state['aggregation'][:1000]}\n\n"
                f"Wiki baseline for tagged constituencies:\n{baseline_block}\n\n"
                "In 2–3 sentences, note where the current analysis confirms the baseline "
                "and where it deviates. Flag any significant departure."
            )},
        ],
        temperature=0.2,
    )
    state["baseline_notes"] = raw.strip()
    return state


# ---------------------------------------------------------------------------
# Node 7: final_synthesis
# ---------------------------------------------------------------------------

def _final_synthesis_node(state: AnalystState) -> AnalystState:
    raw = llm_call(
        [
            {"role": "system", "content": state["system_prompt"]},
            {"role": "user", "content": (
                f"Aggregated analysis:\n{state['aggregation']}\n\n"
                f"Red-team challenge:\n{state['red_team_notes']}\n\n"
                f"Baseline comparison:\n{state['baseline_notes']}\n\n"
                "Write the FINAL SYNTHESIS for the dashboard:\n"
                "- 2 sentence executive summary\n"
                "- Overall confidence: HIGH / MEDIUM / LOW with one-line rationale\n"
                "- Top 3 key implications for Johor election monitoring\n"
                "- One sentence on what to watch next\n"
                "Format as plain prose, not bullet points."
            )},
        ],
        temperature=0.3,
    )
    state["final_summary"] = raw.strip()

    # Persist lens results to DB if configured
    _persist_analyses(state)

    # Build full output JSON
    state["output"] = json.dumps({
        "article_id": state["article_id"],
        "lenses": state["lenses"],
        "peripheral_notes": state["peripheral_notes"],
        "aggregation": state["aggregation"],
        "red_team_notes": state["red_team_notes"],
        "baseline_notes": state["baseline_notes"],
        "final_summary": state["final_summary"],
    })
    return state


def _chain_to_seat_node(state: AnalystState) -> AnalystState:
    """After analysis, dispatch seat_agent tasks for each tagged constituency."""
    import asyncio
    import os
    import httpx

    control_plane_url = os.environ.get("CONTROL_PLANE_URL", "http://control_plane:8000")
    constituency_codes = state.get("constituency_codes", [])

    if not constituency_codes:
        log.info("chain.no_constituencies", article_id=state.get("article_id"))
        return state

    async def _dispatch():
        async with httpx.AsyncClient(timeout=10.0) as client:
            for code in constituency_codes:
                try:
                    response = await client.post(
                        f"{control_plane_url}/agents/seat_agent/tasks",
                        json={
                            "message": json.dumps({"constituency_code": code}),
                            "metadata": {"constituency_code": code},
                        },
                    )
                    response.raise_for_status()
                    result = response.json()
                    log.info("chain.seat_dispatched", task_id=result.get("task_id"), code=code)
                except Exception as exc:
                    log.warning("chain.seat_error", code=code, error=str(exc))

    try:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            new_loop.run_until_complete(_dispatch())
        finally:
            new_loop.close()
    except Exception as exc:
        log.warning("chain.seat_dispatch_failed", error=str(exc))

    return state


def _persist_analyses(state: AnalystState) -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url or not state.get("article_id"):
        return

    import asyncio
    import asyncpg  # type: ignore

    async def _do_persist():
        conn = await asyncpg.connect(database_url)
        try:
            for code in state.get("constituency_codes", []) or ["JOHOR"]:
                for lens_name, lens_data in state["lenses"].items():
                    await conn.execute(
                        """
                        INSERT INTO analyses
                            (id, article_id, constituency_code, lens, direction, strength, summary)
                        VALUES ($1,$2,$3,$4,$5,$6,$7)
                        ON CONFLICT DO NOTHING
                        """,
                        str(uuid.uuid4()),
                        state["article_id"],
                        code,
                        lens_name,
                        lens_data.get("direction", ""),
                        lens_data.get("strength"),
                        lens_data.get("summary", "")[:2000],
                    )
        finally:
            await conn.close()

    try:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            new_loop.run_until_complete(_do_persist())
        finally:
            new_loop.close()
    except Exception as exc:
        log.warning("analyst.db_error", error=str(exc))


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_analyst_graph():
    g = StateGraph(AnalystState)

    g.add_node("retrieve_wiki",   _retrieve_wiki_node)
    g.add_node("run_lenses",      _run_lenses_node)
    g.add_node("peripheral_scan", _peripheral_scan_node)
    g.add_node("aggregate",       _aggregate_node)
    g.add_node("red_team",        _red_team_node)
    g.add_node("baseline_compare",_baseline_compare_node)
    g.add_node("final_synthesis", _final_synthesis_node)
    g.add_node("chain_to_seat",   _chain_to_seat_node)

    g.set_entry_point("retrieve_wiki")
    g.add_edge("retrieve_wiki",    "run_lenses")
    g.add_edge("run_lenses",       "peripheral_scan")
    g.add_edge("peripheral_scan",  "aggregate")
    g.add_edge("aggregate",        "red_team")
    g.add_edge("red_team",         "baseline_compare")
    g.add_edge("baseline_compare", "final_synthesis")
    g.add_edge("final_synthesis",  "chain_to_seat")
    g.add_edge("chain_to_seat",    END)

    return g.compile()
