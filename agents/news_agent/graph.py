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

# Johor relevance keywords (any match passes the filter)
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


def _filter_node(state: NewsState) -> NewsState:
    """Keep only articles that mention Johor or related election keywords."""
    filtered: list[dict] = []
    for art in state["raw_articles"]:
        combined = (art["title"] + " " + art["content"]).lower()
        if any(kw in combined for kw in _JOHOR_KEYWORDS):
            filtered.append(art)

    log.info("filter.done", kept=len(filtered), dropped=len(state["raw_articles"]) - len(filtered))
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
    """
    import os
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        log.warning("upsert.no_db", reason="DATABASE_URL not set — skipping DB write")
        state["upserted_count"] = 0
        state["output"] = f"Fetched {len(state['tagged_articles'])} articles (no DB configured)"
        return state

    import asyncio
    import json

    async def _do_upsert():
        import asyncpg  # type: ignore
        conn = await asyncpg.connect(database_url)
        count = 0
        try:
            for art in state["tagged_articles"]:
                try:
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
                        str(uuid.uuid4()),
                        art["url"],
                        art["title"][:1000],
                        (art["content"] or "")[:10000],
                        art["source"],
                        art.get("published_at"),
                        json.dumps(art.get("constituency_ids", [])),
                    )
                    count += 1
                except Exception as exc:
                    log.warning("upsert.row_error", url=art["url"], error=str(exc))
        finally:
            await conn.close()
        return count

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're inside an async context — run in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _do_upsert())
                count = future.result(timeout=30)
        else:
            count = loop.run_until_complete(_do_upsert())
    except Exception as exc:
        log.error("upsert.failed", error=str(exc))
        count = 0

    state["upserted_count"] = count
    state["output"] = (
        f"Scraped {len(state['raw_articles'])} articles, "
        f"filtered to {len(state['filtered_articles'])}, "
        f"upserted {count} to DB"
    )
    log.info("upsert.done", count=count)
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
