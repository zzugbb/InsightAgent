from __future__ import annotations

import json
import re
from ast import Add, BinOp, Div, Expression, Mod, Mult, Pow, Sub, UAdd, USub, UnaryOp, parse
from dataclasses import dataclass
from typing import Callable, Iterator

from app.config import get_settings
from app.services.chroma_rag_service import query_knowledge_base


class MockToolExecutionError(RuntimeError):
    def __init__(self, message: str, *, fatal: bool):
        super().__init__(message)
        self.fatal = fatal


@dataclass(frozen=True)
class ToolInvocation:
    name: str
    tool_input: dict[str, object]


ToolRunner = Callable[..., dict[str, object]]


@dataclass(frozen=True)
class ToolRegistration:
    name: str
    kind: str
    label: str
    retryable_by_default: bool
    default_timeout_ms: int
    requires_user_context: bool
    supports_result_preview: bool
    runner: ToolRunner


@dataclass(frozen=True)
class ToolRuntimeContext:
    name: str
    prompt: str
    user_id: str
    attempt: int
    registration: ToolRegistration
    retryable_by_default: bool
    default_timeout_ms: int
    requires_user_context: bool


def normalize_tool_spec(tool_spec: dict[str, object]) -> ToolInvocation:
    name = str(tool_spec.get("name", "")).strip()
    tool_input = tool_spec.get("input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    return ToolInvocation(name=name, tool_input=tool_input)


def _run_mock_plan(*, tool_input: dict[str, object], prompt: str, user_id: str) -> dict[str, object]:
    del tool_input, prompt, user_id
    return {
        "plan": "Split task into analysis -> retrieval -> synthesis.",
        "echo": True,
    }


def _run_mock_retrieve(
    *,
    tool_input: dict[str, object],
    prompt: str,
    user_id: str,
) -> dict[str, object]:
    query = str(tool_input.get("query", ""))
    top_k_raw = tool_input.get("top_k")
    top_k = top_k_raw if isinstance(top_k_raw, int) else 4
    kb_raw = tool_input.get("knowledge_base_id")
    kb_id = str(kb_raw or get_settings().rag_default_knowledge_base_id)
    try:
        result = query_knowledge_base(
            user_id=user_id,
            knowledge_base_id=kb_id,
            query_text=query or prompt,
            top_k=top_k,
        )
    except Exception as exc:  # noqa: BLE001
        raise MockToolExecutionError(
            f"RAG query failed: {exc}",
            fatal=False,
        ) from exc
    chunks = [
        str(x.get("content", "")).strip()
        for x in result.get("hits", [])
        if isinstance(x, dict)
    ]
    clean_chunks = [x for x in chunks if x]
    return {
        "chunks": clean_chunks,
        "hits": result.get("hits", []),
        "hit_count": int(result.get("hit_count", 0) or 0),
        "knowledge_base_id": str(result.get("knowledge_base_id", kb_id)),
        "collection": result.get("collection"),
    }


def _run_calc_eval(*, tool_input: dict[str, object], prompt: str, user_id: str) -> dict[str, object]:
    del prompt, user_id
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


_REGISTERED_TOOLS = {
    "mock_plan": ToolRegistration(
        name="mock_plan",
        kind="mock_planner",
        label="Mock Planner",
        retryable_by_default=True,
        default_timeout_ms=3_000,
        requires_user_context=True,
        supports_result_preview=True,
        runner=_run_mock_plan,
    ),
    "mock_retrieve": ToolRegistration(
        name="mock_retrieve",
        kind="mock_retrieval",
        label="Mock Retrieval",
        retryable_by_default=True,
        default_timeout_ms=5_000,
        requires_user_context=True,
        supports_result_preview=True,
        runner=_run_mock_retrieve,
    ),
    "calc_eval": ToolRegistration(
        name="calc_eval",
        kind="local_calculator",
        label="Calculator",
        retryable_by_default=True,
        default_timeout_ms=3_000,
        requires_user_context=True,
        supports_result_preview=True,
        runner=_run_calc_eval,
    ),
}


def get_registered_tool_names() -> tuple[str, ...]:
    return tuple(sorted(_REGISTERED_TOOLS))


def resolve_tool_registration(name: str) -> ToolRegistration | None:
    return _REGISTERED_TOOLS.get(name)


def ensure_tool_registration(name: str) -> ToolRegistration:
    registration = resolve_tool_registration(name)
    if registration is None:
        raise MockToolExecutionError(f"Unknown mock tool: {name}", fatal=True)
    return registration


def maybe_raise_mock_tool_execution_error(*, name: str, prompt: str, attempt: int) -> None:
    del name
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


def build_tool_runtime_context(
    *,
    name: str,
    prompt: str,
    user_id: str,
    attempt: int,
) -> ToolRuntimeContext:
    registration = ensure_tool_registration(name)
    requires_user_context = tool_requires_user_context(name)
    effective_user_id = user_id if requires_user_context else ""
    return ToolRuntimeContext(
        name=name,
        prompt=prompt,
        user_id=effective_user_id,
        attempt=attempt,
        registration=registration,
        retryable_by_default=is_tool_retryable_by_default(name),
        default_timeout_ms=get_tool_default_timeout_ms(name),
        requires_user_context=requires_user_context,
    )


def build_tool_result_preview(*, name: str, output: dict[str, object]) -> dict[str, object] | None:
    registration = resolve_tool_registration(name)
    if registration is None:
        return output
    if not registration.supports_result_preview:
        return None
    return output


def tool_requires_user_context(name: str) -> bool:
    registration = resolve_tool_registration(name)
    if registration is None:
        return True
    return registration.requires_user_context


def is_tool_retryable_by_default(name: str) -> bool:
    registration = resolve_tool_registration(name)
    if registration is None:
        return True
    return registration.retryable_by_default


def get_tool_default_timeout_ms(name: str) -> int:
    registration = resolve_tool_registration(name)
    if registration is None:
        return 3_000
    return registration.default_timeout_ms


def compute_tool_retry_decision(*, ctx: ToolRuntimeContext, exc: MockToolExecutionError) -> bool:
    max_retry = 1 if ctx.retryable_by_default else 0
    return (not exc.fatal) and ctx.attempt < max_retry


def build_tool_end_payload(
    *,
    name: str,
    task_id: str,
    step_id: str,
    output: dict[str, object],
    retry_count: int,
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "step_id": step_id,
        "status": "done",
        "latency_ms": max(1, get_tool_default_timeout_ms(name) // 250),
        "output_preview": build_tool_result_preview(name=name, output=output),
        "retry_count": retry_count,
    }


def build_tool_success_meta(
    *,
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object],
    retry_count: int,
    last_error: str | None,
) -> dict[str, object]:
    return {
        "tool": {
            "name": name,
            "input": tool_input,
            "output": output,
            "status": "done",
            "retry_count": retry_count,
            "error": last_error,
        },
    }


def build_tool_error_meta(
    *,
    name: str,
    tool_input: dict[str, object],
    retry_count: int,
    error_message: str,
) -> dict[str, object]:
    return {
        "tool": {
            "name": name,
            "input": tool_input,
            "status": "error",
            "retry_count": retry_count,
            "error": error_message,
        },
    }


def build_tool_start_payload(
    *,
    task_id: str,
    step_id: str,
    name: str,
    tool_input: dict[str, object],
    retry_count: int,
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "step_id": step_id,
        "name": name,
        "input": tool_input,
        "retry_count": retry_count,
    }


def build_tool_error_payload(
    *,
    task_id: str,
    step_id: str,
    error_message: str,
    retry_count: int,
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "step_id": step_id,
        "status": "error",
        "latency_ms": 12,
        "output_preview": {"error": error_message},
        "retry_count": retry_count,
        "error": error_message,
    }


def build_tool_phase(attempt: int) -> str:
    return "tool_running" if attempt == 0 else "tool_retry"


def build_tool_execution_policy(ctx: ToolRuntimeContext) -> dict[str, object]:
    return {
        "max_retry": 1 if ctx.retryable_by_default else 0,
        "latency_ms": max(1, ctx.default_timeout_ms // 250),
        "effective_user_id": ctx.user_id,
    }


def build_action_step_initial_meta(
    *,
    name: str,
    tool_input: dict[str, object],
    model: str,
    label: str,
    token_count: int,
) -> dict[str, object]:
    return {
        "model": model,
        "step_type": "tool_call",
        "label": label,
        "retryCount": 0,
        "tokens": token_count,
        "cost_estimate": None,
        "tool": {
            "name": name,
            "input": tool_input,
            "status": "running",
            "retry_count": 0,
        },
    }


def build_action_step_initial_step(
    *,
    step_id: str,
    seq: int,
    name: str,
    meta: dict[str, object],
) -> dict[str, object]:
    return {
        "id": step_id,
        "seq": seq,
        "type": "action",
        "content": f"Tool running: {name}",
        "meta": meta,
    }


def build_tool_step_success_update(
    *,
    action_step: dict[str, object],
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object],
    retry_count: int,
    token_count: int,
    last_error: str | None,
) -> dict[str, object]:
    return {
        **action_step,
        "content": f"Tool done: {name}",
        "meta": {
            **dict(action_step.get("meta", {})),
            "step_type": "tool_call",
            "retryCount": retry_count,
            "tokens": token_count,
            **build_tool_success_meta(
                name=name,
                tool_input=tool_input,
                output=output,
                retry_count=retry_count,
                last_error=last_error,
            ),
        },
    }


def build_tool_step_error_update(
    *,
    action_step: dict[str, object],
    name: str,
    tool_input: dict[str, object],
    retry_count: int,
    token_count: int,
    error_message: str,
) -> dict[str, object]:
    return {
        **action_step,
        "content": f"Tool error: {name}",
        "meta": {
            **dict(action_step.get("meta", {})),
            "step_type": "tool_call",
            "retryCount": retry_count,
            "tokens": token_count,
            **build_tool_error_meta(
                name=name,
                tool_input=tool_input,
                retry_count=retry_count,
                error_message=error_message,
            ),
        },
    }


def build_tool_attempt_start_events(
    *,
    task_id: str,
    step_id: str,
    name: str,
    tool_input: dict[str, object],
    attempt: int,
) -> dict[str, dict[str, object]]:
    return {
        "tool_start": build_tool_start_payload(
            task_id=task_id,
            step_id=step_id,
            name=name,
            tool_input=tool_input,
            retry_count=attempt,
        ),
        "state": {
            "task_id": task_id,
            "phase": build_tool_phase(attempt),
        },
    }


def build_tool_attempt_bundle(
    *,
    task_id: str,
    step_id: str,
    name: str,
    tool_input: dict[str, object],
    prompt: str,
    user_id: str,
    attempt: int,
) -> dict[str, object]:
    runtime_ctx = build_tool_runtime_context(
        name=name,
        prompt=prompt,
        user_id=user_id,
        attempt=attempt,
    )
    return {
        "start_events": build_tool_attempt_start_events(
            task_id=task_id,
            step_id=step_id,
            name=name,
            tool_input=tool_input,
            attempt=attempt,
        ),
        "runtime_ctx": runtime_ctx,
        "runtime_policy": build_tool_execution_policy(runtime_ctx),
    }


def build_tool_attempt_execution(
    *,
    task_id: str,
    iteration_ctx: dict[str, object],
    action_step: dict[str, object],
    attempt_bundle: dict[str, object],
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object] | None,
    exc: MockToolExecutionError | None,
    token_count: int,
    last_error: str | None,
    model: str,
    rag_step_id: str,
    rag_token_count: int,
) -> dict[str, object]:
    return build_tool_plan_item_execution(
        task_id=task_id,
        iteration_ctx=iteration_ctx,
        action_step=action_step,
        runtime_ctx=attempt_bundle["runtime_ctx"],
        name=name,
        tool_input=tool_input,
        output=output,
        exc=exc,
        token_count=token_count,
        last_error=last_error,
        model=model,
        rag_step_id=rag_step_id,
        rag_token_count=rag_token_count,
    )


