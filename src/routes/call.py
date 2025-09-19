from fastapi import APIRouter, Request, Response, HTTPException
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse
from src.utils.env import TWILIO_AUTH_TOKEN, TTS_PROVIDER, TTS_VOICE, WELCOME_GREETING, ENVIRONMENT, EXTERNAL_URL, FORCE_VALIDATION
from src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Get Twilio Auth Token from .env
validator = RequestValidator(TWILIO_AUTH_TOKEN)


@router.post("/twiml")
async def call_twiml(request: Request):
    try:
        # Log comprehensive request details for troubleshooting
        logger.info("ConversationRelay TwiML request received", {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "query_params": dict(request.query_params),
            "path_params": dict(request.path_params) if hasattr(request, 'path_params') else {},
        })
        
        # Get content type
        content_type = request.headers.get("content-type", "")
        logger.info("Content-Type detected", {"content_type": content_type})
        
        if "application/x-www-form-urlencoded" in content_type:
            # Twilio sends form data
            logger.info("Parsing as form data")
            form = await request.form()
            params = dict(form)
        elif "application/json" in content_type:
            # JSON data
            logger.info("Parsing as JSON")
            body = await request.json()
            params = body if isinstance(body, dict) else {}
        else:
            # Try form first (Twilio default), fallback to empty
            logger.info("Unknown content type, trying form parsing")
            try:
                form = await request.form()
                params = dict(form)
            except Exception as e:
                logger.warning("Form parsing failed", {"error": str(e)})
                params = {}
        
        logger.info("ConversationRelay TwiML request received", {
            "body": params,
            "query": dict(request.query_params),
            "headers": {
                "x-twilio-signature": request.headers.get("x-twilio-signature"),
                "content-type": request.headers.get("content-type"),
            },
        })

        # Validate Twilio signature
        signature = request.headers.get("X-Twilio-Signature")
        
        # Determine the correct URL for validation
        if EXTERNAL_URL:
            # Use external URL (ngrok, load balancer, etc.)
            validation_url = f"{EXTERNAL_URL.rstrip('/')}{request.url.path}"
            if request.url.query:
                validation_url += f"?{request.url.query}"
        else:
            # Use the request URL as-is
            validation_url = str(request.url)
        
        # Log validation details for debugging
        logger.info("Signature validation details", {
            "signature_provided": bool(signature),
            "validation_url": validation_url,
            "request_url": str(request.url),
            "external_url": EXTERNAL_URL,
            "environment": ENVIRONMENT,
            "params_count": len(params) if params else 0,
            "host_header": request.headers.get("host"),
            "user_agent": request.headers.get("user-agent"),
        })
        
        # Always validate Twilio signatures (no development mode bypass)
        if not signature:
            logger.warning("No Twilio signature provided", {
                "url": validation_url,
                "environment": ENVIRONMENT
            })
            raise HTTPException(status_code=403, detail="Missing Twilio signature")
        
        # For testing purposes, temporarily log more details
        validation_result = validator.validate(validation_url, params, signature)
        
        # Temporary bypass for development testing - remove in production
        if not validation_result and ENVIRONMENT == 'development' and not FORCE_VALIDATION:
            logger.warning("Signature validation failed but bypassing for development", {
                "validation_url": validation_url,
                "signature_preview": signature[:20] + "..." if signature else None,
            })
            validation_result = True
        
        if not validation_result:
            logger.warning("Twilio webhook validation failed", {
                "validation_url": validation_url,
                "request_url": str(request.url),
                "external_url": EXTERNAL_URL,
                "hasSignature": bool(signature),
                "environment": ENVIRONMENT,
                "signature_preview": signature[:20] + "..." if signature else None,
                "params_keys": list(params.keys()) if params else [],
            })
            
            # In development, provide more helpful error info
            if ENVIRONMENT == 'development':
                logger.info("Validation details for debugging", {
                    "signature": signature,
                    "params": dict(params),
                    "validation_url": validation_url
                })
            
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

        # Extract parameters from request
        call_sid = params.get("CallSid")
        from_number = params.get("From")
        to_number = params.get("To")
        direction = params.get("Direction")
        language = params.get("language", "en-US")
        welcome_greeting = params.get("welcomeGreeting", WELCOME_GREETING)
        action_url = params.get("actionUrl")

        # Build WebSocket URL dynamically based on request
        host = request.headers.get("host")
        websocket_url = f"wss://{host}/ws/"

        # Create TwiML response using Twilio SDK
        response = VoiceResponse()

        # Connect to ConversationRelay
        connect_action_url = action_url or f"https://{host}/call/action"
        connect = response.connect(action=connect_action_url)
        
        conversation_relay = connect.conversation_relay(
            url=websocket_url,
            dtmf_detection=True,
            interruptible="any",
            welcome_greeting=welcome_greeting,
            tts_provider=TTS_PROVIDER,
            voice=TTS_VOICE
        )

        twiml_response = str(response)

        logger.info("ConversationRelay TwiML response generated", {
            "CallSid": call_sid,
            "From": from_number,
            "To": to_number,
            "Direction": direction,
            "language": language,
            "websocketUrl": websocket_url,
            "responseLength": len(twiml_response),
        })

        return Response(content=twiml_response, media_type="text/xml")

    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error generating ConversationRelay TwiML", {
            "error": str(error),
            "body": params if 'params' in locals() else None,
        })

        # Return a simple fallback TwiML on error
        fallback_response = VoiceResponse()
        fallback_response.say("I'm sorry, there was an error starting the conversation. Please try again later.")
        fallback_response.hangup()
        fallback_twiml = str(fallback_response)

        return Response(content=fallback_twiml, media_type="text/xml")


@router.post("/action")
async def call_action(request: Request):
    try:
        # Get request body based on content type
        content_type = request.headers.get("content-type", "")
        
        if "application/x-www-form-urlencoded" in content_type:
            form = await request.form()
            params = dict(form)
        elif "application/json" in content_type:
            body = await request.json()
            params = body if isinstance(body, dict) else {}
        else:
            # Try form first (Twilio default)
            try:
                form = await request.form()
                params = dict(form)
            except Exception:
                params = {}
    
        # Validate Twilio signature
        signature = request.headers.get("X-Twilio-Signature")
        
        # Determine the correct URL for validation
        if EXTERNAL_URL:
            # Use external URL (ngrok, load balancer, etc.)
            validation_url = f"{EXTERNAL_URL.rstrip('/')}{request.url.path}"
            if request.url.query:
                validation_url += f"?{request.url.query}"
        else:
            # Use the request URL as-is
            validation_url = str(request.url)
        
        # Always validate Twilio signatures (no development mode bypass)
        if not signature:
            logger.warning("No Twilio signature provided for action endpoint", {
                "url": validation_url,
                "environment": ENVIRONMENT
            })
            raise HTTPException(status_code=403, detail="Missing Twilio signature")
        
        if not validator.validate(validation_url, params, signature):
            logger.warning("Twilio action webhook validation failed", {
                "validation_url": validation_url,
                "hasSignature": bool(signature),
                "environment": ENVIRONMENT
            })
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")
        
        # TODO: Implement call action logic
        logger.info("Call action received", {"params": params})
        return {"result": "action received"}
        
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in call action", {"error": str(error)})
        return {"result": "error", "message": str(error)}
