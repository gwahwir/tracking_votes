"""Constituency tagger — maps article text to Johor Parlimen/DUN seat codes.

Codes use dotted format matching GeoJSON: "N.01"–"N.56", "P.140"–"P.165".

Keyword lists contain place names and localities only. Candidate names are
loaded from the DB at first use via _enrich_from_db(), so they stay current
without code changes. Falls back to the static lists if no DB is available.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field


@dataclass
class ConstituencyMatch:
    code: str           # e.g. "P.140" or "N.01"
    seat_type: str      # "parlimen" | "dun"
    name: str
    matched_keyword: str


# ---------------------------------------------------------------------------
# Lookup tables  (code, name, [place names / localities / abbreviations])
# Candidate names are intentionally omitted — loaded from DB at runtime.
# Authoritative seat names from GeoJSON; Parlimen P.140–P.165, DUN N.01–N.56
# ---------------------------------------------------------------------------

# fmt: off
_PARLIMEN: list[tuple[str, str, list[str]]] = [
    ("P.140", "Segamat",          ["Segamat", "Genuang", "Buloh Kasap", "Jementah"]),
    ("P.141", "Sekijang",         ["Sekijang", "Pemanis", "Kemelah"]),
    ("P.142", "Labis",            ["Labis", "Tenang", "Bekok"]),
    ("P.143", "Pagoh",            ["Pagoh", "Bukit Kepong", "Bukit Pasir", "Bukit Serampang"]),
    ("P.144", "Ledang",           ["Ledang", "Gambir", "Tangkak", "Serom"]),
    ("P.145", "Bakri",            ["Bakri", "Bentayan", "Simpang Jeram", "Bukit Naning"]),
    ("P.146", "Muar",             ["Muar", "Maharani", "Sungai Balang", "Sg Balang"]),
    ("P.147", "Parit Sulong",     ["Parit Sulong", "Semerah", "Sri Medan"]),
    ("P.148", "Ayer Hitam",       ["Ayer Hitam", "Air Hitam", "Yong Peng", "Semarang"]),
    ("P.149", "Sri Gading",       ["Sri Gading", "Parit Yaani", "Parit Raja"]),
    ("P.150", "Batu Pahat",       ["Batu Pahat", "Penggaram", "Senggarang", "Rengit"]),
    ("P.151", "Simpang Renggam",  ["Simpang Renggam", "Machap", "Layang-Layang", "Layang Layang"]),
    ("P.152", "Kluang",           ["Kluang", "Mengkibol", "Mahkota"]),
    ("P.153", "Sembrong",         ["Sembrong", "Paloh", "Kahang"]),
    ("P.154", "Mersing",          ["Mersing", "Endau", "Tenggaroh"]),
    ("P.155", "Tenggara",         ["Tenggara", "Panti", "Pasir Raja"]),
    ("P.156", "Kota Tinggi",      ["Kota Tinggi", "Sedili", "Johor Lama"]),
    ("P.157", "Pengerang",        ["Pengerang", "Penawar", "Tanjung Surat", "RAPID", "Pengerang Integrated Petroleum Complex"]),
    ("P.158", "Tebrau",           ["Tebrau", "Masai", "Plentong", "Tiram", "Puteri Wangsa", "Taman Johor Jaya"]),
    ("P.159", "Pasir Gudang",     ["Pasir Gudang", "Johor Jaya", "Permas", "Permas Jaya", "Pasir Gudang Industrial"]),
    ("P.160", "Johor Bahru",      ["Johor Bahru", "JB", "Larkin", "Stulang", "Bukit Chagar", "Taman Melodies", "Taman Pelangi"]),
    ("P.161", "Pulai",            ["Pulai", "Gelang Patah", "Perling", "Kempas", "Taman Pulai"]),
    ("P.162", "Iskandar Puteri",  ["Iskandar Puteri", "Skudai", "Kota Iskandar", "Nusajaya", "Iskandar Malaysia", "Medini", "EduCity", "Puteri Harbour"]),
    ("P.163", "Kulai",            ["Kulai", "Bukit Permai", "Bukit Batu", "Senai", "Indahpura", "Kulai Jaya"]),
    ("P.164", "Pontian",          ["Pontian", "Benut", "Pulai Sebatang"]),
    ("P.165", "Tanjung Piai",     ["Tanjung Piai", "Pekan Nanas", "Kukup"]),
]

_DUN: list[tuple[str, str, list[str]]] = [
    ("N.01", "Buloh Kasap",    ["Buloh Kasap"]),
    ("N.02", "Jementah",       ["Jementah"]),
    ("N.03", "Pemanis",        ["Pemanis"]),
    ("N.04", "Kemelah",        ["Kemelah"]),
    ("N.05", "Tenang",         ["Tenang"]),
    ("N.06", "Bekok",          ["Bekok"]),
    ("N.07", "Bukit Kepong",   ["Bukit Kepong"]),
    ("N.08", "Bukit Pasir",    ["Bukit Pasir"]),
    ("N.09", "Gambir",         ["Gambir"]),
    ("N.10", "Tangkak",        ["Tangkak"]),
    ("N.11", "Serom",          ["Serom"]),
    ("N.12", "Bentayan",       ["Bentayan"]),
    ("N.13", "Simpang Jeram",  ["Simpang Jeram"]),
    ("N.14", "Bukit Naning",   ["Bukit Naning"]),
    ("N.15", "Maharani",       ["Maharani"]),
    ("N.16", "Sungai Balang",  ["Sungai Balang", "Sg Balang"]),
    ("N.17", "Semerah",        ["Semerah"]),
    ("N.18", "Sri Medan",      ["Sri Medan"]),
    ("N.19", "Yong Peng",      ["Yong Peng"]),
    ("N.20", "Semarang",       ["Semarang"]),
    ("N.21", "Parit Yaani",    ["Parit Yaani"]),
    ("N.22", "Parit Raja",     ["Parit Raja"]),
    ("N.23", "Penggaram",      ["Penggaram"]),
    ("N.24", "Senggarang",     ["Senggarang"]),
    ("N.25", "Rengit",         ["Rengit"]),
    ("N.26", "Machap",         ["Machap"]),
    ("N.27", "Layang-Layang",  ["Layang-Layang", "Layang Layang"]),
    ("N.28", "Mengkibol",      ["Mengkibol"]),
    ("N.29", "Mahkota",        ["Mahkota"]),
    ("N.30", "Paloh",          ["Paloh"]),
    ("N.31", "Kahang",         ["Kahang"]),
    ("N.32", "Endau",          ["Endau"]),
    ("N.33", "Tenggaroh",      ["Tenggaroh"]),
    ("N.34", "Panti",          ["Panti"]),
    ("N.35", "Pasir Raja",     ["Pasir Raja"]),
    ("N.36", "Sedili",         ["Sedili"]),
    ("N.37", "Johor Lama",     ["Johor Lama"]),
    ("N.38", "Penawar",        ["Penawar"]),
    ("N.39", "Tanjung Surat",  ["Tanjung Surat"]),
    ("N.40", "Tiram",          ["Tiram"]),
    ("N.41", "Puteri Wangsa",  ["Puteri Wangsa"]),
    ("N.42", "Johor Jaya",     ["Johor Jaya"]),
    ("N.43", "Permas",         ["Permas", "Permas Jaya"]),
    ("N.44", "Larkin",         ["Larkin"]),
    ("N.45", "Stulang",        ["Stulang"]),
    ("N.46", "Perling",        ["Perling"]),
    ("N.47", "Kempas",         ["Kempas"]),
    ("N.48", "Skudai",         ["Skudai"]),
    ("N.49", "Kota Iskandar",  ["Kota Iskandar"]),
    ("N.50", "Bukit Permai",   ["Bukit Permai"]),
    ("N.51", "Bukit Batu",     ["Bukit Batu"]),
    ("N.52", "Senai",          ["Senai"]),
    ("N.53", "Benut",          ["Benut"]),
    ("N.54", "Pulai Sebatang", ["Pulai Sebatang"]),
    ("N.55", "Pekan Nanas",    ["Pekan Nanas"]),
    ("N.56", "Kukup",          ["Kukup"]),
]
# fmt: on


# ---------------------------------------------------------------------------
# DB enrichment — loads candidate names from historical_results at startup
# ---------------------------------------------------------------------------

# Mutable keyword dicts: code -> set of keywords (populated by _enrich_from_db)
_parlimen_keywords: dict[str, set[str]] = {code: set([name] + kws) for code, name, kws in _PARLIMEN}
_dun_keywords: dict[str, set[str]] = {code: set([name] + kws) for code, name, kws in _DUN}
_db_enriched = False
_compiled_parlimen: list[tuple[str, str, re.Pattern]] | None = None
_compiled_dun: list[tuple[str, str, re.Pattern]] | None = None


def _enrich_from_db() -> None:
    """Pull all candidate names from historical_results and merge into keyword sets."""
    global _db_enriched
    if _db_enriched:
        return

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        _db_enriched = True
        return

    try:
        import asyncio
        import asyncpg  # type: ignore

        async def _fetch():
            conn = await asyncpg.connect(database_url)
            try:
                rows = await conn.fetch("""
                    SELECT constituency_code,
                           c->>'name' AS candidate_name
                    FROM historical_results,
                         json_array_elements(candidates) AS c
                    WHERE state = 'Johor'
                      AND c->>'party' NOT IN (
                          'TOTAL REJECTED BALLOTS','UNRETURNED BALLOTS','BNGAINFROMPH'
                      )
                      AND c->>'name' NOT LIKE '%BALLOT%'
                      AND c->>'name' NOT LIKE 'TOTAL%'
                      AND c->>'name' NOT LIKE '%UNRETURNED%'
                      AND length(c->>'name') > 4
                """)
                return rows
            finally:
                await conn.close()

        loop = asyncio.new_event_loop()
        try:
            rows = loop.run_until_complete(_fetch())
        finally:
            loop.close()

        # Common Malay/Chinese name particles that appear across hundreds of candidates
        # and would produce false positives if used as standalone keywords
        _NAME_PARTICLES = {
            "bin", "binti", "binte", "a/l", "a/p",
            "mohamed", "mohammad", "muhammad", "mohamad",
            "abd", "abdul", "abdullah",
            "ahmad", "ahmed",
            "ali", "hassan", "hussein", "hussin",
            "lee", "lim", "tan", "wong", "ng", "ong", "chan",
            "syed", "sharifah",
        }

        added = 0
        for row in rows:
            code = row["constituency_code"]
            name = (row["candidate_name"] or "").strip()
            if not name or len(name) < 5:
                continue
            # Strip honorifics so "Tan Sri Muhyiddin" also matches "Muhyiddin"
            clean = re.sub(
                r"^(Tan Sri|Tun|Datuk Seri|Datuk|Dato'|Dato|Dr\.?|Haji|Hj\.?|"
                r"Ustaz|Cikgu|YB|YAB|YBhg|Datin|Prof\.?)\s+",
                "", name, flags=re.IGNORECASE
            ).strip()
            # Also strip "bin/binti <surname>" suffix to get first name only
            clean = re.sub(r"\s+bin(ti)?\s+.*$", "", clean, flags=re.IGNORECASE).strip()

            # Only add the stripped form if it's a meaningful unique identifier
            # (at least 2 words OR not a bare common particle)
            def _is_usable(kw: str) -> bool:
                if len(kw) < 5:
                    return False
                words = kw.lower().split()
                # Single-word keywords must not be common name particles
                if len(words) == 1 and words[0] in _NAME_PARTICLES:
                    return False
                return True

            if code in _parlimen_keywords:
                _parlimen_keywords[code].add(name)
                if clean and clean != name and _is_usable(clean):
                    _parlimen_keywords[code].add(clean)
                added += 1
            elif code in _dun_keywords:
                _dun_keywords[code].add(name)
                if clean and clean != name and _is_usable(clean):
                    _dun_keywords[code].add(clean)
                added += 1

        import structlog
        structlog.get_logger(__name__).info(
            "constituency_tagger.db_enriched",
            candidates_added=added,
            seats=len(_parlimen_keywords) + len(_dun_keywords),
        )

    except Exception as exc:
        import structlog
        structlog.get_logger(__name__).warning(
            "constituency_tagger.db_enrich_failed", error=str(exc)
        )

    _db_enriched = True
    # Invalidate compiled pattern cache so next call rebuilds with enriched keywords
    global _compiled_parlimen, _compiled_dun
    _compiled_parlimen = None
    _compiled_dun = None


def _build_patterns(
    keywords_by_code: dict[str, set[str]],
    seat_lookup: list[tuple[str, str, list[str]]],
) -> list[tuple[str, str, re.Pattern]]:
    patterns = []
    for code, name, _ in seat_lookup:
        kws = keywords_by_code.get(code, {name})
        if not kws:
            continue
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(kw) for kw in sorted(kws, key=len, reverse=True)) + r")\b",
            re.IGNORECASE,
        )
        patterns.append((code, name, pattern))
    return patterns


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def tag_article(text: str) -> list[ConstituencyMatch]:
    """Return all constituency matches found in the given text.

    Deduplicates by code — only the first match per constituency is returned.
    Enriches keyword lists from DB on first call; caches compiled patterns.
    """
    global _compiled_parlimen, _compiled_dun
    _enrich_from_db()

    if _compiled_parlimen is None:
        _compiled_parlimen = _build_patterns(_parlimen_keywords, _PARLIMEN)
    if _compiled_dun is None:
        _compiled_dun = _build_patterns(_dun_keywords, _DUN)

    parlimen_patterns = _compiled_parlimen
    dun_patterns = _compiled_dun

    combined = text[:8000]
    seen: set[str] = set()
    matches: list[ConstituencyMatch] = []

    for code, name, pattern in parlimen_patterns:
        if code in seen:
            continue
        m = pattern.search(combined)
        if m:
            matches.append(ConstituencyMatch(code=code, seat_type="parlimen", name=name, matched_keyword=m.group(0)))
            seen.add(code)

    for code, name, pattern in dun_patterns:
        if code in seen:
            continue
        m = pattern.search(combined)
        if m:
            matches.append(ConstituencyMatch(code=code, seat_type="dun", name=name, matched_keyword=m.group(0)))
            seen.add(code)

    return matches


def tag_codes(text: str) -> list[str]:
    """Return just the list of matched constituency codes."""
    return [m.code for m in tag_article(text)]
