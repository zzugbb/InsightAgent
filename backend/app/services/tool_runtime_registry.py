from __future__ import annotations

import json
import re

from collections.abc import Mapping, Sequence

from dataclasses import replace

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

_TOOL_REGISTRY_PROVIDER_SOURCE_SENSITIVE_TOKEN_RE = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|client[_-]?secret|secret|token|password)"
    r"(?:\s*[:=][^\s,;/]+|[^\s,;/]*)?"
)
_TOOL_REGISTRY_PROVIDER_SOURCE_ARTIFACT_KEYS = frozenset(
    {
        "provider_source",
        "provider_source_name",
        "tool_registry_provider_source",
    }
)
_TOOL_REGISTRY_PROVIDER_SOURCES_ARTIFACT_KEYS = frozenset(
    {
        "provider_sources",
        "tool_registry_provider_sources",
    }
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


def _impl__iter_tool_registry_provider_source_diagnostic_values(
    diagnostics: object,
):
    if not isinstance(diagnostics, dict):
        return
    for key in _TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS:
        if not key.endswith("_registry_sources"):
            continue
        values = diagnostics.get(key, ())
        if not isinstance(values, (list, tuple)):
            continue
        for value in values:
            if isinstance(value, str) and value.strip():
                yield value


def _impl__sanitize_tool_registry_file_diagnostics_with_provider_source_aliases(
    diagnostics: object,
    *,
    provider_source_aliases: Mapping[str, str] | None = None,
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
        alias_by_value = (
            _impl_build_safe_tool_registry_provider_source_alias_map(values)
            if key.endswith("_registry_sources")
            else {}
        )
        for raw_value in values:
            raw_value_key = str(raw_value)
            safe_value = (
                provider_source_aliases.get(raw_value_key)
                if provider_source_aliases is not None
                else None
            ) or alias_by_value.get(
                raw_value_key
            ) or _impl__sanitize_tool_registry_provider_source_name_for_artifact(
                raw_value
            )
            if not safe_value or safe_value in sanitized[key]:
                continue
            sanitized[key].append(safe_value)
    return _normalize_tool_registry_file_diagnostics(sanitized)


def _impl_sanitize_tool_registry_file_diagnostics(
    diagnostics: object,
) -> dict[str, tuple[str, ...]]:
    return _impl__sanitize_tool_registry_file_diagnostics_with_provider_source_aliases(
        diagnostics
    )


def _impl__sanitize_tool_registry_source_diagnostics_with_provider_source_aliases(
    source_diagnostics: object,
    *,
    provider_source_aliases: Mapping[str, str] | None = None,
) -> dict[str, dict[str, tuple[str, ...]]]:
    if not isinstance(source_diagnostics, dict):
        return {}
    alias_inputs: list[object] = list(source_diagnostics.keys())
    for diagnostics in source_diagnostics.values():
        alias_inputs.extend(
            _impl__iter_tool_registry_provider_source_diagnostic_values(diagnostics)
        )
    alias_by_source = dict(provider_source_aliases or {})
    alias_by_source.update(
        {
            source_name: alias
            for source_name, alias in _impl_build_safe_tool_registry_provider_source_alias_map(
                [
                    source_name
                    for source_name in alias_inputs
                    if str(source_name).strip()
                    and str(source_name) not in alias_by_source
                ]
            ).items()
            if source_name not in alias_by_source
        }
    )
    sanitized: dict[str, dict[str, tuple[str, ...]]] = {}
    for source_name, diagnostics in source_diagnostics.items():
        normalized_source_name = alias_by_source.get(
            str(source_name),
            _impl__sanitize_tool_registry_provider_source_name_for_artifact(
                source_name
            ),
        )
        if not normalized_source_name:
            continue
        sanitized[normalized_source_name] = _merge_tool_registry_file_diagnostics(
            sanitized.get(normalized_source_name),
            _impl__sanitize_tool_registry_file_diagnostics_with_provider_source_aliases(
                diagnostics,
                provider_source_aliases=alias_by_source,
            ),
        )
    return sanitized


def _impl_sanitize_tool_registry_source_diagnostics(
    source_diagnostics: object,
) -> dict[str, dict[str, tuple[str, ...]]]:
    return _impl__sanitize_tool_registry_source_diagnostics_with_provider_source_aliases(
        source_diagnostics
    )


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
        use_provider_source_aliases = str(raw_entry.get("target")) == "registry_sources"
        for key, value in raw_entry.items():
            if key == "values" and isinstance(value, (list, tuple)):
                alias_by_value = (
                    _impl_build_safe_tool_registry_provider_source_alias_map(value)
                    if use_provider_source_aliases
                    else {}
                )
                deduped_safe_values: list[str] = []
                for raw_value in value:
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


def _impl__sanitize_tool_registry_provider_source_name_for_artifact(
    provider_source_name: object,
) -> str:
    safe_value = _redact_tool_registry_diagnostic_value(
        str(provider_source_name).strip()
    )
    safe_value = _TOOL_REGISTRY_PROVIDER_SOURCE_SENSITIVE_TOKEN_RE.sub(
        "[redacted]",
        safe_value,
    )
    return safe_value or "default"


def _impl_build_safe_tool_registry_provider_source_alias_map(
    source_names: Sequence[object],
) -> dict[str, str]:
    raw_source_names = [str(source_name) for source_name in source_names]
    base_alias_by_raw = {
        source_name: _impl__sanitize_tool_registry_provider_source_name_for_artifact(
            source_name
        )
        for source_name in raw_source_names
    }
    base_alias_counts: dict[str, int] = {}
    for base_alias in base_alias_by_raw.values():
        base_alias_counts[base_alias] = base_alias_counts.get(base_alias, 0) + 1

    collision_index_by_base_alias: dict[str, int] = {}
    alias_by_raw: dict[str, str] = {}
    used_aliases: set[str] = set()
    for source_name in raw_source_names:
        if source_name in alias_by_raw:
            continue
        base_alias = base_alias_by_raw[source_name]
        if base_alias_counts.get(base_alias, 0) <= 1:
            alias = base_alias
        else:
            next_index = collision_index_by_base_alias.get(base_alias, 0) + 1
            collision_index_by_base_alias[base_alias] = next_index
            alias = f"{base_alias}#{next_index}"

        deduped_alias = alias
        dedupe_index = 1
        while deduped_alias in used_aliases:
            dedupe_index += 1
            deduped_alias = f"{alias}-{dedupe_index}"
        used_aliases.add(deduped_alias)
        alias_by_raw[source_name] = deduped_alias
    return alias_by_raw


def _impl__sanitize_tool_registry_provider_sources_for_artifact(
    provider_sources: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> dict[str, ToolRegistryProvider]:
    if not isinstance(provider_sources, dict):
        return {}
    sanitized: dict[str, ToolRegistryProvider] = {}
    alias_by_source = provider_source_aliases or (
        _impl_build_safe_tool_registry_provider_source_alias_map(
            list(provider_sources.keys())
        )
    )
    for source_name, provider in provider_sources.items():
        safe_source_name = alias_by_source.get(
            str(source_name),
            _impl__sanitize_tool_registry_provider_source_name_for_artifact(source_name),
        )
        if safe_source_name in sanitized:
            continue
        sanitized[safe_source_name] = provider
    return sanitized


def _impl_resolve_unique_tool_registry_provider_source_alias(
    *,
    settings: object,
    tool_registry_provider_source: object,
) -> str:
    raw_requested_source = str(tool_registry_provider_source)
    requested_source = raw_requested_source.strip()
    if not requested_source:
        return raw_requested_source

    source_artifacts = build_tool_registry_provider_sources_from_settings_artifacts(
        settings=settings
    )
    named_sources = source_artifacts["sources"]
    normalized_source_specs = get_tool_registry_provider_source_specs_from_settings(
        settings=settings
    )
    available_sources = ["default"]
    available_sources.extend(
        name
        for name in sorted({*named_sources.keys(), *normalized_source_specs.keys()})
        if name and name != "default"
    )
    if raw_requested_source in available_sources:
        return raw_requested_source

    alias_by_source = build_safe_tool_registry_provider_source_alias_map(
        available_sources
    )
    alias_matches = [
        source_name
        for source_name, alias in alias_by_source.items()
        if alias == requested_source
    ]
    if len(alias_matches) == 1:
        return alias_matches[0]

    alias_matches = [
        source_name
        for source_name in available_sources
        if _impl__sanitize_tool_registry_provider_source_name_for_artifact(source_name)
        == requested_source
    ]
    if len(alias_matches) == 1:
        return alias_matches[0]
    return raw_requested_source


def _impl__sanitize_tool_registry_provider_source_fields_for_artifact(
    payload: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> object:
    if isinstance(payload, dict):
        sanitized: dict[object, object] = {}
        for key, value in payload.items():
            safe_key = str(key)
            if safe_key in _TOOL_REGISTRY_PROVIDER_SOURCE_ARTIFACT_KEYS:
                sanitized[key] = (
                    (provider_source_aliases or {}).get(
                        str(value),
                        _impl__sanitize_tool_registry_provider_source_name_for_artifact(
                            value
                        ),
                    )
                )
                continue
            if (
                safe_key in _TOOL_REGISTRY_PROVIDER_SOURCES_ARTIFACT_KEYS
                and isinstance(value, (list, tuple))
            ):
                alias_by_source = (
                    provider_source_aliases
                    or _impl_build_safe_tool_registry_provider_source_alias_map(
                        [
                            source_name
                            for source_name in value
                            if isinstance(source_name, str) and source_name.strip()
                        ]
                    )
                )
                sanitized[key] = [
                    alias_by_source.get(
                        source_name,
                        _impl__sanitize_tool_registry_provider_source_name_for_artifact(
                            source_name
                        ),
                    )
                    if isinstance(source_name, str) and source_name.strip()
                    else source_name
                    for source_name in value
                ]
                continue
            sanitized[key] = (
                _impl__sanitize_tool_registry_provider_source_fields_for_artifact(
                    value,
                    provider_source_aliases=provider_source_aliases,
                )
            )
        return sanitized
    if isinstance(payload, tuple):
        return tuple(
            _impl__sanitize_tool_registry_provider_source_fields_for_artifact(
                value,
                provider_source_aliases=provider_source_aliases,
            )
            for value in payload
        )
    if isinstance(payload, list):
        return [
            _impl__sanitize_tool_registry_provider_source_fields_for_artifact(
                value,
                provider_source_aliases=provider_source_aliases,
            )
            for value in payload
        ]
    return payload


def _impl__coerce_tool_registry_diagnostics_count(value: object) -> int:
    if isinstance(value, str):
        value = value.strip()
    if value in (None, ""):
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _impl__build_tool_registry_diagnostics_summary_model_from_payload(
    summary_payload: dict[str, object],
) -> ToolRegistryDiagnosticsSummaryModel:
    entries = sanitize_tool_registry_diagnostics_summary_entries(
        summary_payload.get("entries", ())
    )
    has_value_entries = any(
        isinstance(entry.get("values"), (list, tuple)) for entry in entries
    )
    if not has_value_entries:
        return ToolRegistryDiagnosticsSummaryModel(
            has_diagnostics=bool(summary_payload.get("has_diagnostics", False)),
            skipped_total=_impl__coerce_tool_registry_diagnostics_count(
                summary_payload.get("skipped_total", 0)
            ),
            missing_total=_impl__coerce_tool_registry_diagnostics_count(
                summary_payload.get("missing_total", 0)
            ),
            total=_impl__coerce_tool_registry_diagnostics_count(
                summary_payload.get("total", 0)
            ),
            entries=entries,
        )

    skipped_total = 0
    missing_total = 0
    total = 0
    normalized_entries: list[dict[str, object]] = []
    for entry in entries:
        normalized_entry = dict(entry)
        values = normalized_entry.get("values")
        count = len(values) if isinstance(values, (list, tuple)) else 0
        normalized_entry["count"] = count
        normalized_entries.append(normalized_entry)
        total += count
        kind = str(normalized_entry.get("kind", "")).strip().lower()
        if kind == "skipped":
            skipped_total += count
        elif kind == "missing":
            missing_total += count
    return ToolRegistryDiagnosticsSummaryModel(
        has_diagnostics=total > 0,
        skipped_total=skipped_total,
        missing_total=missing_total,
        total=total,
        entries=tuple(normalized_entries),
    )


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


from app.services.module_export_utils import install_rebound_exports
from app.services import tool_runtime_registry_settings as _registry_settings

install_rebound_exports(
    source_module=_registry_settings,
    target_namespace=globals(),
    export_names=_registry_settings._REGISTRY_SETTINGS_IMPL_EXPORTS,
)
from app.services import tool_runtime_registry_runtime as _registry_runtime

for _runtime_impl_name in _registry_runtime._RUNTIME_IMPL_EXPORTS:
    globals()[_runtime_impl_name] = getattr(_registry_runtime, _runtime_impl_name)


from app.services import tool_runtime_registry_public as _registry_public
_registry_public.install_tool_runtime_registry_public_wrappers(globals())
_registry_runtime.bind_tool_runtime_registry_runtime_public_names(globals())
