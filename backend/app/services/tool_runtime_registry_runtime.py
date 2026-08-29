from __future__ import annotations

from app.services import tool_runtime_registry as _registry


def _bind_registry_namespace(namespace: dict[str, object]) -> None:
    globals().update(
        {
            name: value
            for name, value in namespace.items()
            if not name.startswith("__")
        }
    )


_bind_registry_namespace(vars(_registry))


_RUNTIME_IMPL_EXPORTS: tuple[str, ...] = (
    '_impl_build_configured_tool_registry_provider_runtime_service_actions',
    '_impl_build_configured_tool_registry_provider_runtime_service_actions_model',
    '_impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models',
    '_impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model',
    '_impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts',
    '_impl_build_configured_tool_registry_provider_runtime_service_actions_outputs',
    '_impl_build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model',
    '_impl_build_configured_tool_registry_provider_runtime_service_action_model_from_dict',
    '_impl_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts',
    '_impl_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict',
    '_impl_build_configured_tool_registry_provider_service_execution_provider_source_aliases',
    '_impl_build_configured_tool_registry_provider_service_execution_model_from_dict',
    '_impl_execute_configured_tool_registry_provider_runtime_service_actions',
    '_impl_build_configured_tool_registry_provider_runtime_service_actions_result_model',
    '_impl_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models',
    '_impl_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict',
    '_impl_build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict',
    '_impl_execute_configured_tool_registry_provider_runtime_service_actions_result_model',
    '_impl_execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models',
    '_impl_execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models',
    '_impl_execute_configured_tool_registry_provider_runtime_service_actions_model',
    '_impl_execute_configured_tool_registry_provider_runtime_service_actions_outputs',
    '_impl_build_configured_tool_registry_provider_service_execution_model',
    '_impl_build_configured_tool_registry_provider_service_execution',
    '_impl_build_configured_tool_registry_provider_service_execution_result_model',
    '_impl_build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model',
    '_impl_build_configured_tool_registry_provider_service_execution_result_model_from_models',
    '_impl_build_configured_tool_registry_provider_service_execution_outputs_from_models',
    '_impl_build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model',
    '_impl_execute_configured_tool_registry_provider_service_execution_outputs_from_models',
    '_impl_build_configured_tool_registry_provider_service_execution_outputs',
    '_impl_execute_configured_tool_registry_provider_service_execution',
    '_impl_execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model',
    '_impl_execute_configured_tool_registry_provider_service_execution_outputs',
    '_impl_execute_configured_tool_registry_provider_service_execution_model',
    '_impl_build_configured_tool_registry_provider_preflight_summary_model',
    '_impl_build_configured_tool_registry_provider_preflight_service_execution_model_from_dict',
    '_impl_build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict',
    '_impl__merge_configured_tool_registry_provider_preflight_service_execution_payload',
    '_impl_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict',
    '_impl_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model',
    '_impl_build_configured_tool_registry_provider_preflight_execution_models_from_dict',
    '_impl_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload',
    '_impl_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model',
    '_impl_build_configured_tool_registry_provider_preflight_models_from_service_execution_payload',
    '_impl_build_configured_tool_registry_provider_preflight_models_from_service_execution_model',
    '_impl_build_configured_tool_registry_provider_preflight_models_from_dict',
    '_impl_build_configured_tool_registry_provider_preflight_models_from_models',
    '_impl_build_configured_tool_registry_provider_preflight_summary_model_from_dict',
    '_impl_build_configured_tool_registry_provider_preflight_summary_model_from_result_model',
    '_impl_build_configured_tool_registry_provider_preflight_summary_model_from_models',
    '_impl_build_configured_tool_registry_provider_preflight_summary_model_from_parts',
    '_impl_build_configured_tool_registry_provider_preflight_summary',
    '_impl_build_configured_tool_registry_provider_preflight_outputs_from_resolved_models',
    '_impl_build_configured_tool_registry_provider_preflight_outputs_from_models',
    '_impl_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model',
    '_impl_build_configured_tool_registry_provider_preflight_outputs',
    '_impl_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload',
    '_impl_build_configured_tool_registry_provider_preflight_outputs_from_dict',
    '_impl_build_configured_tool_registry_provider_preflight_models',
    '_impl_build_configured_tool_registry_provider_preflight_dicts',
    '_impl_build_configured_tool_registry_provider_preflight_result_model',
    '_impl_build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model',
    '_impl_build_configured_tool_registry_provider_preflight_result_model_from_models',
    '_impl_build_configured_tool_registry_provider_preflight_result_model_from_dict',
    '_impl_build_configured_tool_registry_provider_preflight_result',
    '_impl_execute_configured_tool_registry_provider_preflight_models_from_service_execution_model',
    '_impl_execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model',
    '_impl_execute_configured_tool_registry_provider_preflight_outputs',
    '_impl_execute_configured_tool_registry_provider_preflight_summary_model',
    '_impl_execute_configured_tool_registry_provider_preflight_summary',
    '_impl_execute_configured_tool_registry_provider_preflight_dicts',
    '_impl_execute_configured_tool_registry_provider_preflight_models',
    '_impl_execute_configured_tool_registry_provider_preflight',
    '_impl_execute_configured_tool_registry_provider_preflight_model',
    '_impl_build_configured_tool_registry_provider_runtime_artifacts_model',
    '_impl_build_configured_tool_registry_provider_runtime_artifacts',
)


def _impl_build_configured_tool_registry_provider_runtime_service_actions(
    *,
    runtime_artifacts: dict[str, object],
) -> list[dict[str, object]]:
    return build_configured_tool_registry_provider_runtime_service_actions_model(
        runtime_artifacts=runtime_artifacts,
    ).to_dict()


def _impl_build_configured_tool_registry_provider_runtime_service_actions_model(
    *,
    runtime_artifacts: dict[str, object],
) -> ConfiguredToolRegistryProviderRuntimeServiceActionsModel:
    provider = runtime_artifacts.get("provider")
    if provider is None:
        provider = StaticToolRegistryProvider({})
    provider_source_name = str(runtime_artifacts.get("provider_source_name", "default"))
    return build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model(
        runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name=provider_source_name,
            runtime_artifacts=runtime_artifacts,
        ),
    )


