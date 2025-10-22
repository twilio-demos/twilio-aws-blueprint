from enum import Enum
from typing import Literal, Optional, TypedDict

from pydantic import BaseModel, field_validator

from src.utils.env import (
    DTMF_MAX_DIGITS,
    DTMF_TIMEOUT,
    IDLE_MAX_ATTEMPTS,
    IDLE_TIMEOUT,
    LANGUAGE,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CallRequest(BaseModel):
    call_sid: str
    from_number: str
    to_number: str
    status: str


class ActionResponse(BaseModel):
    result: str


class SessionDTMFConfig(BaseModel):
    MaxDigits: int = DTMF_MAX_DIGITS
    Timeout: int = DTMF_TIMEOUT


class SessionIdleConfig(BaseModel):
    MaxAttempts: int = IDLE_MAX_ATTEMPTS
    Timeout: int = IDLE_TIMEOUT


class SessionConfig(BaseModel):
    DTMF: SessionDTMFConfig = SessionDTMFConfig()
    Idle: SessionIdleConfig = SessionIdleConfig()
    Hints: str = ""
    Lang: str = LANGUAGE


class Session(BaseModel):
    CallSid: str
    SessionId: str
    ThreadId: str
    SessionStatus: str = "in-progress"
    Created: str
    Config: SessionConfig = SessionConfig()
    SessionState: dict[str, str | int | bool] = {}


class MessageType(str, Enum):
    user = "user"
    agent = "agent"
    system = "system"


class ToolCall(BaseModel):
    """Represents a tool call made by the agent."""

    id: str
    name: str
    arguments: dict
    result: str | None = None

    # Allow field assignment after creation
    model_config = {"frozen": False}

    @field_validator("arguments", mode="before")
    @classmethod
    def validate_arguments(cls, v):
        """Ensure arguments is always a dictionary."""
        if not isinstance(v, dict):
            # Log the invalid value for debugging
            logger.warning(f"ToolCall arguments should be a dict, got {type(v)}: {v}")
            # Convert non-dict values to empty dict to prevent validation errors
            return {}
        return v


class MessageContent(BaseModel):
    """Rich message content that can include text, tool calls, and metadata."""

    text: str = ""
    tool_calls: list[ToolCall] = []
    agent_name: str | None = None  # Which specialist agent generated this
    metadata: dict = {}


class Message(BaseModel):
    ThreadId: str
    MessageId: str
    Sent: str
    Content: str  # Keep for backward compatibility
    Type: MessageType

    # New rich content fields
    RichContent: MessageContent | None = None


class StreamChunk(TypedDict):
    type: Literal["content", "agent", "metadata"]
    data: str | dict


class LanguagePrompts(BaseModel):
    welcome_greeting: str = "Hello! This is the default greeting."
    welcome_error: str = "Hello! This is the default error greeting."
    error: str = "This is the default error prompt."
    idle: str = "This is the default idle prompt."
    idle_timeout: str = "This is the default timeout prompt."


class LanguageSettings(BaseModel):
    initial_hints: Optional[str] = None
    transcription_provider: str = "Deepgram"
    speech_model: str = "nova-3-general"
    tts_provider: str = "ElevenLabs"
    tts_voice: str = "lxYfHSkYm1EzQzGhdbfc"
    fallback_tts: str = "Google.en-US-Chirp3-HD-Aoede"


class Language(BaseModel):
    prompts: LanguagePrompts = LanguagePrompts()
    settings: LanguageSettings = LanguageSettings()
