import asyncio
import json
import re
from collections.abc import AsyncIterator
from datetime import datetime
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from starlette.responses import PlainTextResponse, StreamingResponse

from app.api.deps import get_current_user
from app.config import get_settings
from app.schemas.trace import TraceStep, parse_trace_steps
from app.services.audit_service import safe_record_audit_event
from app.services.chat_execution_service import (
    sse_error_payload,
    sse_event,
    stream_task_execution,
)
from app.services.chat_persistence_service import (
    count_tasks,
    create_message,
    create_task,
    ensure_session,
    get_session,
    get_task_messages,
    get_tasks_usage_dashboard,
    get_tasks_usage_summary,
    get_task,
    get_task_trace,
    get_task_trace_delta_from_task,
    update_task_status,
    list_tasks,
)
from app.services.task_status_service import (
    normalize_task_status,
    task_status_label,
    task_status_rank,
)


router = APIRouter()


def _parse_last_event_id(value: str | None) -> int | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = int(raw)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _latest_seq_from_task(task: dict) -> int:
    trace_json = task.get("trace_json")
    if not isinstance(trace_json, str) or not trace_json.strip():
        return 0
    try:
        raw = json.loads(trace_json)
    except Exception:
        return 0
    if not isinstance(raw, list):
        return 0
    steps = parse_trace_steps([x for x in raw if isinstance(x, dict)])
    if not steps:
        return 0
    return max((s.seq or 0) for s in steps)


async def stream_running_task_reconnect(
    task_id: str,
    user_id: str,
    *,
    after_seq: int = 0,
) -> AsyncIterator[str]:
    settings = get_settings()
    cursor = max(0, int(after_seq))
    poll_delay_fast_sec = max(0.05, float(settings.stream_reconnect_poll_fast_sec))
    poll_delay_max_sec = max(
        poll_delay_fast_sec,
        float(settings.stream_reconnect_poll_max_sec),
    )
    poll_delay_sec = poll_delay_fast_sec
    heartbeat_interval_sec = max(
        0.1,
        float(settings.stream_reconnect_heartbeat_interval_sec),
    )
    last_heartbeat_ts = monotonic()
    last_emitted_step_id: str | None = None
    last_phase: str | None = None

    def emit_state(phase: str) -> str | None:
        nonlocal last_phase
        if phase == last_phase:
            return None
        last_phase = phase
        return sse_event("state", {"task_id": task_id, "phase": phase})

    first_task = get_task(task_id, user_id)
    session_id = str(first_task.get("session_id")) if first_task else None
    yield sse_event(
        "start",
        {
            "session_id": session_id,
            "task_id": task_id,
            "resumed": True,
        },
    )
    while True:
        task = get_task(task_id, user_id)
        if task is None:
            yield sse_event(
                "error",
                sse_error_payload(
                    task_id=task_id,
                    message="Task not found during reconnect stream.",
                    code="task_not_found",
                    fatal=True,
                    retry_count=0,
                ),
            )
            return

        steps, next_cursor, _ = get_task_trace_delta_from_task(
            task,
            after_seq=cursor,
            limit=200,
        )
        if steps:
            parsed_steps = parse_trace_steps(steps)
            for step in parsed_steps:
                step_payload = step.model_dump(exclude_none=True)
                last_emitted_step_id = step.id
                yield sse_event(
                    "trace",
                    {
                        "task_id": task_id,
                        "step_id": step.id,
                        "step": step_payload,
                    },
                )
            cursor = next_cursor
            poll_delay_sec = poll_delay_fast_sec
        else:
            poll_delay_sec = min(poll_delay_max_sec, poll_delay_sec * 1.6)

        status = str(task.get("status", "running"))
        if status in {"completed", "failed"}:
            if last_emitted_step_id is None:
                full_steps = get_task_trace(task_id, user_id)
                if full_steps:
                    maybe_id = full_steps[-1].get("id")
                    if isinstance(maybe_id, str):
                        last_emitted_step_id = maybe_id
            if status == "completed":
                usage_payload: dict[str, object] | None = None
                usage_raw = task.get("usage_json")
                if isinstance(usage_raw, str) and usage_raw.strip():
                    try:
                        parsed_usage = json.loads(usage_raw)
                        if isinstance(parsed_usage, dict):
                            usage_payload = parsed_usage
                    except Exception:
                        usage_payload = None
                yield sse_event(
                    "done",
                    {
                        "session_id": str(task.get("session_id", "")) or session_id,
                        "task_id": task_id,
                        "step_id": last_emitted_step_id,
                        "status": "completed",
                        "usage": usage_payload,
                        "resumed": True,
                    },
                )
            else:
                state_event = emit_state("error")
                if state_event is not None:
                    yield state_event
                yield sse_event(
                    "error",
                    {
                        **sse_error_payload(
                            task_id=task_id,
                            step_id=last_emitted_step_id,
                            message="Task ended with failed status.",
                            code="task_failed",
                            fatal=True,
                            retry_count=0,
                        ),
                        "session_id": str(task.get("session_id", "")) or session_id,
                        "resumed": True,
                    },
                )
            return

        phase_event = emit_state("streaming" if status == "running" else status)
        if phase_event is not None:
            yield phase_event

        now = monotonic()
        if now - last_heartbeat_ts >= heartbeat_interval_sec:
            yield sse_event(
                "heartbeat",
                {
                    "task_id": task_id,
                    "ts": datetime.now().isoformat(),
                    "resumed": True,
                },
            )
            last_heartbeat_ts = now
        await asyncio.sleep(poll_delay_sec)


