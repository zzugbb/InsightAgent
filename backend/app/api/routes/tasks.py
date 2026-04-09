from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from app.schemas.trace import TraceStep, parse_trace_steps
from app.services.chat_persistence_service import (
    create_message,
    create_task,
    ensure_session,
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
def get_tasks(limit: int = Query(default=20, ge=1, le=100)) -> TaskListResponse:
    tasks = list_tasks(limit=limit)
    return TaskListResponse(
        items=[TaskResponse(**task) for task in tasks],
    )


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
) -> TaskTraceDeltaResponse:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    steps, next_cursor, has_more = get_task_trace_delta(
        task_id=task_id,
        after_seq=after_seq,
    )
    return TaskTraceDeltaResponse(
        task_id=task_id,
        steps=parse_trace_steps(steps),
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/{task_id}/stream")
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
