# Phase D: General Election Extension Architecture

## Goal

Generalize the system from Johor-only to support all Malaysian states and the full General Election (222 Parlimen + ~600 DUN seats nationwide). The architecture should allow state-by-state rollout — start with Johor, add states incrementally.

**Prerequisite:** Phases A-C should be complete for Johor, proving the full pipeline works end-to-end.

---

## Context: What Exists Today

### GeoJSON Coverage (Already Complete)
The `public/geojson/malaysia/` directory already has nationwide GeoJSON data:

**Per-state files** in `public/geojson/malaysia/states/`:
- 13 states x 2 (DUN + Parlimen) = 26 files
- 3 Federal Territories x 1 (Parlimen only) = 3 files
- Total: 29 files covering all 222 Parlimen + ~600 DUN seats

**Delimitation files** in `public/geojson/malaysia/delimitations/`:
- `peninsular_2018_dun.geojson` / `peninsular_2018_parlimen.geojson`
- `sabah_2019_dun.geojson` / `sabah_2019_parlimen.geojson`
- `sarawak_2015_dun.geojson` / `sarawak_2015_parlimen.geojson`

**GeoJSON property format** (consistent across all files):
```json
{
  "state": "Johor",
  "parlimen": "P.140 Segamat",
  "code_parlimen": "P.140",
  "dun": "N.01 Buloh Kasap",
  "code_dun": "N.01"
}
```

### Johor-Specific Code That Needs Generalization

1. **`agents/news_agent/constituency_tagger.py`** — Hardcoded Johor seats only (P140-P165, N01-N56)
2. **`agents/news_agent/graph.py`** — `_JOHOR_KEYWORDS` list (line 22-28) filters only Johor-related articles
3. **`agents/analyst_agent/graph.py`** — System prompt references "Johor" specifically
4. **`agents/analyst_agent/prompts/*.txt`** — Prompts are Johor-specific
5. **`agents/seat_agent/graph.py`** — Prompt says "election analyst for Johor"
6. **`dashboard/src/components/map/ElectionMap.jsx`** — Hardcoded Johor GeoJSON paths and center coordinates (`[1.485, 103.74]`)
7. **`dashboard/src/components/layout/TopBar.jsx`** — Title says "Johor Election Monitor"
8. **`wiki/`** — All content is Johor-specific
9. **`docker-compose.yml`** — Database named `johor_elections`

---

## Implementation Steps

### Step 1: Add a state/election context system

Create a configuration layer that defines the current election scope.

**Create `control_plane/election_config.py`:**

```python
"""Election scope configuration.

Defines which state/election is currently being monitored.
Supports multiple concurrent scopes (e.g., monitor Johor + Selangor simultaneously).
"""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class ElectionScope:
    """Defines an election monitoring scope."""
    state: str                          # "Johor", "Selangor", etc. or "Malaysia" for GE
    election_type: str                  # "state" or "general"
    seat_type: str                      # "dun", "parlimen", or "both"
    label: str = ""                     # Display label, e.g. "PRN Johor 2027"

    # GeoJSON paths (relative to public/geojson/)
    geojson_parlimen: str = ""
    geojson_dun: str = ""

    # Map center and zoom
    center_lat: float = 4.0
    center_lng: float = 109.5
    default_zoom: int = 6

    # Keywords for news filtering
    keywords: list[str] = field(default_factory=list)

    # Constituency code prefix for this state
    parlimen_range: str = ""            # e.g. "P.140-P.165" for Johor
    dun_range: str = ""                 # e.g. "N.01-N.56" for Johor


# Pre-defined scopes
SCOPES = {
    "johor": ElectionScope(
        state="Johor",
        election_type="state",
        seat_type="both",
        label="PRN Johor",
        geojson_parlimen="johor-parlimen.geojson",
        geojson_dun="johor-dun.geojson",
        center_lat=1.485, center_lng=103.74, default_zoom=8,
        keywords=["johor", "jb", "johor bahru", "muar", "batu pahat", "kluang",
                  "segamat", "pontian", "kota tinggi", "mersing", "kulai", "pasir gudang",
                  "iskandar"],
        parlimen_range="P.140-P.165",
        dun_range="N.01-N.56",
    ),
    "selangor": ElectionScope(
        state="Selangor",
        election_type="state",
        seat_type="both",
        label="PRN Selangor",
        geojson_parlimen="malaysia/states/selangor_parlimen.geojson",
        geojson_dun="malaysia/states/selangor_dun.geojson",
        center_lat=3.1, center_lng=101.5, default_zoom=9,
        keywords=["selangor", "shah alam", "petaling jaya", "subang", "klang",
                  "ampang", "gombak", "hulu langat", "sepang"],
        parlimen_range="P.094-P.115",
        dun_range="N.01-N.56",
    ),
    "general": ElectionScope(
        state="Malaysia",
        election_type="general",
        seat_type="parlimen",
        label="GE16",
        geojson_parlimen="malaysia/delimitations/peninsular_2018_parlimen.geojson",
        geojson_dun="",  # Not applicable for GE overview
        center_lat=4.0, center_lng=109.5, default_zoom=6,
        keywords=["election", "pilihanraya", "pru", "ge16", "parlimen",
                  "calon", "umno", "dap", "pkr", "pas", "bersatu", "amanah"],
        parlimen_range="P.001-P.222",
    ),
    # Add more states as needed...
}
```

