from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import replace

from app.services.chroma_rag_service import normalize_knowledge_base_id


def _runtime_module():
    from app.services import tool_runtime

    return tool_runtime


def _proxy(name: str):
    return getattr(_runtime_module(), name)


def _call_runtime(attr_name: str, *args, **kwargs):
    return _proxy(attr_name)(*args, **kwargs)


ConfiguredToolRegistryProvider = _proxy("ConfiguredToolRegistryProvider")
MockToolExecutionError = _proxy("MockToolExecutionError")
StaticToolRegistryProvider = _proxy("StaticToolRegistryProvider")
ToolRuntimeContext = _proxy("ToolRuntimeContext")
_REGISTERED_TOOLS = _proxy("_REGISTERED_TOOLS")


def _coerce_tool_execution_string_like_value(*args, **kwargs):
    return _call_runtime("_coerce_tool_execution_string_like_value", *args, **kwargs)


def _extract_http_json_retrieval_list_from_container(*args, **kwargs):
    return _call_runtime("_extract_http_json_retrieval_list_from_container", *args, **kwargs)


def _format_safe_tool_display_label(*args, **kwargs):
    return _call_runtime("_format_safe_tool_display_label", *args, **kwargs)


def _format_safe_tool_execution_summary_field_name(*args, **kwargs):
    return _call_runtime("_format_safe_tool_execution_summary_field_name", *args, **kwargs)


def _get_safe_http_json_request_id_display_value(*args, **kwargs):
    return _call_runtime("_get_safe_http_json_request_id_display_value", *args, **kwargs)


def _get_tool_runtime_trace_semantic_kind(*args, **kwargs):
    return _call_runtime("_get_tool_runtime_trace_semantic_kind", *args, **kwargs)


def _is_non_text_sequence(*args, **kwargs):
    return _call_runtime("_is_non_text_sequence", *args, **kwargs)


def _label_implies_local_knowledge_retrieval(*args, **kwargs):
    return _call_runtime("_label_implies_local_knowledge_retrieval", *args, **kwargs)


def _label_implies_real_calc_summary(*args, **kwargs):
    return _call_runtime("_label_implies_real_calc_summary", *args, **kwargs)


def _label_implies_real_retrieval_summary(*args, **kwargs):
    return _call_runtime("_label_implies_real_retrieval_summary", *args, **kwargs)


def _normalize_http_json_safe_output_shape(*args, **kwargs):
    return _call_runtime("_normalize_http_json_safe_output_shape", *args, **kwargs)


def _normalize_nonnegative_int_count_value(*args, **kwargs):
    return _call_runtime("_normalize_nonnegative_int_count_value", *args, **kwargs)


def _normalize_planned_tool_names(*args, **kwargs):
    return _call_runtime("_normalize_planned_tool_names", *args, **kwargs)


def _normalize_result_output_keys(*args, **kwargs):
    return _call_runtime("_normalize_result_output_keys", *args, **kwargs)


def _normalize_result_preview_keys(*args, **kwargs):
    return _call_runtime("_normalize_result_preview_keys", *args, **kwargs)


def _normalize_tool_execution_kind(*args, **kwargs):
    return _call_runtime("_normalize_tool_execution_kind", *args, **kwargs)


def _normalize_tool_result_projection_output(*args, **kwargs):
    return _call_runtime("_normalize_tool_result_projection_output", *args, **kwargs)


def _normalize_tool_semantic_kind(*args, **kwargs):
    return _call_runtime("_normalize_tool_semantic_kind", *args, **kwargs)


def _redact_http_json_raw_fallback_value(*args, **kwargs):
    return _call_runtime("_redact_http_json_raw_fallback_value", *args, **kwargs)


def _redact_http_json_sensitive_payload_text(*args, **kwargs):
    return _call_runtime("_redact_http_json_sensitive_payload_text", *args, **kwargs)


def _redact_http_json_sensitive_payload_value(*args, **kwargs):
    return _call_runtime("_redact_http_json_sensitive_payload_value", *args, **kwargs)


def _sanitize_tool_runtime_trace_artifact_payload(*args, **kwargs):
    return _call_runtime("_sanitize_tool_runtime_trace_artifact_payload", *args, **kwargs)


def estimate_token_count(*args, **kwargs):
    return _call_runtime("estimate_token_count", *args, **kwargs)


def get_default_tool_registry(*args, **kwargs):
    return _call_runtime("get_default_tool_registry", *args, **kwargs)


def get_default_tool_registry_provider(*args, **kwargs):
    return _call_runtime("get_default_tool_registry_provider", *args, **kwargs)


def get_tool_display_name_from_registration(*args, **kwargs):
    return _call_runtime("get_tool_display_name_from_registration", *args, **kwargs)


def get_tool_effective_result_output_keys(*args, **kwargs):
    return _call_runtime("get_tool_effective_result_output_keys", *args, **kwargs)


def get_tool_effective_result_preview_keys(*args, **kwargs):
    return _call_runtime("get_tool_effective_result_preview_keys", *args, **kwargs)


def get_tool_execution_display_name_from_registration(*args, **kwargs):
    return _call_runtime("get_tool_execution_display_name_from_registration", *args, **kwargs)


def get_tool_observation_display_name_from_registration(*args, **kwargs):
    return _call_runtime("get_tool_observation_display_name_from_registration", *args, **kwargs)


def get_tool_semantic_kind(*args, **kwargs):
    return _call_runtime("get_tool_semantic_kind", *args, **kwargs)


def make_step_id(*args, **kwargs):
    return _call_runtime("make_step_id", *args, **kwargs)


def normalize_tool_output_for_registration(*args, **kwargs):
    return _call_runtime("normalize_tool_output_for_registration", *args, **kwargs)


def normalize_tool_registry_name(*args, **kwargs):
    return _call_runtime("normalize_tool_registry_name", *args, **kwargs)


def normalize_tool_registry_names(*args, **kwargs):
    return _call_runtime("normalize_tool_registry_names", *args, **kwargs)


def run_tool(*args, **kwargs):
    return _call_runtime("run_tool", *args, **kwargs)


def sanitize_tool_execution_diagnostics(*args, **kwargs):
    return _call_runtime("sanitize_tool_execution_diagnostics", *args, **kwargs)


def sanitize_tool_execution_summary(*args, **kwargs):
    return _call_runtime("sanitize_tool_execution_summary", *args, **kwargs)


def sanitize_tool_registry_diagnostics_artifact_payload(*args, **kwargs):
    return _call_runtime("sanitize_tool_registry_diagnostics_artifact_payload", *args, **kwargs)


def __getattr__(name: str):
    return _proxy(name)


def build_tool_registry_provider(
    *,
    provider: ToolRegistryProvider | None = None,
    loader: ToolRegistryLoader | None = None,
    overrides: dict[str, ToolRegistration] | None = None,
    disabled_tool_names: tuple[str, ...] = (),
) -> ToolRegistryProvider:
    if provider is not None and not overrides and not disabled_tool_names:
        return provider
    if provider is None and loader is None and not overrides and not disabled_tool_names:
        return get_default_tool_registry_provider()
    return ConfiguredToolRegistryProvider(
        provider=provider,
        loader=loader,
        overrides=overrides,
        disabled_tool_names=disabled_tool_names,
    )


def build_tool_registry(
    *,
    base_registry: dict[str, ToolRegistration] | None = None,
    overrides: dict[str, ToolRegistration] | None = None,
    disabled_tool_names: tuple[str, ...] | None = None,
) -> dict[str, ToolRegistration]:
    registry = get_default_tool_registry() if base_registry is None else dict(base_registry)
    if overrides:
        registry.update(overrides)
    if disabled_tool_names:
        for name in normalize_tool_registry_names(disabled_tool_names):
            registry.pop(name, None)
    return registry


