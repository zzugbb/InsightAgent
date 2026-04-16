import json
import re
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator
from starlette.responses import PlainTextResponse

from app.api.deps import get_current_user
from app.schemas.trace import parse_trace_steps
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
    get_session_tasks,
    get_session_usage_summary,
    list_sessions,
    update_session_title,
)
from app.services.task_status_service import (
    normalize_task_status,
    task_status_label,
    task_status_rank,
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


class SessionExportMessage(BaseModel):
    id: str
    task_id: str | None = None
    role: str
    content: str
    created_at: str


class SessionExportTracePreviewStep(BaseModel):
    id: str
    seq: int | None = None
    type: str
    title: str
    content_excerpt: str


class SessionExportTaskSummary(BaseModel):
    id: str
    prompt: str
    status: str
    status_normalized: str
    status_label: str
    status_rank: int
    created_at: str
    updated_at: str
    usage: dict[str, object] | None = None
    trace_step_count: int
    rag_hit_count: int
    trace_preview: list[SessionExportTracePreviewStep]


class SessionExportStats(BaseModel):
    task_count: int
    message_count: int
    trace_step_count: int
    rag_hit_count: int


class SessionExportJsonResponse(BaseModel):
    version: str
    exported_at: str
    session: SessionResponse
    usage_summary: SessionUsageSummaryResponse
    stats: SessionExportStats
    messages: list[SessionExportMessage]
    tasks: list[SessionExportTaskSummary]


def _normalize_filename_part(raw: str, fallback: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw).strip("-._")
    return normalized or fallback


def _build_session_export_filename(session: dict, ext: str) -> str:
    sid = _normalize_filename_part(str(session.get("id", "")), "session")
    title = _normalize_filename_part(str(session.get("title") or ""), "")
    suffix = f"-{title}" if title else ""
    return f"insightagent-session-{sid}{suffix}.{ext}"


def _parse_usage_blob(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _normalize_excerpt(text: str, limit: int = 140) -> str:
    normalized = " ".join((text or "").strip().split())
    if not normalized:
        return ""
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


def _trace_step_title(step: Any) -> str:
    meta = getattr(step, "meta", None)
    label = getattr(meta, "label", None) if meta is not None else None
    if isinstance(label, str) and label.strip():
        return label.strip()
    step_type = getattr(meta, "step_type", None) if meta is not None else None
    if isinstance(step_type, str) and step_type.strip():
        return step_type.strip().replace("_", " ")
    raw_type = getattr(step, "type", None)
    if isinstance(raw_type, str) and raw_type.strip():
        return raw_type.strip().replace("_", " ")
    return "step"


def _task_status_meta(task: dict) -> dict[str, object]:
    status = str(task.get("status", ""))
    return {
        "status_normalized": normalize_task_status(status),
        "status_label": task_status_label(status),
        "status_rank": task_status_rank(status),
    }


def _build_session_task_summary(
    task: dict,
) -> tuple[SessionExportTaskSummary, int, int]:
    raw_trace = task.get("trace_json")
    parsed_steps: list[Any] = []
    if isinstance(raw_trace, str) and raw_trace.strip():
        try:
            loaded = json.loads(raw_trace)
            if isinstance(loaded, list):
                parsed_steps = parse_trace_steps([x for x in loaded if isinstance(x, dict)])
        except Exception:
            parsed_steps = []

    rag_hit_count = 0
    preview_steps: list[SessionExportTracePreviewStep] = []
    for step in parsed_steps:
        rag_meta = getattr(step, "meta", None)
        rag_obj = getattr(rag_meta, "rag", None) if rag_meta is not None else None
        if isinstance(rag_obj, dict):
            chunks = rag_obj.get("chunks")
            if isinstance(chunks, list):
                rag_hit_count += sum(1 for chunk in chunks if isinstance(chunk, str) and chunk.strip())

    for step in parsed_steps[-3:]:
        content = getattr(step, "content", "") or ""
        preview_steps.append(
            SessionExportTracePreviewStep(
                id=str(getattr(step, "id", "")),
                seq=getattr(step, "seq", None),
                type=str(getattr(step, "type", "")),
                title=_trace_step_title(step),
                content_excerpt=_normalize_excerpt(str(content), limit=120),
            ),
        )

    status_meta = _task_status_meta(task)
    summary = SessionExportTaskSummary(
        id=str(task["id"]),
        prompt=str(task.get("prompt", "")),
        status=str(task.get("status", "")),
        status_normalized=str(status_meta["status_normalized"]),
        status_label=str(status_meta["status_label"]),
        status_rank=int(status_meta["status_rank"]),
        created_at=str(task.get("created_at", "")),
        updated_at=str(task.get("updated_at", "")),
        usage=_parse_usage_blob(task.get("usage_json")),
        trace_step_count=len(parsed_steps),
        rag_hit_count=rag_hit_count,
        trace_preview=preview_steps,
    )
    return summary, len(parsed_steps), rag_hit_count


def _append_fenced_block(lines: list[str], content: str, language: str = "text") -> None:
    text = content.rstrip("\n")
    fence = "```"
    if "```" in text:
        fence = "~~~"
    lines.append(f"{fence}{language}".rstrip())
    lines.append(text)
    lines.append(fence)


def _build_session_export_markdown(payload: SessionExportJsonResponse) -> str:
    lines: list[str] = []
    lines.append("# InsightAgent Session Export")
    lines.append("")
    lines.append(f"- Exported At: {payload.exported_at}")
    lines.append(f"- Session ID: {payload.session.id}")
    lines.append(f"- Session Title: {payload.session.title or '(untitled)'}")
    lines.append(f"- Message Count: {payload.stats.message_count}")
    lines.append(f"- Task Count: {payload.stats.task_count}")
    lines.append(f"- Trace Step Count: {payload.stats.trace_step_count}")
    lines.append(f"- RAG Hit Count: {payload.stats.rag_hit_count}")
    lines.append("")
    lines.append("## Usage Summary")
    lines.append("")
    _append_fenced_block(
        lines,
        json.dumps(payload.usage_summary.model_dump(), ensure_ascii=False, indent=2),
        "json",
    )
    lines.append("")
    lines.append("## Messages")
    lines.append("")
    if not payload.messages:
        lines.append("_No messages_")
        lines.append("")
    else:
        for idx, msg in enumerate(payload.messages, start=1):
            ref = f" · task={msg.task_id}" if msg.task_id else ""
            lines.append(f"### {idx}. {msg.role.upper()} · {msg.created_at}{ref}")
            lines.append("")
            _append_fenced_block(lines, msg.content or "", "text")
            lines.append("")

    lines.append("## Tasks")
    lines.append("")
    if not payload.tasks:
        lines.append("_No tasks_")
        lines.append("")
    else:
        for idx, task in enumerate(payload.tasks, start=1):
            lines.append(f"### {idx}. {task.id}")
            lines.append("")
            lines.append(f"- Status: {task.status} ({task.status_normalized}, rank={task.status_rank})")
            lines.append(f"- Prompt: {_normalize_excerpt(task.prompt, limit=180)}")
            lines.append(f"- Updated At: {task.updated_at}")
            lines.append(f"- Trace Steps: {task.trace_step_count}")
            lines.append(f"- RAG Hits: {task.rag_hit_count}")
            if task.usage:
                lines.append("- Usage:")
                _append_fenced_block(
                    lines,
                    json.dumps(task.usage, ensure_ascii=False, indent=2),
                    "json",
                )
            if task.trace_preview:
                lines.append("- Trace Preview:")
                for preview in task.trace_preview:
                    seq = preview.seq if preview.seq is not None else "-"
                    lines.append(
                        f"  - seq={seq} · {preview.type} · {preview.title} · {preview.content_excerpt or '(empty)'}",
                    )
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _build_session_export_payload(
    session: dict,
    user_id: str,
) -> SessionExportJsonResponse:
    session_id = str(session["id"])
    usage_summary = SessionUsageSummaryResponse(
        **get_session_usage_summary(session_id, user_id=user_id),
    )
    message_rows = get_session_messages(session_id, user_id)
    task_rows = get_session_tasks(session_id, user_id)
    task_summaries: list[SessionExportTaskSummary] = []
    trace_step_total = 0
    rag_hit_total = 0
    for task_row in task_rows:
        summary, trace_count, rag_count = _build_session_task_summary(task_row)
        task_summaries.append(summary)
        trace_step_total += trace_count
        rag_hit_total += rag_count

    return SessionExportJsonResponse(
        version="1.0",
        exported_at=datetime.now().isoformat(),
        session=SessionResponse(**session),
        usage_summary=usage_summary,
        stats=SessionExportStats(
            task_count=len(task_rows),
            message_count=len(message_rows),
            trace_step_count=trace_step_total,
            rag_hit_count=rag_hit_total,
        ),
        messages=[
            SessionExportMessage(
                id=row["id"],
                task_id=row["task_id"],
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"],
            )
            for row in message_rows
        ],
        tasks=task_summaries,
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


@router.get("/{session_id}/export/json", response_model=SessionExportJsonResponse)
def export_session_json(
    session_id: str,
    response: Response,
    download: bool = Query(
        default=False,
        description="为 true 时附加 Content-Disposition 附件头",
    ),
    current_user: dict = Depends(get_current_user),
) -> SessionExportJsonResponse:
    user_id = str(current_user["id"])
    session = get_session(session_id, user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    payload = _build_session_export_payload(session, user_id)
    if download:
        response.headers["Content-Disposition"] = (
            f'attachment; filename="{_build_session_export_filename(session, "json")}"'
        )
    return payload


@router.get("/{session_id}/export/markdown", response_class=PlainTextResponse)
def export_session_markdown(
    session_id: str,
    download: bool = Query(
        default=False,
        description="为 true 时附加 Content-Disposition 附件头",
    ),
    current_user: dict = Depends(get_current_user),
) -> PlainTextResponse:
    user_id = str(current_user["id"])
    session = get_session(session_id, user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    payload = _build_session_export_payload(session, user_id)
    markdown = _build_session_export_markdown(payload)
    headers: dict[str, str] = {}
    if download:
        headers["Content-Disposition"] = (
            f'attachment; filename="{_build_session_export_filename(session, "md")}"'
        )
    return PlainTextResponse(
        markdown,
        headers=headers,
        media_type="text/markdown; charset=utf-8",
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
