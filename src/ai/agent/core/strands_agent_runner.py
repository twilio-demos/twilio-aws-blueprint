"""Strands-based AI Agent Runner implementation."""

import json
from typing import AsyncGenerator, Awaitable, Callable

from strands import Agent

from src.ai.agent.core.base_agent_runner import BaseAgentRunner
from src.ai.agent.strands.agent import StrandsAgentFactory
from src.services.sessionservice import instance as session_service
from src.services.threadservice import instance as thread_service
from src.types.models import MessageType, Session, StreamChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StrandsAgentRunner(BaseAgentRunner):
    """Strands-based AI Agent Runner for conversation handling."""

    def __init__(
        self,
        session: Session,
        update_language_handler: Callable[[str], Awaitable[None]],
        perform_handoff_handler: Callable[[any], Awaitable[None]],
    ):
        """
        Initialize the Strands Agent Runner.

        Args:
            session: Initialized user session
            update_language_handler: ConversationRelay handler for changing language
            perform_handoff_handler: ConversationRelay handler for performing handoff
        """
        super().__init__(session)
        self.update_language_handler = update_language_handler
        self.perform_handoff_handler = perform_handoff_handler
        self.agent: Agent = None
        self.initialize_agent_system()

    def initialize_agent_system(self) -> None:
        """Initialize the Strands agent system."""
        self.agent = StrandsAgentFactory.create_conversation_agent()
        logger.info("Strands agent system initialized")

    def get_agent_system_info(self) -> dict:
        """Get information about the Strands agent system."""
        if not self.agent:
            return {"error": "Agent system not initialized"}

        # Get tool names from the agent
        tool_names = []
        if hasattr(self.agent, "tool_names") and self.agent.tool_names:
            # Strands provides tool_names attribute (set or list)
            tool_names = list(self.agent.tool_names)

        return {
            "system_type": "Strands",
            "agent_name": (
                self.agent.name if hasattr(self.agent, "name") else "conversation_agent"
            ),
            "tools": tool_names,
            "tool_count": len(tool_names),
        }

    def _build_context_message(self, user_input: str) -> str:
        """Build message with session context."""
        # Add session context to message
        context_parts = [user_input]

        # Add session state context if available
        # this is where you would add any relevant session state information that (use case dependent) the agent might need to know for processing the request.
        # For example, if you have user authentication status, previous interactions, or any other contextual data stored in the session, you can append it to the context_parts list here.
        if self.session.SessionState:
            if self.session.SessionState.get("user_authenticated"):
                username = self.session.SessionState.get("username", "User")
                context_parts.append(f"\n[User {username} is authenticated]")
            else:
                context_parts.append("\n[User is not authenticated]")

        # # Add message history context
        # if self.state["messages"]:
        #     history_summary = f"\n[Previous messages: {len(self.state['messages'])}]"
        #     context_parts.append(history_summary)

        return "".join(context_parts)

    async def stream_request(
        self, user_input: str
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Process a user request with streaming responses.

        Args:
            user_input: User's input text

        Yields:
            Streaming response chunks
        """
        logger.info("Streaming request (Strands):", {"user_input": user_input})
        logger.info("=" * 60)

        # Track tool usage: map tool_use_id to tool_name
        active_tools = {}

        # Accumulate full response to save to DynamoDB
        full_response = ""

        try:
            # Build message with context
            message = self._build_context_message(user_input)

            # Stream response from Strands agent (using async streaming)
            async for event in self.agent.stream_async(message):
                logger.debug(f"Received event: {event}")

                # Handle text content streaming
                if "data" in event and event["data"]:
                    content = event["data"]
                    logger.debug(
                        f"Streaming content: {content[:50]}..."
                        if len(content) > 50
                        else content
                    )
                    # Accumulate for persistence
                    full_response += content
                    yield {"type": "content", "data": content}

                # Handle tool usage tracking - store tool name by ID
                if "current_tool_use" in event:
                    tool_use = event["current_tool_use"]
                    if tool_use and "name" in tool_use:
                        tool_name = tool_use["name"]
                        tool_use_id = tool_use.get("toolUseId")
                        logger.info(f"🔧 Tool in use: {tool_name} (ID: {tool_use_id})")

                        # Store the mapping
                        if tool_use_id:
                            active_tools[tool_use_id] = tool_name

                        # Track tool input as it accumulates
                        if "input" in tool_use:
                            logger.debug(f"Tool input: {tool_use['input']}")

                # Handle tool streaming events (progress updates from tools)
                if "tool_stream_event" in event:
                    tool_stream = event["tool_stream_event"]
                    if tool_stream and "data" in tool_stream:
                        logger.debug(f"Tool progress: {tool_stream['data']}")

                # Handle message events that contain tool results
                if "message" in event:
                    message = event["message"]
                    if message.get("role") == "user" and "content" in message:
                        # Check if this message contains tool results
                        for content_block in message["content"]:
                            if (
                                isinstance(content_block, dict)
                                and "toolResult" in content_block
                            ):
                                tool_result = content_block["toolResult"]
                                tool_use_id = tool_result.get("toolUseId")
                                content = tool_result.get("content")

                                logger.debug(
                                    f"Tool result in message - ID: {tool_use_id}, Content: {content}"
                                )

                                if tool_use_id and content:
                                    # Get the tool name from our tracking
                                    tool_name = active_tools.get(tool_use_id)

                                    if tool_name:
                                        logger.info(
                                            f"[Tool Result] {tool_name} completed"
                                        )

                                        # Extract the actual result string from content
                                        result_str = None

                                        # Try different content structures
                                        if (
                                            isinstance(content, list)
                                            and len(content) > 0
                                        ):
                                            # Content is typically [{"text": "result"}]
                                            first_item = content[0]
                                            if isinstance(first_item, dict):
                                                if "text" in first_item:
                                                    result_str = first_item["text"]
                                                elif "content" in first_item:
                                                    result_str = first_item["content"]
                                            elif isinstance(first_item, str):
                                                result_str = first_item
                                        elif isinstance(content, str):
                                            result_str = content
                                        elif isinstance(content, dict):
                                            # Sometimes content is directly a dict
                                            if "text" in content:
                                                result_str = content["text"]
                                            elif "content" in content:
                                                result_str = content["content"]

                                        logger.debug(
                                            f"Extracted result_str: {result_str}"
                                        )

                                        if result_str:
                                            logger.info(
                                                f"Invoking handler for {tool_name} with result: {result_str}"
                                            )
                                            await self._handle_tool_result(
                                                tool_name, result_str
                                            )
                                        else:
                                            logger.warning(
                                                f"Could not extract result string from content: {content}"
                                            )

                                        # Clean up tracking
                                        if tool_use_id in active_tools:
                                            del active_tools[tool_use_id]
                                    else:
                                        logger.warning(
                                            f"Tool result received for unknown tool_use_id: {tool_use_id}"
                                        )

            logger.info("🔍 Stream completed (Strands)")

            # Save agent response
            if full_response:
                thread_service.append(self.session, full_response, MessageType.agent)
                logger.info(
                    f"Saved agent response to DynamoDB ({len(full_response)} chars)"
                )

        except Exception as e:
            import traceback

            error_msg = f"Streaming error (Strands): {str(e)}"
            logger.error(error_msg)
            logger.error(f"Full traceback: {traceback.format_exc()}")

    async def _handle_tool_result(self, tool_name: str, result: str | None):
        """Handle tool results that require relay actions."""
        if not result:
            logger.warning(f"Tool {tool_name} returned empty result")
            return

        try:
            logger.info(f"Handling tool result for {tool_name} with result: {result}")

            # Handle update_language_tool
            if tool_name == "update_language_tool":
                # Result is the language code
                logger.info(f"Calling update_language_handler with: {result}")
                await self.update_language_handler(result)
                logger.info("update_language_handler completed successfully")

            # Handle perform_handoff_tool
            elif tool_name == "perform_handoff_tool":
                logger.info(f"Parsing handoff data: {result}")
                handoff_data = json.loads(result)
                logger.info(f"Calling perform_handoff_handler with: {handoff_data}")
                await self.perform_handoff_handler(handoff_data)
                logger.info("perform_handoff_handler completed successfully")

            # Handle update_hints_tool
            elif tool_name == "update_hints_tool":
                logger.info(f"Hints update: {result}")
                # This should be implemented if needed, this should trigger handoff i.e restart session with new hints
                # For now, just log that hints were updated
                logger.info(
                    "Hints updated successfully (no action required in relay-only mode)"
                )

            # Handle look_up_availability
            elif tool_name == "look_up_availability":
                logger.info(f"Parsing availability data: {result}")
                availability_data = json.loads(result)

                if availability_data.get("success"):
                    appointments = availability_data.get("appointments", {})
                    slot_count = sum(len(slots) for slots in appointments.values())
                    logger.info(f"Found {slot_count} available appointment slots")

                    # Update session state
                    updated_state = dict(self.session.SessionState)
                    updated_state["last_availability_check"] = result
                    updated_state["scheduling_step"] = "selecting_slot"
                    session_service.update_state(self.session, updated_state)
                    logger.info("Session state updated with availability check")

            # Handle schedule_appointment
            elif tool_name == "schedule_appointment":
                logger.info(f"Parsing appointment data: {result}")
                appointment_data = json.loads(result)

                if appointment_data.get("success"):
                    confirmation_number = appointment_data.get("confirmation_number")
                    logger.info(f"Appointment scheduled: {confirmation_number}")

                    # Update session state with appointment details
                    updated_state = dict(self.session.SessionState)
                    updated_state["appointment_scheduled"] = True
                    updated_state["appointment_data"] = (
                        result  # Store full JSON as string
                    )
                    updated_state["confirmation_number"] = confirmation_number
                    updated_state["scheduling_step"] = "confirmed"
                    session_service.update_state(self.session, updated_state)
                    logger.info(
                        f"Session state updated with appointment: {confirmation_number}"
                    )
                else:
                    error = appointment_data.get("error", "Unknown error")
                    logger.error(f"Appointment scheduling failed: {error}")

                    # Update session state with failure
                    updated_state = dict(self.session.SessionState)
                    updated_state["scheduling_step"] = "failed"
                    updated_state["last_error"] = error
                    session_service.update_state(self.session, updated_state)

            else:
                logger.debug(f"Tool {tool_name} does not require handler")

        except Exception as e:
            import traceback

            logger.error(f"Error handling tool result for {tool_name}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
