import asyncio
from typing import Awaitable, Callable

from src.types.models import Session
from src.utils.env import DTMF_MAX_DIGITS, DTMF_TIMEOUT
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DtmfBuffer:
    """Buffers DTMF digits received and flushes them per session configuration"""

    def __init__(self):
        self.session: Session | None = None
        self.buffer: str = ""
        self.timer_handle: asyncio.TimerHandle | None = None

    def clear(self):
        # Cancel existing timers so they do not trigger any callbacks
        if self.timer_handle is not None:
            self.timer_handle.cancel()

    async def flush(self, callback: Callable[[str], Awaitable[None]]):
        logger.info(
            "Returning buffered DTMF",
            {
                "sessionId": self.session.SessionId
                if self.session is not None
                else "unknown",
                "digits": self.buffer,
            },
        )
        try:
            await callback(self.buffer)
        except Exception as error:
            logger.error("Error in DTMF callback", {"error": str(error)})
        self.buffer = ""

    async def handle_input(
        self, digit: str, callback: Callable[[str], Awaitable[None]]
    ):
        self.buffer += digit

        # Cancel existing timers so they do not trigger any callbacks
        if self.timer_handle is not None:
            self.timer_handle.cancel()

        max_digits = DTMF_MAX_DIGITS
        timeout = DTMF_TIMEOUT
        if self.session is not None:
            max_digits = self.session.Config.DTMF.MaxDigits
            timeout = self.session.Config.DTMF.Timeout

        # If we hit max_digits, we want to trigger the callback immediately rather than wait for more input
        if len(self.buffer) >= max_digits:
            await self.flush(callback)
            return

        # Wait for more digits up to the timeout before flushing
        loop = asyncio.get_running_loop()
        self.timer_handle = loop.call_later(
            timeout, lambda: asyncio.create_task(self.flush(callback))
        )