def build_tool_attempt_loop_result(
    *,
    attempt_execution: dict[str, object],
) -> dict[str, object]:
    return {
        "tool_end_event": attempt_execution["tool_end_event"],
        "error_event": attempt_execution["error_event"],
        "retryable": attempt_execution["retryable"],
        "next_action_step": attempt_execution["next_action_step"],
        "last_error": attempt_execution["last_error"],
        "plan_item_result": attempt_execution["plan_item_result"],
        "postprocess": attempt_execution["postprocess"],
        "success_effects": attempt_execution["success_effects"],
        "terminal_effects": attempt_execution["terminal_effects"],
    }


def build_tool_attempt_loop_terminal_result(
    *,
    loop_result: dict[str, object],
) -> dict[str, object]:
    terminal_effects = loop_result["terminal_effects"]
    return {
        "should_return": terminal_effects is not None,
        "terminal_effects": terminal_effects,
    }


def build_tool_plan_item_retry_loop_result(
    *,
    loop_result: dict[str, object],
) -> dict[str, object]:
    success_effects = loop_result["success_effects"]
    terminal_effects = loop_result["terminal_effects"]
    trace_event = (
        success_effects["trace"]
        if success_effects is not None
        else terminal_effects["trace"]
        if terminal_effects is not None
        else None
    )
    return {
        "outcome": "success" if success_effects is not None else "terminal_failure",
        "trace_event": trace_event,
        "success_effects": success_effects,
        "terminal_effects": terminal_effects,
    }


