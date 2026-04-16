"""Wiki agent executor — routes to ingest or lint graph based on the task message."""
from __future__ import annotations

from agents.base.executor import LangGraphA2AExecutor
from .graph import build_ingest_graph, build_lint_graph


class WikiAgentExecutor(LangGraphA2AExecutor):
    AGENT_NAME = "Johor Wiki Agent"
    AGENT_TYPE_ID = "wiki_agent"
    AGENT_DESCRIPTION = (
        "LLM-wiki ingest and lint agent. "
        "Ingests article content into the wiki knowledge base; "
        "also runs lint checks for contradictions and staleness."
    )
    AGENT_PORT = 8005

    def __init__(self) -> None:
        super().__init__()
        self._ingest_graph = None
        self._lint_graph = None

    def build_graph(self):
        # Default graph is the ingest graph
        return self._get_ingest_graph()

    def _get_ingest_graph(self):
        if self._ingest_graph is None:
            self._ingest_graph = build_ingest_graph()
        return self._ingest_graph

    def _get_lint_graph(self):
        if self._lint_graph is None:
            self._lint_graph = build_lint_graph()
        return self._lint_graph

    def _build_initial_state(self, message_text: str, metadata: dict) -> dict:
        mode = metadata.get("mode", "ingest")
        if mode == "lint":
            return {"input": message_text, "metadata": metadata, "report": {}, "output": ""}
        return {
            "input": message_text,
            "metadata": metadata,
            "relevant_pages": [],
            "updates": [],
            "log_entry": "",
            "output": "",
        }

    async def execute(self, task_id, message_text, metadata):
        mode = metadata.get("mode", "ingest")
        graph = self._get_lint_graph() if mode == "lint" else self._get_ingest_graph()

        # Temporarily swap self._graph so the parent execute() uses the right one
        self._graph = graph
        async for chunk in super().execute(task_id, message_text, metadata):
            yield chunk

    def _summarise_node_output(self, node_name: str, node_output) -> str:
        if node_name == "retrieve_wiki":
            pages = node_output.get("relevant_pages", [])
            names = [p.path for p in pages]
            return f"NODE_OUTPUT::retrieve_wiki: found {len(pages)} relevant page(s): {names}"
        if node_name == "update_pages":
            updates = node_output.get("updates", [])
            return f"NODE_OUTPUT::update_pages: {len(updates)} page(s) queued for update"
        if node_name == "write_updates":
            return f"NODE_OUTPUT::write_updates: {node_output.get('output', 'done')}"
        if node_name == "lint":
            report = node_output.get("report", {})
            return f"NODE_OUTPUT::lint: {report.get('summary', 'done')}"
        return super()._summarise_node_output(node_name, node_output)

    async def _get_final_output(self, graph, initial_state: dict) -> str:
        result = await graph.ainvoke(initial_state)
        return result.get("output", "done")
