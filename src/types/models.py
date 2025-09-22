from pydantic import BaseModel


class CallRequest(BaseModel):
    call_sid: str
    from_number: str
    to_number: str
    status: str


class ActionResponse(BaseModel):
    result: str