def build_tool_plan_item_retry_loop_execution_result(
    *,
    loop_result: dict[str, object],
) -> dict[str, object]:
    retry_loop_result = build_tool_plan_item_retry_loop_result(
        loop_result=loop_result,
    )
    loop_terminal_result = build_tool_attempt_loop_terminal_result(
        loop_result=loop_result,
    )
    return {
        "outcome": retry_loop_result["outcome"],
        "trace_event": retry_loop_result["trace_event"],
        "success_effects": retry_loop_result["success_effects"],
        "terminal_effects": retry_loop_result["terminal_effects"],
        "should_return": loop_terminal_result["should_return"],
        "loop_result": loop_result,
        "retry_loop_result": retry_loop_result,
        "loop_terminal_result": loop_terminal_result,
    }


def execute_tool_plan_item_retry_loop(
    *,
    task_id: str,
    iteration_ctx: dict[str, object],
    initial_action_step: dict[str, object],
    tool_name: str,
    tool_input: dict[str, object],
    prompt: str,
    user_id: str,
    model: str,
    estimate_token_count: Callable[[str], int],
    make_step_id: Callable[[], str],
    raise_if_should_abort: Callable[[], None],
    run_tool_fn: ToolRunner | None = None,
) -> Iterator[dict[str, object]]:
    step_id = str(iteration_ctx["step_id"])
    action_step = dict(initial_action_step)
    attempt = 0
    last_error: str | None = None
    runner = run_tool if run_tool_fn is None else run_tool_fn

    while True:
        raise_if_should_abort()
        attempt_bundle = build_tool_attempt_bundle(
            task_id=task_id,
            step_id=step_id,
            name=tool_name,
            tool_input=tool_input,
            prompt=prompt,
            user_id=user_id,
            attempt=attempt,
        )
        start_events = attempt_bundle["start_events"]
        yield {
            "kind": "event",
            "event": "tool_start",
            "data": start_events["tool_start"],
        }
        yield {
            "kind": "event",
            "event": "state",
            "data": start_events["state"],
        }

        try:
            raise_if_should_abort()
            runtime_policy = attempt_bundle["runtime_policy"]
            output = runner(
                name=tool_name,
                tool_input=tool_input,
                prompt=prompt,
                user_id=str(runtime_policy["effective_user_id"]),
                attempt=attempt,
            )
            plan_item_execution = build_tool_attempt_execution(
                task_id=task_id,
                iteration_ctx=iteration_ctx,
                action_step=action_step,
                attempt_bundle=attempt_bundle,
                name=tool_name,
                tool_input=tool_input,
                output=output,
                exc=None,
                token_count=estimate_token_count(
                    f"{tool_name} {json.dumps(output, ensure_ascii=False)}"
                ),
                last_error=last_error,
                model=model,
                rag_step_id=make_step_id(),
                rag_token_count=estimate_token_count(
                    "\n".join(str(x) for x in output.get("chunks", []))
                )
                if isinstance(output, dict)
                else 0,
            )
            loop_result = build_tool_attempt_loop_result(
                attempt_execution=plan_item_execution,
            )
            action_step = loop_result["next_action_step"]
            yield {
                "kind": "event",
                "event": "tool_end",
                "data": loop_result["tool_end_event"],
            }
            yield {
                "kind": "result",
                "result": build_tool_plan_item_retry_loop_execution_result(
                    loop_result=loop_result,
                ),
            }
            return

        except MockToolExecutionError as exc:
            plan_item_execution = build_tool_attempt_execution(
                task_id=task_id,
                iteration_ctx=iteration_ctx,
                action_step=action_step,
                attempt_bundle=attempt_bundle,
                name=tool_name,
                tool_input=tool_input,
                output=None,
                exc=exc,
                token_count=estimate_token_count(str(exc)),
                last_error=None,
                model=model,
                rag_step_id=make_step_id(),
                rag_token_count=0,
            )
            loop_result = build_tool_attempt_loop_result(
                attempt_execution=plan_item_execution,
            )
            action_step = loop_result["next_action_step"]
            yield {
                "kind": "event",
                "event": "tool_end",
                "data": loop_result["tool_end_event"],
            }
            error_event = loop_result["error_event"]
            if error_event is not None:
                yield {
                    "kind": "event",
                    "event": "error",
                    "data": error_event,
                }
            if bool(loop_result["retryable"]):
                attempt += 1
                last_error = str(loop_result["last_error"])
                continue

            yield {
                "kind": "result",
                "result": build_tool_plan_item_retry_loop_execution_result(
                    loop_result=loop_result,
                ),
            }
            return


