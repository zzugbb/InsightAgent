import json
from collections.abc import Iterator
from datetime import datetime
from uuid import uuid4

from app.services.chat_persistence_service import (
    complete_task,
    create_message,
    update_task_status,
)
from app.services.chroma_memory_service import try_append_task_memory
from app.services.provider_service import get_llm_provider


def sse_event(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream_task_execution(
    *,
    task_id: str,
    session_id: str,
    prompt: str,
    persist_user_message: bool = False,
) -> Iterator[str]:
    thought_step_id = str(uuid4())
    tool_step_id = str(uuid4())
    rag_step_id = str(uuid4())
    final_step_id = str(uuid4())
    trace_steps: list[dict[str, object]] = []

    if persist_user_message:
        create_message(
            session_id=session_id,
            task_id=task_id,
            role="user",
            content=prompt,
        )

    update_task_status(task_id=task_id, status="running")

    try:
        provider = get_llm_provider()
        result = provider.generate(prompt)
        completion_chunks = list(provider.stream_generate(prompt))
        preview = prompt.strip()[:120]
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
                "id": tool_step_id,
                "type": "action",
                "content": "Mock tool call (no external I/O in mock mode).",
                "meta": {
                    "model": result.model,
                    "step_type": "tool_call",
                    "tool": {
                        "name": "mock_plan",
                        "input": {"prompt_preview": preview},
                        "output": {"echo": True},
                        "status": "done",
                    },
                },
            },
            {
                "id": rag_step_id,
                "type": "thought",
                "content": "Retrieved snippets from mock knowledge base.",
                "meta": {
                    "model": result.model,
                    "step_type": "rag_retrieval",
                    "rag": {
                        "chunks": [
                            "(mock) Context line 1 for this session.",
                            "(mock) Context line 2.",
                        ],
                        "knowledge_base_id": "mock_kb",
                    },
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

        yield sse_event(
            "start",
            {
                "session_id": session_id,
                "task_id": task_id,
                "provider": result.provider,
                "model": result.model,
            },
        )
        yield sse_event(
            "state",
            {
                "task_id": task_id,
                "phase": "thinking",
            },
        )
        yield sse_event(
            "trace",
            {
                "task_id": task_id,
                "step_id": thought_step_id,
                "step": trace_steps[0],
            },
        )
        yield sse_event(
            "trace",
            {
                "task_id": task_id,
                "step_id": tool_step_id,
                "step": trace_steps[1],
            },
        )
        yield sse_event(
            "trace",
            {
                "task_id": task_id,
                "step_id": rag_step_id,
                "step": trace_steps[2],
            },
        )
        yield sse_event(
            "trace",
            {
                "task_id": task_id,
                "step_id": final_step_id,
                "step": {
                    **trace_steps[3],
                    "content": "",
                },
            },
        )
        yield sse_event(
            "heartbeat",
            {
                "task_id": task_id,
                "ts": datetime.now().isoformat(),
            },
        )
        yield sse_event(
            "state",
            {
                "task_id": task_id,
                "phase": "streaming",
            },
        )
        for chunk in completion_chunks:
            yield sse_event(
                "token",
                {
                    "task_id": task_id,
                    "step_id": final_step_id,
                    "delta": chunk,
                },
            )
        create_message(
            session_id=session_id,
            task_id=task_id,
            role="assistant",
            content=result.content,
        )
        complete_task(task_id=task_id, trace_steps=trace_steps)
        try_append_task_memory(
            session_id,
            task_id=task_id,
            user_prompt=prompt,
            assistant_excerpt=result.content,
        )
        yield sse_event(
            "done",
            {
                "session_id": session_id,
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
        yield sse_event(
            "state",
            {
                "task_id": task_id,
                "phase": "error",
            },
        )
        yield sse_event(
            "error",
            {
                "task_id": task_id,
                "step_id": final_step_id,
                "message": str(exc),
                "retryable": False,
            },
        )
