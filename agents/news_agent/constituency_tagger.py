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
# Lookup tables  (code, name, [extra keywords / localities / candidate names])
# Authoritative names from GeoJSON; Parlimen P.140–P.165, DUN N.01–N.56
# Candidate names from 2022 GE15 results (winners + notable runners-up)
# ---------------------------------------------------------------------------

# fmt: off
_PARLIMEN: list[tuple[str, str, list[str]]] = [
    ("P.140", "Segamat",          ["Segamat", "Genuang", "Buloh Kasap", "Jementah", "Zahari Sarip", "Ng Kor Sim"]),
    ("P.141", "Sekijang",         ["Sekijang", "Pemanis", "Kemelah", "Anuar Abdul Manap", "Saraswathy"]),
    ("P.142", "Labis",            ["Labis", "Tenang", "Bekok", "Haslinda Salleh", "Tan Chong"]),
    ("P.143", "Pagoh",            ["Pagoh", "Bukit Kepong", "Bukit Pasir", "Bukit Serampang", "Sahruddin Jamal", "Muhyiddin"]),
    ("P.144", "Ledang",           ["Ledang", "Gambir", "Tangkak", "Serom", "Ee Chin Li", "Sahrihan Jani"]),
    ("P.145", "Bakri",            ["Bakri", "Bentayan", "Simpang Jeram", "Bukit Naning", "Salahuddin Ayub", "Ng Yak Howe"]),
    ("P.146", "Muar",             ["Muar", "Maharani", "Sungai Balang", "Abdul Aziz Talib", "Selamat Takim"]),
    ("P.147", "Parit Sulong",     ["Parit Sulong", "Semerah", "Sri Medan", "Mohd Fared", "Zulkurnain Kamisan"]),
    ("P.148", "Ayer Hitam",       ["Ayer Hitam", "Air Hitam", "Yong Peng", "Semarang", "Ling Tian Soon", "Samsolbari Jamali"]),
    ("P.149", "Sri Gading",       ["Sri Gading", "Parit Yaani", "Parit Raja", "Mohamad Najib Samuri", "Nor Rashidah Ramli"]),
    ("P.150", "Batu Pahat",       ["Batu Pahat", "Penggaram", "Senggarang", "Rengit", "Gan Peck Cheng", "Mohd Puad Zarkashi"]),
    ("P.151", "Simpang Renggam",  ["Simpang Renggam", "Machap", "Layang-Layang", "Layang Layang", "Onn Hafiz Ghazi", "Abd Mutalip"]),
    ("P.152", "Kluang",           ["Kluang", "Mengkibol", "Mahkota", "Chew Chong Sin", "Sharifah Azizah"]),
    ("P.153", "Sembrong",         ["Sembrong", "Paloh", "Kahang", "Lee Ting Han", "R Vidyananthan"]),
    ("P.154", "Mersing",          ["Mersing", "Endau", "Tenggaroh", "Alwiyah Talib", "Raven Kumar"]),
    ("P.155", "Tenggara",         ["Tenggara", "Panti", "Pasir Raja", "Hahasrin Hashim", "Rashidah Ismail"]),
    ("P.156", "Kota Tinggi",      ["Kota Tinggi", "Sedili", "Johor Lama", "Muszaide Makmor", "Norlizah Noh"]),
    ("P.157", "Pengerang",        ["Pengerang", "Penawar", "Tanjung Surat", "RAPID", "Fauziah Misri", "Aznan Tamin"]),
    ("P.158", "Tebrau",           ["Tebrau", "Masai", "Plentong", "Tiram", "Puteri Wangsa", "Azizul Bachok", "Amira Aisya"]),
    ("P.159", "Pasir Gudang",     ["Pasir Gudang", "Johor Jaya", "Permas", "Permas Jaya", "Liow Cai Tung", "Baharudin Mohamed Taib"]),
    ("P.160", "Johor Bahru",      ["Johor Bahru", "JB", "Larkin", "Stulang", "Bukit Chagar", "Mohd Hairi", "Andrew Chen"]),
    ("P.161", "Pulai",            ["Pulai", "Gelang Patah", "Perling", "Kempas", "Liew Chin Tong", "Ramlee Bohani"]),
    ("P.162", "Iskandar Puteri",  ["Iskandar Puteri", "Skudai", "Kota Iskandar", "Nusajaya", "Iskandar Malaysia", "Marina Ibrahim", "Pandak Ahmad"]),
    ("P.163", "Kulai",            ["Kulai", "Bukit Permai", "Bukit Batu", "Senai", "Indahpura", "Mohd Jafni", "Arthur Chiong", "Wong Bor Yang"]),
    ("P.164", "Pontian",          ["Pontian", "Benut", "Pulai Sebatang", "Hasni Mohammad", "Hasrunizah Hassan"]),
    ("P.165", "Tanjung Piai",     ["Tanjung Piai", "Pekan Nanas", "Kukup", "Tan Eng Meng", "Jefridin Atan"]),
]