**Add API endpoint** in `control_plane/routes.py`:

```python
@router.get("/election-scopes")
async def list_scopes():
    """Return available election scopes."""
    from .election_config import SCOPES
    return {k: {"state": v.state, "label": v.label, "election_type": v.election_type,
                "seat_type": v.seat_type, "center": [v.center_lat, v.center_lng],
                "zoom": v.default_zoom, "geojson_parlimen": v.geojson_parlimen,
                "geojson_dun": v.geojson_dun}
            for k, v in SCOPES.items()}

@router.get("/election-scopes/{scope_id}")
async def get_scope(scope_id: str):
    """Return a specific election scope."""
    from .election_config import SCOPES
    scope = SCOPES.get(scope_id)
    if not scope:
        raise HTTPException(status_code=404, detail=f"Scope '{scope_id}' not found")
    return { ... }  # Same format as above
```

### Step 2: Generalize the constituency tagger

Replace the hardcoded Johor lookup table with a data-driven approach that loads constituency data from a JSON file per state.

**Create `data/constituencies/` directory:**

```
data/
  constituencies/
    johor.json       # All Johor seats with keywords
    selangor.json    # All Selangor seats
    ...
    malaysia.json    # All 222 Parlimen seats
```

**Format for `data/constituencies/johor.json`:**

```json
{
  "state": "Johor",
  "parlimen": [
    {"code": "P.140", "name": "Segamat", "keywords": ["Segamat", "Genuang"]},
    {"code": "P.141", "name": "Sekijang", "keywords": ["Sekijang", "Labis"]},
    ...
  ],
  "dun": [
    {"code": "N.01", "name": "Buloh Kasap", "keywords": ["Buloh Kasap"]},
    {"code": "N.02", "name": "Jementah", "keywords": ["Jementah"]},
    ...
  ]
}
```

**Rewrite `agents/news_agent/constituency_tagger.py`:**