class TaskCreateRequest(BaseModel):
    user_input: str = Field(min_length=1)
    session_id: str | None = None


class TaskCreateResponse(BaseModel):
    task_id: str
    session_id: str
    status: str
    status_normalized: str
    status_label: str
    status_rank: int


class TaskResponse(BaseModel):
    id: str
    session_id: str
    prompt: str
    status: str
    status_normalized: str
    status_label: str
    status_rank: int
    trace_json: str | None = None
    usage_json: str | None = None
    created_at: str
    updated_at: str


class TaskCancelResponse(BaseModel):
    task_id: str
    previous_status: str
    status: str
    status_normalized: str
    status_label: str
    status_rank: int
    already_terminal: bool


class TaskTraceResponse(BaseModel):
    task_id: str
    steps: list[TraceStep]
    status: str
    status_normalized: str
    status_label: str
    status_rank: int


class TaskTraceDeltaResponse(BaseModel):
    task_id: str
    steps: list[TraceStep]
    next_cursor: int
    has_more: bool
    server_time: str = Field(description="服务端生成响应时间（ISO8601）")
    lag_seq: int = Field(description="当前游标到最新 seq 的差值")
    dropped: bool = Field(description="是否发生服务端丢步（当前实现恒为 false）")


def _with_status_meta(item: dict) -> dict:
    status = str(item.get("status", ""))
    return {
        **item,
        "status_normalized": normalize_task_status(status),
        "status_label": task_status_label(status),
        "status_rank": task_status_rank(status),
    }


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int = Field(description="符合条件的任务总数（全局或指定 session_id）")
    limit: int
    offset: int
    has_more: bool = Field(description="是否仍有下一页")


class TaskUsageSummaryResponse(BaseModel):
    tasks_total: int
    tasks_with_usage: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_estimate: float
    avg_total_tokens: float | None = None
    avg_cost_estimate: float | None = None


class TaskUsageTrendPoint(BaseModel):
    day: str
    tasks_with_usage: int
    total_tokens: int
    cost_estimate: float


class TaskUsageBySessionRow(BaseModel):
    session_id: str
    session_title: str | None = None
    tasks_with_usage: int
    total_tokens: int
    cost_estimate: float
    last_task_at: str | None = None


class TaskUsageTopTaskRow(BaseModel):
    task_id: str
    session_id: str
    session_title: str | None = None
    prompt_excerpt: str
    total_tokens: int
    cost_estimate: float
    created_at: str
    updated_at: str


class TaskUsageDashboardResponse(BaseModel):
    window_days: int
    summary: TaskUsageSummaryResponse
    trend: list[TaskUsageTrendPoint]
    by_session: list[TaskUsageBySessionRow]
    top_tasks: list[TaskUsageTopTaskRow]


