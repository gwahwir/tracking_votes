"""Signals analyser executor."""
from __future__ import annotations

from agents.base.executor import LangGraphA2AExecutor
from .graph import build_signals_graph


class SignalsAnalyserExecutor(LangGraphA2AExecutor):
    AGENT_NAME = "Johor Signals Analyser"
    AGENT_TYPE_ID = "signals_analyser"
    AGENT_DESCRIPTION = (
        "Analyses social media signals (Reddit, Lowyat) for electoral sentiment "
        "relevant to the Johor election. Produces tone, claim, implication, and "
        "signal_strength. Writes a single social_signal lens entry to analyses."
    )
    AGENT_PORT = 8006

    def build_graph(self):
        return build_signals_graph()

    def _build_initial_state(self, message_text: str, metadata: dict) -> dict:
        return {
            "input": message_text,
            "metadata": metadata,
            "article_id": "",
            "article_text": "",
            "source": "",
            "engagement": {},
            "analysis": {},
            "output": "",
        }

    def _summarise_node_output(self, node_name: str, node_output) -> str:
        if node_name == "analyse":
            a = node_output.get("analysis", {})
            return f"NODE_OUTPUT::analyse: tone={a.get('tone')} implication={a.get('implication')} strength={a.get('signal_strength')}"
        if node_name == "store":
            a = node_output.get("analysis", {})
            return f"NODE_OUTPUT::store: claim saved — {a.get('claim', '')[:80]}"
        return super()._summarise_node_output(node_name, node_output)

    def _extract_final_output(self, final_state: dict) -> str:
        return final_state.get("output", "{}")
