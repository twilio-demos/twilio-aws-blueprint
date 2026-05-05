"""
Twilio Agent Connect (TAC) voice agent application.

This application uses the TAC SDK to handle ConversationRelay WebSocket connections
and integrates with Strands agent framework for appointment scheduling.

Key features:
- Real-time voice streaming via ConversationRelay
- Conversation Orchestrator integration for memory and context
- Strands agent for appointment scheduling with tool calling
- Idle detection and timeout handling
- Message persistence to DynamoDB
- Multi-turn conversational flow

Usage:
    python -m src.main_tac
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from tac import TAC, TACConfig
from tac.channels.voice import VoiceChannel
from tac.models.handoff import PendingHandoffData
from tac.models.session import ConversationSession
from tac.models.voice import InterruptMessage
from tac.server import TACFastAPIServer

from src.ai.agent.core.strands_agent_runner import StrandsAgentRunner
from src.services.threadservice import instance as thread_service
from src.types.models import MessageType
from src.types.models import Session as LegacySession
from src.utils.env import AGENT_RUNNER_TYPE
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ============================================================================
# Idle Detection System
# ============================================================================


class IdleMinder:
    """Tracks idle state and triggers prompts."""

    def __init__(
        self, timeout: float = 20.0, max_attempts: int = 3, idle_callback=None
    ):
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.idle_callback = idle_callback
        self.attempts = 0
        self.timer_handle: asyncio.TimerHandle | None = None

    def clear(self):
        """Cancel idle timer."""
        if self.timer_handle:
            self.timer_handle.cancel()
            self.timer_handle = None

    def reset_attempts(self):
        """Reset attempt counter (user is active)."""
        self.attempts = 0

    def start_idle_timer(self):
        """Start idle detection timer."""
        self.clear()
        loop = asyncio.get_running_loop()
        self.timer_handle = loop.call_later(
            self.timeout, lambda: asyncio.create_task(self._trigger_idle())
        )

    async def _trigger_idle(self):
        """Called when idle timeout expires."""
        self.attempts += 1
        reached_max = self.attempts >= self.max_attempts

        if self.idle_callback:
            await self.idle_callback(reached_max)

        # Restart timer if not at max attempts
        if not reached_max:
            self.start_idle_timer()


# Store idle minders per conversation
idle_minders: dict[str, IdleMinder] = {}

# ============================================================================
# TAC Configuration
# ============================================================================

# Initialize TAC
config = TACConfig.from_env()
tac = TAC(config=config)
voice_channel = VoiceChannel(tac, config={"auto_retrieve_memory": True})

logger.info(
    "TAC initialized",
    {
        "mode": "conversation_orchestrator"
        if config.conversation_configuration_id
        else "relay_only",
    },
)

# Store agent runners per conversation (since Strands needs session context)
agent_runners: dict[str, StrandsAgentRunner] = {}

# ============================================================================
# Helper Functions
# ============================================================================


def initialize_session_metadata(session: ConversationSession):
    """Initialize session metadata with configuration."""
    if not session.metadata:
        session.metadata = {}

    # Initialize defaults (replaces SessionService)
    session.metadata.setdefault("thread_id", str(uuid.uuid4()))
    session.metadata.setdefault("idle_timeout", 20)
    session.metadata.setdefault("idle_max_attempts", 3)
    session.metadata.setdefault("language", "en-US")
    session.metadata.setdefault("status", "active")
    session.metadata.setdefault("dtmf_max_digits", 10)
    session.metadata.setdefault("dtmf_timeout", 3)
    session.metadata.setdefault("user_authenticated", False)
    session.metadata.setdefault("username", None)


def create_legacy_session(
    session: ConversationSession, thread_id: str
) -> LegacySession:
    """Create a legacy Session object for compatibility with existing services."""
    return LegacySession(
        CallSid=session.conversation_id,
        SessionId=session.conversation_id,
        ThreadId=thread_id,
        Created=datetime.now(timezone.utc).isoformat(),
        CallFrom=session.author_info.address if session.author_info else None,
        CallTo=None,
    )


async def handle_idle_timeout(reached_max: bool, conv_id: str):
    """Handle idle timeout - send reminder or end call."""
    if reached_max:
        logger.info("Max idle attempts reached, ending call", {"conv_id": conv_id})
        # End call after too many idle attempts
        sessions = voice_channel._conversations
        if conv_id in sessions:
            session = sessions[conv_id]
            session.pending_handoff_data = PendingHandoffData(
                type="end", handoffData='{"result":"idle_timeout"}'
            )

        await voice_channel.send_response(
            conv_id, "I haven't heard from you in a while. Goodbye!"
        )
    else:
        logger.debug(
            f"Sending idle reminder (attempt {idle_minders[conv_id].attempts if conv_id in idle_minders else 0})"
        )
        await voice_channel.send_response(conv_id, "Are you still there?")


# ============================================================================
# TAC Callbacks
# ============================================================================


async def handle_message_ready(
    user_message: str, session: ConversationSession, memory_response
) -> None:
    """Main message handler - processes user input through Strands agent."""
    conv_id = session.conversation_id

    logger.info(
        "📥 Message received",
        {
            "conv_id": conv_id,
            "message": user_message[:50] + "..."
            if len(user_message) > 50
            else user_message,
        },
    )

    # Log memory response from Conversation Orchestrator
    if memory_response:
        # Extract memory details
        memory_dict = {}
        memory_attrs = []
        try:
            # First, inspect available attributes
            memory_attrs = [attr for attr in dir(memory_response) if not attr.startswith('_')]

            # Try to convert to dict if it has model_dump
            if hasattr(memory_response, 'model_dump'):
                memory_dict = memory_response.model_dump()
            elif hasattr(memory_response, 'dict'):
                memory_dict = memory_response.dict()
            else:
                # Fallback: extract public attributes
                memory_dict = {
                    k: getattr(memory_response, k)
                    for k in memory_attrs
                    if not callable(getattr(memory_response, k))
                }
        except Exception as e:
            logger.warning(f"Could not serialize memory_response: {e}")
            memory_dict = {"error": str(e)}

        logger.info(
            "💾 Memory retrieved from CO",
            {
                "conv_id": conv_id,
                "memory_data": memory_dict,
                "available_attrs": memory_attrs[:10],  # First 10 attrs
            },
        )

    # Initialize session metadata
    initialize_session_metadata(session)

    # Initialize idle minder
    if conv_id not in idle_minders:
        idle_timeout = session.metadata["idle_timeout"]
        idle_max_attempts = session.metadata["idle_max_attempts"]

        idle_minders[conv_id] = IdleMinder(
            timeout=idle_timeout,
            max_attempts=idle_max_attempts,
            idle_callback=lambda reached_max: handle_idle_timeout(reached_max, conv_id),
        )

    # User is active - reset idle tracking
    minder = idle_minders[conv_id]
    minder.reset_attempts()
    minder.clear()

    # Get thread_id and create legacy session
    thread_id = session.metadata["thread_id"]
    legacy_session = create_legacy_session(session, thread_id)

    # Initialize Strands agent runner for this conversation
    if conv_id not in agent_runners:

        async def update_language_handler(language: str):
            """Update conversation language via WebSocket message."""
            session.metadata["language"] = language
            websocket = voice_channel.get_websocket(conv_id)
            if websocket:
                try:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "language",
                                "ttsLanguage": language,
                                "transcriptionLanguage": language,
                            }
                        )
                    )
                    await websocket.send_text(
                        json.dumps({"type": "text", "token": "", "last": True})
                    )
                    logger.info(
                        "Language updated", {"conv_id": conv_id, "language": language}
                    )
                except Exception as e:
                    logger.error("Failed to send language switch", {"error": str(e)})

        async def perform_handoff_handler(handoff_data: dict):
            """Trigger handoff to human agent by setting pending_handoff_data."""
            logger.info("Handoff requested", {"conv_id": conv_id})
            sessions = voice_channel._conversations
            if conv_id in sessions:
                sessions[conv_id].pending_handoff_data = PendingHandoffData(
                    type="end", handoffData=json.dumps(handoff_data)
                )

        # Create Strands agent runner
        agent_runners[conv_id] = StrandsAgentRunner(
            legacy_session,
            update_language_handler,
            perform_handoff_handler,
        )

        logger.info(
            "Strands agent runner created",
            agent_runners[conv_id].get_agent_system_info(),
        )

    # Get the agent runner
    agent_runner = agent_runners[conv_id]

    # Save user message to threadservice
    thread_service.append(legacy_session, user_message, MessageType.user)

    # Create async generator to stream response tokens
    async def stream_response():
        """Stream content tokens from Strands agent."""
        collected_response = ""
        try:
            async for chunk in agent_runner.stream_request(user_message):
                if chunk.get("type") == "content":
                    content = chunk.get("data", "")
                    if isinstance(content, str):
                        collected_response += content
                        yield content
        except Exception as e:
            logger.error(f"Error streaming from Strands agent: {e}")
            error_msg = (
                "I apologize, but I'm having trouble processing your request right now."
            )
            if not collected_response:
                yield error_msg
        finally:
            if collected_response:
                logger.info(
                    "Response sent",
                    {
                        "conv_id": conv_id,
                        "length": len(collected_response),
                    },
                )

    # Stream response to the user in real-time
    await voice_channel.send_response(conv_id, stream_response())

    # After response completes, restart idle timer
    if conv_id in idle_minders:
        idle_minders[conv_id].start_idle_timer()


async def handle_interrupt(
    session: ConversationSession, interrupt_msg: InterruptMessage
):
    """Handle user interruption - clear idle timer as user is active."""
    conv_id = session.conversation_id
    logger.debug(f"User interrupted at {interrupt_msg.duration_until_interrupt_ms}ms")

    # Clear idle timer - user is active
    if conv_id in idle_minders:
        idle_minders[conv_id].reset_attempts()
        idle_minders[conv_id].clear()


async def handle_conversation_ended(session: ConversationSession):
    """Clean up when conversation ends."""
    conv_id = session.conversation_id

    logger.info("Conversation ended", {"conv_id": conv_id})

    # Clean up idle minder
    if conv_id in idle_minders:
        idle_minders[conv_id].clear()
        del idle_minders[conv_id]

    # Clean up agent runner
    if conv_id in agent_runners:
        del agent_runners[conv_id]

    # Note: Message history persists in DynamoDB via threadservice


# ============================================================================
# Register TAC Callbacks
# ============================================================================

tac.on_message_ready(handle_message_ready)
tac.on_interrupt(handle_interrupt)
tac.on_conversation_ended(handle_conversation_ended)

# ============================================================================
# Start Server
# ============================================================================


def start():
    """Start the TAC FastAPI server."""
    logger.info("Starting Twilio Agent Connect application")
    logger.info(f"Agent runner: {AGENT_RUNNER_TYPE}")

    # Create and start TAC FastAPI server
    server = TACFastAPIServer(tac=tac, voice_channel=voice_channel)
    server.start()


if __name__ == "__main__":
    start()
