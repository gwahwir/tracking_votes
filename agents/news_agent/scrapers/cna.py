"""Channel NewsAsia (CNA) — Malaysia section RSS."""
from __future__ import annotations

from .rss import RawArticle, scrape_rss

_FEEDS = [
    "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=10416",  # Malaysia
]


def scrape(max_items: int = 20) -> list[RawArticle]:
    articles: list[RawArticle] = []
    for feed_url in _FEEDS:
        try:
            articles.extend(scrape_rss(feed_url, "CNA", max_items=max_items))
        except Exception:
            pass
    return articles
