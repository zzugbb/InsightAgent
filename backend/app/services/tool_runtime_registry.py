from __future__ import annotations

import json

from collections.abc import Mapping, Sequence

from dataclasses import replace
from functools import wraps

from pathlib import Path

from types import SimpleNamespace

from typing import Callable

from app.config import get_settings

from app.services.tool_runtime_http_json import (
    _build_invalid_tool_execution_diagnostics,
    _build_tool_execution_runtime_template_context,
    _build_tool_execution_summary_from_spec,
    _build_tool_runner_from_execution_spec,
    _clone_tool_execution_settings,
    _coerce_tool_default_timeout_ms,
    _coerce_tool_execution_string_like_value,
    _collect_invalid_tool_execution_messages_from_extra_tool_specs,
    _collect_invalid_tool_execution_messages_from_override_specs,
    _describe_tool_default_timeout_ms_validation_error,
    _describe_tool_execution_spec_validation_errors,
    _normalize_runtime_semantic_kind,
    _normalize_safe_explicit_result_keys,
    _redact_tool_registry_diagnostic_value,
    _resolve_tool_execution_kind_from_spec,
    build_tool_registry_settings_execution_diagnostics,
    sanitize_tool_execution_diagnostics,
    sanitize_tool_execution_summary,
)

from app.services.tool_runtime_execution import (
    build_tool_registry,
    build_tool_registry_provider,
    build_tool_trace_event,
)

def _runtime_module():
    from app.services import tool_runtime

    return tool_runtime


def _proxy(name: str):
    return getattr(_runtime_module(), name)


def _call_runtime(attr_name: str, *args, **kwargs):
    return _proxy(attr_name)(*args, **kwargs)

ConfiguredToolRegistryProviderPreflightResultModel = _proxy("ConfiguredToolRegistryProviderPreflightResultModel")
ConfiguredToolRegistryProviderPreflightSummaryModel = _proxy("ConfiguredToolRegistryProviderPreflightSummaryModel")
ConfiguredToolRegistryProviderRuntimeArtifactsModel = _proxy("ConfiguredToolRegistryProviderRuntimeArtifactsModel")
ConfiguredToolRegistryProviderRuntimeServiceActionModel = _proxy("ConfiguredToolRegistryProviderRuntimeServiceActionModel")
ConfiguredToolRegistryProviderRuntimeServiceActionsModel = _proxy("ConfiguredToolRegistryProviderRuntimeServiceActionsModel")
ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel = _proxy("ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel")
ConfiguredToolRegistryProviderServiceExecutionModel = _proxy("ConfiguredToolRegistryProviderServiceExecutionModel")
ConfiguredToolRegistryProviderServiceExecutionResultModel = _proxy("ConfiguredToolRegistryProviderServiceExecutionResultModel")
StaticToolRegistryProvider = _proxy("StaticToolRegistryProvider")
ToolRegistration = _proxy("ToolRegistration")
ToolRegistryDiagnosticsRuntimeArtifactsModel = _proxy("ToolRegistryDiagnosticsRuntimeArtifactsModel")
ToolRegistryDiagnosticsSummaryModel = _proxy("ToolRegistryDiagnosticsSummaryModel")
ToolRegistryLoader = _proxy("ToolRegistryLoader")
ToolRegistryLoaderFactory = _proxy("ToolRegistryLoaderFactory")
ToolRegistryProvider = _proxy("ToolRegistryProvider")
ToolRegistryProviderFactory = _proxy("ToolRegistryProviderFactory")
ToolRegistrySettingsConfig = _proxy("ToolRegistrySettingsConfig")
_REGISTERED_TOOLS = _proxy("_REGISTERED_TOOLS")
_TOOL_REGISTRY_FACTORY_ADAPTER_KEYS = _proxy("_TOOL_REGISTRY_FACTORY_ADAPTER_KEYS")
_TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS = _proxy("_TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS")
_TOOL_REGISTRY_LOADER_ADAPTER_KEYS = _proxy("_TOOL_REGISTRY_LOADER_ADAPTER_KEYS")
_TOOL_REGISTRY_PROFILE_CONFIGS = _proxy("_TOOL_REGISTRY_PROFILE_CONFIGS")
_TOOL_REGISTRY_PROVIDER_ADAPTER_KEYS = _proxy("_TOOL_REGISTRY_PROVIDER_ADAPTER_KEYS")

def _annotate_loader_factory_profile(*args, **kwargs):
    return _call_runtime("_annotate_loader_factory_profile", *args, **kwargs)

def _annotate_provider_factory_profile(*args, **kwargs):
    return _call_runtime("_annotate_provider_factory_profile", *args, **kwargs)

def _clone_tool_registry_provider_source_scoped_settings(*args, **kwargs):
    return _call_runtime("_clone_tool_registry_provider_source_scoped_settings", *args, **kwargs)

def _coerce_tool_registry_spec_payload(*args, **kwargs):
    return _call_runtime("_coerce_tool_registry_spec_payload", *args, **kwargs)

def _find_tool_registry_provider_source_reference_cycle_edges(*args, **kwargs):
    return _call_runtime("_find_tool_registry_provider_source_reference_cycle_edges", *args, **kwargs)

def _is_non_text_sequence(*args, **kwargs):
    return _call_runtime("_is_non_text_sequence", *args, **kwargs)

def _merge_inline_tool_registry_extra_tool_specs(*args, **kwargs):
    return _call_runtime("_merge_inline_tool_registry_extra_tool_specs", *args, **kwargs)

def _normalize_named_tool_registry_component_name(*args, **kwargs):
    return _call_runtime("_normalize_named_tool_registry_component_name", *args, **kwargs)

def _order_tool_registry_factory_specs(*args, **kwargs):
    return _call_runtime("_order_tool_registry_factory_specs", *args, **kwargs)

def _order_tool_registry_loader_specs(*args, **kwargs):
    return _call_runtime("_order_tool_registry_loader_specs", *args, **kwargs)

def _order_tool_registry_provider_source_specs(*args, **kwargs):
    return _call_runtime("_order_tool_registry_provider_source_specs", *args, **kwargs)

def _order_tool_registry_provider_specs(*args, **kwargs):
    return _call_runtime("_order_tool_registry_provider_specs", *args, **kwargs)

def _parse_tool_registry_json_object_setting(*args, **kwargs):
    return _call_runtime("_parse_tool_registry_json_object_setting", *args, **kwargs)

def _sanitize_tool_runtime_trace_artifact_payload(*args, **kwargs):
    return _call_runtime("_sanitize_tool_runtime_trace_artifact_payload", *args, **kwargs)

def build_configured_tool_registry_provider_preflight_tool_details(*args, **kwargs):
    return _call_runtime("build_configured_tool_registry_provider_preflight_tool_details", *args, **kwargs)

def build_tool_registry_extra_tools_from_specs(*args, **kwargs):
    return _call_runtime("build_tool_registry_extra_tools_from_specs", *args, **kwargs)

def build_tool_registry_profile_settings_config(*args, **kwargs):
    return _call_runtime("build_tool_registry_profile_settings_config", *args, **kwargs)

def get_default_tool_registry(*args, **kwargs):
    return _call_runtime("get_default_tool_registry", *args, **kwargs)

def get_default_tool_registry_provider(*args, **kwargs):
    return _call_runtime("get_default_tool_registry_provider", *args, **kwargs)

def get_tool_registry_profile_name_from_settings(*args, **kwargs):
    return _call_runtime("get_tool_registry_profile_name_from_settings", *args, **kwargs)

def get_tool_registry_provider_source_name_from_settings(*args, **kwargs):
    return _call_runtime("get_tool_registry_provider_source_name_from_settings", *args, **kwargs)

def get_tool_registry_provider_source_specs_from_settings(*args, **kwargs):
    return _call_runtime("get_tool_registry_provider_source_specs_from_settings", *args, **kwargs)

def load_tool_registry(*args, **kwargs):
    return _call_runtime("load_tool_registry", *args, **kwargs)

def normalize_tool_registry_name(*args, **kwargs):
    return _call_runtime("normalize_tool_registry_name", *args, **kwargs)

def normalize_tool_registry_names(*args, **kwargs):
    return _call_runtime("normalize_tool_registry_names", *args, **kwargs)

def resolve_named_tool_registry_loader(*args, **kwargs):
    return _call_runtime("resolve_named_tool_registry_loader", *args, **kwargs)

def resolve_named_tool_registry_loader_factory(*args, **kwargs):
    return _call_runtime("resolve_named_tool_registry_loader_factory", *args, **kwargs)

def resolve_named_tool_registry_provider_factory(*args, **kwargs):
    return _call_runtime("resolve_named_tool_registry_provider_factory", *args, **kwargs)

def resolve_named_tool_registry_provider_reference(*args, **kwargs):
    return _call_runtime("resolve_named_tool_registry_provider_reference", *args, **kwargs)

def __getattr__(name: str):
    return _proxy(name)


_ACTIVE_PUBLIC_PROXY_NAMES: set[str] = set()


def _impl_build_tool_registry_extra_tools_from_file(
    *,
    registry_file: str,
    settings: object | None = None,
) -> dict[str, ToolRegistration]:
    payload = _coerce_tool_registry_spec_payload(
        load_tool_registry_file_payload(registry_file=registry_file)
    )
    if not isinstance(payload, Mapping):
        return {}
    if isinstance(payload.get("extra_tools"), Mapping):
        payload = payload["extra_tools"]
    return build_tool_registry_extra_tools_from_specs(
        extra_tool_specs=payload,
        settings=settings,
    )


def _impl__resolve_tool_registry_file_path(
    *,
    registry_file: str,
    base_dir: Path | None = None,
) -> Path | None:
    normalized_path = registry_file.strip()
    if not normalized_path:
        return None
    path = Path(normalized_path).expanduser()
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path
    return path.resolve()


def _impl__resolve_tool_registry_dir_path(
    *,
    registry_dir: str,
    base_dir: Path | None = None,
) -> Path | None:
    normalized_path = registry_dir.strip()
    if not normalized_path:
        return None
    path = Path(normalized_path).expanduser()
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path
    return path.resolve()


def _impl_load_tool_registry_file_payload(
    *,
    registry_file: str,
    base_dir: Path | None = None,
) -> dict[str, object] | None:
    resolved_path = _resolve_tool_registry_file_path(
        registry_file=registry_file,
        base_dir=base_dir,
    )
    if resolved_path is None:
        return None
    try:
        raw_payload = resolved_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _impl__normalize_tool_registry_file_diagnostics(
    diagnostics: dict[str, list[str]],
) -> dict[str, tuple[str, ...]]:
    return {
        key: tuple(value)
        for key, value in diagnostics.items()
    }


def _impl__empty_tool_registry_file_diagnostics() -> dict[str, tuple[str, ...]]:
    return {key: () for key in _TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS}


def _impl__has_tool_registry_file_diagnostics(
    diagnostics: Mapping[str, tuple[str, ...]] | None,
) -> bool:
    if not isinstance(diagnostics, Mapping):
        return False
    for key in _TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS:
        values = diagnostics.get(key, ())
        if isinstance(values, (list, tuple)) and values:
            return True
    return False


def _impl__merge_tool_registry_file_diagnostics(
    *diagnostics: dict[str, tuple[str, ...]] | None,
) -> dict[str, tuple[str, ...]]:
    merged: dict[str, list[str]] = {
        key: [] for key in _TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS
    }
    for diagnostic_group in diagnostics:
        if not isinstance(diagnostic_group, dict):
            continue
        for key in _TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS:
            values = diagnostic_group.get(key, ())
            if not isinstance(values, (list, tuple)):
                continue
            for value in values:
                safe_value = _redact_tool_registry_diagnostic_value(value)
                if not safe_value or safe_value in merged[key]:
                    continue
                merged[key].append(safe_value)
    return _normalize_tool_registry_file_diagnostics(merged)


def _impl_sanitize_tool_registry_file_diagnostics(
    diagnostics: object,
) -> dict[str, tuple[str, ...]]:
    if not isinstance(diagnostics, dict):
        return _empty_tool_registry_file_diagnostics()
    sanitized: dict[str, list[str]] = {
        key: [] for key in _TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS
    }
    for key in _TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS:
        values = diagnostics.get(key, ())
        if not isinstance(values, (list, tuple)):
            continue
        for raw_value in values:
            safe_value = _redact_tool_registry_diagnostic_value(raw_value)
            if not safe_value or safe_value in sanitized[key]:
                continue
            sanitized[key].append(safe_value)
    return _normalize_tool_registry_file_diagnostics(sanitized)


def _impl_sanitize_tool_registry_source_diagnostics(
    source_diagnostics: object,
) -> dict[str, dict[str, tuple[str, ...]]]:
    if not isinstance(source_diagnostics, dict):
        return {}
    sanitized: dict[str, dict[str, tuple[str, ...]]] = {}
    for source_name, diagnostics in source_diagnostics.items():
        normalized_source_name = str(source_name).strip()
        if not normalized_source_name:
            continue
        sanitized[normalized_source_name] = sanitize_tool_registry_file_diagnostics(
            diagnostics
        )
    return sanitized


def _impl_sanitize_tool_registry_diagnostics_summary_entries(
    entries: object,
) -> tuple[dict[str, object], ...]:
    if not isinstance(entries, (list, tuple)):
        return ()
    sanitized_entries: list[dict[str, object]] = []
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            continue
        sanitized_entry: dict[str, object] = {}
        safe_values: tuple[str, ...] | None = None
        for key, value in raw_entry.items():
            if key == "values" and isinstance(value, (list, tuple)):
                safe_values = tuple(
                    safe_value
                    for safe_value in (
                        _redact_tool_registry_diagnostic_value(raw_value)
                        for raw_value in value
                    )
                    if safe_value
                )
                sanitized_entry[key] = safe_values
                continue
            sanitized_entry[key] = sanitize_tool_registry_diagnostics_artifact_payload(
                value
            )
        if safe_values is not None:
            sanitized_entry["count"] = len(safe_values)
        sanitized_entries.append(sanitized_entry)
    return tuple(sanitized_entries)


