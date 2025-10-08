import copy
import uuid
from datetime import datetime, timezone

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

    def create(self, call_sid: str, session_id: str) -> Session:
        """Creates a session object, caches it in memory, and persists it to DynamoDB."""
        session = Session(
            CallSid=call_sid,
            SessionId=session_id,
            ThreadId=str(uuid.uuid4()),
            Created=datetime.now(timezone.utc).isoformat(),
        )
        self.sessions[session_id] = session
        super()._add_item(session)
        return session

    def restore(self, call_sid: str, session_id: str, old_session: Session) -> Session:
        """
        Restores a previous session to a new session.
        Creates a session object, caches it in memory, and persists it to DynamoDB.
        """
        session = copy.deepcopy(old_session)
        session.CallSid = call_sid
        session.SessionId = session_id
        session.SessionStatus = "in-progress"
        session.Created = datetime.now(timezone.utc).isoformat()
        self.sessions[session_id] = session
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

    def update_status(
        self, call_sid: str, session_id: str, status: str
    ) -> Session | None:
        """Updates session status and returns the updated session object."""

        # Perform updates only if the value actually changed
        if (
            session_id in self.sessions
            and self.sessions[session_id].SessionStatus == status
        ):
            return self.sessions[session_id]

        super()._update_item(
            {"CallSid": call_sid, "SessionId": session_id},
            "set SessionStatus=:s",
            {":s": status},
        )

        # Get the updated object if not in memory yet, otherwise update the object in-memory and return it
        if session_id not in self.sessions:
            return self.get(call_sid, session_id)

        # Update object in memory
        self.sessions[session_id].SessionStatus = status
        return self.sessions[session_id]

    def update_state(
        self, call_sid: str, session_id: str, state: dict[str, str | int | bool]
    ) -> Session | None:
        """Updates session state and returns the updated session object."""

        # Perform updates only if the value actually changed
        if (
            session_id in self.sessions
            and self.sessions[session_id].SessionState == state
        ):
            return self.sessions[session_id]

        super()._update_item(
            {"CallSid": call_sid, "SessionId": session_id},
            "set SessionState=:s",
            {":s": state},
        )

        # Get the updated object if not in memory yet, otherwise update the object in-memory and return it
        if session_id not in self.sessions:
            return self.get(call_sid, session_id)

        # Update object in memory
        self.sessions[session_id].SessionState = state
        return self.sessions[session_id]

    def update_dtmf_config(
        self, call_sid: str, session_id: str, max_digits: int, timeout: int
    ) -> Session | None:
        """Updates session DTMF config and returns the updated session object."""

        # Perform updates only if the values actually changed
        if (
            session_id in self.sessions
            and self.sessions[session_id].Config.DTMF.MaxDigits == max_digits
            and self.sessions[session_id].Config.DTMF.Timeout == timeout
        ):
            return self.sessions[session_id]

        super()._update_item(
            {"CallSid": call_sid, "SessionId": session_id},
            "set Config.DTMF.MaxDigits=:m, Config.DTMF.Timeout=:t",
            {":m": max_digits, ":t": timeout},
        )

        # Get the updated object if not in memory yet, otherwise update the object in-memory and return it
        if session_id not in self.sessions:
            return self.get(call_sid, session_id)

        # Update object in memory
        self.sessions[session_id].Config.DTMF.MaxDigits = max_digits
        self.sessions[session_id].Config.DTMF.Timeout = timeout
        return self.sessions[session_id]

    def update_idle_config(
        self, call_sid: str, session_id: str, max_attempts: int, timeout: int
    ) -> Session | None:
        """Updates session idle config and returns the updated session object."""

        # Perform updates only if the values actually changed
        if (
            session_id in self.sessions
            and self.sessions[session_id].Config.Idle.MaxAttempts == max_attempts
            and self.sessions[session_id].Config.Idle.Timeout == timeout
        ):
            return self.sessions[session_id]

        super()._update_item(
            {"CallSid": call_sid, "SessionId": session_id},
            "set Config.Idle.MaxAttempts=:m, Config.Idle.Timeout=:t",
            {":m": max_attempts, ":t": timeout},
        )

        # Get the updated object if not in memory yet, otherwise update the object in-memory and return it
        if session_id not in self.sessions:
            return self.get(call_sid, session_id)

        # Update object in memory
        self.sessions[session_id].Config.Idle.MaxAttempts = max_attempts
        self.sessions[session_id].Config.Idle.Timeout = timeout
        return self.sessions[session_id]


instance = SessionService()
