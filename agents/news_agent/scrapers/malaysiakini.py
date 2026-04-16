"""Malaysiakini RSS feed."""
from __future__ import annotations

from .rss import RawArticle, scrape_rss

_FEEDS = [
    "https://www.malaysiakini.com/rss/",
]


def scrape(max_items: int = 30) -> list[RawArticle]:
    articles: list[RawArticle] = []
    for feed_url in _FEEDS:
        try:
            articles.extend(scrape_rss(feed_url, "Malaysiakini", max_items=max_items))
        except Exception:
            pass
    return articles
