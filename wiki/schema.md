# Wiki Schema — Johor Election Dashboard

## Purpose

This wiki is a curated, LLM-maintained knowledge base encoding persistent facts about Johor elections, parties, constituencies, candidates, and political context. It is injected as context into every LLM call to ground analysis in current, project-specific knowledge rather than relying solely on model training data.

---

## Page Types

| Type | Location | Purpose |
|------|----------|---------|
| `entity/party` | `entities/parties/` | Party background, ideology, Johor presence, electoral history |
| `entity/constituency` | `entities/constituencies/parlimen/` or `dun/` | Seat history, demographics, candidates, margins |
| `entity/candidate` | `entities/candidates/` | Key candidate profiles, track record |
| `concept` | `concepts/` | Thematic overviews (political landscape, economic context, etc.) |
| `comparison` | `comparisons/` | Side-by-side analysis of parties or policy positions |

---

## Citation Format

Every factual claim must carry a citation:

```
[Source: {outlet or source name}, {date}]
```

Examples:
- `[Source: Wikipedia – 2022 Johor state election, 2024]`
- `[Source: Malaysiakini, 2024-03-15]`
- `[Source: The Star, 2025-01-10]`
- `[Source: Bridget Welsh, bridgetwelsh.com, 2022]`

Human-authored seed content uses `[Source: Wikipedia, {article title}, {year accessed}]`.

---

## Ingest Workflow

When the `wiki_agent` ingests a new article (reliability score ≥ 60):

1. **Retrieve** — `retriever.py` identifies the top-3 most relevant existing wiki pages using TF-IDF keyword scoring
2. **Update** — LLM reads the article + retrieved pages + this schema, then:
   - Identifies which existing pages to update with new facts
   - Flags any `[CONTRADICTION]` where new info conflicts with existing wiki content
   - Creates new candidate or constituency pages if names appear that have no page yet
3. **Log** — Append a timestamped entry to `log.md`:
   ```
   [YYYY-MM-DD HH:MM UTC] INGEST: {article headline} ({source})
   Pages updated: {comma-separated list}
   New pages created: {comma-separated list or "none"}
   Contradictions flagged: {count or "none"}
   ```
4. **Never silently overwrite contradictions** — mark as `[CONTRADICTION: {new claim} — conflicts with: {existing claim}]` and leave for human review

---

## Page Size Limit

Pages are capped at **~300 lines**. When a page approaches this limit:
- Move older/superseded claims to an `## Archive` section at the bottom
- The active content stays in the main body
- Archive entries retain their citations

---

## Staleness Policy

Claims older than **90 days** without a corroborating newer source should be marked:
```
[STALE — last confirmed: {date}]
```

The `wiki_agent` lint mode checks for this and surfaces stale claims in the WikiModal.

---

## Lint Checks (run weekly)

The `wiki_agent` linter checks for:
- `[CONTRADICTION]` markers that have not been resolved
- Claims with no citation
- Pages with no inbound cross-references (orphaned pages)
- Pages exceeding 300 lines
- Claims marked `[STALE]`

---

## Formatting Conventions

- Headings: `##` for main sections, `###` for subsections
- Party names: always include both English and Malay names on first mention
- Constituency codes: always include both code and full name, e.g. `P157 Johor Bahru`
- Election references: use `GE14 (2018)`, `GE15 (2022)`, `Johor SE 2022` (state election)
- Seat counts: include out of total, e.g. `40/56 DUN seats`
- Do not use speculative language without explicit `[UNCERTAIN]` tag
