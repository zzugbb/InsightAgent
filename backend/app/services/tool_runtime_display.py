from __future__ import annotations


def bind_tool_runtime_display_public_names(namespace: dict[str, object]) -> None:
    globals().update(namespace)


def _find_builtin_registration_by_runner(
    runner: ToolRunner,
) -> ToolRegistration | None:
    for registration in _REGISTERED_TOOLS.values():
        if registration.runner is runner:
            return registration
    return None


def get_tool_display_name_from_registration(
    *,
    name: str,
    registration: ToolRegistration | None,
) -> str:
    if registration is not None:
        label = registration.label.strip()
        if label:
            return _format_safe_tool_display_label(
                label,
                fallback_name=name,
                registration=registration,
            )
    return _humanize_tool_display_name(normalize_tool_registry_name(name))


def _format_safe_tool_display_label(
    raw_label: object,
    *,
    fallback_name: str,
    registration: ToolRegistration | None,
    uses_http_json: bool = False,
) -> str:
    label = str(raw_label).strip() if isinstance(raw_label, str) else ""
    if not label:
        return _humanize_tool_display_name(normalize_tool_registry_name(fallback_name))
    if (
        uses_http_json
        or (
            registration is not None
            and _normalize_tool_execution_kind(registration.execution_kind) == "http_json"
        )
    ):
        safe_label = _redact_tool_registry_diagnostic_value(label)
        if safe_label:
            return safe_label
    return label


_TOOL_DISPLAY_ACRONYMS = {
    "api": "API",
    "csv": "CSV",
    "http": "HTTP",
    "https": "HTTPS",
    "id": "ID",
    "json": "JSON",
    "kb": "KB",
    "llm": "LLM",
    "rag": "RAG",
    "sse": "SSE",
    "sql": "SQL",
    "ui": "UI",
    "url": "URL",
    "ux": "UX",
}


def _humanize_tool_display_name(name: str) -> str:
    normalized_name = str(name).strip()
    if not normalized_name:
        return ""
    tokens = [token for token in re.split(r"[^A-Za-z0-9]+", normalized_name) if token]
    if not tokens:
        return normalized_name
    humanized_tokens: list[str] = []
    for token in tokens:
        lowered = token.lower()
        acronym = _TOOL_DISPLAY_ACRONYMS.get(lowered)
        if acronym is not None:
            humanized_tokens.append(acronym)
            continue
        humanized_tokens.append(token[:1].upper() + token[1:].lower())
    return " ".join(humanized_tokens)


def get_tool_execution_display_name_from_registration(
    *,
    name: str,
    registration: ToolRegistration | None,
) -> str:
    return get_tool_display_name_from_registration(
        name=name,
        registration=registration,
    )


def get_tool_observation_display_name_from_registration(
    *,
    name: str,
    registration: ToolRegistration | None,
) -> str:
    return get_tool_execution_display_name_from_registration(
        name=name,
        registration=registration,
    )


def _normalize_tool_semantic_kind(kind: object) -> str | None:
    if isinstance(kind, UserString):
        kind = str(kind)
    normalized_kind = str(kind).strip() if isinstance(kind, str) else ""
    if not normalized_kind:
        return None
    if (
        normalized_kind == "knowledge_retrieval"
        or normalized_kind.endswith("knowledge_retrieval")
        or normalized_kind.endswith("_retrieval")
    ):
        return "knowledge_retrieval"
    if (
        normalized_kind == "local_calculator"
        or normalized_kind.endswith("_calculator")
        or normalized_kind.endswith("_calc")
    ):
        return "local_calculator"
    if normalized_kind == "task_planner" or normalized_kind.endswith("_planner"):
        return "task_planner"
    return normalized_kind


def _normalize_tool_observation_label(raw_value: object) -> str:
    if not isinstance(raw_value, str):
        return ""
    normalized = raw_value.strip()
    normalized = re.sub(r"\s*\[[^\[\]]+\]\s*$", "", normalized)
    return " ".join(normalized.lower().replace("_", " ").split())


def _label_implies_local_knowledge_retrieval(raw_value: object) -> bool:
    normalized = _normalize_tool_observation_label(raw_value)
    return normalized in {
        "knowledge retrieval",
        "hot retrieval",
        "task retrieve",
        "task retrieve hot",
        "mock retrieve",
    }


