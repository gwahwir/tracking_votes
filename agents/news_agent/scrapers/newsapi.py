"""NewsAPI.org wrapper — fallback when RSS feeds yield no results."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
import structlog

from .rss import RawArticle

log = structlog.get_logger(__name__)

_JOHOR_QUERY = "Johor OR Parlimen OR DUN election Malaysia"


def scrape(max_items: int = 20) -> list[RawArticle]:
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        return []

    last_exc: Exception | None = None
    data = None
    for attempt in range(3):
        try:
            resp = httpx.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": _JOHOR_QUERY,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": min(max_items, 100),
                    "apiKey": api_key,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as exc:
            last_exc = exc
            # Don't retry auth or hard rate-limit errors
            if hasattr(exc, "response") and exc.response is not None and exc.response.status_code in (401, 403, 429):
                log.warning("newsapi.no_retry", status=exc.response.status_code, error=str(exc))
                return []
            delay = 2.0 ** attempt
            log.warning("newsapi.retry", attempt=attempt + 1, delay=delay, error=str(exc))
            time.sleep(delay)

    if data is None:
        log.error("newsapi.failed", error=str(last_exc))
        return []

    articles: list[RawArticle] = []
    for item in data.get("articles", []):
        url = item.get("url", "")
        if not url or url == "https://removed.com":
            continue
        published_at: Optional[datetime] = None
        raw_date = item.get("publishedAt")
        if raw_date:
            try:
                published_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except ValueError:
                pass

        articles.append(RawArticle(
            url=url,
            title=item.get("title", ""),
            content=(item.get("content") or item.get("description") or ""),
            source=item.get("source", {}).get("name", "NewsAPI"),
            published_at=published_at,
        ))

    return articles