def _impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models(
    *,
    service_actions: ConfiguredToolRegistryProviderRuntimeServiceActionsModel,
) -> tuple[
    ConfiguredToolRegistryProviderRuntimeServiceActionsModel,
    list[dict[str, object]],
]:
    return service_actions, service_actions.to_dict()


def _impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model(
    *,
    runtime_artifacts: ConfiguredToolRegistryProviderRuntimeArtifactsModel,
) -> tuple[
    ConfiguredToolRegistryProviderRuntimeServiceActionsModel,
    list[dict[str, object]],
]:
    service_actions_model = (
        build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model(
            runtime_artifacts=runtime_artifacts,
        )
    )
    return service_actions_model, service_actions_model.to_dict()


def _impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts(
    *,
    service_actions: list[dict[str, object]],
) -> tuple[
    ConfiguredToolRegistryProviderRuntimeServiceActionsModel,
    list[dict[str, object]],
]:
    service_actions_model = build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
        service_actions=service_actions,
    )
    return service_actions_model, service_actions_model.to_dict()


def _impl_build_configured_tool_registry_provider_runtime_service_actions_outputs(
    *,
    runtime_artifacts: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderRuntimeServiceActionsModel,
    list[dict[str, object]],
]:
    service_actions_model = build_configured_tool_registry_provider_runtime_service_actions_model(
        runtime_artifacts=runtime_artifacts,
    )
    return service_actions_model, service_actions_model.to_dict()


def _impl_build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model(
    *,
    runtime_artifacts: ConfiguredToolRegistryProviderRuntimeArtifactsModel,
) -> ConfiguredToolRegistryProviderRuntimeServiceActionsModel:
    service_actions: list[ConfiguredToolRegistryProviderRuntimeServiceActionModel] = []
    diagnostics_runtime = runtime_artifacts.diagnostics_runtime
    trace_step = diagnostics_runtime.trace_step
    trace_event = diagnostics_runtime.trace_event
    if isinstance(trace_step, dict) and isinstance(trace_event, dict):
        service_actions.append(
            build_tool_registry_diagnostics_trace_service_action_model(
                trace_step=trace_step,
                trace_event=trace_event,
            )
        )
    audit_event = runtime_artifacts.audit_event
    if isinstance(audit_event, dict):
        service_actions.append(
            build_tool_registry_diagnostics_audit_service_action_model(
                audit_event=audit_event,
            )
        )
    return ConfiguredToolRegistryProviderRuntimeServiceActionsModel(
        actions=tuple(service_actions),
    )


def _impl_build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
    service_action: dict[str, object],
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> ConfiguredToolRegistryProviderRuntimeServiceActionModel:
    return ConfiguredToolRegistryProviderRuntimeServiceActionModel(
        kind=str(service_action.get("kind")),
        trace_step=_impl__sanitize_tool_registry_provider_source_fields_for_artifact(
            _sanitize_tool_runtime_trace_artifact_payload(
                service_action.get("trace_step"),
                provider_source_aliases=provider_source_aliases,
            ),
            provider_source_aliases=provider_source_aliases,
        )
        if isinstance(service_action.get("trace_step"), dict)
        else None,
        trace_event=_impl__sanitize_tool_registry_provider_source_fields_for_artifact(
            _sanitize_tool_runtime_trace_artifact_payload(
                service_action.get("trace_event"),
                provider_source_aliases=provider_source_aliases,
            ),
            provider_source_aliases=provider_source_aliases,
        )
        if isinstance(service_action.get("trace_event"), dict)
        else None,
        persist_force=bool(service_action.get("persist_force")),
        kwargs=_impl__sanitize_tool_registry_provider_source_fields_for_artifact(
            _sanitize_tool_runtime_trace_artifact_payload(
                service_action.get("kwargs"),
                provider_source_aliases=provider_source_aliases,
            ),
            provider_source_aliases=provider_source_aliases,
        )
        if isinstance(service_action.get("kwargs"), dict)
        else None,
    )


def _impl_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
    *,
    service_actions: list[dict[str, object]],
    provider_source_aliases: dict[str, str] | None = None,
) -> ConfiguredToolRegistryProviderRuntimeServiceActionsModel:
    if provider_source_aliases is None:
        provider_source_aliases = _impl_build_safe_tool_registry_provider_source_alias_map(
            list(
                _call_runtime(
                    "_iter_tool_runtime_provider_source_artifact_values",
                    [action for action in service_actions if isinstance(action, dict)],
                )
            )
        )
    return ConfiguredToolRegistryProviderRuntimeServiceActionsModel(
        actions=tuple(
            build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
                service_action,
                provider_source_aliases=provider_source_aliases,
            )
            for service_action in service_actions
            if isinstance(service_action, dict)
        )
    )


