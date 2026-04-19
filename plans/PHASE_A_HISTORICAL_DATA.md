# Phase A: Historical Election Data Ingestion

## Goal

Populate the system with structured, seat-level historical election results for Johor so that the seat_agent, analyst_agent, and wiki knowledge base have real baselines to anchor predictions against. Without this data, predictions are ungrounded LLM speculation.

---

## Context: What Exists Today

- **Wiki concept pages** exist for parties (6 files in `wiki/entities/parties/`) and political concepts (5 files in `wiki/concepts/`), including `johor-state-election-2022.md` with coalition-level results (BN 40, PH 12, PN 3, MUDA 1).
- **Wiki constituency and candidate directories do NOT exist** — `wiki/entities/constituencies/` and `wiki/entities/candidates/` are referenced in the plan but never created.
- **GeoJSON** has all 56 DUN seats (property `code_dun` e.g. `"N.01"`) and 26 Parlimen seats (property `code_parlimen` e.g. `"P.140"`).
- **The seat_agent** (`agents/seat_agent/graph.py`) has a `load_baseline` node (line 92) that currently returns a **mock** — `historical_winners: {}`, `voter_demographics: {}`. This is the primary integration point.
- **The constituency_tagger** (`agents/news_agent/constituency_tagger.py`) maps keywords to seat codes. DUN codes use format `N01`-`N56` (no dot), Parlimen uses `P140`-`P165`.

---

## Data Required

### 1. Johor DUN Historical Results (56 seats x 3 elections)

For each of the 56 DUN seats, across the **2013**, **2018**, and **2022** state elections:

| Field | Type | Example |
|-------|------|---------|
| `code_dun` | string | `"N.01"` |
| `seat_name` | string | `"Buloh Kasap"` |
| `year` | int | `2022` |
| `winner_party` | string | `"BN"` / `"UMNO"` |
| `winner_coalition` | string | `"BN"` |
| `winner_name` | string | `"Ahmad bin Abdullah"` |
| `winner_votes` | int | `12345` |
| `margin` | int | `2500` (votes over runner-up) |
| `margin_pct` | float | `8.5` (percentage margin) |
| `turnout_pct` | float | `65.2` |
| `total_voters` | int | `25000` |
| `total_votes_cast` | int | `16300` |
| `num_candidates` | int | `4` |
| `candidates` | list | `[{name, party, coalition, votes}, ...]` |

### 2. Johor Parlimen Historical Results (26 seats x 3 elections)

Same schema as DUN but for **GE13 (2013)**, **GE14 (2018)**, and **GE15 (2022)** using `code_parlimen` format.

### 3. Demographic Data Per Seat

| Field | Type | Example |
|-------|------|---------|
| `code` | string | `"N.01"` |
| `malay_pct` | float | `65.0` |
| `chinese_pct` | float | `25.0` |
| `indian_pct` | float | `7.0` |
| `others_pct` | float | `3.0` |
| `urban_rural` | string | `"semi-urban"` |
| `region` | string | `"north"` / `"central"` / `"south"` |

### Data Sources

- **SPR (Election Commission of Malaysia)** — official results (keputusan.spr.gov.my)
- **Wikipedia** — "2022 Johor state election", "Malaysian general election 2022, results by state"
- **Undi.info** — community-maintained election data
- **Tindak Malaysia** — constituency demographic profiles

---

## Implementation Steps

### Step 1: Create the data directory and schema

Create `data/historical/` directory with structured JSON files:

```
data/
  historical/
    johor_dun_results.json      # All 56 DUN seats x 3 elections
    johor_parlimen_results.json  # All 26 Parlimen seats x 3 elections
    johor_demographics.json      # Per-seat demographic breakdown
    schema.md                    # Documents the data format
```

**File format for `johor_dun_results.json`:**

```json
{
  "metadata": {
    "state": "Johor",
    "seat_type": "dun",
    "elections": ["2013", "2018", "2022"],
    "source": "SPR, Wikipedia, Undi.info",
    "last_updated": "2026-04-20"
  },
  "seats": {
    "N.01": {
      "name": "Buloh Kasap",
      "parlimen": "P.140",
      "results": {
        "2022": {
          "winner": {"name": "...", "party": "UMNO", "coalition": "BN", "votes": 12345},
          "margin": 2500,
          "margin_pct": 8.5,
          "turnout_pct": 55.2,
          "total_voters": 25000,
          "total_votes_cast": 13800,
          "candidates": [
            {"name": "...", "party": "UMNO", "coalition": "BN", "votes": 12345},
            {"name": "...", "party": "PKR", "coalition": "PH", "votes": 9845},
            {"name": "...", "party": "Bersatu", "coalition": "PN", "votes": 1610}
          ]
        },
        "2018": { ... },
        "2013": { ... }
      }
    },
    "N.02": { ... }
  }
}
```

### Step 2: Build a data ingestion script

