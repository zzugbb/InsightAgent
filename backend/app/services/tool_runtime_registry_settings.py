from __future__ import annotations


def bind_tool_runtime_registry_settings_public_names(namespace: dict[str, object]) -> None:
    globals().update(namespace)


def _impl_build_tool_registry_extra_tools_from_settings(
    *,
    settings: object | None = None,
) -> dict[str, ToolRegistration]:
    if settings is None:
        settings = get_settings()
    raw_extra_tools = getattr(settings, "tool_registry_extra_tools_json", None)
    extra_tool_specs = _parse_tool_registry_json_object_setting(raw_extra_tools)
    if extra_tool_specs is None:
        return {}

    runtime_template_context = _build_tool_execution_runtime_template_context(
        settings=settings,
    )
    extra_tools: dict[str, ToolRegistration] = {}
    for name, spec in extra_tool_specs.items():
        spec = _coerce_tool_registry_spec_payload(spec)
        if not isinstance(name, str) or not isinstance(spec, Mapping):
            continue
        spec = dict(spec)
        normalized_name = normalize_tool_registry_name(name)
        if normalized_name in _REGISTERED_TOOLS:
            continue
        template_name = spec.get("template")
        if not isinstance(template_name, str):
            continue
        template_registration = _REGISTERED_TOOLS.get(
            normalize_tool_registry_name(template_name)
        )
        if template_registration is None:
            continue
        raw_default_timeout_ms = spec.get(
            "default_timeout_ms", template_registration.default_timeout_ms
        )
        resolved_default_timeout_ms = _coerce_tool_default_timeout_ms(
            raw_default_timeout_ms,
            fallback_timeout_ms=template_registration.default_timeout_ms,
        )
        execution_spec = spec.get("execution")
        resolved_execution_kind = _resolve_tool_execution_kind_from_spec(
            execution_spec
        )
        validation_errors: list[str] = []
        if "default_timeout_ms" in spec:
            timeout_error = _describe_tool_default_timeout_ms_validation_error(
                raw_default_timeout_ms
            )
            if timeout_error:
                validation_errors.append(timeout_error)
        validation_errors.extend(
            _describe_tool_execution_spec_validation_errors(
                execution_spec,
                template_context=runtime_template_context,
            )
        )
        extra_tools[name] = replace(
            template_registration,
            name=name,
            kind=str(spec.get("kind", template_registration.kind)),
            label=str(spec.get("label", template_registration.label)),
            retryable_by_default=bool(
                spec.get("retryable_by_default", template_registration.retryable_by_default)
            ),
            default_timeout_ms=resolved_default_timeout_ms,
            runner=_build_tool_runner_from_execution_spec(
                execution_spec=execution_spec,
                fallback_runner=template_registration.runner,
                default_timeout_ms=resolved_default_timeout_ms,
                template_context=runtime_template_context,
            ),
            requires_user_context=bool(
                spec.get("requires_user_context", template_registration.requires_user_context)
            ),
            supports_result_preview=bool(
                spec.get("supports_result_preview", template_registration.supports_result_preview)
            ),
            result_preview_keys=_normalize_safe_explicit_result_keys(
                spec.get("result_preview_keys"),
                fallback_keys=template_registration.result_preview_keys,
            ),
            result_output_keys=_normalize_safe_explicit_result_keys(
                spec.get("result_output_keys"),
                fallback_keys=template_registration.result_output_keys,
            ),
            runtime_semantic_kind=(
                _normalize_runtime_semantic_kind(spec.get("runtime_semantic_kind"))
                or template_registration.runtime_semantic_kind
            ),
            execution_kind=resolved_execution_kind or template_registration.execution_kind,
            execution_summary=_build_tool_execution_summary_from_spec(
                execution_spec,
                template_context=runtime_template_context,
            )
            or sanitize_tool_execution_summary(template_registration.execution_summary),
            execution_diagnostics=sanitize_tool_execution_diagnostics(
                validation_errors
                if validation_errors
                else template_registration.execution_diagnostics
            ),
        )
    return extra_tools