```python
"""Data-driven constituency tagger.

Loads constituency data from JSON files in data/constituencies/.
Supports multiple states simultaneously.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

CONSTITUENCY_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "constituencies"

@dataclass
class ConstituencyMatch:
    code: str
    seat_type: str
    name: str
    state: str
    matched_keyword: str

# Cache loaded patterns
_loaded_states: dict[str, list[tuple[str, str, str, re.Pattern]]] = {}

def _load_state(state_key: str) -> list[tuple[str, str, str, re.Pattern]]:
    """Load and compile patterns for a state."""
    if state_key in _loaded_states:
        return _loaded_states[state_key]

    data_file = CONSTITUENCY_DATA_DIR / f"{state_key}.json"
    if not data_file.exists():
        return []

    data = json.loads(data_file.read_text())
    patterns = []

    for seat_type in ("parlimen", "dun"):
        for seat in data.get(seat_type, []):
            keywords = [seat["name"]] + seat.get("keywords", [])
            if not keywords:
                continue
            pattern = re.compile(
                r"\b(" + "|".join(re.escape(kw) for kw in keywords) + r")\b",
                re.IGNORECASE,
            )
            patterns.append((seat["code"], seat["name"], seat_type, data["state"], pattern))

    _loaded_states[state_key] = patterns
    return patterns

def load_all_states():
    """Load patterns for all available state files."""
    for f in CONSTITUENCY_DATA_DIR.glob("*.json"):
        _load_state(f.stem)

def tag_article(text: str, states: list[str] | None = None) -> list[ConstituencyMatch]:
    """Tag article with constituency matches.

    Args:
        text: Article text to search
        states: List of state keys to match against (e.g. ["johor", "selangor"]).
                If None, matches against all loaded states.
    """
    if states is None:
        load_all_states()
        all_patterns = []
        for patterns in _loaded_states.values():
            all_patterns.extend(patterns)
    else:
        all_patterns = []
        for state_key in states:
            all_patterns.extend(_load_state(state_key))

    combined = text[:5000]
    seen: set[str] = set()
    matches: list[ConstituencyMatch] = []

    for code, name, seat_type, state, pattern in all_patterns:
        if code in seen:
            continue
        m = pattern.search(combined)
        if m:
            matches.append(ConstituencyMatch(
                code=code, seat_type=seat_type, name=name,
                state=state, matched_keyword=m.group(0),
            ))
            seen.add(code)

    return matches

def tag_codes(text: str, states: list[str] | None = None) -> list[str]:
    """Return just the matched constituency codes."""
    return [m.code for m in tag_article(text, states)]
```

### Step 3: Generalize the news agent filter

**Modify `agents/news_agent/graph.py`:**

Replace the hardcoded `_JOHOR_KEYWORDS` with scope-aware filtering.

```python
def _filter_node(state: NewsState) -> NewsState:
    """Keep articles relevant to the active election scope(s)."""
    import os
    from control_plane.election_config import SCOPES

    # Get active scopes from environment or default to Johor
    active_scopes = os.environ.get("ACTIVE_SCOPES", "johor").split(",")

    keywords = set()
    # Always include general election keywords
    keywords.update(["election", "pilihanraya", "pru", "calon", "parlimen", "dun",
                     "umno", "bn", "pkr", "dap", "bersatu", "pas", "amanah"])

    # Add scope-specific keywords
    for scope_key in active_scopes:
        scope = SCOPES.get(scope_key.strip())
        if scope:
            keywords.update(scope.keywords)

    filtered = []
    for art in state["raw_articles"]:
        combined = (art["title"] + " " + art["content"]).lower()
        if any(kw in combined for kw in keywords):
            filtered.append(art)

    state["filtered_articles"] = filtered
    return state
```

### Step 4: Add state context to database models

**Modify `agents/base/models.py`:**

Add a `state` column to `SeatPrediction` and `Article` models:

```python
class SeatPrediction(Base):
    # ... existing columns ...
    state = Column(String(64), nullable=True, index=True)  # "Johor", "Selangor", etc.

class Article(Base):
    # ... existing columns ...
    states = Column(JSON, nullable=True)  # ["Johor", "Selangor"] — which states this article is relevant to
```

**Migration approach:** Since we're using `create_all`, adding nullable columns is backward-compatible. For existing data, run a one-time script to set `state="Johor"` on all existing records.

### Step 5: Generalize agent prompts

**Modify prompts to accept state context dynamically.**

In `agents/analyst_agent/prompts/system.txt`, change from:

```
You are an election analyst for Johor, Malaysia.
```

To a template:

```
You are an election analyst for {{STATE}}, Malaysia.

{{WIKI_CONTEXT}}

Analyse articles with these perspectives, grounded in {{STATE}}'s specific political dynamics.
```

The `_retrieve_wiki_node` in `agents/analyst_agent/graph.py` should inject the state name:

```python
def _retrieve_wiki_node(state: AnalystState) -> AnalystState:
    # ... existing parsing ...

    # Determine which state this article pertains to
    election_state = data.get("state", "Johor")  # Default to Johor for backward compat

    state["system_prompt"] = _SYSTEM_TEMPLATE\
        .replace("{{WIKI_CONTEXT}}", wiki_ctx)\
        .replace("{{STATE}}", election_state)

    return state
```

