import json
from datetime import datetime
from uuid import uuid4
from collections.abc import Iterator

from fastapi import APIRouter
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

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


def _sse_event(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _chat_stream(prompt: str, session_id: str | None) -> Iterator[str]:
    resolved_session_id = ensure_session(prompt=prompt, session_id=session_id)
    task_id = create_task(session_id=resolved_session_id, prompt=prompt)
    create_message(
        session_id=resolved_session_id,
        task_id=task_id,
        role="user",
        content=prompt,
    )
    thought_step_id = str(uuid4())
    final_step_id = str(uuid4())
    trace_steps: list[dict[str, object]] = []

    try:
        provider = get_llm_provider()
        result = provider.generate(prompt)
        completion_chunks = list(provider.stream_generate(prompt))
        trace_steps = [
            {
                "id": thought_step_id,
                "type": "thought",
                "content": f"Mock provider is preparing a response for: {prompt.strip()}",
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

        yield _sse_event(
            "start",
            {
                "session_id": resolved_session_id,
                "task_id": task_id,
                "provider": result.provider,
                "model": result.model,
            },
        )
        yield _sse_event(
            "state",
            {
                "task_id": task_id,
                "phase": "thinking",
            },
        )
        yield _sse_event(
            "trace",
            {
                "task_id": task_id,
                "step_id": thought_step_id,
                "step": trace_steps[0],
            },
        )
        yield _sse_event(
            "trace",
            {
                "task_id": task_id,
                "step_id": final_step_id,
                "step": {
                    **trace_steps[1],
                    "content": "",
                },
            },
        )
        yield _sse_event(
            "heartbeat",
            {
                "task_id": task_id,
                "ts": datetime.now().isoformat(),
            },
        )
        yield _sse_event(
            "state",
            {
                "task_id": task_id,
                "phase": "streaming",
            },
        )
        for chunk in completion_chunks:
            yield _sse_event(
                "token",
                {
                    "task_id": task_id,
                    "step_id": final_step_id,
                    "delta": chunk,
                },
            )
        create_message(
            session_id=resolved_session_id,
            task_id=task_id,
            role="assistant",
            content=result.content,
        )
        complete_task(task_id=task_id, trace_steps=trace_steps)
        yield _sse_event(
            "done",
            {
                "session_id": resolved_session_id,
                "task_id": task_id,
                "step_id": final_step_id,
                "status": "completed",
                "usage": {
                    "prompt_tokens": None,
                    "completion_tokens": len(completion_chunks),
                    "cost_estimate": None,
                },
            },
        )
    except Exception as exc:
        complete_task(task_id=task_id, trace_steps=trace_steps, status="failed")
        yield _sse_event(
            "state",
            {
                "task_id": task_id,
                "phase": "error",
            },
        )
        yield _sse_event(
            "error",
            {
                "task_id": task_id,
                "step_id": final_step_id,
                "message": str(exc),
                "retryable": False,
            },
        )


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


@router.post("/stream")
def stream_chat(payload: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _chat_stream(payload.prompt, payload.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
