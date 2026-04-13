import json
from collections.abc import Iterator
from datetime import datetime
from time import monotonic, sleep

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from app.schemas.trace import TraceStep, parse_trace_steps
from app.services.chat_execution_service import sse_event, stream_task_execution
from app.services.chat_persistence_service import (
    count_tasks,
    create_message,
    create_task,
    ensure_session,
    get_session,
    get_tasks_usage_summary,
    get_task,
    get_task_trace,
    get_task_trace_delta,
    list_tasks,
)
from app.services.task_status_service import (
    normalize_task_status,
    task_status_label,
    task_status_rank,
)


router = APIRouter()


def stream_running_task_reconnect(task_id: str) -> Iterator[str]:
    cursor = 0
    poll_delay_fast_sec = 0.3
    poll_delay_max_sec = 2.0
    poll_delay_sec = poll_delay_fast_sec
    heartbeat_interval_sec = 2.0
    last_heartbeat_ts = monotonic()
    last_emitted_step_id: str | None = None
    last_phase: str | None = None

    def emit_state(phase: str) -> str | None:
        nonlocal last_phase
        if phase == last_phase:
            return None
        last_phase = phase
        return sse_event("state", {"task_id": task_id, "phase": phase})

    first_task = get_task(task_id)
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
        task = get_task(task_id)
        if task is None:
            yield sse_event(
                "error",
                {
                    "task_id": task_id,
                    "message": "Task not found during reconnect stream.",
                    "fatal": True,
                    "retryCount": 0,
                },
            )
            return

        steps, next_cursor, _ = get_task_trace_delta(
            task_id=task_id,
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
                full_steps = get_task_trace(task_id)
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
                        "session_id": str(task.get("session_id", "")) or session_id,
                        "task_id": task_id,
                        "step_id": last_emitted_step_id,
                        "message": "Task ended with failed status.",
                        "fatal": True,
                        "retryCount": 0,
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
        sleep(poll_delay_sec)


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


@router.post("", response_model=TaskCreateResponse)
def create_task_entry(payload: TaskCreateRequest) -> TaskCreateResponse:
    resolved_session_id = ensure_session(
        prompt=payload.user_input,
        session_id=payload.session_id,
    )
    task_id = create_task(
        session_id=resolved_session_id,
        prompt=payload.user_input,
        status="pending",
    )
    create_message(
        session_id=resolved_session_id,
        task_id=task_id,
        role="user",
        content=payload.user_input,
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
) -> TaskListResponse:
    if session_id is not None and session_id.strip():
        sid = session_id.strip()
        if get_session(sid) is None:
            raise HTTPException(status_code=404, detail="Session not found")
        tasks = list_tasks(limit=limit, session_id=sid, offset=offset)
        total = count_tasks(sid)
    else:
        tasks = list_tasks(limit=limit, offset=offset)
        total = count_tasks(None)
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
) -> TaskUsageSummaryResponse:
    sid = session_id.strip() if session_id else None
    if sid and get_session(sid) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    raw = get_tasks_usage_summary(sid)
    return TaskUsageSummaryResponse(**raw)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task_detail(task_id: str) -> TaskResponse:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**_with_status_meta(task))


@router.get("/{task_id}/trace", response_model=TaskTraceResponse)
def get_task_trace_detail(task_id: str) -> TaskTraceResponse:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    raw_steps = get_task_trace(task_id)
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
) -> TaskTraceDeltaResponse:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    steps, next_cursor, has_more = get_task_trace_delta(
        task_id=task_id,
        after_seq=after_seq,
        limit=limit,
    )
    return TaskTraceDeltaResponse(
        task_id=task_id,
        steps=parse_trace_steps(steps),
        next_cursor=next_cursor,
        has_more=has_more,
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
def stream_task_detail(task_id: str) -> StreamingResponse:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] not in {"pending", "running"}:
        raise HTTPException(
            status_code=409,
            detail="Task stream can only be opened for pending/running tasks",
        )

    if task["status"] == "running":
        return StreamingResponse(
            stream_running_task_reconnect(task_id),
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
            prompt=task["prompt"],
            persist_user_message=False,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
