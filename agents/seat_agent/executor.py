"""Seat agent executor — win-likelihood prediction per constituency."""
from __future__ import annotations

import json
import logging
from typing import Any

from agents.base.executor import LangGraphA2AExecutor

log = logging.getLogger(__name__)


class SeatAgentExecutor(LangGraphA2AExecutor):
    """
    Aggregates multi-lens signals for a constituency and predicts win likelihood.

    Pipeline:
    1. gather_signals — retrieve all analyses for articles tagged to this constituency
    2. load_baseline — load constituency wiki baseline + party pages
    3. assess — LLM aggregates signals into SeatPrediction (party, confidence, signal breakdown)
    4. store — persist to seat_predictions table
    """

    def build_graph(self):
        """Build the 4-node LangGraph pipeline."""
        from langgraph.graph import END, StateGraph

        from .graph import assess, gather_signals, load_baseline, store

        graph = StateGraph(dict)
        graph.add_node("gather_signals", gather_signals)
        graph.add_node("load_baseline", load_baseline)
        graph.add_node("assess", assess)
        graph.add_node("store", store)

        graph.set_entry_point("gather_signals")
        graph.add_edge("gather_signals", "load_baseline")
        graph.add_edge("load_baseline", "assess")
        graph.add_edge("assess", "store")
        graph.add_edge("store", END)

        return graph.compile()

    def _build_initial_state(self, message_text: str, metadata: dict) -> dict:
        """Parse incoming message as JSON with constituency_code."""
        try:
            data = json.loads(message_text)
            code = data.get("constituency_code") or metadata.get("constituency_code")
        except Exception:
            code = metadata.get("constituency_code") or message_text
        return {"constituency_code": code, "input": message_text, "metadata": metadata}

    def prepare_input(self, message: str) -> dict:
        """Legacy — kept for compatibility."""
        try:
            data = json.loads(message)
            return {"constituency_code": data.get("constituency_code"), "context": data}
        except Exception:
            return {"constituency_code": message, "context": {}}

    def format_output(self, result: dict) -> str:
        """Format result as JSON string."""
        return json.dumps(result.get("seat_prediction", {}), indent=2)