Create `scripts/ingest_historical.py` that:

1. Reads the JSON files from `data/historical/`
2. Creates a new `historical_results` table in PostgreSQL (or reuses an existing approach)
3. Loads all results into the database

**New SQLAlchemy model** — add to `agents/base/models.py`:

```python
class HistoricalResult(Base):
    """Historical election result for a constituency."""
    __tablename__ = "historical_results"

    id = Column(String(36), primary_key=True)
    constituency_code = Column(String(16), nullable=False, index=True)  # "N.01", "P.140"
    seat_type = Column(String(16), nullable=False)  # "dun" or "parlimen"
    seat_name = Column(String(128), nullable=False)
    election_year = Column(Integer, nullable=False, index=True)
    state = Column(String(64), nullable=False, default="Johor")

    # Winner
    winner_name = Column(String(256), nullable=True)
    winner_party = Column(String(64), nullable=True)
    winner_coalition = Column(String(64), nullable=True)
    winner_votes = Column(Integer, nullable=True)

    # Margins and turnout
    margin = Column(Integer, nullable=True)
    margin_pct = Column(Float, nullable=True)
    turnout_pct = Column(Float, nullable=True)
    total_voters = Column(Integer, nullable=True)
    total_votes_cast = Column(Integer, nullable=True)

    # Full candidate list
    candidates = Column(JSON, nullable=True)  # [{name, party, coalition, votes}, ...]

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

**New demographics model:**

```python
class ConstituencyDemographics(Base):
    """Demographic profile for a constituency."""
    __tablename__ = "constituency_demographics"

    id = Column(String(36), primary_key=True)
    constituency_code = Column(String(16), nullable=False, unique=True, index=True)
    seat_name = Column(String(128), nullable=False)
    state = Column(String(64), nullable=False, default="Johor")

    malay_pct = Column(Float, nullable=True)
    chinese_pct = Column(Float, nullable=True)
    indian_pct = Column(Float, nullable=True)
    others_pct = Column(Float, nullable=True)
    urban_rural = Column(String(32), nullable=True)  # "urban", "semi-urban", "rural"
    region = Column(String(32), nullable=True)  # "north", "central", "south"

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
```

### Step 3: Populate the JSON files with real data

This is the most labor-intensive step. For each of the 56 DUN seats and 26 Parlimen seats, compile results from the data sources listed above.

**Approach: Use an LLM-assisted script** — create `scripts/compile_historical_data.py`:

1. For each constituency code in the GeoJSON, search Wikipedia / SPR for results
2. Parse the results into the JSON schema
3. Write to `data/historical/johor_dun_results.json`
4. Manual verification pass to correct any errors

**Important:** The DUN seat names in GeoJSON (`N.01 Buloh Kasap`) should be cross-referenced with the constituency_tagger names. Note a discrepancy: the GeoJSON uses `"N.01 Buloh Kasap"` but the tagger uses `("N01", "Pulai Sebatang")`. These need to be reconciled — **use the GeoJSON names as authoritative** since they come from the official delimitation data.

### Step 4: Generate wiki constituency pages

Create `wiki/entities/constituencies/dun/` and `wiki/entities/constituencies/parlimen/` directories.

For each seat, generate a markdown page from the historical data:

**Template for `wiki/entities/constituencies/dun/n01-buloh-kasap.md`:**

```markdown
# N.01 Buloh Kasap

**State:** Johor
**Type:** DUN (State)
**Parlimen:** P.140 Segamat
**Region:** North Johor

## Demographics

| Ethnic Group | Percentage |
|-------------|-----------|
| Malay       | 72.0%     |
| Chinese     | 20.0%     |
| Indian      | 6.0%      |
| Others      | 2.0%      |

**Classification:** Semi-rural

## Election History

### 2022 Johor State Election

| Candidate | Party | Coalition | Votes | % |
|-----------|-------|-----------|-------|---|
| [Winner Name] | UMNO | BN | 12,345 | 52.3% |
| [Runner-up] | PKR | PH | 9,845 | 41.7% |
| [Third] | Bersatu | PN | 1,410 | 6.0% |

**Turnout:** 55.2% | **Margin:** 2,500 (8.5%)
**Swing:** +5.2% to BN from 2018

### 2018 Johor State Election
...

### 2013 Johor State Election
...

## Analysis Notes

- Traditional BN/UMNO seat with strong Malay majority
- PH competitive in 2018 but BN recovered in 2022
- Low turnout in 2022 benefited BN machinery

[Source: SPR Official Results; Wikipedia – 2022 Johor state election]
```

**Script:** Create `scripts/generate_wiki_pages.py` that reads `data/historical/johor_dun_results.json` and `johor_demographics.json`, then generates one `.md` file per seat using the template above.

### Step 5: Wire historical data into the seat_agent

Modify `agents/seat_agent/graph.py`, specifically the `load_baseline` function (line 92-108):

**Current code (mock):**
```python
async def load_baseline(state: dict, config: dict) -> dict:
    state["wiki_baseline"] = {
        "constituency_name": f"Constituency {constituency_code}",
        "historical_winners": {},
        "voter_demographics": {},
    }
    return state
