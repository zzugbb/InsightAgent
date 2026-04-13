import json
import re
from ast import Add, BinOp, Div, Expression, Mod, Mult, Pow, Sub, UAdd, USub, UnaryOp, parse
from collections.abc import Iterator
from datetime import datetime
from time import monotonic
from uuid import uuid4

from app.config import get_settings
from app.services.chat_persistence_service import (
    complete_task,
    create_message,
    update_task_status,
    update_task_trace_steps,
)
from app.services.chroma_memory_service import try_append_task_memory
from app.services.provider_service import get_llm_provider


class MockToolExecutionError(RuntimeError):
    def __init__(self, message: str, *, fatal: bool):
        super().__init__(message)
        self.fatal = fatal


def sse_event(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _extract_calc_expression(prompt: str) -> str | None:
    tagged = re.search(r"\[calc:(.+?)\]", prompt, flags=re.IGNORECASE)
    if tagged:
        expr = tagged.group(1).strip()
        return expr or None

    plain = re.search(r"(?:计算|calc)\s*[:：]?\s*([0-9+\-*/().%\s]{3,})", prompt)
    if plain:
        expr = plain.group(1).strip()
        return expr or None

    return None


def _safe_eval_expression(expr: str) -> float:
    tree = parse(expr, mode="eval")

    def _eval(node: object) -> float:
        if isinstance(node, Expression):
            return _eval(node.body)
        if isinstance(node, BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, Add):
                return left + right
            if isinstance(node.op, Sub):
                return left - right
            if isinstance(node.op, Mult):
                return left * right
            if isinstance(node.op, Div):
                return left / right
            if isinstance(node.op, Mod):
                return left % right
            if isinstance(node.op, Pow):
                return left**right
            raise ValueError("unsupported binary operator")
        if isinstance(node, UnaryOp):
            value = _eval(node.operand)
            if isinstance(node.op, UAdd):
                return value
            if isinstance(node.op, USub):
                return -value
            raise ValueError("unsupported unary operator")
        if isinstance(node, int | float):
            return float(node)
        if hasattr(node, "value") and isinstance(getattr(node, "value"), (int, float)):
            return float(getattr(node, "value"))
        raise ValueError("unsupported expression node")

    return _eval(tree)


def _build_tool_plan(prompt: str) -> list[dict[str, object]]:
    normalized = prompt.strip().lower()
    plan: list[dict[str, object]] = [
        {
            "name": "mock_plan",
            "input": {
                "prompt_preview": prompt.strip()[:120],
            },
        }
    ]

    if (
        "rag" in normalized
        or "知识" in normalized
        or "检索" in normalized
        or "context" in normalized
        or "[mock-multi-tool]" in normalized
    ):
        plan.append(
            {
                "name": "mock_retrieve",
                "input": {
                    "query": prompt.strip()[:80] or "default query",
                    "top_k": 2,
                },
            }
        )

    calc_expr = _extract_calc_expression(prompt)
    if calc_expr:
        plan.append(
            {
                "name": "calc_eval",
                "input": {
                    "expression": calc_expr,
                },
            }
        )

    return plan


def _run_mock_tool(
    *,
    name: str,
    tool_input: dict[str, object],
    prompt: str,
    attempt: int,
) -> dict[str, object]:
    normalized = prompt.strip().lower()

    if "[mock-tool-fatal]" in normalized:
        raise MockToolExecutionError(
            "Mock tool fatal error: planner contract validation failed.",
            fatal=True,
        )

    if "[mock-tool-error]" in normalized and attempt == 0:
        raise MockToolExecutionError(
            "Mock tool transient error: plan source unavailable on first attempt.",
            fatal=False,
        )

    if name == "mock_plan":
        return {
            "plan": "Split task into analysis -> retrieval -> synthesis.",
            "echo": True,
        }

    if name == "mock_retrieve":
        query = str(tool_input.get("query", ""))
        return {
            "chunks": [
                f"(mock) Retrieved snippet A for: {query}",
                "(mock) Retrieved snippet B with supporting detail.",
            ],
            "knowledge_base_id": "mock_kb",
        }

    if name == "calc_eval":
        expression = str(tool_input.get("expression", "")).strip()
        if not expression:
            raise MockToolExecutionError(
                "Calculator tool requires a non-empty expression.",
                fatal=False,
            )
        try:
            value = _safe_eval_expression(expression)
        except Exception as exc:
            raise MockToolExecutionError(
                f"Calculator parse/eval failed: {exc}",
                fatal=False,
            ) from exc
        return {
            "expression": expression,
            "result": value,
            "tool_kind": "local_calculator",
        }

    raise MockToolExecutionError(f"Unknown mock tool: {name}", fatal=True)


def stream_task_execution(
    *,
    task_id: str,
    session_id: str,
    prompt: str,
    persist_user_message: bool = False,
) -> Iterator[str]:
    STREAM_TRACE_PERSIST_EVERY = 8
    STREAM_HEARTBEAT_INTERVAL_SEC = 2.0
    TRACE_PERSIST_MIN_INTERVAL_SEC = max(
        0.0, float(get_settings().trace_persist_min_interval_sec)
    )
    TOOL_MAX_RETRY = 1
    trace_steps: list[dict[str, object]] = []
    seq_cursor = 0
    last_trace_persist_ts = 0.0

    def persist_trace(*, force: bool = False) -> None:
        nonlocal last_trace_persist_ts
        if not trace_steps:
            return
        now = monotonic()
        if (
            not force
            and last_trace_persist_ts > 0
            and now - last_trace_persist_ts < TRACE_PERSIST_MIN_INTERVAL_SEC
        ):
            return
        update_task_trace_steps(task_id, trace_steps)
        last_trace_persist_ts = now

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

        yield sse_event(
            "start",
            {
                "session_id": session_id,
                "task_id": task_id,
                "provider": getattr(provider, "provider", "mock"),
                "model": getattr(provider, "model", "mock-gpt"),
            },
        )
        yield sse_event("state", {"task_id": task_id, "phase": "thinking"})

        plan_step_id = str(uuid4())
        seq_cursor += 1
        tool_plan = _build_tool_plan(prompt)
        plan_content = "Planned tools: " + ", ".join(
            str(x["name"]) for x in tool_plan
        )
        plan_step = {
            "id": plan_step_id,
            "seq": seq_cursor,
            "type": "thought",
            "content": plan_content,
            "meta": {
                "model": getattr(provider, "model", "mock-gpt"),
                "step_type": "planning",
                "label": "tool_plan",
            },
        }
        trace_steps.append(plan_step)
        yield sse_event(
            "trace",
            {"task_id": task_id, "step_id": plan_step_id, "step": plan_step},
        )
        persist_trace(force=True)

        tool_observations: list[str] = []

        for idx, tool_spec in enumerate(tool_plan, start=1):
            tool_name = str(tool_spec["name"])
            tool_input = tool_spec.get("input")
            if not isinstance(tool_input, dict):
                tool_input = {}

            action_step_id = str(uuid4())
            action_step = {
                "id": action_step_id,
                "seq": seq_cursor + 1,
                "type": "action",
                "content": f"Tool running: {tool_name}",
                "meta": {
                    "model": getattr(provider, "model", "mock-gpt"),
                    "step_type": "tool_call",
                    "label": f"tool_{idx}",
                    "retryCount": 0,
                    "tool": {
                        "name": tool_name,
                        "input": tool_input,
                        "status": "running",
                        "retry_count": 0,
                    },
                },
            }
            seq_cursor += 1
            action_step["seq"] = seq_cursor

            attempt = 0
            last_error: str | None = None

            while True:
                yield sse_event(
                    "tool_start",
                    {
                        "task_id": task_id,
                        "step_id": action_step_id,
                        "name": tool_name,
                        "input": tool_input,
                        "retry_count": attempt,
                    },
                )
                yield sse_event(
                    "state",
                    {
                        "task_id": task_id,
                        "phase": "tool_running" if attempt == 0 else "tool_retry",
                    },
                )

                try:
                    output = _run_mock_tool(
                        name=tool_name,
                        tool_input=tool_input,
                        prompt=prompt,
                        attempt=attempt,
                    )

                    action_step = {
                        **action_step,
                        "content": f"Tool done: {tool_name}",
                        "meta": {
                            **dict(action_step.get("meta", {})),
                            "step_type": "tool_call",
                            "retryCount": attempt,
                            "tool": {
                                "name": tool_name,
                                "input": tool_input,
                                "output": output,
                                "status": "done",
                                "retry_count": attempt,
                                "error": last_error,
                            },
                        },
                    }
                    yield sse_event(
                        "tool_end",
                        {
                            "task_id": task_id,
                            "step_id": action_step_id,
                            "status": "done",
                            "latency_ms": 12,
                            "output_preview": output,
                            "retry_count": attempt,
                        },
                    )
                    break

                except MockToolExecutionError as exc:
                    last_error = str(exc)
                    is_retryable = (not exc.fatal) and attempt < TOOL_MAX_RETRY
                    action_step = {
                        **action_step,
                        "content": f"Tool error: {tool_name}",
                        "meta": {
                            **dict(action_step.get("meta", {})),
                            "step_type": "tool_call",
                            "retryCount": attempt + 1,
                            "tool": {
                                "name": tool_name,
                                "input": tool_input,
                                "output": {"error": last_error},
                                "status": "error",
                                "retry_count": attempt + 1,
                                "error": last_error,
                            },
                        },
                    }
                    yield sse_event(
                        "tool_end",
                        {
                            "task_id": task_id,
                            "step_id": action_step_id,
                            "status": "error",
                            "latency_ms": 12,
                            "output_preview": {"error": last_error},
                            "retry_count": attempt + 1,
                            "error": last_error,
                        },
                    )
                    yield sse_event(
                        "error",
                        {
                            "task_id": task_id,
                            "step_id": action_step_id,
                            "message": last_error,
                            "fatal": not is_retryable,
                            "retryCount": attempt + 1,
                        },
                    )
                    if is_retryable:
                        attempt += 1
                        continue

                    trace_steps.append(action_step)
                    yield sse_event(
                        "trace",
                        {
                            "task_id": task_id,
                            "step_id": action_step_id,
                            "step": action_step,
                        },
                    )
                    persist_trace(force=True)
                    complete_task(task_id=task_id, trace_steps=trace_steps, status="failed")
                    yield sse_event("state", {"task_id": task_id, "phase": "error"})
                    return

            trace_steps.append(action_step)
            yield sse_event(
                "trace",
                {
                    "task_id": task_id,
                    "step_id": action_step_id,
                    "step": action_step,
                },
            )
            persist_trace()

            tool_meta = action_step.get("meta") if isinstance(action_step, dict) else None
            tool_obj = (
                tool_meta.get("tool")
                if isinstance(tool_meta, dict) and isinstance(tool_meta.get("tool"), dict)
                else {}
            )
            output = tool_obj.get("output") if isinstance(tool_obj, dict) else None
            tool_observations.append(f"{tool_name}: {json.dumps(output, ensure_ascii=False)}")

            if tool_name == "mock_retrieve" and isinstance(output, dict):
                chunks = output.get("chunks")
                kb = output.get("knowledge_base_id")
                if isinstance(chunks, list):
                    seq_cursor += 1
                    rag_step_id = str(uuid4())
                    rag_step = {
                        "id": rag_step_id,
                        "seq": seq_cursor,
                        "type": "thought",
                        "content": "Retrieved snippets from mock knowledge base.",
                        "meta": {
                            "model": getattr(provider, "model", "mock-gpt"),
                            "step_type": "rag_retrieval",
                            "rag": {
                                "chunks": [str(x) for x in chunks],
                                "knowledge_base_id": str(kb) if kb else "mock_kb",
                            },
                        },
                    }
                    trace_steps.append(rag_step)
                    yield sse_event(
                        "trace",
                        {"task_id": task_id, "step_id": rag_step_id, "step": rag_step},
                    )
                    persist_trace()

        yield sse_event("state", {"task_id": task_id, "phase": "streaming"})
        final_step_id = str(uuid4())
        seq_cursor += 1
        final_step_streaming: dict[str, object] = {
            "id": final_step_id,
            "seq": seq_cursor,
            "type": "observation",
            "content": "",
            "meta": {
                "model": getattr(provider, "model", "mock-gpt"),
                "step_type": "final_answer",
                "tokens": None,
                "cost_estimate": None,
            },
        }
        trace_steps.append(final_step_streaming)
        yield sse_event(
            "trace",
            {
                "task_id": task_id,
                "step_id": final_step_id,
                "step": final_step_streaming,
            },
        )
        persist_trace(force=True)

        last_heartbeat_ts = monotonic()
        yield sse_event(
            "heartbeat",
            {
                "task_id": task_id,
                "ts": datetime.now().isoformat(),
            },
        )

        provider_prompt = prompt
        if tool_observations:
            provider_prompt = (
                f"{prompt}\n\nTool observations:\n" + "\n".join(tool_observations)
            )
        completion_tokens = 0
        fallback_completion_tokens = 0

        streamed_content = ""
        final_step_seq = int(final_step_streaming.get("seq", seq_cursor))
        for chunk in provider.stream_generate(provider_prompt):
            completion_tokens += 1
            now = monotonic()
            if now - last_heartbeat_ts >= STREAM_HEARTBEAT_INTERVAL_SEC:
                yield sse_event(
                    "heartbeat",
                    {
                        "task_id": task_id,
                        "ts": datetime.now().isoformat(),
                    },
                )
                last_heartbeat_ts = now
            yield sse_event(
                "token",
                {
                    "task_id": task_id,
                    "step_id": final_step_id,
                    "delta": chunk,
                },
            )
            streamed_content += chunk
            should_persist = completion_tokens % STREAM_TRACE_PERSIST_EVERY == 0
            if should_persist:
                final_step_seq += 1
                final_step_streaming = {
                    **final_step_streaming,
                    "content": streamed_content,
                    "seq": final_step_seq,
                }
                trace_steps[-1] = final_step_streaming
                persist_trace()

        final_content = streamed_content
        if not final_content:
            fallback = provider.generate(provider_prompt)
            final_content = fallback.content
            fallback_completion_tokens = len(final_content.split())
        else:
            final_step_seq += 1
        trace_steps[-1] = {
            **final_step_streaming,
            "content": final_content,
            "seq": final_step_seq,
        }
        persist_trace(force=True)

        create_message(
            session_id=session_id,
            task_id=task_id,
            role="assistant",
            content=final_content,
        )

        usage_payload: dict[str, object] = {
            "prompt_tokens": None,
            "completion_tokens": completion_tokens or fallback_completion_tokens,
            "cost_estimate": None,
        }

        complete_task(
            task_id=task_id,
            trace_steps=trace_steps,
            usage=usage_payload,
        )
        try_append_task_memory(
            session_id,
            task_id=task_id,
            user_prompt=prompt,
            assistant_excerpt=final_content,
        )

        yield sse_event(
            "done",
            {
                "session_id": session_id,
                "task_id": task_id,
                "step_id": final_step_id,
                "status": "completed",
                "usage": usage_payload,
            },
        )

    except Exception as exc:
        complete_task(task_id=task_id, trace_steps=trace_steps, status="failed")
        yield sse_event("state", {"task_id": task_id, "phase": "error"})
        yield sse_event(
            "error",
            {
                "task_id": task_id,
                "message": str(exc),
                "fatal": True,
                "retryCount": 0,
            },
        )
