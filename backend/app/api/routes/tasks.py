from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from app.schemas.trace import TraceStep, parse_trace_steps
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
from app.services.chat_execution_service import stream_task_execution


router = APIRouter()


class TaskCreateRequest(BaseModel):
    user_input: str = Field(min_length=1)
    session_id: str | None = None


class TaskCreateResponse(BaseModel):
    task_id: str
    session_id: str
    status: str


class TaskResponse(BaseModel):
    id: str
    session_id: str
    prompt: str
    status: str
    trace_json: str | None = None
    usage_json: str | None = None
    created_at: str
    updated_at: str


class TaskTraceResponse(BaseModel):
    task_id: str
    steps: list[TraceStep]
    status: str


class TaskTraceDeltaResponse(BaseModel):
    task_id: str
    steps: list[TraceStep]
    next_cursor: int
    has_more: bool


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
        items=[TaskResponse(**task) for task in tasks],
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
    return TaskResponse(**task)


@router.get("/{task_id}/trace", response_model=TaskTraceResponse)
def get_task_trace_detail(task_id: str) -> TaskTraceResponse:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    raw_steps = get_task_trace(task_id)
    return TaskTraceResponse(
        task_id=task_id,
        steps=parse_trace_steps(raw_steps),
        status=task["status"],
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
    if task["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail="Task stream can only be opened for pending tasks",
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