def build_tool_attempt_success_events(
    *,
    task_id: str,
    step_id: str,
    name: str,
    output: dict[str, object],
    retry_count: int,
) -> dict[str, dict[str, object]]:
    return {
        "tool_end": build_tool_end_payload(
            name=name,
            task_id=task_id,
            step_id=step_id,
            output=output,
            retry_count=retry_count,
        )
    }


def build_tool_attempt_error_events(
    *,
    task_id: str,
    step_id: str,
    error_message: str,
    retry_count: int,
) -> dict[str, dict[str, object]]:
    return {
        "tool_end": build_tool_error_payload(
            task_id=task_id,
            step_id=step_id,
            error_message=error_message,
            retry_count=retry_count,
        )
    }


def build_tool_attempt_success_transition(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object],
    retry_count: int,
    token_count: int,
    last_error: str | None,
) -> dict[str, object]:
    return {
        "action_step": build_tool_step_success_update(
            action_step=action_step,
            name=name,
            tool_input=tool_input,
            output=output,
            retry_count=retry_count,
            token_count=token_count,
            last_error=last_error,
        ),
        "events": build_tool_attempt_success_events(
            task_id=task_id,
            step_id=step_id,
            name=name,
            output=output,
            retry_count=retry_count,
        ),
    }


def build_tool_attempt_error_transition(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    runtime_ctx: ToolRuntimeContext,
    name: str,
    tool_input: dict[str, object],
    exc: MockToolExecutionError,
    token_count: int,
) -> dict[str, object]:
    error_message = str(exc)
    retry_count = runtime_ctx.attempt + 1
    retryable = compute_tool_retry_decision(ctx=runtime_ctx, exc=exc)
    return {
        "action_step": build_tool_step_error_update(
            action_step=action_step,
            name=name,
            tool_input=tool_input,
            retry_count=retry_count,
            token_count=token_count,
            error_message=error_message,
        ),
        "events": {
            **build_tool_attempt_error_events(
                task_id=task_id,
                step_id=step_id,
                error_message=error_message,
                retry_count=retry_count,
            ),
            "error": {
                "task_id": task_id,
                "message": error_message,
                "code": "tool_execution_error",
                "fatal": not retryable,
                "retryable": retryable,
                "retryCount": retry_count,
                "step_id": step_id,
            },
        },
        "retryable": retryable,
        "error_message": error_message,
        "retry_count": retry_count,
    }


