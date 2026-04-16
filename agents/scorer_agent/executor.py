"""Scorer agent executor."""
from __future__ import annotations

from agents.base.executor import LangGraphA2AExecutor
from .graph import build_scorer_graph


class ScorerAgentExecutor(LangGraphA2AExecutor):
    AGENT_NAME = "Johor Scorer Agent"
    AGENT_TYPE_ID = "scorer_agent"
    AGENT_DESCRIPTION = (
        "Reliability scorer for Johor election news articles. "
        "Scores source authority, accuracy signals, and bias indicators "
        "using wiki-grounded LLM analysis. Emits wiki ingest tasks for "
        "high-scoring articles (score >= 60)."
    )
    AGENT_PORT = 8002

    def build_graph(self):
        return build_scorer_graph()

    def _build_initial_state(self, message_text: str, metadata: dict) -> dict:
        return {
            "input": message_text,
            "metadata": metadata,
            "article_id": "",
            "article_text": "",
            "source": "",
            "wiki_context": "",
            "score_result": {},
            "output": "",
        }

    def _summarise_node_output(self, node_name: str, node_output) -> str:
        if node_name == "retrieve_wiki":
            ctx = node_output.get("wiki_context", "")
            pages = ctx.count("###")
            return f"NODE_OUTPUT::retrieve_wiki: {pages} wiki excerpt(s) loaded"
        if node_name == "score":
            result = node_output.get("score_result", {})
            score = result.get("score", "?")
            justification = result.get("justification", "")[:80]
            return f"NODE_OUTPUT::score: reliability={score}/100 — {justification}"
        if node_name == "store":
            result = node_output.get("score_result", {})
            score = result.get("score", 0)
            emitted = score >= 60
            return f"NODE_OUTPUT::store: score={score} persisted, wiki_task_emitted={emitted}"
        return super()._summarise_node_output(node_name, node_output)

    async def _get_final_output(self, graph, initial_state: dict) -> str:
        result = await graph.ainvoke(initial_state)
        return result.get("output", "{}")
