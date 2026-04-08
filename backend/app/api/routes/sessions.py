from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.chat_persistence_service import get_session, get_session_messages


router = APIRouter()


class SessionResponse(BaseModel):
    id: str
    title: str | None = None
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    session_id: str
    task_id: str | None = None
    role: str
    content: str
    created_at: str


class SessionMessagesResponse(BaseModel):
    session: SessionResponse
    messages: list[MessageResponse]


@router.get("/{session_id}", response_model=SessionResponse)
def get_session_detail(session_id: str) -> SessionResponse:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(**session)


@router.get("/{session_id}/messages", response_model=SessionMessagesResponse)
def get_session_messages_detail(session_id: str) -> SessionMessagesResponse:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = get_session_messages(session_id)
    return SessionMessagesResponse(
        session=SessionResponse(**session),
        messages=[MessageResponse(**message) for message in messages],
    )
