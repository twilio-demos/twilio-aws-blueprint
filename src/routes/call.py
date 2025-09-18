from fastapi import APIRouter, Request, Response, HTTPException
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse
from src.utils.env import TWILIO_AUTH_TOKEN, TTS_PROVIDER, TTS_VOICE, WELCOME_GREETING
from src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Get Twilio Auth Token from .env
validator = RequestValidator(TWILIO_AUTH_TOKEN)


@router.post("/twiml")
async def call_twiml(request: Request):
    try:
        # Log comprehensive request details for troubleshooting
        logger.info("ConversationRelay TwiML request received - DEBUG INFO", {
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
        url = str(request.url)
        
        if not signature or not validator.validate(url, params, signature):
            logger.warning("Twilio webhook validation failed", {
                "url": url,
                "hasSignature": bool(signature),
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
        url = str(request.url)
        
        if not signature or not validator.validate(url, params, signature):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")
        
        # TODO: Implement call action logic
        logger.info("Call action received", {"params": params})
        return {"result": "action received"}
        
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in call action", {"error": str(error)})
        return {"result": "error", "message": str(error)}
