"""Signals analyser — FastAPI app entry point."""
from agents.base.server import build_a2a_app
from .executor import SignalsAnalyserExecutor

app = build_a2a_app(SignalsAnalyserExecutor())
