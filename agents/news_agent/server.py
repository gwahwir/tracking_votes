"""News agent — FastAPI app entry point."""
from agents.base.server import build_a2a_app
from .executor import NewsAgentExecutor

app = build_a2a_app(NewsAgentExecutor())
