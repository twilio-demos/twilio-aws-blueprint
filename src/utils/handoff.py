from typing import Any

from fastapi import Response

from src.utils.logger import get_logger
from src.utils.twiml import create_error_twiml, create_idle_twiml

logger = get_logger(__name__)


def handle_handoff(call_sid: str, session_id: str, handoff_data: Any):
    if "result" in handoff_data:
        match handoff_data.get("result"):
            case "idle":
                twiml_response = create_idle_twiml()
                return Response(content=twiml_response, media_type="text/xml")

    twiml_response = create_error_twiml()
    return Response(content=twiml_response, media_type="text/xml")
