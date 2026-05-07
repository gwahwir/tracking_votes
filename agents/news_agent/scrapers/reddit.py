"""Reddit scraper using the public JSON API (no auth required).

Pulls recent posts from r/malaysia, r/bolehland, r/malaysians, r/MalaysiaPolitics.
Uses Reddit's unauthenticated JSON endpoint — no API key needed, but
rate-limited to ~60 req/min. We fetch at most once per scrape cycle so
this is well within limits.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

import httpx
import structlog

from .rss import RawArticle

log = structlog.get_logger(__name__)

_SUBREDDITS = ["malaysia", "bolehland", "malaysians", "MalaysiaPolitics"]
_HEADERS = {"User-Agent": "ElectionMonitor/1.0 (research bot)"}


def _fetch_subreddit(subreddit: str, max_items: int) -> list[RawArticle]:
    url = f"https://www.reddit.com/r/{subreddit}/new.json"
    last_exc: Exception | None = None

    for attempt in range(3):
        try:
            resp = httpx.get(
                url,
                params={"limit": min(max_items, 100)},
                headers=_HEADERS,
                timeout=15,
                follow_redirects=True,
            )
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as exc:
            last_exc = exc
            if hasattr(exc, "response") and exc.response is not None and exc.response.status_code in (401, 403, 429):
                log.warning("reddit.no_retry", subreddit=subreddit, status=exc.response.status_code)
                return []
            delay = 2.0 ** attempt
            log.warning("reddit.retry", subreddit=subreddit, attempt=attempt + 1, delay=delay, error=str(exc))
            time.sleep(delay)
    else:
        log.error("reddit.failed", subreddit=subreddit, error=str(last_exc))
        return []

    articles: list[RawArticle] = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})

        url_val = post.get("url", "")
        if not url_val:
            continue

        title = post.get("title", "")
        # selftext is the post body for text posts; may be empty for link posts
        body = post.get("selftext", "") or ""
        # For link posts include the post URL context in content so the tagger
        # and filter have something to work with beyond just the title
        if not body:
            body = post.get("url", "")

        # Combine title + flair + body for richer context
        flair = post.get("link_flair_text") or ""
        content = f"{flair} {body}".strip() if flair else body

        created_utc = post.get("created_utc")
        published_at: Optional[datetime] = None
        if created_utc:
            try:
                published_at = datetime.fromtimestamp(float(created_utc), tz=timezone.utc)
            except (ValueError, OSError):
                pass

        # Use the Reddit post permalink as the canonical URL so upsert deduplicates correctly
        permalink = post.get("permalink", "")
        canonical_url = f"https://www.reddit.com{permalink}" if permalink else url_val

        articles.append(RawArticle(
            url=canonical_url,
            title=title,
            content=content,
            source=f"Reddit r/{subreddit}",
            published_at=published_at,
            source_type="signal",
            metadata={
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "subreddit": subreddit,
            },
        ))

    return articles


def scrape(max_items: int = 30) -> list[RawArticle]:
    articles: list[RawArticle] = []
    for subreddit in _SUBREDDITS:
        try:
            fetched = _fetch_subreddit(subreddit, max_items=max_items)
            articles.extend(fetched)
            log.debug("reddit.done", subreddit=subreddit, count=len(fetched))
        except Exception as exc:
            log.warning("reddit.scraper_error", subreddit=subreddit, error=str(exc))
    return articles
