from fastapi import APIRouter, HTTPException, Request, Response

from src.utils.env import WELCOME_GREETING
from src.utils.logger import get_logger
from src.utils.twiml import create_fallback_twiml, create_initial_twiml

router = APIRouter()
logger = get_logger(__name__)


@router.post("/twiml")
async def call_twiml(request: Request):
    try:
        # Get parsed request body
        params = request.state.twilio_params

        # Log comprehensive request details for troubleshooting
        logger.info(
            "ConversationRelay TwiML request received",
            {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "query_params": dict(request.query_params),
                "path_params": dict(request.path_params)
                if hasattr(request, "path_params")
                else {},
                "body": params,
            },
        )

        # Extract parameters from request
        call_sid = params.get("CallSid")
        from_number = params.get("From")
        to_number = params.get("To")
        direction = params.get("Direction")
        language = params.get("language", "en-US")
        welcome_greeting = params.get("welcomeGreeting", WELCOME_GREETING)
        action_url = params.get("actionUrl")
        host = request.headers.get("host")

        # Generate ConversationRelay twiml
        twiml_response = create_initial_twiml(action_url, host, welcome_greeting, {})

        logger.info(
            "ConversationRelay TwiML response generated",
            {
                "CallSid": call_sid,
                "From": from_number,
                "To": to_number,
                "Direction": direction,
                "language": language,
                "responseLength": len(twiml_response),
                "response": twiml_response,
            },
        )

        return Response(content=twiml_response, media_type="text/xml")

    except HTTPException:
        raise
    except Exception as error:
        logger.error(
            "Error generating ConversationRelay TwiML",
            {
                "error": str(error),
                "body": params if "params" in locals() else None,
            },
        )

        # Return a simple fallback TwiML on error
        fallback_twiml = create_fallback_twiml()

        return Response(content=fallback_twiml, media_type="text/xml")


@router.post("/action")
async def call_action(request: Request):
    try:
        # Get parsed request body
        params = request.state.twilio_params

        # TODO: Uncomment below line to reconnect upon failure only.
        # if 'SessionId' in params and 'ErrorCode' in params:
        if "SessionId" in params:
            host = request.headers.get("host")

            call_sid = params.get("CallSid")
            error_code = params.get("ErrorCode")
            error_message = params.get("ErrorMessage")
            session_duration = params.get("SessionDuration")
            session_id = params.get("SessionId")
            session_status = params.get("SessionStatus")

            action_url = str(request.url)

            logger.info(
                "Connect action received with error code",
                {
                    "call_sid": call_sid,
                    "error_code": error_code,
                    "error_message": error_message,
                    "session_duration": session_duration,
                    "session_id": session_id,
                    "session_status": session_status,
                },
            )

            # Create ConversationRelay twiml again to resume the session
            # Leave out the welcome message for a seamless experience
            twiml_response = create_initial_twiml(
                action_url,
                host,
                "",
                {"resume_session_id": session_id, "resume_call_sid": call_sid},
            )

            logger.info(
                "ConversationRelay reconnect TwiML response generated",
                {
                    "CallSid": call_sid,
                    "SessionId": session_id,
                    "responseLength": len(twiml_response),
                    "response": twiml_response,
                },
            )

            return Response(content=twiml_response, media_type="text/xml")

        # TODO: Implement call action logic
        logger.info("Call action received", {"params": params})
        return {"result": "action received"}

    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in call action", {"error": str(error)})
        return {"result": "error", "message": str(error)}