Similarly update `agents/seat_agent/graph.py` assess prompt.

### Step 6: Add state selector to the dashboard

**Modify `dashboard/src/components/layout/DashboardShell.jsx`:**

Add a state/scope selector dropdown:

```jsx
import { Select } from '@mantine/core'

// In DashboardShell:
const [activeScope, setActiveScope] = useState('johor')
const [scopes, setScopes] = useState({})

// Fetch available scopes on mount
useEffect(() => {
  fetch(`${API_BASE}/election-scopes`)
    .then(res => res.json())
    .then(data => setScopes(data))
}, [])

// In TopBar:
<Select
  data={Object.entries(scopes).map(([key, scope]) => ({
    value: key,
    label: scope.label || scope.state,
  }))}
  value={activeScope}
  onChange={setActiveScope}
  placeholder="Select election"
  w={200}
/>
```

**Modify `ElectionMap.jsx`** to use scope-provided GeoJSON paths and center:

```jsx
export const ElectionMap = ({ scope, mapType, useCartogram, onConstituencySelect }) => {
  // Use scope to determine GeoJSON path, center, and zoom
  const geojsonPath = mapType === 'parlimen'
    ? scope?.geojson_parlimen
    : scope?.geojson_dun

  const center = scope?.center || [4.0, 109.5]
  const zoom = scope?.zoom || 6

  useEffect(() => {
    if (!geojsonPath) return
    fetch(`/geojson/${geojsonPath}`)
      .then(res => res.json())
      .then(data => setGeoJsonData(data))
  }, [geojsonPath])

  return (
    <MapContainer center={center} zoom={zoom} ...>
      ...
    </MapContainer>
  )
}
```

### Step 7: Add scope-filtered API endpoints

**Modify `control_plane/routes.py`** to support state filtering:

```python
@router.get("/seat-predictions")
async def get_seat_predictions(request: Request, limit: int = 100, state: str | None = None):
    """Return seat predictions, optionally filtered by state."""
    # ... existing code ...
    if state:
        where = "WHERE state = $2"
        params.append(state)
    # ...

@router.get("/articles")
async def get_articles(request: Request, limit: int = 100, state: str | None = None):
    """Return articles, optionally filtered by state."""
    # ...
```

### Step 8: Create a nationwide overview map

For GE monitoring, add a national-level map showing all 222 Parlimen seats.

This is mostly handled by the scope system — when `activeScope` is `"general"`, the map loads `malaysia/delimitations/peninsular_2018_parlimen.geojson` and centers on Malaysia.

However, for a complete view, you need to merge Peninsular + Sabah + Sarawak GeoJSON into one file, or render three map layers:

**Create `scripts/merge_geojson.py`:**

```python
"""Merge Peninsular + Sabah + Sarawak Parlimen GeoJSON into one nationwide file."""
import json
from pathlib import Path

BASE = Path("public/geojson/malaysia/delimitations")
OUTPUT = Path("public/geojson/malaysia/malaysia_parlimen.geojson")

merged = {"type": "FeatureCollection", "features": []}

for f in ["peninsular_2018_parlimen.geojson", "sabah_2019_parlimen.geojson", "sarawak_2015_parlimen.geojson"]:
    data = json.loads((BASE / f).read_text())
    merged["features"].extend(data["features"])

OUTPUT.write_text(json.dumps(merged))
print(f"Merged {len(merged['features'])} features -> {OUTPUT}")
```

### Step 9: Scale the wiki structure

**Create state-specific wiki directories:**

```
wiki/
  entities/
    constituencies/
      johor/
        dun/       # 56 files (from Phase A)
        parlimen/  # 26 files (from Phase A)
      selangor/
        dun/
        parlimen/
      ...
    parties/       # National parties (already exists)
  concepts/
    johor/         # Move existing Johor concepts here
    selangor/      # New
    national/      # GE-level concepts
```

Update `agents/wiki_agent/loader.py` to support loading wiki pages filtered by state.

### Step 10: Add state-specific news sources

