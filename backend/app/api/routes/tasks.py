from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.chat_persistence_service import (
    get_task,
    get_task_trace,
    get_task_trace_delta,
)


router = APIRouter()


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
    steps: list[dict]
    status: str


class TaskTraceDeltaResponse(BaseModel):
    task_id: str
    steps: list[dict]
    next_cursor: int
    has_more: bool


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
    return TaskTraceResponse(
        task_id=task_id,
        steps=get_task_trace(task_id),
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
        steps=steps,
        next_cursor=next_cursor,
        has_more=has_more,
    )
