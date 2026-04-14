from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator

from app.api.deps import get_current_user
from app.services.chroma_memory_service import (
    add_session_memory_text,
    cleanup_session_memory_collection,
    get_session_memory_status,
    query_session_memory,
)
from app.services.chat_persistence_service import (
    count_sessions,
    create_session_record,
    delete_session,
    get_session,
    get_session_messages,
    get_session_usage_summary,
    list_sessions,
    update_session_title,
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
    total: int = Field(description="符合条件的会话总数")
    limit: int
    offset: int
    has_more: bool = Field(description="是否仍有下一页（offset + len(items) < total）")


class CreateSessionRequest(BaseModel):
    title: str | None = None


class UpdateSessionRequest(BaseModel):
    title: str


class SessionMemoryStatusResponse(BaseModel):
    collection: str
    chroma_url: str
    chroma_reachable: bool
    collection_exists: bool
    document_count: int
    error: str | None = None


class SessionUsageSummaryResponse(BaseModel):
    tasks_total: int
    tasks_with_usage: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_estimate: float
    avg_total_tokens: float | None = None
    avg_cost_estimate: float | None = None


class MemoryAddRequest(BaseModel):
    text: str = Field(min_length=1, max_length=32_000)
    metadata: dict[str, str] | None = Field(
        default=None,
        description="可选；Chroma document metadata（字符串键值）",
    )

    @field_validator("metadata")
    @classmethod
    def _validate_metadata(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        if v is None or len(v) == 0:
            return None
        if len(v) > 32:
            raise ValueError("metadata may have at most 32 keys")
        for key, val in v.items():
            if len(key) > 128:
                raise ValueError("metadata key too long (max 128)")
            if len(val) > 8192:
                raise ValueError("metadata value too long (max 8192 per value)")
        return v


class MemoryAddResponse(BaseModel):
    added_id: str
    document_count: int


class MemoryQueryRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8_000)
    n_results: int = Field(default=4, ge=1, le=50)


class MemoryQueryResponse(BaseModel):
    ids: list[list[str]]
    documents: list[list[str]]
    distances: list[list[float | None]] | None = None
    metadatas: list[list[dict[str, Any]]] | None = Field(
        default=None,
        description="与 documents 对齐的 Chroma metadata；无则空 dict",
    )


@router.post("", response_model=SessionResponse)
def post_session(
    payload: CreateSessionRequest = CreateSessionRequest(),
    current_user: dict = Depends(get_current_user),
) -> SessionResponse:
    row = create_session_record(title=payload.title, user_id=str(current_user["id"]))
    return SessionResponse(**row)


@router.get("", response_model=SessionListResponse)
def get_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(
        default=0,
        ge=0,
        le=50_000,
        description="跳过前 offset 条（与 limit 组合做分页）",
    ),
    current_user: dict = Depends(get_current_user),
) -> SessionListResponse:
    user_id = str(current_user["id"])
    sessions = list_sessions(user_id=user_id, limit=limit, offset=offset)
    total = count_sessions(user_id=user_id)
    n = len(sessions)
    return SessionListResponse(
        items=[SessionResponse(**session) for session in sessions],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + n < total,
    )


@router.patch("/{session_id}", response_model=SessionResponse)
def patch_session(
    session_id: str,
    payload: UpdateSessionRequest,
    current_user: dict = Depends(get_current_user),
) -> SessionResponse:
    row = update_session_title(session_id, payload.title, str(current_user["id"]))
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(**row)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session_detail(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> SessionResponse:
    session = get_session(session_id, str(current_user["id"]))
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(**session)


@router.get("/{session_id}/memory/status", response_model=SessionMemoryStatusResponse)
def get_session_memory_status_route(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> SessionMemoryStatusResponse:
    user_id = str(current_user["id"])
    if get_session(session_id, user_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    raw = get_session_memory_status(session_id)
    return SessionMemoryStatusResponse(**raw)


@router.get("/{session_id}/usage/summary", response_model=SessionUsageSummaryResponse)
def get_session_usage_summary_route(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> SessionUsageSummaryResponse:
    user_id = str(current_user["id"])
    if get_session(session_id, user_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    raw = get_session_usage_summary(session_id, user_id=user_id)
    return SessionUsageSummaryResponse(**raw)


@router.post("/{session_id}/memory/add", response_model=MemoryAddResponse)
def post_session_memory_add(
    session_id: str,
    payload: MemoryAddRequest,
    current_user: dict = Depends(get_current_user),
) -> MemoryAddResponse:
    if get_session(session_id, str(current_user["id"])) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        raw = add_session_memory_text(
            session_id,
            payload.text,
            metadatas=payload.metadata,
        )
        return MemoryAddResponse(**raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — Chroma 不可达等
        msg = str(exc).strip() or type(exc).__name__
        raise HTTPException(status_code=503, detail=msg[:400]) from exc


@router.post("/{session_id}/memory/query", response_model=MemoryQueryResponse)
def post_session_memory_query(
    session_id: str,
    payload: MemoryQueryRequest,
    current_user: dict = Depends(get_current_user),
) -> MemoryQueryResponse:
    if get_session(session_id, str(current_user["id"])) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        raw = query_session_memory(
            session_id,
            payload.text,
            n_results=payload.n_results,
        )
        return MemoryQueryResponse(**raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).strip() or type(exc).__name__
        raise HTTPException(status_code=503, detail=msg[:400]) from exc


@router.get("/{session_id}/messages", response_model=SessionMessagesResponse)
def get_session_messages_detail(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> SessionMessagesResponse:
    user_id = str(current_user["id"])
    session = get_session(session_id, user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = get_session_messages(session_id, user_id)
    return SessionMessagesResponse(
        session=SessionResponse(**session),
        messages=[MessageResponse(**message) for message in messages],
    )


@router.delete("/{session_id}", status_code=204)
def delete_session_route(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> Response:
    user_id = str(current_user["id"])
    if get_session(session_id, user_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not delete_session(session_id, user_id):
        raise HTTPException(status_code=404, detail="Session not found")
    # best-effort: 清理 Chroma 会话 memory collection，失败不阻塞主删除流程
    cleanup_session_memory_collection(session_id)
    return Response(status_code=204)
