"""LangGraph graph for the news agent.

Nodes: fetch → filter → tag → upsert
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, TypedDict

import structlog
from langgraph.graph import END, StateGraph

from .constituency_tagger import tag_codes
from .scrapers import thestar, fmt, malaysiakini, cna, newsapi
from .scrapers.rss import RawArticle

log = structlog.get_logger(__name__)

# Fast model for relevance classification — reads from env, falls back to gpt-4o-mini
import os as _os
_FILTER_MODEL = _os.environ.get("OPENAI_SMALL_MODEL", "openai/gpt-4o-mini")

# Fallback keyword filter used if LLM call fails
_JOHOR_KEYWORDS = [
    "johor", "parlimen", "dun", "umno", "bn", "pkr", "dap", "bersatu",
    "pru", "pilihanraya", "calon", "ge15", "ge14", "iskandar",
    "johor bahru", "jb", "muar", "batu pahat", "kluang", "segamat",
    "pontian", "kota tinggi", "mersing", "kulai", "pasir gudang",
    "election malaysia", "malaysia election",
]


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class NewsState(TypedDict):
    input: str
    metadata: dict[str, Any]
    raw_articles: list[dict]       # RawArticle serialised to dict
    filtered_articles: list[dict]
    tagged_articles: list[dict]    # + constituency_ids field
    upserted_count: int
    output: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def _fetch_node(state: NewsState) -> NewsState:
    """Fetch articles from all sources concurrently (sync via threads)."""
    scrapers = [thestar, fmt, malaysiakini, cna, newsapi]
    all_raw: list[RawArticle] = []

    for scraper in scrapers:
        try:
            articles = scraper.scrape()
            all_raw.extend(articles)
            log.debug("scraper.done", source=scraper.__name__.split(".")[-1], count=len(articles))
        except Exception as exc:
            log.warning("scraper.error", source=scraper.__name__, error=str(exc))

    state["raw_articles"] = [_article_to_dict(a) for a in all_raw]
    log.info("fetch.done", total=len(all_raw))
    return state


def _keyword_filter(articles: list[dict]) -> list[dict]:
    """Fallback keyword-based filter."""
    return [
        art for art in articles
        if any(kw in (art["title"] + " " + art["content"]).lower() for kw in _JOHOR_KEYWORDS)
    ]


def _llm_filter(articles: list[dict]) -> list[dict]:
    """LLM-based relevance filter using a cheap/fast model.

    Sends all articles in one batch call. Each article is represented by its
    title + first 500 chars of content. Returns articles the LLM deems
    potentially relevant to the Johor state election.
    """
    from agents.base.llm import llm_call

    if not articles:
        return []

    # Build numbered article list for the prompt
    article_snippets = []
    for i, art in enumerate(articles):
        snippet = (art.get("content") or "")[:500].strip()
        article_snippets.append(f'[{i}] {art["title"]}\n{snippet}')

    prompt = f"""You are filtering news articles for relevance to the Johor state election in Malaysia.

An article is RELEVANT if it could plausibly affect voter sentiment or electoral outcomes in Johor, including:
- Direct coverage of Johor constituencies, candidates, or campaigns
- National party events, leadership changes, or internal conflicts (BN/UMNO, PH/DAP/PKR/Amanah, PN/Bersatu/PAS)
- Federal government policies that affect Johor voters (economy, cost of living, development projects)
- Corruption cases or scandals involving politicians active in Johor
- Events held outside Johor but involving Johor politicians or targeting Johor voters
- Anything that shifts national political narrative that Johor voters would care about

An article is NOT RELEVANT if it covers:
- Sports, entertainment, celebrity news with no political angle
- Foreign news with no Malaysia connection
- Business/finance with no electoral implications
- Natural disasters or crimes unrelated to politics

Here are {len(articles)} articles to assess:

{chr(10).join(article_snippets)}