def _impl_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
    *,
    provider: ToolRegistryProvider,
    provider_source_name: str,
    runtime_artifacts: dict[str, object],
    provider_source_aliases: dict[str, str] | None = None,
) -> ConfiguredToolRegistryProviderRuntimeArtifactsModel:
    diagnostics_runtime_payload = runtime_artifacts.get(
        "diagnostics_runtime",
        {
            "summary": {
                "has_diagnostics": False,
                "skipped_total": 0,
                "missing_total": 0,
                "total": 0,
                "entries": (),
            },
            "trace_step": None,
            "trace_event": None,
            "audit_detail": None,
        },
    )
    summary_payload = diagnostics_runtime_payload.get("summary", {})
    if not isinstance(summary_payload, dict):
        summary_payload = {}
    if provider_source_aliases is None:
        provider_source_aliases = dict(
            _call_runtime(
                "_build_tool_runtime_artifact_provider_source_aliases",
                provider_source_name=runtime_artifacts.get(
                    "provider_source_name", provider_source_name
                ),
                provider_sources=runtime_artifacts.get("provider_sources", {}),
                selected_source_diagnostics=runtime_artifacts.get(
                    "selected_source_diagnostics", {}
                ),
                source_diagnostics=runtime_artifacts.get("source_diagnostics", {}),
                diagnostics_runtime=diagnostics_runtime_payload,
                audit_event=runtime_artifacts.get("audit_event"),
            )
        )
    safe_provider_source_name = (
        (provider_source_aliases or {}).get(
            str(runtime_artifacts.get("provider_source_name", provider_source_name)),
            _impl__sanitize_tool_registry_provider_source_name_for_artifact(
                runtime_artifacts.get("provider_source_name", provider_source_name)
            ),
        )
    )
    return ConfiguredToolRegistryProviderRuntimeArtifactsModel(
        provider=provider,
        provider_source_name=safe_provider_source_name,
        provider_sources=_impl__sanitize_tool_registry_provider_sources_for_artifact(
            runtime_artifacts.get("provider_sources", {}),
            provider_source_aliases=provider_source_aliases,
        ),
        selected_source_diagnostics=_impl__sanitize_tool_registry_file_diagnostics_with_provider_source_aliases(
            runtime_artifacts.get("selected_source_diagnostics", {}),
            provider_source_aliases=provider_source_aliases,
        ),
        source_diagnostics=_impl__sanitize_tool_registry_source_diagnostics_with_provider_source_aliases(
            runtime_artifacts.get("source_diagnostics", {}),
            provider_source_aliases=provider_source_aliases,
        ),
        diagnostics_runtime=ToolRegistryDiagnosticsRuntimeArtifactsModel(
            summary=_impl__build_tool_registry_diagnostics_summary_model_from_payload(
                summary_payload
            ),
            trace_step=_impl__sanitize_tool_registry_provider_source_fields_for_artifact(
                _sanitize_tool_runtime_trace_artifact_payload(
                    diagnostics_runtime_payload.get("trace_step"),
                    provider_source_aliases=provider_source_aliases,
                ),
                provider_source_aliases=provider_source_aliases,
            )
            if isinstance(diagnostics_runtime_payload.get("trace_step"), dict)
            else None,
            trace_event=_impl__sanitize_tool_registry_provider_source_fields_for_artifact(
                _sanitize_tool_runtime_trace_artifact_payload(
                    diagnostics_runtime_payload.get("trace_event"),
                    provider_source_aliases=provider_source_aliases,
                ),
                provider_source_aliases=provider_source_aliases,
            )
            if isinstance(diagnostics_runtime_payload.get("trace_event"), dict)
            else None,
            audit_detail=_impl__sanitize_tool_registry_provider_source_fields_for_artifact(
                _sanitize_tool_runtime_trace_artifact_payload(
                    diagnostics_runtime_payload.get("audit_detail"),
                    provider_source_aliases=provider_source_aliases,
                ),
                provider_source_aliases=provider_source_aliases,
            )
            if isinstance(diagnostics_runtime_payload.get("audit_detail"), dict)
            else None,
        ),
        audit_event=_impl__sanitize_tool_registry_provider_source_fields_for_artifact(
            _sanitize_tool_runtime_trace_artifact_payload(
                runtime_artifacts.get("audit_event"),
                provider_source_aliases=provider_source_aliases,
            ),
            provider_source_aliases=provider_source_aliases,
        )
        if isinstance(runtime_artifacts.get("audit_event"), dict)
        else None,
    )


def _impl_build_configured_tool_registry_provider_service_execution_provider_source_aliases(
    *,
    service_execution: dict[str, object],
) -> dict[str, str]:
    runtime_artifacts_payload = service_execution.get("runtime_artifacts", {})
    if not isinstance(runtime_artifacts_payload, dict):
        runtime_artifacts_payload = {}
    service_actions_payload = service_execution.get("service_actions", [])
    if not isinstance(service_actions_payload, (list, tuple)):
        service_actions_payload = []
    return _impl_build_safe_tool_registry_provider_source_alias_map(
        list(
            _call_runtime(
                "_build_tool_runtime_artifact_provider_source_aliases",
                provider_source_name=service_execution.get(
                    "provider_source_name", "default"
                ),
                provider_sources=runtime_artifacts_payload.get("provider_sources", {}),
                selected_source_diagnostics=runtime_artifacts_payload.get(
                    "selected_source_diagnostics", {}
                ),
                source_diagnostics=runtime_artifacts_payload.get(
                    "source_diagnostics", {}
                ),
                diagnostics_runtime=runtime_artifacts_payload.get(
                    "diagnostics_runtime"
                ),
                audit_event=runtime_artifacts_payload.get("audit_event"),
                service_actions=service_actions_payload,
            ).keys()
        )
    )


def _impl_build_configured_tool_registry_provider_service_execution_model_from_dict(
    *,
    service_execution: dict[str, object],
) -> ConfiguredToolRegistryProviderServiceExecutionModel:
    provider = service_execution["provider"]
    provider_source_aliases = (
        _impl_build_configured_tool_registry_provider_service_execution_provider_source_aliases(
            service_execution=service_execution,
        )
    )
    provider_source_name = (provider_source_aliases or {}).get(
        str(service_execution["provider_source_name"]),
        _impl__sanitize_tool_registry_provider_source_name_for_artifact(
            service_execution["provider_source_name"]
        ),
    )
    runtime_artifacts_payload = service_execution.get("runtime_artifacts", {})
    if not isinstance(runtime_artifacts_payload, dict):
        runtime_artifacts_payload = {}
    service_actions_payload = service_execution.get("service_actions", [])
    if not isinstance(service_actions_payload, (list, tuple)):
        service_actions_payload = []
    return ConfiguredToolRegistryProviderServiceExecutionModel(
        provider=provider,
        provider_source_name=provider_source_name,
        runtime_artifacts=build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
            provider=provider,
            provider_source_name=provider_source_name,
            runtime_artifacts=runtime_artifacts_payload,
            provider_source_aliases=provider_source_aliases,
        ),
        service_actions=build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
            service_actions=service_actions_payload,
            provider_source_aliases=provider_source_aliases,
        ).actions,
    )


