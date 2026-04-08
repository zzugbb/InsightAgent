from fastapi import APIRouter
from pydantic import BaseModel, Field
from uuid import uuid4

from app.services.chat_persistence_service import (
    complete_task,
    create_message,
    create_task,
    ensure_session,
)
from app.services.provider_service import get_llm_provider


router = APIRouter()


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)
    session_id: str | None = None


class ChatResponse(BaseModel):
    content: str
    provider: str
    model: str
    mode: str
    session_id: str
    task_id: str


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    provider = get_llm_provider()
    result = provider.generate(payload.prompt)
    resolved_session_id = ensure_session(
        prompt=payload.prompt,
        session_id=payload.session_id,
    )
    task_id = create_task(session_id=resolved_session_id, prompt=payload.prompt)
    thought_step_id = str(uuid4())
    final_step_id = str(uuid4())
    trace_steps = [
        {
            "id": thought_step_id,
            "type": "thought",
            "content": f"Mock provider is preparing a response for: {payload.prompt.strip()}",
            "meta": {
                "model": result.model,
                "step_type": "planning",
            },
        },
        {
            "id": final_step_id,
            "type": "observation",
            "content": result.content,
            "meta": {
                "model": result.model,
                "step_type": "final_answer",
                "tokens": None,
                "cost_estimate": None,
            },
        },
    ]
    create_message(
        session_id=resolved_session_id,
        task_id=task_id,
        role="user",
        content=payload.prompt,
    )
    create_message(
        session_id=resolved_session_id,
        task_id=task_id,
        role="assistant",
        content=result.content,
    )
    complete_task(task_id=task_id, trace_steps=trace_steps)
    return ChatResponse(
        content=result.content,
        provider=result.provider,
        model=result.model,
        mode="json",
        session_id=resolved_session_id,
        task_id=task_id,
    )