def build_tool_step_output(action_step: dict[str, object]) -> dict[str, object] | None:
    tool_meta = action_step.get("meta") if isinstance(action_step, dict) else None
    tool_obj = (
        tool_meta.get("tool")
        if isinstance(tool_meta, dict) and isinstance(tool_meta.get("tool"), dict)
        else None
    )
    output = tool_obj.get("output") if isinstance(tool_obj, dict) else None
    return output if isinstance(output, dict) else None


def build_tool_observation_entry(*, name: str, output: dict[str, object] | None) -> str:
    return f"{name}: {json.dumps(output, ensure_ascii=False)}"


def build_tool_trace_event(
    *,
    task_id: str,
    step_id: str,
    step: dict[str, object],
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "step_id": step_id,
        "step": step,
    }


def build_tool_terminal_failure_transition(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    error_message: str,
    retry_count: int,
) -> dict[str, object]:
    return {
        "trace": build_tool_trace_event(
            task_id=task_id,
            step_id=step_id,
            step=action_step,
        ),
        "audit_detail": {
            "step_id": step_id,
            "retry_count": retry_count,
        },
        "state": {
            "task_id": task_id,
            "phase": "error",
        },
        "status": "failed",
        "error_message": error_message,
    }


def build_tool_rag_step(
    *,
    step_id: str,
    seq: int,
    model: str,
    chunks: list[str],
    knowledge_base_id: str,
    token_count: int,
) -> dict[str, object]:
    return {
        "id": step_id,
        "seq": seq,
        "type": "thought",
        "content": "Retrieved snippets from mock knowledge base.",
        "meta": {
            "model": model,
            "step_type": "rag_retrieval",
            "tokens": token_count,
            "cost_estimate": None,
            "rag": {
                "chunks": chunks,
                "knowledge_base_id": knowledge_base_id,
            },
        },
    }


