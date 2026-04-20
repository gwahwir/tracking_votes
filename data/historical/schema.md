# Historical Election Data Schema

## Files

| File | Contents |
|------|----------|
| `johor_dun_results.json` | 56 DUN seats × 2 elections (2018, 2022) |
| `johor_parlimen_results.json` | 26 Parlimen seats × 2 elections (2018, 2022) |
| `johor_demographics.json` | Per-seat ethnic and urban/rural breakdown (82 seats) |

## johor_dun_results.json / johor_parlimen_results.json

```json
{
  "metadata": {
    "state": "Johor",
    "seat_type": "dun" | "parlimen",
    "elections": ["2018", "2022"],
    "source": "SPR, TindakMalaysia, Wikipedia",
    "last_updated": "YYYY-MM-DD"
  },
  "seats": {
    "N.01": {
      "name": "Buloh Kasap",
      "parlimen": "P.140",          // DUN only
      "results": {
        "2022": {
          "winner_name": "string",
          "winner_party": "string",  // e.g. "UMNO", "PKR", "DAP"
          "winner_coalition": "string", // "BN", "PH", "PN", "IND"
          "winner_votes": 12345,
          "margin": 2500,            // votes over runner-up
          "margin_pct": 8.5,         // margin as % of total votes cast
          "turnout_pct": 55.2,
          "total_voters": 25000,     // registered voters
          "total_votes_cast": 13800,
          "num_candidates": 3,
          "candidates": [
            {"name": "string", "party": "string", "coalition": "string", "votes": 12345}
          ]
        }
      }
    }
  }
}
```

## johor_demographics.json

```json
{
  "metadata": { ... },
  "seats": {
    "N.01": {
      "name": "Buloh Kasap",
      "state": "Johor",
      "malay_pct": 72.0,
      "chinese_pct": 20.0,
      "indian_pct": 6.0,
      "others_pct": 2.0,
      "urban_rural": "rural" | "semi-urban" | "urban",
      "region": "north" | "central" | "south"
    }
  }
}
```

## Constituency Codes

- DUN: `N.01` – `N.56` (Johor state seats)
- Parlimen: `P.140` – `P.165` (Johor federal seats)
- Dotted format matches GeoJSON properties (`code_dun`, `code_parlimen`)

## Coalition Mapping

| Label | Parties (2018) | Parties (2022) |
|-------|---------------|----------------|
| BN    | UMNO, MCA, MIC | UMNO, MCA, MIC |
| PH    | PKR, DAP, AMANAH, BERSATU | PKR, DAP, AMANAH |
| PN    | — | BERSATU, PAS, GERAKAN |
| GS    | PAS | — |
| IND   | Independents / minor parties | Independents / minor parties |
