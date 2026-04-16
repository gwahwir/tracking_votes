"""Constituency tagger — maps article text to Johor Parlimen/DUN seat codes.

Uses keyword matching against a lookup table of seat names, aliases, and
notable localities within each constituency.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ConstituencyMatch:
    code: str           # e.g. "P157" or "N.28"
    seat_type: str      # "parlimen" | "dun"
    name: str
    matched_keyword: str


# ---------------------------------------------------------------------------
# Lookup tables
# Parlimen: P.140–P.165 (Johor 26 seats)
# DUN: N.01–N.56 (Johor 56 seats)
# ---------------------------------------------------------------------------

# fmt: off
_PARLIMEN: list[tuple[str, str, list[str]]] = [
    # (code, name, [keywords / aliases / major localities])
    ("P140", "Pulai",          ["Pulai", "Gelang Patah", "Permas Jaya"]),
    ("P141", "Ledang",         ["Ledang", "Muar North", "Tangkak"]),
    ("P142", "Bakri",          ["Bakri", "Muar"]),
    ("P143", "Muar",           ["Muar", "Maharani"]),
    ("P144", "Parit Sulong",   ["Parit Sulong", "Batu Pahat North"]),
    ("P145", "Ayer Hitam",     ["Ayer Hitam", "Air Hitam"]),
    ("P146", "Sri Gading",     ["Sri Gading", "Batu Pahat"]),
    ("P147", "Batu Pahat",     ["Batu Pahat"]),
    ("P148", "Simpang Renggam",["Simpang Renggam", "Kluang South"]),
    ("P149", "Kluang",         ["Kluang"]),
    ("P150", "Sembrong",       ["Sembrong", "Kluang North"]),
    ("P151", "Mersing",        ["Mersing", "Endau"]),
    ("P152", "Tenggara",       ["Tenggara", "Kota Tinggi South"]),
    ("P153", "Kota Tinggi",    ["Kota Tinggi"]),
    ("P154", "Pengerang",      ["Pengerang", "RAPID", "Refinery"]),
    ("P155", "Tebrau",         ["Tebrau", "Masai", "Plentong"]),
    ("P156", "Pasir Gudang",   ["Pasir Gudang", "Pasir Gudang Port"]),
    ("P157", "Johor Bahru",    ["Johor Bahru", "JB", "Stulang", "Bukit Chagar"]),
    ("P158", "Pulai",          []),   # Note: duplicate name resolved by code
    ("P159", "Pontian",        ["Pontian", "Benut"]),
    ("P160", "Tanjung Piai",   ["Tanjung Piai", "Kukup"]),
    ("P161", "Batu Pahat",     []),   # deconflict via subkeywords
    ("P162", "Segamat",        ["Segamat", "Genuang"]),
    ("P163", "Sekijang",       ["Sekijang", "Labis"]),
    ("P164", "Pagoh",          ["Pagoh", "Bukit Serampang"]),
    ("P165", "Kulai",          ["Kulai", "Indahpura", "Bandar Tenggara"]),
]

_DUN: list[tuple[str, str, list[str]]] = [
    ("N01",  "Pulai Sebatang",  ["Pulai Sebatang"]),
    ("N02",  "Benut",           ["Benut"]),
    ("N03",  "Pontian",         ["Pontian"]),
    ("N04",  "Pekan Nanas",     ["Pekan Nanas"]),
    ("N05",  "Kukup",           ["Kukup"]),
    ("N06",  "Sri Gading",      ["Sri Gading"]),
    ("N07",  "Parit Raja",      ["Parit Raja"]),
    ("N08",  "Bukit Naning",    ["Bukit Naning"]),
    ("N09",  "Sembrong",        ["Sembrong"]),
    ("N10",  "Paloh",           ["Paloh"]),
    ("N11",  "Pemangkat",       ["Pemangkat"]),
    ("N12",  "Tenggaroh",       ["Tenggaroh"]),
    ("N13",  "Maharani",        ["Maharani"]),
    ("N14",  "Sungai Balang",   ["Sungai Balang"]),
    ("N15",  "Parit Jawa",      ["Parit Jawa"]),
    ("N16",  "Senggarang",      ["Senggarang"]),
    ("N17",  "Semerah",         ["Semerah"]),
    ("N18",  "Yong Peng",       ["Yong Peng"]),
    ("N19",  "Simpang Jeram",   ["Simpang Jeram"]),
    ("N20",  "Penggaram",       ["Penggaram"]),
    ("N21",  "Parit Yaani",     ["Parit Yaani"]),
    ("N22",  "Rengit",          ["Rengit"]),
    ("N23",  "Machap Umboo",    ["Machap Umboo", "Machap"]),
    ("N24",  "Layang-Layang",   ["Layang-Layang", "Layang Layang"]),
    ("N25",  "Mengkibol",       ["Mengkibol"]),
    ("N26",  "Mahkota",         ["Mahkota"]),
    ("N27",  "Johor Jaya",      ["Johor Jaya"]),
    ("N28",  "Permas",          ["Permas", "Permas Jaya"]),
    ("N29",  "Puteri Wangsa",   ["Puteri Wangsa"]),
    ("N30",  "Stulang",         ["Stulang"]),
    ("N31",  "Kempas",          ["Kempas"]),
    ("N32",  "Larkin",          ["Larkin"]),
    ("N33",  "Bukit Permai",    ["Bukit Permai"]),
    ("N34",  "Bukit Batu",      ["Bukit Batu"]),
    ("N35",  "Senai",           ["Senai"]),
    ("N36",  "Skudai",          ["Skudai"]),
    ("N37",  "Kempas",          []),
    ("N38",  "Pengerang",       ["Pengerang"]),
    ("N39",  "Tanjung Surat",   ["Tanjung Surat"]),
    ("N40",  "Sedili",          ["Sedili"]),
    ("N41",  "Penawar",         ["Penawar"]),
    ("N42",  "Tiram",           ["Tiram"]),
    ("N43",  "Sungai Tiram",    ["Sungai Tiram"]),
    ("N44",  "Johor Bahru",     ["Johor Bahru", "JB City"]),
    ("N45",  "Bukit Chagar",    ["Bukit Chagar"]),
    ("N46",  "Berbau",          ["Berbau"]),
    ("N47",  "Kota Iskandar",   ["Kota Iskandar", "Iskandar Puteri"]),
    ("N48",  "Nusajaya",        ["Nusajaya", "Iskandar Malaysia"]),
    ("N49",  "Pulai",           ["Pulai"]),
    ("N50",  "Sekudai",         ["Sekudai"]),
    ("N51",  "Mengkibol",       []),
    ("N52",  "Paloh",           []),
    ("N53",  "Bekok",           ["Bekok"]),
    ("N54",  "Tenang",          ["Tenang"]),
    ("N55",  "Pemanis",         ["Pemanis"]),
    ("N56",  "Bukit Kepong",    ["Bukit Kepong"]),
]
# fmt: on

# Pre-compile patterns for O(1) lookup
_PARLIMEN_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    (code, name, re.compile(
        r"\b(" + "|".join(re.escape(kw) for kw in ([name] + keywords)) + r")\b",
        re.IGNORECASE,
    ))
    for code, name, keywords in _PARLIMEN
    if [name] + keywords
]

_DUN_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    (code, name, re.compile(
        r"\b(" + "|".join(re.escape(kw) for kw in ([name] + keywords)) + r")\b",
        re.IGNORECASE,
    ))
    for code, name, keywords in _DUN
    if [name] + keywords
]


def tag_article(text: str) -> list[ConstituencyMatch]:
    """Return all constituency matches found in the given text.

    Deduplicates by code — only the first match per constituency is returned.
    """
    combined = text[:5000]  # limit to first 5000 chars to keep it fast
    seen: set[str] = set()
    matches: list[ConstituencyMatch] = []

    for code, name, pattern in _PARLIMEN_PATTERNS:
        if code in seen:
            continue
        m = pattern.search(combined)
        if m:
            matches.append(ConstituencyMatch(code=code, seat_type="parlimen", name=name, matched_keyword=m.group(0)))
            seen.add(code)

    for code, name, pattern in _DUN_PATTERNS:
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
