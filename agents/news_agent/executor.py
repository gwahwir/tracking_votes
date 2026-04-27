"""News agent executor."""
from __future__ import annotations

from agents.base.executor import LangGraphA2AExecutor
from .graph import build_news_graph


class NewsAgentExecutor(LangGraphA2AExecutor):
    AGENT_NAME = "Johor News Agent"
    AGENT_TYPE_ID = "news_agent"
    AGENT_DESCRIPTION = (
        "Scrapes Malaysian news sources for Johor election coverage, "
        "filters by relevance, tags with constituency codes, and stores to DB."
    )
    AGENT_PORT = 8001

    def build_graph(self):
        return build_news_graph()

    def _build_initial_state(self, message_text: str, metadata: dict) -> dict:
        return {
            "input": message_text,
            "metadata": metadata,
            "raw_articles": [],
            "filtered_articles": [],
            "tagged_articles": [],
            "upserted_count": 0,
            "output": "",
        }

    def _summarise_node_output(self, node_name: str, node_output) -> str:
        if node_name == "fetch":
            count = len(node_output.get("raw_articles", []))
            return f"NODE_OUTPUT::fetch: retrieved {count} raw articles"
        if node_name == "filter":
            count = len(node_output.get("filtered_articles", []))
            return f"NODE_OUTPUT::filter: {count} Johor-relevant articles passed filter"
        if node_name == "tag":
            articles = node_output.get("tagged_articles", [])
            tagged = sum(1 for a in articles if a.get("constituency_ids"))
            return f"NODE_OUTPUT::tag: {tagged}/{len(articles)} articles tagged with constituency codes"
        if node_name == "upsert":
            return f"NODE_OUTPUT::upsert: {node_output.get('output', 'done')}"
        return super()._summarise_node_output(node_name, node_output)

    def _extract_final_output(self, final_state: dict) -> str:
        return final_state.get("output", "done")
