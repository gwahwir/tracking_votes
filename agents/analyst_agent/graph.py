"""Analyst agent — 3-stage LangGraph pipeline.

Stages:
  1. retrieve_wiki  — fetch relevant wiki pages
  2. run_lenses     — 6 lens analyses in parallel (Political, Demographic, Historical,
                      Strategic, Fact-check, Bridget Welsh)
  3. chain_to_seat  — dispatch seat_agent tasks for tagged constituencies
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, TypedDict

import structlog
from langgraph.graph import END, StateGraph

from agents.base.llm import llm_call, llm_call_async
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
    title: str
    constituency_codes: list[str]
    wiki_context: str
    system_prompt: str
    lenses: dict[str, Any]        # lens_name -> {direction, strength, summary, ...}
    output: str                   # JSON of full analysis


# ---------------------------------------------------------------------------
# Node 1: retrieve_wiki
# ---------------------------------------------------------------------------

def _retrieve_wiki_node(state: AnalystState) -> AnalystState:
    try:
        data = json.loads(state["input"])
        state["article_id"] = data.get("article_id", str(uuid.uuid4()))
        state["article_text"] = data.get("article_text", state["input"])
        state["title"] = data.get("title", "")
        state["constituency_codes"] = data.get("constituency_codes", [])
    except (json.JSONDecodeError, TypeError):
        state["article_id"] = str(uuid.uuid4())
        state["article_text"] = state["input"]
        state["title"] = ""
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

async def _run_lenses_node(state: AnalystState) -> AnalystState:
    system = state["system_prompt"]
    title_line = f"Title: {state['title']}\n\n" if state.get("title") else ""
    article = f"{title_line}{state['article_text'][:4000]}"
    article_id = state.get("article_id", "")

    async def _call_lens(name: str, lens_prompt: str) -> tuple[str, Any]:
        messages = [
            {"role": "system", "content": f"{system}\n\n{lens_prompt}"},
            {"role": "user", "content": f"Analyse this article:\n\n{article}"},
        ]
        for attempt in range(2):
            try:
                raw = await llm_call_async(messages, response_format={"type": "json_object"}, temperature=0.3)
            except Exception as exc:
                if attempt == 0:
                    log.warning("analyst.lens_llm_retry", lens=name, error=str(exc))
                    continue
                log.warning("analyst.lens_llm_failed", lens=name, error=str(exc))
                return name, {"parse_error": True}
            cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            try:
                return name, json.loads(cleaned)
            except json.JSONDecodeError:
                if attempt == 0:
                    log.warning("analyst.lens_parse_retry", lens=name)
                    continue
                log.warning("analyst.lens_parse_failed", lens=name)
                return name, {"parse_error": True}
        return name, {"parse_error": True}

    async def _call_lens_with_timeout(name: str, lens_prompt: str) -> tuple[str, Any]:
        try:
            return await asyncio.wait_for(_call_lens(name, lens_prompt), timeout=60.0)
        except asyncio.TimeoutError:
            log.warning("analyst.lens_timeout", lens=name)
            return name, {"parse_error": True, "timeout": True}

    tasks = [_call_lens_with_timeout(name, prompt) for name, prompt in _LENS_PROMPTS.items()]
    lens_results = await asyncio.gather(*tasks)

    results: dict[str, Any] = {}
    for name, result in lens_results:
        results[name] = result
        if not result.get("parse_error"):
            log.debug("analyst.lens_done", lens=name)
            await _persist_single_lens(article_id, name, result)

    state["lenses"] = results
    state["output"] = json.dumps({"article_id": state["article_id"], "lenses": state["lenses"]})
    return state


# ---------------------------------------------------------------------------
# Node 3: chain_to_seat
# ---------------------------------------------------------------------------

# Valid Johor constituency codes
_VALID_CODES: frozenset[str] = frozenset(
    [f"P.{n}" for n in range(140, 166)] +
    [f"N.{n:02d}" for n in range(1, 57)]
)

# Seat name → code lookup for fallback resolution when LLM emits wrong code numbers
_SEAT_NAME_TO_CODE: dict[str, str] = {
    name.lower(): code for code, name, _ in [
        ("P.140","Segamat",[]),("P.141","Sekijang",[]),("P.142","Labis",[]),
        ("P.143","Pagoh",[]),("P.144","Ledang",[]),("P.145","Bakri",[]),
        ("P.146","Muar",[]),("P.147","Parit Sulong",[]),("P.148","Ayer Hitam",[]),
        ("P.149","Sri Gading",[]),("P.150","Batu Pahat",[]),("P.151","Simpang Renggam",[]),
        ("P.152","Kluang",[]),("P.153","Sembrong",[]),("P.154","Mersing",[]),
        ("P.155","Tenggara",[]),("P.156","Kota Tinggi",[]),("P.157","Pengerang",[]),
        ("P.158","Tebrau",[]),("P.159","Pasir Gudang",[]),("P.160","Johor Bahru",[]),
        ("P.161","Pulai",[]),("P.162","Iskandar Puteri",[]),("P.163","Kulai",[]),
        ("P.164","Pontian",[]),("P.165","Tanjung Piai",[]),
        ("N.01","Buloh Kasap",[]),("N.02","Jementah",[]),("N.03","Pemanis",[]),
        ("N.04","Kemelah",[]),("N.05","Tenang",[]),("N.06","Bekok",[]),
        ("N.07","Bukit Kepong",[]),("N.08","Bukit Pasir",[]),("N.09","Gambir",[]),
        ("N.10","Tangkak",[]),("N.11","Serom",[]),("N.12","Bentayan",[]),
        ("N.13","Simpang Jeram",[]),("N.14","Bukit Naning",[]),("N.15","Maharani",[]),
        ("N.16","Sungai Balang",[]),("N.17","Semerah",[]),("N.18","Sri Medan",[]),
        ("N.19","Yong Peng",[]),("N.20","Semarang",[]),("N.21","Parit Yaani",[]),
        ("N.22","Parit Raja",[]),("N.23","Penggaram",[]),("N.24","Senggarang",[]),
        ("N.25","Rengit",[]),("N.26","Machap",[]),("N.27","Layang-Layang",[]),
        ("N.28","Mengkibol",[]),("N.29","Mahkota",[]),("N.30","Paloh",[]),
        ("N.31","Kahang",[]),("N.32","Endau",[]),("N.33","Tenggaroh",[]),
        ("N.34","Panti",[]),("N.35","Pasir Raja",[]),("N.36","Sedili",[]),
        ("N.37","Johor Lama",[]),("N.38","Penawar",[]),("N.39","Tanjung Surat",[]),
        ("N.40","Tiram",[]),("N.41","Puteri Wangsa",[]),("N.42","Johor Jaya",[]),
        ("N.43","Permas",[]),("N.44","Larkin",[]),("N.45","Stulang",[]),
        ("N.46","Perling",[]),("N.47","Kempas",[]),("N.48","Skudai",[]),
        ("N.49","Kota Iskandar",[]),("N.50","Bukit Permai",[]),("N.51","Bukit Batu",[]),
        ("N.52","Senai",[]),("N.53","Benut",[]),("N.54","Pulai Sebatang",[]),
        ("N.55","Pekan Nanas",[]),("N.56","Kukup",[]),
    ]
}


def _resolve_code(raw: str) -> str | None:
    """Extract and validate a constituency code from a raw LLM string.

    1. Try to parse a P/N code directly — if valid, use it.
    2. If the parsed code is invalid (wrong number), scan the full string for a
       known seat name and use that code instead (LLM got the name right, number wrong).
    3. Return None if neither resolves to a valid code.
    """
    for m in re.finditer(r'\b([PN])\.?(\d+)\b', raw, re.IGNORECASE):
        code = f"{m.group(1).upper()}.{m.group(2)}"
        if code in _VALID_CODES:
            return code
    # Fallback: scan for a known seat name in the raw string
    raw_lower = raw.lower()
    for name, code in _SEAT_NAME_TO_CODE.items():
        if re.search(r'\b' + re.escape(name) + r'\b', raw_lower):
            return code
    return None


def _extract_codes_from_lens(lens_data: dict[str, Any]) -> list[str]:
    """Pull constituency codes out of a lens seat_implications list.

    The LLM is instructed to name the constituency in the rationale text and
    omit a separate code field, so we resolve solely from the rationale.
    Falls back to any P/N code if no seat name is found.
    """
    implications = lens_data.get("seat_implications", [])
    codes: list[str] = []
    for item in implications:
        search_text = item.get("rationale", "") if isinstance(item, dict) else str(item)
        code = _resolve_code(search_text)
        if code and code not in codes:
            codes.append(code)
    return codes


def _chain_to_seat_node(state: AnalystState) -> AnalystState:
    import httpx

    control_plane_url = os.environ.get("CONTROL_PLANE_URL", "http://control_plane:8000")

    lenses = state.get("lenses", {})

    # Merge pre-tagged codes with codes from political + strategic lenses
    raw_tagged = state.get("constituency_codes", [])
    if isinstance(raw_tagged, str):
        try:
            raw_tagged = json.loads(raw_tagged)
        except (json.JSONDecodeError, TypeError):
            raw_tagged = [raw_tagged] if raw_tagged else []
    tagged_codes: list[str] = [c for c in raw_tagged if isinstance(c, str)]
    political_codes = _extract_codes_from_lens(lenses.get("political", {}))
    strategic_codes = _extract_codes_from_lens(lenses.get("strategic", {}))
    constituency_codes = list(dict.fromkeys(tagged_codes + political_codes + strategic_codes))

    if not constituency_codes:
        log.info("chain.no_constituencies", article_id=state.get("article_id"))
        return state

    log.info("chain.constituencies", article_id=state.get("article_id"),
             tagged=tagged_codes, from_political=political_codes,
             from_strategic=strategic_codes, total=len(constituency_codes))

    article_id = state.get("article_id")

    async def _dispatch():
        import asyncpg  # type: ignore
        # Write merged codes back to articles.constituency_ids
        database_url = os.environ.get("DATABASE_URL")
        if database_url and article_id:
            try:
                conn = await asyncpg.connect(database_url)
                try:
                    # Merge with existing tags — never discard what the regex tagger found
                    row = await conn.fetchrow(
                        "SELECT constituency_ids FROM articles WHERE id = $1", article_id
                    )
                    existing: list[str] = []
                    if row and row["constituency_ids"]:
                        try:
                            existing = json.loads(row["constituency_ids"])
                            if not isinstance(existing, list):
                                existing = []
                        except (json.JSONDecodeError, TypeError):
                            existing = []
                    merged = list(dict.fromkeys(existing + constituency_codes))
                    await conn.execute(
                        "UPDATE articles SET constituency_ids = $1 WHERE id = $2",
                        json.dumps(merged),
                        article_id,
                    )
                    log.info("chain.tags_updated", article_id=article_id, codes=merged)
                finally:
                    await conn.close()
            except Exception as exc:
                log.warning("chain.tags_update_failed", error=str(exc))

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


async def _persist_single_lens(article_id: str, lens_name: str, lens_data: dict) -> None:
    """Write one lens result to DB immediately after it completes."""
    if lens_data.get("parse_error"):
        return
    database_url = os.environ.get("DATABASE_URL")
    if not database_url or not article_id:
        return

    import asyncpg  # type: ignore

    try:
        conn = await asyncpg.connect(database_url)
        try:
            await conn.execute(
                """
                INSERT INTO analyses
                    (id, article_id, lens_name, direction, strength, summary, full_result)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT (article_id, lens_name)
                DO UPDATE SET
                    direction   = EXCLUDED.direction,
                    strength    = EXCLUDED.strength,
                    summary     = EXCLUDED.summary,
                    full_result = EXCLUDED.full_result
                """,
                str(uuid.uuid4()),
                article_id,
                lens_name,
                lens_data.get("direction", ""),
                lens_data.get("strength"),
                (lens_data.get("summary", "") or "")[:2000],
                json.dumps(lens_data),
            )
        finally:
            await conn.close()
    except Exception as exc:
        log.warning("analyst.db_error", lens=lens_name, error=str(exc))


async def _persist_analyses(state: AnalystState) -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url or not state.get("article_id"):
        return

    import asyncpg  # type: ignore

    try:
        conn = await asyncpg.connect(database_url)
        try:
            for lens_name, lens_data in state["lenses"].items():
                if lens_data.get("parse_error"):
                    continue
                await conn.execute(
                    """
                    INSERT INTO analyses
                        (id, article_id, lens_name, direction, strength, summary, full_result)
                    VALUES ($1,$2,$3,$4,$5,$6,$7)
                    ON CONFLICT (article_id, lens_name)
                    DO UPDATE SET
                        direction   = EXCLUDED.direction,
                        strength    = EXCLUDED.strength,
                        summary     = EXCLUDED.summary,
                        full_result = EXCLUDED.full_result
                    """,
                    str(uuid.uuid4()),
                    state["article_id"],
                    lens_name,
                    lens_data.get("direction", ""),
                    lens_data.get("strength"),
                    (lens_data.get("summary", "") or "")[:2000],
                    json.dumps(lens_data),
                )
        finally:
            await conn.close()
    except Exception as exc:
        log.warning("analyst.db_error", error=str(exc))


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_analyst_graph():
    g = StateGraph(AnalystState)

    g.add_node("retrieve_wiki", _retrieve_wiki_node)
    g.add_node("run_lenses",    _run_lenses_node)
    g.add_node("chain_to_seat", _chain_to_seat_node)

    g.set_entry_point("retrieve_wiki")
    g.add_edge("retrieve_wiki", "run_lenses")
    g.add_edge("run_lenses",    "chain_to_seat")
    g.add_edge("chain_to_seat", END)

    return g.compile()
