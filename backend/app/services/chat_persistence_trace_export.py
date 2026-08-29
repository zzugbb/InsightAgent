from __future__ import annotations

import re


def bind_chat_persistence_trace_export_public_names(namespace: dict[str, object]) -> None:
    globals().update(namespace)


def _normalize_trace_preview_excerpt(text: str, limit: int = 160) -> str:
    normalized = " ".join((text or "").strip().split())
    if not normalized:
        return ""
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


def _coerce_trace_string_like_value(value: object) -> object:
    if isinstance(value, UserString):
        return str(value)
    return value


def _normalize_trace_json_compatible_value(value: object) -> object:
    value = _coerce_trace_string_like_value(value)
    if isinstance(value, UserDict):
        value = value.data
    if isinstance(value, Mapping):
        return {
            str(_coerce_trace_string_like_value(key)): _normalize_trace_json_compatible_value(
                item
            )
            for key, item in value.items()
        }
    if isinstance(value, UserList):
        value = value.data
    if isinstance(value, tuple):
        value = list(value)
    if isinstance(value, list):
        return [_normalize_trace_json_compatible_value(item) for item in value]
    return value


def _stringify_trace_tool_output_preview(value: object) -> str:
    value = _normalize_trace_json_compatible_value(value)
    if value is None:
        return ""
    if isinstance(value, str):
        parsed_mapping = _parse_trace_tool_json_mapping_string(value)
        if isinstance(parsed_mapping, dict):
            return json.dumps(parsed_mapping, ensure_ascii=False, separators=(",", ":"))
        return value.strip()
    if isinstance(value, tuple):
        value = list(value)
    if isinstance(value, (dict, list, int, float, bool)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return ""


def _parse_trace_tool_json_mapping_string(value: str) -> dict[str, object] | None:
    value = _coerce_trace_string_like_value(value)
    if not isinstance(value, str):
        return None
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


def _coerce_trace_tool_output_preview_mapping(value: object) -> dict[str, object] | None:
    value = _normalize_trace_json_compatible_value(value)
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    return _parse_trace_tool_json_mapping_string(value)


def _coerce_trace_tool_output_mapping(value: object) -> dict[str, object] | None:
    value = _normalize_trace_json_compatible_value(value)
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    return _parse_trace_tool_json_mapping_string(value)


def _trace_tool_meta_uses_http_json_execution(tool_meta: dict[str, object]) -> bool:
    raw_execution_kind = _coerce_trace_string_like_value(tool_meta.get("execution_kind"))
    if (
        isinstance(raw_execution_kind, str)
        and raw_execution_kind.strip().lower() == "http_json"
    ):
        return True
    for raw_value in (tool_meta.get("label"), tool_meta.get("name")):
        if (
            _trace_tool_label_implies_real_retrieval_summary(raw_value)
            or _trace_tool_label_implies_real_calc_summary(raw_value)
        ):
            return True
    return False


def _trace_tool_meta_implies_provider_or_hosted_tool(
    tool_meta: dict[str, object],
) -> bool:
    if _trace_tool_meta_uses_http_json_execution(tool_meta):
        return True
    for raw_value in (tool_meta.get("label"), tool_meta.get("name")):
        normalized_label = _normalize_trace_tool_label(raw_value)
        if normalized_label.startswith(("provider ", "hosted ")):
            return True
        if isinstance(raw_value, str) and raw_value.strip().lower().startswith(
            ("provider_", "hosted_")
        ):
            return True
    return False


def _trace_label_implies_http_json_execution(value: object) -> bool:
    value = _coerce_trace_string_like_value(value)
    if not isinstance(value, str):
        return False
    normalized = " ".join(value.strip().lower().replace("_", " ").split())
    return "http json" in normalized


def _normalize_trace_http_json_tool_output(
    tool_meta: dict[str, object],
    output: dict[str, object],
) -> dict[str, object]:
    if not (
        _trace_tool_meta_implies_provider_or_hosted_tool(tool_meta)
        or _trace_tool_meta_uses_http_json_execution(tool_meta)
    ):
        return output
    output_with_hints = dict(output)
    injected_hint_keys: list[str] = []
    for hint_key in (
        "tool_kind",
        "semantic_kind",
        "semantic_family",
        "kind",
    ):
        if hint_key in output_with_hints:
            continue
        hint_value = tool_meta.get(hint_key)
        if isinstance(hint_value, str) and hint_value.strip():
            output_with_hints[hint_key] = hint_value
            injected_hint_keys.append(hint_key)
    normalized_output = _normalize_http_json_safe_output_shape(output_with_hints)
    for hint_key in injected_hint_keys:
        normalized_output.pop(hint_key, None)
    return normalized_output


def _normalize_trace_http_json_tool_input(
    tool_meta: dict[str, object],
    tool_input: dict[str, object],
) -> dict[str, object]:
    if not _trace_tool_meta_implies_provider_or_hosted_tool(tool_meta):
        return tool_input
    safe_tool_input = _redact_http_json_sensitive_payload_value(tool_input)
    if isinstance(safe_tool_input, dict):
        return safe_tool_input
    return tool_input


def _normalize_trace_tool_output_request_id(
    output: dict[str, object],
) -> dict[str, object]:
    if "request_id" not in output:
        return output
    normalized_output = dict(output)
    safe_request_id = _get_safe_http_json_request_id_display_value(
        normalized_output.get("request_id")
    )
    if safe_request_id is None:
        normalized_output.pop("request_id", None)
    else:
        normalized_output["request_id"] = safe_request_id
    return normalized_output


def _normalize_trace_tool_output_key_list(raw_value: object) -> list[str]:
    if isinstance(raw_value, UserList):
        raw_value = raw_value.data
    if not isinstance(raw_value, (list, tuple)):
        return []
    normalized_keys: list[str] = []
    for raw_key in raw_value:
        raw_key = _coerce_trace_string_like_value(raw_key)
        if not isinstance(raw_key, str):
            continue
        key = raw_key.strip()
        if key:
            normalized_keys.append(key)
    return normalized_keys


def _resolve_trace_safe_tool_output(tool_meta: dict[str, object]) -> object | None:
    normalized_keys = _normalize_trace_tool_output_key_list(
        tool_meta.get("effective_result_output_keys")
    )
    if not normalized_keys:
        return None
    output = tool_meta.get("output")
    output_mapping = _coerce_trace_tool_output_mapping(output)
    if not isinstance(output_mapping, dict):
        if _trace_tool_meta_implies_provider_or_hosted_tool(tool_meta):
            return _redact_http_json_raw_fallback_value(output)
        return output
    output_mapping = _normalize_trace_tool_output_request_id(
        _normalize_trace_http_json_tool_output(tool_meta, output_mapping)
    )
    return {
        key: output_mapping[key]
        for key in normalized_keys
        if key in output_mapping
    }


def _infer_trace_tool_preview_output_keys(output: dict[str, object]) -> list[str]:
    if (
        "documents_total" in output
        or "hit_count" in output
        or "knowledge_base_id" in output
    ):
        return ["documents_total", "hit_count", "knowledge_base_id", "request_id"]
    if "expression" in output or "result" in output:
        return ["expression", "result", "request_id"]
    if "plan" in output or "steps" in output:
        return ["plan", "steps", "request_id"]
    return []


def _resolve_trace_tool_output_preview(tool_meta: dict[str, object]) -> object | None:
    preview_value = tool_meta.get("output_preview")
    if preview_value is None:
        return None
    preview_mapping = _coerce_trace_tool_output_preview_mapping(preview_value)
    if not isinstance(preview_mapping, dict):
        if _trace_tool_meta_implies_provider_or_hosted_tool(tool_meta):
            return _redact_http_json_raw_fallback_value(preview_value)
        return preview_value
    preview_mapping = _normalize_trace_tool_output_request_id(
        _normalize_trace_http_json_tool_output(
            tool_meta,
            preview_mapping,
        )
    )
    preview_keys = _normalize_trace_tool_output_key_list(
        tool_meta.get("effective_result_preview_keys")
    )
    if not preview_keys:
        preview_keys = _normalize_trace_tool_output_key_list(
            tool_meta.get("result_preview_keys")
        )
    if not preview_keys and _trace_tool_meta_uses_http_json_execution(tool_meta):
        preview_keys = _infer_trace_tool_preview_output_keys(preview_mapping)
    if not preview_keys:
        return preview_mapping
    projected_preview = {
        key: preview_mapping[key]
        for key in preview_keys
        if key in preview_mapping
    }
    return projected_preview or preview_mapping


def _stringify_trace_safe_tool_output(tool_meta: dict[str, object]) -> str:
    return _stringify_trace_tool_output_preview(
        _resolve_trace_safe_tool_output(tool_meta)
    )


def _resolve_trace_tool_result_summary_input(
    tool_meta: dict[str, object],
) -> dict[str, object] | None:
    safe_output = _resolve_trace_safe_tool_output(tool_meta)
    if isinstance(safe_output, dict):
        return safe_output
    preview_output = _coerce_trace_tool_output_preview_mapping(
        tool_meta.get("output_preview")
    )
    if isinstance(preview_output, dict):
        return _normalize_trace_tool_output_request_id(
            _normalize_trace_http_json_tool_output(tool_meta, preview_output)
        )
    return None


def _normalize_trace_tool_semantic_kind(raw_value: object) -> str | None:
    raw_value = _coerce_trace_string_like_value(raw_value)
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip().lower()
    if not normalized:
        return None
    if normalized == "retrieval":
        return "knowledge_retrieval"
    if (
        normalized == "knowledge_retrieval"
        or normalized.endswith("knowledge_retrieval")
        or normalized.endswith("_retrieval")
    ):
        return "knowledge_retrieval"
    if normalized == "planner":
        return "task_planner"
    if normalized == "task_planner" or normalized.endswith("_planner"):
        return "task_planner"
    if normalized == "calculator":
        return "local_calculator"
    if (
        normalized == "local_calculator"
        or normalized.endswith("_calculator")
        or normalized.endswith("_calc")
    ):
        return "local_calculator"
    return normalized


def _normalize_trace_tool_label(raw_value: object) -> str:
    raw_value = _coerce_trace_string_like_value(raw_value)
    if not isinstance(raw_value, str):
        return ""
    normalized = raw_value.strip()
    normalized = re.sub(r"\s*\[[^\[\]]+\]\s*$", "", normalized)
    return " ".join(normalized.lower().replace("_", " ").split())


def _trace_tool_label_implies_local_knowledge_retrieval(raw_value: object) -> bool:
    normalized = _normalize_trace_tool_label(raw_value)
    return normalized in {
        "knowledge retrieval",
        "hot retrieval",
        "task retrieve",
        "task retrieve hot",
        "mock retrieve",
    }


def _trace_tool_label_implies_real_retrieval_summary(raw_value: object) -> bool:
    normalized = _normalize_trace_tool_label(raw_value)
    return normalized in {
        "provider search",
        "hosted search",
        "provider retrieval",
    }


def _trace_tool_label_implies_real_calc_summary(raw_value: object) -> bool:
    normalized = _normalize_trace_tool_label(raw_value)
    return normalized in {
        "provider math",
        "hosted math",
        "provider calc",
        "provider calculator",
        "hosted calc",
        "hosted calculator",
    }


def _trace_tool_label_implies_planner_summary(raw_value: object) -> bool:
    normalized = _normalize_trace_tool_label(raw_value)
    return normalized in {
        "task planner",
        "provider planner",
        "hosted planner",
        "mock planner",
    }


def _normalize_trace_tool_result_plan_steps(raw_steps: object) -> list[str]:
    if isinstance(raw_steps, UserList):
        raw_steps = raw_steps.data
    if not isinstance(raw_steps, (list, tuple)):
        return []
    normalized_steps: list[str] = []
    for raw_step in raw_steps:
        raw_step = _coerce_trace_string_like_value(raw_step)
        if not isinstance(raw_step, str):
            continue
        step = raw_step.strip()
        if step:
            normalized_steps.append(step)
    return normalized_steps


def _infer_trace_tool_result_summary(tool_meta: dict[str, object]) -> str:
    output = _resolve_trace_tool_result_summary_input(tool_meta)
    if not isinstance(output, dict):
        return ""
    raw_output = tool_meta.get("output") if isinstance(tool_meta.get("output"), dict) else None
    raw_preview_output = (
        _coerce_trace_tool_output_preview_mapping(tool_meta.get("output_preview"))
    )

    explicit_semantic_kind = _normalize_trace_tool_semantic_kind(
        tool_meta.get("semantic_kind")
    )
    fallback_runtime_kind = _normalize_trace_tool_semantic_kind(
        tool_meta.get("kind")
        or output.get("tool_kind")
        or output.get("kind")
        or (raw_output or {}).get("tool_kind")
        or (raw_output or {}).get("kind")
        or (raw_preview_output or {}).get("tool_kind")
        or (raw_preview_output or {}).get("kind")
    )
    runtime_semantic_kind = explicit_semantic_kind or fallback_runtime_kind
    semantic_family = _normalize_trace_tool_semantic_kind(
        tool_meta.get("semantic_family") or output.get("tool_family")
    )
    label_implies_real_calc = (
        _trace_tool_label_implies_real_calc_summary(tool_meta.get("label"))
        or _trace_tool_label_implies_real_calc_summary(tool_meta.get("name"))
    )
    label_implies_real_retrieval = (
        _trace_tool_label_implies_real_retrieval_summary(tool_meta.get("label"))
        or _trace_tool_label_implies_real_retrieval_summary(tool_meta.get("name"))
    )

    plan = _coerce_trace_string_like_value(output.get("plan"))
    if isinstance(plan, str) and plan.strip():
        return f"Planned steps - {plan.strip()}."
    steps = _normalize_trace_tool_result_plan_steps(output.get("steps"))
    if steps:
        return f"Planned steps - {' -> '.join(steps)}."

    expression = _coerce_trace_string_like_value(output.get("expression"))
    result = output.get("result")
    request_id = _coerce_trace_string_like_value(output.get("request_id"))
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

    hit_count = output.get("hit_count")
    knowledge_base_id = output.get("knowledge_base_id")
    if isinstance(hit_count, int) and hit_count >= 0:
        hit_label = "hit" if hit_count == 1 else "hits"
        label_implies_local_retrieval = (
            _trace_tool_label_implies_local_knowledge_retrieval(tool_meta.get("label"))
            or _trace_tool_label_implies_local_knowledge_retrieval(tool_meta.get("name"))
        )
        if (
            (
                explicit_semantic_kind == "knowledge_retrieval"
                or (
                    explicit_semantic_kind is None
                    and (
                        semantic_family == "knowledge_retrieval"
                        or (
                            semantic_family is None
                            and label_implies_local_retrieval
                        )
                    )
                )
            )
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

    documents_total = output.get("documents_total")
    if isinstance(documents_total, int) and documents_total >= 0:
        document_label = "document" if documents_total == 1 else "documents"
        source_suffix = ""
        if isinstance(knowledge_base_id, str) and knowledge_base_id.strip():
            if explicit_semantic_kind == "knowledge_retrieval":
                source_suffix = f" from knowledge base {knowledge_base_id.strip()}"
            elif (
                runtime_semantic_kind != "knowledge_retrieval"
                and semantic_family == "knowledge_retrieval"
            ):
                source_suffix = f" from {knowledge_base_id.strip()}"
            elif (
                runtime_semantic_kind is None
                and semantic_family is None
                and label_implies_real_retrieval
            ):
                source_suffix = f" from {knowledge_base_id.strip()}"
        if isinstance(request_id, str) and request_id.strip():
            return (
                f"Retrieved {documents_total} {document_label}{source_suffix} "
                f"(request id {request_id.strip()})."
            )
        return f"Retrieved {documents_total} {document_label}{source_suffix}."
    return ""


def _resolve_trace_tool_semantic_category(
    tool_meta: dict[str, object],
) -> str | None:
    semantic = _normalize_trace_tool_semantic_kind(
        tool_meta.get("semantic_family")
        or tool_meta.get("semantic_kind")
        or tool_meta.get("kind")
    )
    if semantic:
        if semantic == "knowledge_retrieval" or semantic.endswith("_retrieval"):
            return "retrieval"
        if (
            semantic == "local_calculator"
            or semantic.endswith("_calculator")
            or semantic.endswith("_calc")
        ):
            return "calculator"
        if semantic == "task_planner" or semantic.endswith("_planner"):
            return "planner"
    output = _resolve_trace_tool_result_summary_input(tool_meta)
    if not isinstance(output, dict):
        return None
    label_implies_retrieval = (
        _trace_tool_label_implies_local_knowledge_retrieval(tool_meta.get("label"))
        or _trace_tool_label_implies_local_knowledge_retrieval(tool_meta.get("name"))
        or _trace_tool_label_implies_real_retrieval_summary(tool_meta.get("label"))
        or _trace_tool_label_implies_real_retrieval_summary(tool_meta.get("name"))
    )
    if label_implies_retrieval and (
        (isinstance(output.get("hit_count"), int) and output.get("hit_count") >= 0)
        or (
            isinstance(output.get("documents_total"), int)
            and output.get("documents_total") >= 0
        )
    ):
        return "retrieval"
    label_implies_calc = (
        _trace_tool_label_implies_real_calc_summary(tool_meta.get("label"))
        or _trace_tool_label_implies_real_calc_summary(tool_meta.get("name"))
    )
    if label_implies_calc and output.get("result") is not None:
        return "calculator"
    label_implies_planner = (
        _trace_tool_label_implies_planner_summary(tool_meta.get("label"))
        or _trace_tool_label_implies_planner_summary(tool_meta.get("name"))
    )
    plan = output.get("plan")
    steps = _normalize_trace_tool_result_plan_steps(output.get("steps"))
    if label_implies_planner and (
        (isinstance(plan, str) and plan.strip()) or steps
    ):
        return "planner"
    return None


def _format_trace_tool_semantic_descriptor(tool_meta: dict[str, object]) -> str:
    semantic_kind = str(tool_meta.get("semantic_kind") or tool_meta.get("kind") or "").strip()
    semantic_family = str(tool_meta.get("semantic_family") or "").strip()
    if not semantic_kind:
        return semantic_family or (_resolve_trace_tool_semantic_category(tool_meta) or "")
    if not semantic_family or semantic_family == semantic_kind:
        return semantic_kind
    return f"{semantic_kind} · {semantic_family}"


def _sanitize_trace_http_json_display_label(
    tool_meta: dict[str, object],
    label: str,
) -> str:
    if not label:
        return label
    label_tool_meta = dict(tool_meta)
    label_tool_meta["label"] = label
    if not (
        _trace_tool_meta_implies_provider_or_hosted_tool(label_tool_meta)
        and _trace_http_json_export_content_needs_sanitization(label)
    ):
        return label
    return _redact_trace_http_json_export_content_fallback(label)


def _resolve_trace_tool_display_label(tool_meta: dict[str, object]) -> str:
    tool_name = str(tool_meta.get("name") or "").strip()
    tool_label = str(tool_meta.get("label") or "").strip()
    if not tool_name:
        return _sanitize_trace_http_json_display_label(tool_meta, tool_label)
    canonical_label = get_tool_display_name(tool_name)
    if not tool_label:
        return canonical_label
    if normalize_tool_registry_name(tool_label) == normalize_tool_registry_name(
        tool_name
    ):
        return canonical_label
    return _sanitize_trace_http_json_display_label(tool_meta, tool_label)


def get_trace_step_display_title(step: TraceStep) -> str:
    meta = getattr(step, "meta", None)
    tool_meta = getattr(meta, "tool", None) if meta is not None else None
    if isinstance(tool_meta, dict):
        tool_label = _resolve_trace_tool_display_label(tool_meta)
        semantic_descriptor = _format_trace_tool_semantic_descriptor(tool_meta)
        if tool_label:
            return (
                f"{tool_label} [{semantic_descriptor}]"
                if semantic_descriptor
                else tool_label
            )
    rag_meta = getattr(meta, "rag", None) if meta is not None else None
    if isinstance(rag_meta, dict):
        return "Knowledge Retrieval Snippets"
    label = getattr(meta, "label", None) if meta is not None else None
    if isinstance(label, str) and label.strip():
        return label.strip()
    step_type = getattr(meta, "step_type", None) if meta is not None else None
    if isinstance(step_type, str) and step_type.strip():
        return step_type.strip().replace("_", " ")
    raw_type = getattr(step, "type", None)
    if isinstance(raw_type, str) and raw_type.strip():
        return raw_type.strip().replace("_", " ")
    return "step"


def get_trace_step_display_content(step: TraceStep) -> str:
    content = str(getattr(step, "content", "") or "")
    meta = getattr(step, "meta", None)
    tool_registry_meta = getattr(meta, "tool_registry", None) if meta is not None else None
    tool_meta = getattr(meta, "tool", None) if meta is not None else None
    tool_registry_lines: list[str] = []
    if isinstance(tool_registry_meta, dict):
        content = _redact_tool_registry_diagnostic_value(content)
        raw_entries = tool_registry_meta.get("entries", ())
        if isinstance(raw_entries, (list, tuple)):
            for entry in raw_entries:
                if not isinstance(entry, dict):
                    continue
                kind = str(entry.get("kind", "")).strip().lower()
                target = str(entry.get("target", "")).strip().lower().replace("_", " ")
                label = f"{kind} {target}".strip()
                raw_values = entry.get("values", ())
                values: list[str] = []
                if isinstance(raw_values, (list, tuple)):
                    for value in raw_values:
                        safe_value = _redact_tool_registry_diagnostic_value(value)
                        if safe_value:
                            values.append(safe_value)
                if values:
                    tool_registry_lines.append(f"{label}: {', '.join(values)}")
                    continue
                count = int(entry.get("count", 0) or 0)
                if label:
                    tool_registry_lines.append(f"{label}: {count}")
    if not isinstance(tool_meta, dict):
        label = getattr(meta, "label", None) if meta is not None else None
        if (
            _trace_label_implies_http_json_execution(label)
            or _trace_label_implies_http_json_execution(content)
        ) and _trace_http_json_export_content_needs_sanitization(content):
            content = _redact_trace_http_json_export_content_fallback(content)
        if not tool_registry_lines:
            return content
        base_lines = [content] if content else []
        diagnostics_lines = [
            line for line in tool_registry_lines if line not in base_lines
        ]
        return "\n".join([*base_lines, *diagnostics_lines])
    normalized_tool_meta = _normalize_trace_json_compatible_value(tool_meta)
    if isinstance(normalized_tool_meta, dict):
        tool_meta = normalized_tool_meta
    if (
        _trace_tool_meta_implies_provider_or_hosted_tool(tool_meta)
        and _trace_http_json_export_content_needs_sanitization(content)
    ):
        content = _build_trace_http_json_export_content(
            tool_meta,
            fallback_content=content,
        )
    result_summary = _coerce_trace_string_like_value(tool_meta.get("result_summary"))
    normalized_result_summary = (
        result_summary.strip()
        if isinstance(result_summary, str) and result_summary.strip()
        else ""
    )
    if not normalized_result_summary:
        normalized_result_summary = _infer_trace_tool_result_summary(tool_meta)
    elif _trace_tool_meta_implies_provider_or_hosted_tool(tool_meta):
        normalized_result_summary = _sanitize_trace_tool_result_summary_text(
            normalized_result_summary
        )
    primary_content = content
    if normalized_result_summary:
        stripped_content = content.strip()
        if not stripped_content or stripped_content.startswith("Tool done:"):
            primary_content = normalized_result_summary
        elif normalized_result_summary not in stripped_content:
            primary_content = "\n".join(
                part for part in (content, normalized_result_summary) if part
            )
    preview_text = _stringify_trace_tool_output_preview(
        _resolve_trace_tool_output_preview(tool_meta)
    )
    safe_output_text = _stringify_trace_safe_tool_output(tool_meta)
    preview_line = (
        f"Preview: {preview_text}"
        if preview_text and preview_text not in primary_content
        else ""
    )
    output_line = (
        f"Output: {safe_output_text}"
        if safe_output_text and safe_output_text != preview_text
        else ""
    )
    base_lines = [
        part for part in (primary_content, preview_line, output_line) if part
    ]
    diagnostics_lines = [
        line
        for line in tool_registry_lines
        if not any(line in existing for existing in base_lines)
    ]
    if not base_lines:
        if diagnostics_lines:
            return "\n".join(diagnostics_lines)
        return primary_content or preview_text or safe_output_text
    return "\n".join([*base_lines, *diagnostics_lines])


_TASK_FAILURE_SOURCE_VALUES = {
    "error_event",
    "tool_error",
    "trace_content",
    "legacy_trace",
}


def _truncate_task_failure_hint(value: str) -> str:
    normalized = " ".join(value.strip().split())
    return f"{normalized[:96]}..." if len(normalized) > 96 else normalized


def _normalize_task_failure_hint(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    safe_value = _redact_trace_http_json_export_content_fallback(value)
    return _truncate_task_failure_hint(safe_value)


def _normalize_task_failure_source(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized if normalized in _TASK_FAILURE_SOURCE_VALUES else None


def _trace_step_meta_payload(step: TraceStep) -> dict[str, object]:
    meta = getattr(step, "meta", None)
    if meta is None:
        return {}
    if hasattr(meta, "model_dump"):
        payload = meta.model_dump(exclude_none=True)
        return payload if isinstance(payload, dict) else {}
    if isinstance(meta, dict):
        return dict(meta)
    return {}


def _resolve_trace_step_failure_insight(
    step: TraceStep,
) -> dict[str, str] | None:
    meta = _trace_step_meta_payload(step)
    error_event = meta.get("error_event")
    if isinstance(error_event, dict):
        for key in ("message", "detail", "code"):
            hint = _normalize_task_failure_hint(error_event.get(key))
            if hint:
                return {"failure_hint": hint, "failure_source": "error_event"}

    tool_meta = meta.get("tool")
    if isinstance(tool_meta, dict):
        hint = _normalize_task_failure_hint(tool_meta.get("error"))
        if hint:
            return {"failure_hint": hint, "failure_source": "tool_error"}
        if str(tool_meta.get("status") or "").strip().lower() == "error":
            content_hint = _normalize_task_failure_hint(
                get_trace_step_display_content(step)
            )
            if content_hint:
                return {
                    "failure_hint": content_hint,
                    "failure_source": "tool_error",
                }

    content_hint = _normalize_task_failure_hint(get_trace_step_display_content(step))
    if content_hint:
        lower_content = content_hint.lower()
        if any(
            keyword in lower_content
            for keyword in ("error", "failed", "timeout", "cancel")
        ):
            return {"failure_hint": content_hint, "failure_source": "trace_content"}
    return None


def _extract_task_failure_insight_from_trace_json(
    *,
    status: object,
    trace_json: object,
) -> dict[str, str] | None:
    if normalize_task_status(str(status or "")) != "failed":
        return None
    try:
        steps = _load_parsed_trace_steps_from_trace_json(trace_json)
    except Exception:
        steps = []
    if not steps:
        return None
    for step in reversed(steps):
        insight = _resolve_trace_step_failure_insight(step)
        if insight is not None:
            return insight
    for step in reversed(steps):
        hint = _normalize_task_failure_hint(getattr(step, "content", ""))
        if hint:
            return {"failure_hint": hint, "failure_source": "legacy_trace"}
    return None


def get_trace_step_markdown_meta(
    step: TraceStep,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> dict[str, object] | None:
    meta = getattr(step, "meta", None)
    if meta is None:
        return None
    payload = (
        meta.model_dump(exclude_none=True)
        if hasattr(meta, "model_dump")
        else dict(meta)
        if isinstance(meta, dict)
        else None
    )
    if not isinstance(payload, dict):
        return None
    tool_meta = payload.get("tool")
    if isinstance(tool_meta, dict):
        normalized_tool_meta = _normalize_trace_json_compatible_value(tool_meta)
        sanitized_tool_meta = (
            dict(normalized_tool_meta)
            if isinstance(normalized_tool_meta, dict)
            else dict(tool_meta)
        )
        raw_label_value = sanitized_tool_meta.get("label")
        if isinstance(raw_label_value, str) and raw_label_value.strip():
            sanitized_tool_meta["label"] = _sanitize_trace_http_json_display_label(
                sanitized_tool_meta,
                raw_label_value.strip(),
            )
        raw_input_value = sanitized_tool_meta.get("input")
        if isinstance(raw_input_value, dict):
            sanitized_tool_meta["input"] = _normalize_trace_http_json_tool_input(
                sanitized_tool_meta,
                raw_input_value,
            )
        raw_preview_value = sanitized_tool_meta.get("output_preview")
        projected_preview_value = _resolve_trace_tool_output_preview(sanitized_tool_meta)
        if projected_preview_value is not None:
            sanitized_tool_meta["output_preview"] = projected_preview_value
        safe_output_value = _resolve_trace_safe_tool_output(sanitized_tool_meta)
        if raw_preview_value is not None and safe_output_value is None:
            preview_mapping = _coerce_trace_tool_output_preview_mapping(raw_preview_value)
            preview_keys = _normalize_trace_tool_output_key_list(
                sanitized_tool_meta.get("effective_result_preview_keys")
            )
            if (
                preview_keys
                and _trace_tool_meta_uses_http_json_execution(sanitized_tool_meta)
                and projected_preview_value is not None
            ):
                sanitized_tool_meta["output"] = projected_preview_value
            elif isinstance(preview_mapping, dict):
                sanitized_tool_meta["output"] = _normalize_trace_http_json_tool_output(
                    sanitized_tool_meta,
                    preview_mapping,
                )
            else:
                sanitized_tool_meta["output"] = (
                    _redact_http_json_raw_fallback_value(raw_preview_value)
                    if _trace_tool_meta_implies_provider_or_hosted_tool(
                        sanitized_tool_meta
                    )
                    else raw_preview_value
                )
        elif safe_output_value is not None:
            sanitized_tool_meta["output"] = safe_output_value
        raw_result_summary = _coerce_trace_string_like_value(
            sanitized_tool_meta.get("result_summary")
        )
        if isinstance(raw_result_summary, str) and raw_result_summary.strip():
            if _trace_tool_meta_implies_provider_or_hosted_tool(sanitized_tool_meta):
                sanitized_tool_meta["result_summary"] = (
                    _sanitize_trace_tool_result_summary_text(raw_result_summary)
                )
            else:
                sanitized_tool_meta["result_summary"] = raw_result_summary
        else:
            inferred_result_summary = _infer_trace_tool_result_summary(
                sanitized_tool_meta
            )
            if inferred_result_summary:
                sanitized_tool_meta["result_summary"] = (
                    _sanitize_trace_tool_result_summary_text(inferred_result_summary)
                    if _trace_tool_meta_implies_provider_or_hosted_tool(
                        sanitized_tool_meta
                    )
                    else inferred_result_summary
                )
        payload["tool"] = sanitized_tool_meta
    rag_meta = payload.get("rag")
    normalized_rag_meta = _normalize_trace_json_compatible_value(rag_meta)
    if isinstance(normalized_rag_meta, dict):
        sanitized_rag_meta = dict(normalized_rag_meta)
        raw_chunks = sanitized_rag_meta.get("chunks")
        sanitized_chunks = _sanitize_markdown_meta_rag_chunks(raw_chunks)
        if sanitized_chunks is not raw_chunks:
            sanitized_rag_meta["chunks"] = sanitized_chunks
            payload["rag"] = sanitized_rag_meta
    for diagnostics_key in (
        "tool_registry",
        "diagnostics_runtime",
        "runtime_artifacts",
        "service_execution",
        "preflight_result",
        "execution_result",
        "selected_source_diagnostics",
        "source_diagnostics",
        "audit_detail",
        "audit_event",
    ):
        if diagnostics_key in payload:
            payload[diagnostics_key] = sanitize_tool_registry_diagnostics_artifact_payload(
                payload.get(diagnostics_key)
            )
    payload = _sanitize_trace_provider_source_meta_values_for_export(
        payload,
        provider_source_aliases=provider_source_aliases,
    )
    return payload


_TRACE_HTTP_JSON_EXPORT_CONTENT_SENSITIVE_RE = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|client[_-]?secret|authorization|bearer\s+\S+|token\s*=|secret\s*=)"
)
_RAG_EXPORT_DOCUMENT_VERSION_RE = re.compile(r"^sha256:[a-f0-9]{16,64}$")
_RAG_EXPORT_CONTENT_HASH_RE = re.compile(r"^[a-f0-9]{64}$")


def _trace_http_json_export_content_needs_sanitization(content: str) -> bool:
    if not content:
        return False
    if _TRACE_HTTP_JSON_EXPORT_CONTENT_SENSITIVE_RE.search(content):
        return True
    redacted_content = _redact_tool_registry_diagnostic_value(content)
    if isinstance(redacted_content, str) and redacted_content != content:
        return True
    safe_content = _redact_http_json_sensitive_payload_value(content)
    return isinstance(safe_content, str) and safe_content != content


def _redact_trace_http_json_export_content_fallback(content: str) -> str:
    safe_content = _redact_http_json_sensitive_payload_value(content)
    if not isinstance(safe_content, str):
        safe_content = content
    redacted_content = _redact_tool_registry_diagnostic_value(safe_content)
    safe_text = redacted_content if isinstance(redacted_content, str) else safe_content
    return re.sub(r"(?i)\bbearer\s+\S+", "[redacted]", safe_text)


def _sanitize_rag_export_text(value: object, *, limit: int) -> str | None:
    raw = _coerce_trace_string_like_value(value)
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    if _trace_http_json_export_content_needs_sanitization(text):
        text = _redact_trace_http_json_export_content_fallback(text)
    return text[:limit]


def _sanitize_rag_export_document_version(value: object) -> str | None:
    raw = _sanitize_rag_export_text(value, limit=80)
    if raw and _RAG_EXPORT_DOCUMENT_VERSION_RE.fullmatch(raw):
        return raw
    return None


def _sanitize_rag_export_content_hash(value: object) -> str | None:
    raw = _sanitize_rag_export_text(value, limit=80)
    if raw and _RAG_EXPORT_CONTENT_HASH_RE.fullmatch(raw):
        return raw
    return None


def _sanitize_rag_export_knowledge_base_id(value: object) -> str | None:
    raw = _coerce_trace_string_like_value(value)
    if not isinstance(raw, str) or not raw.strip():
        return None
    return normalize_knowledge_base_id(raw)


def _sanitize_rag_export_knowledge_base_ids(value: object) -> list[str]:
    sanitized_ids: list[str] = []
    seen: set[str] = set()
    for item in _coerce_export_string_list(value):
        safe_id = _sanitize_rag_export_knowledge_base_id(item)
        if safe_id is None or safe_id in seen:
            continue
        seen.add(safe_id)
        sanitized_ids.append(safe_id)
    return sanitized_ids


def _sanitize_trace_tool_result_summary_text(result_summary: str) -> str:
    if not _trace_http_json_export_content_needs_sanitization(result_summary):
        return result_summary
    return _redact_trace_http_json_export_content_fallback(result_summary)


def _sanitize_markdown_meta_rag_chunks(chunks: object) -> object:
    chunks = _normalize_trace_json_compatible_value(chunks)
    if not isinstance(chunks, (list, tuple)):
        return chunks
    sanitized_chunks: list[object] = []
    changed = False
    for chunk in chunks:
        chunk = _normalize_trace_json_compatible_value(chunk)
        if isinstance(chunk, str):
            if _trace_http_json_export_content_needs_sanitization(chunk):
                sanitized_chunks.append(
                    _redact_trace_http_json_export_content_fallback(chunk)
                )
                changed = True
            else:
                sanitized_chunks.append(chunk)
            continue
        if isinstance(chunk, dict):
            content = chunk.get("content")
            if (
                isinstance(content, str)
                and _trace_http_json_export_content_needs_sanitization(content)
            ):
                sanitized_chunk = dict(chunk)
                sanitized_chunk["content"] = (
                    _redact_trace_http_json_export_content_fallback(content)
                )
                sanitized_chunks.append(sanitized_chunk)
                changed = True
            else:
                sanitized_chunks.append(chunk)
            continue
        sanitized_chunks.append(chunk)
    return sanitized_chunks if changed else chunks


def _build_trace_http_json_export_content(
    tool_meta: dict[str, object],
    *,
    fallback_content: str,
) -> str:
    label = _resolve_trace_tool_display_label(tool_meta)
    summary = _infer_trace_tool_result_summary(tool_meta)
    preview_text = _stringify_trace_tool_output_preview(
        _resolve_trace_tool_output_preview(tool_meta)
    )
    safe_output_text = _stringify_trace_safe_tool_output(tool_meta)

    lines: list[str] = []
    if summary:
        lines.append(summary)
    elif label and (preview_text or safe_output_text):
        lines.append(f"{label}:")
    if preview_text:
        lines.append(f"Preview: {preview_text}")
    if safe_output_text and safe_output_text != preview_text:
        lines.append(f"Output: {safe_output_text}")
    safe_content = " ".join(lines).strip()
    if safe_content:
        return safe_content
    return _redact_trace_http_json_export_content_fallback(fallback_content)


def _sanitize_trace_step_content_for_export(step: TraceStep) -> str:
    content = str(getattr(step, "content", "") or "")
    meta = getattr(step, "meta", None)
    tool_meta = getattr(meta, "tool", None) if meta is not None else None
    if not isinstance(tool_meta, dict):
        label = getattr(meta, "label", None) if meta is not None else None
        if not (
            _trace_label_implies_http_json_execution(label)
            or _trace_label_implies_http_json_execution(content)
        ):
            return content
        if not _trace_http_json_export_content_needs_sanitization(content):
            return content
        return _redact_trace_http_json_export_content_fallback(content)
    if not _trace_tool_meta_implies_provider_or_hosted_tool(tool_meta):
        return content
    if not _trace_http_json_export_content_needs_sanitization(content):
        return content
    return _build_trace_http_json_export_content(
        tool_meta,
        fallback_content=content,
    )


def _trace_preview_title(step: TraceStep) -> str:
    return get_trace_step_display_title(step)


def _sanitize_trace_step_for_export(
    step: TraceStep,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> TraceStep:
    sanitized_meta = get_trace_step_markdown_meta(
        step,
        provider_source_aliases=provider_source_aliases,
    )
    original_meta = getattr(step, "meta", None)
    original_meta_payload = (
        original_meta.model_dump(exclude_none=True)
        if hasattr(original_meta, "model_dump")
        else dict(original_meta)
        if isinstance(original_meta, dict)
        else None
    )
    payload = step.model_dump(exclude_none=True)
    if sanitized_meta is not None:
        payload["meta"] = sanitized_meta
    sanitized_step = TraceStep.model_validate(payload)
    sanitized_content = _sanitize_trace_step_content_for_export(sanitized_step)
    if sanitized_content != str(getattr(step, "content", "") or ""):
        payload["content"] = sanitized_content
    if (
        sanitized_meta == original_meta_payload
        and payload.get("content") == getattr(step, "content", None)
    ):
        return step
    return TraceStep.model_validate(payload)


def get_task_trace_preview_summary_from_task(
    task: dict,
    *,
    preview_limit: int = 3,
) -> dict[str, object]:
    trace_summary = get_task_trace_export_summary_from_task(task)
    trace_steps = _coerce_export_trace_steps(trace_summary.get("steps"))
    trace_step_count = int(trace_summary.get("step_count", len(trace_steps)) or 0)
    rag_hit_count = int(trace_summary.get("rag_hit_count", 0) or 0)

    preview_steps: list[dict[str, object]] = []
    bounded_limit = max(0, int(preview_limit))
    for step in trace_steps[-bounded_limit:] if bounded_limit else []:
        preview_steps.append(
            {
                "id": str(getattr(step, "id", "")),
                "seq": getattr(step, "seq", None),
                "type": str(getattr(step, "type", "")),
                "title": _trace_preview_title(step),
                "content_excerpt": _normalize_trace_preview_excerpt(
                    get_trace_step_display_content(step),
                    limit=160,
                ),
            }
        )

    return {
        "trace_step_count": trace_step_count,
        "rag_hit_count": rag_hit_count,
        "trace_preview": preview_steps,
    }


def get_trace_rag_export_summary(
    trace_steps: list[TraceStep],
) -> dict[str, object]:
    rag_hit_count = 0
    rag_knowledge_base_ids: list[str] = []
    rag_chunks: list[dict[str, object]] = []
    seen_kb_ids: set[str] = set()

    for step in trace_steps:
        rag_meta = step.meta.rag if step.meta else None
        normalized_rag_meta = _normalize_trace_json_compatible_value(rag_meta)
        if isinstance(normalized_rag_meta, dict):
            rag_meta = normalized_rag_meta
        if not isinstance(rag_meta, dict):
            continue
        raw_chunks = rag_meta.get("chunks")
        if isinstance(raw_chunks, UserList):
            raw_chunks = raw_chunks.data
        raw_chunk_metadata = rag_meta.get("chunk_metadata")
        if isinstance(raw_chunk_metadata, UserList):
            raw_chunk_metadata = raw_chunk_metadata.data
        chunk_metadata_rows = (
            list(raw_chunk_metadata)
            if isinstance(raw_chunk_metadata, (list, tuple))
            else []
        )
        kb_id_text = _sanitize_rag_export_knowledge_base_id(
            rag_meta.get("knowledge_base_id")
        )
        if kb_id_text and kb_id_text not in seen_kb_ids:
            seen_kb_ids.add(kb_id_text)
            rag_knowledge_base_ids.append(kb_id_text)
        if isinstance(raw_chunks, (list, tuple)):
            for index, chunk in enumerate(raw_chunks):
                chunk_text = _coerce_trace_string_like_value(chunk)
                if isinstance(chunk_text, str):
                    chunk_text = chunk_text.strip()
                    if not chunk_text:
                        continue
                    chunk_payload: dict[str, object] = {}
                    if index < len(chunk_metadata_rows):
                        chunk_metadata = _coerce_payload_mapping_or_none(
                            chunk_metadata_rows[index]
                        )
                        if chunk_metadata is not None:
                            chunk_payload.update(chunk_metadata)
                    chunk_payload.update(
                        {
                            "step_id": step.id,
                            "knowledge_base_id": kb_id_text,
                            "content": chunk_text,
                        }
                    )
                    sanitized_rows = _sanitize_export_rag_chunk_rows([chunk_payload])
                    rag_hit_count += 1
                    rag_chunks.append(sanitized_rows[0] if sanitized_rows else chunk_payload)
                    continue
                chunk_row = _coerce_payload_mapping_or_none(chunk)
                if chunk_row is None:
                    continue
                chunk_payload = dict(chunk_row)
                content = _coerce_trace_string_like_value(chunk_payload.get("content"))
                if not isinstance(content, str) or not content.strip():
                    continue
                chunk_payload["content"] = content.strip()
                chunk_payload["step_id"] = step.id
                chunk_payload["knowledge_base_id"] = kb_id_text
                sanitized_rows = _sanitize_export_rag_chunk_rows([chunk_payload])
                if not sanitized_rows:
                    continue
                rag_hit_count += 1
                rag_chunks.append(sanitized_rows[0])

    return {
        "rag_hit_count": rag_hit_count,
        "rag_knowledge_base_ids": rag_knowledge_base_ids,
        "rag_chunks": rag_chunks,
    }


def get_task_trace_export_summary_from_task(
    task: dict,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> dict[str, object]:
    trace_steps = get_task_trace_steps_from_task(task)
    rag_summary = get_trace_rag_export_summary(trace_steps)
    alias_by_source = provider_source_aliases or (
        _build_trace_steps_provider_source_aliases(trace_steps)
    )
    export_steps = [
        _sanitize_trace_step_for_export(
            step,
            provider_source_aliases=alias_by_source,
        )
        for step in trace_steps
    ]
    rag_knowledge_base_ids = _sanitize_rag_export_knowledge_base_ids(
        rag_summary.get("rag_knowledge_base_ids", [])
    )
    rag_chunks = _sanitize_export_rag_chunk_rows(rag_summary.get("rag_chunks"))
    return {
        "steps": export_steps,
        "step_count": len(trace_steps),
        "rag_hit_count": int(rag_summary.get("rag_hit_count", 0) or 0),
        "rag_knowledge_base_ids": rag_knowledge_base_ids,
        "rag_chunks": rag_chunks,
    }


def _get_task_status_summary_from_task(task: dict) -> dict[str, object]:
    task = _coerce_export_payload_block_to_dict(task)
    status = str(task.get("status", ""))
    return {
        "status": status,
        "status_normalized": normalize_task_status(status),
        "status_label": task_status_label(status),
        "status_rank": task_status_rank(status),
    }


def get_task_trace_response_summary_from_task(task: dict) -> dict[str, object]:
    trace_summary = get_task_trace_export_summary_from_task(task)
    return {
        "steps": _coerce_export_trace_steps(trace_summary.get("steps")),
        **_get_task_status_summary_from_task(task),
    }


def get_task_trace_delta_response_summary_from_task(
    task: dict,
    *,
    after_seq: int = 0,
    limit: int = 200,
) -> dict[str, object]:
    parsed_steps, next_cursor, has_more, latest_seq, _latest_step_id = (
        get_task_trace_delta_snapshot_from_task(
            task,
            after_seq=after_seq,
            limit=limit,
        )
    )
    provider_source_aliases = _build_trace_steps_provider_source_aliases(parsed_steps)
    return {
        "steps": [
            _sanitize_trace_step_for_export(
                step,
                provider_source_aliases=provider_source_aliases,
            )
            for step in parsed_steps
        ],
        "next_cursor": next_cursor,
        "has_more": has_more,
        "lag_seq": max(0, latest_seq - next_cursor),
        "dropped": False,
    }


def _sanitize_task_response_trace_json(
    trace_json: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> object:
    trace_json = _coerce_trace_string_like_value(trace_json)
    if not isinstance(trace_json, str) or not trace_json.strip():
        return trace_json
    trace_steps = _load_parsed_trace_steps_from_trace_json(trace_json)
    if not trace_steps:
        if _trace_http_json_export_content_needs_sanitization(trace_json):
            return _redact_trace_http_json_export_content_fallback(trace_json)
        return trace_json
    sanitized_steps = [
        _sanitize_trace_step_for_export(
            step,
            provider_source_aliases=provider_source_aliases,
        )
        for step in trace_steps
    ]
    return json.dumps(
        [step.model_dump(exclude_none=True) for step in sanitized_steps],
        ensure_ascii=False,
    )


def _build_task_response_provider_source_aliases(task: dict[str, object]) -> dict[str, str]:
    source_names: list[str] = []
    _append_governance_provider_source_alias_inputs(
        source_names,
        task.get("governance"),
    )
    for trace_step in _load_trace_steps_from_trace_json(task.get("trace_json")):
        _append_trace_provider_source_alias_inputs(
            source_names,
            trace_step.get("meta"),
        )
    return build_safe_tool_registry_provider_source_alias_map(source_names)


def get_task_response_summary_from_task(
    task: dict,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> dict[str, object]:
    task = _coerce_export_payload_block_to_dict(task)
    usage_json = _coerce_trace_string_like_value(task.get("usage_json"))
    failure_insight = (
        {
            "failure_hint": failure_hint,
            "failure_source": failure_source,
        }
        if (failure_hint := _normalize_task_failure_hint(task.get("failure_hint")))
        and (failure_source := _normalize_task_failure_source(task.get("failure_source")))
        else _extract_task_failure_insight_from_trace_json(
            status=task.get("status"),
            trace_json=task.get("trace_json"),
        )
    )
    provider_source_aliases = (
        provider_source_aliases
        if provider_source_aliases is not None
        else _build_task_response_provider_source_aliases(task)
    )
    return {
        "id": str(task.get("id", "")),
        "session_id": str(task.get("session_id", "")),
        "prompt": str(task.get("prompt", "")),
        **_get_task_status_summary_from_task(task),
        "governance": _normalize_task_governance_payload_for_response(
            task.get("governance"),
            provider_source_aliases=provider_source_aliases,
        ),
        "trace_json": _sanitize_task_response_trace_json(
            task.get("trace_json"),
            provider_source_aliases=provider_source_aliases,
        ),
        "usage_json": usage_json,
        **(failure_insight or {}),
        "created_at": str(task.get("created_at", "")),
        "updated_at": str(task.get("updated_at", "")),
    }


def get_task_cancel_response_summary_from_task(
    task: dict,
    *,
    previous_status: str,
    already_terminal: bool,
) -> dict[str, object]:
    task = _coerce_export_payload_block_to_dict(task)
    return {
        "task_id": str(task.get("id", "")),
        "previous_status": previous_status,
        **_get_task_status_summary_from_task(task),
        "already_terminal": already_terminal,
    }


def get_task_create_response_summary(
    *,
    task_id: str,
    session_id: str,
    status: str,
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "session_id": session_id,
        **_get_task_status_summary_from_task({"status": status}),
    }


def _get_task_trace_export_summary_with_provider_source_aliases(
    task: dict[str, object],
    *,
    provider_source_aliases: dict[str, str],
) -> dict[str, object]:
    try:
        return get_task_trace_export_summary_from_task(
            task,
            provider_source_aliases=provider_source_aliases,
        )
    except TypeError as exc:
        if "provider_source_aliases" not in str(exc):
            raise
        return get_task_trace_export_summary_from_task(task)


def _build_task_export_provider_source_aliases(
    task: dict[str, object],
    trace_summary: dict[str, object],
) -> dict[str, str]:
    source_names: list[str] = []
    _append_governance_provider_source_alias_inputs(
        source_names,
        task.get("governance"),
    )
    _append_governance_provider_source_alias_inputs(
        source_names,
        trace_summary.get("governance"),
    )
    for trace_step in _load_trace_steps_from_trace_json(task.get("trace_json")):
        _append_trace_provider_source_alias_inputs(
            source_names,
            trace_step.get("meta"),
        )
    raw_steps = trace_summary.get("steps")
    if isinstance(raw_steps, UserList):
        raw_steps = raw_steps.data
    if isinstance(raw_steps, (list, tuple)):
        for item in raw_steps:
            row = _coerce_payload_mapping_or_none(item)
            if row is None:
                continue
            _append_trace_provider_source_alias_inputs(source_names, row.get("meta"))
    return build_safe_tool_registry_provider_source_alias_map(source_names)


def get_task_export_summary_from_task(task: dict) -> dict[str, object]:
    task = _coerce_export_payload_block_to_dict(task)
    provider_source_aliases = _build_task_response_provider_source_aliases(task)
    trace_summary = _get_task_trace_export_summary_with_provider_source_aliases(
        task,
        provider_source_aliases=provider_source_aliases,
    )
    provider_source_aliases = _build_task_export_provider_source_aliases(
        task,
        trace_summary,
    )
    trace_steps = _coerce_export_trace_steps(
        trace_summary.get("steps"),
        provider_source_aliases=provider_source_aliases,
    )
    return {
        "task": {
            "id": str(task.get("id", "")),
            "session_id": str(task.get("session_id", "")),
            "prompt": str(task.get("prompt", "")),
            **_get_task_status_summary_from_task(task),
            "created_at": str(task.get("created_at", "")),
            "updated_at": str(task.get("updated_at", "")),
        },
        "usage": get_task_usage_from_task(task),
        "trace": {
            "governance": _normalize_task_governance_payload_for_response(
                task.get("governance"),
                provider_source_aliases=provider_source_aliases,
            ),
            "steps": trace_steps,
            "step_count": int(trace_summary.get("step_count", 0) or 0),
            "rag_hit_count": int(trace_summary.get("rag_hit_count", 0) or 0),
            "rag_knowledge_base_ids": _sanitize_rag_export_knowledge_base_ids(
                trace_summary.get("rag_knowledge_base_ids", [])
            ),
            "rag_chunks": _sanitize_export_rag_chunk_rows(
                trace_summary.get("rag_chunks")
            ),
        },
    }


def get_task_export_payload_summary(
    task: dict,
    message_rows: list[dict[str, object]] | tuple[dict[str, object], ...],
) -> dict[str, object]:
    export_summary = get_task_export_summary_from_task(task)
    export_message_rows = _coerce_export_payload_block_list_to_dicts(message_rows)
    return {
        "task": export_summary.get("task"),
        "usage": export_summary.get("usage"),
        "trace": export_summary.get("trace"),
        "messages": [
            {
                "id": str(row.get("id", "")),
                "role": str(row.get("role", "")),
                "content": _sanitize_export_message_content(row.get("content", "")),
                "created_at": str(row.get("created_at", "")),
            }
            for row in export_message_rows
        ],
    }


def _coerce_export_payload_block_to_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    value = _normalize_trace_json_compatible_value(value)
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        normalized_dumped = _normalize_trace_json_compatible_value(dumped)
        if isinstance(normalized_dumped, dict):
            return normalized_dumped
    return {}


def _coerce_export_payload_block_list_to_dicts(value: object) -> list[dict[str, object]]:
    if isinstance(value, UserList):
        value = value.data
    if not isinstance(value, (list, tuple)):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        row = _coerce_export_payload_block_to_dict(item)
        if row:
            rows.append(row)
    return rows


def _normalize_export_payload_row_values(
    row: dict[str, object],
) -> dict[str, object]:
    normalized_row = _normalize_trace_json_compatible_value(dict(row))
    return normalized_row if isinstance(normalized_row, dict) else dict(row)


def _normalize_export_payload_block_list_to_dicts(
    value: object,
) -> list[dict[str, object]]:
    return [
        _normalize_export_payload_row_values(row)
        for row in _coerce_export_payload_block_list_to_dicts(value)
    ]


def _sanitize_task_rows_trace_summary_rows(value: object) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in _normalize_export_payload_block_list_to_dicts(value):
        if "trace_preview" in row:
            row["trace_preview"] = _sanitize_session_export_trace_preview_rows(
                row.get("trace_preview")
            )
        rows.append(row)
    return rows


def _sanitize_session_export_payload_task_rows(
    value: object,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in _normalize_export_payload_block_list_to_dicts(value):
        task_summary = _coerce_export_payload_block_to_dict(row.get("task"))
        if task_summary:
            row["task"] = _normalize_export_payload_row_values(task_summary)
        trace_summary = _coerce_export_payload_block_to_dict(row.get("trace"))
        if trace_summary:
            trace_summary = _normalize_export_payload_row_values(trace_summary)
            if "preview" in trace_summary:
                trace_summary["preview"] = _sanitize_session_export_trace_preview_rows(
                    trace_summary.get("preview")
                )
            row["trace"] = trace_summary
        rows.append(row)
    return rows


def _coerce_export_string_list(value: object) -> list[str]:
    if isinstance(value, UserList):
        value = value.data
    if not isinstance(value, (list, tuple)):
        return []
    strings: list[str] = []
    for item in value:
        item = _coerce_trace_string_like_value(item)
        if isinstance(item, str):
            strings.append(item)
    return strings


def _coerce_payload_mapping_or_original(value: object) -> object:
    if isinstance(value, dict):
        return dict(value)
    normalized_value = _normalize_trace_json_compatible_value(value)
    if isinstance(normalized_value, dict):
        return normalized_value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        normalized_dumped = _normalize_trace_json_compatible_value(dumped)
        if isinstance(normalized_dumped, dict):
            return normalized_dumped
    return value


def _coerce_payload_mapping_or_none(value: object) -> dict[str, object] | None:
    mapped = _coerce_payload_mapping_or_original(value)
    return mapped if isinstance(mapped, dict) else None


def _build_export_trace_provider_source_aliases(
    trace_summary: dict[str, object],
) -> dict[str, str]:
    source_names: list[str] = []
    _append_governance_provider_source_alias_inputs(
        source_names,
        trace_summary.get("governance"),
    )
    raw_steps = trace_summary.get("steps")
    if isinstance(raw_steps, UserList):
        raw_steps = raw_steps.data
    if isinstance(raw_steps, (list, tuple)):
        for item in raw_steps:
            row = _coerce_payload_mapping_or_none(item)
            if row is None:
                continue
            _append_trace_provider_source_alias_inputs(source_names, row.get("meta"))
    return build_safe_tool_registry_provider_source_alias_map(source_names)


def _coerce_export_trace_steps(
    value: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> list[TraceStep]:
    if isinstance(value, UserList):
        value = value.data
    if not isinstance(value, (list, tuple)):
        return []
    steps: list[TraceStep] = []
    for item in value:
        if isinstance(item, TraceStep):
            steps.append(
                _sanitize_trace_step_for_export(
                    item,
                    provider_source_aliases=provider_source_aliases,
                )
            )
            continue
        row = _coerce_export_payload_block_to_dict(item)
        if row:
            normalized_row = _normalize_trace_json_compatible_value(row)
            if isinstance(normalized_row, dict):
                row = normalized_row
            steps.append(
                _sanitize_trace_step_for_export(
                    TraceStep.model_validate(row),
                    provider_source_aliases=provider_source_aliases,
                )
            )
    return steps


def _sanitize_export_rag_chunk_rows(value: object) -> list[dict[str, object]]:
    chunks = _coerce_export_payload_block_list_to_dicts(value)
    sanitized_chunks: list[dict[str, object]] = []
    for chunk in chunks:
        sanitized_chunk = _normalize_trace_json_compatible_value(dict(chunk))
        if not isinstance(sanitized_chunk, dict):
            continue
        content = _coerce_trace_string_like_value(sanitized_chunk.get("content"))
        if (
            isinstance(content, str)
            and _trace_http_json_export_content_needs_sanitization(content)
        ):
            sanitized_chunk["content"] = _redact_trace_http_json_export_content_fallback(
                content
            )
        elif isinstance(content, str):
            sanitized_chunk["content"] = content
        knowledge_base_id = _sanitize_rag_export_knowledge_base_id(
            sanitized_chunk.get("knowledge_base_id")
        )
        if knowledge_base_id is not None:
            sanitized_chunk["knowledge_base_id"] = knowledge_base_id
        else:
            sanitized_chunk.pop("knowledge_base_id", None)
        source = _sanitize_rag_export_text(sanitized_chunk.get("source"), limit=240)
        if source is not None:
            sanitized_chunk["source"] = source
        document_id = _sanitize_rag_export_text(
            sanitized_chunk.get("document_id"),
            limit=128,
        )
        if document_id is not None:
            sanitized_chunk["document_id"] = document_id
        document_version = _sanitize_rag_export_document_version(
            sanitized_chunk.get("document_version")
        )
        content_hash = _sanitize_rag_export_content_hash(
            sanitized_chunk.get("content_hash")
        )
        if document_version is not None:
            sanitized_chunk["document_version"] = document_version
        else:
            sanitized_chunk.pop("document_version", None)
        if content_hash is not None:
            sanitized_chunk["content_hash"] = content_hash
        else:
            sanitized_chunk.pop("content_hash", None)
        sanitized_chunks.append(sanitized_chunk)
    return sanitized_chunks


def _sanitize_export_message_content(value: object) -> str:
    content = str(value)
    if _trace_http_json_export_content_needs_sanitization(content):
        return _redact_trace_http_json_export_content_fallback(content)
    return content


def _sanitize_export_message_rows(value: object) -> list[object]:
    if isinstance(value, UserList):
        value = value.data
    if not isinstance(value, (list, tuple)):
        return []
    sanitized_messages: list[object] = []
    for item in value:
        row = _coerce_payload_mapping_or_none(item)
        if row is None:
            sanitized_messages.append(item)
            continue
        sanitized_row = _normalize_trace_json_compatible_value(dict(row))
        if not isinstance(sanitized_row, dict):
            sanitized_messages.append(item)
            continue
        if "content" in sanitized_row:
            sanitized_row["content"] = _sanitize_export_message_content(
                sanitized_row.get("content", "")
            )
        sanitized_messages.append(sanitized_row)
    return sanitized_messages


def get_task_export_response_summary(
    task: dict,
    message_rows: list[dict[str, object]] | tuple[dict[str, object], ...],
) -> dict[str, object]:
    payload_summary = _coerce_export_payload_block_to_dict(
        get_task_export_payload_summary(task, message_rows)
    )
    trace_summary = _coerce_export_payload_block_to_dict(payload_summary.get("trace"))
    provider_source_aliases = _build_export_trace_provider_source_aliases(
        trace_summary
    )
    trace_steps = _coerce_export_trace_steps(
        trace_summary.get("steps"),
        provider_source_aliases=provider_source_aliases,
    )
    return {
        "task": payload_summary.get("task"),
        "usage": payload_summary.get("usage"),
        "trace": {
            "governance": _normalize_task_governance_payload_for_response(
                trace_summary.get("governance"),
                provider_source_aliases=provider_source_aliases,
            ),
            "step_count": int(trace_summary.get("step_count", len(trace_steps)) or 0),
            "rag_hit_count": int(trace_summary.get("rag_hit_count", 0) or 0),
            "rag_knowledge_base_ids": _coerce_export_string_list(
                trace_summary.get("rag_knowledge_base_ids", [])
            ),
            "rag_chunks": _sanitize_export_rag_chunk_rows(
                trace_summary.get("rag_chunks")
            ),
            "steps": trace_steps,
        },
        "messages": _sanitize_export_message_rows(payload_summary.get("messages", [])),
    }


def get_task_trace_delta_snapshot_from_task(
    task: dict,
    *,
    after_seq: int = 0,
    limit: int = 200,
) -> tuple[list[TraceStep], int, bool, int, str | None]:
    task = _coerce_export_payload_block_to_dict(task)
    bounded_limit = max(1, int(limit))
    raw_trace_steps = get_task_trace_steps_from_task(task)
    provider_source_aliases = _build_trace_steps_provider_source_aliases(
        raw_trace_steps
    )
    trace_steps = [
        _sanitize_trace_step_for_export(
            step,
            provider_source_aliases=provider_source_aliases,
        )
        for step in raw_trace_steps
    ]
    latest_seq = max((int(step.seq or 0) for step in trace_steps), default=0)
    latest_step_id = trace_steps[-1].id if trace_steps else None
    all_delta_steps = [step for step in trace_steps if int(step.seq or 0) > after_seq]
    delta_steps = all_delta_steps[:bounded_limit]
    next_cursor = after_seq if not delta_steps else int(delta_steps[-1].seq or 0)
    status = str(task.get("status", ""))
    still_running = status in ("queued", "pending", "running")
    has_more = len(all_delta_steps) > len(delta_steps) or still_running
    return delta_steps, next_cursor, has_more, latest_seq, latest_step_id

_CHAT_PERSISTENCE_TRACE_EXPORT_EXPORTS = (
    '_normalize_trace_preview_excerpt',
    '_coerce_trace_string_like_value',
    '_normalize_trace_json_compatible_value',
    '_stringify_trace_tool_output_preview',
    '_parse_trace_tool_json_mapping_string',
    '_coerce_trace_tool_output_preview_mapping',
    '_coerce_trace_tool_output_mapping',
    '_trace_tool_meta_uses_http_json_execution',
    '_trace_tool_meta_implies_provider_or_hosted_tool',
    '_trace_label_implies_http_json_execution',
    '_normalize_trace_http_json_tool_output',
    '_normalize_trace_http_json_tool_input',
    '_normalize_trace_tool_output_request_id',
    '_normalize_trace_tool_output_key_list',
    '_resolve_trace_safe_tool_output',
    '_infer_trace_tool_preview_output_keys',
    '_resolve_trace_tool_output_preview',
    '_stringify_trace_safe_tool_output',
    '_resolve_trace_tool_result_summary_input',
    '_normalize_trace_tool_semantic_kind',
    '_normalize_trace_tool_label',
    '_trace_tool_label_implies_local_knowledge_retrieval',
    '_trace_tool_label_implies_real_retrieval_summary',
    '_trace_tool_label_implies_real_calc_summary',
    '_trace_tool_label_implies_planner_summary',
    '_normalize_trace_tool_result_plan_steps',
    '_infer_trace_tool_result_summary',
    '_resolve_trace_tool_semantic_category',
    '_format_trace_tool_semantic_descriptor',
    '_sanitize_trace_http_json_display_label',
    '_resolve_trace_tool_display_label',
    'get_trace_step_display_title',
    'get_trace_step_display_content',
    '_TASK_FAILURE_SOURCE_VALUES',
    '_truncate_task_failure_hint',
    '_normalize_task_failure_hint',
    '_normalize_task_failure_source',
    '_trace_step_meta_payload',
    '_resolve_trace_step_failure_insight',
    '_extract_task_failure_insight_from_trace_json',
    'get_trace_step_markdown_meta',
    '_TRACE_HTTP_JSON_EXPORT_CONTENT_SENSITIVE_RE',
    '_RAG_EXPORT_DOCUMENT_VERSION_RE',
    '_RAG_EXPORT_CONTENT_HASH_RE',
    '_trace_http_json_export_content_needs_sanitization',
    '_redact_trace_http_json_export_content_fallback',
    '_sanitize_rag_export_text',
    '_sanitize_rag_export_document_version',
    '_sanitize_rag_export_content_hash',
    '_sanitize_rag_export_knowledge_base_id',
    '_sanitize_rag_export_knowledge_base_ids',
    '_sanitize_trace_tool_result_summary_text',
    '_sanitize_markdown_meta_rag_chunks',
    '_build_trace_http_json_export_content',
    '_sanitize_trace_step_content_for_export',
    '_trace_preview_title',
    '_sanitize_trace_step_for_export',
    'get_task_trace_preview_summary_from_task',
    'get_trace_rag_export_summary',
    'get_task_trace_export_summary_from_task',
    '_get_task_status_summary_from_task',
    'get_task_trace_response_summary_from_task',
    'get_task_trace_delta_response_summary_from_task',
    '_sanitize_task_response_trace_json',
    '_build_task_response_provider_source_aliases',
    'get_task_response_summary_from_task',
    'get_task_cancel_response_summary_from_task',
    'get_task_create_response_summary',
    '_get_task_trace_export_summary_with_provider_source_aliases',
    '_build_task_export_provider_source_aliases',
    'get_task_export_summary_from_task',
    'get_task_export_payload_summary',
    '_coerce_export_payload_block_to_dict',
    '_coerce_export_payload_block_list_to_dicts',
    '_normalize_export_payload_row_values',
    '_normalize_export_payload_block_list_to_dicts',
    '_sanitize_task_rows_trace_summary_rows',
    '_sanitize_session_export_payload_task_rows',
    '_coerce_export_string_list',
    '_coerce_payload_mapping_or_original',
    '_coerce_payload_mapping_or_none',
    '_build_export_trace_provider_source_aliases',
    '_coerce_export_trace_steps',
    '_sanitize_export_rag_chunk_rows',
    '_sanitize_export_message_content',
    '_sanitize_export_message_rows',
    'get_task_export_response_summary',
    'get_task_trace_delta_snapshot_from_task',
)