class TaskExportMessage(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class TaskExportRagChunk(BaseModel):
    step_id: str
    knowledge_base_id: str | None = None
    content: str


class TaskExportTask(BaseModel):
    id: str
    session_id: str
    prompt: str
    status: str
    status_normalized: str
    status_label: str
    status_rank: int
    created_at: str
    updated_at: str


class TaskExportTrace(BaseModel):
    step_count: int
    rag_hit_count: int
    rag_knowledge_base_ids: list[str]
    rag_chunks: list[TaskExportRagChunk]
    steps: list[TraceStep]


class TaskExportJsonResponse(BaseModel):
    version: str
    exported_at: str
    task: TaskExportTask
    usage: dict[str, object] | None = None
    messages: list[TaskExportMessage]
    trace: TaskExportTrace


def _normalize_filename_part(raw: str, fallback: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw).strip("-._")
    return normalized or fallback


def _build_task_export_filename(task: dict, ext: str) -> str:
    task_id_part = _normalize_filename_part(str(task.get("id", "")), "task")
    session_id_part = _normalize_filename_part(
        str(task.get("session_id", "")),
        "session",
    )
    return f"insightagent-task-{task_id_part}-session-{session_id_part}.{ext}"


def _parse_task_usage_blob(task: dict) -> dict[str, object] | None:
    usage_raw = task.get("usage_json")
    if not isinstance(usage_raw, str) or not usage_raw.strip():
        return None
    try:
        parsed = json.loads(usage_raw)
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _collect_rag_export(steps: list[TraceStep]) -> tuple[int, list[str], list[TaskExportRagChunk]]:
    rag_hit_count = 0
    rag_knowledge_base_ids: list[str] = []
    rag_chunks: list[TaskExportRagChunk] = []
    seen_kb_ids: set[str] = set()

    for step in steps:
        rag_meta = step.meta.rag if step.meta else None
        if not isinstance(rag_meta, dict):
            continue
        raw_chunks = rag_meta.get("chunks")
        kb_id = rag_meta.get("knowledge_base_id")
        kb_id_text = kb_id.strip() if isinstance(kb_id, str) and kb_id.strip() else None
        if kb_id_text and kb_id_text not in seen_kb_ids:
            seen_kb_ids.add(kb_id_text)
            rag_knowledge_base_ids.append(kb_id_text)
        if isinstance(raw_chunks, list):
            for chunk in raw_chunks:
                if not isinstance(chunk, str):
                    continue
                chunk_text = chunk.strip()
                if not chunk_text:
                    continue
                rag_hit_count += 1
                rag_chunks.append(
                    TaskExportRagChunk(
                        step_id=step.id,
                        knowledge_base_id=kb_id_text,
                        content=chunk_text,
                    ),
                )

    return rag_hit_count, rag_knowledge_base_ids, rag_chunks


def _build_task_export_payload(task: dict, user_id: str) -> TaskExportJsonResponse:
    task_id = str(task["id"])
    raw_steps = get_task_trace(task_id, user_id)
    parsed_steps = parse_trace_steps(raw_steps)
    rag_hit_count, rag_knowledge_base_ids, rag_chunks = _collect_rag_export(parsed_steps)
    return TaskExportJsonResponse(
        version="1.0",
        exported_at=datetime.now().isoformat(),
        task=TaskExportTask(**_with_status_meta(task)),
        usage=_parse_task_usage_blob(task),
        messages=[
            TaskExportMessage(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"],
            )
            for row in get_task_messages(task_id, user_id)
        ],
        trace=TaskExportTrace(
            step_count=len(parsed_steps),
            rag_hit_count=rag_hit_count,
            rag_knowledge_base_ids=rag_knowledge_base_ids,
            rag_chunks=rag_chunks,
            steps=parsed_steps,
        ),
    )


def _append_fenced_block(lines: list[str], content: str, language: str = "text") -> None:
    text = content.rstrip("\n")
    fence = "```"
    if "```" in text:
        fence = "~~~"
    lines.append(f"{fence}{language}".rstrip())
    lines.append(text)
    lines.append(fence)


def _build_task_export_markdown(payload: TaskExportJsonResponse) -> str:
    lines: list[str] = []
    lines.append("# InsightAgent Task Export")
    lines.append("")
    lines.append(f"- Exported At: {payload.exported_at}")
    lines.append(f"- Task ID: {payload.task.id}")
    lines.append(f"- Session ID: {payload.task.session_id}")
    lines.append(
        f"- Status: {payload.task.status} ({payload.task.status_normalized}, rank={payload.task.status_rank})",
    )
    lines.append(f"- Created At: {payload.task.created_at}")
    lines.append(f"- Updated At: {payload.task.updated_at}")
    lines.append("")
    lines.append("## Prompt")
    lines.append("")
    _append_fenced_block(lines, payload.task.prompt or "", "text")
    lines.append("")

    if payload.usage:
        lines.append("## Usage")
        lines.append("")
        _append_fenced_block(
            lines,
            json.dumps(payload.usage, ensure_ascii=False, indent=2),
            "json",
        )
        lines.append("")

    lines.append("## Messages")
    lines.append("")
    if not payload.messages:
        lines.append("_No task-linked messages_")
        lines.append("")
    else:
        for idx, msg in enumerate(payload.messages, start=1):
            lines.append(f"### {idx}. {msg.role.upper()} · {msg.created_at}")
            lines.append("")
            _append_fenced_block(lines, msg.content or "", "text")
            lines.append("")

    lines.append("## Trace Summary")
    lines.append("")
    lines.append(f"- Step Count: {payload.trace.step_count}")
    lines.append(f"- RAG Hit Count: {payload.trace.rag_hit_count}")
    if payload.trace.rag_knowledge_base_ids:
        lines.append(
            "- RAG Knowledge Bases: "
            + ", ".join(payload.trace.rag_knowledge_base_ids),
        )
    else:
        lines.append("- RAG Knowledge Bases: (none)")
    lines.append("")

    if payload.trace.rag_chunks:
        lines.append("## RAG Chunks")
        lines.append("")
        for idx, chunk in enumerate(payload.trace.rag_chunks, start=1):
            kb = chunk.knowledge_base_id or "default"
            lines.append(f"### {idx}. step={chunk.step_id} · kb={kb}")
            lines.append("")
            _append_fenced_block(lines, chunk.content, "text")
            lines.append("")

    lines.append("## Trace Steps")
    lines.append("")
    if not payload.trace.steps:
        lines.append("_No trace steps_")
        lines.append("")
    else:
        for idx, step in enumerate(payload.trace.steps, start=1):
            seq = step.seq if step.seq is not None else idx
            lines.append(f"### {idx}. seq={seq} · {step.type} · {step.id}")
            lines.append("")
            if step.meta is not None:
                _append_fenced_block(
                    lines,
                    json.dumps(
                        step.meta.model_dump(exclude_none=True),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "json",
                )
                lines.append("")
            _append_fenced_block(lines, step.content or "", "text")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


@router.post("", response_model=TaskCreateResponse)
def create_task_entry(
    payload: TaskCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> TaskCreateResponse:
    user_id = str(current_user["id"])
    try:
        resolved_session_id = ensure_session(
            prompt=payload.user_input,
            user_id=user_id,
            session_id=payload.session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    task_id = create_task(
        session_id=resolved_session_id,
        prompt=payload.user_input,
        user_id=user_id,
        status="pending",
    )
    create_message(
        session_id=resolved_session_id,
        user_id=user_id,
        task_id=task_id,
        role="user",
        content=payload.user_input,
    )
    safe_record_audit_event(
        user_id=user_id,
        event_type="task_create",
        detail={
            "session_id": resolved_session_id,
            "task_id": task_id,
            "prompt_length": len(payload.user_input.strip()),
        },
    )
    return TaskCreateResponse(
        task_id=task_id,
        session_id=resolved_session_id,
        status="pending",
        status_normalized=normalize_task_status("pending"),
        status_label=task_status_label("pending"),
        status_rank=task_status_rank("pending"),
    )


@router.get("", response_model=TaskListResponse)
def get_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(
        default=0,
        ge=0,
        le=50_000,
        description="跳过前 offset 条（与 limit 组合做分页）",
    ),
    session_id: str | None = Query(
        default=None,
        description="仅返回该会话下的任务；会话须存在，否则 404",
    ),
    current_user: dict = Depends(get_current_user),
) -> TaskListResponse:
    user_id = str(current_user["id"])
    if session_id is not None and session_id.strip():
        sid = session_id.strip()
        if get_session(sid, user_id) is None:
            raise HTTPException(status_code=404, detail="Session not found")
        tasks = list_tasks(user_id=user_id, limit=limit, session_id=sid, offset=offset)
        total = count_tasks(user_id, sid)
    else:
        tasks = list_tasks(user_id=user_id, limit=limit, offset=offset)
        total = count_tasks(user_id, None)
    n = len(tasks)
    return TaskListResponse(
        items=[TaskResponse(**_with_status_meta(task)) for task in tasks],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + n < total,
    )


@router.get("/usage/summary", response_model=TaskUsageSummaryResponse)
def get_tasks_usage_summary_route(
    session_id: str | None = Query(
        default=None,
        description="可选：按会话聚合；会话不存在时返回 404",
    ),
    current_user: dict = Depends(get_current_user),
) -> TaskUsageSummaryResponse:
    user_id = str(current_user["id"])
    sid = session_id.strip() if session_id else None
    if sid and get_session(sid, user_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    raw = get_tasks_usage_summary(user_id, sid)
    return TaskUsageSummaryResponse(**raw)


@router.get("/usage/dashboard", response_model=TaskUsageDashboardResponse)
def get_tasks_usage_dashboard_route(
    session_id: str | None = Query(
        default=None,
        description="可选：按会话聚合；会话不存在时返回 404",
    ),
    window_days: int = Query(
        default=14,
        ge=1,
        le=90,
        description="趋势窗口天数（含今天）",
    ),
    top_sessions: int = Query(
        default=8,
        ge=1,
        le=30,
        description="会话榜返回条数",
    ),
    top_tasks: int = Query(
        default=12,
        ge=1,
        le=50,
        description="任务榜返回条数",
    ),
    current_user: dict = Depends(get_current_user),
) -> TaskUsageDashboardResponse:
    user_id = str(current_user["id"])
    sid = session_id.strip() if session_id else None
    if sid and get_session(sid, user_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    payload = get_tasks_usage_dashboard(
        user_id,
        session_id=sid,
        window_days=window_days,
        top_sessions=top_sessions,
        top_tasks=top_tasks,
    )
    return TaskUsageDashboardResponse(
        window_days=int(payload["window_days"]),
        summary=TaskUsageSummaryResponse(**payload["summary"]),
        trend=[TaskUsageTrendPoint(**row) for row in payload["trend"]],
        by_session=[TaskUsageBySessionRow(**row) for row in payload["by_session"]],
        top_tasks=[TaskUsageTopTaskRow(**row) for row in payload["top_tasks"]],
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task_detail(
    task_id: str,
    current_user: dict = Depends(get_current_user),
) -> TaskResponse:
    task = get_task(task_id, str(current_user["id"]))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**_with_status_meta(task))


@router.post("/{task_id}/cancel", response_model=TaskCancelResponse)
def cancel_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
) -> TaskCancelResponse:
    user_id = str(current_user["id"])
    task = get_task(task_id, user_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    previous_status = str(task.get("status", ""))
    normalized_prev = normalize_task_status(previous_status)
    already_terminal = normalized_prev in {"completed", "failed", "cancelled", "timed_out"}

    if not already_terminal:
        update_task_status(task_id=task_id, status="cancelled", user_id=user_id)
        task = get_task(task_id, user_id) or {**task, "status": "cancelled"}

    current_status = str(task.get("status", ""))
    safe_record_audit_event(
        user_id=user_id,
        event_type="task_cancel",
        detail={
            "task_id": task_id,
            "session_id": str(task.get("session_id", "")) or None,
            "previous_status": previous_status,
            "status": current_status,
            "already_terminal": already_terminal,
        },
    )
    return TaskCancelResponse(
        task_id=task_id,
        previous_status=previous_status,
        status=current_status,
        status_normalized=normalize_task_status(current_status),
        status_label=task_status_label(current_status),
        status_rank=task_status_rank(current_status),
        already_terminal=already_terminal,
    )


@router.get("/{task_id}/export/json", response_model=TaskExportJsonResponse)
def export_task_json(
    task_id: str,
    response: Response,
    download: bool = Query(
        default=False,
        description="为 true 时附加 Content-Disposition 附件头",
    ),
    current_user: dict = Depends(get_current_user),
) -> TaskExportJsonResponse:
    user_id = str(current_user["id"])
    task = get_task(task_id, user_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    payload = _build_task_export_payload(task, user_id)
    if download:
        response.headers["Content-Disposition"] = (
            f'attachment; filename="{_build_task_export_filename(task, "json")}"'
        )
    return payload


@router.get("/{task_id}/export/markdown", response_class=PlainTextResponse)
def export_task_markdown(
    task_id: str,
    download: bool = Query(
        default=False,
        description="为 true 时附加 Content-Disposition 附件头",
    ),
    current_user: dict = Depends(get_current_user),
) -> PlainTextResponse:
    user_id = str(current_user["id"])
    task = get_task(task_id, user_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    payload = _build_task_export_payload(task, user_id)
    markdown = _build_task_export_markdown(payload)
    headers: dict[str, str] = {}
    if download:
        headers["Content-Disposition"] = (
            f'attachment; filename="{_build_task_export_filename(task, "md")}"'
        )
    return PlainTextResponse(
        markdown,
        headers=headers,
        media_type="text/markdown; charset=utf-8",
    )


@router.get("/{task_id}/trace", response_model=TaskTraceResponse)
def get_task_trace_detail(
    task_id: str,
    current_user: dict = Depends(get_current_user),
) -> TaskTraceResponse:
    user_id = str(current_user["id"])
    task = get_task(task_id, user_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    raw_steps = get_task_trace(task_id, user_id)
    status = str(task["status"])
    return TaskTraceResponse(
        task_id=task_id,
        steps=parse_trace_steps(raw_steps),
        status=status,
        status_normalized=normalize_task_status(status),
        status_label=task_status_label(status),
        status_rank=task_status_rank(status),
    )


@router.get("/{task_id}/trace/delta", response_model=TaskTraceDeltaResponse)
def get_task_trace_delta_detail(
    task_id: str,
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(
        default=200,
        ge=1,
        le=500,
        description="单次返回的最大 delta step 数",
    ),
    current_user: dict = Depends(get_current_user),
) -> TaskTraceDeltaResponse:
    task = get_task(task_id, str(current_user["id"]))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    steps, next_cursor, has_more = get_task_trace_delta_from_task(
        task,
        after_seq=after_seq,
        limit=limit,
    )
    parsed_steps = parse_trace_steps(steps)
    lag_seq = max(0, _latest_seq_from_task(task) - next_cursor)
    return TaskTraceDeltaResponse(
        task_id=task_id,
        steps=parsed_steps,
        next_cursor=next_cursor,
        has_more=has_more,
        server_time=datetime.now().isoformat(),
        lag_seq=lag_seq,
        dropped=False,
    )


@router.get(
    "/{task_id}/stream",
    summary="任务 SSE 流",
    description=(
        "返回 `text/event-stream`；`event: trace` 的 `data.step` 与 REST "
        "`GET /api/tasks/{task_id}/trace` 中的 `TraceStep` 同构。"
        "完整事件约定见仓库根目录 `README.md` 的 SSE 与 TraceStep 契约章节。"
    ),
    response_class=StreamingResponse,
)
def stream_task_detail(
    task_id: str,
    request: Request,
    after_seq: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    user_id = str(current_user["id"])
    task = get_task(task_id, user_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] not in {"pending", "running"}:
        raise HTTPException(
            status_code=409,
            detail="Task stream can only be opened for pending/running tasks",
        )

    if task["status"] == "running":
        header_cursor = _parse_last_event_id(request.headers.get("Last-Event-ID"))
        resume_cursor = max(after_seq, header_cursor or 0)
        return StreamingResponse(
            stream_running_task_reconnect(
                task_id,
                user_id=user_id,
                after_seq=resume_cursor,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    return StreamingResponse(
        stream_task_execution(
            task_id=task_id,
            session_id=task["session_id"],
            user_id=user_id,
            prompt=task["prompt"],
            persist_user_message=False,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