def _impl__build_registry_overrides_from_specs(
    *,
    override_specs: object,
    base_registry: dict[str, ToolRegistration],
    disabled_tool_names: set[str],
    settings: object | None = None,
) -> tuple[dict[str, ToolRegistration], set[str]]:
    override_specs = _coerce_tool_registry_spec_payload(override_specs)
    if not isinstance(override_specs, dict):
        return {}, disabled_tool_names

    runtime_template_context = _build_tool_execution_runtime_template_context(
        settings=settings,
    )
    overrides: dict[str, ToolRegistration] = {}
    for name, spec in override_specs.items():
        if not isinstance(name, str) or not isinstance(spec, dict):
            continue
        normalized_name = normalize_tool_registry_name(name)
        base_registration = base_registry.get(normalized_name)
        if base_registration is None:
            continue
        if spec.get("enabled") is False:
            disabled_tool_names.add(normalized_name)
        elif spec.get("enabled") is True:
            disabled_tool_names.discard(normalized_name)
        metadata_keys = {
            "kind",
            "label",
            "retryable_by_default",
            "default_timeout_ms",
            "requires_user_context",
            "supports_result_preview",
            "result_preview_keys",
            "result_output_keys",
            "runtime_semantic_kind",
            "execution",
        }
        if not any(key in spec for key in metadata_keys):
            continue
        raw_default_timeout_ms = spec.get(
            "default_timeout_ms", base_registration.default_timeout_ms
        )
        resolved_default_timeout_ms = _coerce_tool_default_timeout_ms(
            raw_default_timeout_ms,
            fallback_timeout_ms=base_registration.default_timeout_ms,
        )
        execution_spec = spec.get("execution")
        resolved_execution_kind = _resolve_tool_execution_kind_from_spec(
            execution_spec
        )
        validation_errors: list[str] = []
        if "default_timeout_ms" in spec:
            timeout_error = _describe_tool_default_timeout_ms_validation_error(
                raw_default_timeout_ms
            )
            if timeout_error:
                validation_errors.append(timeout_error)
        validation_errors.extend(
            _describe_tool_execution_spec_validation_errors(
                execution_spec,
                template_context=runtime_template_context,
            )
        )
        overrides[normalized_name] = replace(
            base_registration,
            kind=str(spec.get("kind", base_registration.kind)),
            label=str(spec.get("label", base_registration.label)),
            retryable_by_default=bool(
                spec.get("retryable_by_default", base_registration.retryable_by_default)
            ),
            default_timeout_ms=resolved_default_timeout_ms,
            runner=_build_tool_runner_from_execution_spec(
                execution_spec=execution_spec,
                fallback_runner=base_registration.runner,
                default_timeout_ms=resolved_default_timeout_ms,
                template_context=runtime_template_context,
            ),
            requires_user_context=bool(
                spec.get("requires_user_context", base_registration.requires_user_context)
            ),
            supports_result_preview=bool(
                spec.get("supports_result_preview", base_registration.supports_result_preview)
            ),
            result_preview_keys=_normalize_safe_explicit_result_keys(
                spec.get("result_preview_keys"),
                fallback_keys=base_registration.result_preview_keys,
            ),
            result_output_keys=_normalize_safe_explicit_result_keys(
                spec.get("result_output_keys"),
                fallback_keys=base_registration.result_output_keys,
            ),
            runtime_semantic_kind=(
                _normalize_runtime_semantic_kind(spec.get("runtime_semantic_kind"))
                or base_registration.runtime_semantic_kind
            ),
            execution_kind=resolved_execution_kind or base_registration.execution_kind,
            execution_summary=_build_tool_execution_summary_from_spec(
                execution_spec,
                template_context=runtime_template_context,
            )
            or sanitize_tool_execution_summary(base_registration.execution_summary),
            execution_diagnostics=sanitize_tool_execution_diagnostics(
                validation_errors
                if validation_errors
                else base_registration.execution_diagnostics
            ),
        )
    return overrides, disabled_tool_names


