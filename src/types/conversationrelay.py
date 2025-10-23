from enum import Enum
from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field

# Incoming Message Types from Twilio


class CallType(str, Enum):
    PSTN = "PSTN"
    SIP = "SIP"
    CLIENT = "CLIENT"
    PUBLIC_SIP = "PUBLIC_SIP"


class Direction(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallStatus(str, Enum):
    RINGING = "RINGING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SetupMessage(BaseModel):
    type: Literal["setup"]
    sessionId: str
    accountSid: str
    parentCallSid: str
    callSid: str
    from_: str | None = Field(validation_alias="from")  # Field alias for 'from' keyword
    to: str
    forwardedFrom: Optional[str] = None
    callType: CallType
    callerName: Optional[str] = None
    direction: Direction
    callStatus: CallStatus
    customParameters: Optional[Dict[str, Any]] = None


class PromptMessage(BaseModel):
    type: Literal["prompt"]
    voicePrompt: str
    lang: str
    last: bool


class DTMFMessage(BaseModel):
    type: Literal["dtmf"]
    digit: str


class InterruptMessage(BaseModel):
    type: Literal["interrupt"]
    utteranceUntilInterrupt: str
    durationUntilInterruptMs: int


class ErrorMessage(BaseModel):
    type: Literal["error"]
    description: str


# Union type for all incoming messages
IncomingMessage = Union[
    SetupMessage, PromptMessage, DTMFMessage, InterruptMessage, ErrorMessage
]

# Outgoing Message Types to Twilio


class TextTokenMessage(BaseModel):
    type: Literal["text"]
    token: str
    last: Optional[bool] = False
    lang: Optional[str] = None
    interruptible: Optional[bool] = None
    preemptible: Optional[bool] = None


class PlayMediaMessage(BaseModel):
    type: Literal["play"]
    source: str
    loop: Optional[int] = 1
    preemptible: Optional[bool] = False
    interruptible: Optional[bool] = True


class SendDigitsMessage(BaseModel):
    type: Literal["sendDigits"]
    digits: str


class SwitchLanguageMessage(BaseModel):
    type: Literal["language"]
    ttsLanguage: Optional[str] = None
    transcriptionLanguage: Optional[str] = None


class EndSessionMessage(BaseModel):
    type: Literal["end"]
    handoffData: Optional[str] = None


# Union type for all outgoing messages
OutgoingMessage = Union[
    TextTokenMessage,
    PlayMediaMessage,
    SendDigitsMessage,
    SwitchLanguageMessage,
    EndSessionMessage,
]
