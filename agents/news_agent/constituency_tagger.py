"""Constituency tagger — maps article text to Johor Parlimen/DUN seat codes.

Codes use dotted format matching GeoJSON: "N.01"–"N.56", "P.140"–"P.165".
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ConstituencyMatch:
    code: str           # e.g. "P.140" or "N.01"
    seat_type: str      # "parlimen" | "dun"
    name: str
    matched_keyword: str


# ---------------------------------------------------------------------------
# Lookup tables  (code, name, [extra keywords / localities])
# Authoritative names from GeoJSON; Parlimen P.140–P.165, DUN N.01–N.56
# ---------------------------------------------------------------------------

# fmt: off
_PARLIMEN: list[tuple[str, str, list[str]]] = [
    ("P.140", "Segamat",          ["Segamat", "Genuang", "Buloh Kasap", "Jementah"]),
    ("P.141", "Sekijang",         ["Sekijang", "Pemanis", "Kemelah"]),
    ("P.142", "Labis",            ["Labis", "Tenang", "Bekok"]),
    ("P.143", "Pagoh",            ["Pagoh", "Bukit Kepong", "Bukit Pasir", "Bukit Serampang"]),
    ("P.144", "Ledang",           ["Ledang", "Gambir", "Tangkak", "Serom"]),
    ("P.145", "Bakri",            ["Bakri", "Bentayan", "Simpang Jeram", "Bukit Naning"]),
    ("P.146", "Muar",             ["Muar", "Maharani", "Sungai Balang"]),
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
    ("P.157", "Pengerang",        ["Pengerang", "Penawar", "Tanjung Surat", "RAPID", "Refinery"]),
    ("P.158", "Tebrau",           ["Tebrau", "Masai", "Plentong", "Tiram", "Puteri Wangsa"]),
    ("P.159", "Pasir Gudang",     ["Pasir Gudang", "Johor Jaya", "Permas", "Permas Jaya"]),
    ("P.160", "Johor Bahru",      ["Johor Bahru", "JB", "Larkin", "Stulang", "Bukit Chagar"]),
    ("P.161", "Pulai",            ["Pulai", "Gelang Patah", "Perling", "Kempas"]),
    ("P.162", "Iskandar Puteri",  ["Iskandar Puteri", "Skudai", "Kota Iskandar", "Nusajaya", "Iskandar Malaysia"]),
    ("P.163", "Kulai",            ["Kulai", "Bukit Permai", "Bukit Batu", "Senai", "Indahpura"]),
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
    ("N.16", "Sungai Balang",  ["Sungai Balang"]),
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

# Pre-compile patterns
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
    combined = text[:5000]
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
