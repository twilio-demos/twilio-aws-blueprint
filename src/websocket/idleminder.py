import asyncio
from typing import Awaitable, Callable

from src.types.models import Session
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IdleMinder:
    """Waits for the session to become idle and invokes an action to remind the user."""

    def __init__(
        self, session: Session, idle_callback: Callable[[bool], Awaitable[None]]
    ):
        self.session = session
        self.attempts = 0
        self.timer_handle: asyncio.TimerHandle | None = None
        self.idle_callback: Callable = idle_callback

    def clear(self):
        # Cancel existing timers so they do not trigger any callbacks
        if self.timer_handle is not None:
            self.timer_handle.cancel()

    def handle_idle(self):
        self.clear()

        loop = asyncio.get_running_loop()
        self.timer_handle = loop.call_later(
            self.session.Config.Idle.Timeout,
            lambda: asyncio.create_task(self.trigger()),
        )

    def handle_activity(self):
        self.attempts = 0

    async def trigger(self):
        self.attempts += 1
        logger.info(
            "Triggering idle minder",
            {
                "sessionId": self.session.SessionId,
                "attempts": self.attempts,
            },
        )
        try:
            await self.idle_callback(
                self.attempts >= self.session.Config.Idle.MaxAttempts
            )
        except Exception as error:
            logger.error("Error in idle callback", {"error": str(error)})