```

**Replace with real data loading:**

```python
async def load_baseline(state: dict, config: dict) -> dict:
    constituency_code = state.get("constituency_code")

    session_maker = get_session_maker()
    if not session_maker:
        state["wiki_baseline"] = {"error": "No database"}
        return state

    async with session_maker() as session:
        # Load historical results
        stmt = select(HistoricalResult).where(
            HistoricalResult.constituency_code == constituency_code
        ).order_by(HistoricalResult.election_year.desc())
        result = await session.execute(stmt)
        history = result.scalars().all()

        # Load demographics
        stmt_demo = select(ConstituencyDemographics).where(
            ConstituencyDemographics.constituency_code == constituency_code
        )
        result_demo = await session.execute(stmt_demo)
        demographics = result_demo.scalars().first()

        # Also load wiki page content via filesystem
        wiki_context = _load_wiki_page(constituency_code)

        state["wiki_baseline"] = {
            "constituency_name": history[0].seat_name if history else constituency_code,
            "historical_winners": {
                str(h.election_year): {
                    "party": h.winner_party,
                    "coalition": h.winner_coalition,
                    "margin_pct": h.margin_pct,
                    "turnout_pct": h.turnout_pct,
                    "candidates": h.candidates,
                }
                for h in history
            },
            "voter_demographics": {
                "malay_pct": demographics.malay_pct,
                "chinese_pct": demographics.chinese_pct,
                "indian_pct": demographics.indian_pct,
                "others_pct": demographics.others_pct,
                "urban_rural": demographics.urban_rural,
            } if demographics else {},
            "wiki_context": wiki_context,
        }

    return state
```

### Step 6: Add historical data API endpoint

Add to `control_plane/routes.py`:

```python
@router.get("/historical/{constituency_code}")
async def get_historical(request: Request, constituency_code: str):
    """Return historical election results for a constituency."""
    # Query historical_results table
    ...

@router.get("/demographics/{constituency_code}")
async def get_demographics(request: Request, constituency_code: str):
    """Return demographic profile for a constituency."""
    ...
```

### Step 7: Fix constituency code inconsistencies

The tagger uses `N01` (no dot) but the GeoJSON uses `N.01` (with dot). The database and API should standardize on the **dotted format** (`N.01`, `P.140`) to match the GeoJSON.

In `agents/news_agent/constituency_tagger.py`, update the `_DUN` and `_PARLIMEN` lists to use dotted codes:

```python
# Change from:
("N01",  "Pulai Sebatang",  ["Pulai Sebatang"]),
# Change to:
("N.01",  "Buloh Kasap",  ["Buloh Kasap", "Pulai Sebatang"]),
```

Also reconcile the seat names with the GeoJSON `dun` property values.

---

## Files to Create

| File | Purpose |
|------|---------|
| `data/historical/schema.md` | Documents the data format |
| `data/historical/johor_dun_results.json` | 56 DUN seats x 3 elections |
| `data/historical/johor_parlimen_results.json` | 26 Parlimen seats x 3 elections |
| `data/historical/johor_demographics.json` | Per-seat demographics |
| `scripts/ingest_historical.py` | Load JSON into PostgreSQL |
| `scripts/generate_wiki_pages.py` | Generate constituency wiki pages |

## Files to Modify

| File | Change |
|------|--------|
| `agents/base/models.py` | Add `HistoricalResult` and `ConstituencyDemographics` models |
| `agents/seat_agent/graph.py` | Replace mock `load_baseline` with real DB queries (lines 92-108) |
| `agents/news_agent/constituency_tagger.py` | Fix codes to dotted format, reconcile names with GeoJSON |
| `control_plane/routes.py` | Add `/historical/{code}` and `/demographics/{code}` endpoints |
| `wiki/index.md` | Add constituency pages to the index |

---

## Verification

1. Run `scripts/ingest_historical.py` — verify all 56 DUN + 26 Parlimen results load into PostgreSQL
2. Run `scripts/generate_wiki_pages.py` — verify 82 wiki pages created (56 DUN + 26 Parlimen)
3. Hit `GET /historical/N.01` — should return 3 election results
4. Hit `GET /demographics/N.01` — should return ethnic breakdown
5. Dispatch a seat_agent task for `N.01` — verify `load_baseline` returns real data instead of empty dicts
6. Spot-check 5 random seats against Wikipedia to confirm data accuracy

---

## Estimated Scope

- Data compilation: ~56 DUN + 26 Parlimen seats, 3 elections each = 246 result records
- Wiki pages: 82 files (56 DUN + 26 Parlimen)
- Code changes: 4 files modified, 3 new scripts, 4 new data files
