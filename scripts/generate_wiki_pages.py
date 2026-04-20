"""
Generate wiki constituency pages from historical election data.

Reads:
  data/historical/johor_dun_results.json
  data/historical/johor_parlimen_results.json
  data/historical/johor_demographics.json

Writes:
  wiki/entities/constituencies/dun/n01-buloh-kasap.md  (56 files)
  wiki/entities/constituencies/parlimen/p140-segamat.md (26 files)

Usage:
    python scripts/generate_wiki_pages.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "historical"
WIKI_DUN = ROOT / "wiki" / "entities" / "constituencies" / "dun"
WIKI_PAR = ROOT / "wiki" / "entities" / "constituencies" / "parlimen"


def slug(code: str, name: str) -> str:
    """e.g. 'N.01', 'Buloh Kasap' -> 'n01-buloh-kasap'"""
    code_part = code.replace(".", "").lower()
    name_part = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{code_part}-{name_part}"


def fmt_votes(v) -> str:
    if v is None:
        return "—"
    return f"{int(v):,}"


def fmt_pct(v) -> str:
    if v is None:
        return "—"
    return f"{float(v):.1f}%"


def election_table(result: dict, total_cast: int | None) -> str:
    candidates = result.get("candidates") or []
    rows = []
    for c in candidates:
        votes = c.get("votes")
        pct = f"{votes / total_cast * 100:.1f}%" if votes and total_cast else "—"
        rows.append(
            f"| {c.get('name','—')} | {c.get('party','—')} | {c.get('coalition','—')} "
            f"| {fmt_votes(votes)} | {pct} |"
        )
    table = "| Candidate | Party | Coalition | Votes | % |\n"
    table += "|-----------|-------|-----------|------:|--:|\n"
    table += "\n".join(rows) if rows else "| — | — | — | — | — |"
    return table


def render_result_section(year: str, result: dict, election_label: str) -> str:
    total_cast = result.get("total_votes_cast")
    lines = [
        f"### {election_label}",
        "",
        election_table(result, total_cast),
        "",
        f"**Turnout:** {fmt_pct(result.get('turnout_pct'))} "
        f"| **Margin:** {fmt_votes(result.get('margin'))} ({fmt_pct(result.get('margin_pct'))})",
        "",
    ]
    return "\n".join(lines)


DUN_ELECTION_LABELS = {
    "2022": "2022 Johor State Election",
    "2018": "2018 Johor State Election",
}

PAR_ELECTION_LABELS = {
    "2022": "GE15 (2022)",
    "2018": "GE14 (2018)",
}


def generate_dun_page(
    code: str, seat: dict, demographics: dict
) -> str:
    name = seat["name"]
    parlimen = seat.get("parlimen", "—")
    demo = demographics.get(code, {})

    lines = [
        f"# {code} {name}",
        "",
        f"**State:** Johor  ",
        f"**Type:** DUN (State)  ",
        f"**Parlimen:** {parlimen}  ",
        f"**Region:** {demo.get('region', '—').title()}  ",
        "",
        "## Demographics",
        "",
        "| Ethnic Group | Percentage |",
        "|-------------|-----------|",
        f"| Malay       | {fmt_pct(demo.get('malay_pct'))} |",
        f"| Chinese     | {fmt_pct(demo.get('chinese_pct'))} |",
        f"| Indian      | {fmt_pct(demo.get('indian_pct'))} |",
        f"| Others      | {fmt_pct(demo.get('others_pct'))} |",
        "",
        f"**Classification:** {demo.get('urban_rural', '—').replace('-', ' ').title()}",
        "",
        "## Election History",
        "",
    ]

    for year in ["2022", "2018"]:
        result = seat.get("results", {}).get(year)
        if result:
            label = DUN_ELECTION_LABELS.get(year, f"{year} Election")
            lines.append(render_result_section(year, result, label))

    lines += [
        "---",
        "",
        "*Source: SPR Official Results; TindakMalaysia; Wikipedia*",
    ]
    return "\n".join(lines)


def generate_parlimen_page(
    code: str, seat: dict, demographics: dict
) -> str:
    name = seat["name"]
    demo = demographics.get(code, {})

    lines = [
        f"# {code} {name}",
        "",
        f"**State:** Johor  ",
        f"**Type:** Parlimen (Federal)  ",
        f"**Region:** {demo.get('region', '—').title()}  ",
        "",
        "## Demographics",
        "",
        "| Ethnic Group | Percentage |",
        "|-------------|-----------|",
        f"| Malay       | {fmt_pct(demo.get('malay_pct'))} |",
        f"| Chinese     | {fmt_pct(demo.get('chinese_pct'))} |",
        f"| Indian      | {fmt_pct(demo.get('indian_pct'))} |",
        f"| Others      | {fmt_pct(demo.get('others_pct'))} |",
        "",
        f"**Classification:** {demo.get('urban_rural', '—').replace('-', ' ').title()}",
        "",
        "## Election History",
        "",
    ]

    for year in ["2022", "2018"]:
        result = seat.get("results", {}).get(year)
        if result:
            label = PAR_ELECTION_LABELS.get(year, f"{year} Election")
            lines.append(render_result_section(year, result, label))

    lines += [
        "---",
        "",
        "*Source: SPR Official Results; TindakMalaysia; Wikipedia*",
    ]
    return "\n".join(lines)


def main():
    dun_data = json.loads((DATA_DIR / "johor_dun_results.json").read_text(encoding="utf-8"))
    par_data = json.loads((DATA_DIR / "johor_parlimen_results.json").read_text(encoding="utf-8"))
    demo_raw = json.loads((DATA_DIR / "johor_demographics.json").read_text(encoding="utf-8"))

    # Build demographics lookup by code
    demographics = {code: seat for code, seat in demo_raw["seats"].items()}

    WIKI_DUN.mkdir(parents=True, exist_ok=True)
    WIKI_PAR.mkdir(parents=True, exist_ok=True)

    dun_count = 0
    for code, seat in dun_data["seats"].items():
        content = generate_dun_page(code, seat, demographics)
        filename = slug(code, seat["name"]) + ".md"
        (WIKI_DUN / filename).write_text(content, encoding="utf-8")
        dun_count += 1

    par_count = 0
    for code, seat in par_data["seats"].items():
        content = generate_parlimen_page(code, seat, demographics)
        filename = slug(code, seat["name"]) + ".md"
        (WIKI_PAR / filename).write_text(content, encoding="utf-8")
        par_count += 1

    print(f"Generated {dun_count} DUN pages -> {WIKI_DUN}")
    print(f"Generated {par_count} Parlimen pages -> {WIKI_PAR}")
    print(f"Total: {dun_count + par_count} pages")


if __name__ == "__main__":
    main()
