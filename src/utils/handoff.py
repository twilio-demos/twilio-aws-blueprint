import json

from fastapi import Request, Response
from typing_extensions import Optional

from src.types.models import Session
from src.utils.logger import get_logger
from src.utils.twiml import create_error_twiml, create_idle_twiml, create_initial_twiml

logger = get_logger(__name__)


def handle_handoff(request: Request, session: Optional[Session]):
    # Get parsed request body
    params = request.state.twilio_params
    call_sid = params.get("CallSid")
    session_id = params.get("SessionId")
    handoff_data = json.loads(params.get("HandoffData"))
    language = handoff_data.get(
        "language", session.Config.Lang if session is not None else None
    )

    if "result" in handoff_data:
        match handoff_data.get("result"):
            case "idle":
                twiml_response = create_idle_twiml(language)
                return Response(content=twiml_response, media_type="text/xml")
            case "hint":
                # Restart the session with a new list of hints.
                host = request.headers.get("host")
                action_url = str(request.url)

                twiml_response = create_initial_twiml(
                    action_url,
                    host,
                    language,
                    handoff_data.get("message"),
                    handoff_data.get("hints"),
                    {"resume_session_id": session_id, "resume_call_sid": call_sid},
                )

                return Response(content=twiml_response, media_type="text/xml")

    twiml_response = create_error_twiml(language)
    return Response(content=twiml_response, media_type="text/xml")
