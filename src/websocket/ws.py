from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from twilio.request_validator import RequestValidator
from src.types.conversationrelay import IncomingMessage, OutgoingMessage, TextTokenMessage, SetupMessage, PromptMessage, DTMFMessage, InterruptMessage, ErrorMessage
from src.utils.env import TWILIO_AUTH_TOKEN
from src.utils.logger import get_logger
import json
from typing import Dict, Any, Optional

router = APIRouter()
logger = get_logger(__name__)

# Initialize Twilio request validator
validator = RequestValidator(TWILIO_AUTH_TOKEN)

class ConversationRelayHandler:
    """Handles ConversationRelay WebSocket messages"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id: str = None
        self.call_sid: str = None
    
    async def handle_setup_message(self, message: SetupMessage):
        """Handle setup message from Twilio"""
        self.session_id = message.sessionId
        self.call_sid = message.callSid
        
        logger.info("ConversationRelay session setup", {
            "sessionId": message.sessionId,
            "callSid": message.callSid,
            "from": message.from_,
            "to": message.to,
            "direction": message.direction,
            "callType": message.callType
        })
        
        # TODO: Initialize AI agent session
        # TODO: Send welcome message if needed
    
    async def handle_prompt_message(self, message: PromptMessage):
        """Handle voice prompt from caller"""
        logger.info("Received voice prompt", {
            "sessionId": self.session_id,
            "voicePrompt": message.voicePrompt,
            "lang": message.lang,
            "last": message.last
        })
        
        # TODO: Process with AI agent
        # TODO: Generate response
        
        # Example response - replace with AI processing
        response = TextTokenMessage(
            type="text",
            token="I heard you say: " + message.voicePrompt,
            last=True
        )
        await self.send_message(response)
    
    async def handle_dtmf_message(self, message: DTMFMessage):
        """Handle DTMF digit from caller"""
        logger.info("Received DTMF digit", {
            "sessionId": self.session_id,
            "digit": message.digit
        })
        
        # TODO: Process DTMF input
        # Example: menu navigation, confirmation, etc.
    
    async def handle_interrupt_message(self, message: InterruptMessage):
        """Handle caller interruption"""
        logger.info("Caller interrupted", {
            "sessionId": self.session_id,
            "utteranceUntilInterrupt": message.utteranceUntilInterrupt,
            "durationMs": message.durationUntilInterruptMs
        })
        
        # TODO: Stop current AI processing
        # TODO: Handle interruption gracefully
    
    async def handle_error_message(self, message: ErrorMessage):
        """Handle error from Twilio"""
        logger.error("Twilio ConversationRelay error", {
            "sessionId": self.session_id,
            "description": message.description
        })
        
        # TODO: Handle error appropriately
        # TODO: Maybe send fallback response
    
    async def send_message(self, message: OutgoingMessage):
        """Send message to Twilio"""
        message_json = message.model_dump_json()
        await self.websocket.send_text(message_json)
        
        logger.debug("Sent message to Twilio", {
            "sessionId": self.session_id,
            "messageType": message.type,
            "message": message_json
        })
    
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
                logger.warning("Unknown message type received", {
                    "sessionId": self.session_id,
                    "messageType": message_type,
                    "rawMessage": raw_message
                })
                
        except Exception as e:
            logger.error("Error processing message", {
                "sessionId": self.session_id,
                "error": str(e),
                "rawMessage": raw_message
            })

@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    try:
        # For WebSocket connections, Twilio sends the signature in headers during the HTTP upgrade
        # Extract signature from headers
        headers = dict(websocket.headers)
        x_twilio_signature = headers.get("x-twilio-signature")
        
        if x_twilio_signature:
            # Validate signature using WebSocket URL and headers
            url = str(websocket.url)
            if not validator.validate(url, {}, x_twilio_signature):
                logger.warning("WebSocket Twilio signature validation failed", {
                    "url": url,
                    "hasSignature": bool(x_twilio_signature),
                })
                await websocket.close(code=1008, reason="Invalid Twilio signature")
                return
            else:
                logger.info("WebSocket Twilio signature validated successfully")
        else:
            logger.warning("No Twilio signature provided for WebSocket connection", {
                "url": str(websocket.url),
                "headers": headers
            })

            await websocket.close(code=1008, reason="Missing Twilio signature")
            return
    
        await websocket.accept()
        handler = ConversationRelayHandler(websocket)
        
        logger.info("WebSocket connection established", {
            "url": str(websocket.url),
            "validated": bool(x_twilio_signature)
        })
        
        try:
            while True:
                data = await websocket.receive_text()
                await handler.process_message(data)
                
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected", {
                "sessionId": handler.session_id,
                "callSid": handler.call_sid
            })
        except Exception as e:
            logger.error("WebSocket error", {
                "sessionId": handler.session_id,
                "error": str(e)
            })
            await websocket.close()
            
    except Exception as e:
        logger.error("WebSocket connection error", {
            "error": str(e),
            "url": str(websocket.url)
        })
        try:
            await websocket.close(code=1011, reason="Server error")
        except:
            pass