def _impl_execute_configured_tool_registry_provider_runtime_service_actions(
    *,
    service_actions: list[dict[str, object]],
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
) -> dict[str, object]:
    result_model = execute_configured_tool_registry_provider_runtime_service_actions_result_model(
        service_actions=service_actions,
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
    )
    return result_model.to_dict()


def _impl_build_configured_tool_registry_provider_runtime_service_actions_result_model(
    *,
    trace_write_count: int,
    audit_event_count: int,
) -> ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel:
    return ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel(
        trace_write_count=int(trace_write_count),
        audit_event_count=int(audit_event_count),
    )


def _impl_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models(
    *,
    execution_result: ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel,
) -> tuple[
    ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel,
    dict[str, object],
]:
    return execution_result, execution_result.to_dict()


def _impl_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict(
    *,
    execution_result: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel,
    dict[str, object],
]:
    result_model = build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict(
        execution_result=execution_result,
    )
    return result_model, result_model.to_dict()


def _impl_build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict(
    *,
    execution_result: dict[str, object],
) -> ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel:
    return build_configured_tool_registry_provider_runtime_service_actions_result_model(
        trace_write_count=int(execution_result.get("trace_write_count", 0)),
        audit_event_count=int(execution_result.get("audit_event_count", 0)),
    )


def _impl_execute_configured_tool_registry_provider_runtime_service_actions_result_model(
    *,
    service_actions: list[dict[str, object]],
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
) -> ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel:
    return execute_configured_tool_registry_provider_runtime_service_actions_model(
        service_actions=build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
            service_actions=service_actions,
        ),
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
    )


def _impl_execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models(
    *,
    service_actions: ConfiguredToolRegistryProviderRuntimeServiceActionsModel,
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
) -> tuple[
    ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel,
    dict[str, object],
]:
    result_model = (
        execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models(
            service_actions=service_actions,
            trace_steps=trace_steps,
            persist_trace_fn=persist_trace_fn,
            record_audit_event_fn=record_audit_event_fn,
        )
    )
    return result_model, result_model.to_dict()


def _impl_execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models(
    *,
    service_actions: ConfiguredToolRegistryProviderRuntimeServiceActionsModel,
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
) -> ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel:
    trace_write_count = 0
    audit_event_count = 0
    provider_source_aliases = _impl_build_safe_tool_registry_provider_source_alias_map(
        list(
            _call_runtime(
                "_iter_tool_runtime_provider_source_artifact_values",
                service_actions.actions,
            )
        )
    )
    for service_action in service_actions.actions:
        kind = service_action.kind
        if kind == "internal_trace_write":
            trace_step = service_action.trace_step
            if trace_step is None:
                continue
            sanitized_trace_step = _sanitize_tool_runtime_trace_artifact_payload(
                trace_step,
                provider_source_aliases=provider_source_aliases,
            )
            sanitized_trace_step = (
                _impl__sanitize_tool_registry_provider_source_fields_for_artifact(
                    sanitized_trace_step,
                    provider_source_aliases=provider_source_aliases,
                )
            )
            if not isinstance(sanitized_trace_step, dict):
                continue
            trace_steps.append(sanitized_trace_step)
            persist_trace_fn(force=bool(service_action.persist_force))
            trace_write_count += 1
            continue
        if kind != "record_audit_event":
            continue
        kwargs = service_action.kwargs
        if kwargs is None:
            continue
        safe_kwargs = _impl__sanitize_tool_registry_provider_source_fields_for_artifact(
            kwargs,
            provider_source_aliases=provider_source_aliases,
        )
        if not isinstance(safe_kwargs, dict):
            continue
        record_audit_event_fn(**safe_kwargs)
        audit_event_count += 1
    return build_configured_tool_registry_provider_runtime_service_actions_result_model(
        trace_write_count=trace_write_count,
        audit_event_count=audit_event_count,
    )


def _impl_execute_configured_tool_registry_provider_runtime_service_actions_model(
    *,
    service_actions: ConfiguredToolRegistryProviderRuntimeServiceActionsModel,
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
) -> ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel:
    return execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models(
        service_actions=service_actions,
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
    )


def _impl_execute_configured_tool_registry_provider_runtime_service_actions_outputs(
    *,
    service_actions: list[dict[str, object]],
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
) -> tuple[
    ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel,
    dict[str, object],
]:
    result_model = execute_configured_tool_registry_provider_runtime_service_actions_result_model(
        service_actions=service_actions,
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
    )
    return result_model, result_model.to_dict()


def _impl_build_configured_tool_registry_provider_service_execution_model(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    settings: object | None = None,
) -> ConfiguredToolRegistryProviderServiceExecutionModel:
    runtime_artifacts = build_configured_tool_registry_provider_runtime_artifacts_model(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        settings=settings,
    )
    return ConfiguredToolRegistryProviderServiceExecutionModel(
        provider=runtime_artifacts.provider,
        provider_source_name=runtime_artifacts.provider_source_name,
        runtime_artifacts=runtime_artifacts,
        service_actions=build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model(
            runtime_artifacts=runtime_artifacts,
        ).actions,
    )


def _impl_build_configured_tool_registry_provider_service_execution(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    settings: object | None = None,
) -> dict[str, object]:
    return build_configured_tool_registry_provider_service_execution_model(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        settings=settings,
    ).to_dict()


def _impl_build_configured_tool_registry_provider_service_execution_result_model(
    *,
    service_execution: dict[str, object],
    execution_result: dict[str, object],
) -> ConfiguredToolRegistryProviderServiceExecutionResultModel:
    result_model, _ = build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
        service_execution=build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution=service_execution,
        ),
        execution_result=execution_result,
    )
    return result_model


def _impl_build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    execution_result: dict[str, object],
) -> ConfiguredToolRegistryProviderServiceExecutionResultModel:
    result_model, _ = build_configured_tool_registry_provider_service_execution_outputs_from_models(
        service_execution=service_execution,
        execution_result=build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict(
            execution_result=execution_result,
        ),
    )
    return result_model


