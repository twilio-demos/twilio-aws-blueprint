import json
from typing import List

from fastapi import WebSocket

from src.ai.agent.core.agent_runner_factory import AgentRunnerFactory
from src.services.sessionservice import instance as session_service
from src.services.threadservice import instance as thread_service
from src.types.conversationrelay import (
    DTMFMessage,
    EndSessionMessage,
    ErrorMessage,
    InterruptMessage,
    OutgoingMessage,
    PromptMessage,
    SetupMessage,
    SwitchLanguageMessage,
    TextTokenMessage,
)
from src.types.models import MessageType
from src.utils.env import IDLE_REMINDER, WELCOME_GREETING
from src.utils.logger import get_logger

from .dtmfbuffer import DtmfBuffer
from .idleminder import IdleMinder

logger = get_logger(__name__)


class ConversationRelayHandler:
    """Handles ConversationRelay WebSocket messages"""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.call_sid: str | None = None
        self.session_id: str | None = None
        self.thread_id: str | None = None
        self.session_service = session_service
        self.thread_service = thread_service
        self.dtmf_buffer = DtmfBuffer()
        self.idle_minder = IdleMinder(self.handle_idle)
        self.agent_runner = AgentRunnerFactory.create_runner("langgraph")

    async def handle_idle(self, reached_max_attempts: bool):
        if reached_max_attempts:
            # Send end message with handoff data.
            response = EndSessionMessage(type="end", handoffData='{"result":"idle"}')
            await self.send_message(response)
            return

        # TODO: LLM probably needs to know about this.
        response = TextTokenMessage(type="text", token=IDLE_REMINDER, last=True)
        await self.send_message(response)
        self.idle_minder.handle_activity(True, IDLE_REMINDER)
        if self.thread_id is not None:
            self.thread_service.append(
                self.thread_id, IDLE_REMINDER, MessageType.system
            )

    async def handle_setup_message(self, message: SetupMessage):
        """Handle setup message from Twilio"""
        self.session_id = message.sessionId
        self.call_sid = message.callSid
        self.dtmf_buffer.session_id = self.session_id
        self.dtmf_buffer.call_sid = self.call_sid
        self.idle_minder.session_id = self.session_id
        self.idle_minder.call_sid = self.call_sid

        logger.info(
            "ConversationRelay session setup",
            {
                "sessionId": message.sessionId,
                "callSid": message.callSid,
                "from": message.from_,
                "to": message.to,
                "direction": message.direction,
                "callType": message.callType,
            },
        )

        new_session = True
        hints = None
        language = None
        greeting = WELCOME_GREETING
        if message.customParameters is not None:
            # Persist custom settings to the session
            hints = message.customParameters.get("initial_hints", hints)
            language = message.customParameters.get("initial_language", language)
            greeting = message.customParameters.get("initial_greeting", greeting)

        if (
            message.customParameters is not None
            and "resume_session_id" in message.customParameters
            and "resume_call_sid" in message.customParameters
        ):
            old_session = self.session_service.get(
                message.customParameters["resume_call_sid"],
                message.customParameters["resume_session_id"],
            )
            if (
                old_session is not None
                and old_session.CallSid == message.customParameters["resume_call_sid"]
            ):
                new_session = False
                resume_error = (
                    message.customParameters.get("resume_error", "false") == "true"
                )
                logger.info(
                    "Restoring previous session",
                    {
                        "callSid": self.call_sid,
                        "oldSession": old_session.SessionId,
                        "newSession": self.session_id,
                        "hadError": resume_error,
                    },
                )
                self.session_service.restore(
                    self.call_sid,
                    self.session_id,
                    hints,
                    language,
                    old_session,
                    resume_error,
                )
                self.thread_service.get(old_session.ThreadId)
                self.thread_id = old_session.ThreadId

        if new_session:
            session = self.session_service.create(
                self.call_sid, self.session_id, hints, language
            )
            self.thread_id = session.ThreadId
            self.idle_minder.handle_activity(False, greeting)
            if self.thread_id is not None:
                self.thread_service.append(self.thread_id, greeting, MessageType.system)

        # TODO: Initialize AI agent session
        # TODO: Send welcome message if needed

    async def handle_prompt_message(self, message: PromptMessage):
        """Handle voice prompt from caller"""
        logger.info(
            "Received voice prompt",
            {
                "sessionId": self.session_id,
                "voicePrompt": message.voicePrompt,
                "lang": message.lang,
                "last": message.last,
            },
        )

        self.idle_minder.handle_activity()
        if self.thread_id is not None:
            self.thread_service.append(
                self.thread_id, message.voicePrompt, MessageType.user
            )

        async for chunk in self.agent_runner.stream_request(
            message.voicePrompt, self.thread_id
        ):
            logger.debug("Stream chunk:", {"chunk": chunk})
            if chunk["type"] == "content":
                response = TextTokenMessage(
                    type="text", token=str(chunk["data"]), last=False
                )
                logger.info("Sending text token to Twilio", {"text": response})
                await self.send_message(response)
                self.idle_minder.handle_activity(False, str(chunk["data"]))

    async def handle_dtmf_message(self, message: DTMFMessage):
        """Handle DTMF digit from caller"""
        logger.info(
            "Received DTMF digit",
            {"sessionId": self.session_id, "digit": message.digit},
        )

        async def handle_dtmf_flush(digits: str):
            if self.thread_id is not None:
                self.thread_service.append(self.thread_id, digits, MessageType.user)
            # TODO: Process with AI agent
            # Example response - replace with AI processing
            response = TextTokenMessage(
                type="text",
                token="Digits received: " + " ".join(list(digits)),
                last=True,
            )
            await self.send_message(response)
            if self.thread_id is not None:
                self.thread_service.append(
                    self.thread_id, response.token, MessageType.agent
                )

        await self.dtmf_buffer.handle_input(message.digit, handle_dtmf_flush)

        self.idle_minder.handle_activity()

    async def handle_interrupt_message(self, message: InterruptMessage):
        """Handle caller interruption"""
        logger.info(
            "Caller interrupted",
            {
                "sessionId": self.session_id,
                "utteranceUntilInterrupt": message.utteranceUntilInterrupt,
                "durationMs": message.durationUntilInterruptMs,
            },
        )

        self.idle_minder.handle_activity()

        # TODO: Stop current AI processing
        # TODO: Handle interruption gracefully

    async def handle_error_message(self, message: ErrorMessage):
        """Handle error from Twilio"""
        logger.error(
            "Twilio ConversationRelay error",
            {"sessionId": self.session_id, "description": message.description},
        )

        # TODO: Handle error appropriately
        # TODO: Maybe send fallback response

    async def update_hints(self, hints: List[str], prompt: str):
        newResponse = EndSessionMessage(
            type="end",
            handoffData=json.dumps(
                {
                    "result": "hint",
                    "message": prompt,
                    "hints": ",".join(hints) if len(hints) > 0 else "",
                }
            ),
        )
        await self.send_message(newResponse)

    async def update_language(self, language: str):
        newResponse = SwitchLanguageMessage(
            type="language", ttsLanguage=language, transcriptionLanguage=language
        )
        await self.send_message(newResponse)
        if self.call_sid is not None and self.session_id is not None:
            session_service.update_language(self.call_sid, self.session_id, language)

    async def send_message(self, message: OutgoingMessage):
        """Send message to Twilio"""
        message_json = message.model_dump_json()
        await self.websocket.send_text(message_json)

        logger.debug(
            "Sent message to Twilio",
            {
                "sessionId": self.session_id,
                "messageType": message.type,
                "message": message_json,
            },
        )

    def process_disconnect(self):
        self.dtmf_buffer.clear()
        self.idle_minder.clear()

    async def process_message(self, raw_message: str):
        """Process incoming message from Twilio"""
        try:
            message_data = json.loads(raw_message)
            message_type = message_data.get("type")

            if message_type == "setup":
                message = SetupMessage(**message_data)
                await self.handle_setup_message(message)
            elif message_type == "prompt":
                message = PromptMessage(**message_data)
                await self.handle_prompt_message(message)
            elif message_type == "dtmf":
                message = DTMFMessage(**message_data)
                await self.handle_dtmf_message(message)
            elif message_type == "interrupt":
                message = InterruptMessage(**message_data)
                await self.handle_interrupt_message(message)
            elif message_type == "error":
                message = ErrorMessage(**message_data)
                await self.handle_error_message(message)
            else:
                logger.warning(
                    "Unknown message type received",
                    {
                        "sessionId": self.session_id,
                        "messageType": message_type,
                        "rawMessage": raw_message,
                    },
                )

        except Exception as e:
            logger.error(
                "Error processing message",
                {
                    "sessionId": self.session_id,
                    "error": str(e),
                    "rawMessage": raw_message,
                },
            )