_DUN: list[tuple[str, str, list[str]]] = [
    ("N.01", "Buloh Kasap",    ["Buloh Kasap", "Zahari Sarip", "Norazman Md Diah"]),
    ("N.02", "Jementah",       ["Jementah", "Ng Kor Sim", "See Ann Giap"]),
    ("N.03", "Pemanis",        ["Pemanis", "Anuar Abdul Manap", "Yoong Thau"]),
    ("N.04", "Kemelah",        ["Kemelah", "Saraswathy Nallathanby", "Sulaiman Mohd Nor"]),
    ("N.05", "Tenang",         ["Tenang", "Haslinda Salleh", "Lim Wei Jiet"]),
    ("N.06", "Bekok",          ["Bekok", "Tan Chong", "M Kanan"]),
    ("N.07", "Bukit Kepong",   ["Bukit Kepong", "Sahruddin Jamal", "Ismail Mohamed"]),
    ("N.08", "Bukit Pasir",    ["Bukit Pasir", "Fazli Salleh", "Iqbal Razak"]),
    ("N.09", "Gambir",         ["Gambir", "Sahrihan Jani", "Mohd Solihan Badri"]),
    ("N.10", "Tangkak",        ["Tangkak", "Ee Chin Li", "Ong Chee Siang"]),
    ("N.11", "Serom",          ["Serom", "Khairin Nisa", "Rahmat Daud"]),
    ("N.12", "Bentayan",       ["Bentayan", "Ng Yak Howe", "Gan Q'I Ru", "Eddy Tan"]),
    ("N.13", "Simpang Jeram",  ["Simpang Jeram", "Salahuddin Ayub", "Lokman Md Don"]),
    ("N.14", "Bukit Naning",   ["Bukit Naning", "Mohd Fuad Tukirin", "Mahadzir Abu Said"]),
    ("N.15", "Maharani",       ["Maharani", "Abdul Aziz Talib", "Nor Hayati Bachok"]),
    ("N.16", "Sungai Balang",  ["Sungai Balang", "Sg Balang", "Selamat Takim", "Zainuddin Sayuti"]),
    ("N.17", "Semerah",        ["Semerah", "Mohd Fared Mohd Khalid", "Ariss Samsudin"]),
    ("N.18", "Sri Medan",      ["Sri Medan", "Zulkurnain Kamisan", "Halim Othman"]),
    ("N.19", "Yong Peng",      ["Yong Peng", "Ling Tian Soon", "Alan Tee Boon Tsong"]),
    ("N.20", "Semarang",       ["Semarang", "Samsolbari Jamali", "Shazani A Hamid"]),
    ("N.21", "Parit Yaani",    ["Parit Yaani", "Mohamad Najib Samuri", "Aminolhuda Hassan"]),
    ("N.22", "Parit Raja",     ["Parit Raja", "Nor Rashidah Ramli", "Zulkifli Mat Daud"]),
    ("N.23", "Penggaram",      ["Penggaram", "Gan Peck Cheng", "Ter Hwa Kwong", "Ronald Sia"]),
    ("N.24", "Senggarang",     ["Senggarang", "Yusla Ismail", "Hamid Jamah"]),
    ("N.25", "Rengit",         ["Rengit", "Mohd Puad Zarkashi", "Mohammad Huzair"]),
    ("N.26", "Machap",         ["Machap", "Onn Hafiz Ghazi", "Azlisham Azahar"]),
    ("N.27", "Layang-Layang",  ["Layang-Layang", "Layang Layang", "Abd Mutalip Abd Rahim", "Maszlee Malik"]),
    ("N.28", "Mengkibol",      ["Mengkibol", "Chew Chong Sin", "Kelly Chye", "Wong Chan Giap"]),
    ("N.29", "Mahkota",        ["Mahkota", "Sharifah Azizah", "Muhammad Taqiuddin"]),
    ("N.30", "Paloh",          ["Paloh", "Lee Ting Han", "Sheikh Umar Bagharib"]),
    ("N.31", "Kahang",         ["Kahang", "R Vidyananthan", "Daud Yusof"]),
    ("N.32", "Endau",          ["Endau", "Alwiyah Talib", "Youzaimi Yusof"]),
    ("N.33", "Tenggaroh",      ["Tenggaroh", "Raven Kumar Krishnasamy", "Roslan Nikmat"]),
    ("N.34", "Panti",          ["Panti", "Hahasrin Hashim", "Hassan Rasid"]),
    ("N.35", "Pasir Raja",     ["Pasir Raja", "Rashidah Ismail", "Intan Jawahir"]),
    ("N.36", "Sedili",         ["Sedili", "Muszaide Makmor", "Hasnol Hadi"]),
    ("N.37", "Johor Lama",     ["Johor Lama", "Norlizah Noh", "Alias Rasman"]),
    ("N.38", "Penawar",        ["Penawar", "Fauziah Misri", "Mohd Faizal Asmar"]),
    ("N.39", "Tanjung Surat",  ["Tanjung Surat", "Aznan Tamin", "Selamat Daud"]),
    ("N.40", "Tiram",          ["Tiram", "Azizul Bachok", "Karim Deraman"]),
    ("N.41", "Puteri Wangsa",  ["Puteri Wangsa", "Amira Aisya Abdul Aziz", "Ng Yew Aik", "Loh Kah Yong"]),
    ("N.42", "Johor Jaya",     ["Johor Jaya", "Liow Cai Tung", "Chan San San"]),
    ("N.43", "Permas",         ["Permas", "Permas Jaya", "Baharudin Mohamed Taib", "Tazul Arifin"]),
    ("N.44", "Larkin",         ["Larkin", "Mohd Hairi Md Shah", "Zulkifli Bujang"]),
    ("N.45", "Stulang",        ["Stulang", "Andrew Chen Kah Eng", "Ang Boon Heng"]),
    ("N.46", "Perling",        ["Perling", "Liew Chin Tong", "Tan Hiang Kee"]),
    ("N.47", "Kempas",         ["Kempas", "Ramlee Bohani", "Napsiah Khamis"]),
    ("N.48", "Skudai",         ["Skudai", "Marina Ibrahim", "Lim Soon Hai"]),
    ("N.49", "Kota Iskandar",  ["Kota Iskandar", "Pandak Ahmad", "Dzulkefly Ahmad"]),
    ("N.50", "Bukit Permai",   ["Bukit Permai", "Mohd Jafni Md Shukor", "Azrol Ab Rahani"]),
    ("N.51", "Bukit Batu",     ["Bukit Batu", "Arthur Chiong", "Supayyah Solaimuthu"]),
    ("N.52", "Senai",          ["Senai", "Wong Bor Yang", "Kenny Shen"]),
    ("N.53", "Benut",          ["Benut", "Hasni Mohammad", "Isa Ab Hamid"]),
    ("N.54", "Pulai Sebatang", ["Pulai Sebatang", "Hasrunizah Hassan", "Suhaizan Kayat"]),
    ("N.55", "Pekan Nanas",    ["Pekan Nanas", "Tan Eng Meng", "Yeo Tung Siong"]),
    ("N.56", "Kukup",          ["Kukup", "Jefridin Atan", "Mahathir Iskandar"]),
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