def get_registered_tool_names(
    *,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> tuple[str, ...]:
    provider_stack = resolve_tool_registry_provider(
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    return tuple(sorted(provider_stack.load_tool_registry()))


def resolve_tool_registry_provider(
    *,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> ToolRegistryProvider:
    if registry is not None:
        return StaticToolRegistryProvider(registry=dict(registry))
    return build_tool_registry_provider(
        provider=registry_provider,
        loader=registry_loader,
    )


def resolve_tool_registration(
    name: str,
    *,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> ToolRegistration | None:
    provider_stack = resolve_tool_registry_provider(
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    lookup_name = normalize_tool_registry_name(name)
    return provider_stack.load_tool_registry().get(lookup_name)


def ensure_tool_registration(
    name: str,
    *,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> ToolRegistration:
    registration = resolve_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if registration is None:
        raise MockToolExecutionError(f"Unknown tool: {name}", fatal=True)
    return registration


def maybe_raise_tool_execution_error(*, name: str, prompt: str, attempt: int) -> None:
    del name
    normalized = prompt.strip().lower()

    if "[tool-fatal]" in normalized or "[mock-tool-fatal]" in normalized:
        raise MockToolExecutionError(
            "Tool fatal error: planner contract validation failed.",
            fatal=True,
        )

    if ("[tool-error]" in normalized or "[mock-tool-error]" in normalized) and attempt == 0:
        raise MockToolExecutionError(
            "Tool transient error: plan source unavailable on first attempt.",
            fatal=False,
        )


def maybe_raise_mock_tool_execution_error(*, name: str, prompt: str, attempt: int) -> None:
    maybe_raise_tool_execution_error(
        name=name,
        prompt=prompt,
        attempt=attempt,
    )


def build_tool_runtime_context(
    *,
    name: str,
    prompt: str,
    user_id: str,
    attempt: int,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> ToolRuntimeContext:
    registration = ensure_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    canonical_name = registration.name
    requires_user_context = tool_requires_user_context(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    effective_user_id = user_id if requires_user_context else ""
    return ToolRuntimeContext(
        name=canonical_name,
        prompt=prompt,
        user_id=effective_user_id,
        attempt=attempt,
        registration=registration,
        retryable_by_default=is_tool_retryable_by_default(
            canonical_name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        default_timeout_ms=get_tool_default_timeout_ms(
            canonical_name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        requires_user_context=requires_user_context,
    )


def _normalize_tool_input_for_registration(
    *,
    name: str,
    tool_input: dict[str, object],
    registration: ToolRegistration,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    if get_tool_semantic_kind(name=name, registration=registration) != "task_planner":
        return tool_input
    if not _is_non_text_sequence(tool_input.get("planned_tool_names")):
        return tool_input
    raw_planned_tool_names = _normalize_planned_tool_names(tool_input.get("planned_tool_names"))
    if not raw_planned_tool_names:
        return tool_input

    existing_labels = tool_input.get("planned_tool_labels")
    planned_tool_names: list[str] = []
    planned_tool_labels: list[str] = []
    planned_tool_kinds: list[str] = []
    planned_tool_execution_kinds: list[str] = []
    for idx, planned_tool_name in enumerate(raw_planned_tool_names):
        planned_registration = resolve_tool_registration(
            planned_tool_name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        semantic_kind = get_tool_semantic_kind(
            name=planned_tool_name,
            registration=planned_registration,
        )
        if semantic_kind == "task_planner":
            continue
        planned_tool_names.append(planned_tool_name)
        label = ""
        if _is_non_text_sequence(existing_labels) and idx < len(existing_labels):
            raw_label = _coerce_tool_execution_string_like_value(existing_labels[idx])
            label = str(raw_label).strip()
        if not label:
            label = get_tool_display_name_from_registration(
                name=planned_tool_name,
                registration=planned_registration,
            )
        planned_tool_labels.append(label)
        planned_tool_kinds.append(semantic_kind or "")
        planned_tool_execution_kinds.append(
            _normalize_tool_execution_kind(planned_registration.execution_kind) or ""
            if planned_registration is not None
            else ""
        )

    normalized_input = dict(tool_input)
    normalized_input["planned_tool_names"] = list(planned_tool_names)
    normalized_input["planned_tool_labels"] = planned_tool_labels
    normalized_input["planned_tool_kinds"] = planned_tool_kinds
    normalized_input["planned_tool_execution_kinds"] = planned_tool_execution_kinds
    return normalized_input


def build_tool_runtime_input(
    *,
    name: str,
    tool_input: dict[str, object],
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if resolved_registration is None:
        return dict(tool_input)
    return _normalize_tool_input_for_registration(
        name=canonical_name,
        tool_input=dict(tool_input),
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )


def build_tool_visible_input(
    *,
    name: str,
    tool_input: dict[str, object],
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    normalized_tool_input = build_tool_runtime_input(
        name=canonical_name,
        tool_input=tool_input,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if (
        resolved_registration is not None
        and _normalize_tool_execution_kind(resolved_registration.execution_kind) == "http_json"
    ):
        safe_tool_input = _redact_http_json_sensitive_payload_value(normalized_tool_input)
        if isinstance(safe_tool_input, dict):
            return safe_tool_input
    return normalized_tool_input


def _with_action_step_tool_input(
    action_step: dict[str, object],
    *,
    tool_input: dict[str, object],
) -> dict[str, object]:
    meta = action_step.get("meta")
    if not isinstance(meta, dict):
        return action_step
    tool_meta = meta.get("tool")
    if not isinstance(tool_meta, dict):
        return action_step
    return {
        **action_step,
        "meta": {
            **meta,
            "tool": {
                **tool_meta,
                "input": tool_input,
            },
        },
    }


def build_tool_result_preview(
    *,
    name: str,
    output: dict[str, object],
    registry: dict[str, ToolRegistration] | None = None,
    registration: ToolRegistration | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object] | None:
    resolved_registration = registration or resolve_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if resolved_registration is None:
        return output
    if not resolved_registration.supports_result_preview:
        return None
    normalized_output = _normalize_tool_result_projection_output(
        output,
        registration=resolved_registration,
    )
    result_preview_keys = get_tool_effective_result_preview_keys(
        name=name,
        registration=resolved_registration,
    )
    has_explicit_preview_keys = bool(
        _normalize_result_preview_keys(resolved_registration.result_preview_keys)
    )
    semantic_kind = get_tool_semantic_kind(
        name=name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if result_preview_keys:
        preview = {
            key: normalized_output[key]
            for key in result_preview_keys
            if key in normalized_output
        }
        if semantic_kind == "task_planner":
            normalized_steps = _normalize_tool_result_plan_steps(preview.get("steps"))
            if normalized_steps:
                preview["steps"] = normalized_steps
        return preview
    if has_explicit_preview_keys:
        return {}
    if semantic_kind == "task_planner":
        task_planner_output = dict(normalized_output)
        normalized_steps = _normalize_tool_result_plan_steps(
            task_planner_output.get("steps")
        )
        if normalized_steps:
            task_planner_output["steps"] = normalized_steps
        return task_planner_output
    return normalized_output


def build_tool_result_output(
    *,
    name: str,
    output: dict[str, object],
    registry: dict[str, ToolRegistration] | None = None,
    registration: ToolRegistration | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    resolved_registration = registration or resolve_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if resolved_registration is None:
        return output
    normalized_source_output = _normalize_tool_result_projection_output(
        output,
        registration=resolved_registration,
    )
    result_output_keys = get_tool_effective_result_output_keys(
        name=name,
        registration=resolved_registration,
    )
    has_explicit_output_keys = bool(
        _normalize_result_output_keys(resolved_registration.result_output_keys)
    )
    has_explicit_preview_keys = bool(
        _normalize_result_preview_keys(resolved_registration.result_preview_keys)
    )
    semantic_kind = get_tool_semantic_kind(
        name=name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if not result_output_keys:
        if has_explicit_output_keys:
            return {}
        if has_explicit_preview_keys and not get_tool_effective_result_preview_keys(
            name=name,
            registration=resolved_registration,
        ):
            return {}
        if semantic_kind == "task_planner":
            normalized_output = dict(normalized_source_output)
            normalized_steps = _normalize_tool_result_plan_steps(
                normalized_output.get("steps")
            )
            if normalized_steps:
                normalized_output["steps"] = normalized_steps
            return normalized_output
        return normalized_source_output
    normalized_output = {
        key: normalized_source_output[key]
        for key in result_output_keys
        if key in normalized_source_output
    }
    if semantic_kind == "task_planner":
        normalized_steps = _normalize_tool_result_plan_steps(normalized_output.get("steps"))
        if normalized_steps:
            normalized_output["steps"] = normalized_steps
    return normalized_output


def _normalize_tool_result_plan_steps(raw_steps: object) -> list[str]:
    if not isinstance(raw_steps, Sequence) or isinstance(
        raw_steps,
        (str, bytes, bytearray, memoryview),
    ):
        return []
    normalized_steps: list[str] = []
    for raw_step in raw_steps:
        raw_step = _coerce_tool_execution_string_like_value(raw_step)
        if not isinstance(raw_step, str):
            continue
        step = raw_step.strip()
        if step:
            normalized_steps.append(step)
    return normalized_steps


def _summarize_generic_tool_result_payload(payload: dict[str, object]) -> str | None:
    parts: list[str] = []
    for key, value in payload.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        safe_key = _format_safe_tool_execution_summary_field_name(normalized_key)
        if safe_key == "[redacted]":
            continue
        if isinstance(value, bool):
            parts.append(f"{safe_key}={'true' if value else 'false'}")
            continue
        if isinstance(value, (int, float)):
            parts.append(f"{safe_key}={value}")
            continue
        value = _coerce_tool_execution_string_like_value(value)
        if isinstance(value, str):
            normalized_value = value.strip()
            if normalized_value:
                safe_value = _redact_http_json_raw_fallback_value(normalized_value)
                parts.append(f"{safe_key}={safe_value}")
            continue
    if not parts:
        return None
    return ", ".join(parts[:3])


def build_tool_result_summary(
    *,
    name: str,
    output: dict[str, object],
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> str | None:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if resolved_registration is None:
        return None
    effective_result_output_keys = get_tool_effective_result_output_keys(
        name=canonical_name,
        registration=resolved_registration,
    )
    if not effective_result_output_keys:
        return None
    outward_output = build_tool_result_output(
        name=canonical_name,
        output=output,
        registry=registry,
        registration=resolved_registration,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    resolved_display_name = (
        _format_safe_tool_display_label(
            display_name,
            fallback_name=canonical_name,
            registration=resolved_registration,
        )
        if display_name is not None
        else get_tool_observation_display_name_from_registration(
            name=canonical_name,
            registration=resolved_registration,
        )
    )
    runtime_semantic_kind = _get_tool_runtime_trace_semantic_kind(
        name=canonical_name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    semantic_family = get_tool_semantic_kind(
        name=canonical_name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )

    plan = _coerce_tool_execution_string_like_value(outward_output.get("plan"))
    if isinstance(plan, str) and plan.strip():
        return f"Planned steps - {plan.strip()}."
    steps = _normalize_tool_result_plan_steps(outward_output.get("steps"))
    if steps:
        return f"Planned steps - {' -> '.join(steps)}."

    expression = _coerce_tool_execution_string_like_value(
        outward_output.get("expression")
    )
    result = outward_output.get("result")
    request_id = _get_safe_http_json_request_id_display_value(
        outward_output.get("request_id")
    )
    if isinstance(expression, str) and expression.strip() and result is not None:
        if isinstance(request_id, str) and request_id.strip():
            return (
                f"Calculated {expression.strip()} = {result} "
                f"(request id {request_id.strip()})."
            )
        return f"Calculated {expression.strip()} = {result}."
    if (
        semantic_family == "local_calculator"
        or (
            result is not None
            and semantic_family is None
            and runtime_semantic_kind is None
            and (
                _label_implies_real_calc_summary(canonical_name)
                or _label_implies_real_calc_summary(resolved_display_name)
            )
        )
    ) and result is not None:
        if isinstance(request_id, str) and request_id.strip():
            return f"Calculated result = {result} (request id {request_id.strip()})."
        return f"Calculated result = {result}."

    hit_count = _normalize_nonnegative_int_count_value(outward_output.get("hit_count"))
    knowledge_base_id = _coerce_tool_execution_string_like_value(
        outward_output.get("knowledge_base_id")
    )
    if hit_count is not None:
        hit_label = "hit" if hit_count == 1 else "hits"
        if (
            runtime_semantic_kind == "knowledge_retrieval"
            and isinstance(knowledge_base_id, str)
            and knowledge_base_id.strip()
        ):
            if isinstance(request_id, str) and request_id.strip():
                return (
                    f"Retrieved {hit_count} {hit_label} from knowledge base "
                    f"{knowledge_base_id.strip()} (request id {request_id.strip()})."
                )
            return (
                f"Retrieved {hit_count} {hit_label} from knowledge base "
                f"{knowledge_base_id.strip()}."
            )
        if (
            runtime_semantic_kind != "knowledge_retrieval"
            and semantic_family == "knowledge_retrieval"
        ):
            if isinstance(request_id, str) and request_id.strip():
                return f"Retrieved {hit_count} {hit_label} (request id {request_id.strip()})."
            return f"Retrieved {hit_count} {hit_label}."
        if isinstance(request_id, str) and request_id.strip():
            return f"Retrieved {hit_count} {hit_label} (request id {request_id.strip()})."
        return f"Retrieved {hit_count} {hit_label}."

    documents_total = _normalize_nonnegative_int_count_value(
        outward_output.get("documents_total")
    )
    if documents_total is not None:
        document_label = "document" if documents_total == 1 else "documents"
        source_suffix = ""
        if isinstance(knowledge_base_id, str) and knowledge_base_id.strip():
            if runtime_semantic_kind == "knowledge_retrieval":
                source_suffix = f" from knowledge base {knowledge_base_id.strip()}"
            elif semantic_family == "knowledge_retrieval":
                source_suffix = f" from {knowledge_base_id.strip()}"
        if isinstance(request_id, str) and request_id.strip():
            return (
                f"Retrieved {documents_total} {document_label}{source_suffix} "
                f"(request id {request_id.strip()})."
            )
        return f"Retrieved {documents_total} {document_label}{source_suffix}."

    chunks = _extract_tool_rag_chunks_from_output(outward_output)
    if chunks and semantic_family == "knowledge_retrieval":
        snippet_label = "snippet" if len(chunks) == 1 else "snippets"
        if isinstance(request_id, str) and request_id.strip():
            return (
                f"Retrieved {len(chunks)} {snippet_label} "
                f"(request id {request_id.strip()})."
            )
        return f"Retrieved {len(chunks)} {snippet_label}."

    generic_payload_summary = _summarize_generic_tool_result_payload(outward_output)
    if generic_payload_summary:
        return f"{resolved_display_name} output - {generic_payload_summary}."
    return None


def build_tool_runtime_semantics_meta(
    *,
    name: str,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if resolved_registration is None:
        return {}
    semantic_kind = _get_tool_runtime_trace_semantic_kind(
        name=canonical_name,
        registration=resolved_registration,
    )
    semantic_family = get_tool_semantic_kind(
        name=canonical_name,
        registration=resolved_registration,
    )
    effective_result_preview_keys = get_tool_effective_result_preview_keys(
        name=canonical_name,
        registration=resolved_registration,
    )
    effective_result_output_keys = get_tool_effective_result_output_keys(
        name=canonical_name,
        registration=resolved_registration,
    )
    meta: dict[str, object] = {
        "kind": resolved_registration.kind,
        "semantic_kind": semantic_kind,
        "supports_result_preview": resolved_registration.supports_result_preview,
        "effective_result_preview_keys": list(effective_result_preview_keys),
    }
    execution_kind = _normalize_tool_execution_kind(resolved_registration.execution_kind)
    if execution_kind is not None:
        meta["execution_kind"] = execution_kind
    execution_summary = sanitize_tool_execution_summary(
        resolved_registration.execution_summary,
    )
    if execution_summary is not None:
        meta["execution_summary"] = execution_summary
    execution_diagnostics = sanitize_tool_execution_diagnostics(
        resolved_registration.execution_diagnostics,
    )
    if execution_diagnostics:
        meta["execution_diagnostics"] = list(execution_diagnostics)
    if semantic_family and semantic_family != semantic_kind:
        meta["semantic_family"] = semantic_family
    if effective_result_output_keys:
        meta["effective_result_output_keys"] = list(effective_result_output_keys)
    return meta


def tool_requires_user_context(
    name: str,
    *,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> bool:
    registration = resolve_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if registration is None:
        return True
    return registration.requires_user_context


def is_tool_retryable_by_default(
    name: str,
    *,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> bool:
    registration = resolve_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if registration is None:
        return True
    return registration.retryable_by_default


def get_tool_default_timeout_ms(
    name: str,
    *,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> int:
    registration = resolve_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
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
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    outward_output = build_tool_result_output(
        name=canonical_name,
        output=output,
        registry=registry,
        registration=resolved_registration,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    payload = {
        "task_id": task_id,
        "step_id": step_id,
        "status": "done",
        "latency_ms": max(
            1,
            (
                resolved_registration.default_timeout_ms
                if resolved_registration is not None
                else get_tool_default_timeout_ms(canonical_name)
            )
            // 250,
        ),
        "output_preview": build_tool_result_preview(
            name=canonical_name,
            output=outward_output,
            registry=registry,
            registration=resolved_registration,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        **build_tool_runtime_semantics_meta(
            name=canonical_name,
            registration=resolved_registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "retry_count": retry_count,
    }
    effective_result_output_keys = get_tool_effective_result_output_keys(
        name=canonical_name,
        registration=resolved_registration,
    )
    if effective_result_output_keys:
        payload["output"] = outward_output
        result_summary = build_tool_result_summary(
            name=canonical_name,
            output=output,
            registry=registry,
            registration=resolved_registration,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        if result_summary:
            payload["result_summary"] = result_summary
    return payload


def build_tool_success_meta(
    *,
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object],
    retry_count: int,
    last_error: str | None,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    safe_last_error = (
        _normalize_tool_error_message_for_registration(
            last_error,
            registration=resolved_registration,
        )
        if isinstance(last_error, str)
        else last_error
    )
    normalized_tool_input = build_tool_visible_input(
        name=canonical_name,
        tool_input=tool_input,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    outward_output = build_tool_result_output(
        name=canonical_name,
        output=output,
        registry=registry,
        registration=resolved_registration,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    resolved_display_name = (
        _format_safe_tool_display_label(
            display_name,
            fallback_name=canonical_name,
            registration=resolved_registration,
        )
        if display_name is not None
        else get_tool_execution_display_name_from_registration(
            name=canonical_name,
            registration=resolved_registration,
        )
    )
    result_summary = build_tool_result_summary(
        name=canonical_name,
        output=output,
        display_name=resolved_display_name,
        registry=registry,
        registration=resolved_registration,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    return {
        "tool": {
            "name": canonical_name,
            "label": resolved_display_name,
            "input": normalized_tool_input,
            "output": outward_output,
            "output_preview": build_tool_result_preview(
                name=canonical_name,
                output=outward_output,
                registry=registry,
                registration=resolved_registration,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
            "status": "done",
            "retry_count": retry_count,
            "error": safe_last_error,
            **({"result_summary": result_summary} if result_summary else {}),
            **build_tool_runtime_semantics_meta(
                name=canonical_name,
                registration=resolved_registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        },
    }


def _normalize_tool_error_message_for_registration(
    error_message: str,
    *,
    registration: ToolRegistration | None,
) -> str:
    if (
        registration is not None
        and _normalize_tool_execution_kind(registration.execution_kind) == "http_json"
    ):
        safe_message = _redact_http_json_raw_fallback_value(error_message)
        return safe_message if isinstance(safe_message, str) else "[redacted]"
    return error_message


def build_tool_error_meta(
    *,
    name: str,
    tool_input: dict[str, object],
    retry_count: int,
    error_message: str,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    safe_error_message = _normalize_tool_error_message_for_registration(
        error_message,
        registration=resolved_registration,
    )
    normalized_tool_input = build_tool_visible_input(
        name=canonical_name,
        tool_input=tool_input,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    resolved_display_name = (
        _format_safe_tool_display_label(
            display_name,
            fallback_name=canonical_name,
            registration=resolved_registration,
        )
        if display_name is not None
        else get_tool_execution_display_name_from_registration(
            name=canonical_name,
            registration=resolved_registration,
        )
    )
    return {
        "tool": {
            "name": canonical_name,
            "label": resolved_display_name,
            "input": normalized_tool_input,
            "status": "error",
            "retry_count": retry_count,
            "error": safe_error_message,
            **build_tool_runtime_semantics_meta(
                name=canonical_name,
                registration=resolved_registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        },
    }


def build_tool_start_payload(
    *,
    task_id: str,
    step_id: str,
    name: str,
    tool_input: dict[str, object],
    retry_count: int,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    normalized_tool_input = build_tool_visible_input(
        name=canonical_name,
        tool_input=tool_input,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    resolved_display_name = (
        _format_safe_tool_display_label(
            display_name,
            fallback_name=canonical_name,
            registration=resolved_registration,
        )
        if display_name is not None
        else get_tool_execution_display_name_from_registration(
            name=canonical_name,
            registration=resolved_registration,
        )
    )
    return {
        "task_id": task_id,
        "step_id": step_id,
        "name": canonical_name,
        "display_name": resolved_display_name,
        "input": normalized_tool_input,
        **build_tool_runtime_semantics_meta(
            name=canonical_name,
            registration=resolved_registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "retry_count": retry_count,
    }


def build_tool_error_payload(
    *,
    name: str | None = None,
    task_id: str,
    step_id: str,
    error_message: str,
    retry_count: int,
    latency_ms: int = 12,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    semantic_meta: dict[str, object] = {}
    normalized_name = (
        normalize_tool_registry_name(name) if isinstance(name, str) and name.strip() else None
    )
    if normalized_name is not None:
        resolved_registration = registration or resolve_tool_registration(
            normalized_name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        error_message = _normalize_tool_error_message_for_registration(
            error_message,
            registration=resolved_registration,
        )
        semantic_meta = build_tool_runtime_semantics_meta(
            name=normalized_name,
            registration=resolved_registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
    else:
        error_message = _normalize_tool_error_message_for_registration(
            error_message,
            registration=registration,
        )
    return {
        "task_id": task_id,
        "step_id": step_id,
        "status": "error",
        "latency_ms": latency_ms,
        "output_preview": {"error": error_message},
        **semantic_meta,
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
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    normalized_tool_input = build_tool_visible_input(
        name=canonical_name,
        tool_input=tool_input,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    resolved_display_name = (
        _format_safe_tool_display_label(
            display_name,
            fallback_name=canonical_name,
            registration=resolved_registration,
        )
        if display_name is not None
        else get_tool_execution_display_name_from_registration(
            name=canonical_name,
            registration=resolved_registration,
        )
    )
    return {
        "model": model,
        "step_type": "tool_call",
        "label": label,
        "retryCount": 0,
        "tokens": token_count,
        "cost_estimate": None,
        "tool": {
            "name": canonical_name,
            "label": resolved_display_name,
            "input": normalized_tool_input,
            "status": "running",
            "retry_count": 0,
            **build_tool_runtime_semantics_meta(
                name=canonical_name,
                registration=resolved_registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        },
    }


def build_action_step_initial_step(
    *,
    step_id: str,
    seq: int,
    name: str,
    meta: dict[str, object],
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    tool_meta = meta.get("tool") if isinstance(meta.get("tool"), dict) else None
    display_name = (
        str(tool_meta.get("label")).strip()
        if isinstance(tool_meta, dict) and isinstance(tool_meta.get("label"), str)
        else get_tool_execution_display_name_from_registration(
            name=name,
            registration=registration
            or resolve_tool_registration(
                name,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        )
    )
    return {
        "id": step_id,
        "seq": seq,
        "type": "action",
        "content": f"Tool running: {display_name}",
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
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    tool_meta = action_step.get("meta") if isinstance(action_step, dict) else None
    tool_obj = (
        tool_meta.get("tool")
        if isinstance(tool_meta, dict) and isinstance(tool_meta.get("tool"), dict)
        else None
    )
    resolved_registration = registration or resolve_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    raw_display_name = display_name or (
        str(tool_obj.get("label")).strip()
        if isinstance(tool_obj, dict) and isinstance(tool_obj.get("label"), str)
        else None
    )
    resolved_display_name = (
        _format_safe_tool_display_label(
            raw_display_name,
            fallback_name=name,
            registration=resolved_registration,
        )
        if raw_display_name is not None
        else get_tool_execution_display_name_from_registration(
            name=name,
            registration=resolved_registration,
        )
    )
    return {
        **action_step,
        "content": f"Tool done: {resolved_display_name}",
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
                display_name=resolved_display_name,
                registration=registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
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
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    tool_meta = action_step.get("meta") if isinstance(action_step, dict) else None
    tool_obj = (
        tool_meta.get("tool")
        if isinstance(tool_meta, dict) and isinstance(tool_meta.get("tool"), dict)
        else None
    )
    resolved_registration = registration or resolve_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    raw_display_name = display_name or (
        str(tool_obj.get("label")).strip()
        if isinstance(tool_obj, dict) and isinstance(tool_obj.get("label"), str)
        else None
    )
    resolved_display_name = (
        _format_safe_tool_display_label(
            raw_display_name,
            fallback_name=name,
            registration=resolved_registration,
        )
        if raw_display_name is not None
        else get_tool_execution_display_name_from_registration(
            name=name,
            registration=resolved_registration,
        )
    )
    sanitized_action_step = sanitize_tool_registry_diagnostics_artifact_payload(
        action_step
    )
    assert isinstance(sanitized_action_step, dict)
    sanitized_meta = sanitize_tool_registry_diagnostics_artifact_payload(
        dict(sanitized_action_step.get("meta", {}))
    )
    assert isinstance(sanitized_meta, dict)
    return {
        **sanitized_action_step,
        "content": f"Tool error: {resolved_display_name}",
        "meta": {
            **sanitized_meta,
            "step_type": "tool_call",
            "retryCount": retry_count,
            "tokens": token_count,
            **build_tool_error_meta(
                name=name,
                tool_input=tool_input,
                retry_count=retry_count,
                error_message=error_message,
                display_name=resolved_display_name,
                registration=registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
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
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, dict[str, object]]:
    return {
        "tool_start": build_tool_start_payload(
            task_id=task_id,
            step_id=step_id,
            name=name,
            tool_input=tool_input,
            retry_count=attempt,
            display_name=display_name,
            registration=registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
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
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    runtime_ctx = build_tool_runtime_context(
        name=name,
        prompt=prompt,
        user_id=user_id,
        attempt=attempt,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    return {
        "normalized_tool_input": build_tool_runtime_input(
            name=runtime_ctx.name,
            tool_input=tool_input,
            registration=runtime_ctx.registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "start_events": build_tool_attempt_start_events(
            task_id=task_id,
            step_id=step_id,
            name=runtime_ctx.name,
            tool_input=tool_input,
            attempt=attempt,
            display_name=get_tool_execution_display_name_from_registration(
                name=runtime_ctx.registration.name,
                registration=runtime_ctx.registration,
            ),
            registration=runtime_ctx.registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
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
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    return build_tool_plan_item_execution(
        task_id=task_id,
        iteration_ctx=iteration_ctx,
        action_step=action_step,
        runtime_ctx=attempt_bundle["runtime_ctx"],
        name=attempt_bundle["runtime_ctx"].name,
        tool_input=tool_input,
        output=output,
        exc=exc,
        token_count=token_count,
        last_error=last_error,
        model=model,
        rag_step_id=rag_step_id,
        rag_token_count=rag_token_count,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )


def build_tool_attempt_loop_result(
    *,
    attempt_execution: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_attempt_loop_result_payload(
        {
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
    )


def _sanitize_tool_plan_attempt_loop_result_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = dict(payload)
    for key in (
        "tool_end_event",
        "error_event",
        "next_action_step",
        "last_error",
        "plan_item_result",
        "postprocess",
        "success_effects",
        "terminal_effects",
    ):
        if key in sanitized:
            sanitized[key] = sanitize_tool_registry_diagnostics_artifact_payload(
                sanitized[key]
            )
    next_action_step = sanitized.get("next_action_step")
    if isinstance(next_action_step, dict):
        sanitized["next_action_step"] = _sanitize_tool_trace_event_step(
            next_action_step
        )
    if "postprocess" in sanitized:
        sanitized["postprocess"] = _sanitize_tool_plan_loop_postprocess_payload(
            sanitized["postprocess"]
        )
    if "success_effects" in sanitized:
        sanitized["success_effects"] = _sanitize_tool_plan_loop_effects_payload(
            sanitized["success_effects"]
        )
    if "terminal_effects" in sanitized:
        sanitized["terminal_effects"] = _sanitize_tool_plan_loop_effects_payload(
            sanitized["terminal_effects"]
        )
    return sanitized


def _sanitize_tool_plan_retry_loop_result_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = dict(payload)
    for key in ("trace_event", "success_effects", "terminal_effects"):
        if key in sanitized:
            sanitized[key] = sanitize_tool_registry_diagnostics_artifact_payload(
                sanitized[key]
            )
    if "trace_event" in sanitized:
        sanitized["trace_event"] = _sanitize_tool_trace_event_payload(
            sanitized["trace_event"]
        )
    if "success_effects" in sanitized:
        sanitized["success_effects"] = _sanitize_tool_plan_loop_effects_payload(
            sanitized["success_effects"]
        )
    if "terminal_effects" in sanitized:
        sanitized["terminal_effects"] = _sanitize_tool_plan_loop_effects_payload(
            sanitized["terminal_effects"]
        )
    if "loop_result" in sanitized:
        loop_result = sanitized["loop_result"]
        if isinstance(loop_result, dict):
            sanitized["loop_result"] = _sanitize_tool_plan_attempt_loop_result_payload(
                loop_result
            )
    if "retry_loop_result" in sanitized:
        retry_loop_result = sanitized["retry_loop_result"]
        if isinstance(retry_loop_result, dict):
            sanitized["retry_loop_result"] = _sanitize_tool_plan_retry_loop_result_payload(
                retry_loop_result
            )
    if "loop_terminal_result" in sanitized:
        loop_terminal_result = sanitized["loop_terminal_result"]
        if isinstance(loop_terminal_result, dict):
            sanitized["loop_terminal_result"] = _sanitize_tool_plan_loop_terminal_result_payload(
                loop_terminal_result
            )
    return sanitized


def _sanitize_tool_plan_loop_terminal_result_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = dict(payload)
    if "terminal_effects" in sanitized:
        sanitized["terminal_effects"] = sanitize_tool_registry_diagnostics_artifact_payload(
            sanitized["terminal_effects"]
        )
        sanitized["terminal_effects"] = _sanitize_tool_plan_loop_effects_payload(
            sanitized["terminal_effects"]
        )
    return sanitized


def _sanitize_tool_plan_loop_postprocess_payload(
    postprocess: object,
) -> object:
    if not isinstance(postprocess, dict):
        return postprocess
    sanitized = dict(postprocess)
    if "trace" in sanitized:
        sanitized["trace"] = _sanitize_tool_trace_event_payload(sanitized["trace"])
    if "rag_followup" in sanitized:
        sanitized["rag_followup"] = _sanitize_tool_plan_rag_followup_payload(
            sanitized["rag_followup"]
        )
    return sanitized


def _sanitize_tool_plan_loop_effects_payload(
    effects: object,
) -> object:
    if not isinstance(effects, dict):
        return effects
    sanitized = dict(effects)
    trace_step = sanitized.get("trace_step")
    if isinstance(trace_step, dict):
        sanitized["trace_step"] = _sanitize_tool_trace_event_step(trace_step)
    if "trace" in sanitized:
        sanitized["trace"] = _sanitize_tool_trace_event_payload(sanitized["trace"])
    if "rag_followup" in sanitized:
        sanitized["rag_followup"] = _sanitize_tool_plan_rag_followup_payload(
            sanitized["rag_followup"]
        )
    return sanitized


def _sanitize_tool_plan_rag_followup_payload(
    rag_followup: object,
) -> object:
    sanitized = sanitize_tool_registry_diagnostics_artifact_payload(rag_followup)
    if not isinstance(sanitized, dict):
        return sanitized
    followup = dict(sanitized)
    step = followup.get("step")
    if isinstance(step, dict):
        followup["step"] = _sanitize_tool_trace_event_step(step)
    if "trace" in followup:
        followup["trace"] = _sanitize_tool_trace_event_payload(followup["trace"])
    return followup


def build_tool_attempt_loop_terminal_result(
    *,
    loop_result: dict[str, object],
) -> dict[str, object]:
    sanitized_loop_result = _sanitize_tool_plan_attempt_loop_result_payload(loop_result)
    terminal_effects = sanitized_loop_result["terminal_effects"]
    return _sanitize_tool_plan_loop_terminal_result_payload(
        {
            "should_return": terminal_effects is not None,
            "terminal_effects": terminal_effects,
        }
    )


def build_tool_plan_item_retry_loop_result(
    *,
    loop_result: dict[str, object],
) -> dict[str, object]:
    sanitized_loop_result = _sanitize_tool_plan_attempt_loop_result_payload(loop_result)
    success_effects = sanitized_loop_result["success_effects"]
    terminal_effects = sanitized_loop_result["terminal_effects"]
    trace_event = (
        success_effects["trace"]
        if success_effects is not None
        else terminal_effects["trace"]
        if terminal_effects is not None
        else None
    )
    return _sanitize_tool_plan_retry_loop_result_payload(
        {
            "outcome": "success" if success_effects is not None else "terminal_failure",
            "trace_event": trace_event,
            "success_effects": success_effects,
            "terminal_effects": terminal_effects,
        }
    )


def build_tool_plan_item_retry_loop_execution_result(
    *,
    loop_result: dict[str, object],
) -> dict[str, object]:
    sanitized_loop_result = _sanitize_tool_plan_attempt_loop_result_payload(loop_result)
    retry_loop_result = build_tool_plan_item_retry_loop_result(
        loop_result=sanitized_loop_result,
    )
    loop_terminal_result = build_tool_attempt_loop_terminal_result(
        loop_result=sanitized_loop_result,
    )
    return _sanitize_tool_plan_retry_loop_result_payload(
        {
            "outcome": retry_loop_result["outcome"],
            "trace_event": retry_loop_result["trace_event"],
            "success_effects": retry_loop_result["success_effects"],
            "terminal_effects": retry_loop_result["terminal_effects"],
            "should_return": loop_terminal_result["should_return"],
            "loop_result": sanitized_loop_result,
            "retry_loop_result": retry_loop_result,
            "loop_terminal_result": loop_terminal_result,
        }
    )


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
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> Iterator[dict[str, object]]:
    step_id = str(iteration_ctx["step_id"])
    action_step = dict(initial_action_step)
    attempt = 0
    last_error: str | None = None
    if run_tool_fn is None:
        def default_runner(
            *,
            name: str,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
            attempt: int,
        ) -> dict[str, object]:
            return run_tool(
                name=name,
                tool_input=tool_input,
                prompt=prompt,
                user_id=user_id,
                attempt=attempt,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            )

        runner = default_runner
    else:
        runner = run_tool_fn

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
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        normalized_tool_input = attempt_bundle["normalized_tool_input"]
        action_step = _with_action_step_tool_input(
            action_step,
            tool_input=normalized_tool_input,
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
                tool_input=normalized_tool_input,
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
                tool_input=normalized_tool_input,
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
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
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
                tool_input=normalized_tool_input,
                output=None,
                exc=exc,
                token_count=estimate_token_count(str(exc)),
                last_error=None,
                model=model,
                rag_step_id=make_step_id(),
                rag_token_count=0,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
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


def execute_tool_plan_item_service_execution(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
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
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> Iterator[dict[str, object]]:
    for item in execute_tool_plan_item_retry_loop(
        task_id=task_id,
        iteration_ctx=iteration_ctx,
        initial_action_step=initial_action_step,
        tool_name=tool_name,
        tool_input=tool_input,
        prompt=prompt,
        user_id=user_id,
        model=model,
        estimate_token_count=estimate_token_count,
        make_step_id=make_step_id,
        raise_if_should_abort=raise_if_should_abort,
        run_tool_fn=run_tool_fn,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    ):
        if item["kind"] == "event":
            yield item
            continue
        loop_execution_result = item["result"]
        service_execution = build_tool_plan_item_service_execution(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
            loop_execution_result=loop_execution_result,
        )
        service_execution["loop_execution_result"] = (
            _sanitize_tool_runtime_trace_artifact_payload(
                loop_execution_result
            )
        )
        yield {
            "kind": "result",
            "result": service_execution,
        }
        return


def execute_tool_plan_item_service_actions(
    *,
    service_actions: list[dict[str, object]],
    trace_steps: list[dict[str, object]],
    tool_observations: list[str],
    seq_cursor: int,
    persist_trace_fn: Callable[..., None],
    complete_task_fn: Callable[..., None],
    record_failure_event_fn: Callable[..., None],
) -> Iterator[dict[str, object]]:
    current_seq_cursor = int(seq_cursor)
    for raw_service_action in service_actions:
        service_action = _sanitize_tool_runtime_trace_artifact_payload(
            raw_service_action
        )
        if not isinstance(service_action, dict):
            continue
        kind = str(service_action["kind"])
        if kind == "trace_write":
            trace_steps.append(service_action["trace_step"])
            yield {
                "kind": "event",
                "event": "trace",
                "data": service_action["trace_event"],
            }
            persist_trace_fn(force=bool(service_action["persist_force"]))
            continue
        if kind == "continue":
            tool_observations.extend(service_action["tool_observations"])
            current_seq_cursor += int(service_action["seq_increment"])
            continue
        if kind == "complete_task":
            complete_task_fn(**service_action["kwargs"])
            continue
        if kind == "record_failure_event":
            record_failure_event_fn(**service_action["kwargs"])
            continue
        if kind == "emit_state":
            yield {
                "kind": "event",
                "event": str(service_action["event"]),
                "data": service_action["data"],
            }
            continue
        if kind == "return":
            yield {
                "kind": "result",
                "result": {
                    "seq_cursor": current_seq_cursor,
                    "should_return": True,
                },
            }
            return
        raise AssertionError(f"unsupported tool service action: {kind}")

    yield {
        "kind": "result",
        "result": {
            "seq_cursor": current_seq_cursor,
            "should_return": False,
        },
    }


def build_tool_attempt_success_events(
    *,
    task_id: str,
    step_id: str,
    name: str,
    output: dict[str, object],
    retry_count: int,
    registration: ToolRegistration | None = None,
) -> dict[str, dict[str, object]]:
    return {
        "tool_end": build_tool_end_payload(
            name=name,
            task_id=task_id,
            step_id=step_id,
            output=output,
            retry_count=retry_count,
            registration=registration,
        )
    }


def build_tool_attempt_error_events(
    *,
    name: str,
    task_id: str,
    step_id: str,
    error_message: str,
    retry_count: int,
    latency_ms: int = 12,
    registration: ToolRegistration | None = None,
) -> dict[str, dict[str, object]]:
    return {
        "tool_end": build_tool_error_payload(
            name=name,
            task_id=task_id,
            step_id=step_id,
            error_message=error_message,
            retry_count=retry_count,
            latency_ms=latency_ms,
            registration=registration,
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
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
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
            display_name=display_name,
            registration=registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "events": build_tool_attempt_success_events(
            task_id=task_id,
            step_id=step_id,
            name=name,
            output=output,
            retry_count=retry_count,
            registration=registration,
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
    display_name: str | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    error_message = str(exc)
    safe_error_message = _normalize_tool_error_message_for_registration(
        error_message,
        registration=runtime_ctx.registration,
    )
    retry_count = runtime_ctx.attempt + 1
    retryable = compute_tool_retry_decision(ctx=runtime_ctx, exc=exc)
    return {
        "action_step": build_tool_step_error_update(
            action_step=action_step,
            name=name,
            tool_input=tool_input,
            retry_count=retry_count,
            token_count=token_count,
            error_message=safe_error_message,
            display_name=display_name,
            registration=runtime_ctx.registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "events": {
            **build_tool_attempt_error_events(
                name=name,
                task_id=task_id,
                step_id=step_id,
                error_message=safe_error_message,
                retry_count=retry_count,
                latency_ms=max(1, runtime_ctx.default_timeout_ms // 250),
                registration=runtime_ctx.registration,
            ),
            "error": {
                "task_id": task_id,
                "message": safe_error_message,
                "code": "tool_execution_error",
                "fatal": not retryable,
                "retryable": retryable,
                "retryCount": retry_count,
                "step_id": step_id,
            },
        },
        "retryable": retryable,
        "error_message": safe_error_message,
        "retry_count": retry_count,
    }


def _parse_tool_json_mapping_string(value: str) -> dict[str, object] | None:
    normalized = value.strip()
    if not normalized:
        return None
    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, str):
        nested = parsed.strip()
        if not nested.startswith("{"):
            return None
        try:
            parsed = json.loads(nested)
        except json.JSONDecodeError:
            return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _coerce_tool_output_preview_mapping(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    return _parse_tool_json_mapping_string(value)


def _coerce_tool_output_mapping(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    return _parse_tool_json_mapping_string(value)


def build_tool_step_output(action_step: dict[str, object]) -> dict[str, object] | None:
    tool_obj = get_action_step_tool_meta(action_step)
    output = tool_obj.get("output") if isinstance(tool_obj, dict) else None
    if _step_tool_meta_uses_http_json_execution(tool_obj):
        safe_output = _resolve_step_tool_safe_output(tool_obj)
        if isinstance(safe_output, dict):
            return safe_output
        if isinstance(output, dict):
            return _normalize_http_json_safe_output_shape(output)
    if isinstance(output, dict):
        return output
    safe_output = _resolve_step_tool_safe_output(tool_obj)
    if isinstance(safe_output, dict):
        return safe_output
    preview_output = tool_obj.get("output_preview") if isinstance(tool_obj, dict) else None
    preview_mapping = _coerce_tool_output_preview_mapping(preview_output)
    if (
        isinstance(preview_mapping, dict)
        and _step_tool_meta_uses_http_json_execution(tool_obj)
    ):
        return _normalize_http_json_safe_output_shape(preview_mapping)
    return preview_mapping


def get_action_step_tool_meta(action_step: dict[str, object]) -> dict[str, object] | None:
    tool_meta = action_step.get("meta") if isinstance(action_step, dict) else None
    tool_obj = (
        tool_meta.get("tool")
        if isinstance(tool_meta, dict) and isinstance(tool_meta.get("tool"), dict)
        else None
    )
    return tool_obj if isinstance(tool_obj, dict) else None


def _resolve_step_tool_safe_output(
    step_tool_meta: dict[str, object] | None,
) -> object | None:
    if not isinstance(step_tool_meta, dict):
        return None
    output_keys = step_tool_meta.get("effective_result_output_keys")
    if not isinstance(output_keys, (list, tuple)):
        return None
    normalized_keys = [
        key.strip()
        for key in output_keys
        if isinstance(key, str) and key.strip()
    ]
    if not normalized_keys:
        return None
    output = step_tool_meta.get("output")
    output_mapping = _coerce_tool_output_mapping(output)
    if not isinstance(output_mapping, dict):
        return output
    if _step_tool_meta_uses_http_json_execution(step_tool_meta):
        output_mapping = _normalize_http_json_safe_output_shape(output_mapping)
    return {
        key: output_mapping[key]
        for key in normalized_keys
        if key in output_mapping
    }


def _step_tool_meta_uses_http_json_execution(
    step_tool_meta: dict[str, object] | None,
) -> bool:
    if not isinstance(step_tool_meta, dict):
        return False
    return _normalize_tool_execution_kind(step_tool_meta.get("execution_kind")) == "http_json"


def _build_tool_result_summary_from_step_meta_semantics(
    *,
    output: dict[str, object],
    step_tool_meta: dict[str, object] | None,
) -> str | None:
    if not isinstance(output, dict):
        return None
    if _step_tool_meta_uses_http_json_execution(step_tool_meta):
        output = _normalize_http_json_safe_output_shape(output)
    meta_label = (
        str(step_tool_meta.get("label")).strip()
        if isinstance(step_tool_meta, dict)
        and isinstance(step_tool_meta.get("label"), str)
        else ""
    )
    meta_name = (
        str(step_tool_meta.get("name")).strip()
        if isinstance(step_tool_meta, dict)
        and isinstance(step_tool_meta.get("name"), str)
        else ""
    )
    structural_tool_kind = (
        str(step_tool_meta.get("kind")).strip()
        if isinstance(step_tool_meta, dict)
        and isinstance(step_tool_meta.get("kind"), str)
        else ""
    )
    explicit_semantic_kind = (
        str(step_tool_meta.get("semantic_kind")).strip()
        if isinstance(step_tool_meta, dict)
        and isinstance(step_tool_meta.get("semantic_kind"), str)
        else ""
    )
    explicit_semantic_family = (
        str(step_tool_meta.get("semantic_family")).strip()
        if isinstance(step_tool_meta, dict)
        and isinstance(step_tool_meta.get("semantic_family"), str)
        else ""
    )
    label_implies_local_retrieval = (
        _label_implies_local_knowledge_retrieval(meta_label)
        or _label_implies_local_knowledge_retrieval(meta_name)
    )
    label_implies_real_retrieval = (
        _label_implies_real_retrieval_summary(meta_label)
        or _label_implies_real_retrieval_summary(meta_name)
    )
    label_implies_real_calc = (
        _label_implies_real_calc_summary(meta_label)
        or _label_implies_real_calc_summary(meta_name)
    )
    runtime_semantic_kind = _normalize_tool_semantic_kind(
        explicit_semantic_kind or None
    )
    explicit_runtime_semantic_family = _normalize_tool_semantic_kind(
        explicit_semantic_family or None
    )
    structural_semantic_family = _normalize_tool_semantic_kind(
        structural_tool_kind or None
    )
    semantic_family = explicit_runtime_semantic_family
    if semantic_family is None and structural_semantic_family in {
        "knowledge_retrieval",
        "local_calculator",
        "task_planner",
    } and normalize_tool_registry_name(meta_name) not in _REGISTERED_TOOLS:
        semantic_family = structural_semantic_family
    has_runtime_semantic_hint = semantic_family is not None
    if (
        not has_runtime_semantic_hint
        and not label_implies_local_retrieval
        and not label_implies_real_retrieval
        and not label_implies_real_calc
    ):
        return None
    allow_local_knowledge_base_summary = (
        runtime_semantic_kind == "knowledge_retrieval"
        or (
            runtime_semantic_kind is None
            and (
                explicit_runtime_semantic_family == "knowledge_retrieval"
                or label_implies_local_retrieval
            )
        )
    )

    plan = output.get("plan")
    if isinstance(plan, str) and plan.strip():
        return f"Planned steps - {plan.strip()}."
    steps = _normalize_tool_result_plan_steps(output.get("steps"))
    if steps:
        return f"Planned steps - {' -> '.join(steps)}."

    expression = output.get("expression")
    result = output.get("result")
    request_id = _get_safe_http_json_request_id_display_value(
        output.get("request_id")
    )
    if isinstance(expression, str) and expression.strip() and result is not None:
        if isinstance(request_id, str) and request_id.strip():
            return (
                f"Calculated {expression.strip()} = {result} "
                f"(request id {request_id.strip()})."
            )
        return f"Calculated {expression.strip()} = {result}."
    if (
        semantic_family == "local_calculator"
        or runtime_semantic_kind == "local_calculator"
        or (
            result is not None
            and semantic_family is None
            and runtime_semantic_kind is None
            and label_implies_real_calc
        )
    ) and result is not None:
        if isinstance(request_id, str) and request_id.strip():
            return f"Calculated result = {result} (request id {request_id.strip()})."
        return f"Calculated result = {result}."

    hit_count = _normalize_nonnegative_int_count_value(output.get("hit_count"))
    knowledge_base_id = output.get("knowledge_base_id")
    if hit_count is not None:
        hit_label = "hit" if hit_count == 1 else "hits"
        if (
            allow_local_knowledge_base_summary
            and isinstance(knowledge_base_id, str)
            and knowledge_base_id.strip()
        ):
            if isinstance(request_id, str) and request_id.strip():
                return (
                    f"Retrieved {hit_count} {hit_label} from knowledge base "
                    f"{knowledge_base_id.strip()} (request id {request_id.strip()})."
                )
            return (
                f"Retrieved {hit_count} {hit_label} from knowledge base "
                f"{knowledge_base_id.strip()}."
            )
        if semantic_family == "knowledge_retrieval":
            if isinstance(request_id, str) and request_id.strip():
                return f"Retrieved {hit_count} {hit_label} (request id {request_id.strip()})."
            return f"Retrieved {hit_count} {hit_label}."
        if isinstance(request_id, str) and request_id.strip():
            return f"Retrieved {hit_count} {hit_label} (request id {request_id.strip()})."
        return f"Retrieved {hit_count} {hit_label}."

    documents_total = _normalize_nonnegative_int_count_value(
        output.get("documents_total")
    )
    if documents_total is not None:
        document_label = "document" if documents_total == 1 else "documents"
        if isinstance(request_id, str) and request_id.strip():
            return (
                f"Retrieved {documents_total} {document_label} "
                f"(request id {request_id.strip()})."
            )
        return f"Retrieved {documents_total} {document_label}."
    return None


def build_tool_observation_entry(
    *,
    name: str,
    output: dict[str, object] | None,
    display_name: str | None = None,
    step_tool_meta: dict[str, object] | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> str:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    meta_display_name = (
        str(step_tool_meta.get("label")).strip()
        if isinstance(step_tool_meta, dict) and isinstance(step_tool_meta.get("label"), str)
        else ""
    )
    uses_http_json_step_meta = _step_tool_meta_uses_http_json_execution(step_tool_meta)
    raw_display_name = display_name or meta_display_name
    resolved_display_name = (
        _format_safe_tool_display_label(
            raw_display_name,
            fallback_name=canonical_name,
            registration=resolved_registration,
            uses_http_json=uses_http_json_step_meta,
        )
        if raw_display_name
        else get_tool_observation_display_name_from_registration(
            name=canonical_name,
            registration=resolved_registration,
        )
    )
    meta_result_summary = (
        str(step_tool_meta.get("result_summary")).strip()
        if isinstance(step_tool_meta, dict)
        and isinstance(step_tool_meta.get("result_summary"), str)
        else ""
    )
    if meta_result_summary:
        if _step_tool_meta_uses_http_json_execution(step_tool_meta) or (
            resolved_registration is not None
            and _normalize_tool_execution_kind(resolved_registration.execution_kind)
            == "http_json"
        ):
            safe_summary = _redact_http_json_raw_fallback_value(meta_result_summary)
            meta_result_summary = (
                safe_summary if isinstance(safe_summary, str) else "[redacted]"
            )
        return f"{resolved_display_name}: {meta_result_summary}"
    meta_safe_output = _resolve_step_tool_safe_output(step_tool_meta)
    if isinstance(meta_safe_output, dict) and not isinstance(output, dict):
        result_summary = build_tool_result_summary(
            name=canonical_name,
            output=meta_safe_output,
            display_name=resolved_display_name,
            registration=resolved_registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        if result_summary is None:
            result_summary = _build_tool_result_summary_from_step_meta_semantics(
                output=meta_safe_output,
                step_tool_meta=step_tool_meta,
            )
        if result_summary:
            return f"{resolved_display_name}: {result_summary}"
    if meta_safe_output is not None and not isinstance(output, dict):
        if _step_tool_meta_uses_http_json_execution(step_tool_meta):
            meta_safe_output = _redact_http_json_raw_fallback_value(meta_safe_output)
        return (
            f"{resolved_display_name}: "
            f"{json.dumps(meta_safe_output, ensure_ascii=False)}"
        )
    meta_preview_output = (
        step_tool_meta.get("output_preview")
        if isinstance(step_tool_meta, dict)
        else None
    )
    meta_preview_mapping = _coerce_tool_output_preview_mapping(meta_preview_output)
    if isinstance(meta_preview_mapping, dict) and not isinstance(output, dict):
        if _step_tool_meta_uses_http_json_execution(step_tool_meta):
            meta_preview_mapping = _normalize_http_json_safe_output_shape(
                meta_preview_mapping
            )
        result_summary = build_tool_result_summary(
            name=canonical_name,
            output=meta_preview_mapping,
            display_name=resolved_display_name,
            registration=resolved_registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        if result_summary is None:
            result_summary = _build_tool_result_summary_from_step_meta_semantics(
                output=meta_preview_mapping,
                step_tool_meta=step_tool_meta,
            )
        if result_summary:
            return f"{resolved_display_name}: {result_summary}"
    if meta_preview_output is not None and not isinstance(output, dict):
        if isinstance(meta_preview_mapping, dict) and _step_tool_meta_uses_http_json_execution(
            step_tool_meta
        ):
            return (
                f"{resolved_display_name}: "
                f"{json.dumps(meta_preview_mapping, ensure_ascii=False)}"
            )
        if _step_tool_meta_uses_http_json_execution(step_tool_meta):
            meta_preview_output = _redact_http_json_raw_fallback_value(
                meta_preview_output
            )
        return (
            f"{resolved_display_name}: "
            f"{json.dumps(meta_preview_output, ensure_ascii=False)}"
        )
    if isinstance(output, dict):
        result_summary = build_tool_result_summary(
            name=canonical_name,
            output=output,
            display_name=resolved_display_name,
            registration=resolved_registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        if result_summary is None:
            result_summary = _build_tool_result_summary_from_step_meta_semantics(
                output=output,
                step_tool_meta=step_tool_meta,
            )
        if result_summary:
            return f"{resolved_display_name}: {result_summary}"
        meta_safe_output = _resolve_step_tool_safe_output(step_tool_meta)
        if meta_safe_output is not None:
            return (
                f"{resolved_display_name}: "
                f"{json.dumps(meta_safe_output, ensure_ascii=False)}"
            )
        if meta_preview_output is not None:
            if _step_tool_meta_uses_http_json_execution(step_tool_meta):
                meta_preview_output = _redact_http_json_raw_fallback_value(
                    meta_preview_output
                )
            return (
                f"{resolved_display_name}: "
                f"{json.dumps(meta_preview_output, ensure_ascii=False)}"
            )
    observation_output = output
    if isinstance(output, dict):
        effective_result_output_keys = get_tool_effective_result_output_keys(
            name=canonical_name,
            registration=resolved_registration,
        )
        observation_output = build_tool_result_output(
            name=canonical_name,
            output=output,
            registry=registry,
            registration=resolved_registration,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        if not effective_result_output_keys:
            preview_output = build_tool_result_preview(
                name=canonical_name,
                output=observation_output,
                registry=registry,
                registration=resolved_registration,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            )
            if preview_output is not None:
                observation_output = preview_output
        if (
            isinstance(observation_output, dict)
            and _step_tool_meta_uses_http_json_execution(step_tool_meta)
        ):
            observation_output = _normalize_http_json_safe_output_shape(
                observation_output
            )
    return (
        f"{resolved_display_name}: "
        f"{json.dumps(observation_output, ensure_ascii=False)}"
    )


def build_tool_trace_event(
    *,
    task_id: str,
    step_id: str,
    step: dict[str, object],
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "step_id": step_id,
        "step": _sanitize_tool_trace_event_step(step),
    }


def _sanitize_tool_trace_event_step(step: dict[str, object]) -> dict[str, object]:
    tool_obj = get_action_step_tool_meta(step)
    if not _step_tool_meta_uses_http_json_execution(tool_obj):
        return step
    sanitized_step = dict(step)
    meta = sanitized_step.get("meta")
    if not isinstance(meta, dict):
        return step
    sanitized_meta = dict(meta)
    sanitized_tool = dict(tool_obj) if isinstance(tool_obj, dict) else {}
    safe_output = build_tool_step_output(step)
    if isinstance(safe_output, dict):
        sanitized_tool["output"] = safe_output
    preview_value = sanitized_tool.get("output_preview")
    preview_mapping = _coerce_tool_output_preview_mapping(preview_value)
    if isinstance(preview_mapping, dict):
        sanitized_tool["output_preview"] = _normalize_http_json_safe_output_shape(
            preview_mapping
        )
    elif isinstance(preview_value, str):
        sanitized_tool["output_preview"] = _redact_http_json_raw_fallback_value(
            preview_value
        )
    sanitized_meta["tool"] = sanitized_tool
    sanitized_step["meta"] = sanitized_meta
    return sanitized_step


def _sanitize_tool_trace_event_payload(event: object) -> object:
    if not isinstance(event, dict):
        return event
    step = event.get("step")
    if not isinstance(step, dict):
        return event
    sanitized_step = _sanitize_tool_trace_event_step(step)
    if sanitized_step is step:
        return event
    sanitized_event = dict(event)
    sanitized_event["step"] = sanitized_step
    return sanitized_event


def build_tool_terminal_failure_transition(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    error_message: str,
    retry_count: int,
) -> dict[str, object]:
    return _sanitize_tool_terminal_failure_payload(
        {
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
    )


def _sanitize_tool_terminal_failure_payload(
    payload: dict[str, object] | None,
) -> dict[str, object] | None:
    if payload is None:
        return None
    sanitized = sanitize_tool_registry_diagnostics_artifact_payload(payload)
    assert isinstance(sanitized, dict)
    return sanitized


def _sanitize_tool_plan_item_result_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = dict(payload)
    for key in ("action_step", "terminal_failure"):
        if key in sanitized:
            sanitized[key] = _sanitize_tool_runtime_trace_artifact_payload(
                sanitized[key]
            )
    if "success_bundle" in sanitized:
        sanitized["success_bundle"] = _sanitize_tool_plan_success_bundle_payload(
            sanitized["success_bundle"]
        )
    if "last_error" in sanitized:
        sanitized["last_error"] = sanitize_tool_registry_diagnostics_artifact_payload(
            sanitized["last_error"]
        )
    return sanitized


def _sanitize_tool_plan_success_bundle_payload(
    success_bundle: object,
) -> object:
    if not isinstance(success_bundle, dict):
        return success_bundle
    bundle = dict(success_bundle)
    if "trace" in bundle:
        bundle["trace"] = _sanitize_tool_trace_event_payload(bundle["trace"])
    if "rag_followup" in bundle:
        bundle["rag_followup"] = _sanitize_tool_plan_success_bundle_rag_followup_payload(
            bundle["rag_followup"]
        )
    return bundle


def _sanitize_tool_plan_success_bundle_rag_followup_payload(
    rag_followup: object,
) -> object:
    if not isinstance(rag_followup, dict):
        return rag_followup
    followup = dict(rag_followup)
    step = followup.get("step")
    if isinstance(step, dict):
        followup["step"] = _sanitize_tool_trace_event_step(step)
    if "trace" in followup:
        followup["trace"] = _sanitize_tool_trace_event_payload(followup["trace"])
    return followup


def build_tool_rag_step(
    *,
    step_id: str,
    seq: int,
    model: str,
    chunks: list[str],
    chunk_metadata: list[dict[str, object]] | None = None,
    knowledge_base_id: str | None,
    token_count: int,
    content: str | None = None,
) -> dict[str, object]:
    rag_meta: dict[str, object] = {
        "chunks": chunks,
    }
    if isinstance(knowledge_base_id, str) and knowledge_base_id:
        rag_meta["knowledge_base_id"] = normalize_knowledge_base_id(knowledge_base_id)
    safe_chunk_metadata = [
        dict(metadata)
        for metadata in (chunk_metadata or [])
        if isinstance(metadata, dict) and metadata
    ]
    if safe_chunk_metadata:
        rag_meta["chunk_metadata"] = safe_chunk_metadata
        document_versions = _build_tool_rag_document_versions(safe_chunk_metadata)
        if document_versions:
            rag_meta["document_versions"] = document_versions
    return {
        "id": step_id,
        "seq": seq,
        "type": "thought",
        "content": content
        or "Knowledge Retrieval returned snippets from the selected knowledge base.",
        "meta": {
            "model": model,
            "step_type": "rag_retrieval",
            "tokens": token_count,
            "cost_estimate": None,
            "rag": rag_meta,
        },
    }


def _build_tool_rag_followup_content(
    *,
    display_name: str | None,
    runtime_semantic_kind: str | None,
    semantic_family: str | None,
) -> str:
    normalized_display_name = (
        str(display_name).strip() if isinstance(display_name, str) else ""
    )
    normalized_runtime_semantic_kind = _normalize_tool_semantic_kind(
        runtime_semantic_kind
    )
    normalized_semantic_family = _normalize_tool_semantic_kind(semantic_family)
    if (
        normalized_runtime_semantic_kind != "knowledge_retrieval"
        and normalized_semantic_family == "knowledge_retrieval"
    ):
        if normalized_display_name:
            return f"{normalized_display_name} returned snippets."
        return "Knowledge Retrieval returned snippets."
    if normalized_display_name and normalized_display_name != "Knowledge Retrieval":
        return f"{normalized_display_name} returned snippets from the selected knowledge base."
    return "Knowledge Retrieval returned snippets from the selected knowledge base."


_TOOL_RAG_DOCUMENT_TEXT_FIELDS = (
    "snippet",
    "snippet_text",
    "snippetText",
    "content",
    "content_text",
    "contentText",
    "text",
    "text_content",
    "textContent",
    "excerpt",
    "summary",
    "description",
    "body",
    "body_text",
    "bodyText",
    "plain_text",
    "plainText",
    "markdown",
    "chunk",
    "chunkText",
    "passage",
    "page_content",
    "pageContent",
    "document_text",
    "documentText",
)
_TOOL_RAG_DOCUMENT_CONTAINER_FIELDS = (
    "metadata",
    "document",
    "payload",
    "_source",
    "chunk",
    "node",
    "data",
    "record",
    "item",
    "attributes",
    "source",
    "fields",
    "entity",
    "rich_snippet",
    "richSnippet",
    "top",
    "detected_extensions",
    "detectedExtensions",
)
_TOOL_RAG_DOCUMENT_LIST_FIELDS = (
    "documents",
    "items",
    "results",
    "hits",
    "matches",
    "organic_results",
    "organicResults",
    "points",
    "source_nodes",
    "sourceNodes",
    "data",
    "records",
    "value",
)
_TOOL_RAG_DOCUMENT_VERSION_RE = re.compile(r"^sha256:[a-f0-9]{16,64}$")
_TOOL_RAG_CONTENT_HASH_RE = re.compile(r"^[a-f0-9]{64}$")
_TOOL_RAG_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)(^|[?&#;\s])(?:api[_-]?key|access[_-]?token|token|secret|password)=[^&#;\s]+"
)


def _redact_tool_rag_chunk_text(raw_value: str) -> str:
    return _redact_http_json_sensitive_payload_text(raw_value)


def _sanitize_tool_rag_metadata_text(value: object, *, limit: int) -> str | None:
    raw = _coerce_tool_execution_string_like_value(value)
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    safe = _redact_tool_rag_chunk_text(text)
    safe = _TOOL_RAG_SENSITIVE_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}[redacted]",
        safe,
    )
    return safe[:limit]


def _sanitize_tool_rag_document_version(value: object) -> str | None:
    raw = _sanitize_tool_rag_metadata_text(value, limit=80)
    if raw and _TOOL_RAG_DOCUMENT_VERSION_RE.fullmatch(raw):
        return raw
    return None


def _sanitize_tool_rag_content_hash(value: object) -> str | None:
    raw = _sanitize_tool_rag_metadata_text(value, limit=80)
    if raw and _TOOL_RAG_CONTENT_HASH_RE.fullmatch(raw):
        return raw
    return None


def _coerce_tool_rag_metadata_mapping(raw_document: Mapping) -> dict[str, object]:
    metadata: dict[str, object] = {}
    raw_metadata = raw_document.get("metadata")
    if isinstance(raw_metadata, Mapping):
        metadata.update(dict(raw_metadata))
    for key in (
        "source",
        "document_id",
        "documentId",
        "document_version",
        "documentVersion",
        "content_hash",
        "contentHash",
    ):
        if key in raw_document:
            metadata[key] = raw_document[key]
    return metadata


def _build_tool_rag_chunk_metadata(raw_document: Mapping) -> dict[str, object]:
    raw_metadata = _coerce_tool_rag_metadata_mapping(raw_document)
    metadata: dict[str, object] = {}
    source = _sanitize_tool_rag_metadata_text(raw_metadata.get("source"), limit=240)
    if source:
        metadata["source"] = source
    raw_document_id = raw_metadata.get("document_id", raw_metadata.get("documentId"))
    document_id = _sanitize_tool_rag_metadata_text(raw_document_id, limit=128)
    if document_id:
        metadata["document_id"] = document_id
    raw_document_version = raw_metadata.get(
        "document_version",
        raw_metadata.get("documentVersion"),
    )
    document_version = _sanitize_tool_rag_document_version(raw_document_version)
    if document_version:
        metadata["document_version"] = document_version
    raw_content_hash = raw_metadata.get("content_hash", raw_metadata.get("contentHash"))
    content_hash = _sanitize_tool_rag_content_hash(raw_content_hash)
    if content_hash:
        metadata["content_hash"] = content_hash
    return metadata


def _extract_tool_rag_chunk_from_document_mapping(
    raw_document: dict,
    *,
    depth: int = 0,
    visited: set[int] | None = None,
) -> str | None:
    if depth > 4:
        return None
    if visited is None:
        visited = set()
    document_id = id(raw_document)
    if document_id in visited:
        return None
    visited.add(document_id)
    for field_name in _TOOL_RAG_DOCUMENT_TEXT_FIELDS:
        raw_value = raw_document.get(field_name)
        if not isinstance(raw_value, str):
            continue
        normalized_chunk = raw_value.strip()
        if normalized_chunk:
            return _redact_tool_rag_chunk_text(normalized_chunk)
    for field_name in _TOOL_RAG_DOCUMENT_TEXT_FIELDS:
        nested_document = raw_document.get(field_name)
        if not isinstance(nested_document, dict):
            continue
        nested_chunk = _extract_tool_rag_chunk_from_document_mapping(
            nested_document,
            depth=depth + 1,
            visited=visited,
        )
        if nested_chunk:
            return nested_chunk
    for container_name in _TOOL_RAG_DOCUMENT_CONTAINER_FIELDS:
        nested_document = raw_document.get(container_name)
        if isinstance(nested_document, str):
            normalized_chunk = nested_document.strip()
            if normalized_chunk:
                return _redact_tool_rag_chunk_text(normalized_chunk)
            continue
        if not isinstance(nested_document, dict):
            continue
        nested_chunk = _extract_tool_rag_chunk_from_document_mapping(
            nested_document,
            depth=depth + 1,
            visited=visited,
        )
        if nested_chunk:
            return nested_chunk
    return None


def _extract_tool_rag_chunks_from_document_list(raw_documents: object) -> list[str]:
    normalized_documents = _extract_http_json_retrieval_list_from_container(raw_documents)
    if normalized_documents is None:
        return []
    extracted_chunks: list[str] = []
    for raw_document in normalized_documents:
        if isinstance(raw_document, str):
            normalized_chunk = raw_document.strip()
            if normalized_chunk:
                extracted_chunks.append(_redact_tool_rag_chunk_text(normalized_chunk))
            continue
        if not isinstance(raw_document, dict):
            continue
        normalized_chunk = _extract_tool_rag_chunk_from_document_mapping(raw_document)
        if normalized_chunk:
            extracted_chunks.append(normalized_chunk)
    return extracted_chunks


def _extract_tool_rag_chunks_from_output(output: dict[str, object]) -> list[str]:
    raw_chunks = output.get("chunks")
    if isinstance(raw_chunks, (list, tuple)):
        extracted_chunks = _extract_tool_rag_chunks_from_document_list(raw_chunks)
        if extracted_chunks:
            return extracted_chunks

    for list_field_name in _TOOL_RAG_DOCUMENT_LIST_FIELDS:
        extracted_chunks = _extract_tool_rag_chunks_from_document_list(
            output.get(list_field_name)
        )
        if extracted_chunks:
            return extracted_chunks
    return []


def _extract_tool_rag_chunk_metadata_from_document_list(
    raw_documents: object,
) -> list[dict[str, object]]:
    normalized_documents = _extract_http_json_retrieval_list_from_container(raw_documents)
    if normalized_documents is None:
        return []
    chunk_metadata: list[dict[str, object]] = []
    for raw_document in normalized_documents:
        if isinstance(raw_document, str):
            if raw_document.strip():
                chunk_metadata.append({})
            continue
        if not isinstance(raw_document, Mapping):
            continue
        raw_mapping = dict(raw_document)
        normalized_chunk = _extract_tool_rag_chunk_from_document_mapping(raw_mapping)
        if normalized_chunk:
            chunk_metadata.append(_build_tool_rag_chunk_metadata(raw_document))
    return chunk_metadata


def _extract_tool_rag_chunk_metadata_from_output(
    output: dict[str, object],
) -> list[dict[str, object]]:
    extracted = _extract_tool_rag_chunk_metadata_from_document_list(
        output.get("chunks")
    )
    if extracted and any(item for item in extracted):
        return extracted
    for list_field_name in _TOOL_RAG_DOCUMENT_LIST_FIELDS:
        extracted = _extract_tool_rag_chunk_metadata_from_document_list(
            output.get(list_field_name)
        )
        if extracted and any(item for item in extracted):
            return extracted
    return []


def _build_tool_rag_document_versions(
    chunk_metadata: list[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for metadata in chunk_metadata:
        document_version = str(metadata.get("document_version") or "").strip()
        content_hash = str(metadata.get("content_hash") or "").strip()
        if not _TOOL_RAG_DOCUMENT_VERSION_RE.fullmatch(document_version):
            continue
        if not _TOOL_RAG_CONTENT_HASH_RE.fullmatch(content_hash):
            continue
        key = f"{document_version}\x1f{content_hash}"
        if key not in grouped:
            grouped[key] = {
                "document_version": document_version,
                "content_hash": content_hash,
                "chunk_count": 0,
            }
            source = str(metadata.get("source") or "").strip()
            if source:
                grouped[key]["source"] = source
            document_id = str(metadata.get("document_id") or "").strip()
            if document_id:
                grouped[key]["document_id"] = document_id
        grouped[key]["chunk_count"] = int(grouped[key]["chunk_count"]) + 1
    document_versions = list(grouped.values())
    document_versions.sort(
        key=lambda item: (
            str(item.get("source") or ""),
            str(item.get("document_id") or ""),
            str(item.get("document_version") or ""),
        )
    )
    return document_versions


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
    result = {
        "outcome": outcome,
        "action_step": action_step,
        "events": events,
        "retryable": retryable,
        "error_message": error_message,
        "retry_count": retry_count,
    }
    if outcome == "success" and error_message is None:
        return result
    return _sanitize_tool_attempt_error_result_payload(result)


def _sanitize_tool_attempt_error_result_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = dict(payload)
    for key in ("action_step", "events", "error_message"):
        if key in sanitized:
            sanitized[key] = sanitize_tool_registry_diagnostics_artifact_payload(
                sanitized[key]
            )
    return sanitized


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
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    display_name = get_tool_execution_display_name_from_registration(
        name=runtime_ctx.registration.name,
        registration=runtime_ctx.registration,
    )
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
            display_name=display_name,
            registration=runtime_ctx.registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
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
        display_name=display_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
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
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    return {
        "step_id": step_id,
        "action_step": build_action_step_initial_step(
            step_id=step_id,
            seq=seq,
            name=canonical_name,
            meta=build_action_step_initial_meta(
                name=canonical_name,
                tool_input=tool_input,
                model=model,
                label=label,
                token_count=token_count,
                display_name=display_name,
                registration=registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        ),
    }


def build_tool_iteration_success_artifacts(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    name: str,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    output = build_tool_step_output(action_step)
    step_tool_meta = get_action_step_tool_meta(action_step)
    canonical_name = normalize_tool_registry_name(name)
    return {
        "trace": build_tool_trace_event(
            task_id=task_id,
            step_id=step_id,
            step=action_step,
        ),
        "observation": build_tool_observation_entry(
            name=canonical_name,
            output=output,
            display_name=display_name,
            step_tool_meta=step_tool_meta,
            registration=registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "output": output,
    }


def build_tool_rag_followup(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    tool_name: str,
    tool_kind: str | None = None,
    tool_semantic_family: str | None = None,
    display_name: str | None = None,
    output: dict[str, object] | None,
    token_count: int,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object] | None:
    if not isinstance(output, dict):
        return None
    runtime_semantic_kind = _normalize_tool_semantic_kind(tool_kind)
    if runtime_semantic_kind is None:
        runtime_semantic_kind = _get_tool_runtime_trace_semantic_kind(
            name=tool_name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
    semantic_family = _normalize_tool_semantic_kind(tool_semantic_family)
    if semantic_family is None:
        semantic_family = get_tool_semantic_kind(
            name=tool_name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
    semantic_kind = runtime_semantic_kind
    if semantic_kind != "knowledge_retrieval":
        semantic_kind = semantic_family
    if semantic_kind != "knowledge_retrieval":
        return None
    chunks = _extract_tool_rag_chunks_from_output(output)
    if not chunks:
        return None
    chunk_metadata = _extract_tool_rag_chunk_metadata_from_output(output)
    kb = output.get("knowledge_base_id")
    step = build_tool_rag_step(
        step_id=step_id,
        seq=seq,
        model=model,
        chunks=chunks,
        chunk_metadata=chunk_metadata,
        knowledge_base_id=str(kb) if kb else None,
        token_count=token_count,
        content=_build_tool_rag_followup_content(
            display_name=display_name,
            runtime_semantic_kind=runtime_semantic_kind,
            semantic_family=semantic_family,
        ),
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
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    normalized_output = (
        normalize_tool_output_for_registration(
            output=output,
            registration=runtime_ctx.registration,
        )
        if isinstance(output, dict)
        else output
    )
    execution_display_name = get_tool_execution_display_name_from_registration(
        name=runtime_ctx.registration.name,
        registration=runtime_ctx.registration,
    )
    start_events = build_tool_attempt_start_events(
        task_id=task_id,
        step_id=step_id,
        name=name,
        tool_input=tool_input,
        attempt=runtime_ctx.attempt,
        display_name=execution_display_name,
        registration=runtime_ctx.registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    outcome = build_tool_attempt_outcome(
        task_id=task_id,
        step_id=step_id,
        action_step=dict(action_step),
        runtime_ctx=runtime_ctx,
        name=name,
        tool_input=tool_input,
        output=normalized_output,
        exc=exc,
        token_count=token_count,
        last_error=last_error,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if outcome["outcome"] == "success":
        observation_display_name = get_tool_observation_display_name_from_registration(
            name=runtime_ctx.registration.name,
            registration=runtime_ctx.registration,
        )
        return {
            "start_events": start_events,
            "outcome": outcome,
            "success_artifacts": build_tool_iteration_success_artifacts(
                task_id=task_id,
                step_id=step_id,
                action_step=outcome["action_step"],
                name=name,
                display_name=observation_display_name,
                registration=runtime_ctx.registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
            "rag_source_output": normalized_output if isinstance(normalized_output, dict) else None,
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
    return _sanitize_tool_plan_item_result_payload(
        {
            "outcome": outcome,
            "action_step": action_step,
            "last_error": last_error,
            "success_bundle": success_bundle,
            "terminal_failure": terminal_failure,
        }
    )


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
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
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
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    success_artifacts = iteration_execution.get("success_artifacts")
    rag_followup = None
    if success_artifacts is not None:
        success_output = iteration_execution.get("rag_source_output")
        if not isinstance(success_output, dict):
            success_output = success_artifacts["output"]
        rag_followup = build_tool_rag_followup(
            task_id=task_id,
            step_id=rag_step_id,
            seq=int(action_step.get("seq", 0)) + 1,
            model=model,
            tool_name=name,
            tool_kind=_get_tool_runtime_trace_semantic_kind(
                name=runtime_ctx.registration.name,
                registration=runtime_ctx.registration,
            ),
            tool_semantic_family=get_tool_semantic_kind(
                name=runtime_ctx.registration.name,
                registration=runtime_ctx.registration,
            ),
            display_name=get_tool_display_name_from_registration(
                name=runtime_ctx.registration.name,
                registration=runtime_ctx.registration,
            ),
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


def _sanitize_tool_plan_item_payload_dict(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = _sanitize_tool_runtime_trace_artifact_payload(payload)
    assert isinstance(sanitized, dict)
    return sanitized


def _sanitize_tool_plan_item_payload_list(
    payload: list[dict[str, object]],
) -> list[dict[str, object]]:
    sanitized = _sanitize_tool_runtime_trace_artifact_payload(payload)
    assert isinstance(sanitized, list)
    return sanitized


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
        trace_step = success_effects["trace_step"]
        trace_steps = [
            _sanitize_tool_trace_event_step(trace_step)
            if isinstance(trace_step, dict)
            else trace_step
        ]
        trace_events = [
            _sanitize_tool_trace_event_payload(loop_execution_result["trace_event"])
        ]
        rag_followup = success_effects["rag_followup"]
        if rag_followup is not None:
            trace_steps.append(rag_followup["step"])
            trace_events.append(_sanitize_tool_trace_event_payload(rag_followup["trace"]))
        return _sanitize_tool_plan_item_payload_dict(
            {
                "trace_steps": trace_steps,
                "trace_events": trace_events,
                "observation": success_effects["observation"],
                "tool_observations": [success_effects["observation"]],
                "terminal_effects": None,
                "seq_increment": 1 if rag_followup is not None else 0,
                "should_return": False,
            }
        )

    assert terminal_effects is not None
    terminal_trace_step = terminal_effects["trace_step"]
    terminal_trace = terminal_effects["trace"]
    sanitized_terminal_effects = dict(terminal_effects)
    if isinstance(terminal_trace_step, dict):
        sanitized_terminal_effects["trace_step"] = _sanitize_tool_trace_event_step(
            terminal_trace_step
        )
    sanitized_terminal_effects["trace"] = _sanitize_tool_trace_event_payload(
        terminal_trace
    )
    return _sanitize_tool_plan_item_payload_dict(
        {
            "trace_steps": [sanitized_terminal_effects["trace_step"]],
            "trace_events": [sanitized_terminal_effects["trace"]],
            "observation": None,
            "tool_observations": [],
            "terminal_effects": sanitized_terminal_effects,
            "seq_increment": 0,
            "should_return": bool(loop_execution_result["should_return"]),
        }
    )


def build_tool_plan_item_terminal_return_effects(
    *,
    terminal_effects: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "task_status": terminal_effects["status"],
            "state_event": terminal_effects["state"],
            "failure_event": {
                "event_type": "task_failed",
                "code": "tool_execution_error",
                "message": terminal_effects["error_message"],
                "detail": terminal_effects["audit_detail"],
            },
        }
    )


def build_tool_plan_item_continue_update(
    *,
    stream_effects: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "tool_observations": list(stream_effects["tool_observations"]),
            "seq_increment": int(stream_effects["seq_increment"]),
        }
    )


def build_tool_plan_item_continue_action(
    *,
    continue_update: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "tool_observations": list(continue_update["tool_observations"]),
            "seq_increment": int(continue_update["seq_increment"]),
        }
    )


def build_tool_plan_item_next_action(
    *,
    continue_update: dict[str, object],
    terminal_return_effects: dict[str, object] | None,
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "kind": "return" if terminal_return_effects is not None else "continue",
            "continue_update": continue_update,
            "terminal_return_effects": terminal_return_effects,
        }
    )


def build_tool_plan_item_return_action(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
    user_id: str,
    terminal_return_effects: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "complete_task_kwargs": {
                "task_id": task_id,
                "trace_steps": trace_steps,
                "user_id": user_id,
                "status": str(terminal_return_effects["task_status"]),
            },
            "failure_event_kwargs": terminal_return_effects["failure_event"],
            "state_event": terminal_return_effects["state_event"],
        }
    )


def build_tool_plan_item_trace_write_action(
    *,
    trace_write: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "trace_step": trace_write["step"],
            "trace_event": trace_write["event"],
            "persist_force": bool(trace_write["force_persist"]),
        }
    )


def build_tool_plan_item_next_action_execution(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
    user_id: str,
    next_action: dict[str, object],
) -> dict[str, object]:
    continue_action = build_tool_plan_item_continue_action(
        continue_update=next_action["continue_update"],
    )
    if str(next_action["kind"]) == "return":
        terminal_return_effects = next_action["terminal_return_effects"]
        assert terminal_return_effects is not None
        return _sanitize_tool_plan_item_payload_dict(
            {
                "kind": "return",
                "continue_update": next_action["continue_update"],
                "continue_action": continue_action,
                "return_action": build_tool_plan_item_return_action(
                    task_id=task_id,
                    trace_steps=trace_steps,
                    user_id=user_id,
                    terminal_return_effects=terminal_return_effects,
                ),
            }
        )
    return _sanitize_tool_plan_item_payload_dict(
        {
            "kind": "continue",
            "continue_update": next_action["continue_update"],
            "continue_action": continue_action,
            "return_action": None,
        }
    )


def build_tool_plan_item_service_actions(
    *,
    service_execution: dict[str, object],
) -> list[dict[str, object]]:
    actions = [
        build_tool_plan_item_trace_write_service_action(
            trace_write_action=trace_write_action,
        )
        for trace_write_action in service_execution["trace_write_actions"]
    ]
    next_action_execution = service_execution["next_action_execution"]
    if str(next_action_execution["kind"]) == "return":
        return_action = next_action_execution["return_action"]
        assert return_action is not None
        return _sanitize_tool_plan_item_payload_list(
            [
                *actions,
                *build_tool_plan_item_return_service_actions(
                    return_action=return_action,
                ),
            ]
        )

    continue_action = next_action_execution["continue_action"]
    return _sanitize_tool_plan_item_payload_list(
        [
            *actions,
            build_tool_plan_item_continue_service_action(
                continue_action=continue_action,
            ),
        ]
    )


def build_tool_plan_item_trace_write_service_action(
    *,
    trace_write_action: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "kind": "trace_write",
            "trace_step": trace_write_action["trace_step"],
            "trace_event": trace_write_action["trace_event"],
            "persist_force": bool(trace_write_action["persist_force"]),
        }
    )


def build_tool_plan_item_continue_service_action(
    *,
    continue_action: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "kind": "continue",
            "tool_observations": list(continue_action["tool_observations"]),
            "seq_increment": int(continue_action["seq_increment"]),
        }
    )


def build_tool_plan_item_return_service_actions(
    *,
    return_action: dict[str, object],
) -> list[dict[str, object]]:
    return _sanitize_tool_plan_item_payload_list(
        [
            {
                "kind": "complete_task",
                "kwargs": return_action["complete_task_kwargs"],
            },
            {
                "kind": "record_failure_event",
                "kwargs": return_action["failure_event_kwargs"],
            },
            {
                "kind": "emit_state",
                "event": "state",
                "data": return_action["state_event"],
            },
            {
                "kind": "return",
            },
        ]
    )


def build_tool_plan_item_service_effects_execution(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
    user_id: str,
    service_effects: dict[str, object],
) -> dict[str, object]:
    service_execution = {
        "trace_write_actions": list(service_effects["trace_write_actions"]),
        "next_action_execution": build_tool_plan_item_next_action_execution(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
            next_action=service_effects["next_action"],
        ),
    }
    service_execution["service_actions"] = build_tool_plan_item_service_actions(
        service_execution=service_execution,
    )
    sanitized_service_execution = _sanitize_tool_runtime_trace_artifact_payload(
        service_execution
    )
    assert isinstance(sanitized_service_execution, dict)
    return sanitized_service_execution


def build_tool_plan_item_service_execution(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
    user_id: str,
    loop_execution_result: dict[str, object],
) -> dict[str, object]:
    service_effects = build_tool_plan_item_service_effects(
        loop_execution_result=loop_execution_result,
    )
    return build_tool_plan_item_service_effects_execution(
        task_id=task_id,
        trace_steps=trace_steps,
        user_id=user_id,
        service_effects=service_effects,
    )


def build_tool_plan_item_service_effects(
    *,
    loop_execution_result: dict[str, object],
) -> dict[str, object]:
    stream_effects = build_tool_plan_item_stream_effects(
        loop_execution_result=loop_execution_result,
    )
    continue_update = build_tool_plan_item_continue_update(
        stream_effects=stream_effects,
    )
    terminal_effects = stream_effects["terminal_effects"]
    terminal_return_effects = (
        build_tool_plan_item_terminal_return_effects(
            terminal_effects=terminal_effects,
        )
        if terminal_effects is not None
        else None
    )
    should_return = bool(stream_effects["should_return"])
    next_action = build_tool_plan_item_next_action(
        continue_update=continue_update,
        terminal_return_effects=terminal_return_effects,
    )
    trace_writes = [
        {
            "step": trace_step,
            "event": trace_event,
            "force_persist": should_return,
        }
        for trace_step, trace_event in zip(
            stream_effects["trace_steps"],
            stream_effects["trace_events"],
        )
    ]
    trace_write_actions = [
        build_tool_plan_item_trace_write_action(trace_write=trace_write)
        for trace_write in trace_writes
    ]
    service_effects = {
        "trace_steps": stream_effects["trace_steps"],
        "trace_events": stream_effects["trace_events"],
        "trace_writes": trace_writes,
        "trace_write_actions": trace_write_actions,
        "continue_update": continue_update,
        "next_action": next_action,
        "tool_observations": continue_update["tool_observations"],
        "seq_increment": continue_update["seq_increment"],
        "should_return": should_return,
        "terminal_return_effects": terminal_return_effects,
    }
    sanitized_service_effects = _sanitize_tool_runtime_trace_artifact_payload(
        service_effects
    )
    assert isinstance(sanitized_service_effects, dict)
    return sanitized_service_effects
