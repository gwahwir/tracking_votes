"""
Fetch and compile constituency demographics from Thevesh's census dataset.

Source: github.com/Thevesh/analysis-election-msia (census_dun.csv, census_parlimen.csv)
Data year: 2020 Census

Output: data/historical/johor_demographics.json

Usage:
    python scripts/scrape_demographics.py
"""
from __future__ import annotations

import json
import io
from pathlib import Path

import requests

DUN_CSV_URL = "https://raw.githubusercontent.com/Thevesh/analysis-election-msia/master/data/census_dun.csv"
PARLIMEN_CSV_URL = "https://raw.githubusercontent.com/Thevesh/analysis-election-msia/master/data/census_parlimen.csv"

HEADERS = {"User-Agent": "JohorElectionResearch/1.0 (academic project)"}
OUT_DIR = Path("data/historical")

# ---------------------------------------------------------------------------
# Region classification by Parlimen code
# ---------------------------------------------------------------------------

PARLIMEN_REGION: dict[str, str] = {
    "P.140": "north",   # Segamat
    "P.141": "north",   # Sekijang
    "P.142": "north",   # Labis
    "P.143": "north",   # Pagoh
    "P.144": "north",   # Ledang
    "P.145": "central", # Bakri
    "P.146": "central", # Muar
    "P.147": "west",    # Parit Sulong
    "P.148": "west",    # Ayer Hitam
    "P.149": "west",    # Sri Gading
    "P.150": "west",    # Batu Pahat
    "P.151": "central", # Simpang Renggam
    "P.152": "central", # Kluang
    "P.153": "north",   # Sembrong
    "P.154": "east",    # Mersing
    "P.155": "east",    # Tenggara
    "P.156": "east",    # Kota Tinggi
    "P.157": "east",    # Pengerang
    "P.158": "south",   # Tebrau
    "P.159": "south",   # Pasir Gudang
    "P.160": "south",   # Johor Bahru
    "P.161": "south",   # Pulai
    "P.162": "south",   # Iskandar Puteri
    "P.163": "south",   # Kulai
    "P.164": "west",    # Pontian
    "P.165": "west",    # Tanjung Piai
}

# DUN -> Parlimen mapping (for region lookup)
DUN_PARLIMEN: dict[str, str] = {
    "N.01": "P.140", "N.02": "P.140",
    "N.03": "P.141", "N.04": "P.141",
    "N.05": "P.142", "N.06": "P.142",
    "N.07": "P.143", "N.08": "P.143",
    "N.09": "P.144", "N.10": "P.144", "N.11": "P.144",
    "N.12": "P.145", "N.13": "P.145", "N.14": "P.145",
    "N.15": "P.146", "N.16": "P.146",
    "N.17": "P.147", "N.18": "P.147",
    "N.19": "P.148", "N.20": "P.148",
    "N.21": "P.149", "N.22": "P.149",
    "N.23": "P.150", "N.24": "P.150", "N.25": "P.150",
    "N.26": "P.151", "N.27": "P.151",
    "N.28": "P.152", "N.29": "P.152",
    "N.30": "P.153", "N.31": "P.153",
    "N.32": "P.154", "N.33": "P.154",
    "N.34": "P.155", "N.35": "P.155",
    "N.36": "P.156", "N.37": "P.156",
    "N.38": "P.157", "N.39": "P.157",
    "N.40": "P.158", "N.41": "P.158",
    "N.42": "P.159", "N.43": "P.159",
    "N.44": "P.160", "N.45": "P.160",
    "N.46": "P.161", "N.47": "P.161",
    "N.48": "P.162", "N.49": "P.162",
    "N.50": "P.163", "N.51": "P.163", "N.52": "P.163",
    "N.53": "P.164", "N.54": "P.164",
    "N.55": "P.165", "N.56": "P.165",
}


def _urban_rural(population_density: float) -> str:
    """
    Classify by population density (persons/km²) — a constituency-level proxy
    for the NRPP 2030 Rural Grid System typology (PLANMalaysia, 2017).

    Raw constituency population is always >20k so can't distinguish urban/rural;
    density captures settlement character instead.

    Thresholds calibrated to Johor DUN distribution:
      urban      ≥ 500 /km²   (Johor Bahru, Pasir Gudang area)
      semi-urban  200–499 /km² (mixed peri-urban)
      rural       < 200 /km²   (interior/coastal agricultural)
    """
    if population_density >= 500:
        return "urban"
    elif population_density >= 200:
        return "semi-urban"
    else:
        return "rural"


def _safe_float(val: str) -> float | None:
    try:
        return float(val) if val.strip() else None
    except (ValueError, AttributeError):
        return None


def _safe_int(val: str) -> int | None:
    try:
        return int(float(val)) if val.strip() else None
    except (ValueError, AttributeError):
        return None


def fetch_csv(url: str) -> list[dict]:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    lines = r.text.splitlines()
    headers = lines[0].split(",")
    rows = []
    for line in lines[1:]:
        values = line.split(",")
        # pad if row is shorter than header
        while len(values) < len(headers):
            values.append("")
        rows.append(dict(zip(headers, values)))
    return rows


