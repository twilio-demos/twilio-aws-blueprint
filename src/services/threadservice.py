import uuid
from datetime import datetime, timezone
from typing import List

from boto3.dynamodb.conditions import Key

from src.types.models import (
    Message,
    MessageType,
)
from src.utils.logger import get_logger

from .dynamodbservice import DynamoDBService

logger = get_logger(__name__)


class ThreadService(DynamoDBService):
    def __init__(self):
        super().__init__("ConversationRelayMessages")
        self.thread_messages: dict[str, List[Message]] = {}

    def append(self, thread_id: str, content: str, type: MessageType) -> Message:
        """Creates a message object, appends the thread in memory, and persists it to DynamoDB."""
        message = Message(
            ThreadId=thread_id,
            MessageId=str(uuid.uuid4()),
            Sent=datetime.now(timezone.utc).isoformat(),
            Content=content,
            Type=type,
        )
        if thread_id not in self.thread_messages:
            self.thread_messages[thread_id] = []
        self.thread_messages[thread_id].append(message)
        super()._add_item(message)
        return message

    def append_rich_message(self, message: Message) -> Message:
        """
        Append a pre-built rich message to the thread.

        Args:
            message: The Message object to append

        Returns:
            Message: The appended message
        """
        thread_id = message.ThreadId
        if thread_id not in self.thread_messages:
            self.thread_messages[thread_id] = []
        self.thread_messages[thread_id].append(message)
        super()._add_item(message)
        return message

    def get(self, thread_id: str) -> List[Message]:
        """Gets a thread from memory if present, otherwise from DynamoDB."""

        # Return locally cached object if present
        if thread_id in self.thread_messages:
            return self.thread_messages[thread_id]

        items = super()._query(Key("ThreadId").eq(thread_id))
        if items is None:
            return []

        # Store in memory for future reference
        self.thread_messages[thread_id] = list(map(lambda m: Message(**m), items))
        return self.thread_messages[thread_id]


instance = ThreadService()
