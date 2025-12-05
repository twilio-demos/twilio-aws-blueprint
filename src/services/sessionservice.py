import copy
import uuid
from datetime import datetime, timezone

from typing_extensions import Optional

from src.types.models import (
    Session,
)
from src.utils.logger import get_logger

from .dynamodbservice import DynamoDBService

logger = get_logger(__name__)


class SessionService(DynamoDBService):
    def __init__(self):
        super().__init__("ConversationRelaySessions")
        self.sessions: dict[str, Session] = {}

    def create(
        self,
        call_sid: str,
        session_id: str,
        call_from: Optional[str],
        call_to: Optional[str],
        hints: Optional[str],
        language: Optional[str],
    ) -> Session:
        """Creates a session object, caches it in memory, and persists it to DynamoDB."""
        session = Session(
            CallSid=call_sid,
            SessionId=session_id,
            ThreadId=str(uuid.uuid4()),
            Created=datetime.now(timezone.utc).isoformat(),
            CallFrom=call_from,
            CallTo=call_to,
        )
        if hints is not None:
            session.Config.Hints = hints
        if language is not None:
            session.Config.Lang = language
        self.sessions[session_id] = session
        super()._add_item(session)
        return session

    def restore(
        self,
        new_session_id: str,
        hints: Optional[str],
        language: Optional[str],
        old_session: Session,
        resume_error: bool,
    ) -> Session:
        """
        Restores a previous session to a new session.
        Creates a session object, caches it in memory, and persists it to DynamoDB.
        """
        session = copy.deepcopy(old_session)
        session.SessionId = new_session_id
        session.SessionStatus = "in-progress"
        session.Created = datetime.now(timezone.utc).isoformat()

        # The restored session may have updated configuration.
        if hints is not None:
            session.Config.Hints = hints
        if language is not None:
            session.Config.Lang = language

        if resume_error:
            # If the resume is occurring due to an error, track the number of errors to prevent infinite reconnect loops
            errors = session.SessionState.get("resume_error_attempts", 0)
            session.SessionState["resume_error_attempts"] = int(errors) + 1

        self.sessions[new_session_id] = session
        super()._add_item(session)
        return session

    def get(self, call_sid: str, session_id: str) -> Session | None:
        """Gets a session from memory if present, otherwise from DynamoDB."""

        # Return locally cached object if present
        if session_id in self.sessions:
            return self.sessions[session_id]

        session = super()._get_item({"CallSid": call_sid, "SessionId": session_id})
        if session is None:
            return None

        # Store in memory for future reference
        self.sessions[session_id] = Session(**session)
        return self.sessions[session_id]

    def update_language(self, session: Session, language: str) -> Session | None:
        """Updates session language and returns the updated session object."""

        # Perform updates only if the value actually changed
        if session.Config.Lang == language:
            return session

        # Update persisted storage
        super()._update_item(
            {"CallSid": session.CallSid, "SessionId": session.SessionId},
            "set Config.Lang=:s",
            {":s": language},
        )

        # Update object in memory
        session.Config.Lang = language
        return session

    def update_call_status(
        self, call_sid: str, session_id: str, status: str
    ) -> Session | None:
        """Updates session status by ID and returns the updated session object."""
        session = self.get(call_sid, session_id)
        if session is not None:
            return self.update_status(session, status)
        return None

    def update_status(self, session: Session, status: str) -> Session | None:
        """Updates session status and returns the updated session object."""

        # Perform updates only if the value actually changed
        if session.SessionStatus == status:
            return session

        # Update persisted storage
        super()._update_item(
            {"CallSid": session.CallSid, "SessionId": session.SessionId},
            "set SessionStatus=:s",
            {":s": status},
        )

        # Update object in memory
        session.SessionStatus = status
        return session

    def update_state(
        self, session: Session, state: dict[str, str | int | bool]
    ) -> Session | None:
        """Updates session state and returns the updated session object."""

        # Perform updates only if the value actually changed
        if session.SessionState == state:
            return session

        # Update persisted storage
        super()._update_item(
            {"CallSid": session.CallSid, "SessionId": session.SessionId},
            "set SessionState=:s",
            {":s": state},
        )

        # Update object in memory
        session.SessionState = state
        return session

    def update_dtmf_config(
        self, session: Session, max_digits: int, timeout: int
    ) -> Session | None:
        """Updates session DTMF config and returns the updated session object."""

        # Perform updates only if the values actually changed
        if (
            session.Config.DTMF.MaxDigits == max_digits
            and session.Config.DTMF.Timeout == timeout
        ):
            return session

        # Update persisted storage
        super()._update_item(
            {"CallSid": session.CallSid, "SessionId": session.SessionId},
            "set Config.DTMF.MaxDigits=:m, Config.DTMF.Timeout=:t",
            {":m": max_digits, ":t": timeout},
        )

        # Update object in memory
        session.Config.DTMF.MaxDigits = max_digits
        session.Config.DTMF.Timeout = timeout
        return session

    def update_idle_config(
        self, session: Session, max_attempts: int, timeout: int
    ) -> Session | None:
        """Updates session idle config and returns the updated session object."""

        # Perform updates only if the values actually changed
        if (
            session.Config.Idle.MaxAttempts == max_attempts
            and session.Config.Idle.Timeout == timeout
        ):
            return session

        # Update persisted storage
        super()._update_item(
            {"CallSid": session.CallSid, "SessionId": session.SessionId},
            "set Config.Idle.MaxAttempts=:m, Config.Idle.Timeout=:t",
            {":m": max_attempts, ":t": timeout},
        )

        # Update object in memory
        session.Config.Idle.MaxAttempts = max_attempts
        session.Config.Idle.Timeout = timeout
        return session


instance = SessionService()
