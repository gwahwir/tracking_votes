"""TF-IDF retriever — ranks wiki pages by relevance to a query string."""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .loader import WikiPage, load_all_pages


@dataclass
class RetrievalResult:
    page: WikiPage
    score: float
    excerpt: str   # Most relevant ~300 char snippet


class TFIDFRetriever:
    def __init__(self, pages: list[WikiPage] | None = None) -> None:
        self._pages: list[WikiPage] = pages or []
        self._idf: dict[str, float] = {}
        self._tfs: list[dict[str, float]] = []
        if self._pages:
            self._build_index()

    def reload(self) -> None:
        """Re-read wiki from disk and rebuild the index."""
        self._pages = load_all_pages()
        self._build_index()

    def query(self, text: str, top_k: int = 3) -> list[RetrievalResult]:
        """Return the top_k most relevant pages for the given query text."""
        if not self._pages:
            return []
        q_tokens = _tokenise(text)
        q_tf = _tf(q_tokens)

        scores: list[tuple[float, int]] = []
        for idx, doc_tf in enumerate(self._tfs):
            score = _cosine(q_tf, doc_tf, self._idf)
            scores.append((score, idx))

        scores.sort(reverse=True)
        results: list[RetrievalResult] = []
        for score, idx in scores[:top_k]:
            if score <= 0:
                break
            page = self._pages[idx]
            results.append(RetrievalResult(
                page=page,
                score=round(score, 4),
                excerpt=_best_excerpt(page.content, q_tokens),
            ))
        return results

    # ------------------------------------------------------------------
    # Index construction
    # ------------------------------------------------------------------

    def _build_index(self) -> None:
        n = len(self._pages)
        tokenised = [_tokenise(p.content) for p in self._pages]
        self._tfs = [_tf(tokens) for tokens in tokenised]

        # Document frequency
        df: Counter = Counter()
        for tokens in tokenised:
            for term in set(tokens):
                df[term] += 1

        # IDF with smoothing
        self._idf = {
            term: math.log((n + 1) / (count + 1)) + 1
            for term, count in df.items()
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STOP = frozenset(
    "a an the and or but in on at to of is are was were be been being "
    "have has had do does did will would could should may might this that "
    "these those with for from by as it its we they he she i you".split()
)


def _tokenise(text: str) -> list[str]:
    tokens = re.findall(r"[a-z]+", text.lower())
    return [t for t in tokens if t not in _STOP and len(t) > 2]


def _tf(tokens: list[str]) -> dict[str, float]:
    if not tokens:
        return {}
    counts: Counter = Counter(tokens)
    total = len(tokens)
    return {term: count / total for term, count in counts.items()}


def _cosine(q: dict[str, float], d: dict[str, float], idf: dict[str, float]) -> float:
    dot = 0.0
    for term, qv in q.items():
        if term in d:
            w = idf.get(term, 1.0)
            dot += qv * d[term] * w * w
    return dot


def _best_excerpt(content: str, query_tokens: list[str], window: int = 300) -> str:
    """Find the window of text with the highest density of query tokens."""
    lower = content.lower()
    best_start = 0
    best_count = -1
    step = max(1, window // 4)
    for start in range(0, max(1, len(lower) - window), step):
        chunk = lower[start: start + window]
        count = sum(1 for t in query_tokens if t in chunk)
        if count > best_count:
            best_count = count
            best_start = start
    return content[best_start: best_start + window].strip()
