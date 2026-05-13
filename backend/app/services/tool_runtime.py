from __future__ import annotations

import json
import re
from ast import Add, BinOp, Div, Expression, Mod, Mult, Pow, Sub, UAdd, USub, UnaryOp, parse
from dataclasses import dataclass
from typing import Callable

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
