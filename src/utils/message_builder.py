"""
Agent Message Builder for constructing rich messages with tool calls.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, ToolMessage

from src.types.models import Message, MessageContent, MessageType, ToolCall
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AgentMessageBuilder:
    """Builds rich agent messages that include tool calls and metadata."""

    def __init__(self, thread_id: str):
        self.thread_id = thread_id
        self.text_parts: List[str] = []
        self.tool_calls: List[ToolCall] = []
        self.agent_name: str | None = None
        self.metadata: Dict[str, Any] = {}

    def add_text(self, text: str) -> None:
        """Add text content to the message."""
        if text and text.strip():
            self.text_parts.append(text.strip())

    def add_tool_call(self, tool_call: ToolCall) -> None:
        """Add a tool call to the message."""
        self.tool_calls.append(tool_call)

    def set_agent_name(self, agent_name: str) -> None:
        """Set the name of the agent that generated this message."""
        self.agent_name = agent_name

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the message."""
        self.metadata[key] = value

    def process_ai_message(
        self, ai_message: AIMessage, sender: str | None = None
    ) -> None:
        """
        Process a LangChain AIMessage and extract all relevant information.

        Args:
            ai_message: The AIMessage from LangChain
            sender: The name of the agent that sent this message
        """
        if sender:
            self.set_agent_name(sender)

        # Handle different content types
        if isinstance(ai_message.content, str):
            self.add_text(ai_message.content)
        elif isinstance(ai_message.content, list):
            for i, block in enumerate(ai_message.content):
                logger.debug(f"Processing block {i}: {block} (type: {type(block)})")
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        self.add_text(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        # Handle tool use blocks
                        tool_id = block.get("id")
                        if not tool_id:
                            tool_id = str(uuid.uuid4())
                            logger.warning(
                                f"Generated UUID for missing tool_use ID: {tool_id}"
                            )

                        tool_name = block.get("name")
                        if not tool_name:
                            tool_name = "unknown_tool"
                            logger.warning(
                                "Using default name for missing tool_use name"
                            )

                        tool_input = block.get("input")
                        if isinstance(tool_input, str):
                            # Parse JSON string input
                            try:
                                tool_input = json.loads(tool_input)
                                logger.debug(f"Parsed JSON input: {tool_input}")
                            except json.JSONDecodeError as e:
                                logger.warning(
                                    f"Failed to parse JSON input '{tool_input}': {e}, using empty dict"
                                )
                                tool_input = {}
                        elif not isinstance(tool_input, dict):
                            logger.warning(
                                f"Invalid input type {type(tool_input)}: {tool_input}, using empty dict"
                            )
                            tool_input = {}

                        logger.debug(
                            f"Creating ToolCall from content with id={tool_id}, name={tool_name}, input={tool_input}"
                        )
                        tool_call = ToolCall(
                            id=tool_id,
                            name=tool_name,
                            arguments=tool_input,
                            result=None,  # Will be filled when tool result is available
                        )
                        self.add_tool_call(tool_call)
                else:
                    logger.warning(
                        f"Expected dict but got {type(block)} for content block {i}: {block}"
                    )

        # Handle LangChain tool calls
        if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
            logger.info(f"Processing {len(ai_message.tool_calls)} tool calls")
            for i, tool_call in enumerate(ai_message.tool_calls):
                try:
                    logger.debug(
                        f"Tool call {i}: {tool_call} (type: {type(tool_call)})"
                    )

                    if isinstance(tool_call, dict):
                        # Ensure we have valid values for required fields
                        tool_id = tool_call.get("id")
                        if not tool_id:
                            tool_id = str(uuid.uuid4())
                            logger.warning(
                                f"Generated UUID for missing tool ID: {tool_id}"
                            )

                        tool_name = tool_call.get("name")
                        if not tool_name:
                            tool_name = "unknown_tool"
                            logger.warning("Using default name for missing tool name")

                        tool_args = tool_call.get("args")
                        logger.debug(
                            f"Extracted tool_args: {tool_args} (type: {type(tool_args)})"
                        )
                        if not isinstance(tool_args, dict):
                            logger.warning(
                                f"Invalid args type {type(tool_args)}: {tool_args}, using empty dict"
                            )
                            tool_args = {}

                        logger.debug(
                            f"Creating ToolCall with id={tool_id}, name={tool_name}, args={tool_args}"
                        )
                        logger.debug(
                            f"ToolCall args type: {type(tool_args)}, value: {tool_args}"
                        )
                        tc = ToolCall(
                            id=tool_id,
                            name=tool_name,
                            arguments=tool_args,
                            result=None,
                        )
                        self.add_tool_call(tc)
                    else:
                        # Handle non-dict tool calls (e.g., LangChain ToolCall objects)
                        tool_id = getattr(tool_call, "id", None) or str(uuid.uuid4())
                        tool_name = getattr(tool_call, "name", "unknown_tool")
                        tool_args = getattr(tool_call, "args", {})
                        logger.debug(
                            f"Extracted object tool_args: {tool_args} (type: {type(tool_args)})"
                        )

                        if not isinstance(tool_args, dict):
                            logger.warning(
                                f"Invalid args type {type(tool_args)}: {tool_args}, using empty dict"
                            )
                            tool_args = {}

                        logger.debug(
                            f"Creating ToolCall from object with id={tool_id}, name={tool_name}, args={tool_args}"
                        )
                        logger.debug(
                            f"ToolCall object args type: {type(tool_args)}, value: {tool_args}"
                        )
                        tc = ToolCall(
                            id=tool_id,
                            name=tool_name,
                            arguments=tool_args,
                            result=None,
                        )
                        self.add_tool_call(tc)
                except Exception as e:
                    logger.error(f"Error processing tool call {i}: {e}")
                    logger.error(f"Tool call data: {tool_call}")
                    logger.error(f"Tool call type: {type(tool_call)}")
                    if hasattr(tool_call, "__dict__"):
                        logger.error(f"Tool call attributes: {tool_call.__dict__}")
                    # Create a fallback tool call
                    tc = ToolCall(
                        id=str(uuid.uuid4()),
                        name="error_tool",
                        arguments={"error": str(e), "original_data": str(tool_call)},
                        result=None,
                    )
                    self.add_tool_call(tc)

        # Add message metadata
        if hasattr(ai_message, "response_metadata") and ai_message.response_metadata:
            self.add_metadata("response_metadata", ai_message.response_metadata)

    def process_tool_message(self, tool_message: ToolMessage) -> None:
        """
        Process a tool result message and update the corresponding tool call.

        Args:
            tool_message: The ToolMessage containing the result
        """
        tool_call_id = getattr(tool_message, "tool_call_id", None)
        content = tool_message.content

        # Convert content to string if it's not already
        content_str = ""
        if isinstance(content, str):
            content_str = content
        elif isinstance(content, list):
            # Join list elements into a string
            content_str = " ".join(str(item) for item in content)
        else:
            content_str = str(content)

        # Find the matching tool call and update its result
        for tool_call in self.tool_calls:
            if tool_call.id == tool_call_id:
                tool_call.result = content_str
                logger.info(f"Updated tool call {tool_call_id} with result")
                break
        else:
            # If no matching tool call found, create a new one
            logger.warning(f"No matching tool call found for result {tool_call_id}")
            # Ensure we have a valid tool_call_id
            if not tool_call_id:
                tool_call_id = str(uuid.uuid4())
                logger.warning(f"Generated new tool call ID: {tool_call_id}")

            self.add_tool_call(
                ToolCall(
                    id=tool_call_id,
                    name="unknown_tool",
                    arguments={},
                    result=content_str,
                )
            )

    def build(self) -> Message:
        """
        Build the complete Message object.

        Returns:
            Message: The constructed message with rich content
        """
        # Combine all text parts
        full_text = " ".join(self.text_parts).strip()

        # Create rich content
        rich_content = MessageContent(
            text=full_text,
            tool_calls=self.tool_calls,
            agent_name=self.agent_name,
            metadata=self.metadata,
        )

        # Create the message
        message = Message(
            ThreadId=self.thread_id,
            MessageId=str(uuid.uuid4()),
            Sent=datetime.now(timezone.utc).isoformat(),
            Content=full_text,  # Backward compatibility
            Type=MessageType.agent,
            RichContent=rich_content,
        )

        return message

    def has_content(self) -> bool:
        """Check if the builder has any content to build."""
        return bool(self.text_parts or self.tool_calls)

    def clear(self) -> None:
        """Clear all content from the builder."""
        self.text_parts.clear()
        self.tool_calls.clear()
        self.agent_name = None
        self.metadata.clear()


def create_user_message(thread_id: str, content: str) -> Message:
    """
    Create a simple user message.

    Args:
        thread_id: The thread ID
        content: The user's message content

    Returns:
        Message: The constructed user message
    """
    return Message(
        ThreadId=thread_id,
        MessageId=str(uuid.uuid4()),
        Sent=datetime.now(timezone.utc).isoformat(),
        Content=content,
        Type=MessageType.user,
        RichContent=MessageContent(
            text=content, tool_calls=[], agent_name=None, metadata={}
        ),
    )
