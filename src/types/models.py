from pydantic import BaseModel

from src.utils.env import DTMF_MAX_DIGITS, DTMF_TIMEOUT, IDLE_MAX_ATTEMPTS, IDLE_TIMEOUT


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


class Session(BaseModel):
    CallSid: str
    SessionId: str
    SessionStatus: str = "in-progress"
    Config: SessionConfig = SessionConfig()
    SessionState: dict[str, str | int | bool] | None = None
