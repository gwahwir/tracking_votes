"""Analyst agent executor."""
from __future__ import annotations

from agents.base.executor import LangGraphA2AExecutor
from .graph import build_analyst_graph


class AnalystAgentExecutor(LangGraphA2AExecutor):
    AGENT_NAME = "Johor Analyst Agent"
    AGENT_TYPE_ID = "analyst_agent"
    AGENT_DESCRIPTION = (
        "Multi-perspective analysis agent using a 7-stage LangGraph pipeline. "
        "Produces Political, Demographic, Historical, Strategic, Fact-check, "
        "and Bridget Welsh lens analyses for Johor election articles. "
        "Streams NODE_OUTPUT:: markers for each stage."
    )
    AGENT_PORT = 8003

    def build_graph(self):
        return build_analyst_graph()

    def _build_initial_state(self, message_text: str, metadata: dict) -> dict:
        return {
            "input": message_text,
            "metadata": metadata,
            "article_id": "",
            "article_text": "",
            "constituency_codes": [],
            "wiki_context": "",
            "system_prompt": "",
            "lenses": {},
            "peripheral_notes": "",
            "aggregation": "",
            "red_team_notes": "",
            "baseline_notes": "",
            "final_summary": "",
            "output": "",
        }

    def _summarise_node_output(self, node_name: str, node_output) -> str:
        if node_name == "retrieve_wiki":
            ctx = node_output.get("wiki_context", "")
            pages = ctx.count("###")
            codes = node_output.get("constituency_codes", [])
            return f"NODE_OUTPUT::retrieve_wiki: {pages} wiki page(s) loaded; constituencies={codes}"

        if node_name == "run_lenses":
            lenses = node_output.get("lenses", {})
            directions = {k: v.get("direction", "?") for k, v in lenses.items()}
            return f"NODE_OUTPUT::run_lenses: 6 lenses complete — {directions}"

        if node_name == "peripheral_scan":
            notes = node_output.get("peripheral_notes", "")
            return f"NODE_OUTPUT::peripheral_scan: {notes[:120]}"

        if node_name == "aggregate":
            agg = node_output.get("aggregation", "")
            return f"NODE_OUTPUT::aggregate: {agg[:120]}"

        if node_name == "red_team":
            rt = node_output.get("red_team_notes", "")
            return f"NODE_OUTPUT::red_team: {rt[:120]}"

        if node_name == "baseline_compare":
            bl = node_output.get("baseline_notes", "")
            return f"NODE_OUTPUT::baseline_compare: {bl[:120]}"

        if node_name == "final_synthesis":
            fs = node_output.get("final_summary", "")
            return f"NODE_OUTPUT::final_synthesis: {fs[:150]}"

        return super()._summarise_node_output(node_name, node_output)

    async def _get_final_output(self, graph, initial_state: dict) -> str:
        result = await graph.ainvoke(initial_state)
        return result.get("output", "{}")