**Expand `agents/news_agent/scrapers/`** with state-aware RSS feeds:

```python
# In each scraper, add state-specific feed URLs
FEEDS_BY_STATE = {
    "johor": [
        "https://www.thestar.com.my/news/nation/rss",
        "https://www.freemalaysiatoday.com/rss/",
    ],
    "selangor": [
        "https://www.thestar.com.my/news/nation/rss",
        "https://www.freemalaysiatoday.com/rss/",
        # Selangor-specific feeds...
    ],
    "national": [
        "https://www.thestar.com.my/news/nation/rss",
        "https://www.freemalaysiatoday.com/rss/",
        "https://www.malaysiakini.com/rss/en",
        # All national feeds...
    ],
}
```

### Step 11: Environment variable for active scopes

**Update `.env.template` and `docker-compose.yml`:**

```yaml
environment:
  ACTIVE_SCOPES: johor  # Comma-separated: "johor,selangor" or "general"
  DATABASE_URL: postgresql://johor:johor@postgres:5432/elections  # Rename from johor_elections
```

---

## Rollout Strategy

1. **Start with Johor** — all existing functionality continues to work
2. **Add Selangor** — compile Selangor historical data (Phase A process), add constituency JSON, update `ACTIVE_SCOPES`
3. **Add remaining states** — one at a time, each following the same Phase A pattern
4. **Enable GE mode** — set `ACTIVE_SCOPES=general`, merge GeoJSON, monitor all 222 Parlimen seats

Each state addition requires:
- `data/constituencies/{state}.json` — constituency codes and keywords
- `data/historical/{state}_dun_results.json` — historical DUN results
- `data/historical/{state}_parlimen_results.json` — historical Parlimen results
- `data/historical/{state}_demographics.json` — demographics
- Wiki pages in `wiki/entities/constituencies/{state}/`
- A scope entry in `control_plane/election_config.py`

---

## Files to Create

| File | Purpose |
|------|---------|
| `control_plane/election_config.py` | Election scope definitions |
| `data/constituencies/johor.json` | Johor constituency data (migrated from tagger) |
| `data/constituencies/selangor.json` | Selangor constituency data (first extension) |
| `scripts/merge_geojson.py` | Merge regional GeoJSON into national file |
| `public/geojson/malaysia/malaysia_parlimen.geojson` | Merged national Parlimen GeoJSON |

## Files to Modify

| File | Change |
|------|--------|
| `agents/news_agent/constituency_tagger.py` | Rewrite to load from JSON files instead of hardcoded lists |
| `agents/news_agent/graph.py` | Replace `_JOHOR_KEYWORDS` with scope-aware filtering |
| `agents/analyst_agent/graph.py` | Inject state name into prompts dynamically |
| `agents/analyst_agent/prompts/system.txt` | Template with `{{STATE}}` placeholder |
| `agents/seat_agent/graph.py` | Inject state name into assess prompt |
| `agents/base/models.py` | Add `state` column to SeatPrediction, Article |
| `control_plane/routes.py` | Add `/election-scopes` endpoints, state filtering on existing endpoints |
| `dashboard/src/components/layout/DashboardShell.jsx` | Add scope selector, pass scope to ElectionMap |
| `dashboard/src/components/layout/TopBar.jsx` | Dynamic title from scope label |
| `dashboard/src/components/map/ElectionMap.jsx` | Use scope-provided GeoJSON paths, center, zoom |
| `dashboard/src/hooks/useApi.js` | Add `useElectionScopes` hook, pass state filter to existing hooks |
| `docker-compose.yml` | Add `ACTIVE_SCOPES` env var, rename database |

---

## Verification

1. Set `ACTIVE_SCOPES=johor` — verify existing Johor functionality unchanged
2. Set `ACTIVE_SCOPES=johor,selangor` — verify both states' articles are scraped and tagged
3. Dashboard state selector shows both Johor and Selangor options
4. Selecting Selangor re-centers map and loads Selangor GeoJSON
5. Seat predictions are filtered by state
6. Set `ACTIVE_SCOPES=general` — verify national map loads all 222 Parlimen seats
7. News agent scrapes articles relevant to multiple states simultaneously