def build_tool_prompt_with_observations(
    *,
    prompt: str,
    tool_observations: list[str],
) -> str:
    if not tool_observations:
        return prompt
    return f"{prompt}\n\nTool observations:\n" + "\n".join(tool_observations)


def build_tool_attempt_result(
    *,
    outcome: str,
    action_step: dict[str, object],
    events: dict[str, dict[str, object]],
    retryable: bool,
    error_message: str | None,
    retry_count: int,
) -> dict[str, object]:
    return {
        "outcome": outcome,
        "action_step": action_step,
        "events": events,
        "retryable": retryable,
        "error_message": error_message,
        "retry_count": retry_count,
    }


def build_tool_attempt_outcome(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    runtime_ctx: ToolRuntimeContext,
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object] | None,
    exc: MockToolExecutionError | None,
    token_count: int,
    last_error: str | None,
) -> dict[str, object]:
    if exc is None:
        assert output is not None
        success_transition = build_tool_attempt_success_transition(
            task_id=task_id,
            step_id=step_id,
            action_step=action_step,
            name=name,
            tool_input=tool_input,
            output=output,
            retry_count=runtime_ctx.attempt,
            token_count=token_count,
            last_error=last_error,
        )
        return build_tool_attempt_result(
            outcome="success",
            action_step=success_transition["action_step"],
            events=success_transition["events"],
            retryable=False,
            error_message=None,
            retry_count=runtime_ctx.attempt,
        )

    error_transition = build_tool_attempt_error_transition(
        task_id=task_id,
        step_id=step_id,
        action_step=action_step,
        runtime_ctx=runtime_ctx,
        name=name,
        tool_input=tool_input,
        exc=exc,
        token_count=token_count,
    )
    return build_tool_attempt_result(
        outcome="error",
        action_step=error_transition["action_step"],
        events=error_transition["events"],
        retryable=bool(error_transition["retryable"]),
        error_message=str(error_transition["error_message"]),
        retry_count=int(error_transition["retry_count"]),
    )


def build_tool_iteration_context(
    *,
    step_id: str,
    seq: int,
    name: str,
    tool_input: dict[str, object],
    model: str,
    label: str,
    token_count: int,
) -> dict[str, object]:
    return {
        "step_id": step_id,
        "action_step": build_action_step_initial_step(
            step_id=step_id,
            seq=seq,
            name=name,
            meta=build_action_step_initial_meta(
                name=name,
                tool_input=tool_input,
                model=model,
                label=label,
                token_count=token_count,
            ),
        ),
    }


def build_tool_iteration_success_artifacts(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    name: str,
) -> dict[str, object]:
    output = build_tool_step_output(action_step)
    return {
        "trace": build_tool_trace_event(
            task_id=task_id,
            step_id=step_id,
            step=action_step,
        ),
        "observation": build_tool_observation_entry(name=name, output=output),
        "output": output,
    }


def build_tool_rag_followup(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    tool_name: str,
    output: dict[str, object] | None,
    token_count: int,
) -> dict[str, object] | None:
    if tool_name != "mock_retrieve" or not isinstance(output, dict):
        return None
    chunks = output.get("chunks")
    if not isinstance(chunks, list):
        return None
    kb = output.get("knowledge_base_id")
    step = build_tool_rag_step(
        step_id=step_id,
        seq=seq,
        model=model,
        chunks=[str(x) for x in chunks],
        knowledge_base_id=str(kb) if kb else get_settings().rag_default_knowledge_base_id,
        token_count=token_count,
    )
    return {
        "step": step,
        "trace": build_tool_trace_event(
            task_id=task_id,
            step_id=step_id,
            step=step,
        ),
    }