def _impl_sanitize_tool_registry_diagnostics_artifact_payload(payload: object) -> object:
    if isinstance(payload, dict):
        sanitized: dict[object, object] = {}
        for key, value in payload.items():
            if key == "entries":
                sanitized[key] = sanitize_tool_registry_diagnostics_summary_entries(
                    value
                )
                continue
            sanitized[key] = sanitize_tool_registry_diagnostics_artifact_payload(value)
        return sanitized
    if isinstance(payload, tuple):
        return tuple(
            sanitize_tool_registry_diagnostics_artifact_payload(value)
            for value in payload
        )
    if isinstance(payload, list):
        return [
            sanitize_tool_registry_diagnostics_artifact_payload(value)
            for value in payload
        ]
    if isinstance(payload, str):
        return _redact_tool_registry_diagnostic_value(payload)
    return payload


def _impl__filter_tool_registry_json_object_setting_for_visited_registry_files(
    *,
    raw_value: object,
    visited_files: set[str],
    base_dir: Path | None = None,
) -> tuple[object, bool, tuple[str, ...]]:
    specs = _parse_tool_registry_json_object_setting(raw_value)
    if specs is None:
        return raw_value, False, ()

    filtered_specs: dict[str, object] = {}
    skipped_component_names: list[str] = []
    changed = False
    for component_name, spec in specs.items():
        spec = _coerce_tool_registry_spec_payload(spec)
        if not isinstance(component_name, str) or not isinstance(spec, Mapping):
            continue
        spec = dict(spec)
        registry_file = spec.get("registry_file")
        if isinstance(registry_file, str) and registry_file.strip():
            resolved_path = _resolve_tool_registry_file_path(
                registry_file=registry_file,
                base_dir=base_dir,
            )
            if resolved_path is not None and str(resolved_path) in visited_files:
                changed = True
                skipped_component_names.append(component_name)
                continue
            if (
                resolved_path is not None
                and base_dir is not None
                and not Path(registry_file.strip()).expanduser().is_absolute()
            ):
                spec["registry_file"] = str(resolved_path)
                changed = True
        filtered_specs[component_name] = spec
    if not changed:
        return raw_value, False, ()
    try:
        return (
            json.dumps(filtered_specs, ensure_ascii=False),
            True,
            tuple(skipped_component_names),
        )
    except TypeError:
        return raw_value, False, ()


def _impl__clone_tool_registry_settings_without_visited_registry_file_components(
    *,
    settings: object | None,
    visited_files: set[str],
    base_dir: Path | None = None,
) -> tuple[object | None, dict[str, tuple[str, ...]]]:
    if not visited_files and base_dir is None:
        return settings, {}

    updates: dict[str, object] = {}
    skipped_components_by_kind: dict[str, list[str]] = {}
    component_setting_attrs = (
        ("tool_registry_loaders_json", "loader"),
        ("tool_registry_loader_factories_json", "loader_factory"),
        ("tool_registry_providers_json", "provider"),
        ("tool_registry_provider_factories_json", "provider_factory"),
        ("tool_registry_provider_sources_json", "provider_source"),
    )
    for attr_name, component_kind in component_setting_attrs:
        raw_value = getattr(settings, attr_name, None)
        filtered_value, changed, raw_skipped_component_names = (
            _filter_tool_registry_json_object_setting_for_visited_registry_files(
                raw_value=raw_value,
                visited_files=visited_files,
                base_dir=base_dir,
            )
        )
        if raw_skipped_component_names:
            normalized_names: list[str] = []
            for skipped_component_name in raw_skipped_component_names:
                if component_kind == "provider_source":
                    normalized_name = get_tool_registry_provider_source_name_from_settings(
                        settings=SimpleNamespace(
                            tool_registry_provider_source=skipped_component_name,
                        )
                    )
                else:
                    normalized_name = _normalize_named_tool_registry_component_name(
                        skipped_component_name
                    )
                if normalized_name and normalized_name not in normalized_names:
                    normalized_names.append(normalized_name)
            if normalized_names:
                skipped_components_by_kind.setdefault(component_kind, []).extend(
                    normalized_names
                )
        if not changed:
            continue
        updates[attr_name] = filtered_value
    if not updates:
        return settings, {
            kind: tuple(names)
            for kind, names in skipped_components_by_kind.items()
        }
    return (
        _clone_tool_execution_settings(
            settings=settings or SimpleNamespace(),
            **updates,
        ),
        {
            kind: tuple(names)
            for kind, names in skipped_components_by_kind.items()
        },
    )


