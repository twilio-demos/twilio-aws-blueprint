import json

from fastapi import APIRouter, HTTPException, Request, Response

from src.services.sessionservice import instance as session_service
from src.utils.env import ERROR_MAX_ATTEMPTS, WELCOME_GREETING
from src.utils.handoff import handle_handoff
from src.utils.logger import get_logger
from src.utils.twiml import (
    create_error_twiml,
    create_fallback_twiml,
    create_initial_twiml,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post("/twiml")
async def call_twiml(request: Request):
    params = None
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
        language = params.get("language")
        welcome_greeting = params.get("welcomeGreeting", WELCOME_GREETING)
        initial_hints = params.get("initialHints")
        action_url = params.get("actionUrl")
        host = request.headers.get("host")

        # Generate ConversationRelay twiml
        twiml_response = create_initial_twiml(
            action_url,
            host,
            language,
            welcome_greeting,
            initial_hints,
            {},
        )

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
                "body": params,
            },
        )

        # Return a simple fallback TwiML on error
        fallback_twiml = create_fallback_twiml(
            params.get("language") if params is not None else None
        )

        return Response(content=fallback_twiml, media_type="text/xml")


@router.post("/action")
async def call_action(request: Request):
    try:
        # Get parsed request body
        params = request.state.twilio_params

        if "SessionId" in params:
            call_sid = params.get("CallSid")
            session_id = params.get("SessionId")
            session_status = params.get("SessionStatus")

            session = session_service.update_call_status(
                call_sid, session_id, session_status
            )

            if "HandoffData" in params:
                handoff_data = json.loads(params.get("HandoffData"))
                logger.info(
                    "Handling handoff data",
                    {
                        "call_sid": call_sid,
                        "session_id": session_id,
                        "data": handoff_data,
                    },
                )
                return handle_handoff(request, session)

            if "ErrorCode" in params:
                host = request.headers.get("host")

                error_code = params.get("ErrorCode")
                error_message = params.get("ErrorMessage")
                session_duration = params.get("SessionDuration")

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
                # Initialize new session with current configuration
                initial_hints = None
                initial_language = None
                hit_max_errors = False
                if session is not None:
                    initial_hints = session.Config.Hints
                    initial_language = session.Config.Lang
                    if (
                        int(session.SessionState.get("resume_error_attempts", 0))
                        >= ERROR_MAX_ATTEMPTS
                    ):
                        hit_max_errors = True

                if hit_max_errors:
                    twiml_response = create_error_twiml(initial_language)

                    logger.info(
                        "ConversationRelay maximum errors limit reached",
                        {
                            "CallSid": call_sid,
                            "SessionId": session_id,
                        },
                    )
                else:
                    twiml_response = create_initial_twiml(
                        action_url,
                        host,
                        initial_language,
                        "",  # Leave out the welcome message for a seamless experience
                        initial_hints,
                        {
                            "resume_session_id": session_id,
                            "resume_call_sid": call_sid,
                            "resume_error": "true",
                        },
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

        logger.info("Call action received", {"params": params})
        return {"result": "action received"}

    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in call action", {"error": str(error)})
        return {"result": "error", "message": str(error)}
