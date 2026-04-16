"""Free Malaysia Today (FMT) RSS feeds."""
from __future__ import annotations

from .rss import RawArticle, scrape_rss

_FEEDS = [
    "https://www.freemalaysiatoday.com/feed/",
    "https://www.freemalaysiatoday.com/category/nation/feed/",
]


def scrape(max_items: int = 30) -> list[RawArticle]:
    articles: list[RawArticle] = []
    for feed_url in _FEEDS:
        try:
            articles.extend(scrape_rss(feed_url, "Free Malaysia Today", max_items=max_items))
        except Exception:
            pass
    return articles
