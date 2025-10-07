from enum import Enum

from pydantic import BaseModel

from src.utils.env import (
    DTMF_MAX_DIGITS,
    DTMF_TIMEOUT,
    IDLE_MAX_ATTEMPTS,
    IDLE_TIMEOUT,
    INITIAL_HINTS,
    TTS_LANGUAGE,
)


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
    Hints: str = INITIAL_HINTS
    Language: str = TTS_LANGUAGE


class Session(BaseModel):
    CallSid: str
    SessionId: str
    ThreadId: str
    SessionStatus: str = "in-progress"
    Created: str
    Config: SessionConfig = SessionConfig()
    SessionState: dict[str, str | int | bool] | None = None


class MessageType(str, Enum):
    user = "user"
    agent = "agent"
    system = "system"


class Message(BaseModel):
    ThreadId: str
    MessageId: str
    Sent: str
    Content: str
    Type: MessageType
