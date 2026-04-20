"""
Scrape Johor election historical data from Wikipedia.

Fetches results for each of the 56 DUN seats and 26 Parlimen seats
across the 2018 and 2022 elections.

Usage:
    python scripts/scrape_historical.py

Output:
    data/historical/johor_dun_results.json
    data/historical/johor_parlimen_results.json

Run time: ~5-10 minutes (56 + 26 pages, polite 1s delay between requests).
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Seat definitions from GeoJSON (authoritative names and codes)
# ---------------------------------------------------------------------------

DUN_SEATS = [
    ("N.01", "Buloh Kasap",     "P.140"),
    ("N.02", "Jementah",        "P.140"),
    ("N.03", "Pemanis",         "P.141"),
    ("N.04", "Kemelah",         "P.141"),
    ("N.05", "Tenang",          "P.142"),
    ("N.06", "Bekok",           "P.142"),
    ("N.07", "Bukit Kepong",    "P.143"),
    ("N.08", "Bukit Pasir",     "P.143"),
    ("N.09", "Gambir",          "P.144"),
    ("N.10", "Tangkak",         "P.144"),
    ("N.11", "Serom",           "P.144"),
    ("N.12", "Bentayan",        "P.145"),
    ("N.13", "Simpang Jeram",   "P.145"),
    ("N.14", "Bukit Naning",    "P.145"),
    ("N.15", "Maharani",        "P.146"),
    ("N.16", "Sungai Balang",   "P.146"),
    ("N.17", "Semerah",         "P.147"),
    ("N.18", "Sri Medan",       "P.147"),
    ("N.19", "Yong Peng",       "P.148"),
    ("N.20", "Semarang",        "P.148"),
    ("N.21", "Parit Yaani",     "P.149"),
    ("N.22", "Parit Raja",      "P.149"),
    ("N.23", "Penggaram",       "P.150"),
    ("N.24", "Senggarang",      "P.150"),
    ("N.25", "Rengit",          "P.150"),
    ("N.26", "Machap",          "P.151"),
    ("N.27", "Layang-Layang",   "P.151"),
    ("N.28", "Mengkibol",       "P.152"),
    ("N.29", "Mahkota",         "P.152"),
    ("N.30", "Paloh",           "P.153"),
    ("N.31", "Kahang",          "P.153"),
    ("N.32", "Endau",           "P.154"),
    ("N.33", "Tenggaroh",       "P.154"),
    ("N.34", "Panti",           "P.155"),
    ("N.35", "Pasir Raja",      "P.155"),
    ("N.36", "Sedili",          "P.156"),
    ("N.37", "Johor Lama",      "P.156"),
    ("N.38", "Penawar",         "P.157"),
    ("N.39", "Tanjung Surat",   "P.157"),
    ("N.40", "Tiram",           "P.158"),
    ("N.41", "Puteri Wangsa",   "P.158"),
    ("N.42", "Johor Jaya",      "P.159"),
    ("N.43", "Permas",          "P.159"),
    ("N.44", "Larkin",          "P.160"),
    ("N.45", "Stulang",         "P.160"),
    ("N.46", "Perling",         "P.161"),
    ("N.47", "Kempas",          "P.161"),
    ("N.48", "Skudai",          "P.162"),
    ("N.49", "Kota Iskandar",   "P.162"),
    ("N.50", "Bukit Permai",    "P.163"),
    ("N.51", "Bukit Batu",      "P.163"),
    ("N.52", "Senai",           "P.163"),
    ("N.53", "Benut",           "P.164"),
    ("N.54", "Pulai Sebatang",  "P.164"),
    ("N.55", "Pekan Nanas",     "P.165"),
    ("N.56", "Kukup",           "P.165"),
]

PARLIMEN_SEATS = [
    ("P.140", "Segamat"),
    ("P.141", "Sekijang"),
    ("P.142", "Labis"),
    ("P.143", "Pagoh"),
    ("P.144", "Ledang"),
    ("P.145", "Bakri"),
    ("P.146", "Muar"),
    ("P.147", "Parit Sulong"),
    ("P.148", "Ayer Hitam"),
    ("P.149", "Sri Gading"),
    ("P.150", "Batu Pahat"),
    ("P.151", "Simpang Renggam"),
    ("P.152", "Kluang"),
    ("P.153", "Sembrong"),
    ("P.154", "Mersing"),
    ("P.155", "Tenggara"),
    ("P.156", "Kota Tinggi"),
    ("P.157", "Pengerang"),
    ("P.158", "Tebrau"),
    ("P.159", "Pasir Gudang"),
    ("P.160", "Johor Bahru"),
    ("P.161", "Pulai"),
    ("P.162", "Iskandar Puteri"),
    ("P.163", "Kulai"),
    ("P.164", "Pontian"),
    ("P.165", "Tanjung Piai"),
]

# Manual URL overrides for seats where the Wikipedia page title differs
DUN_WIKI_OVERRIDES: dict[str, str] = {
    "N.27": "Layang-Layang_(state_constituency)",  # avoid Layang-layang duplicate
    "N.30": "Paloh_(Johor_state_constituency)",    # disambiguated
    "N.13": None,   # Simpang Jeram - may not have a page; will try auto
    "N.20": None,   # Semarang - will try auto
}

PARLIMEN_WIKI_OVERRIDES: dict[str, str] = {
    "P.151": "Simpang_Renggam_(federal_constituency)",
}

TARGET_YEARS = {2022, 2018}
STATE_ELECTION_YEARS = {2022, 2018}   # Johor state elections
PARLIMEN_ELECTION_YEARS = {2022, 2018}  # GE15=2022, GE14=2018

HEADERS = {"User-Agent": "JohorElectionResearch/1.0 (academic project)"}
DELAY = 1.2  # seconds between requests


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def fetch(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except Exception as exc:
        print(f"  ERROR fetching {url}: {exc}")
        return None


def wiki_url(page: str) -> str:
    return f"https://en.wikipedia.org/wiki/{page}"


def dun_wiki_page(name: str, code: str) -> str:
    """Build Wikipedia page slug for a DUN seat."""
    if code in DUN_WIKI_OVERRIDES:
        override = DUN_WIKI_OVERRIDES[code]
        return override  # None means fall through to auto
    slug = name.replace(" ", "_")
    return f"{slug}_(state_constituency)"


def parlimen_wiki_page(name: str, code: str) -> str:
    if code in PARLIMEN_WIKI_OVERRIDES:
        return PARLIMEN_WIKI_OVERRIDES[code]
    slug = name.replace(" ", "_")
    return f"{slug}_(federal_constituency)"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_int(text: str) -> int | None:
    """Parse '10,896' -> 10896."""
    cleaned = re.sub(r"[^\d]", "", text)
    return int(cleaned) if cleaned else None


def _parse_float(text: str) -> float | None:
    cleaned = re.sub(r"[^\d.]", "", text)
    try:
        return float(cleaned)
    except ValueError:
        return None


def _year_from_caption(caption: str) -> int | None:
    m = re.search(r"\b(20\d\d|19\d\d)\b", caption)
    return int(m.group(1)) if m else None


# Known party-to-coalition mappings
PARTY_COALITION: dict[str, str] = {
    "UMNO": "BN", "MCA": "BN", "MIC": "BN", "GERAKAN": "BN",
    "BN": "BN",
    "PKR": "PH", "DAP": "PH", "AMANAH": "PH", "BERSATU": "PH",  # Bersatu was in PH pre-2020
    "PH": "PH",
    "PAS": "PN", "BERSATU": "PN",  # post-2020
    "PN": "PN",
    "PEJUANG": "IND", "MUDA": "PH", "PSM": "IND",
    "IND": "IND", "BEBAS": "IND",
}

def _coalition(party: str, year: int) -> str:
    p = party.upper().strip()
    # Bersatu was in PH in 2018, moved to PN after 2020
    if p == "BERSATU":
        return "PH" if year <= 2018 else "PN"
    return PARTY_COALITION.get(p, p)


def parse_results_table(table, year: int) -> dict | None:
    """
    Parse a single election results wikitable.

    Returns a dict with keys:
        candidates, winner_name, winner_party, winner_coalition,
        winner_votes, total_votes_cast, total_voters, turnout_pct, margin,
        margin_pct, num_candidates
    or None if parsing fails.
    """
    rows = table.find_all("tr")
    candidates = []
    total_votes_cast = None
    total_voters = None
    turnout_votes = None
    turnout_pct = None
    majority_votes = None
    majority_pct = None

    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
        if not cells:
            continue

        first = cells[0].lower()

        if "total valid" in first or "total votes" in first:
            if len(cells) >= 2:
                total_votes_cast = _parse_int(cells[1])

        elif "turnout" in first:
            if len(cells) >= 2:
                turnout_votes = _parse_int(cells[1])
            if len(cells) >= 3:
                turnout_pct = _parse_float(cells[2])

        elif "registered" in first or "electorate" in first or "electors" in first:
            if len(cells) >= 2:
                total_voters = _parse_int(cells[1])

        elif "majority" in first:
            if len(cells) >= 2:
                majority_votes = _parse_int(cells[1])
            if len(cells) >= 3:
                majority_pct = _parse_float(cells[2])

        else:
            # Candidate row: [img?, coalition_or_party, candidate, votes, %, delta%]
            # Wikipedia tables vary; try to detect candidate rows
            # Typical: cells[0]='' (img), cells[1]=party, cells[2]=name, cells[3]=votes, cells[4]=%
            # Or: cells[0]=party, cells[1]=name, cells[2]=votes, cells[3]=%
            party = None
            name = None
            votes = None

            # Skip header rows
            if any(h in first for h in ["party", "candidate", "coalition"]):
                continue

            # Detect img placeholder (empty first cell)
            offset = 0
            if cells[0] == "" and len(cells) > 3:
                offset = 1

            if len(cells) - offset >= 3:
                party_raw = cells[offset]
                name_raw = cells[offset + 1]
                votes_raw = cells[offset + 2] if len(cells) > offset + 2 else ""

                votes = _parse_int(votes_raw)
                if votes is not None and votes > 0 and party_raw and name_raw:
                    # Clean party: sometimes "BN(UMNO)" -> extract inner
                    inner = re.search(r"\(([^)]+)\)", party_raw)
                    party = inner.group(1).upper() if inner else party_raw.upper().strip()
                    # Remove citation markers [1]
                    party = re.sub(r"\[\d+\]", "", party).strip()
                    name = re.sub(r"\[\d+\]", "", name_raw).strip()
                    candidates.append({
                        "name": name,
                        "party": party,
                        "coalition": _coalition(party, year),
                        "votes": votes,
                    })

    if not candidates:
        return None

    # Sort by votes descending; winner is first
    candidates.sort(key=lambda c: c["votes"], reverse=True)
    winner = candidates[0]
    runner_up_votes = candidates[1]["votes"] if len(candidates) > 1 else 0

    if total_votes_cast is None:
        total_votes_cast = sum(c["votes"] for c in candidates)

    margin = majority_votes if majority_votes is not None else (winner["votes"] - runner_up_votes)
    marg_pct = majority_pct if majority_pct is not None else (
        round(margin / total_votes_cast * 100, 2) if total_votes_cast else None
    )

    return {
        "winner_name": winner["name"],
        "winner_party": winner["party"],
        "winner_coalition": winner["coalition"],
        "winner_votes": winner["votes"],
        "margin": margin,
        "margin_pct": marg_pct,
        "turnout_pct": turnout_pct,
        "total_voters": total_voters,
        "total_votes_cast": total_votes_cast,
        "num_candidates": len(candidates),
        "candidates": candidates,
    }


def parse_seat_page(soup: BeautifulSoup, target_years: set) -> dict[int, dict]:
    """Parse all election results tables from a constituency page."""
    tables = soup.find_all("table", class_="wikitable")
    results: dict[int, dict] = {}

    for table in tables:
        caption = table.find("caption")
        if not caption:
            continue
        caption_text = caption.get_text(strip=True)
        year = _year_from_caption(caption_text)
        if year not in target_years:
            continue
        parsed = parse_results_table(table, year)
        if parsed:
            results[year] = parsed

    return results


# ---------------------------------------------------------------------------
# Main scraping loops
# ---------------------------------------------------------------------------

def scrape_dun_seats() -> dict:
    """Scrape all 56 Johor DUN seats."""
    output = {
        "metadata": {
            "state": "Johor",
            "seat_type": "dun",
            "elections": ["2018", "2022"],
            "source": "Wikipedia (en.wikipedia.org)",
            "last_updated": "2026-04-20",
            "notes": "Scraped automatically; verify against SPR official results",
        },
        "seats": {},
    }

    missing_pages = []
    partial_data = []

    for code, name, parlimen_code in DUN_SEATS:
        print(f"  {code} {name} ...", end=" ", flush=True)

        # Build candidate URLs to try
        pages_to_try = []
        override = DUN_WIKI_OVERRIDES.get(code, "AUTO")
        if override is None:
            # Auto-generate slug only
            slug = name.replace(" ", "_")
            pages_to_try = [f"{slug}_(state_constituency)"]
        elif override == "AUTO":
            slug = name.replace(" ", "_")
            pages_to_try = [f"{slug}_(state_constituency)"]
        else:
            pages_to_try = [override]

        # Also try without parenthetical disambiguation
        slug = name.replace(" ", "_")
        pages_to_try.append(f"{slug}_(Johor_state_constituency)")

        soup = None
        used_url = None
        for page in pages_to_try:
            url = wiki_url(page)
            soup = fetch(url)
            if soup:
                used_url = url
                break
            time.sleep(0.3)

        if not soup:
            print(f"NOT FOUND")
            missing_pages.append((code, name))
            output["seats"][code] = {
                "name": name,
                "parlimen": parlimen_code,
                "results": {},
                "_scrape_status": "page_not_found",
            }
            time.sleep(DELAY)
            continue

        results = parse_seat_page(soup, TARGET_YEARS)
        found_years = sorted(results.keys(), reverse=True)
        print(f"OK years={found_years} url={used_url.split('/')[-1]}")

        if not found_years:
            partial_data.append((code, name, "no results tables parsed"))
        elif len(found_years) < 2:
            partial_data.append((code, name, f"only {found_years}"))

        output["seats"][code] = {
            "name": name,
            "parlimen": parlimen_code,
            "results": {str(y): results[y] for y in found_years},
            "_scrape_status": "ok" if len(found_years) == 2 else f"partial:{found_years}",
            "_source_url": used_url,
        }

        time.sleep(DELAY)

    print(f"\nDUN scrape complete.")
    if missing_pages:
        print(f"MISSING PAGES ({len(missing_pages)}): {[f'{c} {n}' for c,n in missing_pages]}")
    if partial_data:
        print(f"PARTIAL DATA ({len(partial_data)}):")
        for code, name, reason in partial_data:
            print(f"  {code} {name}: {reason}")

    return output


def scrape_parlimen_seats() -> dict:
    """Scrape all 26 Johor Parlimen seats (GE13/14/15)."""
    output = {
        "metadata": {
            "state": "Johor",
            "seat_type": "parlimen",
            "elections": ["2018", "2022"],
            "source": "Wikipedia (en.wikipedia.org)",
            "last_updated": "2026-04-20",
            "notes": "GE13=2013, GE14=2018, GE15=2022. Scraped automatically; verify against SPR.",
        },
        "seats": {},
    }

    missing_pages = []
    partial_data = []

    for code, name in PARLIMEN_SEATS:
        print(f"  {code} {name} ...", end=" ", flush=True)

        pages_to_try = []
        override = PARLIMEN_WIKI_OVERRIDES.get(code)
        if override:
            pages_to_try = [override]
        slug = name.replace(" ", "_")
        pages_to_try.append(f"{slug}_(federal_constituency)")
        pages_to_try.append(f"{slug}_(Johor)")

        soup = None
        used_url = None
        for page in pages_to_try:
            url = wiki_url(page)
            soup = fetch(url)
            if soup:
                used_url = url
                break
            time.sleep(0.3)

        if not soup:
            print(f"NOT FOUND")
            missing_pages.append((code, name))
            output["seats"][code] = {
                "name": name,
                "results": {},
                "_scrape_status": "page_not_found",
            }
            time.sleep(DELAY)
            continue

        results = parse_seat_page(soup, TARGET_YEARS)
        found_years = sorted(results.keys(), reverse=True)
        print(f"OK years={found_years} url={used_url.split('/')[-1]}")

        if not found_years:
            partial_data.append((code, name, "no results tables parsed"))
        elif len(found_years) < 2:
            partial_data.append((code, name, f"only {found_years}"))

        output["seats"][code] = {
            "name": name,
            "results": {str(y): results[y] for y in found_years},
            "_scrape_status": "ok" if len(found_years) == 2 else f"partial:{found_years}",
            "_source_url": used_url,
        }

        time.sleep(DELAY)

    print(f"\nParlimen scrape complete.")
    if missing_pages:
        print(f"MISSING PAGES ({len(missing_pages)}): {[f'{c} {n}' for c,n in missing_pages]}")
    if partial_data:
        print(f"PARTIAL DATA ({len(partial_data)}):")
        for code, name, reason in partial_data:
            print(f"  {code} {name}: {reason}")

    return output


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    out_dir = Path("data/historical")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== Scraping Johor DUN seats (56 seats x 3 elections) ===")
    dun_data = scrape_dun_seats()
    dun_path = out_dir / "johor_dun_results.json"
    dun_path.write_text(json.dumps(dun_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved -> {dun_path}")

    print("\n=== Scraping Johor Parlimen seats (26 seats x 3 elections) ===")
    parlimen_data = scrape_parlimen_seats()
    parlimen_path = out_dir / "johor_parlimen_results.json"
    parlimen_path.write_text(json.dumps(parlimen_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved -> {parlimen_path}")

    # Summary
    dun_ok = sum(1 for v in dun_data["seats"].values() if v.get("_scrape_status") == "ok")
    par_ok = sum(1 for v in parlimen_data["seats"].values() if v.get("_scrape_status") == "ok")
    print(f"\n=== Summary ===")
    print(f"DUN:      {dun_ok}/56 seats with full 2-election data (2018+2022)")
    print(f"Parlimen: {par_ok}/26 seats with full 2-election data (2018+2022)")
    print(f"\nCheck _scrape_status fields in the JSON for any gaps.")
    print(f"Fields marked 'partial' or 'page_not_found' need manual filling.")


if __name__ == "__main__":
    main()
