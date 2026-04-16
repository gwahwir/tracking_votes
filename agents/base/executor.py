"""LangGraphA2AExecutor — base class for all Johor Election agents.

Concrete agents subclass this and implement `build_graph()`.
The executor:
  - Runs the LangGraph graph for each incoming task
  - Emits NODE_OUTPUT:: SSE markers so the dashboard TaskMonitor shows live progress
  - Supports cancellation via CancellableMixin
  - Optionally traces via Langfuse
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

import structlog

from .cancellation import CancellableMixin
from .tracing import Trace

log = structlog.get_logger(__name__)

# Sentinel prefix for intermediate node outputs visible in the dashboard
NODE_OUTPUT_PREFIX = "NODE_OUTPUT::"


class LangGraphA2AExecutor(CancellableMixin):
    """Base executor.  Subclasses must implement ``build_graph()``."""

    # Override in each agent
    AGENT_NAME: str = "base_agent"
    AGENT_TYPE_ID: str = "base_agent"
    AGENT_DESCRIPTION: str = ""
    AGENT_PORT: int = 9000

    def __init__(self) -> None:
        super().__init__()
        self._graph = None

    def build_graph(self):
        """Return a compiled LangGraph CompiledGraph.

        Subclasses must override this method.
        """
        raise NotImplementedError

    def _get_graph(self):
        if self._graph is None:
            self._graph = self.build_graph()
        return self._graph

    # ------------------------------------------------------------------
    # Main entry point called by the A2A server
    # ------------------------------------------------------------------

    async def execute(
        self,
        task_id: str,
        message_text: str,
        metadata: dict[str, Any],
    ) -> AsyncGenerator[str, None]:
        """Run the LangGraph graph and yield SSE-formatted lines.

        Each node completion yields a ``NODE_OUTPUT::`` line so the dashboard
        can render live progress in the TaskMonitor.
        """
        trace = Trace(
            name=f"{self.AGENT_TYPE_ID}.execute",
            metadata={"task_id": task_id},
        )
        log.info("executor.start", agent=self.AGENT_TYPE_ID, task_id=task_id)

        initial_state = self._build_initial_state(message_text, metadata)
        graph = self._get_graph()

        try:
            # LangGraph streams (node_name, output) tuples when using .astream()
            async for chunk in graph.astream(initial_state, stream_mode="updates"):
                self.raise_if_cancelled()

                for node_name, node_output in chunk.items():
                    summary = self._summarise_node_output(node_name, node_output)
                    line = f"data: {_sse_json(node_name, summary)}\n\n"
                    log.debug("executor.node", agent=self.AGENT_TYPE_ID, node=node_name)
                    yield line

            # Final result
            final = await self._get_final_output(graph, initial_state)
            trace.update(output=final)
            yield f"data: {_sse_json('__result__', final)}\n\n"
            yield "data: [DONE]\n\n"

        except asyncio.CancelledError:
            log.info("executor.cancelled", task_id=task_id)
            yield f"data: {_sse_json('__cancelled__', 'Task cancelled')}\n\n"
            raise
        except Exception as exc:
            log.error("executor.error", task_id=task_id, error=str(exc))
            yield f"data: {_sse_json('__error__', str(exc))}\n\n"
            raise

    # ------------------------------------------------------------------
    # Hooks subclasses can override
    # ------------------------------------------------------------------

    def _build_initial_state(self, message_text: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """Build the initial LangGraph state dict from the A2A message."""
        return {"input": message_text, "metadata": metadata}

    def _summarise_node_output(self, node_name: str, node_output: Any) -> str:
        """Convert a node's raw output to a short string for the SSE stream."""
        if isinstance(node_output, dict):
            # Return a brief summary — subclasses may override for richer info
            keys = list(node_output.keys())
            return f"{NODE_OUTPUT_PREFIX}{node_name}: keys={keys}"
        return f"{NODE_OUTPUT_PREFIX}{node_name}: done"

    async def _get_final_output(self, graph, initial_state: dict) -> str:
        """Run the graph to completion and return the final output string.

        This is called after streaming to collect the final answer.
        Override if your graph stores the result in a specific state key.
        """
        # Re-invoke (non-streaming) to get the final state
        result = await graph.ainvoke(initial_state)
        return str(result.get("output", result))

    # ------------------------------------------------------------------
    # Agent card (served at /.well-known/agent-card.json)
    # ------------------------------------------------------------------

    def agent_card(self) -> dict[str, Any]:
        import os
        port = int(os.environ.get(f"{self.AGENT_TYPE_ID.upper()}_PORT", self.AGENT_PORT))
        base_url = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8000")
        agent_url = f"http://localhost:{port}"
        return {
            "name": self.AGENT_NAME,
            "type_id": self.AGENT_TYPE_ID,
            "description": self.AGENT_DESCRIPTION,
            "url": agent_url,
            "capabilities": {
                "streaming": True,
                "cancellation": True,
            },
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

import json as _json


def _sse_json(node: str, content: Any) -> str:
    return _json.dumps({"type": "node_output", "node": node, "content": content})
