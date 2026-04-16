"""Wiki agent — FastAPI app entry point."""
from agents.base.server import build_a2a_app
from .executor import WikiAgentExecutor

app = build_a2a_app(WikiAgentExecutor())
