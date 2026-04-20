# Updating Historical Election Results and Demographics Data

This document tells a new Claude instance exactly what to do when the user has updated datasets to load into the Johor election monitoring database.

---

## Overview of the data pipeline

```
scripts/scrape_historical.py   → data/historical/johor_dun_results.json
                                  data/historical/johor_parlimen_results.json

scripts/scrape_demographics.py → data/historical/johor_demographics.json

scripts/ingest_historical.py   → PostgreSQL (tables: historical_results, constituency_demographics)
```

All three JSON files feed into a single ingest script that upserts via delete+insert. Re-running the ingest is always safe — it clears existing rows for the same constituency+year before inserting.

---

## Case 1 — Updated election results (historical_results table)

### Option A: Re-scrape from Wikipedia (automated)

Run the scraper to regenerate the JSON files:

```bash
PYTHONPATH=. python scripts/scrape_historical.py
```

This fetches per-constituency Wikipedia pages and writes `johor_dun_results.json` and `johor_parlimen_results.json`. It takes 5–10 minutes due to a 1-second polite delay between requests.

If a new election year needs to be added (e.g. 2027), open `scripts/scrape_historical.py` and add the year to `TARGET_YEARS`:

```python
TARGET_YEARS: set[int] = {2018, 2022, 2027}   # add new year here
```

Wikipedia constituency pages for Johor DUN follow the pattern:
`https://en.wikipedia.org/wiki/<Name>_(state_constituency)`

If a seat's page has a disambiguation suffix or non-standard title, add it to `DUN_WIKI_OVERRIDES` or `PARLIMEN_WIKI_OVERRIDES` in the same script.

### Option B: Manual JSON update (if user provides corrected data)

Edit the relevant JSON file directly. Each file has this structure:

```jsonc
// data/historical/johor_dun_results.json  (or johor_parlimen_results.json)
{
  "metadata": { ... },
  "seats": {
    "N.01": {
      "name": "Buloh Kasap",
      "parlimen": "P.140",
      "results": {
        "2022": {
          "winner_name": "...",
          "winner_party": "BN",
          "winner_coalition": "BN",
          "winner_votes": 8956,
          "margin": 5377,
          "margin_pct": 34.2,
          "turnout_pct": 57.1,
          "total_voters": 28481,
          "total_votes_cast": 15724,
          "num_candidates": 4,
          "candidates": [
            { "name": "...", "party": "BN", "coalition": "BN", "votes": 8956 },
            ...
          ]
        }
      }
    }
  }
}
```

Seat codes:
- DUN: `"N.01"` through `"N.56"` (dotted format — must match exactly)
- Parlimen: `"P.140"` through `"P.165"`

Coalition values used in the codebase: `"BN"`, `"PH"`, `"PN"`, `"GPS"`, `"GRS"`, `"MUDA"`, `"PEJUANG"`, `"IND"`.

After editing the JSON, skip to the **Ingest** step below.

---

## Case 2 — Updated demographics (constituency_demographics table)

### Option A: Re-scrape from Thevesh's census dataset (automated)

```bash
PYTHONPATH=. python scripts/scrape_demographics.py
```

Source: `github.com/Thevesh/analysis-election-msia` — `census_dun.csv` and `census_parlimen.csv` (2020 Malaysian Census).

Output: `data/historical/johor_demographics.json`

The script classifies urban/rural by **population density** using these thresholds (calibrated for Johor DUN scale):

| Classification | Density (persons/km²) |
|---|---|
| urban | ≥ 500 |
| semi-urban | 200–499 |
| rural | < 200 |

This replaces the earlier population-count approach (which put every constituency in "urban" because DUN populations are always >20k). The density proxy aligns with the spirit of the NRPP 2030 Rural Grid System typology (PLANMalaysia, 2017).

### Option B: Manual JSON update (if user provides corrected census figures)

Edit `data/historical/johor_demographics.json`. Each seat entry looks like:

```jsonc
{
  "metadata": { "state": "Johor", "data_year": 2020, ... },
  "seats": {
    "N.01": {
      "name": "Buloh Kasap",
      "seat_type": "dun",
      "parlimen": "P.140",
      "state": "Johor",
      "malay_pct": 61.2,
      "chinese_pct": 29.4,
      "indian_pct": 9.1,
      "others_pct": 0.4,
      "population": 31956,
      "area_km2": 594.0,
      "population_density": 53.8,
      "income_median": 5645.0,
      "urban_rural": "rural",
      "region": "north",
      "data_year": 2020,
      "source": "..."
    }
  }
}
```

`region` values: `"north"`, `"central"`, `"south"`, `"east"`, `"west"`.

`urban_rural` values: `"urban"`, `"semi-urban"`, `"rural"`.

The `malay_pct` field uses **Bumiputera %** as a proxy — it includes non-Malay Bumiputera (Orang Asli, etc.) which are <1% in Johor.

---

## Ingest into PostgreSQL

After updating any of the JSON files, run:

```bash
PYTHONPATH=. python scripts/ingest_historical.py
```

**Requires:**
- Docker Compose running (`docker-compose up -d`)
- `.env` file at project root with `DATABASE_URL=postgresql://...`
- Run from the project root (`c:/Users/user/tracking_votes`)

The script:
1. Creates tables if missing (idempotent)
2. For historical results: deletes existing rows for each `(constituency_code, election_year)` pair, then inserts fresh
3. For demographics: deletes existing row for each `constituency_code`, then inserts fresh

Expected output for a full reload:

```
Schema ready.
DUN:      90 records inserted, 0 seats skipped (no data)
Parlimen: 52 records inserted, 0 seats skipped (no data)
Demo:     82 records inserted
...
Total records loaded: 224
```

If counts are lower, check the JSON files for missing `results` blocks or missing seat codes.

---

## Database schema reference

**`historical_results`**

| Column | Type | Notes |
|---|---|---|
| constituency_code | VARCHAR(16) | `"N.01"`, `"P.140"`, etc. |
| seat_type | VARCHAR(16) | `"dun"` or `"parlimen"` |
| election_year | INTEGER | e.g. `2022` |
| winner_party | VARCHAR(64) | Party abbreviation |
| winner_coalition | VARCHAR(64) | Coalition abbreviation |
| margin | INTEGER | Vote margin |
| margin_pct | FLOAT | Margin as % of votes cast |
| turnout_pct | FLOAT | Turnout % |
| candidates | JSON | Array of `{name, party, coalition, votes}` |

**`constituency_demographics`**

| Column | Type | Notes |
|---|---|---|
| constituency_code | VARCHAR(16) | Unique — one row per seat |
| malay_pct | FLOAT | Bumiputera % (2020 Census) |
| chinese_pct | FLOAT | |
| indian_pct | FLOAT | |
| urban_rural | VARCHAR(32) | `"urban"`, `"semi-urban"`, `"rural"` |
| region | VARCHAR(32) | `"north"`, `"central"`, `"south"`, `"east"`, `"west"` |

Full model definitions: `agents/base/models.py` — `HistoricalResult` and `ConstituencyDemographics`.

---

## API endpoints (after ingest)

The control plane exposes these read endpoints (no restart needed after data reload):

- `GET /historical/{constituency_code}` — results for one seat across all years
- `GET /historical?seat_type=dun&year=2022` — filtered results
- `GET /demographics/{constituency_code}` — demographics for one seat

Defined in `control_plane/routes.py`.
