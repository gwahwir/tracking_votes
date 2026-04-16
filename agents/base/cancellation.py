"""CancellableMixin — gives any executor a thread-safe cancellation flag."""
from __future__ import annotations

import asyncio


class CancellableMixin:
    """Mix into executor classes to get cancel() / is_cancelled() support."""

    def __init__(self) -> None:
        self._cancelled: bool = False
        self._cancel_event: asyncio.Event = asyncio.Event()

    def cancel(self) -> None:
        self._cancelled = True
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        return self._cancelled

    async def wait_for_cancel(self, timeout: float | None = None) -> bool:
        """Await until cancelled (or timeout).  Returns True if cancelled."""
        try:
            await asyncio.wait_for(self._cancel_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    def raise_if_cancelled(self) -> None:
        if self._cancelled:
            raise asyncio.CancelledError("Task was cancelled by the control plane")