def _impl_build_tool_registry_settings_config(
    *,
    settings: object | None = None,
    base_provider: ToolRegistryProvider | None = None,
) -> ToolRegistrySettingsConfig:
    if settings is None:
        settings = get_settings()
    profile_config = build_tool_registry_profile_settings_config(
        profile_name=get_tool_registry_profile_name_from_settings(settings=settings),
    )
    extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)
    raw_overrides = getattr(settings, "tool_registry_overrides_json", None)
    known_registrations = (
        dict(base_provider.load_tool_registry())
        if base_provider is not None
        else get_default_tool_registry()
    )
    known_registrations = build_tool_registry(
        base_registry=known_registrations,
        overrides=extra_tools or None,
    )
    override_specs = _parse_tool_registry_json_object_setting(raw_overrides)
    if override_specs is None:
        return ToolRegistrySettingsConfig(
            overrides=dict(extra_tools),
            disabled_tool_names=normalize_tool_registry_names(profile_config.disabled_tool_names),
        )

    overrides: dict[str, ToolRegistration] = dict(extra_tools)
    disabled_tool_names = set(normalize_tool_registry_names(profile_config.disabled_tool_names))
    source_overrides, disabled_tool_names = _build_registry_overrides_from_specs(
        override_specs=override_specs,
        base_registry=known_registrations,
        disabled_tool_names=disabled_tool_names,
        settings=settings,
    )
    overrides.update(source_overrides)
    return ToolRegistrySettingsConfig(
        overrides=overrides,
        disabled_tool_names=tuple(sorted(disabled_tool_names)),
    )


def _impl_build_tool_registry_overrides_from_settings(
    *,
    settings: object | None = None,
) -> dict[str, ToolRegistration]:
    return build_tool_registry_settings_config(settings=settings).overrides


def _impl_get_disabled_tool_names_from_settings(*, settings: object | None = None) -> tuple[str, ...]:
    return build_tool_registry_settings_config(settings=settings).disabled_tool_names


def _impl_get_configured_tool_registry_provider(*, settings: object | None = None) -> ToolRegistryProvider:
    artifacts = get_configured_tool_registry_provider_artifacts(settings=settings)
    return artifacts["provider"]


def _impl_get_configured_tool_registry_provider_artifacts(
    *,
    settings: object | None = None,
) -> dict[str, object]:
    if settings is None:
        settings = get_settings()
    provider_source_name = get_tool_registry_provider_source_name_from_settings(settings=settings)
    source_artifacts = build_tool_registry_provider_sources_from_settings_artifacts(
        settings=settings
    )
    provider_sources = source_artifacts["sources"]
    base_provider = provider_sources.get(provider_source_name)
    settings_execution_diagnostics = build_tool_registry_settings_execution_diagnostics(
        settings=settings,
        base_provider=base_provider,
    )
    settings_config = build_tool_registry_settings_config(
        settings=settings,
        base_provider=base_provider,
    )
    return {
        "provider": build_tool_registry_provider(
            provider=base_provider,
            overrides=settings_config.overrides or None,
            disabled_tool_names=settings_config.disabled_tool_names,
        ),
        "provider_source_name": provider_source_name,
        "provider_sources": provider_sources,
        "selected_source_diagnostics": sanitize_tool_registry_file_diagnostics(
            _merge_tool_registry_file_diagnostics(
                source_artifacts["source_diagnostics"].get(
                    provider_source_name,
                    _empty_tool_registry_file_diagnostics(),
                ),
                settings_execution_diagnostics,
            ),
        ),
        "source_diagnostics": sanitize_tool_registry_source_diagnostics(
            source_artifacts["source_diagnostics"]
        ),
    }


