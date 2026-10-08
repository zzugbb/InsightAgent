import json
import re
from asyncio import CancelledError
from collections.abc import Iterator
from datetime import datetime
from time import monotonic, sleep
from uuid import uuid4

from app.config import get_settings
from app.providers.base import ProviderCallError, ProviderUsage
from app.providers.completion_signals import normalize_finish_reason
from app.services.answer_completion import with_execution_evidence, with_tool_stop_context
from app.services.audit_service import safe_record_audit_event
from app.services.chat_persistence_service import (
    complete_task,
    create_message,
    get_task_execution_owner_id,
    get_task,
    mark_task_queued_waiting,
    mark_task_running_started,
    touch_task_execution_heartbeat,
    update_task_status,
    update_task_trace_steps,
)
from app.services.chroma_memory_service import try_append_task_memory
from app.services.conversation_context import ConversationContext, load_conversation_context
from app.services.agent_tool_context import with_model_observations
from app.services.provider_service import ProviderSelectionError, get_llm_provider
from app.services.settings_service import get_stored_settings
from app.services.task_checkpoint_service import checkpoint_plan, restored_prefix, validate_resume
from app.services.task_tool_execution import execute_task_tool_plan
from app.services.task_terminal_usage import build_terminal_usage
from app.services.agent_feedback import AgentFeedbackLoop, FeedbackDecision, feedback_enabled, sum_planning_usage
from app.services.task_queue_service import (
    forget_waiting_task,
    get_task_queue_snapshot,
    release_task_execution_slot,
    try_acquire_task_execution_slot,
)
from app.services.tool_runtime import (
    build_safe_tool_registry_provider_source_alias_map,
    build_tool_plan_summary,
    build_tool_plan_artifacts,
    execute_configured_tool_registry_provider_preflight,
    get_configured_tool_registry_provider,
    get_tool_display_name,
    get_tool_registry_profile_name_from_settings,
    get_tool_registry_provider_source_name_from_settings,
    build_tool_iteration_context,
    build_tool_prompt_with_observations,
    execute_tool_plan_item_service_actions,
    execute_tool_plan_item_service_execution,
    resolve_tool_registration,
    StaticToolRegistryProvider,
    _sanitize_tool_runtime_provider_source_name_for_artifact,
    sanitize_tool_registry_diagnostics_artifact_payload,
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


_SSE_PROVIDER_SOURCE_TEXT_RE = re.compile(
    r"(?i)\b("
    r"provider_source|provider_source_name|tool_registry_provider_source"
    r")(\s*[:=]\s*)([^\s,;}\]]+)"
)


def _iter_sse_provider_source_text_values(*values: object) -> Iterator[str]:
    for value in values:
        if value is None:
            continue
        text = str(value)
        for match in _SSE_PROVIDER_SOURCE_TEXT_RE.finditer(text):
            raw_source = match.group(3).strip("\"'")
            if raw_source:
                yield raw_source


def _build_sse_provider_source_aliases(*values: object) -> dict[str, str]:
    source_names: list[str] = []
    seen_source_names: set[str] = set()
    for source_name in _iter_sse_provider_source_text_values(*values):
        if source_name in seen_source_names:
            continue
        seen_source_names.add(source_name)
        source_names.append(source_name)
    return build_safe_tool_registry_provider_source_alias_map(source_names)


def _sanitize_sse_provider_source_text(
    value: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> str:
    text = str(value)

    def redact(match: re.Match[str]) -> str:
        key = match.group(1)
        separator = match.group(2)
        raw_source = match.group(3).strip("\"'")
        safe_source = (provider_source_aliases or {}).get(
            raw_source,
            _sanitize_tool_runtime_provider_source_name_for_artifact(raw_source),
        )
        return f"{key}{separator}{safe_source}"

    return _SSE_PROVIDER_SOURCE_TEXT_RE.sub(redact, text)


def _classify_sse_error_category(code: str) -> str:
    if code in {"remote_api_key_required", "remote_base_url_required"}:
        return "remote_provider"
    if code.startswith("remote_provider_") or code.startswith("remote_api_key_"):
        return "remote_provider"
    if code.startswith("task_queue_"):
        return "task_queue"
    if code in {"task_cancelled", "task_timeout", "task_not_found"}:
        return "task_lifecycle"
    if code.startswith("task_stream_"):
        return "task_stream"
    if code.startswith("tool_"):
        return "tool_runtime"
    return "unknown"


def _classify_http_status_family(status_code: int | None) -> str | None:
    if not isinstance(status_code, int) or status_code < 100:
        return None
    return f"{status_code // 100}xx"


def _classify_sse_error_reason(code: str, status_code: int | None = None) -> str:
    reason_by_code = {
        "remote_provider_network_error": "network",
        "remote_provider_stream_interrupted": "network",
        "remote_api_key_unauthorized": "auth",
        "remote_provider_rate_limited": "rate_limit",
        "remote_provider_upstream_error": "upstream",
        "remote_provider_invalid_json": "invalid_response",
        "remote_provider_stream_invalid_json": "invalid_response",
        "remote_provider_empty_response": "empty_response",
        "remote_api_key_required": "auth",
        "remote_base_url_required": "config",
        "invalid_runtime_mode": "config",
        "task_cancelled": "cancelled",
        "task_timeout": "timeout",
        "task_not_found": "not_found",
    }
    reason = reason_by_code.get(code)
    if reason:
        return reason
    if code == "remote_provider_http_error":
        if status_code in {401, 403}:
            return "auth"
        if status_code == 429:
            return "rate_limit"
        if isinstance(status_code, int) and 500 <= status_code <= 599:
            return "upstream"
        return "http_error"
    if code.startswith("task_queue_"):
        return "queue"
    if code.startswith("tool_"):
        return "tool"
    if code.startswith("task_stream_"):
        return "stream"
    return "unknown"


def _build_sse_error_diagnostic(
    *,
    code: str,
    fatal: bool,
    has_detail: bool,
    status_code: int | None = None,
) -> dict[str, object]:
    return {
        "category": _classify_sse_error_category(code),
        "reason": _classify_sse_error_reason(code, status_code),
        "recoverability": "fatal" if fatal else "retryable",
        "http_status_family": _classify_http_status_family(status_code),
        "has_detail": has_detail,
    }


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
    safe_message = sanitize_tool_registry_diagnostics_artifact_payload(message)
    if not isinstance(safe_message, str):
        safe_message = message
    safe_detail_text: str | None = None
    if detail:
        safe_detail = sanitize_tool_registry_diagnostics_artifact_payload(detail)
        safe_detail_text = safe_detail if isinstance(safe_detail, str) else detail
    provider_source_aliases = _build_sse_provider_source_aliases(
        safe_message,
        safe_detail_text,
    )
    safe_message = _sanitize_sse_provider_source_text(
        safe_message,
        provider_source_aliases=provider_source_aliases,
    )
    payload: dict[str, object] = {
        "task_id": task_id,
        "message": safe_message,
        "code": code,
        "fatal": fatal,
        "retryable": not fatal,
        "retryCount": retry_count,
        "diagnostic": _build_sse_error_diagnostic(
            code=code,
            fatal=fatal,
            status_code=status_code,
            has_detail=bool(safe_detail_text),
        ),
    }
    if step_id:
        payload["step_id"] = step_id
    if safe_detail_text:
        payload["detail"] = _sanitize_sse_provider_source_text(
            safe_detail_text,
            provider_source_aliases=provider_source_aliases,
        )
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
    # Reuse the recorded-field rules so partial failed planning stays unknown, not zero.
    return build_terminal_usage(
        planning_usage=planning_usage, final_usage=final_usage, provider_usage=None,
        prompt_price=0, completion_price=0,
    ) or dict(final_usage)


def _resolve_provider_identity(
    *,
    provider: object,
    runtime_settings: object,
) -> tuple[str, str]:
    provider_name = str(
        getattr(provider, "provider", None)
        or getattr(runtime_settings, "provider", None)
        or "mock"
    ).strip()
    model_name = str(
        getattr(provider, "model", None)
        or getattr(runtime_settings, "model", None)
        or getattr(runtime_settings, "model_name", None)
        or "mock-gpt"
    ).strip()
    return (provider_name or "mock", model_name or "mock-gpt")


def stream_task_execution(
    *,
    task_id: str,
    session_id: str,
    user_id: str,
    prompt: str,
    persist_user_message: bool = False,
    checkpoint_seed: dict | None = None,
) -> Iterator[str]:
    STREAM_TRACE_PERSIST_EVERY = 8
    STREAM_HEARTBEAT_INTERVAL_SEC = 2.0
    TASK_STATUS_PROBE_MIN_INTERVAL_SEC = 0.25
    runtime_config = get_settings()
    TRACE_PERSIST_MIN_INTERVAL_SEC = max(
        0.0, float(runtime_config.trace_persist_min_interval_sec)
    )
    TASK_TIMEOUT_SEC = max(1.0, float(runtime_config.task_timeout_sec))
    TASK_QUEUE_MAX_CONCURRENT = max(
        1,
        int(getattr(runtime_config, "task_queue_max_concurrent", 1) or 1),
    )
    TASK_QUEUE_MAX_CONCURRENT_PER_USER = max(
        0,
        int(getattr(runtime_config, "task_queue_max_concurrent_per_user", 0) or 0),
    )
    TASK_QUEUE_MAX_CONCURRENT_PER_SESSION = max(
        0,
        int(
            getattr(runtime_config, "task_queue_max_concurrent_per_session", 0) or 0
        ),
    )
    TASK_QUEUE_POLL_INTERVAL_SEC = max(
        0.01,
        float(getattr(runtime_config, "task_queue_poll_interval_sec", 0.25) or 0.25),
    )
    TASK_EXECUTION_OWNER_ID = get_task_execution_owner_id(runtime_config)
    TASK_EXECUTION_HEARTBEAT_INTERVAL_SEC = max(
        0.0,
        float(
            getattr(runtime_config, "task_execution_heartbeat_interval_sec", 2.0)
            or 0.0
        ),
    )
    trace_steps: list[dict[str, object]] = []
    seq_cursor = 0
    last_trace_persist_ts = 0.0
    last_status_probe_ts = 0.0
    last_execution_heartbeat_ts = 0.0
    cached_task_status = "pending"
    stream_started_ts = monotonic()
    task_slot = None
    task_running_started = False
    planning_usage_payload = None
    final_usage_payload = None
    provider = None
    final_call_started = False
    agent_stop_reason = None

    def capture_final_finish_reason(response_reason=None):
        if not final_call_started or not trace_steps or (trace_steps[-1].get("meta") or {}).get("step_type") != "final_answer":
            return
        reason = normalize_finish_reason(response_reason)
        getter = getattr(provider, "get_last_finish_reason", None)
        if reason is None and callable(getter):
            try:
                reason = normalize_finish_reason(getter())
            except Exception:
                return
        if reason is not None and (trace_steps[-1].get("meta") or {}).get("provider_finish_reason") != reason:
            step = trace_steps[-1]
            trace_steps[-1] = {**step, "seq": int(step["seq"]) + 1,
                              "meta": {**step.get("meta", {}), "provider_finish_reason": reason}}

    def terminal_usage():
        captured = None
        if final_call_started and final_usage_payload is None:
            getter = getattr(provider, "get_last_usage", None)
            if callable(getter):
                try:
                    captured = getter()
                except Exception:
                    pass  # Usage diagnostics must not replace the original failure.
        return build_terminal_usage(
            planning_usage=planning_usage_payload, final_usage=final_usage_payload,
            provider_usage=captured,
            prompt_price=float(getattr(runtime_config, "usage_prompt_token_price_per_1k", 0)),
            completion_price=float(getattr(runtime_config, "usage_completion_token_price_per_1k", 0)),
        )

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
        safe_detail = dict(detail or {})
        if "diagnostic" not in safe_detail:
            status_code_value = safe_detail.get("status_code")
            status_code = (
                status_code_value if isinstance(status_code_value, int) else None
            )
            retryable_value = safe_detail.get("retryable")
            fatal = not retryable_value if isinstance(retryable_value, bool) else True
            safe_detail["diagnostic"] = _build_sse_error_diagnostic(
                code=code,
                fatal=fatal,
                status_code=status_code,
                has_detail=False,
            )
        record_audit_event(
            event_type=event_type,
            code=code,
            message=message,
            detail=safe_detail,
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

    def maybe_touch_execution_heartbeat(*, now: float | None = None) -> None:
        nonlocal last_execution_heartbeat_ts
        if TASK_EXECUTION_HEARTBEAT_INTERVAL_SEC <= 0:
            return
        current_ts = monotonic() if now is None else now
        if (
            last_execution_heartbeat_ts > 0
            and current_ts - last_execution_heartbeat_ts
            < TASK_EXECUTION_HEARTBEAT_INTERVAL_SEC
        ):
            return
        touch_task_execution_heartbeat(
            task_id=task_id,
            user_id=user_id,
            execution_owner_id=TASK_EXECUTION_OWNER_ID,
        )
        last_execution_heartbeat_ts = current_ts

    def build_abort_error_for_status(
        status: str,
        *,
        timeout_message: str | None = None,
    ) -> TaskExecutionAbortError | None:
        if status in {"cancelled", "canceled"}:
            return TaskExecutionAbortError(
                code="task_cancelled",
                status="cancelled",
                event="cancelled",
                user_message="Task was cancelled by user.",
            )
        if status in {"timed_out", "timeout"}:
            return TaskExecutionAbortError(
                code="task_timeout",
                status="timed_out",
                event="timeout",
                user_message=timeout_message or "Task exceeded timeout limit.",
            )
        if status == "missing":
            return TaskExecutionAbortError(
                code="task_not_found",
                status="failed",
                event="error",
                user_message="Task no longer exists.",
            )
        return None

    def terminal_abort_after_lost_race() -> TaskExecutionAbortError | None:
        return build_abort_error_for_status(probe_task_status(force=True))

    def terminal_write_lost(completed_count: object) -> bool:
        if completed_count is None:
            return False
        try:
            return int(completed_count) <= 0
        except (TypeError, ValueError):
            return False

    def persist_abort_terminal_status(
        exc: TaskExecutionAbortError,
    ) -> TaskExecutionAbortError:
        capture_final_finish_reason()
        completed_count = complete_task(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
            status=exc.status,
            usage=terminal_usage(),
            execution_owner_id=TASK_EXECUTION_OWNER_ID,
        )
        if terminal_write_lost(completed_count):
            terminal_exc = terminal_abort_after_lost_race()
            if terminal_exc is not None:
                return terminal_exc
        return exc

    def complete_task_for_service_action(**kwargs: object) -> object:
        kwargs.setdefault("execution_owner_id", TASK_EXECUTION_OWNER_ID)
        if kwargs.get("status", "completed") != "completed":
            kwargs.setdefault("usage", terminal_usage())
        completed_count = complete_task(**kwargs)
        if terminal_write_lost(completed_count):
            terminal_exc = terminal_abort_after_lost_race()
            if terminal_exc is not None:
                raise terminal_exc
        return completed_count

    def emit_abort_events(exc: TaskExecutionAbortError) -> Iterator[str]:
        effective_exc = persist_abort_terminal_status(exc)
        if effective_exc.event == "timeout":
            record_failure_event(
                event_type="task_timeout",
                code=effective_exc.code,
                message=effective_exc.user_message,
            )
        elif effective_exc.event not in {"cancelled"}:
            record_failure_event(
                event_type="task_failed",
                code=effective_exc.code,
                message=effective_exc.user_message,
            )
        phase = (
            effective_exc.event
            if effective_exc.event in {"cancelled", "timeout"}
            else "error"
        )
        yield sse_event("state", {"task_id": task_id, "phase": phase})
        if effective_exc.event in {"cancelled", "timeout"}:
            yield sse_event(
                effective_exc.event,
                {
                    "task_id": task_id,
                    "status": effective_exc.status,
                    "code": effective_exc.code,
                    "message": effective_exc.user_message,
                },
            )
        yield sse_event(
            "error",
            sse_error_payload(
                task_id=task_id,
                message=effective_exc.user_message,
                code=effective_exc.code,
                fatal=True,
                retry_count=0,
            ),
        )

    def raise_if_should_abort(*, force_status_probe: bool = False) -> None:
        status = probe_task_status(force=force_status_probe)
        abort_error = build_abort_error_for_status(status)
        if abort_error is not None:
            raise abort_error
        elapsed = monotonic() - stream_started_ts
        if elapsed >= TASK_TIMEOUT_SEC:
            timeout_message = (
                f"Task timed out after {TASK_TIMEOUT_SEC:.1f}s. "
                "Please retry with a shorter request or cancel earlier."
            )
            capture_final_finish_reason()
            complete_task(
                task_id=task_id,
                trace_steps=trace_steps,
                user_id=user_id,
                status="timed_out",
                usage=terminal_usage(),
                execution_owner_id=TASK_EXECUTION_OWNER_ID,
            )
            abort_error = build_abort_error_for_status(
                probe_task_status(force=True),
                timeout_message=timeout_message,
            )
            if abort_error is not None:
                raise abort_error
            raise TaskExecutionAbortError(
                code="task_timeout",
                status="timed_out",
                event="timeout",
                user_message=timeout_message,
            )

    if persist_user_message:
        create_message(
            session_id=session_id,
            user_id=user_id,
            task_id=task_id,
            role="user",
            content=prompt,
        )

    def release_task_slot() -> None:
        nonlocal task_slot
        if task_slot is None:
            forget_waiting_task(task_id)
            return
        task_slot.release()
        task_slot = None

    try:
        while task_slot is None:
            raise_if_should_abort(force_status_probe=True)
            task_slot = try_acquire_task_execution_slot(
                task_id=task_id,
                max_concurrent=TASK_QUEUE_MAX_CONCURRENT,
                user_id=user_id,
                session_id=session_id,
                max_concurrent_per_user=TASK_QUEUE_MAX_CONCURRENT_PER_USER,
                max_concurrent_per_session=TASK_QUEUE_MAX_CONCURRENT_PER_SESSION,
            )
            if task_slot is not None:
                break
            if cached_task_status not in {"queued", "queueing", "enqueued"}:
                queued_marked_count = mark_task_queued_waiting(
                    task_id=task_id,
                    user_id=user_id,
                )
                probe_task_status(force=True)
                if queued_marked_count <= 0:
                    release_task_slot()
                    record_failure_event(
                        event_type="task_failed",
                        code="task_queue_start_conflict",
                        message="Task could not be marked queued before waiting.",
                    )
                    yield sse_event("state", {"task_id": task_id, "phase": "error"})
                    yield sse_event(
                        "error",
                        sse_error_payload(
                            task_id=task_id,
                            message="Task could not be marked queued before waiting.",
                            code="task_queue_start_conflict",
                            fatal=True,
                            retry_count=0,
                        ),
                    )
                    return
            yield sse_event(
                "state",
                {
                    "task_id": task_id,
                    "phase": "queued",
                    "queue": get_task_queue_snapshot(
                        max_concurrent=TASK_QUEUE_MAX_CONCURRENT,
                        task_id=task_id,
                    ),
                },
            )
            sleep(TASK_QUEUE_POLL_INTERVAL_SEC)

        running_started_count = mark_task_running_started(
            task_id=task_id,
            user_id=user_id,
            execution_owner_id=TASK_EXECUTION_OWNER_ID,
        )
        last_execution_heartbeat_ts = monotonic()
        probe_task_status(force=True)
        if running_started_count <= 0:
            raise_if_should_abort()
            release_task_slot()
            record_failure_event(
                event_type="task_failed",
                code="task_start_conflict",
                message="Task could not be marked running before execution started.",
            )
            yield sse_event("state", {"task_id": task_id, "phase": "error"})
            yield sse_event(
                "error",
                sse_error_payload(
                    task_id=task_id,
                    message="Task could not be marked running before execution started.",
                    code="task_start_conflict",
                    fatal=True,
                    retry_count=0,
                ),
            )
            return
        task_running_started = True

        runtime_settings = get_stored_settings(user_id)
        provider = get_llm_provider(user_id)
        provider_name, provider_model = _resolve_provider_identity(
            provider=provider,
            runtime_settings=runtime_settings,
        )
        raise_if_should_abort(force_status_probe=True)

        conversation = (load_conversation_context(task_id=task_id, session_id=session_id, user_id=user_id)
                        if provider_name != "mock" and checkpoint_seed is None else ConversationContext([]))
        model_prompt = conversation.with_prompt(prompt)
        raise_if_should_abort(force_status_probe=True)

        yield sse_event(
            "start",
            {
                "session_id": session_id,
                "task_id": task_id,
                "provider": provider_name,
                "model": provider_model,
            },
        )
        yield sse_event("state", {"task_id": task_id, "phase": "thinking"})

        plan_step_id = str(uuid4())
        seq_cursor += 1
        planning_registry_provider = get_configured_tool_registry_provider(
            settings=runtime_settings
        )
        tool_plan_artifacts = None
        if checkpoint_seed is not None:
            tool_plan = validate_resume(checkpoint_seed, planning_registry_provider)
        else:
            tool_plan_artifacts = build_tool_plan_artifacts(
                prompt, provider=provider, registry_provider=planning_registry_provider,
                **({"planning_prompt": model_prompt} if conversation.messages else {}),
            )
            tool_plan = tool_plan_artifacts.tool_plan
        plan_content = build_tool_plan_summary(
            tool_plan,
            registry_provider=planning_registry_provider,
        )
        use_feedback = feedback_enabled(
            tool_plan_artifacts, registry_provider=planning_registry_provider,
            checkpoint_seed=checkpoint_seed, max_rounds=getattr(runtime_config, "agent_max_rounds", 3),
        )
        agent_round = 1
        plan_meta: dict[str, object] = {
            "model": provider_model,
            "step_type": "planning",
            "label": "tool_plan",
            "tokens": _estimate_token_count(plan_content),
            "cost_estimate": None,
            "planning_provider_attempted": bool(tool_plan_artifacts and tool_plan_artifacts.planning_provider_attempted),
            "planning_provider_used": bool(tool_plan_artifacts and tool_plan_artifacts.planning_provider_used),
            "allowed_tool_names": (list(tool_plan_artifacts.allowed_tool_names) if tool_plan_artifacts
                                   else [node["name"] for node in tool_plan]),
            "allowed_tool_labels": (list(tool_plan_artifacts.allowed_tool_labels) if tool_plan_artifacts else [
                get_tool_display_name(node["name"], registry_provider=planning_registry_provider)
                for node in tool_plan
            ]),
            "tool_registry_profile": get_tool_registry_profile_name_from_settings(
                settings=runtime_settings
            ),
            "tool_registry_provider_source": get_tool_registry_provider_source_name_from_settings(
                settings=runtime_settings
            ),
        }
        if provider_name != "mock" and checkpoint_seed is None:
            plan_meta["conversation_context"] = conversation.summary
        saved_plan = None if use_feedback else checkpoint_plan(tool_plan, planning_registry_provider)
        if saved_plan is not None:
            plan_meta["checkpoint_plan"] = saved_plan
        if checkpoint_seed is not None:
            plan_meta.update(
                tokens=0, cost_estimate=0.0, checkpoint_resumed=True,
                checkpoint_source_step_id=checkpoint_seed["source_step_id"],
                checkpoint_start_index=checkpoint_seed["start_index"],
            )
        if tool_plan_artifacts and tool_plan_artifacts.planning_provider_attempted:
            if tool_plan_artifacts.planning_provider_failed:
                planning_usage_payload = build_terminal_usage(
                    planning_usage=None, final_usage=None, provider_usage=tool_plan_artifacts.provider_usage,
                    prompt_price=float(getattr(runtime_config, "usage_prompt_token_price_per_1k", 0)),
                    completion_price=float(getattr(runtime_config, "usage_completion_token_price_per_1k", 0)),
                )
            else:
                planning_usage_payload = _build_usage_payload(
                    prompt_text=tool_plan_artifacts.planning_prompt or prompt,
                    completion_text=plan_content,
                    provider_usage=tool_plan_artifacts.provider_usage,
                )
            recorded_planning = planning_usage_payload or {}
            plan_meta.update(
                {
                    "tokens": recorded_planning.get("completion_tokens"),
                    "cost_estimate": recorded_planning.get("cost_estimate"),
                    "prompt_tokens": recorded_planning.get("prompt_tokens"),
                    "completion_tokens": recorded_planning.get("completion_tokens"),
                    "usage_source": recorded_planning.get("usage_source"),
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
        if checkpoint_seed is not None:
            reused_steps, reused_observations = restored_prefix(checkpoint_seed, seq_cursor + 1)
            tool_observations.extend(reused_observations)
            for reused_step in reused_steps:
                raise_if_should_abort()
                seq_cursor += 1
                trace_steps.append(reused_step)
                yield sse_event("trace", {"task_id": task_id, "step_id": reused_step["id"], "step": reused_step})
            persist_trace(force=True)
        tool_registry_service_result = execute_configured_tool_registry_provider_preflight(
            task_id=task_id,
            step_id=str(uuid4()),
            seq=seq_cursor + 1,
            model=provider_model,
            trace_steps=trace_steps,
            persist_trace_fn=persist_trace,
            record_audit_event_fn=record_audit_event,
            settings=runtime_settings,
        )
        tool_registry_provider = tool_registry_service_result["provider"]
        if use_feedback:
            tool_registry_provider = StaticToolRegistryProvider(tool_registry_provider.load_tool_registry())

        def prepare_iteration(idx, tool_spec, seq, batch_provider):
            tool_name = str(tool_spec["name"])
            tool_input = tool_spec.get("input")
            if not isinstance(tool_input, dict):
                tool_input = {}
            action_step_id = str(uuid4())
            iteration_ctx = build_tool_iteration_context(
                step_id=action_step_id,
                seq=seq,
                name=tool_name,
                tool_input=tool_input,
                model=provider_model,
                label=f"tool_{idx}",
                token_count=_estimate_token_count(
                    f"{tool_name} {json.dumps(tool_input, ensure_ascii=False)}"
                ),
                display_name=get_tool_display_name(
                    tool_name,
                    registry_provider=batch_provider,
                ),
                registration=resolve_tool_registration(
                    tool_name,
                    registry_provider=batch_provider,
                ),
                registry_provider=batch_provider,
            )
            if use_feedback:
                iteration_ctx["action_step"]["meta"]["agent_round"] = agent_round
            return iteration_ctx

        feedback_loop = AgentFeedbackLoop(
            initial_plan=tool_plan, max_rounds=getattr(runtime_config, "agent_max_rounds", 3),
            registry_provider=tool_registry_provider,
        ) if use_feedback else None
        while True:
            tool_result = None
            for item in execute_task_tool_plan(
                tool_plan=tool_plan, max_concurrent=int(getattr(runtime_config, "task_tool_max_concurrent", 1)),
                registry_provider=tool_registry_provider, seq_cursor=seq_cursor, task_id=task_id,
                trace_steps=trace_steps, tool_observations=tool_observations, prompt=prompt,
                user_id=user_id, model=provider_model, prepare_iteration=prepare_iteration,
                estimate_token_count=_estimate_token_count, raise_if_should_abort=raise_if_should_abort,
                touch_heartbeat=maybe_touch_execution_heartbeat,
                execute_item=execute_tool_plan_item_service_execution, apply_actions=execute_tool_plan_item_service_actions,
                persist_trace_fn=persist_trace, complete_task_fn=complete_task_for_service_action,
                record_failure_event_fn=record_failure_event,
                checkpoint_start_index=checkpoint_seed["start_index"] if checkpoint_seed else 1,
                checkpoint_enabled=saved_plan is not None,
                confirm_should_continue=lambda: raise_if_should_abort(force_status_probe=True),
                allow_tool_input=feedback_loop.allow_resolved_input if feedback_loop is not None else None,
            ):
                if item["kind"] == "event":
                    yield sse_event(str(item["event"]), item["data"])
                elif item["kind"] == "heartbeat":
                    yield sse_event("heartbeat", {"task_id": task_id, "ts": datetime.now().isoformat()})
                else:
                    tool_result = item["result"]
            assert tool_result is not None
            seq_cursor = int(tool_result["seq_cursor"])
            if tool_result["should_return"]:
                release_task_slot()
                return
            if feedback_loop is None:
                break
            raise_if_should_abort(force_status_probe=True)
            persist_trace(force=True)
            yield sse_event("state", {"task_id": task_id, "phase": "thinking"})
            source_steps = [step["id"] for step in trace_steps
                            if (step.get("meta") or {}).get("agent_round") == agent_round
                            and step.get("type") == "action"]
            decision = (FeedbackDecision([], "repeated_action") if tool_result.get("stop_reason") == "repeated_action"
                        else feedback_loop.decide(prompt=model_prompt,
                            observations=with_model_observations(tool_observations, trace_steps), provider=provider))
            decision_content = build_tool_plan_summary(decision.plan, registry_provider=tool_registry_provider) if decision.plan else f"Agent tools stopped: {decision.reason}. Generate answer from available observations."
            decision_meta = {"model": provider_model, "step_type": "planning", "label": "agent_decision",
                             "agent_round": feedback_loop.round, "agent_decision": decision.reason,
                             "agent_from_step_ids": source_steps, "tokens": 0, "cost_estimate": 0.0}
            artifacts = decision.artifacts
            if artifacts is not None and artifacts.planning_provider_attempted:
                decision_usage = _build_usage_payload(
                    prompt_text=artifacts.planning_prompt, completion_text=decision_content,
                    provider_usage=artifacts.provider_usage,
                )
                planning_usage_payload = sum_planning_usage(planning_usage_payload, decision_usage)
                decision_meta.update(tokens=decision_usage["completion_tokens"],
                                     cost_estimate=decision_usage["cost_estimate"],
                                     prompt_tokens=decision_usage["prompt_tokens"],
                                     completion_tokens=decision_usage["completion_tokens"],
                                     usage_source=decision_usage["usage_source"])
            raise_if_should_abort(force_status_probe=True)
            seq_cursor += 1
            decision_step = {"id": str(uuid4()), "seq": seq_cursor, "type": "thought",
                             "content": decision_content, "meta": decision_meta}
            trace_steps.append(decision_step)
            yield sse_event("trace", {"task_id": task_id, "step_id": decision_step["id"], "step": decision_step})
            persist_trace(force=True)
            if not decision.plan:
                agent_stop_reason = decision.reason
                break
            agent_round = feedback_loop.round
            tool_plan = decision.plan

        raise_if_should_abort(force_status_probe=True)
        yield sse_event("state", {"task_id": task_id, "phase": "streaming"})
        final_step_id = str(uuid4())
        seq_cursor += 1
        final_step_streaming: dict[str, object] = {
            "id": final_step_id,
            "seq": seq_cursor,
            "type": "observation",
            "content": "",
            "meta": {
                "model": provider_model,
                "step_type": "final_answer",
                **({"agent_stop_reason": agent_stop_reason} if agent_stop_reason is not None else {}),
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
            prompt=model_prompt,
            tool_observations=(with_model_observations(tool_observations, trace_steps)
                               if provider_name != "mock" else tool_observations),
        )
        provider_prompt = with_tool_stop_context(provider_prompt, agent_stop_reason)
        if provider_name != "mock":
            provider_prompt = with_execution_evidence(provider_prompt, trace_steps)
        stream_chunk_count = 0
        provider_usage: ProviderUsage | None = None
        get_last_usage = getattr(provider, "get_last_usage", None)

        streamed_content = ""
        final_step_seq = int(final_step_streaming.get("seq", seq_cursor))
        final_call_started = True
        for chunk in provider.stream_generate(provider_prompt):
            raise_if_should_abort()
            stream_chunk_count += 1
            now = monotonic()
            maybe_touch_execution_heartbeat(now=now)
            if now - last_heartbeat_ts >= STREAM_HEARTBEAT_INTERVAL_SEC:
                yield sse_event(
                    "heartbeat",
                    {
                        "task_id": task_id,
                        "ts": datetime.now().isoformat(),
                    },
                )
                last_heartbeat_ts = now
            streamed_content += chunk
            # Keep all emitted text for terminal failure writes, even between DB batches.
            final_step_seq += 1
            final_step_streaming = {
                **final_step_streaming,
                "content": streamed_content,
                "seq": final_step_seq,
            }
            trace_steps[-1] = final_step_streaming
            yield sse_event(
                "token",
                {
                    "task_id": task_id,
                    "step_id": final_step_id,
                    "delta": chunk,
                },
            )
            should_persist = stream_chunk_count % STREAM_TRACE_PERSIST_EVERY == 0
            if should_persist:
                persist_trace()

        fallback_finish_reason = None
        final_content = streamed_content
        if callable(get_last_usage):
            latest_usage = get_last_usage()
            if isinstance(latest_usage, ProviderUsage):
                provider_usage = latest_usage
        raise_if_should_abort(force_status_probe=True)
        if not final_content:
            raise_if_should_abort(force_status_probe=True)
            fallback = provider.generate(provider_prompt)
            final_content = fallback.content
            fallback_finish_reason = getattr(fallback, "finish_reason", None)
            if isinstance(getattr(fallback, "usage", None), ProviderUsage):
                provider_usage = fallback.usage
            elif callable(get_last_usage):
                latest_usage = get_last_usage()
                if isinstance(latest_usage, ProviderUsage):
                    provider_usage = latest_usage
        # Final content/usage must advance beyond the last emitted snapshot, including empty streams.
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
        capture_final_finish_reason(fallback_finish_reason)
        raise_if_should_abort(force_status_probe=True)
        persist_trace(force=True)

        usage_payload = _merge_usage_payloads(
            final_usage=final_usage_payload,
            planning_usage=planning_usage_payload,
        )

        raise_if_should_abort(force_status_probe=True)
        completed_count = complete_task(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
            usage=usage_payload,
            execution_owner_id=TASK_EXECUTION_OWNER_ID,
            assistant_content=final_content,
        )
        if terminal_write_lost(completed_count):
            raise_if_should_abort(force_status_probe=True)
            raise TaskExecutionAbortError(
                code="task_terminal_race",
                status="failed",
                event="error",
                user_message="Task reached terminal state before completion could be recorded.",
            )

        try_append_task_memory(
            session_id,
            task_id=task_id,
            user_prompt=prompt,
            assistant_excerpt=final_content,
        )

        release_task_slot()
        yield sse_event("trace", {"task_id": task_id, "step_id": final_step_id, "step": trace_steps[-1]})
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
        release_task_slot()
        yield from emit_abort_events(exc)
    except ProviderSelectionError as exc:
        release_task_slot()
        completed_count = complete_task(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
            status="failed",
            usage=terminal_usage(),
            execution_owner_id=TASK_EXECUTION_OWNER_ID,
        )
        if terminal_write_lost(completed_count):
            terminal_exc = terminal_abort_after_lost_race()
            if terminal_exc is not None:
                yield from emit_abort_events(terminal_exc)
                return
        record_failure_event(
            event_type="task_failed",
            code=exc.code,
            message=exc.user_message,
            detail={
                "diagnostic": _build_sse_error_diagnostic(
                    code=exc.code,
                    fatal=True,
                    has_detail=False,
                ),
            },
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
        capture_final_finish_reason()
        rejected_planning_usage = build_terminal_usage(
            planning_usage=None, final_usage=None,
            provider_usage=getattr(exc, "planning_provider_usage", None),
            prompt_price=float(getattr(runtime_config, "usage_prompt_token_price_per_1k", 0)),
            completion_price=float(getattr(runtime_config, "usage_completion_token_price_per_1k", 0)),
        )
        if rejected_planning_usage is not None:
            planning_usage_payload = sum_planning_usage(planning_usage_payload, rejected_planning_usage)
        release_task_slot()
        completed_count = complete_task(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
            status="failed",
            usage=terminal_usage(),
            execution_owner_id=TASK_EXECUTION_OWNER_ID,
        )
        if terminal_write_lost(completed_count):
            terminal_exc = terminal_abort_after_lost_race()
            if terminal_exc is not None:
                yield from emit_abort_events(terminal_exc)
                return
        record_failure_event(
            event_type="task_failed",
            code=exc.code,
            message=exc.user_message,
            detail={
                "status_code": exc.status_code,
                "retryable": exc.retryable,
                "diagnostic": _build_sse_error_diagnostic(
                    code=exc.code,
                    fatal=not exc.retryable,
                    status_code=exc.status_code,
                    has_detail=bool(exc.detail),
                ),
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
        capture_final_finish_reason()
        release_task_slot()
        completed_count = complete_task(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
            status="failed",
            usage=terminal_usage(),
            execution_owner_id=TASK_EXECUTION_OWNER_ID,
        )
        if terminal_write_lost(completed_count):
            terminal_exc = terminal_abort_after_lost_race()
            if terminal_exc is not None:
                yield from emit_abort_events(terminal_exc)
                return
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
    except BaseException as exc:
        release_task_slot()
        if isinstance(exc, CancelledError):
            if task_running_started:
                completed_count = complete_task(
                    task_id=task_id,
                    trace_steps=trace_steps,
                    user_id=user_id,
                    status="failed",
                    usage=terminal_usage(),
                    execution_owner_id=TASK_EXECUTION_OWNER_ID,
                )
                if not terminal_write_lost(completed_count):
                    record_failure_event(
                        event_type="task_failed",
                        code="task_stream_interrupted",
                        message="Task stream was interrupted before completion.",
                    )
        raise
