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
from src.types.models import MessageType, Session
from src.utils.env import IDLE_REMINDER, WELCOME_GREETING
from src.utils.logger import get_logger

from .dtmfbuffer import DtmfBuffer
from .idleminder import IdleMinder

logger = get_logger(__name__)


class ConversationRelayHandler:
    """Handles ConversationRelay WebSocket messages"""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session: Session | None = None
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
        if self.session is not None:
            self.thread_service.append(self.session, IDLE_REMINDER, MessageType.system)

    async def handle_setup_message(self, message: SetupMessage):
        """Handle setup message from Twilio"""
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

        session_id = message.sessionId
        call_sid = message.callSid
        new_session = True
        resume_error = False
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
                        "callSid": call_sid,
                        "oldSession": old_session.SessionId,
                        "newSession": session_id,
                        "hadError": resume_error,
                    },
                )
                self.session = self.session_service.restore(
                    session_id,
                    hints,
                    language,
                    old_session,
                    resume_error,
                )

        if new_session:
            self.session = self.session_service.create(
                call_sid, session_id, hints, language
            )

        if self.session is not None:
            self.dtmf_buffer.session = self.session
            self.idle_minder.session = self.session
            if new_session:
                self.idle_minder.handle_activity(False, greeting)
                self.thread_service.append(self.session, greeting, MessageType.system)
            elif resume_error:
                self.idle_minder.handle_activity(False, "")

        # TODO: Initialize AI agent session
        # TODO: Send welcome message if needed

    async def handle_prompt_message(self, message: PromptMessage):
        """Handle voice prompt from caller"""
        logger.info(
            "Received voice prompt",
            {
                "sessionId": self.log_session_id(),
                "voicePrompt": message.voicePrompt,
                "lang": message.lang,
                "last": message.last,
            },
        )

        self.idle_minder.handle_activity()
        if self.session is not None:
            self.thread_service.append(
                self.session, message.voicePrompt, MessageType.user
            )

            # if "spanish" in message.voicePrompt.lower():
            #     await self.update_language("es-US")
            #     return
            # if "brazil" in message.voicePrompt.lower():
            #     await self.update_language("pt-BR")
            #     return
            # # Hints testing
            # if "need a doctor" in message.voicePrompt.lower():
            #     await self.update_hints(
            #         ["Wilkoff", "Bossong", "Rice", "Wigand"], "Which doctor?"
            #     )

            full_response = ""
            async for chunk in self.agent_runner.stream_request(
                message.voicePrompt, self.session.ThreadId
            ):
                logger.debug("Stream chunk:", {"chunk": chunk})
                if chunk["type"] == "content":
                    response_token = str(chunk["data"])
                    response = TextTokenMessage(
                        type="text", token=response_token, last=False
                    )
                    full_response += response_token
                    await self.send_message(response)
                    self.idle_minder.clear()  # Prevent idle detection while LLM is streaming

            # Send last message to indicate end of response
            response = TextTokenMessage(type="text", token="", last=True)
            await self.send_message(response)
            self.idle_minder.handle_activity(False, full_response)

    async def handle_dtmf_message(self, message: DTMFMessage):
        """Handle DTMF digit from caller"""
        logger.info(
            "Received DTMF digit",
            {
                "sessionId": self.log_session_id(),
                "digit": message.digit,
            },
        )

        async def handle_dtmf_flush(digits: str):
            if self.session is not None:
                self.thread_service.append(self.session, digits, MessageType.user)
            # TODO: Process with AI agent
            # Example response - replace with AI processing
            response = TextTokenMessage(
                type="text",
                token="Digits received: " + " ".join(list(digits)),
                last=True,
            )
            await self.send_message(response)
            if self.session is not None:
                self.thread_service.append(
                    self.session, response.token, MessageType.agent
                )

        await self.dtmf_buffer.handle_input(message.digit, handle_dtmf_flush)

        self.idle_minder.handle_activity()

    async def handle_interrupt_message(self, message: InterruptMessage):
        """Handle caller interruption"""
        logger.info(
            "Caller interrupted",
            {
                "sessionId": self.log_session_id(),
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
            {
                "sessionId": self.log_session_id(),
                "description": message.description,
            },
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
        if self.session is not None:
            session_service.update_language(self.session, language)

    async def send_message(self, message: OutgoingMessage):
        """Send message to Twilio"""
        message_json = message.model_dump_json()
        await self.websocket.send_text(message_json)

        logger.debug(
            "Sent message to Twilio",
            {
                "sessionId": self.log_session_id(),
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
                        "sessionId": self.log_session_id(),
                        "messageType": message_type,
                        "rawMessage": raw_message,
                    },
                )

        except Exception as e:
            logger.error(
                "Error processing message",
                {
                    "sessionId": self.log_session_id(),
                    "error": str(e),
                    "rawMessage": raw_message,
                },
            )

    def log_session_id(self) -> str:
        return self.session.SessionId if self.session is not None else "unknown"