def _impl_build_tool_registry_diagnostics_summary_model(
    *,
    diagnostics: dict[str, tuple[str, ...]],
) -> ToolRegistryDiagnosticsSummaryModel:
    entries: list[dict[str, object]] = []
    skipped_total = 0
    missing_total = 0
    total = 0
    for key in _TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS:
        values = diagnostics.get(key, ())
        if not isinstance(values, (list, tuple)) or not values:
            continue
        alias_by_value = (
            _impl_build_safe_tool_registry_provider_source_alias_map(values)
            if key.endswith("_registry_sources")
            else {}
        )
        deduped_safe_values: list[str] = []
        for raw_value in values:
            raw_value_key = str(raw_value)
            safe_value = alias_by_value.get(
                raw_value_key,
                _impl__sanitize_tool_registry_provider_source_name_for_artifact(
                    raw_value
                ),
            )
            if not safe_value or safe_value in deduped_safe_values:
                continue
            deduped_safe_values.append(safe_value)
        safe_values = tuple(deduped_safe_values)
        if not safe_values:
            continue
        kind, target = key.split("_", 1)
        entry = {
            "kind": kind,
            "target": target,
            "count": len(safe_values),
            "values": safe_values,
        }
        entries.append(entry)
        total += len(safe_values)
        if kind == "skipped":
            skipped_total += len(safe_values)
        elif kind == "missing":
            missing_total += len(safe_values)
    return ToolRegistryDiagnosticsSummaryModel(
        has_diagnostics=bool(entries),
        skipped_total=skipped_total,
        missing_total=missing_total,
        total=total,
        entries=tuple(entries),
    )


def _impl_build_tool_registry_diagnostics_summary(
    *,
    diagnostics: dict[str, tuple[str, ...]],
) -> dict[str, object]:
    return build_tool_registry_diagnostics_summary_model(
        diagnostics=diagnostics,
    ).to_dict()


def _impl__humanize_tool_registry_diagnostics_target(target: object) -> str:
    normalized = str(target).strip().lower() if target is not None else ""
    if not normalized:
        return "diagnostics"
    return normalized.replace("_", " ")


def _impl_build_tool_registry_diagnostics_display_lines(
    *,
    entries: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("kind", "")).strip().lower()
        target = _humanize_tool_registry_diagnostics_target(entry.get("target"))
        label = f"{kind} {target}".strip()
        raw_values = entry.get("values", ())
        values = [
            str(value).strip()
            for value in raw_values
            if str(value).strip()
        ] if isinstance(raw_values, (list, tuple)) else []
        if values:
            lines.append(f"{label}: {', '.join(values)}")
            continue
        count = int(entry.get("count", 0) or 0)
        if label:
            lines.append(f"{label}: {count}")
    return tuple(lines)


def _impl_build_tool_registry_diagnostics_runtime_artifacts_model(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    provider_source_name: str,
    diagnostics: dict[str, tuple[str, ...]],
    provider_source_aliases: dict[str, str] | None = None,
) -> ToolRegistryDiagnosticsRuntimeArtifactsModel:
    summary = build_tool_registry_diagnostics_summary_model(diagnostics=diagnostics)
    if not bool(summary.has_diagnostics):
        return ToolRegistryDiagnosticsRuntimeArtifactsModel(
            summary=summary,
            trace_step=None,
            trace_event=None,
            audit_detail=None,
        )
    safe_provider_source_name = (
        (provider_source_aliases or {}).get(
            str(provider_source_name),
            _impl__sanitize_tool_registry_provider_source_name_for_artifact(
                provider_source_name
            ),
        )
    )

    trace_step = {
        "id": step_id,
        "seq": seq,
        "type": "observation",
        "content": "\n".join(
            (
                "Tool registry diagnostics: "
                f"source={safe_provider_source_name} "
                f"skipped={int(summary.skipped_total)} "
                f"missing={int(summary.missing_total)}",
                *build_tool_registry_diagnostics_display_lines(
                    entries=summary.entries
                ),
            )
        ),
        "meta": {
            "model": model,
            "step_type": "tool_registry_diagnostics",
            "tokens": None,
            "cost_estimate": None,
            "tool_registry": {
                "provider_source": safe_provider_source_name,
                "has_diagnostics": bool(summary.has_diagnostics),
                "skipped_total": int(summary.skipped_total),
                "missing_total": int(summary.missing_total),
                "total": int(summary.total),
                "entries": summary.entries,
            },
        },
    }
    return ToolRegistryDiagnosticsRuntimeArtifactsModel(
        summary=summary,
        trace_step=trace_step,
        trace_event=build_tool_trace_event(
            task_id=task_id,
            step_id=step_id,
            step=trace_step,
        ),
        audit_detail={
            "provider_source": safe_provider_source_name,
            "has_diagnostics": bool(summary.has_diagnostics),
            "skipped_total": int(summary.skipped_total),
            "missing_total": int(summary.missing_total),
            "total": int(summary.total),
            "entries": summary.entries,
        },
    )


