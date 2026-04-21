"""Structured logging configuration."""
from __future__ import annotations

import logging
import sys
import uuid

import structlog
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


def configure_logging(log_level: str = "INFO") -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=level,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer() if sys.stderr.isatty()
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Return a clean JSON 500 for any unhandled exception and log it."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            log = structlog.get_logger(__name__)
            log.error(
                "unhandled_error",
                path=request.url.path,
                method=request.method,
                error=str(exc),
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "type": type(exc).__name__},
            )


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Inject X-Request-ID into structlog context for every request."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=correlation_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = correlation_id
        return response
