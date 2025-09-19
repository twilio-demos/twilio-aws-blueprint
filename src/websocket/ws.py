from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from twilio.request_validator import RequestValidator
from src.types.conversationrelay import IncomingMessage, OutgoingMessage, TextTokenMessage, SetupMessage, PromptMessage, DTMFMessage, InterruptMessage, ErrorMessage
from src.utils.env import TWILIO_AUTH_TOKEN, TWILIO_ACCOUNT_SID, ENVIRONMENT, EXTERNAL_URL, FORCE_VALIDATION
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

def _construct_validation_urls(websocket: WebSocket, headers: dict) -> list[str]:
    """
    Construct validation URLs for Twilio WebSocket signature validation.
    
    Based on testing, Twilio signs WebSocket upgrade requests using:
    1. wss:// scheme (not https://)
    2. The host header including port if present
    """
    urls = []
    
    # Primary method: Use forwarded headers (ngrok, load balancer case)
    if headers.get("x-forwarded-proto") and headers.get("host"):
        forwarded_proto = headers.get("x-forwarded-proto")
        host_with_port = headers.get("host")
        
        # Convert to WebSocket scheme - this is what Twilio actually signs
        if forwarded_proto == "https":
            ws_scheme = "wss"
        else:
            ws_scheme = "ws"
            
        # Primary URL with port (most likely to work)
        primary_url = f"{ws_scheme}://{host_with_port}{websocket.url.path}"
        urls.append(primary_url)
        
        # Fallback: try without port for standard ports (443 for wss, 80 for ws)
        if (ws_scheme == "wss" and ":443" in host_with_port) or (ws_scheme == "ws" and ":80" in host_with_port):
            fallback_url = f"{ws_scheme}://{host_with_port.replace(':443', '').replace(':80', '')}{websocket.url.path}"
            if fallback_url != primary_url:
                urls.append(fallback_url)
                
    # Fallback method: Use EXTERNAL_URL if configured
    elif EXTERNAL_URL:
        base_url = EXTERNAL_URL.rstrip('/')
        
        # Convert external URL to WebSocket scheme
        if base_url.startswith('https://'):
            ws_url = base_url.replace('https://', 'wss://')
        elif base_url.startswith('http://'):
            ws_url = base_url.replace('http://', 'ws://')
        else:
            ws_url = f"wss://{base_url}"  # Default to secure WebSocket
            
        # Add port if present in WebSocket URL but not in external URL
        if websocket.url.port and str(websocket.url.port) not in ws_url:
            if '://' in ws_url:
                scheme, rest = ws_url.split('://', 1)
                ws_url = f"{scheme}://{rest}:{websocket.url.port}"
                
        primary_url = f"{ws_url}{websocket.url.path}"
        urls.append(primary_url)
        
    # Local development fallback
    else:
        urls.append(str(websocket.url))
    
    return urls

@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    try:
        # For WebSocket connections, Twilio sends the signature in headers during the HTTP upgrade
        # Extract signature from headers
        headers = dict(websocket.headers)
        x_twilio_signature = headers.get("x-twilio-signature")
        
        # Signature validation for production or when forced
        if ENVIRONMENT == "production" or FORCE_VALIDATION:
            logger.info("Validating Twilio signature for WebSocket connection")
            
            if not x_twilio_signature:
                logger.warning("No X-Twilio-Signature header found in WebSocket request")
                await websocket.close(code=1008, reason="Missing signature")
                return
            
            # Get the query string parameters
            query_params = dict(websocket.query_params)
            
            # Construct validation URLs using our utility function
            validation_urls = _construct_validation_urls(websocket, headers)
            
            if not validation_urls:
                logger.error("Could not construct validation URLs")
                await websocket.close(code=1008, reason="URL construction failed")
                return
            
            # Attempt validation with constructed URLs
            validation_successful = False
            successful_url = None
            
            for url in validation_urls:
                try:
                    if validator.validate(url, query_params, x_twilio_signature):
                        logger.info(f"Signature validation successful with URL: {url}")
                        validation_successful = True
                        successful_url = url
                        break
                except Exception as e:
                    logger.debug(f"Validation error for URL: {url}", {"error": str(e)})
                    continue
                    
            if not validation_successful:
                logger.error("Signature validation failed for all URLs", {
                    "attempted_urls": validation_urls,
                    "signature": x_twilio_signature[:20] + "..." if x_twilio_signature else None
                })
                await websocket.close(code=1008, reason="Invalid signature")
                return
                
            logger.info("WebSocket signature validated", {"validated_with": successful_url})
        else:
            logger.info("Skipping signature validation (development mode)")
        
        # Accept the WebSocket connection
        await websocket.accept()
        handler = ConversationRelayHandler(websocket)
        
        logger.info("WebSocket connection established", {
            "url": str(websocket.url),
            "session_ready": True
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