def _label_implies_real_retrieval_summary(raw_value: object) -> bool:
    normalized = _normalize_tool_observation_label(raw_value)
    return normalized in {
        "provider search",
        "hosted search",
        "provider retrieval",
    }


def _label_implies_real_calc_summary(raw_value: object) -> bool:
    normalized = _normalize_tool_observation_label(raw_value)
    return normalized in {
        "provider math",
        "hosted math",
        "provider calc",
        "provider calculator",
        "hosted calc",
        "hosted calculator",
    }


def _label_implies_real_planner_summary(raw_value: object) -> bool:
    normalized = _normalize_tool_observation_label(raw_value)
    return normalized in {
        "provider plan",
        "provider planner",
        "hosted plan",
        "hosted planner",
    }


def _get_label_implied_semantic_family(
    *,
    name: str,
    registration: ToolRegistration,
) -> str | None:
    if _label_implies_real_calc_summary(name) or _label_implies_real_calc_summary(
        registration.label
    ):
        return "local_calculator"
    if _label_implies_real_retrieval_summary(
        name
    ) or _label_implies_real_retrieval_summary(registration.label):
        return "knowledge_retrieval"
    if _label_implies_real_planner_summary(name) or _label_implies_real_planner_summary(
        registration.label
    ):
        return "task_planner"
    return None


def _has_known_tool_semantic_family(
    *,
    semantic_kind: str | None,
    semantic_family: str | None,
) -> bool:
    known_families = {"knowledge_retrieval", "local_calculator", "task_planner"}
    return (
        _normalize_tool_semantic_kind(semantic_kind) in known_families
        or _normalize_tool_semantic_kind(semantic_family) in known_families
    )


def _get_label_implied_result_preview_keys(
    *,
    name: str,
    registration: ToolRegistration,
    semantic_kind: str | None,
    semantic_family: str | None,
) -> tuple[str, ...]:
    del semantic_kind, semantic_family
    if (
        _normalize_tool_semantic_kind(registration.kind) is not None
        or _normalize_runtime_semantic_kind(registration.runtime_semantic_kind)
        is not None
    ):
        return ()
    if _label_implies_real_calc_summary(name) or _label_implies_real_calc_summary(
        registration.label
    ):
        return _REGISTERED_TOOLS["calc_eval"].result_preview_keys
    if _label_implies_real_retrieval_summary(
        name
    ) or _label_implies_real_retrieval_summary(registration.label):
        return ("documents_total", *_REGISTERED_TOOLS["task_retrieve"].result_preview_keys)
    if _label_implies_real_planner_summary(name) or _label_implies_real_planner_summary(
        registration.label
    ):
        return _REGISTERED_TOOLS["task_plan"].result_preview_keys
    return ()


def _get_label_implied_result_output_keys(
    *,
    name: str,
    registration: ToolRegistration,
    semantic_kind: str | None,
    semantic_family: str | None,
) -> tuple[str, ...]:
    output_keys = _get_label_implied_result_preview_keys(
        name=name,
        registration=registration,
        semantic_kind=semantic_kind,
        semantic_family=semantic_family,
    )
    if not output_keys:
        return ()
    if _normalize_tool_execution_kind(registration.execution_kind) != "http_json":
        return ()
    if (
        _label_implies_real_calc_summary(name)
        or _label_implies_real_calc_summary(registration.label)
        or _label_implies_real_retrieval_summary(name)
        or _label_implies_real_retrieval_summary(registration.label)
    ) and "request_id" not in output_keys:
        return (*output_keys, "request_id")
    return output_keys


def _get_label_implied_http_json_output_keys_from_preview(
    *,
    name: str,
    registration: ToolRegistration,
) -> tuple[str, ...]:
    if _normalize_tool_execution_kind(registration.execution_kind) != "http_json":
        return ()
    if (
        _normalize_tool_semantic_kind(registration.kind) is not None
        or _normalize_runtime_semantic_kind(registration.runtime_semantic_kind)
        is not None
    ):
        return ()
    output_keys = list(
        _normalize_safe_explicit_result_keys(
            registration.result_preview_keys,
            fallback_keys=(),
        )
    )
    if not output_keys:
        return ()
    if _label_implies_real_retrieval_summary(
        name
    ) or _label_implies_real_retrieval_summary(registration.label):
        for diagnostic_key in ("knowledge_base_id", "request_id"):
            if diagnostic_key not in output_keys:
                output_keys.append(diagnostic_key)
        return tuple(output_keys)
    if _label_implies_real_calc_summary(name) or _label_implies_real_calc_summary(
        registration.label
    ):
        if "request_id" not in output_keys:
            output_keys.append("request_id")
        return tuple(output_keys)
    if _label_implies_real_planner_summary(name) or _label_implies_real_planner_summary(
        registration.label
    ):
        return tuple(output_keys)
    return ()


