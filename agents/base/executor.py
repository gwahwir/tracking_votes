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
        """Run the LangGraph graph and yield SSE-formatted lines."""
        log.info("executor.start", agent=self.AGENT_TYPE_ID, task_id=task_id)

        initial_state = self._build_initial_state(message_text, metadata)
        graph = self._get_graph()

        try:
            final_state: dict[str, Any] = {}
            async for chunk in graph.astream(initial_state, stream_mode="updates"):
                self.raise_if_cancelled()

                for node_name, node_output in chunk.items():
                    summary = self._summarise_node_output(node_name, node_output)
                    line = f"data: {_sse_json(node_name, summary)}\n\n"
                    log.debug("executor.node", agent=self.AGENT_TYPE_ID, node=node_name)
                    yield line
                    if isinstance(node_output, dict):
                        final_state.update(node_output)

            final = self._extract_final_output(final_state)
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

    def _extract_final_output(self, final_state: dict[str, Any]) -> str:
        """Extract the final output string from the accumulated stream state.

        Subclasses may override to pull from a specific state key.
        """
        return str(final_state.get("output", "done"))

    # ------------------------------------------------------------------
    # Agent card (served at /.well-known/agent-card.json)
    # ------------------------------------------------------------------

    def agent_card(self) -> dict[str, Any]:
        import os
        port = int(os.environ.get(f"{self.AGENT_TYPE_ID.upper()}_PORT", self.AGENT_PORT))
        # Use Docker service name (e.g., news_agent, scorer_agent) when in Docker
        # Otherwise fall back to localhost for local development
        hostname = os.environ.get("AGENT_HOSTNAME") or self.AGENT_TYPE_ID
        agent_url = f"http://{hostname}:{port}"
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
