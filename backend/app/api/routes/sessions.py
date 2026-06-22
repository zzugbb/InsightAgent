import json
import re
from datetime import datetime
from typing import Any

import app.services.chat_persistence_service as chat_persistence_service
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator
from starlette.responses import PlainTextResponse

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
    get_session_tasks,
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
    source_tasks_provider: int = 0
    source_tasks_estimated: int = 0
    source_tasks_mixed: int = 0
    source_tasks_legacy: int = 0
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
    governance: "SessionExportTaskGovernanceSummary | None" = None


class SessionExportTaskGovernanceSummary(BaseModel):
    profile: str | None = None
    provider_source: str | None = None
    allowed_tool_names: list[str] = Field(default_factory=list)
    allowed_tool_labels: list[str] = Field(default_factory=list)


class SessionExportGovernanceSummary(BaseModel):
    profiles: list[str] = Field(default_factory=list)
    provider_sources: list[str] = Field(default_factory=list)
    allowed_tool_names: list[str] = Field(default_factory=list)
    allowed_tool_labels: list[str] = Field(default_factory=list)


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
    governance: SessionExportGovernanceSummary | None = None
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


def _normalize_excerpt(text: str, limit: int = 140) -> str:
    normalized = " ".join((text or "").strip().split())
    if not normalized:
        return ""
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


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
    if payload.governance is not None:
        lines.append("## Tool Registry Governance")
        lines.append("")
        lines.append(
            "- Profiles: "
            + (", ".join(payload.governance.profiles) if payload.governance.profiles else "(none)")
        )
        lines.append(
            "- Provider Sources: "
            + (
                ", ".join(payload.governance.provider_sources)
                if payload.governance.provider_sources
                else "(none)"
            )
        )
        allowed_tools = (
            payload.governance.allowed_tool_labels
            if payload.governance.allowed_tool_labels
            else payload.governance.allowed_tool_names
        )
        lines.append(
            "- Allowed Tools: "
            + (", ".join(allowed_tools) if allowed_tools else "(none)")
        )
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
            if task.governance is not None:
                if task.governance.profile:
                    lines.append(
                        f"- Tool Registry Profile: {task.governance.profile}",
                    )
                if task.governance.provider_source:
                    lines.append(
                        f"- Tool Registry Source: {task.governance.provider_source}",
                    )
                allowed_tools = (
                    task.governance.allowed_tool_labels
                    if task.governance.allowed_tool_labels
                    else task.governance.allowed_tool_names
                )
                if allowed_tools:
                    lines.append("- Allowed Tools: " + ", ".join(allowed_tools))
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
    usage_summary_payload = get_session_usage_summary(session_id, user_id=user_id)
    message_rows = get_session_messages(session_id, user_id)
    task_rows = get_session_tasks(session_id, user_id)
    export_summary = chat_persistence_service.get_session_export_response_summary(
        usage_summary=usage_summary_payload,
        task_rows=task_rows,
        message_rows=message_rows,
        preview_limit=3,
    )
    usage_summary = SessionUsageSummaryResponse(
        **(
            export_summary.get("usage_summary")
            if isinstance(export_summary.get("usage_summary"), dict)
            else {}
        ),
    )
    task_summaries: list[SessionExportTaskSummary] = []
    for row in export_summary.get("tasks", []):
        if not isinstance(row, dict):
            continue
        task_summaries.append(
            SessionExportTaskSummary(
                id=str(row.get("id", "")),
                prompt=str(row.get("prompt", "")),
                status=str(row.get("status", "")),
                status_normalized=str(row.get("status_normalized", "")),
                status_label=str(row.get("status_label", "")),
                status_rank=int(row.get("status_rank", 0) or 0),
                created_at=str(row.get("created_at", "")),
                updated_at=str(row.get("updated_at", "")),
                usage=row.get("usage"),
                trace_step_count=int(row.get("trace_step_count", 0) or 0),
                rag_hit_count=int(row.get("rag_hit_count", 0) or 0),
                trace_preview=[
                    SessionExportTracePreviewStep(**item)
                    for item in row.get("trace_preview", [])
                    if isinstance(item, dict)
                ],
                governance=row.get("governance"),
            )
        )
    stats_summary = (
        export_summary.get("stats") if isinstance(export_summary.get("stats"), dict) else {}
    )
    return SessionExportJsonResponse(
        version="1.0",
        exported_at=datetime.now().isoformat(),
        session=SessionResponse(**session),
        usage_summary=usage_summary,
        governance=export_summary.get("governance"),
        stats=SessionExportStats(
            task_count=int(stats_summary.get("task_count", 0) or 0),
            message_count=int(stats_summary.get("message_count", 0) or 0),
            trace_step_count=int(stats_summary.get("trace_step_count", 0) or 0),
            rag_hit_count=int(stats_summary.get("rag_hit_count", 0) or 0),
        ),
        messages=[
            SessionExportMessage(
                id=str(row.get("id", "")),
                task_id=(
                    str(row.get("task_id", ""))
                    if row.get("task_id") is not None
                    else None
                ),
                role=str(row.get("role", "")),
                content=str(row.get("content", "")),
                created_at=str(row.get("created_at", "")),
            )
            for row in export_summary.get("messages", [])
            if isinstance(row, dict)
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