def get_tool_semantic_kind(
    *,
    name: str,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> str | None:
    normalized_name = normalize_tool_registry_name(name)
    default_registration = resolve_tool_registration(
        normalized_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if registration is not None:
        template_registration = _find_builtin_registration_by_runner(registration.runner)
        if template_registration is not None:
            return _normalize_tool_semantic_kind(template_registration.kind)
        if default_registration is not None:
            default_semantic_kind = _normalize_tool_semantic_kind(
                default_registration.kind
            )
            if default_semantic_kind is not None:
                return default_semantic_kind
        registration_semantic_kind = _normalize_tool_semantic_kind(registration.kind)
        if registration_semantic_kind is not None:
            return registration_semantic_kind
        return _get_label_implied_semantic_family(
            name=normalized_name,
            registration=registration,
        )
    if default_registration is not None:
        default_semantic_kind = _normalize_tool_semantic_kind(default_registration.kind)
        if default_semantic_kind is not None:
            return default_semantic_kind
        return _get_label_implied_semantic_family(
            name=normalized_name,
            registration=default_registration,
        )
    return None


def get_tool_runtime_semantic_kind(
    *,
    name: str,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> str | None:
    resolved_registration = registration or resolve_tool_registration(
        normalize_tool_registry_name(name),
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    explicit_runtime_semantic_kind = (
        _normalize_runtime_semantic_kind(resolved_registration.runtime_semantic_kind)
        if resolved_registration is not None
        else None
    )
    if explicit_runtime_semantic_kind is not None:
        return explicit_runtime_semantic_kind
    return get_tool_semantic_kind(
        name=name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )


def _get_tool_runtime_trace_semantic_kind(
    *,
    name: str,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> str | None:
    normalized_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        normalized_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    explicit_runtime_semantic_kind = (
        _normalize_runtime_semantic_kind(resolved_registration.runtime_semantic_kind)
        if resolved_registration is not None
        else None
    )
    if explicit_runtime_semantic_kind is not None:
        return explicit_runtime_semantic_kind
    semantic_family = get_tool_semantic_kind(
        name=normalized_name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if (
        resolved_registration is not None
        and semantic_family in {"knowledge_retrieval", "local_calculator", "task_planner"}
        and normalized_name not in _REGISTERED_TOOLS
        and not _label_implies_local_knowledge_retrieval(normalized_name)
        and not _label_implies_local_knowledge_retrieval(
            resolved_registration.label if resolved_registration is not None else None
        )
    ):
        return normalized_name
    return semantic_family


def get_tool_effective_result_output_keys(
    *,
    name: str,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> tuple[str, ...]:
    normalized_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        normalized_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if resolved_registration is None:
        return ()
    if resolved_registration.result_output_keys:
        return _normalize_safe_explicit_result_keys(
            resolved_registration.result_output_keys,
            fallback_keys=(),
        )
    if not resolved_registration.supports_result_preview:
        return ()
    explicit_runtime_semantic_kind = _normalize_runtime_semantic_kind(
        resolved_registration.runtime_semantic_kind
    )
    semantic_kind = get_tool_runtime_semantic_kind(
        name=normalized_name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    raw_kind = _normalize_runtime_semantic_kind(resolved_registration.kind)
    semantic_family = get_tool_semantic_kind(
        name=normalized_name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if resolved_registration.result_preview_keys:
        label_implied_output_keys = (
            _get_label_implied_http_json_output_keys_from_preview(
                name=normalized_name,
                registration=resolved_registration,
            )
        )
        if label_implied_output_keys:
            return label_implied_output_keys
    if not resolved_registration.result_preview_keys:
        label_implied_output_keys = _get_label_implied_result_output_keys(
            name=normalized_name,
            registration=resolved_registration,
            semantic_kind=semantic_kind,
            semantic_family=semantic_family,
        )
        if label_implied_output_keys:
            return label_implied_output_keys
    should_infer_output_keys = explicit_runtime_semantic_kind is not None or (
        semantic_kind is not None and raw_kind is not None and raw_kind != semantic_kind
    ) or (
        semantic_kind is not None
        and semantic_family is not None
        and semantic_family != semantic_kind
    )
    if not should_infer_output_keys:
        return ()
    output_keys = get_tool_effective_result_preview_keys(
        name=normalized_name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if resolved_registration.result_preview_keys:
        output_keys = _augment_http_json_local_calculator_output_keys(
            output_keys=output_keys,
            registration=resolved_registration,
            semantic_kind=semantic_kind,
            semantic_family=semantic_family,
        )
        return output_keys
    output_keys = _augment_runtime_override_retrieval_output_keys(
        output_keys=output_keys,
        registration=resolved_registration,
        semantic_kind=semantic_kind,
        semantic_family=semantic_family,
    )
    return _augment_http_json_local_calculator_output_keys(
        output_keys=output_keys,
        registration=resolved_registration,
        semantic_kind=semantic_kind,
        semantic_family=semantic_family,
    )


def get_tool_effective_result_preview_keys(
    *,
    name: str,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> tuple[str, ...]:
    normalized_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        normalized_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if resolved_registration is None or not resolved_registration.supports_result_preview:
        return ()
    if resolved_registration.result_preview_keys:
        return _normalize_safe_explicit_result_keys(
            resolved_registration.result_preview_keys,
            fallback_keys=(),
        )
    semantic_kind = get_tool_runtime_semantic_kind(
        name=normalized_name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    semantic_family = get_tool_semantic_kind(
        name=normalized_name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    label_implied_preview_keys = _get_label_implied_result_preview_keys(
        name=normalized_name,
        registration=resolved_registration,
        semantic_kind=semantic_kind,
        semantic_family=semantic_family,
    )
    if label_implied_preview_keys:
        return label_implied_preview_keys
    preview_keys = _get_default_result_preview_keys_for_semantic_kind(semantic_kind)
    if not preview_keys and semantic_family and semantic_family != semantic_kind:
        preview_keys = _get_default_result_preview_keys_for_semantic_kind(
            semantic_family
        )
    if semantic_family and semantic_family != semantic_kind:
        return _augment_runtime_override_retrieval_preview_keys(
            preview_keys=preview_keys,
            registration=resolved_registration,
            semantic_kind=semantic_kind,
            semantic_family=semantic_family,
        )
    if preview_keys:
        return preview_keys
    return ()


def _augment_runtime_override_retrieval_preview_keys(
    *,
    preview_keys: tuple[str, ...],
    registration: ToolRegistration,
    semantic_kind: str | None,
    semantic_family: str | None,
) -> tuple[str, ...]:
    explicit_runtime_semantic_kind = _normalize_runtime_semantic_kind(
        registration.runtime_semantic_kind
    )
    normalized_semantic_kind = _normalize_tool_semantic_kind(semantic_kind)
    normalized_semantic_family = _normalize_tool_semantic_kind(semantic_family)
    if (
        explicit_runtime_semantic_kind is None
        or normalized_semantic_kind == "knowledge_retrieval"
        or normalized_semantic_family != "knowledge_retrieval"
        or "documents_total" in preview_keys
    ):
        return preview_keys
    return ("documents_total", *preview_keys)


def _augment_runtime_override_retrieval_output_keys(
    *,
    output_keys: tuple[str, ...],
    registration: ToolRegistration,
    semantic_kind: str | None,
    semantic_family: str | None,
) -> tuple[str, ...]:
    explicit_runtime_semantic_kind = _normalize_runtime_semantic_kind(
        registration.runtime_semantic_kind
    )
    normalized_semantic_kind = _normalize_tool_semantic_kind(semantic_kind)
    normalized_semantic_family = _normalize_tool_semantic_kind(semantic_family)
    if (
        explicit_runtime_semantic_kind is None
        or normalized_semantic_kind == "knowledge_retrieval"
        or normalized_semantic_family != "knowledge_retrieval"
        or "request_id" in output_keys
    ):
        return output_keys
    return (*output_keys, "request_id")


def _augment_http_json_local_calculator_output_keys(
    *,
    output_keys: tuple[str, ...],
    registration: ToolRegistration,
    semantic_kind: str | None,
    semantic_family: str | None,
) -> tuple[str, ...]:
    normalized_execution_kind = _normalize_tool_execution_kind(registration.execution_kind)
    normalized_semantic_family = _normalize_tool_semantic_kind(semantic_family)
    if (
        normalized_execution_kind != "http_json"
        or normalized_semantic_family != "local_calculator"
        or "request_id" in output_keys
    ):
        return output_keys
    return (*output_keys, "request_id")


def _get_default_result_preview_keys_for_semantic_kind(
    semantic_kind: str | None,
) -> tuple[str, ...]:
    normalized_semantic_kind = _normalize_tool_semantic_kind(semantic_kind)
    if normalized_semantic_kind == "task_planner":
        return _REGISTERED_TOOLS["task_plan"].result_preview_keys
    if normalized_semantic_kind == "knowledge_retrieval":
        return _REGISTERED_TOOLS["task_retrieve"].result_preview_keys
    if normalized_semantic_kind == "local_calculator":
        return _REGISTERED_TOOLS["calc_eval"].result_preview_keys
    return ()


def build_configured_tool_registry_provider_preflight_tool_details(
    *,
    provider: ToolRegistryProvider,
    diagnostics: dict[str, tuple[str, ...]] | None = None,
) -> tuple[dict[str, object], ...]:
    tool_registry = provider.load_tool_registry()
    execution_diagnostics_by_tool = _group_invalid_tool_execution_messages_by_tool(
        diagnostics.get("invalid_tool_executions") if isinstance(diagnostics, dict) else ()
    )
    details: list[dict[str, object]] = []
    for tool_name in sorted(tool_registry):
        registration = tool_registry[tool_name]
        registration_execution_diagnostics = sanitize_tool_execution_diagnostics(
            registration.execution_diagnostics,
        )
        merged_execution_diagnostics = tuple(
            dict.fromkeys(
                (
                    *registration_execution_diagnostics,
                    *execution_diagnostics_by_tool.get(tool_name, ()),
                )
            )
        )
        semantic_family = get_tool_semantic_kind(
            name=tool_name,
            registration=registration,
        )
        label_implied_semantic_family = _get_label_implied_semantic_family(
            name=tool_name,
            registration=registration,
        )
        if (
            label_implied_semantic_family is not None
            and _normalize_tool_semantic_kind(registration.kind) is None
            and _normalize_runtime_semantic_kind(registration.runtime_semantic_kind)
            is None
        ):
            semantic_kind = _get_tool_runtime_trace_semantic_kind(
                name=tool_name,
                registration=registration,
            )
        else:
            semantic_kind = get_tool_runtime_semantic_kind(
                name=tool_name,
                registration=registration,
            )
        effective_result_preview_keys = get_tool_effective_result_preview_keys(
            name=tool_name,
            registration=registration,
        )
        effective_result_output_keys = get_tool_effective_result_output_keys(
            name=tool_name,
            registration=registration,
        )
        label = _format_safe_tool_display_label(
            registration.label,
            fallback_name=tool_name,
            registration=registration,
        )
        details.append(
            {
                "name": tool_name,
                "label": label,
                "kind": registration.kind,
                "semantic_kind": semantic_kind,
                **(
                    {
                        "execution_kind": normalized_execution_kind,
                    }
                    if (
                        normalized_execution_kind := _normalize_tool_execution_kind(
                            registration.execution_kind
                        )
                    )
                    else {}
                ),
                **(
                    {
                        "execution_summary": execution_summary,
                    }
                    if (
                        execution_summary := sanitize_tool_execution_summary(
                            registration.execution_summary
                        )
                    )
                    is not None
                    else {}
                ),
                **(
                    {"semantic_family": semantic_family}
                    if semantic_family and semantic_family != semantic_kind
                    else {}
                ),
                "retryable_by_default": registration.retryable_by_default,
                "default_timeout_ms": registration.default_timeout_ms,
                "requires_user_context": registration.requires_user_context,
                "supports_result_preview": registration.supports_result_preview,
                "effective_result_preview_keys": effective_result_preview_keys,
                **(
                    {"effective_result_output_keys": effective_result_output_keys}
                    if effective_result_output_keys
                    else {}
                ),
                **(
                    {
                        "execution_diagnostics": merged_execution_diagnostics,
                    }
                    if merged_execution_diagnostics
                    else {}
                ),
            }
        )
    return tuple(details)


def normalize_tool_output_for_registration(
    *,
    output: dict[str, object],
    registration: ToolRegistration,
) -> dict[str, object]:
    is_http_json_scalar_fallback_output = isinstance(
        output,
        _HttpJsonScalarFallbackOutput,
    )
    normalized_output = dict(output)
    normalized_name = normalize_tool_registry_name(registration.name)
    default_registration = _REGISTERED_TOOLS.get(normalized_name)
    explicit_runtime_tool_kind = _normalize_runtime_semantic_kind(
        registration.runtime_semantic_kind
    )
    desired_tool_kind = explicit_runtime_tool_kind or registration.kind
    desired_tool_kind_text = (
        str(desired_tool_kind).strip() if desired_tool_kind is not None else ""
    )
    if _normalize_tool_execution_kind(registration.execution_kind) == "http_json":
        normalized_output = _normalize_http_json_safe_output_shape(normalized_output)
        chunks_requested = (
            "chunks" in _normalize_result_preview_keys(registration.result_preview_keys)
            or "chunks" in _normalize_result_output_keys(registration.result_output_keys)
        )
        if chunks_requested:
            extracted_chunks = _extract_tool_rag_chunks_from_output(normalized_output)
            if extracted_chunks:
                normalized_output["chunks"] = extracted_chunks
        if (
            desired_tool_kind_text
            and "documents_total" not in normalized_output
            and _http_json_output_implies_retrieval_count(
                {"tool_kind": desired_tool_kind_text}
            )
        ):
            nested_count = _extract_http_json_retrieval_count_from_nested_containers(
                normalized_output
            )
            if nested_count is not None:
                normalized_output["documents_total"] = nested_count
            if "documents_total" not in normalized_output:
                root_count = _extract_http_json_retrieval_count_from_container(
                    normalized_output
                )
                if root_count is not None:
                    normalized_output["documents_total"] = root_count
            list_alias_names = (
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
            )
            if is_http_json_scalar_fallback_output:
                list_alias_names = (*list_alias_names, "value")
            for alias_name in list_alias_names:
                if "documents_total" in normalized_output:
                    break
                alias_value = normalized_output.get(alias_name)
                if isinstance(alias_value, (list, tuple)):
                    normalized_output["documents_total"] = len(
                        _flatten_http_json_retrieval_sequence(alias_value)
                    )
                    break
                connection_count = _extract_http_json_retrieval_count_from_container(
                    alias_value
                )
                if connection_count is not None:
                    normalized_output["documents_total"] = connection_count
                    break
            if "documents_total" not in normalized_output:
                for alias_name in _HTTP_JSON_RETRIEVAL_COUNT_ALIAS_FIELDS:
                    alias_count = _normalize_nonnegative_int_count_value(
                        normalized_output.get(alias_name)
                    )
                    if alias_count is not None:
                        normalized_output["documents_total"] = alias_count
                        break
        if (
            desired_tool_kind_text
            and "hit_count" not in normalized_output
            and _http_json_output_implies_retrieval_count(
                {"tool_kind": desired_tool_kind_text}
            )
        ):
            hit_list_alias_names = ("data", "records")
            if (
                "hit_count" in registration.result_preview_keys
                or "hit_count" in registration.result_output_keys
            ):
                hit_list_alias_names = ("documents", "items", *hit_list_alias_names)
            if is_http_json_scalar_fallback_output:
                hit_list_alias_names = (*hit_list_alias_names, "value")
            for alias_name in hit_list_alias_names:
                alias_value = normalized_output.get(alias_name)
                if isinstance(alias_value, (list, tuple)):
                    normalized_output["hit_count"] = len(
                        _flatten_http_json_retrieval_sequence(alias_value)
                    )
                    break
                nested_list = _extract_http_json_retrieval_list_from_container(
                    alias_value
                )
                if nested_list is not None:
                    normalized_output["hit_count"] = len(nested_list)
                    break
            has_top_level_hit_container = any(
                alias_name in normalized_output
                for alias_name in (
                    "documents",
                    "items",
                    "results",
                    "hits",
                    "matches",
                    "data",
                    "records",
                )
            )
            if "hit_count" not in normalized_output and not has_top_level_hit_container:
                nested_list = _extract_http_json_retrieval_list_from_container(
                    normalized_output
                )
                if nested_list is not None:
                    normalized_output["hit_count"] = len(nested_list)
        if (
            desired_tool_kind_text
            and "result" not in normalized_output
            and _http_json_output_implies_calculator_result(
                {"tool_kind": desired_tool_kind_text}
            )
        ):
            calc_result_aliases = (
                "answer",
                "result_value",
                "resultValue",
                "computed_value",
                "computedValue",
            )
            if not is_http_json_scalar_fallback_output:
                calc_result_aliases = ("value", *calc_result_aliases)
            for alias_name in calc_result_aliases:
                if alias_name in normalized_output:
                    normalized_output["result"] = normalized_output[alias_name]
                    break
    if not desired_tool_kind_text:
        return normalized_output
    if (
        default_registration is not None
        and registration.runner is default_registration.runner
        and registration.kind == default_registration.kind
        and desired_tool_kind_text == str(registration.kind).strip()
    ):
        return normalized_output

    current_kind = normalized_output.get("tool_kind")
    current_kind_text = str(current_kind).strip() if current_kind is not None else ""
    if not current_kind_text:
        normalized_output["tool_kind"] = desired_tool_kind_text
        return normalized_output
    if current_kind_text == desired_tool_kind_text:
        return normalized_output

    template_registration = _find_builtin_registration_by_runner(registration.runner)
    if (
        template_registration is not None
        and current_kind_text == template_registration.kind
        and desired_tool_kind_text != template_registration.kind
    ):
        normalized_output["tool_kind"] = desired_tool_kind_text
    elif (
        default_registration is not None
        and current_kind_text == default_registration.kind
        and desired_tool_kind_text != default_registration.kind
    ):
        normalized_output["tool_kind"] = desired_tool_kind_text
    elif (
        current_kind_text == str(registration.kind).strip()
        and desired_tool_kind_text != str(registration.kind).strip()
    ):
        normalized_output["tool_kind"] = desired_tool_kind_text
    return normalized_output


def run_tool(
    *,
    name: str,
    tool_input: dict[str, object],
    prompt: str,
    user_id: str,
    attempt: int,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    maybe_raise_tool_execution_error(name=name, prompt=prompt, attempt=attempt)
    ctx = build_tool_runtime_context(
        name=name,
        prompt=prompt,
        user_id=user_id,
        attempt=attempt,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    normalized_tool_input = _normalize_tool_input_for_registration(
        name=name,
        tool_input=tool_input,
        registration=ctx.registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    output = ctx.registration.runner(
        tool_input=normalized_tool_input,
        prompt=ctx.prompt,
        user_id=ctx.user_id,
    )
    return normalize_tool_output_for_registration(
        output=output,
        registration=ctx.registration,
    )


def execute_tool_spec(
    *,
    tool_spec: dict[str, object],
    prompt: str,
    user_id: str,
    attempt: int,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    invocation = normalize_tool_spec(tool_spec)
    return run_tool(
        name=invocation.name,
        tool_input=invocation.tool_input,
        prompt=prompt,
        user_id=user_id,
        attempt=attempt,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )

_TOOL_RUNTIME_DISPLAY_EXPORTS = (
    '_find_builtin_registration_by_runner',
    'get_tool_display_name_from_registration',
    '_format_safe_tool_display_label',
    '_TOOL_DISPLAY_ACRONYMS',
    '_humanize_tool_display_name',
    'get_tool_execution_display_name_from_registration',
    'get_tool_observation_display_name_from_registration',
    '_normalize_tool_semantic_kind',
    '_normalize_tool_observation_label',
    '_label_implies_local_knowledge_retrieval',
    '_label_implies_real_retrieval_summary',
    '_label_implies_real_calc_summary',
    '_label_implies_real_planner_summary',
    '_get_label_implied_semantic_family',
    '_has_known_tool_semantic_family',
    '_get_label_implied_result_preview_keys',
    '_get_label_implied_result_output_keys',
    '_get_label_implied_http_json_output_keys_from_preview',
    'get_tool_semantic_kind',
    'get_tool_runtime_semantic_kind',
    '_get_tool_runtime_trace_semantic_kind',
    'get_tool_effective_result_output_keys',
    'get_tool_effective_result_preview_keys',
    '_augment_runtime_override_retrieval_preview_keys',
    '_augment_runtime_override_retrieval_output_keys',
    '_augment_http_json_local_calculator_output_keys',
    '_get_default_result_preview_keys_for_semantic_kind',
    'build_configured_tool_registry_provider_preflight_tool_details',
    'normalize_tool_output_for_registration',
    'run_tool',
    'execute_tool_spec',
)
