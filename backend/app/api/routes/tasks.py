from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.chat_persistence_service import get_task, get_task_trace


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
    )