def _impl_build_tool_registry_diagnostics_runtime_artifacts(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    provider_source_name: str,
    diagnostics: dict[str, tuple[str, ...]],
    provider_source_aliases: dict[str, str] | None = None,
) -> dict[str, object]:
    return build_tool_registry_diagnostics_runtime_artifacts_model(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        provider_source_name=provider_source_name,
        diagnostics=diagnostics,
        provider_source_aliases=provider_source_aliases,
    ).to_dict()


def _impl_build_tool_registry_diagnostics_audit_event(
    *,
    diagnostics_runtime: dict[str, object],
) -> dict[str, object] | None:
    audit_detail = diagnostics_runtime.get("audit_detail")
    if not isinstance(audit_detail, dict):
        return None
    return {
        "event_type": "tool_registry_diagnostics",
        "code": "tool_registry_diagnostics",
        "message": "Tool registry diagnostics detected during configured provider resolution.",
        "detail": audit_detail,
    }


def _impl_build_tool_registry_diagnostics_audit_service_action(
    *,
    audit_event: dict[str, object],
) -> dict[str, object]:
    return build_tool_registry_diagnostics_audit_service_action_model(
        audit_event=audit_event,
    ).to_dict()


def _impl_build_tool_registry_diagnostics_audit_service_action_model(
    *,
    audit_event: dict[str, object],
) -> ConfiguredToolRegistryProviderRuntimeServiceActionModel:
    return ConfiguredToolRegistryProviderRuntimeServiceActionModel(
        kind="record_audit_event",
        kwargs=audit_event,
    )


def _impl_build_tool_registry_diagnostics_trace_service_action(
    *,
    trace_step: dict[str, object],
    trace_event: dict[str, object],
    persist_force: bool = True,
) -> dict[str, object]:
    return build_tool_registry_diagnostics_trace_service_action_model(
        trace_step=trace_step,
        trace_event=trace_event,
        persist_force=persist_force,
    ).to_dict()


def _impl_build_tool_registry_diagnostics_trace_service_action_model(
    *,
    trace_step: dict[str, object],
    trace_event: dict[str, object],
    persist_force: bool = True,
) -> ConfiguredToolRegistryProviderRuntimeServiceActionModel:
    return ConfiguredToolRegistryProviderRuntimeServiceActionModel(
        kind="internal_trace_write",
        trace_step=trace_step,
        trace_event=trace_event,
        persist_force=bool(persist_force),
    )

_REGISTRY_SETTINGS_IMPL_EXPORTS = (
    '_impl_build_tool_registry_extra_tools_from_settings',
    '_impl__build_registry_overrides_from_specs',
    '_impl_build_tool_registry_settings_config',
    '_impl_build_tool_registry_overrides_from_settings',
    '_impl_get_disabled_tool_names_from_settings',
    '_impl_get_configured_tool_registry_provider',
    '_impl_get_configured_tool_registry_provider_artifacts',
    '_impl_build_tool_registry_diagnostics_summary_model',
    '_impl_build_tool_registry_diagnostics_summary',
    '_impl__humanize_tool_registry_diagnostics_target',
    '_impl_build_tool_registry_diagnostics_display_lines',
    '_impl_build_tool_registry_diagnostics_runtime_artifacts_model',
    '_impl_build_tool_registry_diagnostics_runtime_artifacts',
    '_impl_build_tool_registry_diagnostics_audit_event',
    '_impl_build_tool_registry_diagnostics_audit_service_action',
    '_impl_build_tool_registry_diagnostics_audit_service_action_model',
    '_impl_build_tool_registry_diagnostics_trace_service_action',
    '_impl_build_tool_registry_diagnostics_trace_service_action_model',
)
