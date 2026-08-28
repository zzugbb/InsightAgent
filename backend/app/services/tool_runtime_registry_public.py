from __future__ import annotations

from collections.abc import Callable, MutableMapping, Sequence
from functools import wraps

PublicWrapperSpec = tuple[str, str]

_PUBLIC_WRAPPER_SPECS: tuple[PublicWrapperSpec, ...] = (
    ('build_tool_registry_extra_tools_from_file', '_impl_build_tool_registry_extra_tools_from_file'),
    ('_resolve_tool_registry_file_path', '_impl__resolve_tool_registry_file_path'),
    ('_resolve_tool_registry_dir_path', '_impl__resolve_tool_registry_dir_path'),
    ('load_tool_registry_file_payload', '_impl_load_tool_registry_file_payload'),
    ('_normalize_tool_registry_file_diagnostics', '_impl__normalize_tool_registry_file_diagnostics'),
    ('_empty_tool_registry_file_diagnostics', '_impl__empty_tool_registry_file_diagnostics'),
    ('_has_tool_registry_file_diagnostics', '_impl__has_tool_registry_file_diagnostics'),
    ('_merge_tool_registry_file_diagnostics', '_impl__merge_tool_registry_file_diagnostics'),
    ('sanitize_tool_registry_file_diagnostics', '_impl_sanitize_tool_registry_file_diagnostics'),
    ('sanitize_tool_registry_source_diagnostics', '_impl_sanitize_tool_registry_source_diagnostics'),
    ('sanitize_tool_registry_diagnostics_summary_entries', '_impl_sanitize_tool_registry_diagnostics_summary_entries'),
    ('sanitize_tool_registry_diagnostics_artifact_payload', '_impl_sanitize_tool_registry_diagnostics_artifact_payload'),
    ('_filter_tool_registry_json_object_setting_for_visited_registry_files', '_impl__filter_tool_registry_json_object_setting_for_visited_registry_files'),
    ('_clone_tool_registry_settings_without_visited_registry_file_components', '_impl__clone_tool_registry_settings_without_visited_registry_file_components'),
    ('_expand_skipped_registry_file_component_names', '_impl__expand_skipped_registry_file_component_names'),
    ('_build_tool_registry_from_file_registry', '_impl__build_tool_registry_from_file_registry'),
    ('build_tool_registry_from_file_artifacts', '_impl_build_tool_registry_from_file_artifacts'),
    ('build_tool_registry_loader_from_file_artifacts', '_impl_build_tool_registry_loader_from_file_artifacts'),
    ('build_tool_registry_provider_from_file_artifacts', '_impl_build_tool_registry_provider_from_file_artifacts'),
    ('build_tool_registry_from_file', '_impl_build_tool_registry_from_file'),
    ('build_tool_registry_loader_from_file', '_impl_build_tool_registry_loader_from_file'),
    ('build_tool_registry_provider_from_file', '_impl_build_tool_registry_provider_from_file'),
    ('_build_tool_registry_loader_factory_adapter', '_impl__build_tool_registry_loader_factory_adapter'),
    ('_build_tool_registry_provider_factory_adapter', '_impl__build_tool_registry_provider_factory_adapter'),
    ('build_tool_registry_loaders_from_settings_artifacts', '_impl_build_tool_registry_loaders_from_settings_artifacts'),
    ('build_tool_registry_loader_factories_from_settings_artifacts', '_impl_build_tool_registry_loader_factories_from_settings_artifacts'),
    ('build_tool_registry_loader_factories_from_settings', '_impl_build_tool_registry_loader_factories_from_settings'),
    ('build_tool_registry_provider_factories_from_settings_artifacts', '_impl_build_tool_registry_provider_factories_from_settings_artifacts'),
    ('build_tool_registry_provider_factories_from_settings', '_impl_build_tool_registry_provider_factories_from_settings'),
    ('build_tool_registry_loader_adapter', '_impl_build_tool_registry_loader_adapter'),
    ('build_tool_registry_loaders_from_settings', '_impl_build_tool_registry_loaders_from_settings'),
    ('build_tool_registry_provider_adapter', '_impl_build_tool_registry_provider_adapter'),
    ('build_tool_registry_providers_from_settings', '_impl_build_tool_registry_providers_from_settings'),
    ('build_tool_registry_providers_from_settings_artifacts', '_impl_build_tool_registry_providers_from_settings_artifacts'),
    ('build_tool_registry_provider_sources_from_settings', '_impl_build_tool_registry_provider_sources_from_settings'),
    ('build_tool_registry_provider_sources_from_settings_artifacts', '_impl_build_tool_registry_provider_sources_from_settings_artifacts'),
    ('build_safe_tool_registry_provider_source_alias_map', '_impl_build_safe_tool_registry_provider_source_alias_map'),
    ('resolve_unique_tool_registry_provider_source_alias', '_impl_resolve_unique_tool_registry_provider_source_alias'),
    ('build_tool_registry_extra_tools_from_settings', '_impl_build_tool_registry_extra_tools_from_settings'),
    ('_build_registry_overrides_from_specs', '_impl__build_registry_overrides_from_specs'),
    ('build_tool_registry_settings_config', '_impl_build_tool_registry_settings_config'),
    ('build_tool_registry_overrides_from_settings', '_impl_build_tool_registry_overrides_from_settings'),
    ('get_disabled_tool_names_from_settings', '_impl_get_disabled_tool_names_from_settings'),
    ('get_configured_tool_registry_provider', '_impl_get_configured_tool_registry_provider'),
    ('get_configured_tool_registry_provider_artifacts', '_impl_get_configured_tool_registry_provider_artifacts'),
    ('build_tool_registry_diagnostics_summary_model', '_impl_build_tool_registry_diagnostics_summary_model'),
    ('build_tool_registry_diagnostics_summary', '_impl_build_tool_registry_diagnostics_summary'),
    ('_humanize_tool_registry_diagnostics_target', '_impl__humanize_tool_registry_diagnostics_target'),
    ('build_tool_registry_diagnostics_display_lines', '_impl_build_tool_registry_diagnostics_display_lines'),
    ('build_tool_registry_diagnostics_runtime_artifacts_model', '_impl_build_tool_registry_diagnostics_runtime_artifacts_model'),
    ('build_tool_registry_diagnostics_runtime_artifacts', '_impl_build_tool_registry_diagnostics_runtime_artifacts'),
    ('build_tool_registry_diagnostics_audit_event', '_impl_build_tool_registry_diagnostics_audit_event'),
    ('build_tool_registry_diagnostics_audit_service_action', '_impl_build_tool_registry_diagnostics_audit_service_action'),
    ('build_tool_registry_diagnostics_audit_service_action_model', '_impl_build_tool_registry_diagnostics_audit_service_action_model'),
    ('build_tool_registry_diagnostics_trace_service_action', '_impl_build_tool_registry_diagnostics_trace_service_action'),
    ('build_tool_registry_diagnostics_trace_service_action_model', '_impl_build_tool_registry_diagnostics_trace_service_action_model'),
    ('build_configured_tool_registry_provider_runtime_service_actions', '_impl_build_configured_tool_registry_provider_runtime_service_actions'),
    ('build_configured_tool_registry_provider_runtime_service_actions_model', '_impl_build_configured_tool_registry_provider_runtime_service_actions_model'),
    ('build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models', '_impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models'),
    ('build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model', '_impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model'),
    ('build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts', '_impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts'),
    ('build_configured_tool_registry_provider_runtime_service_actions_outputs', '_impl_build_configured_tool_registry_provider_runtime_service_actions_outputs'),
    ('build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model', '_impl_build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model'),
    ('build_configured_tool_registry_provider_runtime_service_action_model_from_dict', '_impl_build_configured_tool_registry_provider_runtime_service_action_model_from_dict'),
    ('build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts', '_impl_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts'),
    ('build_configured_tool_registry_provider_runtime_artifacts_model_from_dict', '_impl_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict'),
    ('build_configured_tool_registry_provider_service_execution_model_from_dict', '_impl_build_configured_tool_registry_provider_service_execution_model_from_dict'),
    ('execute_configured_tool_registry_provider_runtime_service_actions', '_impl_execute_configured_tool_registry_provider_runtime_service_actions'),
    ('build_configured_tool_registry_provider_runtime_service_actions_result_model', '_impl_build_configured_tool_registry_provider_runtime_service_actions_result_model'),
    ('build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models', '_impl_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models'),
    ('build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict', '_impl_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict'),
    ('build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict', '_impl_build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict'),
    ('execute_configured_tool_registry_provider_runtime_service_actions_result_model', '_impl_execute_configured_tool_registry_provider_runtime_service_actions_result_model'),
    ('execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models', '_impl_execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models'),
    ('execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models', '_impl_execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models'),
    ('execute_configured_tool_registry_provider_runtime_service_actions_model', '_impl_execute_configured_tool_registry_provider_runtime_service_actions_model'),
    ('execute_configured_tool_registry_provider_runtime_service_actions_outputs', '_impl_execute_configured_tool_registry_provider_runtime_service_actions_outputs'),
    ('build_configured_tool_registry_provider_service_execution_model', '_impl_build_configured_tool_registry_provider_service_execution_model'),
    ('build_configured_tool_registry_provider_service_execution', '_impl_build_configured_tool_registry_provider_service_execution'),
    ('build_configured_tool_registry_provider_service_execution_result_model', '_impl_build_configured_tool_registry_provider_service_execution_result_model'),
    ('build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model', '_impl_build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model'),
    ('build_configured_tool_registry_provider_service_execution_result_model_from_models', '_impl_build_configured_tool_registry_provider_service_execution_result_model_from_models'),
    ('build_configured_tool_registry_provider_service_execution_outputs_from_models', '_impl_build_configured_tool_registry_provider_service_execution_outputs_from_models'),
    ('build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model', '_impl_build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model'),
    ('execute_configured_tool_registry_provider_service_execution_outputs_from_models', '_impl_execute_configured_tool_registry_provider_service_execution_outputs_from_models'),
    ('build_configured_tool_registry_provider_service_execution_outputs', '_impl_build_configured_tool_registry_provider_service_execution_outputs'),
    ('execute_configured_tool_registry_provider_service_execution', '_impl_execute_configured_tool_registry_provider_service_execution'),
    ('execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model', '_impl_execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model'),
    ('execute_configured_tool_registry_provider_service_execution_outputs', '_impl_execute_configured_tool_registry_provider_service_execution_outputs'),
    ('execute_configured_tool_registry_provider_service_execution_model', '_impl_execute_configured_tool_registry_provider_service_execution_model'),
    ('build_configured_tool_registry_provider_preflight_summary_model', '_impl_build_configured_tool_registry_provider_preflight_summary_model'),
    ('build_configured_tool_registry_provider_preflight_service_execution_model_from_dict', '_impl_build_configured_tool_registry_provider_preflight_service_execution_model_from_dict'),
    ('build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict', '_impl_build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict'),
    ('_merge_configured_tool_registry_provider_preflight_service_execution_payload', '_impl__merge_configured_tool_registry_provider_preflight_service_execution_payload'),
    ('build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict', '_impl_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict'),
    ('build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model', '_impl_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model'),
    ('build_configured_tool_registry_provider_preflight_execution_models_from_dict', '_impl_build_configured_tool_registry_provider_preflight_execution_models_from_dict'),
    ('build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload', '_impl_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload'),
    ('build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model', '_impl_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model'),
    ('build_configured_tool_registry_provider_preflight_models_from_service_execution_payload', '_impl_build_configured_tool_registry_provider_preflight_models_from_service_execution_payload'),
    ('build_configured_tool_registry_provider_preflight_models_from_service_execution_model', '_impl_build_configured_tool_registry_provider_preflight_models_from_service_execution_model'),
    ('build_configured_tool_registry_provider_preflight_models_from_dict', '_impl_build_configured_tool_registry_provider_preflight_models_from_dict'),
    ('build_configured_tool_registry_provider_preflight_models_from_models', '_impl_build_configured_tool_registry_provider_preflight_models_from_models'),
    ('build_configured_tool_registry_provider_preflight_summary_model_from_dict', '_impl_build_configured_tool_registry_provider_preflight_summary_model_from_dict'),
    ('build_configured_tool_registry_provider_preflight_summary_model_from_result_model', '_impl_build_configured_tool_registry_provider_preflight_summary_model_from_result_model'),
    ('build_configured_tool_registry_provider_preflight_summary_model_from_models', '_impl_build_configured_tool_registry_provider_preflight_summary_model_from_models'),
    ('build_configured_tool_registry_provider_preflight_summary_model_from_parts', '_impl_build_configured_tool_registry_provider_preflight_summary_model_from_parts'),
    ('build_configured_tool_registry_provider_preflight_summary', '_impl_build_configured_tool_registry_provider_preflight_summary'),
    ('build_configured_tool_registry_provider_preflight_outputs_from_resolved_models', '_impl_build_configured_tool_registry_provider_preflight_outputs_from_resolved_models'),
    ('build_configured_tool_registry_provider_preflight_outputs_from_models', '_impl_build_configured_tool_registry_provider_preflight_outputs_from_models'),
    ('build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model', '_impl_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model'),
    ('build_configured_tool_registry_provider_preflight_outputs', '_impl_build_configured_tool_registry_provider_preflight_outputs'),
    ('build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload', '_impl_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload'),
    ('build_configured_tool_registry_provider_preflight_outputs_from_dict', '_impl_build_configured_tool_registry_provider_preflight_outputs_from_dict'),
    ('build_configured_tool_registry_provider_preflight_models', '_impl_build_configured_tool_registry_provider_preflight_models'),
    ('build_configured_tool_registry_provider_preflight_dicts', '_impl_build_configured_tool_registry_provider_preflight_dicts'),
    ('build_configured_tool_registry_provider_preflight_result_model', '_impl_build_configured_tool_registry_provider_preflight_result_model'),
    ('build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model', '_impl_build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model'),
    ('build_configured_tool_registry_provider_preflight_result_model_from_models', '_impl_build_configured_tool_registry_provider_preflight_result_model_from_models'),
    ('build_configured_tool_registry_provider_preflight_result_model_from_dict', '_impl_build_configured_tool_registry_provider_preflight_result_model_from_dict'),
    ('build_configured_tool_registry_provider_preflight_result', '_impl_build_configured_tool_registry_provider_preflight_result'),
    ('execute_configured_tool_registry_provider_preflight_models_from_service_execution_model', '_impl_execute_configured_tool_registry_provider_preflight_models_from_service_execution_model'),
    ('execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model', '_impl_execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model'),
    ('execute_configured_tool_registry_provider_preflight_outputs', '_impl_execute_configured_tool_registry_provider_preflight_outputs'),
    ('execute_configured_tool_registry_provider_preflight_summary_model', '_impl_execute_configured_tool_registry_provider_preflight_summary_model'),
    ('execute_configured_tool_registry_provider_preflight_summary', '_impl_execute_configured_tool_registry_provider_preflight_summary'),
    ('execute_configured_tool_registry_provider_preflight_dicts', '_impl_execute_configured_tool_registry_provider_preflight_dicts'),
    ('execute_configured_tool_registry_provider_preflight_models', '_impl_execute_configured_tool_registry_provider_preflight_models'),
    ('execute_configured_tool_registry_provider_preflight', '_impl_execute_configured_tool_registry_provider_preflight'),
    ('execute_configured_tool_registry_provider_preflight_model', '_impl_execute_configured_tool_registry_provider_preflight_model'),
    ('build_configured_tool_registry_provider_runtime_artifacts_model', '_impl_build_configured_tool_registry_provider_runtime_artifacts_model'),
    ('build_configured_tool_registry_provider_runtime_artifacts', '_impl_build_configured_tool_registry_provider_runtime_artifacts'),
)


