import asyncio
import math
from typing import Awaitable, Callable
from src.utils.logger import get_logger

logger = get_logger(__name__)

class IdleMinder:
    """Waits for the session to become idle and invokes an action to remind the user."""
    
    def __init__(self, idle_callback: Callable[[bool], Awaitable[None]]):
        self.session_id: str = None
        self.attempts = 0
        self.timer_handle: asyncio.TimerHandle = None
        self.idle_callback: Callable = idle_callback
        
        # TODO: Pull params from session
        self.timeout = 20
        self.max_attempts = 3
    
    def clear(self):
      # Cancel existing timers so they do not trigger any callbacks
      if self.timer_handle is not None:
          self.timer_handle.cancel()
    
    def set_timer(self, additional_time_sec: int = 0):
      self.clear()
      loop = asyncio.get_running_loop()
      self.timer_handle = loop.call_later(self.timeout + additional_time_sec, lambda: asyncio.create_task(self.trigger()))
    
    async def trigger(self):
        logger.info("Triggering idle minder", {
            "sessionId": self.session_id,
            "attempts": self.attempts
        })
        try:
            await self.idle_callback(self.attempts >= self.max_attempts)
        except Exception as error:
            logger.error("Error in idle callback", {"error": str(error)})
    
    def handle_activity(self, already_idle: bool = False, response_text: str = ""):
        if already_idle:
            self.attempts += 1
        else:
            self.attempts = 1
        
        # To prevent idle detection during a lengthy response, extend the duration based on the response length
        additional_time_sec = math.ceil(len(response_text.split(" ")) / 2) # Add one half second per word
        
        self.set_timer(additional_time_sec)