def _impl_build_configured_tool_registry_provider_service_execution_result_model_from_models(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    execution_result: ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel,
) -> ConfiguredToolRegistryProviderServiceExecutionResultModel:
    return ConfiguredToolRegistryProviderServiceExecutionResultModel(
        provider=service_execution.provider,
        provider_source_name=service_execution.provider_source_name,
        runtime_artifacts=service_execution.runtime_artifacts,
        trace_write_count=execution_result.trace_write_count,
        audit_event_count=execution_result.audit_event_count,
    )


def _impl_build_configured_tool_registry_provider_service_execution_outputs_from_models(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    execution_result: ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel,
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    dict[str, object],
]:
    result_model = build_configured_tool_registry_provider_service_execution_result_model_from_models(
        service_execution=service_execution,
        execution_result=execution_result,
    )
    return result_model, result_model.to_dict()


def _impl_build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    execution_result: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    dict[str, object],
]:
    return build_configured_tool_registry_provider_service_execution_outputs_from_models(
        service_execution=service_execution,
        execution_result=build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict(
            execution_result=execution_result,
        ),
    )


def _impl_execute_configured_tool_registry_provider_service_execution_outputs_from_models(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    execution_result: ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel,
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    dict[str, object],
]:
    return build_configured_tool_registry_provider_service_execution_outputs_from_models(
        service_execution=service_execution,
        execution_result=execution_result,
    )


def _impl_build_configured_tool_registry_provider_service_execution_outputs(
    *,
    service_execution: dict[str, object],
    execution_result: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    dict[str, object],
]:
    return build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
        service_execution=build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution=service_execution,
        ),
        execution_result=execution_result,
    )


def _impl_execute_configured_tool_registry_provider_service_execution(
    *,
    service_execution: dict[str, object],
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
) -> dict[str, object]:
    _, result_dict = execute_configured_tool_registry_provider_service_execution_outputs(
        service_execution=service_execution,
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
    )
    return result_dict


def _impl_execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    dict[str, object],
]:
    return execute_configured_tool_registry_provider_service_execution_outputs_from_models(
        service_execution=service_execution,
        execution_result=execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models(
            service_actions=ConfiguredToolRegistryProviderRuntimeServiceActionsModel(
                actions=service_execution.service_actions,
            ),
            trace_steps=trace_steps,
            persist_trace_fn=persist_trace_fn,
            record_audit_event_fn=record_audit_event_fn,
        )[0],
    )


def _impl_execute_configured_tool_registry_provider_service_execution_outputs(
    *,
    service_execution: dict[str, object],
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    dict[str, object],
]:
    return execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
        service_execution=build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution=service_execution,
        ),
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
    )


def _impl_execute_configured_tool_registry_provider_service_execution_model(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
) -> ConfiguredToolRegistryProviderServiceExecutionResultModel:
    result_model, _ = execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
        service_execution=service_execution,
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
    )
    return result_model


def _impl_build_configured_tool_registry_provider_preflight_summary_model(
    *,
    preflight_result: dict[str, object],
) -> ConfiguredToolRegistryProviderPreflightSummaryModel:
    return build_configured_tool_registry_provider_preflight_summary_model_from_dict(
        preflight_result=preflight_result,
    )


def _impl_build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
    *,
    preflight_result: dict[str, object],
) -> ConfiguredToolRegistryProviderServiceExecutionModel:
    return build_configured_tool_registry_provider_service_execution_model_from_dict(
        service_execution=build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict(
            preflight_result=preflight_result,
        )
    )


def _impl_build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict(
    *,
    preflight_result: dict[str, object],
) -> dict[str, object]:
    service_execution_payload = preflight_result.get("service_execution", {})
    if not isinstance(service_execution_payload, dict):
        service_execution_payload = {}
    provider = preflight_result.get("provider", service_execution_payload.get("provider"))
    if provider is None:
        provider = StaticToolRegistryProvider({})
    provider_source_name = preflight_result.get(
        "provider_source_name",
        service_execution_payload.get("provider_source_name", "default"),
    )
    runtime_artifacts_payload = preflight_result.get("runtime_artifacts", {})
    if not isinstance(runtime_artifacts_payload, dict):
        runtime_artifacts_payload = {}
    service_runtime_artifacts_payload = service_execution_payload.get("runtime_artifacts", {})
    if not isinstance(service_runtime_artifacts_payload, dict):
        service_runtime_artifacts_payload = {}
    merged_runtime_artifacts_payload: dict[str, object] = {}
    merged_runtime_artifacts_payload.update(service_runtime_artifacts_payload)
    merged_runtime_artifacts_payload.update(runtime_artifacts_payload)
    return {
        **service_execution_payload,
        "provider": service_execution_payload.get("provider", provider),
        "provider_source_name": service_execution_payload.get(
            "provider_source_name", provider_source_name
        ),
        "runtime_artifacts": merged_runtime_artifacts_payload,
    }


def _impl__merge_configured_tool_registry_provider_preflight_service_execution_payload(
    *,
    service_execution: dict[str, object],
    preflight_result: dict[str, object],
) -> dict[str, object]:
    provider = service_execution.get("provider", preflight_result.get("provider"))
    if provider is None:
        provider = StaticToolRegistryProvider({})
    provider_source_name = service_execution.get(
        "provider_source_name",
        preflight_result.get("provider_source_name", "default"),
    )
    runtime_artifacts_payload = preflight_result.get("runtime_artifacts", {})
    if not isinstance(runtime_artifacts_payload, dict):
        runtime_artifacts_payload = {}
    service_runtime_artifacts_payload = service_execution.get("runtime_artifacts", {})
    if not isinstance(service_runtime_artifacts_payload, dict):
        service_runtime_artifacts_payload = {}
    merged_runtime_artifacts_payload: dict[str, object] = {}
    merged_runtime_artifacts_payload.update(service_runtime_artifacts_payload)
    merged_runtime_artifacts_payload.update(runtime_artifacts_payload)
    return {
        **service_execution,
        "provider": service_execution.get("provider", provider),
        "provider_source_name": service_execution.get(
            "provider_source_name",
            provider_source_name,
        ),
        "runtime_artifacts": merged_runtime_artifacts_payload,
    }


