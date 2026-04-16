"""NewsAPI.org wrapper — fallback when RSS feeds yield no results."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from .rss import RawArticle

_JOHOR_QUERY = "Johor OR Parlimen OR DUN election Malaysia"


def scrape(max_items: int = 20) -> list[RawArticle]:
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        return []

    try:
        import httpx

        resp = httpx.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": _JOHOR_QUERY,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": min(max_items, 100),
                "apiKey": api_key,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
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