Return a JSON array of the indices (0-based) of RELEVANT articles only.
Example: [0, 2, 5]
If none are relevant, return [].
Return ONLY the JSON array, no explanation."""

    try:
        response = llm_call(
            messages=[{"role": "user", "content": prompt}],
            model=_FILTER_MODEL,
            response_format={"type": "json_object"},
            temperature=0,
        )
        import json as _json
        # Response may be {"indices": [...]} or just [...]
        parsed = _json.loads(response)
        if isinstance(parsed, list):
            indices = parsed
        else:
            # Find first list value in the object
            indices = next((v for v in parsed.values() if isinstance(v, list)), [])

        relevant = [articles[i] for i in indices if isinstance(i, int) and 0 <= i < len(articles)]
        log.info("filter.llm_done", total=len(articles), kept=len(relevant))
        return relevant

    except Exception as exc:
        log.warning("filter.llm_error", error=str(exc), fallback="keyword filter")
        return _keyword_filter(articles)


def _filter_node(state: NewsState) -> NewsState:
    """Keep only articles relevant to the Johor election using LLM classification.

    Falls back to keyword matching if the LLM call fails.
    """
    raw = state["raw_articles"]
    filtered = _llm_filter(raw)
    log.info("filter.done", kept=len(filtered), dropped=len(raw) - len(filtered))
    state["filtered_articles"] = filtered
    return state


def _tag_node(state: NewsState) -> NewsState:
    """Tag each article with matched constituency codes."""
    tagged: list[dict] = []
    for art in state["filtered_articles"]:
        text = art["title"] + " " + art["content"]
        codes = tag_codes(text)
        art = dict(art)  # copy
        art["constituency_ids"] = codes
        tagged.append(art)

    state["tagged_articles"] = tagged
    return state


def _upsert_node(state: NewsState) -> NewsState:
    """Persist articles to PostgreSQL, deduplicating by URL.

    Falls back gracefully if no DB is configured.
    Automatically dispatches scorer_agent tasks for newly upserted articles.
    """
    import os
    database_url = os.environ.get("DATABASE_URL")
    control_plane_url = os.environ.get("CONTROL_PLANE_URL", "http://control_plane:8000")

    if not database_url:
        log.warning("upsert.no_db", reason="DATABASE_URL not set — skipping DB write")
        state["upserted_count"] = 0
        state["output"] = f"Fetched {len(state['tagged_articles'])} articles (no DB configured)"
        return state

    import asyncio
    import json
    import httpx

    async def _do_upsert():
        import asyncpg  # type: ignore
        conn = await asyncpg.connect(database_url)
        upserted_articles = []
        count = 0
        try:
            for art in state["tagged_articles"]:
                try:
                    article_id = str(uuid.uuid4())
                    await conn.execute(
                        """
                        INSERT INTO articles
                            (id, url, title, content, source, published_at, constituency_ids)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (url) DO UPDATE
                            SET title=EXCLUDED.title,
                                content=EXCLUDED.content,
                                constituency_ids=EXCLUDED.constituency_ids
                        """,
                        article_id,
                        art["url"],
                        art["title"][:1000],
                        (art["content"] or "")[:10000],
                        art["source"],
                        art.get("published_at"),
                        json.dumps(art.get("constituency_ids", [])),
                    )
                    count += 1
                    art_copy = dict(art)
                    art_copy["_article_id"] = article_id  # Store the ID with the article
                    upserted_articles.append(art_copy)
                except Exception as exc:
                    log.warning("upsert.row_error", url=art["url"], error=str(exc))
        finally:
            await conn.close()
        return count, upserted_articles

    async def _auto_score_articles(articles: list[dict]) -> None:
        """Dispatch scorer_agent tasks for each upserted article."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Dispatch scorer tasks with article IDs (already have them from upsert)
            for art in articles:
                try:
                    article_id = art.get("_article_id", str(uuid.uuid4()))
                    message = f"Score this article:\n\nTitle: {art['title']}\n\nURL: {art['url']}\n\nSource: {art['source']}\n\n{art.get('content', '')}"

                    response = await client.post(
                        f"{control_plane_url}/agents/scorer_agent/tasks",
                        json={"message": message, "metadata": {"article_id": article_id}},
                        timeout=10.0,
                    )
                    response.raise_for_status()
                    result = response.json()
                    log.info("auto_score.dispatched", task_id=result.get("task_id"), article_url=art["url"], article_id=article_id)
                except Exception as exc:
                    log.warning("auto_score.dispatch_error", article_url=art["url"], error=str(exc))

    try:
        # Create a new event loop for this thread since we're in a sync context
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            count, upserted_articles = new_loop.run_until_complete(_do_upsert())
            # Dispatch scorer_agent tasks for all upserted articles
            if upserted_articles:
                new_loop.run_until_complete(_auto_score_articles(upserted_articles))
        finally:
            new_loop.close()
    except Exception as exc:
        log.error("upsert.failed", error=str(exc))
        count = 0

    state["upserted_count"] = count
    state["output"] = (
        f"Scraped {len(state['raw_articles'])} articles, "
        f"filtered to {len(state['filtered_articles'])}, "
        f"upserted {count} to DB, "
        f"dispatched {count} to scorer_agent"
    )
    log.info("upsert.done", count=count, auto_score_count=count)
    return state


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_news_graph():
    g = StateGraph(NewsState)
    g.add_node("fetch", _fetch_node)
    g.add_node("filter", _filter_node)
    g.add_node("tag", _tag_node)
    g.add_node("upsert", _upsert_node)

    g.set_entry_point("fetch")
    g.add_edge("fetch", "filter")
    g.add_edge("filter", "tag")
    g.add_edge("tag", "upsert")
    g.add_edge("upsert", END)

    return g.compile()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _article_to_dict(a: RawArticle) -> dict:
    return {
        "url": a.url,
        "title": a.title,
        "content": a.content,
        "source": a.source,
        "published_at": a.published_at,
        "constituency_ids": [],
    }