def _impl_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict(
    *,
    preflight_result: dict[str, object],
) -> ConfiguredToolRegistryProviderServiceExecutionResultModel:
    return build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model(
        service_execution=build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
            preflight_result=preflight_result,
        ),
        preflight_result=preflight_result,
    )


def _impl_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    preflight_result: dict[str, object],
) -> ConfiguredToolRegistryProviderServiceExecutionResultModel:
    return build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model(
        service_execution=service_execution,
        execution_result=preflight_result,
    )


def _impl_build_configured_tool_registry_provider_preflight_execution_models_from_dict(
    *,
    preflight_result: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
]:
    service_execution_model = (
        build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
            preflight_result=preflight_result,
        )
    )
    execution_result_model = (
        build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model(
            service_execution=service_execution_model,
            preflight_result=preflight_result,
        )
    )
    return service_execution_model, execution_result_model


def _impl_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload(
    *,
    service_execution: dict[str, object],
    preflight_result: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
]:
    service_execution_model = build_configured_tool_registry_provider_service_execution_model_from_dict(
        service_execution=_merge_configured_tool_registry_provider_preflight_service_execution_payload(
            service_execution=service_execution,
            preflight_result=preflight_result,
        ),
    )
    execution_result_model = (
        build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model(
            service_execution=service_execution_model,
            preflight_result=preflight_result,
        )
    )
    return service_execution_model, execution_result_model


def _impl_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    preflight_result: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
]:
    execution_result_model = (
        build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model(
            service_execution=service_execution,
            preflight_result=preflight_result,
        )
    )
    return service_execution, execution_result_model


def _impl_build_configured_tool_registry_provider_preflight_models_from_service_execution_payload(
    *,
    service_execution: dict[str, object],
    preflight_result: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
]:
    (
        service_execution_model,
        execution_result_model,
    ) = build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload(
        service_execution=service_execution,
        preflight_result=preflight_result,
    )
    (
        service_execution_model,
        execution_result_model,
        summary_model,
        result_model,
    ) = build_configured_tool_registry_provider_preflight_models_from_models(
        service_execution=service_execution_model,
        execution_result=execution_result_model,
    )
    return (
        service_execution_model,
        execution_result_model,
        summary_model,
        result_model,
    )


def _impl_build_configured_tool_registry_provider_preflight_models_from_service_execution_model(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    preflight_result: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
]:
    (
        service_execution_model,
        execution_result_model,
    ) = build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model(
        service_execution=service_execution,
        preflight_result=preflight_result,
    )
    (
        service_execution_model,
        execution_result_model,
        summary_model,
        result_model,
    ) = build_configured_tool_registry_provider_preflight_models_from_models(
        service_execution=service_execution_model,
        execution_result=execution_result_model,
    )
    return (
        service_execution_model,
        execution_result_model,
        summary_model,
        result_model,
    )


def _impl_build_configured_tool_registry_provider_preflight_models_from_dict(
    *,
    preflight_result: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
]:
    (
        service_execution_model,
        execution_result_model,
    ) = build_configured_tool_registry_provider_preflight_execution_models_from_dict(
        preflight_result=preflight_result,
    )
    (
        service_execution_model,
        execution_result_model,
        summary_model,
        result_model,
    ) = build_configured_tool_registry_provider_preflight_models_from_models(
        service_execution=service_execution_model,
        execution_result=execution_result_model,
    )
    return (
        service_execution_model,
        execution_result_model,
        summary_model,
        result_model,
    )

def _impl_build_configured_tool_registry_provider_preflight_models_from_models(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    execution_result: ConfiguredToolRegistryProviderServiceExecutionResultModel,
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
]:
    summary_model = build_configured_tool_registry_provider_preflight_summary_model_from_parts(
        provider=execution_result.provider,
        provider_source_name=execution_result.provider_source_name,
        runtime_artifacts=execution_result.runtime_artifacts,
        service_actions=service_execution.service_actions,
        trace_write_count=execution_result.trace_write_count,
        audit_event_count=execution_result.audit_event_count,
    )
    result_model = ConfiguredToolRegistryProviderPreflightResultModel(
        provider=execution_result.provider,
        provider_source_name=execution_result.provider_source_name,
        runtime_artifacts=execution_result.runtime_artifacts,
        service_execution=service_execution,
        trace_write_count=execution_result.trace_write_count,
        audit_event_count=execution_result.audit_event_count,
        summary=summary_model,
    )
    return (
        service_execution,
        execution_result,
        summary_model,
        result_model,
    )


def _impl_build_configured_tool_registry_provider_preflight_summary_model_from_dict(
    *,
    preflight_result: dict[str, object],
) -> ConfiguredToolRegistryProviderPreflightSummaryModel:
    return build_configured_tool_registry_provider_preflight_summary_model_from_result_model(
        preflight_result=build_configured_tool_registry_provider_preflight_result_model_from_dict(
            preflight_result=preflight_result,
        ),
    )


def _impl_build_configured_tool_registry_provider_preflight_summary_model_from_result_model(
    *,
    preflight_result: ConfiguredToolRegistryProviderPreflightResultModel,
) -> ConfiguredToolRegistryProviderPreflightSummaryModel:
    return preflight_result.summary


def _impl_build_configured_tool_registry_provider_preflight_summary_model_from_models(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    execution_result: ConfiguredToolRegistryProviderServiceExecutionResultModel,
) -> ConfiguredToolRegistryProviderPreflightSummaryModel:
    return build_configured_tool_registry_provider_preflight_summary_model_from_result_model(
        preflight_result=build_configured_tool_registry_provider_preflight_result_model_from_models(
            service_execution=service_execution,
            execution_result=execution_result,
        ),
    )