def build_tool_iteration_execution(
    *,
    task_id: str,
    step_id: str,
    iteration_ctx: dict[str, object],
    action_step: dict[str, object],
    runtime_ctx: ToolRuntimeContext,
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object] | None,
    exc: MockToolExecutionError | None,
    token_count: int,
    last_error: str | None,
) -> dict[str, object]:
    start_events = build_tool_attempt_start_events(
        task_id=task_id,
        step_id=step_id,
        name=name,
        tool_input=tool_input,
        attempt=runtime_ctx.attempt,
    )
    outcome = build_tool_attempt_outcome(
        task_id=task_id,
        step_id=step_id,
        action_step=dict(action_step),
        runtime_ctx=runtime_ctx,
        name=name,
        tool_input=tool_input,
        output=output,
        exc=exc,
        token_count=token_count,
        last_error=last_error,
    )
    if outcome["outcome"] == "success":
        return {
            "start_events": start_events,
            "outcome": outcome,
            "success_artifacts": build_tool_iteration_success_artifacts(
                task_id=task_id,
                step_id=step_id,
                action_step=outcome["action_step"],
                name=name,
            ),
            "terminal_failure": None,
        }

    terminal_failure = None
    if not bool(outcome["retryable"]):
        terminal_failure = build_tool_terminal_failure_transition(
            task_id=task_id,
            step_id=step_id,
            action_step=outcome["action_step"],
            error_message=str(outcome["error_message"]),
            retry_count=int(outcome["retry_count"]),
        )
    return {
        "start_events": start_events,
        "outcome": outcome,
        "success_artifacts": None,
        "terminal_failure": terminal_failure,
    }


def build_tool_plan_item_success_bundle(
    *,
    success_artifacts: dict[str, object],
    rag_followup: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "trace": success_artifacts["trace"],
        "observation": success_artifacts["observation"],
        "output": success_artifacts["output"],
        "rag_followup": rag_followup,
    }


def build_tool_plan_item_result(
    *,
    outcome: str,
    action_step: dict[str, object],
    last_error: str | None,
    success_bundle: dict[str, object] | None,
    terminal_failure: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "outcome": outcome,
        "action_step": action_step,
        "last_error": last_error,
        "success_bundle": success_bundle,
        "terminal_failure": terminal_failure,
    }


def build_tool_plan_item_execution_result(
    *,
    iteration_execution: dict[str, object],
    rag_followup: dict[str, object] | None,
) -> dict[str, object]:
    success_artifacts = iteration_execution.get("success_artifacts")
    terminal_failure = iteration_execution.get("terminal_failure")
    outcome = iteration_execution["outcome"]
    action_step = outcome["action_step"]
    error_message = outcome.get("error_message")

    if success_artifacts is not None:
        return build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=error_message,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=rag_followup,
            ),
            terminal_failure=None,
        )

    return build_tool_plan_item_result(
        outcome="terminal_failure",
        action_step=action_step,
        last_error=error_message,
        success_bundle=None,
        terminal_failure=terminal_failure,
    )


def build_tool_plan_item_execution(
    *,
    task_id: str,
    iteration_ctx: dict[str, object],
    action_step: dict[str, object],
    runtime_ctx: ToolRuntimeContext,
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object] | None,
    exc: MockToolExecutionError | None,
    token_count: int,
    last_error: str | None,
    model: str,
    rag_step_id: str,
    rag_token_count: int,
) -> dict[str, object]:
    iteration_execution = build_tool_iteration_execution(
        task_id=task_id,
        step_id=str(iteration_ctx["step_id"]),
        iteration_ctx=iteration_ctx,
        action_step=action_step,
        runtime_ctx=runtime_ctx,
        name=name,
        tool_input=tool_input,
        output=output,
        exc=exc,
        token_count=token_count,
        last_error=last_error,
    )
    success_artifacts = iteration_execution.get("success_artifacts")
    rag_followup = None
    if success_artifacts is not None:
        success_output = success_artifacts["output"]
        rag_followup = build_tool_rag_followup(
            task_id=task_id,
            step_id=rag_step_id,
            seq=int(action_step.get("seq", 0)) + 1,
            model=model,
            tool_name=name,
            output=success_output if isinstance(success_output, dict) else None,
            token_count=rag_token_count,
    )
    plan_item_result = build_tool_plan_item_execution_result(
        iteration_execution=iteration_execution,
        rag_followup=rag_followup,
    )
    attempt_outcome = iteration_execution["outcome"]
    postprocess = None
    success_effects = None
    terminal_effects = None
    if plan_item_result["success_bundle"] is not None:
        postprocess = build_tool_plan_item_postprocess(
            plan_item_result=plan_item_result,
        )
        success_effects = build_tool_plan_item_success_effects(
            action_step=plan_item_result["action_step"],
            postprocess=postprocess,
        )
    elif plan_item_result["terminal_failure"] is not None:
        terminal_effects = build_tool_plan_item_terminal_effects(
            action_step=plan_item_result["action_step"],
            terminal_failure=plan_item_result["terminal_failure"],
        )
    return {
        "start_events": iteration_execution["start_events"],
        "iteration_execution": iteration_execution,
        "tool_end_event": attempt_outcome["events"]["tool_end"],
        "error_event": attempt_outcome["events"].get("error"),
        "retryable": bool(attempt_outcome["retryable"]),
        "postprocess": postprocess,
        "success_effects": success_effects,
        "terminal_effects": terminal_effects,
        "plan_item_result": plan_item_result,
        "next_action_step": plan_item_result["action_step"],
        "last_error": plan_item_result["last_error"],
        "terminal_failure": plan_item_result["terminal_failure"],
    }