def make_tool_runtime_registry_public_dispatcher(
    namespace: MutableMapping[str, object],
) -> Callable[..., object]:
    def _call_public_or_impl(name: str, impl, *args, **kwargs):
        runtime_module = namespace["_runtime_module"]
        active_public_proxy_names = namespace["_ACTIVE_PUBLIC_PROXY_NAMES"]
        public_value = getattr(runtime_module(), name, None)
        local_value = namespace.get(name)
        if (
            public_value is not None
            and public_value is not local_value
            and name not in active_public_proxy_names
        ):
            active_public_proxy_names.add(name)
            try:
                return public_value(*args, **kwargs)
            finally:
                active_public_proxy_names.discard(name)
        return impl(*args, **kwargs)

    return _call_public_or_impl


def _make_public_wrapper(
    public_name: str,
    impl,
    dispatcher: Callable[..., object],
) -> Callable[..., object]:
    @wraps(impl)
    def public_wrapper(*args, **kwargs):
        return dispatcher(public_name, impl, *args, **kwargs)

    return public_wrapper


def install_tool_runtime_registry_public_wrappers(
    namespace: MutableMapping[str, object],
    wrapper_specs: Sequence[PublicWrapperSpec] = _PUBLIC_WRAPPER_SPECS,
) -> None:
    dispatcher = make_tool_runtime_registry_public_dispatcher(namespace)
    namespace["_call_public_or_impl"] = dispatcher
    for public_name, impl_name in wrapper_specs:
        namespace[public_name] = _make_public_wrapper(
            public_name,
            namespace[impl_name],
            dispatcher,
        )