def _impl__expand_skipped_registry_file_component_names(
    *,
    settings: object | None,
    skipped_component_names: Mapping[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    expanded_names: dict[str, set[str]] = {
        kind: set(names)
        for kind, names in skipped_component_names.items()
    }

    def add_component_name(kind: str, name: object) -> bool:
        if kind == "provider_source":
            normalized_name = get_tool_registry_provider_source_name_from_settings(
                settings=SimpleNamespace(tool_registry_provider_source=name)
            )
        else:
            normalized_name = _normalize_named_tool_registry_component_name(name)
        if not normalized_name:
            return False
        names = expanded_names.setdefault(kind, set())
        if normalized_name in names:
            return False
        names.add(normalized_name)
        return True

    def references_skipped_component(
        *,
        spec: Mapping[str, object],
        reference_key: str,
        skipped_kind: str,
    ) -> bool:
        if skipped_kind == "provider_source":
            normalized_reference = get_tool_registry_provider_source_name_from_settings(
                settings=SimpleNamespace(
                    tool_registry_provider_source=spec.get(reference_key),
                )
            )
        else:
            normalized_reference = _normalize_named_tool_registry_component_name(
                spec.get(reference_key)
            )
        return bool(
            normalized_reference
            and normalized_reference in expanded_names.get(skipped_kind, set())
        )

    loader_specs = _parse_tool_registry_json_object_setting(
        getattr(settings, "tool_registry_loaders_json", None)
    ) or {}
    loader_factory_specs = _parse_tool_registry_json_object_setting(
        getattr(settings, "tool_registry_loader_factories_json", None)
    ) or {}
    provider_specs = _parse_tool_registry_json_object_setting(
        getattr(settings, "tool_registry_providers_json", None)
    ) or {}
    provider_factory_specs = _parse_tool_registry_json_object_setting(
        getattr(settings, "tool_registry_provider_factories_json", None)
    ) or {}
    source_specs = get_tool_registry_provider_source_specs_from_settings(
        settings=settings,
    )

    changed = True
    while changed:
        changed = False
        for factory_name, spec in loader_factory_specs.items():
            spec = _coerce_tool_registry_spec_payload(spec)
            if not isinstance(spec, Mapping):
                continue
            if references_skipped_component(
                spec=spec,
                reference_key="factory",
                skipped_kind="loader_factory",
            ):
                changed = add_component_name("loader_factory", factory_name) or changed
        for factory_name, spec in provider_factory_specs.items():
            spec = _coerce_tool_registry_spec_payload(spec)
            if not isinstance(spec, Mapping):
                continue
            if references_skipped_component(
                spec=spec,
                reference_key="factory",
                skipped_kind="provider_factory",
            ):
                changed = add_component_name("provider_factory", factory_name) or changed
        for loader_name, spec in loader_specs.items():
            spec = _coerce_tool_registry_spec_payload(spec)
            if not isinstance(spec, Mapping):
                continue
            if references_skipped_component(
                spec=spec,
                reference_key="loader",
                skipped_kind="loader",
            ) or references_skipped_component(
                spec=spec,
                reference_key="loader_factory",
                skipped_kind="loader_factory",
            ):
                changed = add_component_name("loader", loader_name) or changed
        for provider_name, spec in provider_specs.items():
            spec = _coerce_tool_registry_spec_payload(spec)
            if not isinstance(spec, Mapping):
                continue
            if (
                references_skipped_component(
                    spec=spec,
                    reference_key="provider",
                    skipped_kind="provider",
                )
                or references_skipped_component(
                    spec=spec,
                    reference_key="provider",
                    skipped_kind="provider_source",
                )
                or references_skipped_component(
                    spec=spec,
                    reference_key="provider_factory",
                    skipped_kind="provider_factory",
                )
                or references_skipped_component(
                    spec=spec,
                    reference_key="loader",
                    skipped_kind="loader",
                )
                or references_skipped_component(
                    spec=spec,
                    reference_key="loader_factory",
                    skipped_kind="loader_factory",
                )
            ):
                changed = add_component_name("provider", provider_name) or changed
        for source_name, spec in source_specs.items():
            if not isinstance(spec, Mapping):
                continue
            if (
                references_skipped_component(
                    spec=spec,
                    reference_key="provider",
                    skipped_kind="provider",
                )
                or references_skipped_component(
                    spec=spec,
                    reference_key="provider",
                    skipped_kind="provider_source",
                )
                or references_skipped_component(
                    spec=spec,
                    reference_key="provider_factory",
                    skipped_kind="provider_factory",
                )
                or references_skipped_component(
                    spec=spec,
                    reference_key="loader",
                    skipped_kind="loader",
                )
                or references_skipped_component(
                    spec=spec,
                    reference_key="loader_factory",
                    skipped_kind="loader_factory",
                )
            ):
                changed = add_component_name("provider_source", source_name) or changed
    return {
        kind: tuple(sorted(names))
        for kind, names in expanded_names.items()
    }


def _impl__build_tool_registry_from_file_registry(
    *,
    registry_file: str,
    settings: object | None = None,
    provider_source_name: str | None = None,
    _visited_files: set[str],
    _visited_dirs: set[str],
    _visited_sources: set[str],
    _diagnostics: dict[str, list[str]],
) -> dict[str, ToolRegistration]:
    resolved_path = _resolve_tool_registry_file_path(registry_file=registry_file)
    if resolved_path is None:
        return {}
    resolved_path_key = str(resolved_path)
    if not resolved_path.is_file():
        _diagnostics["missing_registry_files"].append(resolved_path_key)
        return {}
    if resolved_path_key in _visited_files:
        _diagnostics["skipped_registry_files"].append(resolved_path_key)
        return {}
    _visited_files.add(resolved_path_key)
    payload = _coerce_tool_registry_spec_payload(
        load_tool_registry_file_payload(registry_file=str(resolved_path))
    )
    if not isinstance(payload, Mapping):
        return {}
    payload = dict(payload)
    source_settings = _clone_tool_registry_provider_source_scoped_settings(
        settings=settings,
        provider_source_name=provider_source_name,
    )

    manifest_keys = {
        "registry_sources",
        "registry_files",
        "registry_dirs",
        "profile",
        "disabled_tool_names",
        "overrides",
        "extra_tools",
    }
    if not any(key in payload for key in manifest_keys):
        _diagnostics["invalid_tool_executions"].extend(
            _collect_invalid_tool_execution_messages_from_extra_tool_specs(
                extra_tool_specs=payload,
                settings=source_settings,
            )
        )
        return build_tool_registry_extra_tools_from_specs(
            extra_tool_specs=payload,
            settings=source_settings,
            provider_source_name=provider_source_name,
        )

    profile_name = get_tool_registry_profile_name_from_settings(
        settings=SimpleNamespace(
            tool_registry_profile=payload.get(
                "profile",
                (
                    getattr(source_settings, "tool_registry_profile", None)
                    if provider_source_name
                    else None
                )
                or "default",
            ),
        )
    )
    source_settings = _clone_tool_registry_provider_source_scoped_settings(
        settings=source_settings,
        provider_source_name=provider_source_name,
        profile_name=profile_name,
    )
    profile_config = build_tool_registry_profile_settings_config(profile_name=profile_name)
    disabled_tool_names = set(normalize_tool_registry_names(profile_config.disabled_tool_names))
    raw_disabled_tool_names = payload.get("disabled_tool_names")
    if _is_non_text_sequence(raw_disabled_tool_names):
        disabled_tool_names.update(normalize_tool_registry_names(raw_disabled_tool_names))

    composed_base_registry: dict[str, ToolRegistration] | None = None
    raw_registry_sources = payload.get("registry_sources")
    if _is_non_text_sequence(raw_registry_sources):
        composed_base_registry = {}
        (
            registry_source_settings,
            skipped_registry_component_names,
        ) = (
            _clone_tool_registry_settings_without_visited_registry_file_components(
                settings=source_settings,
                visited_files=_visited_files,
                base_dir=resolved_path.parent,
            )
        )
        skipped_registry_component_names = _expand_skipped_registry_file_component_names(
            settings=source_settings,
            skipped_component_names=skipped_registry_component_names,
        )
        skipped_provider_sources = set(
            skipped_registry_component_names.get("provider_source", ())
        )
        source_artifacts = build_tool_registry_provider_sources_from_settings_artifacts(
            settings=registry_source_settings,
        )
        named_sources = source_artifacts["sources"]
        source_diagnostics = source_artifacts["source_diagnostics"]
        for child_registry_source in raw_registry_sources:
            child_registry_source = _coerce_tool_execution_string_like_value(
                child_registry_source
            )
            if (
                not isinstance(child_registry_source, str)
                or not child_registry_source.strip()
            ):
                continue
            normalized_source_name = get_tool_registry_provider_source_name_from_settings(
                settings=SimpleNamespace(
                    tool_registry_provider_source=child_registry_source,
                )
            )
            if normalized_source_name in skipped_provider_sources:
                _diagnostics["skipped_registry_sources"].append(normalized_source_name)
                continue
            if normalized_source_name in _visited_sources:
                _diagnostics["skipped_registry_sources"].append(normalized_source_name)
                continue
            source_provider = named_sources.get(normalized_source_name)
            source_diagnostic_values = source_diagnostics.get(normalized_source_name, {})
            source_has_skipped_diagnostics = False
            if isinstance(source_diagnostic_values, dict):
                for diagnostic_key in _TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS:
                    diagnostic_values = source_diagnostic_values.get(diagnostic_key, ())
                    if not isinstance(diagnostic_values, (list, tuple)):
                        continue
                    if diagnostic_key.startswith("skipped_") and diagnostic_values:
                        source_has_skipped_diagnostics = True
                    _diagnostics[diagnostic_key].extend(
                        str(value)
                        for value in diagnostic_values
                        if str(value).strip()
                    )
            if source_provider is None:
                if source_has_skipped_diagnostics:
                    _diagnostics["skipped_registry_sources"].append(
                        normalized_source_name
                    )
                    continue
                _diagnostics["missing_registry_sources"].append(normalized_source_name)
                continue
            _visited_sources.add(normalized_source_name)
            child_registry = source_provider.load_tool_registry()
            if not child_registry:
                continue
            composed_base_registry = build_tool_registry(
                base_registry=composed_base_registry,
                overrides=child_registry,
            )
    raw_registry_files = payload.get("registry_files")
    if _is_non_text_sequence(raw_registry_files):
        if composed_base_registry is None:
            composed_base_registry = {}
        for child_registry_file in raw_registry_files:
            child_registry_file = _coerce_tool_execution_string_like_value(
                child_registry_file
            )
            if not isinstance(child_registry_file, str) or not child_registry_file.strip():
                continue
            resolved_child_file = _resolve_tool_registry_file_path(
                registry_file=child_registry_file,
                base_dir=resolved_path.parent,
            )
            if resolved_child_file is None:
                continue
            resolved_child_file_key = str(resolved_child_file)
            if not resolved_child_file.is_file():
                _diagnostics["missing_registry_files"].append(resolved_child_file_key)
                continue
            child_registry = _build_tool_registry_from_file_registry(
                registry_file=str(resolved_child_file),
                settings=source_settings,
                provider_source_name=provider_source_name,
                _visited_files=_visited_files,
                _visited_dirs=_visited_dirs,
                _visited_sources=_visited_sources,
                _diagnostics=_diagnostics,
            )
            if not child_registry:
                continue
            composed_base_registry = build_tool_registry(
                base_registry=composed_base_registry,
                overrides=child_registry,
            )
    raw_registry_dirs = payload.get("registry_dirs")
    if _is_non_text_sequence(raw_registry_dirs):
        if composed_base_registry is None:
            composed_base_registry = {}
        for child_registry_dir in raw_registry_dirs:
            child_registry_dir = _coerce_tool_execution_string_like_value(
                child_registry_dir
            )
            if not isinstance(child_registry_dir, str) or not child_registry_dir.strip():
                continue
            resolved_dir = _resolve_tool_registry_dir_path(
                registry_dir=child_registry_dir,
                base_dir=resolved_path.parent,
            )
            if resolved_dir is None:
                continue
            resolved_dir_key = str(resolved_dir)
            if not resolved_dir.is_dir():
                _diagnostics["missing_registry_dirs"].append(resolved_dir_key)
                continue
            if resolved_dir_key in _visited_dirs:
                _diagnostics["skipped_registry_dirs"].append(resolved_dir_key)
                continue
            _visited_dirs.add(resolved_dir_key)
            for child_file in sorted(resolved_dir.iterdir(), key=lambda path: path.name):
                if not child_file.is_file() or child_file.suffix.lower() != ".json":
                    continue
                child_registry = _build_tool_registry_from_file_registry(
                    registry_file=str(child_file),
                    settings=source_settings,
                    provider_source_name=provider_source_name,
                    _visited_files=_visited_files,
                    _visited_dirs=_visited_dirs,
                    _visited_sources=_visited_sources,
                    _diagnostics=_diagnostics,
                )
                if not child_registry:
                    continue
                composed_base_registry = build_tool_registry(
                    base_registry=composed_base_registry,
                    overrides=child_registry,
                )

    extra_tool_specs = payload.get("extra_tools")
    extra_tool_specs = _coerce_tool_registry_spec_payload(extra_tool_specs)
    if not isinstance(extra_tool_specs, Mapping):
        extra_tool_specs = payload
    _diagnostics["invalid_tool_executions"].extend(
        _collect_invalid_tool_execution_messages_from_extra_tool_specs(
            extra_tool_specs=extra_tool_specs,
            settings=source_settings,
        )
    )
    extra_tools = build_tool_registry_extra_tools_from_specs(
        extra_tool_specs=extra_tool_specs,
        settings=source_settings,
        provider_source_name=provider_source_name,
    )

    base_registry = build_tool_registry(
        base_registry=(
            composed_base_registry
            if composed_base_registry is not None
            else get_default_tool_registry()
        ),
        overrides=extra_tools or None,
    )
    _diagnostics["invalid_tool_executions"].extend(
        _collect_invalid_tool_execution_messages_from_override_specs(
            override_specs=payload.get("overrides"),
            base_registry=base_registry,
            settings=source_settings,
        )
    )
    source_overrides, disabled_tool_names = _build_registry_overrides_from_specs(
        override_specs=payload.get("overrides"),
        base_registry=base_registry,
        disabled_tool_names=disabled_tool_names,
        settings=source_settings,
    )
    return build_tool_registry(
        base_registry=base_registry,
        overrides=build_tool_registry(
            base_registry=profile_config.overrides,
            overrides=source_overrides or None,
        )
        or None,
        disabled_tool_names=tuple(sorted(disabled_tool_names)),
    )


def _impl_build_tool_registry_from_file_artifacts(
    *,
    registry_file: str,
    settings: object | None = None,
    provider_source_name: str | None = None,
) -> dict[str, object]:
    diagnostics: dict[str, list[str]] = {
        "skipped_registry_sources": [],
        "missing_registry_sources": [],
        "skipped_registry_files": [],
        "missing_registry_files": [],
        "skipped_registry_dirs": [],
        "missing_registry_dirs": [],
        "invalid_tool_executions": [],
    }
    registry = _build_tool_registry_from_file_registry(
        registry_file=registry_file,
        settings=settings,
        provider_source_name=provider_source_name,
        _visited_files=set(),
        _visited_dirs=set(),
        _visited_sources=set(),
        _diagnostics=diagnostics,
    )
    return {
        "registry": registry,
        "diagnostics": _normalize_tool_registry_file_diagnostics(diagnostics),
    }


def _impl_build_tool_registry_loader_from_file_artifacts(
    *,
    registry_file: str,
    settings: object | None = None,
    provider_source_name: str | None = None,
) -> dict[str, object]:
    artifacts = build_tool_registry_from_file_artifacts(
        registry_file=registry_file,
        settings=settings,
        provider_source_name=provider_source_name,
    )
    registry = dict(artifacts["registry"])
    loader = (lambda registry=registry: dict(registry)) if registry else None
    return {
        "loader": loader,
        "registry": registry,
        "diagnostics": artifacts["diagnostics"],
    }


def _impl_build_tool_registry_provider_from_file_artifacts(
    *,
    registry_file: str,
    settings: object | None = None,
    provider_source_name: str | None = None,
) -> dict[str, object]:
    artifacts = build_tool_registry_loader_from_file_artifacts(
        registry_file=registry_file,
        settings=settings,
        provider_source_name=provider_source_name,
    )
    loader = artifacts["loader"]
    registry = dict(artifacts["registry"])
    provider = StaticToolRegistryProvider(registry=registry) if loader is not None else None
    return {
        "provider": provider,
        "registry": registry,
        "diagnostics": artifacts["diagnostics"],
    }


def _impl_build_tool_registry_from_file(
    *,
    registry_file: str,
    settings: object | None = None,
    provider_source_name: str | None = None,
) -> dict[str, ToolRegistration]:
    artifacts = build_tool_registry_from_file_artifacts(
        registry_file=registry_file,
        settings=settings,
        provider_source_name=provider_source_name,
    )
    return dict(artifacts["registry"])


def _impl_build_tool_registry_loader_from_file(
    *,
    registry_file: str,
    settings: object | None = None,
    provider_source_name: str | None = None,
) -> ToolRegistryLoader | None:
    artifacts = build_tool_registry_loader_from_file_artifacts(
        registry_file=registry_file,
        settings=settings,
        provider_source_name=provider_source_name,
    )
    return artifacts["loader"]


def _impl_build_tool_registry_provider_from_file(
    *,
    registry_file: str,
    settings: object | None = None,
    provider_source_name: str | None = None,
) -> ToolRegistryProvider | None:
    artifacts = build_tool_registry_provider_from_file_artifacts(
        registry_file=registry_file,
        settings=settings,
        provider_source_name=provider_source_name,
    )
    return artifacts["provider"]


def _impl__build_tool_registry_loader_factory_adapter(
    *,
    factory: ToolRegistryLoaderFactory,
    spec: dict[str, object],
) -> ToolRegistryLoaderFactory:
    factory_spec = dict(spec)

    def loader_factory(settings: object | None = None) -> ToolRegistryLoader:
        base_loader = factory(settings)
        profile_name_hint = getattr(factory, "_tool_registry_profile_name", None)
        known_base_registry = (
            get_default_tool_registry()
            if profile_name_hint
            else dict(base_loader())
        )
        implicit_profile_name = (
            get_tool_registry_profile_name_from_settings(
                settings=SimpleNamespace(
                    tool_registry_profile=profile_name_hint,
                )
            )
            if profile_name_hint
            else "default"
        )
        profile_name = get_tool_registry_profile_name_from_settings(
            settings=SimpleNamespace(
                tool_registry_profile=factory_spec.get("profile", implicit_profile_name),
            )
        )
        profile_config = build_tool_registry_profile_settings_config(
            profile_name=profile_name
        )
        disabled_tool_names = set(
            normalize_tool_registry_names(profile_config.disabled_tool_names)
        )
        raw_disabled_tool_names = factory_spec.get("disabled_tool_names")
        if _is_non_text_sequence(raw_disabled_tool_names):
            disabled_tool_names.update(normalize_tool_registry_names(raw_disabled_tool_names))

        extra_tools = build_tool_registry_extra_tools_from_specs(
            extra_tool_specs=factory_spec.get("extra_tools"),
            settings=settings,
        )
        base_registry = build_tool_registry(
            base_registry=known_base_registry,
            overrides=extra_tools or None,
        )
        source_overrides, disabled_tool_names = _build_registry_overrides_from_specs(
            override_specs=factory_spec.get("overrides"),
            base_registry=base_registry,
            disabled_tool_names=disabled_tool_names,
            settings=settings,
        )
        registry = build_tool_registry(
            base_registry=base_registry,
            overrides=build_tool_registry(
                base_registry=profile_config.overrides,
                overrides=source_overrides or None,
            )
            or None,
            disabled_tool_names=tuple(sorted(disabled_tool_names)),
        )
        return lambda: dict(registry)

    if (
        "profile" not in factory_spec
        and getattr(factory, "_tool_registry_profile_name", None)
    ):
        return _annotate_loader_factory_profile(
            loader_factory,
            profile_name=str(getattr(factory, "_tool_registry_profile_name")),
        )
    return loader_factory


def _impl__build_tool_registry_provider_factory_adapter(
    *,
    factory: ToolRegistryProviderFactory,
    spec: dict[str, object],
) -> ToolRegistryProviderFactory:
    factory_spec = dict(spec)

    def provider_factory(settings: object | None = None) -> ToolRegistryProvider:
        base_provider = factory(settings)
        profile_name_hint = getattr(factory, "_tool_registry_profile_name", None)
        known_base_registry = (
            get_default_tool_registry()
            if profile_name_hint
            else dict(base_provider.load_tool_registry())
        )
        implicit_profile_name = (
            get_tool_registry_profile_name_from_settings(
                settings=SimpleNamespace(
                    tool_registry_profile=profile_name_hint,
                )
            )
            if profile_name_hint
            else "default"
        )
        profile_name = get_tool_registry_profile_name_from_settings(
            settings=SimpleNamespace(
                tool_registry_profile=factory_spec.get("profile", implicit_profile_name),
            )
        )
        profile_config = build_tool_registry_profile_settings_config(
            profile_name=profile_name
        )
        disabled_tool_names = set(
            normalize_tool_registry_names(profile_config.disabled_tool_names)
        )
        raw_disabled_tool_names = factory_spec.get("disabled_tool_names")
        if _is_non_text_sequence(raw_disabled_tool_names):
            disabled_tool_names.update(normalize_tool_registry_names(raw_disabled_tool_names))

        provider_source_name = get_tool_registry_provider_source_name_from_settings(
            settings=settings
        )
        extra_tools = build_tool_registry_extra_tools_from_specs(
            extra_tool_specs=factory_spec.get("extra_tools"),
            settings=settings,
            provider_source_name=provider_source_name,
        )
        base_registry = build_tool_registry(
            base_registry=known_base_registry,
            overrides=extra_tools or None,
        )
        source_overrides, disabled_tool_names = _build_registry_overrides_from_specs(
            override_specs=factory_spec.get("overrides"),
            base_registry=base_registry,
            disabled_tool_names=disabled_tool_names,
            settings=_clone_tool_execution_settings(
                settings=settings or SimpleNamespace(),
                tool_registry_provider_source=provider_source_name,
            ),
        )
        adapter_overrides = build_tool_registry(
            base_registry=extra_tools or {},
            overrides=source_overrides or None,
        )
        registry = build_tool_registry(
            base_registry=base_registry,
            overrides=build_tool_registry(
                base_registry=profile_config.overrides,
                overrides=adapter_overrides or None,
            ),
            disabled_tool_names=tuple(sorted(disabled_tool_names)),
        )
        return StaticToolRegistryProvider(registry=registry)

    if (
        "profile" not in factory_spec
        and getattr(factory, "_tool_registry_profile_name", None)
    ):
        return _annotate_provider_factory_profile(
            provider_factory,
            profile_name=str(getattr(factory, "_tool_registry_profile_name")),
        )
    return provider_factory


def _impl_build_tool_registry_loaders_from_settings_artifacts(
    *,
    settings: object | None = None,
) -> dict[str, object]:
    if settings is None:
        settings = get_settings()
    loader_source_name = get_tool_registry_provider_source_name_from_settings(
        settings=settings
    )
    loader_profile_name = get_tool_registry_profile_name_from_settings(
        settings=settings
    )
    loader_settings = _clone_tool_registry_provider_source_scoped_settings(
        settings=settings,
        provider_source_name=loader_source_name,
        profile_name=loader_profile_name,
    )
    raw_loaders = getattr(settings, "tool_registry_loaders_json", None)
    loader_specs = _parse_tool_registry_json_object_setting(raw_loaders)
    if loader_specs is None:
        return {
            "loaders": {},
            "loader_diagnostics": {},
        }

    loaders: dict[str, ToolRegistryLoader] = {}
    loader_diagnostics: dict[str, dict[str, tuple[str, ...]]] = {}
    for loader_name, spec in _order_tool_registry_loader_specs(loader_specs):
        spec = _coerce_tool_registry_spec_payload(spec)
        if not isinstance(loader_name, str) or not isinstance(spec, Mapping):
            continue
        spec = dict(spec)
        normalized_loader_name = _normalize_named_tool_registry_component_name(
            loader_name
        )
        if normalized_loader_name is None:
            continue
        spec = _merge_inline_tool_registry_extra_tool_specs(
            spec,
            adapter_keys=_TOOL_REGISTRY_LOADER_ADAPTER_KEYS,
        )
        diagnostics = _empty_tool_registry_file_diagnostics()
        registry_file = spec.get("registry_file")
        loader_reference = spec.get("loader")
        normalized_loader_reference = _normalize_named_tool_registry_component_name(
            loader_reference
        )
        if isinstance(registry_file, str) and registry_file.strip():
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                build_tool_registry_loader_from_file_artifacts(
                    registry_file=registry_file,
                    settings=loader_settings,
                    provider_source_name=loader_source_name,
                )["diagnostics"],
            )
        elif (
            normalized_loader_reference is not None
            and normalized_loader_reference in loader_diagnostics
        ):
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                loader_diagnostics[normalized_loader_reference],
            )
        diagnostics = _merge_tool_registry_file_diagnostics(
            diagnostics,
            _build_invalid_tool_execution_diagnostics(
                messages=_collect_invalid_tool_execution_messages_from_extra_tool_specs(
                    extra_tool_specs=spec.get("extra_tools"),
                    settings=loader_settings,
                )
            ),
        )
        loader = build_tool_registry_loader_adapter(
            spec=spec,
            settings=loader_settings,
            named_loaders=loaders,
        )
        if loader is None:
            if _has_tool_registry_file_diagnostics(diagnostics):
                loader_diagnostics[normalized_loader_name] = diagnostics
            continue
        diagnostics = _merge_tool_registry_file_diagnostics(
            diagnostics,
            _build_invalid_tool_execution_diagnostics(
                messages=_collect_invalid_tool_execution_messages_from_override_specs(
                    override_specs=spec.get("overrides"),
                    base_registry=dict(loader()),
                    settings=loader_settings,
                )
            ),
        )
        loaders[normalized_loader_name] = loader
        loader_diagnostics[normalized_loader_name] = diagnostics
    return {
        "loaders": loaders,
        "loader_diagnostics": loader_diagnostics,
    }


