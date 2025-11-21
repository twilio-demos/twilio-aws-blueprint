import json
from typing import Any, List

from fastapi import WebSocket
from typing_extensions import Tuple

from src.ai.agent.core.agent_runner_factory import AgentRunnerFactory
from src.services.sessionservice import instance as session_service
from src.services.threadservice import instance as thread_service
from src.types.conversationrelay import (
    DTMFMessage,
    EndSessionMessage,
    ErrorMessage,
    InfoMessage,
    InterruptMessage,
    OutgoingMessage,
    PromptMessage,
    SetupMessage,
    SwitchLanguageMessage,
    TextTokenMessage,
)
from src.types.models import MessageType, Session
from src.utils.language import load_language
from src.utils.logger import get_logger

from .dtmfbuffer import DtmfBuffer
from .idleminder import IdleMinder

logger = get_logger(__name__)


class ConversationRelayHandler:
    """Handles ConversationRelay WebSocket messages"""

    def __init__(self, websocket: WebSocket, message: SetupMessage):
        self.websocket = websocket
        self.session_service = session_service
        self.thread_service = thread_service
        self.agent_runner = AgentRunnerFactory.create_runner("langgraph")
        (self.session, is_resume) = self.setup_session(message)
        self.dtmf_buffer = DtmfBuffer(self.session)
        self.idle_minder = IdleMinder(self.session, self.handle_idle)

        if is_resume:
            # When resuming a session, there is no agent greeting, so treat it as idle
            self.idle_minder.handle_idle()

    async def handle_idle(self, reached_max_attempts: bool):
        if reached_max_attempts:
            # Send end message with handoff data.
            response = EndSessionMessage(type="end", handoffData='{"result":"idle"}')
            await self.send_message(response)
            return

        prompt = load_language(self.session.Config.Lang).prompts.idle

        response = TextTokenMessage(type="text", token=prompt, last=True)
        await self.send_message(response)
        self.thread_service.append(self.session, prompt, MessageType.system)

    def setup_session(self, message: SetupMessage) -> Tuple[Session, bool]:
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
        hints = None
        language = None
        greeting = ""
        is_resume = False
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
            is_resume = True
            old_session = self.session_service.get(
                message.customParameters["resume_call_sid"],
                message.customParameters["resume_session_id"],
            )
            if (
                old_session is not None
                and old_session.CallSid == message.customParameters["resume_call_sid"]
            ):
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
                return (
                    self.session_service.restore(
                        session_id,
                        hints,
                        language,
                        old_session,
                        resume_error,
                    ),
                    is_resume,
                )

        session = self.session_service.create(call_sid, session_id, hints, language)
        self.thread_service.append(session, greeting, MessageType.system)
        return (session, is_resume)

    async def handle_input(self, prompt: str) -> str:
        full_response = ""
        async for chunk in self.agent_runner.stream_request(
            prompt, self.session.ThreadId
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

        if len(full_response) < 1:
            # Resume idle detection automatically if the LLM didn't speak a response
            self.idle_minder.handle_idle()

        return full_response

    async def handle_prompt_message(self, message: PromptMessage):
        """Handle voice prompt from caller"""
        logger.info(
            "Received voice prompt",
            {
                "sessionId": self.session.SessionId,
                "voicePrompt": message.voicePrompt,
                "lang": message.lang,
                "last": message.last,
            },
        )

        self.thread_service.append(self.session, message.voicePrompt, MessageType.user)

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

        # Send input to the agent
        await self.handle_input(message.voicePrompt)

    async def handle_dtmf_message(self, message: DTMFMessage):
        """Handle DTMF digit from caller"""
        logger.info(
            "Received DTMF digit",
            {
                "sessionId": self.session.SessionId,
                "digit": message.digit,
            },
        )

        async def handle_dtmf_flush(digits: str):
            self.thread_service.append(self.session, digits, MessageType.user)
            # Send input to the agent
            await self.handle_input(digits)

        await self.dtmf_buffer.handle_input(message.digit, handle_dtmf_flush)

    async def handle_interrupt_message(self, message: InterruptMessage):
        """Handle caller interruption"""
        logger.info(
            "Caller interrupted",
            {
                "sessionId": self.session.SessionId,
                "utteranceUntilInterrupt": message.utteranceUntilInterrupt,
                "durationMs": message.durationUntilInterruptMs,
            },
        )

        # TODO: Stop current AI processing
        # TODO: Handle interruption gracefully

    async def handle_info_message(self, message: InfoMessage):
        """Handle debug messages from Twilio"""
        logger.debug(
            "Received info message",
            {
                "sessionId": self.session.SessionId,
                "name": message.name,
                "value": message.value,
            },
        )

        if message.name == "clientSpeaking" and message.value == "on":
            self.idle_minder.handle_activity()

        if message.name == "agentSpeaking" and message.value == "off":
            self.idle_minder.handle_idle()
        else:
            self.idle_minder.clear()

    async def handle_error_message(self, message: ErrorMessage):
        """Handle error from Twilio"""
        logger.error(
            "Twilio ConversationRelay error",
            {
                "sessionId": self.session.SessionId,
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
        session_service.update_language(self.session, language)

    async def send_message(self, message: OutgoingMessage):
        """Send message to Twilio"""
        message_json = message.model_dump_json()
        await self.websocket.send_text(message_json)

        logger.debug(
            "Sent message to Twilio",
            {
                "sessionId": self.session.SessionId,
                "messageType": message.type,
                "message": message_json,
            },
        )

    def process_disconnect(self):
        self.dtmf_buffer.clear()
        self.idle_minder.clear()

    async def process_message(self, message_type: str, message_data: Any):
        """Process incoming message from Twilio"""
        try:
            if message_type == "prompt":
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
            elif message_type == "info":
                message = InfoMessage(**message_data)
                await self.handle_info_message(message)
            else:
                logger.warning(
                    "Unknown message type received",
                    {
                        "sessionId": self.session.SessionId,
                        "messageType": message_type,
                        "messageData": message_data,
                    },
                )

        except Exception as e:
            logger.error(
                "Error processing message",
                {
                    "sessionId": self.session.SessionId,
                    "error": str(e),
                    "messageData": message_data,
                },
            )