def process_dun(rows: list[dict]) -> dict:
    seats = {}
    johor_rows = [r for r in rows if r.get("state") == "Johor"]
    print(f"  Johor DUN rows found: {len(johor_rows)}")

    for row in johor_rows:
        code = row.get("code_dun", "").strip()
        if not code:
            continue

        name_full = row.get("dun", "").strip()
        # "N.01 Buloh Kasap" -> "Buloh Kasap"
        name = name_full.split(" ", 1)[1] if " " in name_full else name_full

        pop_total = _safe_int(row.get("population_total", "")) or 1
        area_km2 = _safe_float(row.get("area_km2", "")) or 1
        density = pop_total / area_km2

        income_median = _safe_float(row.get("income_median", "")) or 0

        parlimen_code = DUN_PARLIMEN.get(code, "")
        region = PARLIMEN_REGION.get(parlimen_code, "unknown")

        seats[code] = {
            "name": name,
            "seat_type": "dun",
            "parlimen": parlimen_code,
            "state": "Johor",
            "malay_pct": round(_safe_float(row.get("ethnicity_proportion_bumi", "")) or 0, 1),
            "chinese_pct": round(_safe_float(row.get("ethnicity_proportion_chinese", "")) or 0, 1),
            "indian_pct": round(_safe_float(row.get("ethnicity_proportion_indian", "")) or 0, 1),
            "others_pct": round(_safe_float(row.get("ethnicity_proportion_other", "")) or 0, 1),
            "population": pop_total,
            "area_km2": round(area_km2, 1),
            "population_density": round(density, 1),
            "income_median": income_median,
            "urban_rural": _urban_rural(density),
            "region": region,
            "data_year": 2020,
            "source": "Thevesh/analysis-election-msia (census_dun.csv)",
        }

    return seats


def process_parlimen(rows: list[dict]) -> dict:
    seats = {}
    johor_rows = [r for r in rows if r.get("state") == "Johor"]
    print(f"  Johor Parlimen rows found: {len(johor_rows)}")

    for row in johor_rows:
        code = row.get("code_parlimen", "").strip()
        if not code:
            continue

        name_full = row.get("parlimen", "").strip()
        name = name_full.split(" ", 1)[1] if " " in name_full else name_full

        pop_total = _safe_int(row.get("population_total", "")) or 1
        area_km2 = _safe_float(row.get("area_km2", "")) or 1
        density = pop_total / area_km2
        income_median = _safe_float(row.get("income_median", "")) or 0

        region = PARLIMEN_REGION.get(code, "unknown")

        seats[code] = {
            "name": name,
            "seat_type": "parlimen",
            "state": "Johor",
            "malay_pct": round(_safe_float(row.get("ethnicity_proportion_bumi", "")) or 0, 1),
            "chinese_pct": round(_safe_float(row.get("ethnicity_proportion_chinese", "")) or 0, 1),
            "indian_pct": round(_safe_float(row.get("ethnicity_proportion_indian", "")) or 0, 1),
            "others_pct": round(_safe_float(row.get("ethnicity_proportion_other", "")) or 0, 1),
            "population": pop_total,
            "area_km2": round(area_km2, 1),
            "population_density": round(density, 1),
            "income_median": income_median,
            "urban_rural": _urban_rural(density),
            "region": region,
            "data_year": 2020,
            "source": "Thevesh/analysis-election-msia (census_parlimen.csv)",
        }

    return seats


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching DUN census data...")
    dun_rows = fetch_csv(DUN_CSV_URL)
    dun_seats = process_dun(dun_rows)

    print("Fetching Parlimen census data...")
    par_rows = fetch_csv(PARLIMEN_CSV_URL)
    par_seats = process_parlimen(par_rows)

    all_seats = {**dun_seats, **par_seats}

    output = {
        "metadata": {
            "state": "Johor",
            "data_year": 2020,
            "source": "Thevesh/analysis-election-msia on GitHub (2020 Malaysian Census)",
            "note": "Bumiputera % used as proxy for Malay %; includes non-Malay Bumiputera (Orang Asli etc.) which are <1% in Johor",
            "urban_rural_method": "population density + median income thresholds",
            "last_updated": "2026-04-20",
        },
        "seats": all_seats,
    }

    out_path = OUT_DIR / "johor_demographics.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved -> {out_path}")

    # Summary
    urban_counts = {}
    for s in all_seats.values():
        ur = s["urban_rural"]
        urban_counts[ur] = urban_counts.get(ur, 0) + 1

    print(f"\n=== Summary ({len(all_seats)} seats total) ===")
    print(f"DUN: {len(dun_seats)}, Parlimen: {len(par_seats)}")
    print(f"Urban/rural breakdown: {urban_counts}")

    # Spot check
    print("\n=== Sample seats ===")
    for code in ["N.01", "N.42", "N.44", "N.53", "P.160", "P.165"]:
        s = all_seats.get(code)
        if s:
            print(f"  {code} {s['name']}: malay={s['malay_pct']}% chinese={s['chinese_pct']}% indian={s['indian_pct']}% | {s['urban_rural']} | {s['region']} | density={s['population_density']}/km²")


if __name__ == "__main__":
    main()