def _impl_build_tool_registry_loader_factories_from_settings_artifacts(
    *,
    settings: object | None = None,
) -> dict[str, object]:
    if settings is None:
        settings = get_settings()
    raw_factories = getattr(settings, "tool_registry_loader_factories_json", None)
    factory_specs = _parse_tool_registry_json_object_setting(raw_factories)
    if factory_specs is None:
        return {
            "loader_factories": {},
            "loader_factory_diagnostics": {},
        }

    factories: dict[str, ToolRegistryLoaderFactory] = {}
    factory_diagnostics: dict[str, dict[str, tuple[str, ...]]] = {}
    for factory_name, spec in _order_tool_registry_factory_specs(factory_specs):
        spec = _coerce_tool_registry_spec_payload(spec)
        if not isinstance(factory_name, str) or not isinstance(spec, Mapping):
            continue
        spec = dict(spec)
        normalized_factory_name = _normalize_named_tool_registry_component_name(
            factory_name
        )
        if normalized_factory_name is None:
            continue
        spec = _merge_inline_tool_registry_extra_tool_specs(
            spec,
            adapter_keys=_TOOL_REGISTRY_FACTORY_ADAPTER_KEYS,
        )
        diagnostics = _empty_tool_registry_file_diagnostics()
        registry_file = spec.get("registry_file")
        target_name = spec.get("factory")
        normalized_target_name = _normalize_named_tool_registry_component_name(target_name)
        if isinstance(registry_file, str) and registry_file.strip():
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                build_tool_registry_loader_from_file_artifacts(
                    registry_file=registry_file,
                    settings=settings,
                )["diagnostics"],
            )
        elif (
            normalized_target_name is not None
            and normalized_target_name in factory_diagnostics
        ):
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                factory_diagnostics[normalized_target_name],
            )
        diagnostics = _merge_tool_registry_file_diagnostics(
            diagnostics,
            _build_invalid_tool_execution_diagnostics(
                messages=_collect_invalid_tool_execution_messages_from_extra_tool_specs(
                    extra_tool_specs=spec.get("extra_tools"),
                    settings=settings,
                )
            ),
        )
        if isinstance(registry_file, str) and registry_file.strip():
            loader = build_tool_registry_loader_from_file(
                registry_file=registry_file,
                settings=settings,
            )
            if loader is None:
                if _has_tool_registry_file_diagnostics(diagnostics):
                    factory_diagnostics[normalized_factory_name] = diagnostics
                continue
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                _build_invalid_tool_execution_diagnostics(
                    messages=_collect_invalid_tool_execution_messages_from_override_specs(
                        override_specs=spec.get("overrides"),
                        base_registry=dict(loader()),
                        settings=settings,
                    )
                ),
            )
            factory_spec = dict(spec)
            factories[normalized_factory_name] = (
                lambda settings=None, factory_spec=factory_spec: (
                    build_tool_registry_loader_adapter(
                        spec=factory_spec,
                        settings=settings,
                    )
                    or (lambda: {})
                )
            )
            factory_diagnostics[normalized_factory_name] = diagnostics
            continue
        if not isinstance(target_name, str) or not target_name.strip():
            continue
        resolved = resolve_named_tool_registry_loader_factory(
            target_name,
            named_loader_factories=factories,
        )
        if resolved is None:
            if _has_tool_registry_file_diagnostics(diagnostics):
                factory_diagnostics[normalized_factory_name] = diagnostics
            continue
        target_normalized = _normalize_named_tool_registry_component_name(target_name)
        if target_normalized in _TOOL_REGISTRY_PROFILE_CONFIGS:
            resolved = _annotate_loader_factory_profile(
                resolved,
                profile_name=target_normalized,
            )
        base_loader = resolved(settings)
        profile_name_hint = getattr(resolved, "_tool_registry_profile_name", None)
        extra_tools = build_tool_registry_extra_tools_from_specs(
            extra_tool_specs=spec.get("extra_tools"),
            settings=settings,
        )
        base_registry = build_tool_registry(
            base_registry=(
                get_default_tool_registry()
                if profile_name_hint
                else dict(base_loader())
            ),
            overrides=extra_tools or None,
        )
        diagnostics = _merge_tool_registry_file_diagnostics(
            diagnostics,
            _build_invalid_tool_execution_diagnostics(
                messages=_collect_invalid_tool_execution_messages_from_override_specs(
                    override_specs=spec.get("overrides"),
                    base_registry=base_registry,
                    settings=settings,
                )
            ),
        )
        factories[normalized_factory_name] = _build_tool_registry_loader_factory_adapter(
            factory=resolved,
            spec=spec,
        )
        factory_diagnostics[normalized_factory_name] = diagnostics
    return {
        "loader_factories": factories,
        "loader_factory_diagnostics": factory_diagnostics,
    }


def _impl_build_tool_registry_loader_factories_from_settings(
    *,
    settings: object | None = None,
) -> dict[str, ToolRegistryLoaderFactory]:
    artifacts = build_tool_registry_loader_factories_from_settings_artifacts(
        settings=settings
    )
    return artifacts["loader_factories"]


def _impl_build_tool_registry_provider_factories_from_settings_artifacts(
    *,
    settings: object | None = None,
) -> dict[str, object]:
    if settings is None:
        settings = get_settings()
    raw_factories = getattr(settings, "tool_registry_provider_factories_json", None)
    factory_specs = _parse_tool_registry_json_object_setting(raw_factories)
    if factory_specs is None:
        return {
            "provider_factories": {},
            "provider_factory_diagnostics": {},
        }

    factories: dict[str, ToolRegistryProviderFactory] = {}
    factory_diagnostics: dict[str, dict[str, tuple[str, ...]]] = {}
    for factory_name, spec in _order_tool_registry_factory_specs(factory_specs):
        spec = _coerce_tool_registry_spec_payload(spec)
        if not isinstance(factory_name, str) or not isinstance(spec, Mapping):
            continue
        spec = dict(spec)
        normalized_factory_name = _normalize_named_tool_registry_component_name(
            factory_name
        )
        if normalized_factory_name is None:
            continue
        spec = _merge_inline_tool_registry_extra_tool_specs(
            spec,
            adapter_keys=_TOOL_REGISTRY_FACTORY_ADAPTER_KEYS,
        )
        diagnostics = _empty_tool_registry_file_diagnostics()
        registry_file = spec.get("registry_file")
        target_name = spec.get("factory")
        normalized_target_name = _normalize_named_tool_registry_component_name(target_name)
        if isinstance(registry_file, str) and registry_file.strip():
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                build_tool_registry_provider_from_file_artifacts(
                    registry_file=registry_file,
                    settings=settings,
                )["diagnostics"],
            )
        elif (
            normalized_target_name is not None
            and normalized_target_name in factory_diagnostics
        ):
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                factory_diagnostics[normalized_target_name],
            )
        diagnostics = _merge_tool_registry_file_diagnostics(
            diagnostics,
            _build_invalid_tool_execution_diagnostics(
                messages=_collect_invalid_tool_execution_messages_from_extra_tool_specs(
                    extra_tool_specs=spec.get("extra_tools"),
                    settings=settings,
                )
            ),
        )
        if isinstance(registry_file, str) and registry_file.strip():
            provider = build_tool_registry_provider_from_file(
                registry_file=registry_file,
                settings=settings,
            )
            if provider is None:
                if _has_tool_registry_file_diagnostics(diagnostics):
                    factory_diagnostics[normalized_factory_name] = diagnostics
                continue
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                _build_invalid_tool_execution_diagnostics(
                    messages=_collect_invalid_tool_execution_messages_from_override_specs(
                        override_specs=spec.get("overrides"),
                        base_registry=dict(provider.load_tool_registry()),
                        settings=settings,
                    )
                ),
            )
            factory_spec = dict(spec)
            factories[normalized_factory_name] = (
                lambda settings=None, factory_spec=factory_spec: (
                    build_tool_registry_provider_adapter(
                        spec=factory_spec,
                        settings=settings,
                        provider_source_name=get_tool_registry_provider_source_name_from_settings(
                            settings=settings
                        ),
                    )
                    or StaticToolRegistryProvider(registry={})
                )
            )
            factory_diagnostics[normalized_factory_name] = diagnostics
            continue
        if not isinstance(target_name, str) or not target_name.strip():
            continue
        resolved = resolve_named_tool_registry_provider_factory(
            target_name,
            named_provider_factories=factories,
        )
        if resolved is None:
            if _has_tool_registry_file_diagnostics(diagnostics):
                factory_diagnostics[normalized_factory_name] = diagnostics
            continue
        target_normalized = _normalize_named_tool_registry_component_name(target_name)
        if target_normalized in _TOOL_REGISTRY_PROFILE_CONFIGS:
            resolved = _annotate_provider_factory_profile(
                resolved,
                profile_name=target_normalized,
            )
        base_provider = resolved(settings)
        profile_name_hint = getattr(resolved, "_tool_registry_profile_name", None)
        provider_source_name = get_tool_registry_provider_source_name_from_settings(
            settings=settings
        )
        extra_tools = build_tool_registry_extra_tools_from_specs(
            extra_tool_specs=spec.get("extra_tools"),
            settings=settings,
            provider_source_name=provider_source_name,
        )
        base_registry = build_tool_registry(
            base_registry=(
                get_default_tool_registry()
                if profile_name_hint
                else dict(base_provider.load_tool_registry())
            ),
            overrides=extra_tools or None,
        )
        diagnostics = _merge_tool_registry_file_diagnostics(
            diagnostics,
            _build_invalid_tool_execution_diagnostics(
                messages=_collect_invalid_tool_execution_messages_from_override_specs(
                    override_specs=spec.get("overrides"),
                    base_registry=base_registry,
                    settings=_clone_tool_execution_settings(
                        settings=settings or SimpleNamespace(),
                        tool_registry_provider_source=provider_source_name,
                    ),
                )
            ),
        )
        factories[normalized_factory_name] = _build_tool_registry_provider_factory_adapter(
            factory=resolved,
            spec=spec,
        )
        factory_diagnostics[normalized_factory_name] = diagnostics
    return {
        "provider_factories": factories,
        "provider_factory_diagnostics": factory_diagnostics,
    }


def _impl_build_tool_registry_provider_factories_from_settings(
    *,
    settings: object | None = None,
) -> dict[str, ToolRegistryProviderFactory]:
    artifacts = build_tool_registry_provider_factories_from_settings_artifacts(
        settings=settings
    )
    return artifacts["provider_factories"]