def _impl_build_configured_tool_registry_provider_preflight_summary_model_from_parts(
    *,
    provider: ToolRegistryProvider,
    provider_source_name: str,
    runtime_artifacts: ConfiguredToolRegistryProviderRuntimeArtifactsModel,
    service_actions: tuple[ConfiguredToolRegistryProviderRuntimeServiceActionModel, ...],
    trace_write_count: int,
    audit_event_count: int,
) -> ConfiguredToolRegistryProviderPreflightSummaryModel:
    tool_registry = provider.load_tool_registry()
    diagnostics_summary = runtime_artifacts.diagnostics_runtime.summary
    return ConfiguredToolRegistryProviderPreflightSummaryModel(
        provider_source_name=provider_source_name,
        tool_count=len(tool_registry),
        tool_names=tuple(sorted(tool_registry)),
        tool_details=build_configured_tool_registry_provider_preflight_tool_details(
            provider=provider,
            diagnostics=runtime_artifacts.selected_source_diagnostics,
        ),
        service_action_count=len(service_actions),
        service_action_kinds=tuple(action.kind for action in service_actions),
        trace_write_count=trace_write_count,
        audit_event_count=audit_event_count,
        has_diagnostics=diagnostics_summary.has_diagnostics,
        diagnostics_total=diagnostics_summary.total,
        skipped_total=diagnostics_summary.skipped_total,
        missing_total=diagnostics_summary.missing_total,
        diagnostics_summary=diagnostics_summary.to_dict(),
    )


def _impl_build_configured_tool_registry_provider_preflight_summary(
    *,
    preflight_result: dict[str, object],
) -> dict[str, object]:
    return build_configured_tool_registry_provider_preflight_summary_model(
        preflight_result=preflight_result,
    ).to_dict()


def _impl_build_configured_tool_registry_provider_preflight_outputs_from_resolved_models(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    execution_result: ConfiguredToolRegistryProviderServiceExecutionResultModel,
    summary: ConfiguredToolRegistryProviderPreflightSummaryModel,
    result: ConfiguredToolRegistryProviderPreflightResultModel,
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
    dict[str, object],
    dict[str, object],
]:
    return (
        service_execution,
        execution_result,
        summary,
        result,
        summary.to_dict(),
        result.to_dict(),
    )


def _impl_build_configured_tool_registry_provider_preflight_outputs_from_models(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    execution_result: ConfiguredToolRegistryProviderServiceExecutionResultModel,
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
    dict[str, object],
    dict[str, object],
]:
    (
        service_execution_model,
        execution_result_model,
        summary_model,
        result_model,
    ) = build_configured_tool_registry_provider_preflight_models_from_models(
        service_execution=service_execution,
        execution_result=execution_result,
    )
    return build_configured_tool_registry_provider_preflight_outputs_from_resolved_models(
        service_execution=service_execution,
        execution_result=execution_result_model,
        summary=summary_model,
        result=result_model,
    )


def _impl_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    preflight_result: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
    dict[str, object],
    dict[str, object],
]:
    (
        service_execution_model,
        execution_result_model,
    ) = build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model(
        service_execution=service_execution,
        preflight_result=preflight_result,
    )
    return build_configured_tool_registry_provider_preflight_outputs_from_models(
        service_execution=service_execution_model,
        execution_result=execution_result_model,
    )


def _impl_build_configured_tool_registry_provider_preflight_outputs(
    *,
    service_execution: dict[str, object],
    execution_result: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
    dict[str, object],
    dict[str, object],
]:
    return build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload(
        service_execution=service_execution,
        execution_result=execution_result,
    )


def _impl_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload(
    *,
    service_execution: dict[str, object],
    execution_result: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
    dict[str, object],
    dict[str, object],
]:
    return build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
        service_execution=build_configured_tool_registry_provider_service_execution_model_from_dict(
            service_execution=_merge_configured_tool_registry_provider_preflight_service_execution_payload(
                service_execution=service_execution,
                preflight_result=execution_result,
            ),
        ),
        preflight_result=execution_result,
    )


def _impl_build_configured_tool_registry_provider_preflight_outputs_from_dict(
    *,
    preflight_result: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
    dict[str, object],
    dict[str, object],
]:
    return build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
        service_execution=build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
            preflight_result=preflight_result,
        ),
        preflight_result=preflight_result,
    )


def _impl_build_configured_tool_registry_provider_preflight_models(
    *,
    service_execution: dict[str, object],
    execution_result: dict[str, object],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
]:
    return build_configured_tool_registry_provider_preflight_models_from_service_execution_payload(
        service_execution=service_execution,
        preflight_result=execution_result,
    )


def _impl_build_configured_tool_registry_provider_preflight_dicts(
    *,
    preflight_result: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    result_model = build_configured_tool_registry_provider_preflight_result_model_from_dict(
        preflight_result=preflight_result,
    )
    return result_model.summary.to_dict(), result_model.to_dict()


def _impl_build_configured_tool_registry_provider_preflight_result_model(
    *,
    service_execution: dict[str, object],
    execution_result: dict[str, object],
) -> ConfiguredToolRegistryProviderPreflightResultModel:
    _, _, _, result_model = (
        build_configured_tool_registry_provider_preflight_models_from_service_execution_payload(
            service_execution=service_execution,
            preflight_result=execution_result,
        )
    )
    return result_model


def _impl_build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    execution_result: dict[str, object],
) -> ConfiguredToolRegistryProviderPreflightResultModel:
    _, _, _, result_model = (
        build_configured_tool_registry_provider_preflight_models_from_service_execution_model(
            service_execution=service_execution,
            preflight_result=execution_result,
        )
    )
    return result_model


def _impl_build_configured_tool_registry_provider_preflight_result_model_from_models(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    execution_result: ConfiguredToolRegistryProviderServiceExecutionResultModel,
) -> ConfiguredToolRegistryProviderPreflightResultModel:
    _, _, _, result_model, _, _ = build_configured_tool_registry_provider_preflight_outputs_from_models(
        service_execution=service_execution,
        execution_result=execution_result,
    )
    return result_model


def _impl_build_configured_tool_registry_provider_preflight_result_model_from_dict(
    *,
    preflight_result: dict[str, object],
) -> ConfiguredToolRegistryProviderPreflightResultModel:
    _, _, _, result_model, _, _ = build_configured_tool_registry_provider_preflight_outputs_from_dict(
        preflight_result=preflight_result,
    )
    return result_model


