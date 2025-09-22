from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from twilio.request_validator import RequestValidator
from src.utils.env import TWILIO_AUTH_TOKEN, TWILIO_ACCOUNT_SID, ENVIRONMENT, EXTERNAL_URL, FORCE_VALIDATION
from src.utils.logger import get_logger
import json
from typing import Dict, Any, Optional
from .conversationRelayHandler import ConversationRelayHandler

router = APIRouter()
logger = get_logger(__name__)

# Initialize Twilio request validator
validator = RequestValidator(TWILIO_AUTH_TOKEN)


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
            handler.process_disconnect()
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