def build_tool_plan_item_postprocess(
    *,
    plan_item_result: dict[str, object],
) -> dict[str, object]:
    success_bundle = plan_item_result["success_bundle"]
    assert success_bundle is not None
    return {
        "trace": success_bundle["trace"],
        "observation": success_bundle["observation"],
        "output": success_bundle["output"],
        "rag_followup": success_bundle["rag_followup"],
    }


def build_tool_plan_item_success_effects(
    *,
    action_step: dict[str, object],
    postprocess: dict[str, object],
) -> dict[str, object]:
    return {
        "trace_step": action_step,
        "trace": postprocess["trace"],
        "observation": postprocess["observation"],
        "output": postprocess["output"],
        "rag_followup": postprocess["rag_followup"],
    }


def build_tool_plan_item_terminal_effects(
    *,
    action_step: dict[str, object],
    terminal_failure: dict[str, object],
) -> dict[str, object]:
    return {
        "trace_step": action_step,
        "trace": terminal_failure["trace"],
        "status": terminal_failure["status"],
        "error_message": terminal_failure["error_message"],
        "audit_detail": terminal_failure["audit_detail"],
        "state": terminal_failure["state"],
    }


def build_tool_plan_item_stream_effects(
    *,
    loop_execution_result: dict[str, object],
) -> dict[str, object]:
    success_effects = loop_execution_result["success_effects"]
    terminal_effects = loop_execution_result["terminal_effects"]

    if success_effects is not None:
        trace_steps = [success_effects["trace_step"]]
        trace_events = [loop_execution_result["trace_event"]]
        rag_followup = success_effects["rag_followup"]
        if rag_followup is not None:
            trace_steps.append(rag_followup["step"])
            trace_events.append(rag_followup["trace"])
        return {
            "trace_steps": trace_steps,
            "trace_events": trace_events,
            "observation": success_effects["observation"],
            "terminal_effects": None,
            "should_return": False,
        }

    assert terminal_effects is not None
    return {
        "trace_steps": [terminal_effects["trace_step"]],
        "trace_events": [terminal_effects["trace"]],
        "observation": None,
        "terminal_effects": terminal_effects,
        "should_return": bool(loop_execution_result["should_return"]),
    }


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


def _extract_knowledge_base_id(prompt: str) -> str | None:
    tagged = re.search(r"\[kb:([a-zA-Z0-9_-]{1,64})\]", prompt)
    if not tagged:
        return None
    value = tagged.group(1).strip()
    return value or None


def build_tool_plan(prompt: str) -> list[dict[str, object]]:
    normalized = prompt.strip().lower()
    settings = get_settings()
    knowledge_base_id = (
        _extract_knowledge_base_id(prompt) or settings.rag_default_knowledge_base_id
    )
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
                    "top_k": settings.rag_default_top_k,
                    "knowledge_base_id": knowledge_base_id,
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


def run_tool(
    *,
    name: str,
    tool_input: dict[str, object],
    prompt: str,
    user_id: str,
    attempt: int,
) -> dict[str, object]:
    maybe_raise_mock_tool_execution_error(name=name, prompt=prompt, attempt=attempt)
    ctx = build_tool_runtime_context(
        name=name,
        prompt=prompt,
        user_id=user_id,
        attempt=attempt,
    )
    return ctx.registration.runner(
        tool_input=tool_input,
        prompt=ctx.prompt,
        user_id=ctx.user_id,
    )


def execute_tool_spec(
    *,
    tool_spec: dict[str, object],
    prompt: str,
    user_id: str,
    attempt: int,
) -> dict[str, object]:
    invocation = normalize_tool_spec(tool_spec)
    return run_tool(
        name=invocation.name,
        tool_input=invocation.tool_input,
        prompt=prompt,
        user_id=user_id,
        attempt=attempt,
    )
