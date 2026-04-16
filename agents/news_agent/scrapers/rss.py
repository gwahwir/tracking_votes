"""Generic RSS/Atom scraper using feedparser."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import feedparser  # type: ignore


@dataclass
class RawArticle:
    url: str
    title: str
    content: str          # body text (may be empty for paywalled sources)
    source: str           # human-readable outlet name
    published_at: Optional[datetime]


def scrape_rss(feed_url: str, source_name: str, max_items: int = 50) -> list[RawArticle]:
    """Parse an RSS/Atom feed and return a list of RawArticle objects."""
    feed = feedparser.parse(feed_url)
    articles: list[RawArticle] = []

    for entry in feed.entries[:max_items]:
        url = entry.get("link", "")
        if not url:
            continue

        title = entry.get("title", "")
        # Prefer summary/content; fall back to title alone
        body = (
            entry.get("summary", "")
            or _first_content(entry)
            or ""
        )
        # Strip basic HTML tags
        body = _strip_html(body)

        published_at = _parse_date(entry)

        articles.append(RawArticle(
            url=url,
            title=title,
            content=body,
            source=source_name,
            published_at=published_at,
        ))

    return articles


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_content(entry) -> str:
    content = entry.get("content", [])
    if content and isinstance(content, list):
        return content[0].get("value", "")
    return ""


def _parse_date(entry) -> Optional[datetime]:
    import time

    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if t:
        try:
            return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
        except (OverflowError, OSError):
            pass
    return None


def _strip_html(text: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
