import json
import re
from collections.abc import Iterator
from datetime import datetime
from time import monotonic
from uuid import uuid4

from app.config import get_settings
from app.providers.base import ProviderCallError, ProviderUsage
from app.services.audit_service import safe_record_audit_event
from app.services.chat_persistence_service import (
    complete_task,
    create_message,
    get_task,
    update_task_status,
    update_task_trace_steps,
)
from app.services.chroma_memory_service import try_append_task_memory
from app.services.provider_service import ProviderSelectionError, get_llm_provider
from app.services.tool_runtime import (
    build_tool_plan_summary,
    build_tool_plan_artifacts,
    execute_configured_tool_registry_provider_preflight,
    build_tool_iteration_context,
    build_tool_prompt_with_observations,
    execute_tool_plan_item_service_actions,
    execute_tool_plan_item_service_execution,
)


class TaskExecutionAbortError(RuntimeError):
    def __init__(
        self,
        *,
        code: str,
        status: str,
        event: str,
        user_message: str,
    ) -> None:
        super().__init__(user_message)
        self.code = code
        self.status = status
        self.event = event
        self.user_message = user_message


def sse_event(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def sse_error_payload(
    *,
    task_id: str,
    message: str,
    code: str,
    fatal: bool,
    retry_count: int = 0,
    step_id: str | None = None,
    detail: str | None = None,
    status_code: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_id": task_id,
        "message": message,
        "code": code,
        "fatal": fatal,
        "retryable": not fatal,
        "retryCount": retry_count,
    }
    if step_id:
        payload["step_id"] = step_id
    if detail:
        payload["detail"] = detail
    if isinstance(status_code, int):
        payload["status_code"] = status_code
    return payload


def _estimate_token_count(text: str) -> int:
    normalized = text.strip()
    if not normalized:
        return 0
    cjk_units = len(re.findall(r"[\u4e00-\u9fff]", normalized))
    latin_words = len(re.findall(r"[A-Za-z0-9_]+", normalized))
    return max(1, cjk_units + latin_words)


def _estimate_usage_cost(*, prompt_tokens: int, completion_tokens: int) -> float | None:
    settings = get_settings()
    prompt_unit = float(settings.usage_prompt_token_price_per_1k)
    completion_unit = float(settings.usage_completion_token_price_per_1k)
    if prompt_unit <= 0 and completion_unit <= 0:
        return None
    cost = (prompt_tokens / 1000.0) * prompt_unit + (
        completion_tokens / 1000.0
    ) * completion_unit
    return round(cost, 8)


def _normalize_usage_token_count(value: int | None) -> int | None:
    if value is None:
        return None
    if value < 0:
        return None
    return int(value)


def _build_usage_payload(
    *,
    prompt_text: str,
    completion_text: str,
    provider_usage: ProviderUsage | None,
) -> dict[str, object]:
    prompt_tokens_estimated = _estimate_token_count(prompt_text)
    completion_tokens_estimated = _estimate_token_count(completion_text)
    prompt_tokens_provider = _normalize_usage_token_count(
        provider_usage.prompt_tokens if provider_usage else None
    )
    completion_tokens_provider = _normalize_usage_token_count(
        provider_usage.completion_tokens if provider_usage else None
    )
    provider_total_tokens = _normalize_usage_token_count(
        provider_usage.total_tokens if provider_usage else None
    )
    prompt_tokens_final = (
        prompt_tokens_provider
        if prompt_tokens_provider is not None
        else prompt_tokens_estimated
    )
    completion_tokens_final = (
        completion_tokens_provider
        if completion_tokens_provider is not None
        else completion_tokens_estimated
    )
    prompt_tokens_source = (
        "provider" if prompt_tokens_provider is not None else "estimated"
    )
    completion_tokens_source = (
        "provider" if completion_tokens_provider is not None else "estimated"
    )
    usage_source = (
        "provider"
        if prompt_tokens_source == "provider"
        or completion_tokens_source == "provider"
        else "estimated"
    )
    payload: dict[str, object] = {
        "prompt_tokens": prompt_tokens_final,
        "completion_tokens": completion_tokens_final,
        "total_tokens": prompt_tokens_final + completion_tokens_final,
        "prompt_tokens_source": prompt_tokens_source,
        "completion_tokens_source": completion_tokens_source,
        "usage_source": usage_source,
        "cost_estimate": _estimate_usage_cost(
            prompt_tokens=prompt_tokens_final,
            completion_tokens=completion_tokens_final,
        ),
        "prompt_token_price_per_1k": get_settings().usage_prompt_token_price_per_1k,
        "completion_token_price_per_1k": get_settings().usage_completion_token_price_per_1k,
    }
    if provider_total_tokens is not None:
        payload["provider_total_tokens"] = provider_total_tokens
    return payload


def _merge_usage_payloads(
    *,
    final_usage: dict[str, object],
    planning_usage: dict[str, object] | None,
) -> dict[str, object]:
    usage_payload = dict(final_usage)
    if planning_usage is None:
        return usage_payload

    planning_prompt_tokens = int(planning_usage.get("prompt_tokens", 0) or 0)
    planning_completion_tokens = int(planning_usage.get("completion_tokens", 0) or 0)
    planning_total_tokens = int(planning_usage.get("total_tokens", 0) or 0)
    final_prompt_tokens = int(final_usage.get("prompt_tokens", 0) or 0)
    final_completion_tokens = int(final_usage.get("completion_tokens", 0) or 0)
    final_total_tokens = int(final_usage.get("total_tokens", 0) or 0)
    planning_cost_estimate = planning_usage.get("cost_estimate")
    final_cost_estimate = final_usage.get("cost_estimate")

    usage_payload.update(
        {
            "planning_prompt_tokens": planning_prompt_tokens,
            "planning_completion_tokens": planning_completion_tokens,
            "planning_total_tokens": planning_total_tokens,
            "planning_prompt_tokens_source": planning_usage.get("prompt_tokens_source"),
            "planning_completion_tokens_source": planning_usage.get(
                "completion_tokens_source"
            ),
            "planning_usage_source": planning_usage.get("usage_source"),
            "planning_cost_estimate": planning_cost_estimate,
            "overall_prompt_tokens": final_prompt_tokens + planning_prompt_tokens,
            "overall_completion_tokens": final_completion_tokens
            + planning_completion_tokens,
            "overall_total_tokens": final_total_tokens + planning_total_tokens,
        }
    )
    if isinstance(planning_usage.get("provider_total_tokens"), int):
        usage_payload["planning_provider_total_tokens"] = planning_usage[
            "provider_total_tokens"
        ]
    if (
        isinstance(planning_cost_estimate, (int, float))
        and isinstance(final_cost_estimate, (int, float))
    ):
        usage_payload["overall_cost_estimate"] = round(
            float(planning_cost_estimate) + float(final_cost_estimate),
            8,
        )
    elif isinstance(final_cost_estimate, (int, float)):
        usage_payload["overall_cost_estimate"] = float(final_cost_estimate)
    elif isinstance(planning_cost_estimate, (int, float)):
        usage_payload["overall_cost_estimate"] = float(planning_cost_estimate)
    else:
        usage_payload["overall_cost_estimate"] = None
    return usage_payload


def stream_task_execution(
    *,
    task_id: str,
    session_id: str,
    user_id: str,
    prompt: str,
    persist_user_message: bool = False,
) -> Iterator[str]:
    STREAM_TRACE_PERSIST_EVERY = 8
    STREAM_HEARTBEAT_INTERVAL_SEC = 2.0
    TASK_STATUS_PROBE_MIN_INTERVAL_SEC = 0.25
    TRACE_PERSIST_MIN_INTERVAL_SEC = max(
        0.0, float(get_settings().trace_persist_min_interval_sec)
    )
    TASK_TIMEOUT_SEC = max(1.0, float(get_settings().task_timeout_sec))
    trace_steps: list[dict[str, object]] = []
    seq_cursor = 0
    last_trace_persist_ts = 0.0
    last_status_probe_ts = 0.0
    cached_task_status = "pending"
    stream_started_ts = monotonic()

    def record_audit_event(
        *,
        event_type: str,
        code: str,
        message: str,
        detail: dict[str, object] | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "task_id": task_id,
            "session_id": session_id,
            "code": code,
            "message": message[:400],
        }
        if detail:
            payload.update(detail)
        safe_record_audit_event(
            user_id=user_id,
            event_type=event_type,
            detail=payload,
        )

    def record_failure_event(
        *,
        event_type: str,
        code: str,
        message: str,
        detail: dict[str, object] | None = None,
    ) -> None:
        record_audit_event(
            event_type=event_type,
            code=code,
            message=message,
            detail=detail,
        )

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
        update_task_trace_steps(task_id, trace_steps, user_id)
        last_trace_persist_ts = now

    def probe_task_status(*, force: bool = False) -> str:
        nonlocal last_status_probe_ts, cached_task_status
        now = monotonic()
        if (
            not force
            and last_status_probe_ts > 0
            and now - last_status_probe_ts < TASK_STATUS_PROBE_MIN_INTERVAL_SEC
        ):
            return cached_task_status
        task = get_task(task_id, user_id)
        if task is None:
            cached_task_status = "missing"
        else:
            cached_task_status = str(task.get("status", "")).strip().lower()
        last_status_probe_ts = now
        return cached_task_status

    def raise_if_should_abort(*, force_status_probe: bool = False) -> None:
        status = probe_task_status(force=force_status_probe)
        if status in {"cancelled", "canceled"}:
            raise TaskExecutionAbortError(
                code="task_cancelled",
                status="cancelled",
                event="cancelled",
                user_message="Task was cancelled by user.",
            )
        if status in {"timed_out", "timeout"}:
            raise TaskExecutionAbortError(
                code="task_timeout",
                status="timed_out",
                event="timeout",
                user_message="Task exceeded timeout limit.",
            )
        elapsed = monotonic() - stream_started_ts
        if elapsed >= TASK_TIMEOUT_SEC:
            update_task_status(task_id=task_id, status="timed_out", user_id=user_id)
            probe_task_status(force=True)
            raise TaskExecutionAbortError(
                code="task_timeout",
                status="timed_out",
                event="timeout",
                user_message=(
                    f"Task timed out after {TASK_TIMEOUT_SEC:.1f}s. "
                    "Please retry with a shorter request or cancel earlier."
                ),
            )
        if status == "missing":
            raise TaskExecutionAbortError(
                code="task_not_found",
                status="failed",
                event="error",
                user_message="Task no longer exists.",
            )

    if persist_user_message:
        create_message(
            session_id=session_id,
            user_id=user_id,
            task_id=task_id,
            role="user",
            content=prompt,
        )

    update_task_status(task_id=task_id, status="running", user_id=user_id)
    probe_task_status(force=True)

    try:
        provider = get_llm_provider(user_id)
        raise_if_should_abort(force_status_probe=True)

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
        tool_plan_artifacts = build_tool_plan_artifacts(prompt, provider=provider)
        tool_plan = tool_plan_artifacts.tool_plan
        plan_content = build_tool_plan_summary(tool_plan)
        planning_usage_payload = None
        plan_meta: dict[str, object] = {
            "model": getattr(provider, "model", "mock-gpt"),
            "step_type": "planning",
            "label": "tool_plan",
            "tokens": _estimate_token_count(plan_content),
            "cost_estimate": None,
        }
        if tool_plan_artifacts.planning_provider_attempted:
            planning_usage_payload = _build_usage_payload(
                prompt_text=tool_plan_artifacts.planning_prompt or prompt,
                completion_text=plan_content,
                provider_usage=tool_plan_artifacts.provider_usage,
            )
            plan_meta.update(
                {
                    "tokens": planning_usage_payload["completion_tokens"],
                    "cost_estimate": planning_usage_payload["cost_estimate"],
                    "prompt_tokens": planning_usage_payload["prompt_tokens"],
                    "completion_tokens": planning_usage_payload["completion_tokens"],
                    "usage_source": planning_usage_payload["usage_source"],
                    "planning_provider_used": tool_plan_artifacts.planning_provider_used,
                }
            )
        plan_step = {
            "id": plan_step_id,
            "seq": seq_cursor,
            "type": "thought",
            "content": plan_content,
            "meta": plan_meta,
        }
        trace_steps.append(plan_step)
        yield sse_event(
            "trace",
            {"task_id": task_id, "step_id": plan_step_id, "step": plan_step},
        )
        persist_trace(force=True)

        tool_observations: list[str] = []
        tool_registry_service_result = execute_configured_tool_registry_provider_preflight(
            task_id=task_id,
            step_id=str(uuid4()),
            seq=seq_cursor + 1,
            model=getattr(provider, "model", "mock-gpt"),
            trace_steps=trace_steps,
            persist_trace_fn=persist_trace,
            record_audit_event_fn=record_audit_event,
        )
        tool_registry_provider = tool_registry_service_result["provider"]

        for idx, tool_spec in enumerate(tool_plan, start=1):
            raise_if_should_abort()
            tool_name = str(tool_spec["name"])
            tool_input = tool_spec.get("input")
            if not isinstance(tool_input, dict):
                tool_input = {}
            action_step_id = str(uuid4())
            iteration_ctx = build_tool_iteration_context(
                step_id=action_step_id,
                seq=seq_cursor + 1,
                name=tool_name,
                tool_input=tool_input,
                model=getattr(provider, "model", "mock-gpt"),
                label=f"tool_{idx}",
                token_count=_estimate_token_count(
                    f"{tool_name} {json.dumps(tool_input, ensure_ascii=False)}"
                ),
            )
            action_step = iteration_ctx["action_step"]
            seq_cursor += 1
            action_step["seq"] = seq_cursor

            service_execution = None
            for item in execute_tool_plan_item_service_execution(
                task_id=task_id,
                trace_steps=trace_steps,
                iteration_ctx=iteration_ctx,
                initial_action_step=action_step,
                tool_name=tool_name,
                tool_input=tool_input,
                prompt=prompt,
                user_id=user_id,
                model=getattr(provider, "model", "mock-gpt"),
                estimate_token_count=_estimate_token_count,
                make_step_id=lambda: str(uuid4()),
                raise_if_should_abort=raise_if_should_abort,
                registry_provider=tool_registry_provider,
            ):
                if item["kind"] == "event":
                    yield sse_event(str(item["event"]), item["data"])
                    continue
                service_execution = item["result"]

            assert service_execution is not None
            service_action_result = None
            for item in execute_tool_plan_item_service_actions(
                service_actions=service_execution["service_actions"],
                trace_steps=trace_steps,
                tool_observations=tool_observations,
                seq_cursor=seq_cursor,
                persist_trace_fn=persist_trace,
                complete_task_fn=complete_task,
                record_failure_event_fn=record_failure_event,
            ):
                if item["kind"] == "event":
                    yield sse_event(str(item["event"]), item["data"])
                    continue
                service_action_result = item["result"]

            assert service_action_result is not None
            seq_cursor = int(service_action_result["seq_cursor"])
            if bool(service_action_result["should_return"]):
                    return

        yield sse_event("state", {"task_id": task_id, "phase": "streaming"})
        raise_if_should_abort()
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

        provider_prompt = build_tool_prompt_with_observations(
            prompt=prompt,
            tool_observations=tool_observations,
        )
        stream_chunk_count = 0
        provider_usage: ProviderUsage | None = None
        get_last_usage = getattr(provider, "get_last_usage", None)

        streamed_content = ""
        final_step_seq = int(final_step_streaming.get("seq", seq_cursor))
        for chunk in provider.stream_generate(provider_prompt):
            raise_if_should_abort()
            stream_chunk_count += 1
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
            should_persist = stream_chunk_count % STREAM_TRACE_PERSIST_EVERY == 0
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
        if callable(get_last_usage):
            latest_usage = get_last_usage()
            if isinstance(latest_usage, ProviderUsage):
                provider_usage = latest_usage
        if not final_content:
            raise_if_should_abort(force_status_probe=True)
            fallback = provider.generate(provider_prompt)
            final_content = fallback.content
            if isinstance(getattr(fallback, "usage", None), ProviderUsage):
                provider_usage = fallback.usage
            elif callable(get_last_usage):
                latest_usage = get_last_usage()
                if isinstance(latest_usage, ProviderUsage):
                    provider_usage = latest_usage
        else:
            final_step_seq += 1
        final_usage_payload = _build_usage_payload(
            prompt_text=provider_prompt,
            completion_text=final_content,
            provider_usage=provider_usage,
        )
        trace_steps[-1] = {
            **final_step_streaming,
            "content": final_content,
            "seq": final_step_seq,
            "meta": {
                **dict(final_step_streaming.get("meta", {})),
                "tokens": final_usage_payload["completion_tokens"],
                "cost_estimate": final_usage_payload["cost_estimate"],
            },
        }
        persist_trace(force=True)

        create_message(
            session_id=session_id,
            user_id=user_id,
            task_id=task_id,
            role="assistant",
            content=final_content,
        )

        usage_payload = _merge_usage_payloads(
            final_usage=final_usage_payload,
            planning_usage=planning_usage_payload,
        )

        complete_task(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
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

    except TaskExecutionAbortError as exc:
        complete_task(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
            status=exc.status,
        )
        if exc.event == "timeout":
            record_failure_event(
                event_type="task_timeout",
                code=exc.code,
                message=exc.user_message,
            )
        elif exc.event not in {"cancelled"}:
            record_failure_event(
                event_type="task_failed",
                code=exc.code,
                message=exc.user_message,
            )
        phase = exc.event if exc.event in {"cancelled", "timeout"} else "error"
        yield sse_event("state", {"task_id": task_id, "phase": phase})
        if exc.event in {"cancelled", "timeout"}:
            yield sse_event(
                exc.event,
                {
                    "task_id": task_id,
                    "status": exc.status,
                    "code": exc.code,
                    "message": exc.user_message,
                },
            )
        yield sse_event(
            "error",
            sse_error_payload(
                task_id=task_id,
                message=exc.user_message,
                code=exc.code,
                fatal=True,
                retry_count=0,
            ),
        )
    except ProviderSelectionError as exc:
        complete_task(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
            status="failed",
        )
        record_failure_event(
            event_type="task_failed",
            code=exc.code,
            message=exc.user_message,
        )
        yield sse_event("state", {"task_id": task_id, "phase": "error"})
        yield sse_event(
            "error",
            sse_error_payload(
                task_id=task_id,
                message=exc.user_message,
                code=exc.code,
                fatal=True,
                retry_count=0,
            ),
        )
    except ProviderCallError as exc:
        complete_task(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
            status="failed",
        )
        record_failure_event(
            event_type="task_failed",
            code=exc.code,
            message=exc.user_message,
            detail={
                "status_code": exc.status_code,
                "retryable": exc.retryable,
            },
        )
        yield sse_event("state", {"task_id": task_id, "phase": "error"})
        yield sse_event(
            "error",
            sse_error_payload(
                task_id=task_id,
                message=exc.user_message,
                code=exc.code,
                fatal=not exc.retryable,
                retry_count=0,
                detail=exc.detail,
                status_code=exc.status_code,
            ),
        )
    except Exception as exc:
        complete_task(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
            status="failed",
        )
        record_failure_event(
            event_type="task_failed",
            code="task_stream_failure",
            message=str(exc),
        )
        yield sse_event("state", {"task_id": task_id, "phase": "error"})
        yield sse_event(
            "error",
            sse_error_payload(
                task_id=task_id,
                message=str(exc),
                code="task_stream_failure",
                fatal=True,
                retry_count=0,
            ),
        )
