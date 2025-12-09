"""
Agent Message Builder for constructing rich messages with tool calls.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

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
        self._streaming_blocks = {}

    def process_ai_message(
        self, ai_message: AIMessage, sender: str | None = None
    ) -> None:
        """
        Process a LangChain AIMessage and extract all relevant information.
        Handles streaming where blocks arrive in chunks.
        """
        if sender:
            self.set_agent_name(sender)

        # Handle different content types
        if isinstance(ai_message.content, str):
            self.add_text(ai_message.content)
        elif isinstance(ai_message.content, list):
            for block in ai_message.content:
                logger.debug(f"Processing content block: {block} (type: {type(block)})")
                try:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            self._process_text_block(block)
                        elif block.get("type") == "tool_use":
                            self._process_tool_use_block(block)
                        else:
                            logger.warning(
                                f"Unknown block type: {block.get('type')} in block: {block}"
                            )
                    else:
                        logger.warning(
                            f"Expected dict block but got {type(block)}: {block}"
                        )
                except Exception as e:
                    logger.error(f"Error processing block {block}: {e}")
                    # Continue processing other blocks

    def process_persisted_message(self, message: Message) -> None:
        if message.RichContent is None:
            self.text_parts = [message.Content]
            return

        self.text_parts = [message.RichContent.text]
        self.tool_calls = message.RichContent.tool_calls
        self.agent_name = message.RichContent.agent_name
        self.metadata = message.RichContent.metadata

    def _process_text_block(self, block: dict) -> None:
        """Process a text block (may be streaming)."""
        try:
            index = block.get("index")
            text = block.get("text", "")

            logger.debug(
                f"Processing text block - index: {index}, text: '{text}', block: {block}"
            )

            if not text:
                return

            if index is not None:
                # Streaming text - accumulate by index
                if index not in self._streaming_blocks:
                    self._streaming_blocks[index] = {
                        "type": "text",
                        "content": "",
                        "is_finalized": False,
                    }

                # Safely access and update content
                current_block = self._streaming_blocks[index]
                if "content" in current_block:
                    current_block["content"] += text
                else:
                    # Initialize content if it doesn't exist (shouldn't happen but be safe)
                    logger.warning(
                        f"Content key missing for streaming block {index}, initializing"
                    )
                    current_block["content"] = text
            else:
                # Non-streaming text - add directly
                self.add_text(text)

        except Exception as e:
            logger.error(f"Error in _process_text_block with block {block}: {e}")
            # Fallback: try to add text directly if possible
            text = block.get("text", "")
            if text:
                self.add_text(text)

    def _process_tool_use_block(self, block: dict) -> None:
        """
        Process a tool_use block, accumulating data across streaming chunks.
        """
        index = block.get("index")
        if index is None:
            logger.warning(f"tool_use block missing index: {block}")
            return

        # Get or create the accumulator for this tool call
        if index not in self._streaming_blocks:
            self._streaming_blocks[index] = {
                "type": "tool_use",
                "id": None,
                "name": None,
                "input": "",  # Accumulate as string
                "is_finalized": False,
            }

        tool_data = self._streaming_blocks[index]

        # Accumulate data from this chunk
        if block.get("id") is not None:
            tool_data["id"] = block["id"]

        if block.get("name") is not None:
            tool_data["name"] = block["name"]

        if "input" in block:
            input_chunk = block["input"]
            if input_chunk:  # Only append non-empty chunks
                tool_data["input"] += input_chunk

    def finalize_streaming_blocks(self) -> None:
        """
        Finalize all accumulated streaming blocks.
        Call this when you receive an empty content array [] or at end of stream.
        """
        for index, block_data in self._streaming_blocks.items():
            if block_data["is_finalized"]:
                continue

            block_type = block_data["type"]

            if block_type == "text":
                # Finalize accumulated text
                if block_data["content"]:
                    self.add_text(block_data["content"])
                    logger.debug(
                        f"Finalized text block {index}: {len(block_data['content'])} chars"
                    )

            elif block_type == "tool_use":
                # Finalize accumulated tool call
                self._finalize_tool_call(index, block_data)

            block_data["is_finalized"] = True

    def _finalize_tool_call(self, index: int, tool_data: dict) -> None:
        """Finalize and add a complete tool call."""
        tool_id = tool_data["id"]
        tool_name = tool_data["name"]
        tool_input_str = tool_data["input"]

        # Validate required fields - skip if missing critical data
        if not tool_id:
            logger.error(f"Cannot finalize tool call at index {index}: missing tool ID")
            return

        if not tool_name:
            logger.error(
                f"Cannot finalize tool call at index {index}: missing tool name"
            )
            return

        # Parse the accumulated input
        tool_input = {}
        if tool_input_str:
            try:
                tool_input = json.loads(tool_input_str)
                logger.debug(f"Parsed complete JSON input: {tool_input}")
            except json.JSONDecodeError as e:
                logger.error(
                    f"Cannot finalize tool call at index {index}: invalid JSON input '{tool_input_str}': {e}"
                )
                return

        logger.debug(
            f"Finalizing tool call {index}: id={tool_id}, name={tool_name}, input={tool_input}"
        )

        tool_call = ToolCall(
            id=tool_id,
            name=tool_name,
            arguments=tool_input,
            result=None,
        )

        self.add_tool_call(tool_call)

    def clear_streaming_state(self) -> None:
        """Clear streaming state after processing is complete."""
        self._streaming_blocks.clear()

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

    def _build_ai_message(self) -> AIMessage:
        content = []
        index = 0

        for text_block in self.text_parts:
            content.append({"type": "text", "text": text_block, "index": index})
            index += 1

        # TODO: For some reason loading these causes errors
        """
        for tool_block in self.tool_calls:
            content.append(
                {
                    "type": "tool_use",
                    "id": tool_block.id,
                    "name": tool_block.name,
                    "input": json.dumps(tool_block.arguments),
                    "index": index,
                }
            )
            index += 1
        """

        return AIMessage(content=content)

    def _build_human_message(self) -> HumanMessage:
        return HumanMessage(
            content=self.text_parts[0] if len(self.text_parts) > 0 else ""
        )

    def build_langchain_message(self) -> BaseMessage:
        return (
            self._build_human_message()
            if self.agent_name is None
            else self._build_ai_message()
        )

    def has_content(self) -> bool:
        """Check if the builder has any content to build."""
        return bool(self.text_parts or self.tool_calls)

    def clear(self) -> None:
        """Clear all content from the builder."""
        self.text_parts.clear()
        self.tool_calls.clear()
        self.agent_name = None
        self.metadata.clear()
