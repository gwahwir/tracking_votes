"""Seat agent — FastAPI app entry point."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from agents.base.server import build_a2a_app
from agents.base.registration import register_with_control_plane
from control_plane.db import init_database
from .executor import SeatAgentExecutor

executor = SeatAgentExecutor()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        await init_database(database_url)
    await register_with_control_plane(executor.agent_card())
    yield


app = build_a2a_app(executor, lifespan_override=_lifespan)
