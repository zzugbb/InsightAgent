from typing import NoReturn
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.api.deps import get_current_user
from app.api.routes.tasks import TaskCreateResponse
from app.services.chat_persistence_service import get_task, get_task_create_response_summary
from app.services.task_checkpoint_service import checkpoint_candidates, load_trace
from app.services.task_rerun_service import TaskRerunError, create_task_rerun, get_task_reruns

router = APIRouter()


class TaskRerunRequest(BaseModel):
    idempotency_key: UUID = Field(default_factory=uuid4)
    checkpoint_step_id: UUID | None = None
    user_input: str | None = Field(default=None, min_length=1, max_length=64_000)

    @field_validator("user_input")
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("user_input must be nonblank")
        return value.strip() if value is not None else None


class TaskRerunResponse(TaskCreateResponse):
    parent_task_id: str | None = None


class TaskRerunChild(BaseModel):
    task_id: str
    session_id: str
    status: str
    created_at: str


class TaskRerunListResponse(BaseModel):
    task_id: str
    is_rerun: bool
    parent_task_id: str | None
    items: list[TaskRerunChild]
    total: int
    limit: int
    offset: int
    has_more: bool


def translate_error(exc: TaskRerunError) -> NoReturn:
    raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


@router.post("/{task_id}/reruns", response_model=TaskRerunResponse, status_code=201)
def post_rerun(task_id: UUID, payload: TaskRerunRequest,
               current_user: dict = Depends(get_current_user)) -> TaskRerunResponse:
    try:
        branch = create_task_rerun(user_id=str(current_user["id"]), parent_task_id=str(task_id),
                                   user_input=payload.user_input, idempotency_key=str(payload.idempotency_key),
                                   **({"checkpoint_step_id": str(payload.checkpoint_step_id)}
                                      if payload.checkpoint_step_id is not None else {}))
    except TaskRerunError as exc:
        translate_error(exc)
    summary = get_task_create_response_summary(task_id=branch["task_id"], session_id=branch["session_id"],
                                                status=branch["status"])
    return TaskRerunResponse(**summary, parent_task_id=branch["parent_task_id"])


@router.get("/{task_id}/reruns", response_model=TaskRerunListResponse)
def get_reruns(task_id: UUID, limit: int = Query(default=20, ge=1, le=100),
               offset: int = Query(default=0, ge=0),
               current_user: dict = Depends(get_current_user)) -> TaskRerunListResponse:
    try:
        return TaskRerunListResponse(**get_task_reruns(user_id=str(current_user["id"]),
                                                     task_id=str(task_id), limit=limit, offset=offset))
    except TaskRerunError as exc:
        translate_error(exc)


class TaskCheckpointCandidate(BaseModel):
    step_id: str
    index: int
    tool_name: str
    reused_steps: int


class TaskCheckpointListResponse(BaseModel):
    task_id: str
    experimental: bool = True
    items: list[TaskCheckpointCandidate]


@router.get("/{task_id}/checkpoints", response_model=TaskCheckpointListResponse)
def get_checkpoints(task_id: UUID, current_user: dict = Depends(get_current_user)) -> TaskCheckpointListResponse:
    task = get_task(str(task_id), str(current_user["id"]))
    if task is None:
        raise HTTPException(status_code=404, detail="task_not_found")
    return TaskCheckpointListResponse(task_id=str(task_id), items=checkpoint_candidates(load_trace(task.get("trace_json"))))