def _impl_build_tool_registry_loader_adapter(
    *,
    spec: object,
    settings: object | None = None,
    named_loaders: dict[str, ToolRegistryLoader] | None = None,
) -> ToolRegistryLoader | None:
    spec = _coerce_tool_registry_spec_payload(spec)
    if not isinstance(spec, Mapping):
        return None
    spec = dict(spec)
    spec = _merge_inline_tool_registry_extra_tool_specs(
        spec,
        adapter_keys=_TOOL_REGISTRY_LOADER_ADAPTER_KEYS,
    )
    loader_factory_name = spec.get("loader_factory")
    loader_name = spec.get("loader")
    registry_file = spec.get("registry_file")
    known_base_registry: dict[str, ToolRegistration] | None = None
    implicit_profile_name = "default"
    if isinstance(loader_factory_name, str) and loader_factory_name.strip():
        normalized_loader_factory_name = _normalize_named_tool_registry_component_name(
            loader_factory_name
        )
        if normalized_loader_factory_name is None:
            return None
        named_loader_factories = build_tool_registry_loader_factories_from_settings(
            settings=settings
        )
        loader_factory = resolve_named_tool_registry_loader_factory(
            normalized_loader_factory_name,
            named_loader_factories=named_loader_factories,
        )
        if loader_factory is None:
            return None
        base_loader = loader_factory(settings)
        profile_name_hint = getattr(loader_factory, "_tool_registry_profile_name", None)
        if profile_name_hint:
            known_base_registry = get_default_tool_registry()
            implicit_profile_name = get_tool_registry_profile_name_from_settings(
                settings=SimpleNamespace(
                    tool_registry_profile=profile_name_hint,
                )
            )
    elif isinstance(loader_name, str) and loader_name.strip():
        base_loader = resolve_named_tool_registry_loader(loader_name)
        normalized_loader_name = _normalize_named_tool_registry_component_name(loader_name)
        if (
            base_loader is None
            and named_loaders is not None
            and normalized_loader_name is not None
        ):
            base_loader = named_loaders.get(normalized_loader_name)
        if base_loader is None:
            return None
        known_base_registry = dict(base_loader())
    elif isinstance(registry_file, str) and registry_file.strip():
        base_loader = build_tool_registry_loader_from_file(
            registry_file=registry_file,
            settings=settings,
            provider_source_name=get_tool_registry_provider_source_name_from_settings(
                settings=settings
            ),
        )
        if base_loader is None:
            return None
        known_base_registry = dict(base_loader())
    else:
        base_loader = get_default_tool_registry
        known_base_registry = get_default_tool_registry()

    profile_name = get_tool_registry_profile_name_from_settings(
        settings=SimpleNamespace(
            tool_registry_profile=spec.get("profile", implicit_profile_name),
        )
    )
    profile_config = build_tool_registry_profile_settings_config(profile_name=profile_name)
    disabled_tool_names = set(normalize_tool_registry_names(profile_config.disabled_tool_names))
    raw_disabled_tool_names = spec.get("disabled_tool_names")
    if _is_non_text_sequence(raw_disabled_tool_names):
        disabled_tool_names.update(normalize_tool_registry_names(raw_disabled_tool_names))

    extra_tools = build_tool_registry_extra_tools_from_specs(
        extra_tool_specs=spec.get("extra_tools"),
        settings=settings,
    )
    base_registry = build_tool_registry(
        base_registry=known_base_registry if known_base_registry is not None else base_loader(),
        overrides=extra_tools or None,
    )
    source_overrides, disabled_tool_names = _build_registry_overrides_from_specs(
        override_specs=spec.get("overrides"),
        base_registry=base_registry,
        disabled_tool_names=disabled_tool_names,
        settings=settings,
    )
    registry = build_tool_registry(
        base_registry=base_registry,
        overrides=build_tool_registry(
            base_registry=profile_config.overrides,
            overrides=source_overrides or None,
        )
        or None,
        disabled_tool_names=tuple(sorted(disabled_tool_names)),
    )
    return lambda: dict(registry)


def _impl_build_tool_registry_loaders_from_settings(
    *,
    settings: object | None = None,
) -> dict[str, ToolRegistryLoader]:
    artifacts = build_tool_registry_loaders_from_settings_artifacts(settings=settings)
    return artifacts["loaders"]


def _impl_build_tool_registry_provider_adapter(
    *,
    spec: dict[str, object],
    settings: object | None = None,
    provider_source_name: str | None = None,
    named_loaders: dict[str, ToolRegistryLoader] | None = None,
    named_providers: dict[str, ToolRegistryProvider] | None = None,
    named_sources: dict[str, ToolRegistryProvider] | None = None,
) -> ToolRegistryProvider | None:
    spec = _coerce_tool_registry_spec_payload(spec)
    if not isinstance(spec, dict):
        return None
    spec = _merge_inline_tool_registry_extra_tool_specs(
        spec,
        adapter_keys=_TOOL_REGISTRY_PROVIDER_ADAPTER_KEYS,
    )
    provider_factory_name = spec.get("provider_factory")
    provider_name = spec.get("provider")
    loader_factory_name = spec.get("loader_factory")
    loader_name = spec.get("loader")
    registry_file = spec.get("registry_file")
    base_provider: ToolRegistryProvider | None = None
    base_loader: ToolRegistryLoader | None = None
    known_base_registry: dict[str, ToolRegistration] | None = None
    implicit_profile_name = "default"

    if isinstance(provider_factory_name, str) and provider_factory_name.strip():
        normalized_provider_factory_name = _normalize_named_tool_registry_component_name(
            provider_factory_name
        )
        if normalized_provider_factory_name is None:
            return None
        named_provider_factories = build_tool_registry_provider_factories_from_settings(
            settings=settings
        )
        provider_factory = resolve_named_tool_registry_provider_factory(
            normalized_provider_factory_name,
            named_provider_factories=named_provider_factories,
        )
        if provider_factory is None:
            return None
        base_provider = provider_factory(
            _clone_tool_execution_settings(
                settings=settings or SimpleNamespace(),
                **(
                    {"tool_registry_provider_source": provider_source_name}
                    if provider_source_name
                    else {}
                ),
            )
        )
        profile_name_hint = getattr(provider_factory, "_tool_registry_profile_name", None)
        if profile_name_hint:
            known_base_registry = get_default_tool_registry()
            implicit_profile_name = get_tool_registry_profile_name_from_settings(
                settings=SimpleNamespace(
                    tool_registry_profile=profile_name_hint,
                )
            )
    elif isinstance(provider_name, str) and provider_name.strip():
        base_provider = resolve_named_tool_registry_provider_reference(
            provider_name,
            named_providers=named_providers,
            named_sources=named_sources,
        )
        if base_provider is None:
            return None
        known_base_registry = dict(base_provider.load_tool_registry())
    elif isinstance(loader_factory_name, str) and loader_factory_name.strip():
        normalized_loader_factory_name = _normalize_named_tool_registry_component_name(
            loader_factory_name
        )
        if normalized_loader_factory_name is None:
            return None
        named_loader_factories = build_tool_registry_loader_factories_from_settings(
            settings=settings
        )
        loader_factory = resolve_named_tool_registry_loader_factory(
            normalized_loader_factory_name,
            named_loader_factories=named_loader_factories,
        )
        if loader_factory is None:
            return None
        base_loader = loader_factory(
            _clone_tool_execution_settings(
                settings=settings or SimpleNamespace(),
                **(
                    {"tool_registry_provider_source": provider_source_name}
                    if provider_source_name
                    else {}
                ),
            )
        )
        profile_name_hint = getattr(loader_factory, "_tool_registry_profile_name", None)
        if profile_name_hint:
            known_base_registry = get_default_tool_registry()
            implicit_profile_name = get_tool_registry_profile_name_from_settings(
                settings=SimpleNamespace(
                    tool_registry_profile=profile_name_hint,
                )
            )
    elif isinstance(loader_name, str) and loader_name.strip():
        base_loader = resolve_named_tool_registry_loader(loader_name)
        normalized_loader_name = _normalize_named_tool_registry_component_name(loader_name)
        if (
            base_loader is None
            and named_loaders is not None
            and normalized_loader_name is not None
        ):
            base_loader = named_loaders.get(normalized_loader_name)
        if base_loader is None:
            return None
        known_base_registry = dict(base_loader())
    elif isinstance(registry_file, str) and registry_file.strip():
        base_loader = build_tool_registry_loader_from_file(
            registry_file=registry_file,
            settings=settings,
            provider_source_name=provider_source_name,
        )
        if base_loader is None:
            return None
        known_base_registry = dict(base_loader())
    else:
        base_provider = get_default_tool_registry_provider()
        known_base_registry = get_default_tool_registry()

    profile_name = get_tool_registry_profile_name_from_settings(
        settings=SimpleNamespace(
            tool_registry_profile=spec.get("profile", implicit_profile_name),
        )
    )
    profile_config = build_tool_registry_profile_settings_config(profile_name=profile_name)
    disabled_tool_names = set(normalize_tool_registry_names(profile_config.disabled_tool_names))
    raw_disabled_tool_names = spec.get("disabled_tool_names")
    if isinstance(raw_disabled_tool_names, Sequence) and not isinstance(
        raw_disabled_tool_names,
        (str, bytes, bytearray, memoryview),
    ):
        disabled_tool_names.update(normalize_tool_registry_names(raw_disabled_tool_names))

    extra_tools = build_tool_registry_extra_tools_from_specs(
        extra_tool_specs=spec.get("extra_tools"),
        settings=settings,
        provider_source_name=provider_source_name,
    )
    base_registry = build_tool_registry(
        base_registry=known_base_registry
        if known_base_registry is not None
        else load_tool_registry(provider=base_provider, loader=base_loader),
        overrides=extra_tools or None,
    )
    source_overrides, disabled_tool_names = _build_registry_overrides_from_specs(
        override_specs=spec.get("overrides"),
        base_registry=base_registry,
        disabled_tool_names=disabled_tool_names,
        settings=_clone_tool_execution_settings(
            settings=settings or SimpleNamespace(),
            **(
                {"tool_registry_provider_source": provider_source_name}
                if provider_source_name
                else {}
            ),
        ),
    )
    adapter_overrides = build_tool_registry(
        base_registry=extra_tools or {},
        overrides=source_overrides or None,
    )
    if known_base_registry is not None:
        registry = build_tool_registry(
            base_registry=base_registry,
            overrides=build_tool_registry(
                base_registry=profile_config.overrides,
                overrides=adapter_overrides or None,
            ),
            disabled_tool_names=tuple(sorted(disabled_tool_names)),
        )
        return StaticToolRegistryProvider(registry=registry)
    return build_tool_registry_provider(
        provider=base_provider,
        loader=base_loader,
        overrides=build_tool_registry(
            base_registry=profile_config.overrides,
            overrides=adapter_overrides or None,
        ),
        disabled_tool_names=tuple(sorted(disabled_tool_names)),
    )


def _impl_build_tool_registry_providers_from_settings(
    *,
    settings: object | None = None,
) -> dict[str, ToolRegistryProvider]:
    artifacts = build_tool_registry_providers_from_settings_artifacts(settings=settings)
    return artifacts["providers"]


def _impl_build_tool_registry_providers_from_settings_artifacts(
    *,
    settings: object | None = None,
) -> dict[str, object]:
    if settings is None:
        settings = get_settings()
    provider_source_name = get_tool_registry_provider_source_name_from_settings(
        settings=settings
    )
    provider_profile_name = get_tool_registry_profile_name_from_settings(
        settings=settings
    )
    provider_settings = _clone_tool_registry_provider_source_scoped_settings(
        settings=settings,
        provider_source_name=provider_source_name,
        profile_name=provider_profile_name,
    )
    raw_providers = getattr(settings, "tool_registry_providers_json", None)
    provider_specs = _parse_tool_registry_json_object_setting(raw_providers)
    if provider_specs is None:
        return {
            "providers": {},
            "provider_diagnostics": {},
        }

    loader_artifacts = build_tool_registry_loaders_from_settings_artifacts(settings=settings)
    named_loaders = loader_artifacts["loaders"]
    loader_diagnostics = loader_artifacts["loader_diagnostics"]
    loader_factory_artifacts = build_tool_registry_loader_factories_from_settings_artifacts(
        settings=settings
    )
    loader_factory_diagnostics = loader_factory_artifacts["loader_factory_diagnostics"]
    provider_factory_artifacts = build_tool_registry_provider_factories_from_settings_artifacts(
        settings=settings
    )
    provider_factory_diagnostics = provider_factory_artifacts["provider_factory_diagnostics"]
    providers: dict[str, ToolRegistryProvider] = {}
    provider_diagnostics: dict[str, dict[str, tuple[str, ...]]] = {}
    for provider_name, spec in _order_tool_registry_provider_specs(provider_specs):
        spec = _coerce_tool_registry_spec_payload(spec)
        if not isinstance(provider_name, str) or not isinstance(spec, Mapping):
            continue
        spec = dict(spec)
        normalized_provider_name = _normalize_named_tool_registry_component_name(
            provider_name
        )
        if normalized_provider_name is None:
            continue
        spec = _merge_inline_tool_registry_extra_tool_specs(
            spec,
            adapter_keys=_TOOL_REGISTRY_PROVIDER_ADAPTER_KEYS,
        )
        diagnostics = _empty_tool_registry_file_diagnostics()
        registry_file = spec.get("registry_file")
        provider_factory_reference = spec.get("provider_factory")
        provider_reference = spec.get("provider")
        loader_factory_reference = spec.get("loader_factory")
        loader_reference = spec.get("loader")
        normalized_provider_factory_reference = _normalize_named_tool_registry_component_name(
            provider_factory_reference
        )
        normalized_provider_reference = _normalize_named_tool_registry_component_name(
            provider_reference
        )
        normalized_loader_factory_reference = _normalize_named_tool_registry_component_name(
            loader_factory_reference
        )
        normalized_loader_reference = _normalize_named_tool_registry_component_name(
            loader_reference
        )
        if isinstance(registry_file, str) and registry_file.strip():
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                build_tool_registry_provider_from_file_artifacts(
                    registry_file=registry_file,
                    settings=provider_settings,
                    provider_source_name=provider_source_name,
                )["diagnostics"],
            )
        elif (
            normalized_provider_reference is not None
            and normalized_provider_reference in provider_diagnostics
        ):
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                provider_diagnostics[normalized_provider_reference],
            )
        elif (
            normalized_provider_factory_reference is not None
            and normalized_provider_factory_reference in provider_factory_diagnostics
        ):
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                provider_factory_diagnostics[normalized_provider_factory_reference],
            )
        elif (
            normalized_loader_factory_reference is not None
            and normalized_loader_factory_reference in loader_factory_diagnostics
        ):
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                loader_factory_diagnostics[normalized_loader_factory_reference],
            )
        elif (
            normalized_loader_reference is not None
            and normalized_loader_reference in loader_diagnostics
        ):
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                loader_diagnostics[normalized_loader_reference],
            )
        diagnostics = _merge_tool_registry_file_diagnostics(
            diagnostics,
            _build_invalid_tool_execution_diagnostics(
                messages=_collect_invalid_tool_execution_messages_from_extra_tool_specs(
                    extra_tool_specs=spec.get("extra_tools"),
                    settings=provider_settings,
                )
            ),
        )
        provider = build_tool_registry_provider_adapter(
            spec=spec,
            settings=provider_settings,
            provider_source_name=provider_source_name,
            named_loaders=named_loaders,
            named_providers=providers,
        )
        if provider is None:
            if _has_tool_registry_file_diagnostics(diagnostics):
                provider_diagnostics[normalized_provider_name] = diagnostics
            continue
        diagnostics = _merge_tool_registry_file_diagnostics(
            diagnostics,
            _build_invalid_tool_execution_diagnostics(
                messages=_collect_invalid_tool_execution_messages_from_override_specs(
                    override_specs=spec.get("overrides"),
                    base_registry=dict(provider.load_tool_registry()),
                    settings=provider_settings,
                )
            ),
        )
        providers[normalized_provider_name] = provider
        provider_diagnostics[normalized_provider_name] = diagnostics
    return {
        "providers": providers,
        "provider_diagnostics": provider_diagnostics,
    }


