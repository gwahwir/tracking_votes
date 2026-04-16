"""LangGraph graphs for the wiki agent.

Two graphs:
  ingest_graph  — retrieve relevant pages → LLM update → append log → update index
  lint_graph    — run linter → return report (no writes)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from agents.base.llm import llm_call
from .linter import lint_wiki
from .loader import (
    WikiPage,
    append_log,
    load_all_pages,
    update_index,
    write_page,
)
from .retriever import TFIDFRetriever

# Shared retriever instance (reloaded on each ingest task)
_retriever = TFIDFRetriever()


# ---------------------------------------------------------------------------
# Ingest graph
# ---------------------------------------------------------------------------

class IngestState(TypedDict):
    input: str                          # article text / news summary to ingest
    metadata: dict[str, Any]
    relevant_pages: list[WikiPage]
    updates: list[dict[str, str]]       # [{path, new_content}]
    log_entry: str
    output: str


def _retrieve_node(state: IngestState) -> IngestState:
    _retriever.reload()
    results = _retriever.query(state["input"], top_k=5)
    state["relevant_pages"] = [r.page for r in results]
    return state


def _update_pages_node(state: IngestState) -> IngestState:
    pages = state["relevant_pages"]
    if not pages:
        state["updates"] = []
        state["log_entry"] = ""
        return state

    context_blocks = "\n\n---\n\n".join(
        f"### {p.path}\n{p.content[:2000]}" for p in pages
    )

    prompt = f"""You are the wiki editor for a Johor, Malaysia election monitoring system.

Below are the current wiki pages most relevant to the incoming article:

{context_blocks}

---

Incoming article / information:
{state["input"][:3000]}

---

Your task:
1. Identify which wiki pages should be updated with new facts from the article.
2. For each page to update, output the COMPLETE updated markdown content.
3. If a claim contradicts existing content, add a `[CONTRADICTION]` marker inline — do NOT silently overwrite.
4. Every new fact must include a citation: `[Source: {{outlet}}, {{date}}]`
5. Do not update pages that are not relevant.

Respond in this exact JSON format:
{{
  "updates": [
    {{"path": "entities/parties/dap.md", "content": "...full updated markdown..."}},
    ...
  ],
  "log_entry": "One-sentence summary of what changed and why."
}}

If no updates are needed, respond with: {{"updates": [], "log_entry": "No relevant updates needed."}}
"""

    raw = llm_call(
        [{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    import json
    try:
        result = json.loads(raw)
        state["updates"] = result.get("updates", [])
        state["log_entry"] = result.get("log_entry", "")
    except (json.JSONDecodeError, KeyError):
        state["updates"] = []
        state["log_entry"] = "Wiki update parse error — no changes applied."

    return state


def _write_updates_node(state: IngestState) -> IngestState:
    written: list[str] = []
    for upd in state["updates"]:
        path = upd.get("path", "")
        content = upd.get("content", "")
        if path and content:
            write_page(path, content)
            written.append(path)

    # Append log entry
    if state.get("log_entry"):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = f"## {ts}\n\n{state['log_entry']}\n\nPages updated: {', '.join(written) or 'none'}"
        append_log(entry)

    # Rebuild index
    all_pages = load_all_pages()
    update_index(all_pages)

    state["output"] = f"Updated {len(written)} page(s): {', '.join(written) or 'none'}"
    return state


def build_ingest_graph():
    g = StateGraph(IngestState)
    g.add_node("retrieve_wiki", _retrieve_node)
    g.add_node("update_pages", _update_pages_node)
    g.add_node("write_updates", _write_updates_node)

    g.set_entry_point("retrieve_wiki")
    g.add_edge("retrieve_wiki", "update_pages")
    g.add_edge("update_pages", "write_updates")
    g.add_edge("write_updates", END)

    return g.compile()


# ---------------------------------------------------------------------------
# Lint graph
# ---------------------------------------------------------------------------

class LintState(TypedDict):
    input: str
    metadata: dict[str, Any]
    report: dict[str, Any]
    output: str


def _lint_node(state: LintState) -> LintState:
    report = lint_wiki()
    state["report"] = report.to_dict()
    state["output"] = report.summary()
    return state


def build_lint_graph():
    g = StateGraph(LintState)
    g.add_node("lint", _lint_node)
    g.set_entry_point("lint")
    g.add_edge("lint", END)
    return g.compile()
