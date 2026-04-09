from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

from app.services.chat_persistence_service import (
    create_session_record,
    delete_session,
    get_session,
    get_session_messages,
    list_sessions,
)


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


class SessionListResponse(BaseModel):
    items: list[SessionResponse]


class CreateSessionRequest(BaseModel):
    title: str | None = None


@router.post("", response_model=SessionResponse)
def post_session(payload: CreateSessionRequest = CreateSessionRequest()) -> SessionResponse:
    row = create_session_record(title=payload.title)
    return SessionResponse(**row)


@router.get("", response_model=SessionListResponse)
def get_sessions(limit: int = Query(default=20, ge=1, le=100)) -> SessionListResponse:
    sessions = list_sessions(limit=limit)
    return SessionListResponse(
        items=[SessionResponse(**session) for session in sessions],
    )


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


@router.delete("/{session_id}", status_code=204)
def delete_session_route(session_id: str) -> Response:
    if not delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return Response(status_code=204)