def _impl_build_tool_registry_provider_sources_from_settings(
    *,
    settings: object | None = None,
    named_loaders: dict[str, ToolRegistryLoader] | None = None,
    named_providers: dict[str, ToolRegistryProvider] | None = None,
) -> dict[str, ToolRegistryProvider]:
    artifacts = build_tool_registry_provider_sources_from_settings_artifacts(
        settings=settings,
        named_loaders=named_loaders,
        named_providers=named_providers,
    )
    return artifacts["sources"]


def _impl_build_tool_registry_provider_sources_from_settings_artifacts(
    *,
    settings: object | None = None,
    named_loaders: dict[str, ToolRegistryLoader] | None = None,
    named_providers: dict[str, ToolRegistryProvider] | None = None,
) -> dict[str, object]:
    if settings is None:
        settings = get_settings()
    raw_sources = getattr(settings, "tool_registry_provider_sources_json", None)
    source_specs = _parse_tool_registry_json_object_setting(raw_sources)
    if source_specs is None:
        return {
            "sources": {},
            "source_diagnostics": {},
        }

    loader_artifacts: dict[str, object] | None = None
    provider_artifacts: dict[str, object] | None = None
    loader_factory_artifacts: dict[str, object] | None = None
    provider_factory_artifacts: dict[str, object] | None = None
    settings_backed_named_loaders = named_loaders is None
    settings_backed_named_providers = named_providers is None
    if named_loaders is None:
        loader_artifacts = build_tool_registry_loaders_from_settings_artifacts(
            settings=settings
        )
        named_loaders = loader_artifacts["loaders"]
    loader_diagnostics = (
        loader_artifacts["loader_diagnostics"] if loader_artifacts is not None else {}
    )
    loader_factory_artifacts = build_tool_registry_loader_factories_from_settings_artifacts(
        settings=settings
    )
    loader_factory_diagnostics = loader_factory_artifacts["loader_factory_diagnostics"]
    if named_providers is None:
        provider_artifacts = build_tool_registry_providers_from_settings_artifacts(
            settings=settings
        )
        named_providers = provider_artifacts["providers"]
    provider_diagnostics = (
        provider_artifacts["provider_diagnostics"] if provider_artifacts is not None else {}
    )
    provider_factory_artifacts = build_tool_registry_provider_factories_from_settings_artifacts(
        settings=settings
    )
    provider_factory_diagnostics = provider_factory_artifacts["provider_factory_diagnostics"]
    settings_execution_diagnostics = build_tool_registry_settings_execution_diagnostics(
        settings=settings
    )
    provider_source_reference_cycle_edges = (
        _find_tool_registry_provider_source_reference_cycle_edges(source_specs)
    )
    sources: dict[str, ToolRegistryProvider] = {}
    source_diagnostics: dict[str, dict[str, tuple[str, ...]]] = {}
    for source_name, spec in _order_tool_registry_provider_source_specs(source_specs):
        spec = _coerce_tool_registry_spec_payload(spec)
        if not isinstance(source_name, str) or not isinstance(spec, Mapping):
            continue
        spec = dict(spec)
        normalized_source_name = get_tool_registry_provider_source_name_from_settings(
            settings=SimpleNamespace(
                tool_registry_provider_source=source_name,
            )
        )
        source_profile_name = None
        if any(key in spec for key in _TOOL_REGISTRY_PROVIDER_ADAPTER_KEYS):
            source_profile_name = get_tool_registry_profile_name_from_settings(
                settings=SimpleNamespace(
                    tool_registry_profile=spec.get("profile", "default"),
                )
            )
            spec = _merge_inline_tool_registry_extra_tool_specs(
                spec,
                adapter_keys=_TOOL_REGISTRY_PROVIDER_ADAPTER_KEYS,
            )
        source_settings = _clone_tool_execution_settings(
            settings=settings,
            tool_registry_provider_source=normalized_source_name,
            **(
                {"tool_registry_profile": source_profile_name}
                if source_profile_name
                else {}
            ),
        )
        source_named_loaders = named_loaders
        source_loader_diagnostics = loader_diagnostics
        if settings_backed_named_loaders:
            source_loader_artifacts = build_tool_registry_loaders_from_settings_artifacts(
                settings=source_settings
            )
            source_named_loaders = source_loader_artifacts["loaders"]
            source_loader_diagnostics = source_loader_artifacts["loader_diagnostics"]
        source_loader_factory_artifacts = (
            build_tool_registry_loader_factories_from_settings_artifacts(
                settings=source_settings
            )
        )
        source_loader_factory_diagnostics = source_loader_factory_artifacts[
            "loader_factory_diagnostics"
        ]
        source_named_providers = named_providers
        source_provider_diagnostics = provider_diagnostics
        if settings_backed_named_providers:
            source_provider_artifacts = build_tool_registry_providers_from_settings_artifacts(
                settings=source_settings
            )
            source_named_providers = source_provider_artifacts["providers"]
            source_provider_diagnostics = source_provider_artifacts[
                "provider_diagnostics"
            ]
        source_provider_factory_artifacts = (
            build_tool_registry_provider_factories_from_settings_artifacts(
                settings=source_settings
            )
        )
        source_provider_factory_diagnostics = source_provider_factory_artifacts[
            "provider_factory_diagnostics"
        ]
        source_settings_execution_diagnostics = (
            build_tool_registry_settings_execution_diagnostics(settings=source_settings)
        )
        if any(key in spec for key in _TOOL_REGISTRY_PROVIDER_ADAPTER_KEYS):
            diagnostics = _empty_tool_registry_file_diagnostics()
            registry_file = spec.get("registry_file")
            provider_factory_reference = spec.get("provider_factory")
            provider_reference = spec.get("provider")
            loader_factory_reference = spec.get("loader_factory")
            loader_reference = spec.get("loader")
            normalized_provider_factory_reference = _normalize_named_tool_registry_component_name(
                provider_factory_reference
            )
            normalized_provider_reference = _normalize_named_tool_registry_component_name(
                provider_reference
            )
            normalized_provider_source_reference = (
                get_tool_registry_provider_source_name_from_settings(
                    settings=SimpleNamespace(
                        tool_registry_provider_source=provider_reference,
                    )
                )
            )
            normalized_loader_factory_reference = _normalize_named_tool_registry_component_name(
                loader_factory_reference
            )
            normalized_loader_reference = _normalize_named_tool_registry_component_name(
                loader_reference
            )
            cycle_reference = provider_source_reference_cycle_edges.get(
                normalized_source_name
            )
            if isinstance(registry_file, str) and registry_file.strip():
                diagnostics = _merge_tool_registry_file_diagnostics(
                    diagnostics,
                    build_tool_registry_provider_from_file_artifacts(
                        registry_file=registry_file,
                        settings=source_settings,
                        provider_source_name=normalized_source_name,
                    )["diagnostics"],
                )
            elif (
                normalized_provider_reference is not None
                and normalized_provider_reference in source_provider_diagnostics
            ):
                diagnostics = _merge_tool_registry_file_diagnostics(
                    diagnostics,
                    source_provider_diagnostics[normalized_provider_reference],
                )
            elif (
                cycle_reference is not None
                and normalized_provider_reference not in source_named_providers
            ):
                diagnostics = _merge_tool_registry_file_diagnostics(
                    diagnostics,
                    {
                        **_empty_tool_registry_file_diagnostics(),
                        "skipped_registry_sources": (cycle_reference,),
                    },
                )
            elif (
                normalized_provider_source_reference is not None
                and normalized_provider_source_reference in source_diagnostics
            ):
                diagnostics = _merge_tool_registry_file_diagnostics(
                    diagnostics,
                    source_diagnostics[normalized_provider_source_reference],
                )
            elif (
                normalized_provider_factory_reference is not None
                and normalized_provider_factory_reference
                in source_provider_factory_diagnostics
            ):
                diagnostics = _merge_tool_registry_file_diagnostics(
                    diagnostics,
                    source_provider_factory_diagnostics[
                        normalized_provider_factory_reference
                    ],
                )
            elif (
                normalized_loader_factory_reference is not None
                and normalized_loader_factory_reference in source_loader_factory_diagnostics
            ):
                diagnostics = _merge_tool_registry_file_diagnostics(
                    diagnostics,
                    source_loader_factory_diagnostics[
                        normalized_loader_factory_reference
                    ],
                )
            elif (
                normalized_loader_reference is not None
                and normalized_loader_reference in source_loader_diagnostics
            ):
                diagnostics = _merge_tool_registry_file_diagnostics(
                    diagnostics,
                    source_loader_diagnostics[normalized_loader_reference],
                )
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                _build_invalid_tool_execution_diagnostics(
                    messages=_collect_invalid_tool_execution_messages_from_extra_tool_specs(
                        extra_tool_specs=spec.get("extra_tools"),
                        settings=source_settings,
                    )
                ),
                source_settings_execution_diagnostics,
            )
            if (
                cycle_reference is not None
                and normalized_provider_reference not in source_named_providers
            ):
                source_diagnostics[normalized_source_name] = diagnostics
                continue
            provider = build_tool_registry_provider_adapter(
                spec=spec,
                settings=source_settings,
                provider_source_name=normalized_source_name,
                named_loaders=source_named_loaders,
                named_providers=source_named_providers,
                named_sources=sources,
            )
            if provider is None:
                source_diagnostics[normalized_source_name] = diagnostics
                continue
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                _build_invalid_tool_execution_diagnostics(
                    messages=_collect_invalid_tool_execution_messages_from_override_specs(
                        override_specs=spec.get("overrides"),
                        base_registry=dict(provider.load_tool_registry()),
                        settings=source_settings,
                    )
                ),
            )
            sources[normalized_source_name] = provider
            source_diagnostics[normalized_source_name] = diagnostics
            continue

        extra_tools = build_tool_registry_extra_tools_from_specs(
            extra_tool_specs=spec,
            settings=source_settings,
            provider_source_name=normalized_source_name,
        )
        if not extra_tools:
            continue
        sources[normalized_source_name] = StaticToolRegistryProvider(registry=extra_tools)
        source_diagnostics[normalized_source_name] = _merge_tool_registry_file_diagnostics(
            _empty_tool_registry_file_diagnostics(),
            _build_invalid_tool_execution_diagnostics(
                messages=_collect_invalid_tool_execution_messages_from_extra_tool_specs(
                    extra_tool_specs=spec,
                    settings=source_settings,
                )
            ),
            source_settings_execution_diagnostics,
        )
    return {
        "sources": sources,
        "source_diagnostics": source_diagnostics,
    }


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
        safe_values = tuple(
            value
            for value in (
                _redact_tool_registry_diagnostic_value(raw_value)
                for raw_value in values
            )
            if value
        )
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
) -> ToolRegistryDiagnosticsRuntimeArtifactsModel:
    summary = build_tool_registry_diagnostics_summary_model(diagnostics=diagnostics)
    if not bool(summary.has_diagnostics):
        return ToolRegistryDiagnosticsRuntimeArtifactsModel(
            summary=summary,
            trace_step=None,
            trace_event=None,
            audit_detail=None,
        )

    trace_step = {
        "id": step_id,
        "seq": seq,
        "type": "observation",
        "content": "\n".join(
            (
                "Tool registry diagnostics: "
                f"source={provider_source_name} "
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
                "provider_source": provider_source_name,
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
            "provider_source": provider_source_name,
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
) -> dict[str, object]:
    return build_tool_registry_diagnostics_runtime_artifacts_model(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        provider_source_name=provider_source_name,
        diagnostics=diagnostics,
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
) -> ConfiguredToolRegistryProviderRuntimeServiceActionModel:
    return ConfiguredToolRegistryProviderRuntimeServiceActionModel(
        kind=str(service_action.get("kind")),
        trace_step=_sanitize_tool_runtime_trace_artifact_payload(
            service_action.get("trace_step")
        )
        if isinstance(service_action.get("trace_step"), dict)
        else None,
        trace_event=_sanitize_tool_runtime_trace_artifact_payload(
            service_action.get("trace_event")
        )
        if isinstance(service_action.get("trace_event"), dict)
        else None,
        persist_force=bool(service_action.get("persist_force")),
        kwargs=_sanitize_tool_runtime_trace_artifact_payload(
            service_action.get("kwargs")
        )
        if isinstance(service_action.get("kwargs"), dict)
        else None,
    )


def _impl_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
    *,
    service_actions: list[dict[str, object]],
) -> ConfiguredToolRegistryProviderRuntimeServiceActionsModel:
    return ConfiguredToolRegistryProviderRuntimeServiceActionsModel(
        actions=tuple(
            build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
                service_action
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
    return ConfiguredToolRegistryProviderRuntimeArtifactsModel(
        provider=provider,
        provider_source_name=str(runtime_artifacts.get("provider_source_name", provider_source_name)),
        provider_sources=runtime_artifacts.get("provider_sources", {}),
        selected_source_diagnostics=sanitize_tool_registry_file_diagnostics(
            runtime_artifacts.get("selected_source_diagnostics", {})
        ),
        source_diagnostics=sanitize_tool_registry_source_diagnostics(
            runtime_artifacts.get("source_diagnostics", {})
        ),
        diagnostics_runtime=ToolRegistryDiagnosticsRuntimeArtifactsModel(
            summary=ToolRegistryDiagnosticsSummaryModel(
                has_diagnostics=bool(summary_payload.get("has_diagnostics", False)),
                skipped_total=int(summary_payload.get("skipped_total", 0) or 0),
                missing_total=int(summary_payload.get("missing_total", 0) or 0),
                total=int(summary_payload.get("total", 0) or 0),
                entries=sanitize_tool_registry_diagnostics_summary_entries(
                    summary_payload.get("entries", ())
                ),
            ),
            trace_step=_sanitize_tool_runtime_trace_artifact_payload(
                diagnostics_runtime_payload.get("trace_step")
            )
            if isinstance(diagnostics_runtime_payload.get("trace_step"), dict)
            else None,
            trace_event=_sanitize_tool_runtime_trace_artifact_payload(
                diagnostics_runtime_payload.get("trace_event")
            )
            if isinstance(diagnostics_runtime_payload.get("trace_event"), dict)
            else None,
            audit_detail=_sanitize_tool_runtime_trace_artifact_payload(
                diagnostics_runtime_payload.get("audit_detail")
            )
            if isinstance(diagnostics_runtime_payload.get("audit_detail"), dict)
            else None,
        ),
        audit_event=_sanitize_tool_runtime_trace_artifact_payload(
            runtime_artifacts.get("audit_event")
        )
        if isinstance(runtime_artifacts.get("audit_event"), dict)
        else None,
    )


def _impl_build_configured_tool_registry_provider_service_execution_model_from_dict(
    *,
    service_execution: dict[str, object],
) -> ConfiguredToolRegistryProviderServiceExecutionModel:
    provider = service_execution["provider"]
    provider_source_name = str(service_execution["provider_source_name"])
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
        ),
        service_actions=build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
            service_actions=service_actions_payload
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
    for service_action in service_actions.actions:
        kind = service_action.kind
        if kind == "internal_trace_write":
            trace_step = service_action.trace_step
            if trace_step is None:
                continue
            sanitized_trace_step = _sanitize_tool_runtime_trace_artifact_payload(
                trace_step
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
        record_audit_event_fn(**kwargs)
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
    provider_source_name = str(
        preflight_result.get(
            "provider_source_name",
            service_execution_payload.get("provider_source_name", "default"),
        )
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
    provider_source_name = str(
        service_execution.get(
            "provider_source_name",
            preflight_result.get("provider_source_name", "default"),
        )
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
    diagnostics_runtime = build_tool_registry_diagnostics_runtime_artifacts_model(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        provider_source_name=str(artifacts["provider_source_name"]),
        diagnostics=artifacts["selected_source_diagnostics"],
    )
    return ConfiguredToolRegistryProviderRuntimeArtifactsModel(
        provider=artifacts["provider"],
        provider_source_name=str(artifacts["provider_source_name"]),
        provider_sources=artifacts["provider_sources"],
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


def _call_public_or_impl(name: str, impl, *args, **kwargs):
    public_value = getattr(_runtime_module(), name, None)
    local_value = globals().get(name)
    if (
        public_value is not None
        and public_value is not local_value
        and name not in _ACTIVE_PUBLIC_PROXY_NAMES
    ):
        _ACTIVE_PUBLIC_PROXY_NAMES.add(name)
        try:
            return public_value(*args, **kwargs)
        finally:
            _ACTIVE_PUBLIC_PROXY_NAMES.discard(name)
    return impl(*args, **kwargs)

@wraps(_impl_build_tool_registry_extra_tools_from_file)
def build_tool_registry_extra_tools_from_file(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_extra_tools_from_file", _impl_build_tool_registry_extra_tools_from_file, *args, **kwargs)

@wraps(_impl__resolve_tool_registry_file_path)
def _resolve_tool_registry_file_path(*args, **kwargs):
    return _call_public_or_impl("_resolve_tool_registry_file_path", _impl__resolve_tool_registry_file_path, *args, **kwargs)

@wraps(_impl__resolve_tool_registry_dir_path)
def _resolve_tool_registry_dir_path(*args, **kwargs):
    return _call_public_or_impl("_resolve_tool_registry_dir_path", _impl__resolve_tool_registry_dir_path, *args, **kwargs)

@wraps(_impl_load_tool_registry_file_payload)
def load_tool_registry_file_payload(*args, **kwargs):
    return _call_public_or_impl("load_tool_registry_file_payload", _impl_load_tool_registry_file_payload, *args, **kwargs)

@wraps(_impl__normalize_tool_registry_file_diagnostics)
def _normalize_tool_registry_file_diagnostics(*args, **kwargs):
    return _call_public_or_impl("_normalize_tool_registry_file_diagnostics", _impl__normalize_tool_registry_file_diagnostics, *args, **kwargs)

@wraps(_impl__empty_tool_registry_file_diagnostics)
def _empty_tool_registry_file_diagnostics(*args, **kwargs):
    return _call_public_or_impl("_empty_tool_registry_file_diagnostics", _impl__empty_tool_registry_file_diagnostics, *args, **kwargs)

@wraps(_impl__has_tool_registry_file_diagnostics)
def _has_tool_registry_file_diagnostics(*args, **kwargs):
    return _call_public_or_impl("_has_tool_registry_file_diagnostics", _impl__has_tool_registry_file_diagnostics, *args, **kwargs)

@wraps(_impl__merge_tool_registry_file_diagnostics)
def _merge_tool_registry_file_diagnostics(*args, **kwargs):
    return _call_public_or_impl("_merge_tool_registry_file_diagnostics", _impl__merge_tool_registry_file_diagnostics, *args, **kwargs)

@wraps(_impl_sanitize_tool_registry_file_diagnostics)
def sanitize_tool_registry_file_diagnostics(*args, **kwargs):
    return _call_public_or_impl("sanitize_tool_registry_file_diagnostics", _impl_sanitize_tool_registry_file_diagnostics, *args, **kwargs)

@wraps(_impl_sanitize_tool_registry_source_diagnostics)
def sanitize_tool_registry_source_diagnostics(*args, **kwargs):
    return _call_public_or_impl("sanitize_tool_registry_source_diagnostics", _impl_sanitize_tool_registry_source_diagnostics, *args, **kwargs)

@wraps(_impl_sanitize_tool_registry_diagnostics_summary_entries)
def sanitize_tool_registry_diagnostics_summary_entries(*args, **kwargs):
    return _call_public_or_impl("sanitize_tool_registry_diagnostics_summary_entries", _impl_sanitize_tool_registry_diagnostics_summary_entries, *args, **kwargs)

@wraps(_impl_sanitize_tool_registry_diagnostics_artifact_payload)
def sanitize_tool_registry_diagnostics_artifact_payload(*args, **kwargs):
    return _call_public_or_impl("sanitize_tool_registry_diagnostics_artifact_payload", _impl_sanitize_tool_registry_diagnostics_artifact_payload, *args, **kwargs)

@wraps(_impl__filter_tool_registry_json_object_setting_for_visited_registry_files)
def _filter_tool_registry_json_object_setting_for_visited_registry_files(*args, **kwargs):
    return _call_public_or_impl("_filter_tool_registry_json_object_setting_for_visited_registry_files", _impl__filter_tool_registry_json_object_setting_for_visited_registry_files, *args, **kwargs)

@wraps(_impl__clone_tool_registry_settings_without_visited_registry_file_components)
def _clone_tool_registry_settings_without_visited_registry_file_components(*args, **kwargs):
    return _call_public_or_impl("_clone_tool_registry_settings_without_visited_registry_file_components", _impl__clone_tool_registry_settings_without_visited_registry_file_components, *args, **kwargs)

@wraps(_impl__expand_skipped_registry_file_component_names)
def _expand_skipped_registry_file_component_names(*args, **kwargs):
    return _call_public_or_impl("_expand_skipped_registry_file_component_names", _impl__expand_skipped_registry_file_component_names, *args, **kwargs)

@wraps(_impl__build_tool_registry_from_file_registry)
def _build_tool_registry_from_file_registry(*args, **kwargs):
    return _call_public_or_impl("_build_tool_registry_from_file_registry", _impl__build_tool_registry_from_file_registry, *args, **kwargs)

@wraps(_impl_build_tool_registry_from_file_artifacts)
def build_tool_registry_from_file_artifacts(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_from_file_artifacts", _impl_build_tool_registry_from_file_artifacts, *args, **kwargs)

@wraps(_impl_build_tool_registry_loader_from_file_artifacts)
def build_tool_registry_loader_from_file_artifacts(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_loader_from_file_artifacts", _impl_build_tool_registry_loader_from_file_artifacts, *args, **kwargs)

@wraps(_impl_build_tool_registry_provider_from_file_artifacts)
def build_tool_registry_provider_from_file_artifacts(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_provider_from_file_artifacts", _impl_build_tool_registry_provider_from_file_artifacts, *args, **kwargs)

@wraps(_impl_build_tool_registry_from_file)
def build_tool_registry_from_file(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_from_file", _impl_build_tool_registry_from_file, *args, **kwargs)

@wraps(_impl_build_tool_registry_loader_from_file)
def build_tool_registry_loader_from_file(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_loader_from_file", _impl_build_tool_registry_loader_from_file, *args, **kwargs)

@wraps(_impl_build_tool_registry_provider_from_file)
def build_tool_registry_provider_from_file(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_provider_from_file", _impl_build_tool_registry_provider_from_file, *args, **kwargs)

@wraps(_impl__build_tool_registry_loader_factory_adapter)
def _build_tool_registry_loader_factory_adapter(*args, **kwargs):
    return _call_public_or_impl("_build_tool_registry_loader_factory_adapter", _impl__build_tool_registry_loader_factory_adapter, *args, **kwargs)

@wraps(_impl__build_tool_registry_provider_factory_adapter)
def _build_tool_registry_provider_factory_adapter(*args, **kwargs):
    return _call_public_or_impl("_build_tool_registry_provider_factory_adapter", _impl__build_tool_registry_provider_factory_adapter, *args, **kwargs)

@wraps(_impl_build_tool_registry_loaders_from_settings_artifacts)
def build_tool_registry_loaders_from_settings_artifacts(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_loaders_from_settings_artifacts", _impl_build_tool_registry_loaders_from_settings_artifacts, *args, **kwargs)

@wraps(_impl_build_tool_registry_loader_factories_from_settings_artifacts)
def build_tool_registry_loader_factories_from_settings_artifacts(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_loader_factories_from_settings_artifacts", _impl_build_tool_registry_loader_factories_from_settings_artifacts, *args, **kwargs)

@wraps(_impl_build_tool_registry_loader_factories_from_settings)
def build_tool_registry_loader_factories_from_settings(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_loader_factories_from_settings", _impl_build_tool_registry_loader_factories_from_settings, *args, **kwargs)

@wraps(_impl_build_tool_registry_provider_factories_from_settings_artifacts)
def build_tool_registry_provider_factories_from_settings_artifacts(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_provider_factories_from_settings_artifacts", _impl_build_tool_registry_provider_factories_from_settings_artifacts, *args, **kwargs)

@wraps(_impl_build_tool_registry_provider_factories_from_settings)
def build_tool_registry_provider_factories_from_settings(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_provider_factories_from_settings", _impl_build_tool_registry_provider_factories_from_settings, *args, **kwargs)

@wraps(_impl_build_tool_registry_loader_adapter)
def build_tool_registry_loader_adapter(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_loader_adapter", _impl_build_tool_registry_loader_adapter, *args, **kwargs)

@wraps(_impl_build_tool_registry_loaders_from_settings)
def build_tool_registry_loaders_from_settings(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_loaders_from_settings", _impl_build_tool_registry_loaders_from_settings, *args, **kwargs)

@wraps(_impl_build_tool_registry_provider_adapter)
def build_tool_registry_provider_adapter(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_provider_adapter", _impl_build_tool_registry_provider_adapter, *args, **kwargs)

@wraps(_impl_build_tool_registry_providers_from_settings)
def build_tool_registry_providers_from_settings(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_providers_from_settings", _impl_build_tool_registry_providers_from_settings, *args, **kwargs)

@wraps(_impl_build_tool_registry_providers_from_settings_artifacts)
def build_tool_registry_providers_from_settings_artifacts(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_providers_from_settings_artifacts", _impl_build_tool_registry_providers_from_settings_artifacts, *args, **kwargs)

@wraps(_impl_build_tool_registry_provider_sources_from_settings)
def build_tool_registry_provider_sources_from_settings(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_provider_sources_from_settings", _impl_build_tool_registry_provider_sources_from_settings, *args, **kwargs)

@wraps(_impl_build_tool_registry_provider_sources_from_settings_artifacts)
def build_tool_registry_provider_sources_from_settings_artifacts(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_provider_sources_from_settings_artifacts", _impl_build_tool_registry_provider_sources_from_settings_artifacts, *args, **kwargs)

@wraps(_impl_build_tool_registry_extra_tools_from_settings)
def build_tool_registry_extra_tools_from_settings(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_extra_tools_from_settings", _impl_build_tool_registry_extra_tools_from_settings, *args, **kwargs)

@wraps(_impl__build_registry_overrides_from_specs)
def _build_registry_overrides_from_specs(*args, **kwargs):
    return _call_public_or_impl("_build_registry_overrides_from_specs", _impl__build_registry_overrides_from_specs, *args, **kwargs)

@wraps(_impl_build_tool_registry_settings_config)
def build_tool_registry_settings_config(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_settings_config", _impl_build_tool_registry_settings_config, *args, **kwargs)

@wraps(_impl_build_tool_registry_overrides_from_settings)
def build_tool_registry_overrides_from_settings(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_overrides_from_settings", _impl_build_tool_registry_overrides_from_settings, *args, **kwargs)

@wraps(_impl_get_disabled_tool_names_from_settings)
def get_disabled_tool_names_from_settings(*args, **kwargs):
    return _call_public_or_impl("get_disabled_tool_names_from_settings", _impl_get_disabled_tool_names_from_settings, *args, **kwargs)

@wraps(_impl_get_configured_tool_registry_provider)
def get_configured_tool_registry_provider(*args, **kwargs):
    return _call_public_or_impl("get_configured_tool_registry_provider", _impl_get_configured_tool_registry_provider, *args, **kwargs)

@wraps(_impl_get_configured_tool_registry_provider_artifacts)
def get_configured_tool_registry_provider_artifacts(*args, **kwargs):
    return _call_public_or_impl("get_configured_tool_registry_provider_artifacts", _impl_get_configured_tool_registry_provider_artifacts, *args, **kwargs)

@wraps(_impl_build_tool_registry_diagnostics_summary_model)
def build_tool_registry_diagnostics_summary_model(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_diagnostics_summary_model", _impl_build_tool_registry_diagnostics_summary_model, *args, **kwargs)

@wraps(_impl_build_tool_registry_diagnostics_summary)
def build_tool_registry_diagnostics_summary(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_diagnostics_summary", _impl_build_tool_registry_diagnostics_summary, *args, **kwargs)

@wraps(_impl__humanize_tool_registry_diagnostics_target)
def _humanize_tool_registry_diagnostics_target(*args, **kwargs):
    return _call_public_or_impl("_humanize_tool_registry_diagnostics_target", _impl__humanize_tool_registry_diagnostics_target, *args, **kwargs)

@wraps(_impl_build_tool_registry_diagnostics_display_lines)
def build_tool_registry_diagnostics_display_lines(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_diagnostics_display_lines", _impl_build_tool_registry_diagnostics_display_lines, *args, **kwargs)

@wraps(_impl_build_tool_registry_diagnostics_runtime_artifacts_model)
def build_tool_registry_diagnostics_runtime_artifacts_model(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_diagnostics_runtime_artifacts_model", _impl_build_tool_registry_diagnostics_runtime_artifacts_model, *args, **kwargs)

@wraps(_impl_build_tool_registry_diagnostics_runtime_artifacts)
def build_tool_registry_diagnostics_runtime_artifacts(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_diagnostics_runtime_artifacts", _impl_build_tool_registry_diagnostics_runtime_artifacts, *args, **kwargs)

@wraps(_impl_build_tool_registry_diagnostics_audit_event)
def build_tool_registry_diagnostics_audit_event(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_diagnostics_audit_event", _impl_build_tool_registry_diagnostics_audit_event, *args, **kwargs)

@wraps(_impl_build_tool_registry_diagnostics_audit_service_action)
def build_tool_registry_diagnostics_audit_service_action(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_diagnostics_audit_service_action", _impl_build_tool_registry_diagnostics_audit_service_action, *args, **kwargs)

@wraps(_impl_build_tool_registry_diagnostics_audit_service_action_model)
def build_tool_registry_diagnostics_audit_service_action_model(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_diagnostics_audit_service_action_model", _impl_build_tool_registry_diagnostics_audit_service_action_model, *args, **kwargs)

@wraps(_impl_build_tool_registry_diagnostics_trace_service_action)
def build_tool_registry_diagnostics_trace_service_action(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_diagnostics_trace_service_action", _impl_build_tool_registry_diagnostics_trace_service_action, *args, **kwargs)

@wraps(_impl_build_tool_registry_diagnostics_trace_service_action_model)
def build_tool_registry_diagnostics_trace_service_action_model(*args, **kwargs):
    return _call_public_or_impl("build_tool_registry_diagnostics_trace_service_action_model", _impl_build_tool_registry_diagnostics_trace_service_action_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_service_actions)
def build_configured_tool_registry_provider_runtime_service_actions(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_service_actions", _impl_build_configured_tool_registry_provider_runtime_service_actions, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_service_actions_model)
def build_configured_tool_registry_provider_runtime_service_actions_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_service_actions_model", _impl_build_configured_tool_registry_provider_runtime_service_actions_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models)
def build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models", _impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model)
def build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model", _impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts)
def build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts", _impl_build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_service_actions_outputs)
def build_configured_tool_registry_provider_runtime_service_actions_outputs(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_service_actions_outputs", _impl_build_configured_tool_registry_provider_runtime_service_actions_outputs, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model)
def build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model", _impl_build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_service_action_model_from_dict)
def build_configured_tool_registry_provider_runtime_service_action_model_from_dict(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_service_action_model_from_dict", _impl_build_configured_tool_registry_provider_runtime_service_action_model_from_dict, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts)
def build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts", _impl_build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict)
def build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_artifacts_model_from_dict", _impl_build_configured_tool_registry_provider_runtime_artifacts_model_from_dict, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_service_execution_model_from_dict)
def build_configured_tool_registry_provider_service_execution_model_from_dict(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_service_execution_model_from_dict", _impl_build_configured_tool_registry_provider_service_execution_model_from_dict, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_runtime_service_actions)
def execute_configured_tool_registry_provider_runtime_service_actions(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_runtime_service_actions", _impl_execute_configured_tool_registry_provider_runtime_service_actions, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_service_actions_result_model)
def build_configured_tool_registry_provider_runtime_service_actions_result_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_service_actions_result_model", _impl_build_configured_tool_registry_provider_runtime_service_actions_result_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models)
def build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models", _impl_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict)
def build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict", _impl_build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict)
def build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict", _impl_build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_runtime_service_actions_result_model)
def execute_configured_tool_registry_provider_runtime_service_actions_result_model(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_runtime_service_actions_result_model", _impl_execute_configured_tool_registry_provider_runtime_service_actions_result_model, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models)
def execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models", _impl_execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models)
def execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models", _impl_execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_runtime_service_actions_model)
def execute_configured_tool_registry_provider_runtime_service_actions_model(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_runtime_service_actions_model", _impl_execute_configured_tool_registry_provider_runtime_service_actions_model, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_runtime_service_actions_outputs)
def execute_configured_tool_registry_provider_runtime_service_actions_outputs(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_runtime_service_actions_outputs", _impl_execute_configured_tool_registry_provider_runtime_service_actions_outputs, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_service_execution_model)
def build_configured_tool_registry_provider_service_execution_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_service_execution_model", _impl_build_configured_tool_registry_provider_service_execution_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_service_execution)
def build_configured_tool_registry_provider_service_execution(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_service_execution", _impl_build_configured_tool_registry_provider_service_execution, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_service_execution_result_model)
def build_configured_tool_registry_provider_service_execution_result_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_service_execution_result_model", _impl_build_configured_tool_registry_provider_service_execution_result_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model)
def build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model", _impl_build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_service_execution_result_model_from_models)
def build_configured_tool_registry_provider_service_execution_result_model_from_models(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_service_execution_result_model_from_models", _impl_build_configured_tool_registry_provider_service_execution_result_model_from_models, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_service_execution_outputs_from_models)
def build_configured_tool_registry_provider_service_execution_outputs_from_models(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_service_execution_outputs_from_models", _impl_build_configured_tool_registry_provider_service_execution_outputs_from_models, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model)
def build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model", _impl_build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_service_execution_outputs_from_models)
def execute_configured_tool_registry_provider_service_execution_outputs_from_models(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_service_execution_outputs_from_models", _impl_execute_configured_tool_registry_provider_service_execution_outputs_from_models, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_service_execution_outputs)
def build_configured_tool_registry_provider_service_execution_outputs(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_service_execution_outputs", _impl_build_configured_tool_registry_provider_service_execution_outputs, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_service_execution)
def execute_configured_tool_registry_provider_service_execution(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_service_execution", _impl_execute_configured_tool_registry_provider_service_execution, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model)
def execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model", _impl_execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_service_execution_outputs)
def execute_configured_tool_registry_provider_service_execution_outputs(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_service_execution_outputs", _impl_execute_configured_tool_registry_provider_service_execution_outputs, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_service_execution_model)
def execute_configured_tool_registry_provider_service_execution_model(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_service_execution_model", _impl_execute_configured_tool_registry_provider_service_execution_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_summary_model)
def build_configured_tool_registry_provider_preflight_summary_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_summary_model", _impl_build_configured_tool_registry_provider_preflight_summary_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_service_execution_model_from_dict)
def build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_service_execution_model_from_dict", _impl_build_configured_tool_registry_provider_preflight_service_execution_model_from_dict, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict)
def build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict", _impl_build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict, *args, **kwargs)

@wraps(_impl__merge_configured_tool_registry_provider_preflight_service_execution_payload)
def _merge_configured_tool_registry_provider_preflight_service_execution_payload(*args, **kwargs):
    return _call_public_or_impl("_merge_configured_tool_registry_provider_preflight_service_execution_payload", _impl__merge_configured_tool_registry_provider_preflight_service_execution_payload, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict)
def build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict", _impl_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model)
def build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model", _impl_build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_execution_models_from_dict)
def build_configured_tool_registry_provider_preflight_execution_models_from_dict(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_execution_models_from_dict", _impl_build_configured_tool_registry_provider_preflight_execution_models_from_dict, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload)
def build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload", _impl_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model)
def build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model", _impl_build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_models_from_service_execution_payload)
def build_configured_tool_registry_provider_preflight_models_from_service_execution_payload(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_models_from_service_execution_payload", _impl_build_configured_tool_registry_provider_preflight_models_from_service_execution_payload, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_models_from_service_execution_model)
def build_configured_tool_registry_provider_preflight_models_from_service_execution_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_models_from_service_execution_model", _impl_build_configured_tool_registry_provider_preflight_models_from_service_execution_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_models_from_dict)
def build_configured_tool_registry_provider_preflight_models_from_dict(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_models_from_dict", _impl_build_configured_tool_registry_provider_preflight_models_from_dict, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_models_from_models)
def build_configured_tool_registry_provider_preflight_models_from_models(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_models_from_models", _impl_build_configured_tool_registry_provider_preflight_models_from_models, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_summary_model_from_dict)
def build_configured_tool_registry_provider_preflight_summary_model_from_dict(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_summary_model_from_dict", _impl_build_configured_tool_registry_provider_preflight_summary_model_from_dict, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_summary_model_from_result_model)
def build_configured_tool_registry_provider_preflight_summary_model_from_result_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_summary_model_from_result_model", _impl_build_configured_tool_registry_provider_preflight_summary_model_from_result_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_summary_model_from_models)
def build_configured_tool_registry_provider_preflight_summary_model_from_models(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_summary_model_from_models", _impl_build_configured_tool_registry_provider_preflight_summary_model_from_models, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_summary_model_from_parts)
def build_configured_tool_registry_provider_preflight_summary_model_from_parts(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_summary_model_from_parts", _impl_build_configured_tool_registry_provider_preflight_summary_model_from_parts, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_summary)
def build_configured_tool_registry_provider_preflight_summary(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_summary", _impl_build_configured_tool_registry_provider_preflight_summary, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_outputs_from_resolved_models)
def build_configured_tool_registry_provider_preflight_outputs_from_resolved_models(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_outputs_from_resolved_models", _impl_build_configured_tool_registry_provider_preflight_outputs_from_resolved_models, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_outputs_from_models)
def build_configured_tool_registry_provider_preflight_outputs_from_models(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_outputs_from_models", _impl_build_configured_tool_registry_provider_preflight_outputs_from_models, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model)
def build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model", _impl_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_outputs)
def build_configured_tool_registry_provider_preflight_outputs(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_outputs", _impl_build_configured_tool_registry_provider_preflight_outputs, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload)
def build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload", _impl_build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_outputs_from_dict)
def build_configured_tool_registry_provider_preflight_outputs_from_dict(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_outputs_from_dict", _impl_build_configured_tool_registry_provider_preflight_outputs_from_dict, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_models)
def build_configured_tool_registry_provider_preflight_models(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_models", _impl_build_configured_tool_registry_provider_preflight_models, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_dicts)
def build_configured_tool_registry_provider_preflight_dicts(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_dicts", _impl_build_configured_tool_registry_provider_preflight_dicts, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_result_model)
def build_configured_tool_registry_provider_preflight_result_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_result_model", _impl_build_configured_tool_registry_provider_preflight_result_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model)
def build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model", _impl_build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_result_model_from_models)
def build_configured_tool_registry_provider_preflight_result_model_from_models(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_result_model_from_models", _impl_build_configured_tool_registry_provider_preflight_result_model_from_models, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_result_model_from_dict)
def build_configured_tool_registry_provider_preflight_result_model_from_dict(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_result_model_from_dict", _impl_build_configured_tool_registry_provider_preflight_result_model_from_dict, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_preflight_result)
def build_configured_tool_registry_provider_preflight_result(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_preflight_result", _impl_build_configured_tool_registry_provider_preflight_result, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_preflight_models_from_service_execution_model)
def execute_configured_tool_registry_provider_preflight_models_from_service_execution_model(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_preflight_models_from_service_execution_model", _impl_execute_configured_tool_registry_provider_preflight_models_from_service_execution_model, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model)
def execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model", _impl_execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_preflight_outputs)
def execute_configured_tool_registry_provider_preflight_outputs(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_preflight_outputs", _impl_execute_configured_tool_registry_provider_preflight_outputs, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_preflight_summary_model)
def execute_configured_tool_registry_provider_preflight_summary_model(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_preflight_summary_model", _impl_execute_configured_tool_registry_provider_preflight_summary_model, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_preflight_summary)
def execute_configured_tool_registry_provider_preflight_summary(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_preflight_summary", _impl_execute_configured_tool_registry_provider_preflight_summary, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_preflight_dicts)
def execute_configured_tool_registry_provider_preflight_dicts(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_preflight_dicts", _impl_execute_configured_tool_registry_provider_preflight_dicts, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_preflight_models)
def execute_configured_tool_registry_provider_preflight_models(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_preflight_models", _impl_execute_configured_tool_registry_provider_preflight_models, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_preflight)
def execute_configured_tool_registry_provider_preflight(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_preflight", _impl_execute_configured_tool_registry_provider_preflight, *args, **kwargs)

@wraps(_impl_execute_configured_tool_registry_provider_preflight_model)
def execute_configured_tool_registry_provider_preflight_model(*args, **kwargs):
    return _call_public_or_impl("execute_configured_tool_registry_provider_preflight_model", _impl_execute_configured_tool_registry_provider_preflight_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_artifacts_model)
def build_configured_tool_registry_provider_runtime_artifacts_model(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_artifacts_model", _impl_build_configured_tool_registry_provider_runtime_artifacts_model, *args, **kwargs)

@wraps(_impl_build_configured_tool_registry_provider_runtime_artifacts)
def build_configured_tool_registry_provider_runtime_artifacts(*args, **kwargs):
    return _call_public_or_impl("build_configured_tool_registry_provider_runtime_artifacts", _impl_build_configured_tool_registry_provider_runtime_artifacts, *args, **kwargs)