def _impl_build_configured_tool_registry_provider_preflight_result(
    *,
    service_execution: dict[str, object],
    execution_result: dict[str, object],
) -> dict[str, object]:
    return build_configured_tool_registry_provider_preflight_result_model(
        service_execution=service_execution,
        execution_result=execution_result,
    ).to_dict()


def _impl_execute_configured_tool_registry_provider_preflight_models_from_service_execution_model(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
]:
    execution_result_model, _ = (
        execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
            service_execution=service_execution,
            trace_steps=trace_steps,
            persist_trace_fn=persist_trace_fn,
            record_audit_event_fn=record_audit_event_fn,
        )
    )
    (
        service_execution_model,
        execution_result_model,
        summary_model,
        result_model,
    ) = build_configured_tool_registry_provider_preflight_models_from_models(
        service_execution=service_execution,
        execution_result=execution_result_model,
    )
    return (
        service_execution_model,
        execution_result_model,
        summary_model,
        result_model,
    )


def _impl_execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
    dict[str, object],
    dict[str, object],
]:
    (
        service_execution_model,
        resolved_execution_result_model,
        summary_model,
        result_model,
    ) = execute_configured_tool_registry_provider_preflight_models_from_service_execution_model(
        service_execution=service_execution,
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
    )
    return build_configured_tool_registry_provider_preflight_outputs_from_resolved_models(
        service_execution=service_execution_model,
        execution_result=resolved_execution_result_model,
        summary=summary_model,
        result=result_model,
    )


def _impl_execute_configured_tool_registry_provider_preflight_outputs(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
    settings: object | None = None,
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
    dict[str, object],
    dict[str, object],
]:
    (
        service_execution_model,
        execution_result_model,
        summary_model,
        result_model,
    ) = execute_configured_tool_registry_provider_preflight_models(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
        settings=settings,
    )
    return build_configured_tool_registry_provider_preflight_outputs_from_resolved_models(
        service_execution=service_execution_model,
        execution_result=execution_result_model,
        summary=summary_model,
        result=result_model,
    )


def _impl_execute_configured_tool_registry_provider_preflight_summary_model(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
    settings: object | None = None,
) -> ConfiguredToolRegistryProviderPreflightSummaryModel:
    result_model = execute_configured_tool_registry_provider_preflight_model(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
        settings=settings,
    )
    return build_configured_tool_registry_provider_preflight_summary_model_from_result_model(
        preflight_result=result_model,
    )


def _impl_execute_configured_tool_registry_provider_preflight_summary(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
    settings: object | None = None,
) -> dict[str, object]:
    return execute_configured_tool_registry_provider_preflight_summary_model(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
        settings=settings,
    ).to_dict()


def _impl_execute_configured_tool_registry_provider_preflight_dicts(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
    settings: object | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    result_model = execute_configured_tool_registry_provider_preflight_model(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
        settings=settings,
    )
    return result_model.summary.to_dict(), result_model.to_dict()


def _impl_execute_configured_tool_registry_provider_preflight_models(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
    settings: object | None = None,
) -> tuple[
    ConfiguredToolRegistryProviderServiceExecutionModel,
    ConfiguredToolRegistryProviderServiceExecutionResultModel,
    ConfiguredToolRegistryProviderPreflightSummaryModel,
    ConfiguredToolRegistryProviderPreflightResultModel,
]:
    return execute_configured_tool_registry_provider_preflight_models_from_service_execution_model(
        service_execution=build_configured_tool_registry_provider_service_execution_model(
            task_id=task_id,
            step_id=step_id,
            seq=seq,
            model=model,
            settings=settings,
        ),
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
    )


def _impl_execute_configured_tool_registry_provider_preflight(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
    settings: object | None = None,
) -> dict[str, object]:
    return execute_configured_tool_registry_provider_preflight_model(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
        settings=settings,
    ).to_dict()


def _impl_execute_configured_tool_registry_provider_preflight_model(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
    settings: object | None = None,
) -> ConfiguredToolRegistryProviderPreflightResultModel:
    _, _, _, result_model = execute_configured_tool_registry_provider_preflight_models(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
        settings=settings,
    )
    return result_model


def _impl_build_configured_tool_registry_provider_runtime_artifacts_model(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    settings: object | None = None,
) -> ConfiguredToolRegistryProviderRuntimeArtifactsModel:
    artifacts = get_configured_tool_registry_provider_artifacts(settings=settings)
    provider_sources = artifacts["provider_sources"]
    alias_by_source = _impl_build_safe_tool_registry_provider_source_alias_map(
        list(provider_sources.keys()) if isinstance(provider_sources, dict) else ()
    )
    diagnostics_runtime = build_tool_registry_diagnostics_runtime_artifacts_model(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        provider_source_name=str(artifacts["provider_source_name"]),
        diagnostics=artifacts["selected_source_diagnostics"],
        provider_source_aliases=alias_by_source,
    )
    safe_provider_source_name = alias_by_source.get(
        str(artifacts["provider_source_name"]),
        _impl__sanitize_tool_registry_provider_source_name_for_artifact(
            artifacts["provider_source_name"]
        ),
    )
    return ConfiguredToolRegistryProviderRuntimeArtifactsModel(
        provider=artifacts["provider"],
        provider_source_name=safe_provider_source_name,
        provider_sources=_impl__sanitize_tool_registry_provider_sources_for_artifact(
            provider_sources
        ),
        selected_source_diagnostics=artifacts["selected_source_diagnostics"],
        source_diagnostics=artifacts["source_diagnostics"],
        diagnostics_runtime=diagnostics_runtime,
        audit_event=build_tool_registry_diagnostics_audit_event(
            diagnostics_runtime=diagnostics_runtime.to_dict()
        ),
    )


def _impl_build_configured_tool_registry_provider_runtime_artifacts(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    settings: object | None = None,
) -> dict[str, object]:
    return build_configured_tool_registry_provider_runtime_artifacts_model(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        settings=settings,
    ).to_dict()


def bind_tool_runtime_registry_runtime_public_names(
    namespace: dict[str, object],
) -> None:
    _bind_registry_namespace(namespace)
