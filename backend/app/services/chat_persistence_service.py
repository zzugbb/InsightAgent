from __future__ import annotations

import json
import re
from collections import UserDict, UserList, UserString
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.config import get_settings
from app.db import get_db_connection
from app.schemas.trace import TraceStep, parse_trace_steps
from app.services.task_status_service import (
    normalize_task_status,
    task_status_label,
    task_status_rank,
)
from app.services.chroma_rag_service import normalize_knowledge_base_id
from app.services.tool_runtime import (
    _get_safe_http_json_request_id_display_value,
    _normalize_http_json_output_shape,
    _normalize_http_json_safe_output_shape,
    _redact_http_json_raw_fallback_value,
    _redact_http_json_sensitive_payload_value,
    _sanitize_tool_runtime_provider_source_name_for_artifact,
    _redact_tool_registry_diagnostic_value,
    build_safe_tool_registry_provider_source_alias_map,
    get_configured_tool_registry_provider,
    get_tool_display_name,
    normalize_tool_registry_name,
    resolve_unique_tool_registry_provider_source_alias,
    sanitize_tool_registry_diagnostics_artifact_payload,
)


def _now_iso() -> str:
    return datetime.now().isoformat()


def _build_session_title(prompt: str) -> str:
    normalized = " ".join(prompt.strip().split())
    return normalized[:60] or "New Session"


def _is_placeholder_session_title(title: object) -> bool:
    if not isinstance(title, str):
        return True
    raw = title.strip()
    if not raw:
        return True
    lowered = raw.lower()
    if lowered in {"新会话", "new session"}:
        return True
    if lowered.startswith("会话 ") or lowered.startswith("session "):
        return True
    return False


def _normalize_trace_steps(trace_steps: list[dict]) -> list[dict]:
    normalized_steps: list[dict] = []
    for index, step in enumerate(trace_steps, start=1):
        normalized_step = dict(step)
        normalized_step["seq"] = (
            normalized_step["seq"]
            if isinstance(normalized_step.get("seq"), int)
            else index
        )
        normalized_steps.append(normalized_step)
    return normalized_steps


def _load_trace_steps_from_trace_json(trace_json: object) -> list[dict]:
    if not isinstance(trace_json, str) or not trace_json.strip():
        return []
    try:
        loaded = json.loads(trace_json)
    except Exception:
        return []
    if not isinstance(loaded, list):
        return []
    return _normalize_trace_steps([item for item in loaded if isinstance(item, dict)])


def _load_parsed_trace_steps_from_trace_json(trace_json: object) -> list[TraceStep]:
    return parse_trace_steps(_load_trace_steps_from_trace_json(trace_json))


def _parse_usage_json_blob(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _extract_task_governance_from_trace_steps(
    trace_steps: list[dict],
) -> dict[str, object] | None:
    for item in trace_steps:
        if not isinstance(item, dict):
            continue
        meta = item.get("meta")
        if not isinstance(meta, dict):
            continue

        profile = (
            meta.get("tool_registry_profile")
            if isinstance(meta.get("tool_registry_profile"), str)
            else None
        )
        provider_source = (
            meta.get("tool_registry_provider_source")
            if isinstance(meta.get("tool_registry_provider_source"), str)
            else None
        )
        allowed_tool_names = [
            value
            for value in meta.get("allowed_tool_names", [])
            if isinstance(value, str)
        ]
        allowed_tool_labels = [
            value
            for value in meta.get("allowed_tool_labels", [])
            if isinstance(value, str)
        ]
        normalized = _normalize_task_governance_dict(
            {
                "profile": profile,
                "provider_source": provider_source,
                "allowed_tool_names": allowed_tool_names,
                "allowed_tool_labels": allowed_tool_labels,
            }
        )
        if normalized is None or not _has_task_governance_values(normalized):
            continue
        return normalized
    return None

def _serialize_task_governance_columns(
    trace_steps: list[dict],
) -> tuple[str | None, str | None, str | None, str | None]:
    governance = _extract_task_governance_from_trace_steps(trace_steps)
    if governance is None:
        return None, None, None, None
    allowed_tool_names = governance["allowed_tool_names"]
    allowed_tool_labels = governance["allowed_tool_labels"]
    return (
        governance["profile"] if isinstance(governance["profile"], str) else None,
        governance["provider_source"]
        if isinstance(governance["provider_source"], str)
        else None,
        json.dumps(list(allowed_tool_names), ensure_ascii=False)
        if isinstance(allowed_tool_names, (list, tuple))
        else None,
        json.dumps(list(allowed_tool_labels), ensure_ascii=False)
        if isinstance(allowed_tool_labels, (list, tuple))
        else None,
    )


def _parse_task_governance_json_list_blob(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [item for item in value if isinstance(item, str)]
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, str)]


def _normalize_governance_string_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _normalize_governance_summary_string_list(value: object) -> list[str]:
    return sorted(set(_normalize_governance_string_list(value)))


def _normalize_governance_filter_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized_values = {
        normalized
        for item in value
        if isinstance(item, str)
        for normalized in [_normalize_governance_filter(item)]
        if normalized is not None
    }
    return sorted(normalized_values)


def _build_governance_registry_provider(
    *,
    profile: object,
    provider_source: object,
):
    normalized_profile = (
        profile.strip().lower() if isinstance(profile, str) and profile.strip() else None
    )
    normalized_provider_source = (
        provider_source.strip().lower()
        if isinstance(provider_source, str) and provider_source.strip()
        else None
    )
    if normalized_profile is None and normalized_provider_source is None:
        return None

    runtime_settings = get_settings()
    model_copy = getattr(runtime_settings, "model_copy", None)
    if callable(model_copy):
        effective_settings = model_copy(
            update={
                "tool_registry_profile": (
                    normalized_profile
                    if normalized_profile is not None
                    else getattr(runtime_settings, "tool_registry_profile", None)
                ),
                "tool_registry_provider_source": (
                    normalized_provider_source
                    if normalized_provider_source is not None
                    else getattr(runtime_settings, "tool_registry_provider_source", None)
                ),
            }
        )
    else:
        effective_settings = SimpleNamespace(
            tool_registry_profile=(
                normalized_profile
                if normalized_profile is not None
                else getattr(runtime_settings, "tool_registry_profile", None)
            ),
            tool_registry_provider_source=(
                normalized_provider_source
                if normalized_provider_source is not None
                else getattr(runtime_settings, "tool_registry_provider_source", None)
            ),
            tool_registry_overrides_json=getattr(
                runtime_settings, "tool_registry_overrides_json", None
            ),
            tool_registry_extra_tools_json=getattr(
                runtime_settings, "tool_registry_extra_tools_json", None
            ),
            tool_registry_loaders_json=getattr(
                runtime_settings, "tool_registry_loaders_json", None
            ),
            tool_registry_loader_factories_json=getattr(
                runtime_settings, "tool_registry_loader_factories_json", None
            ),
            tool_registry_providers_json=getattr(
                runtime_settings, "tool_registry_providers_json", None
            ),
            tool_registry_provider_factories_json=getattr(
                runtime_settings, "tool_registry_provider_factories_json", None
            ),
            tool_registry_provider_sources_json=getattr(
                runtime_settings, "tool_registry_provider_sources_json", None
            ),
        )
    return get_configured_tool_registry_provider(settings=effective_settings)


def _normalize_governance_allowed_tool_labels(
    allowed_tool_names: object,
    allowed_tool_labels: object,
    *,
    profile: object = None,
    provider_source: object = None,
) -> list[str]:
    normalized_names = _normalize_governance_string_list(allowed_tool_names)
    normalized_labels = _normalize_governance_string_list(allowed_tool_labels)
    if not normalized_names:
        return normalized_labels

    registry_provider = _build_governance_registry_provider(
        profile=profile,
        provider_source=provider_source,
    )
    resolved_labels: list[str] = []
    for index, tool_name in enumerate(normalized_names):
        current_label = (
            normalized_labels[index] if index < len(normalized_labels) else None
        )
        canonical_label = get_tool_display_name(
            tool_name,
            registry_provider=registry_provider,
        )
        if current_label is None:
            resolved_labels.append(canonical_label)
            continue
        if normalize_tool_registry_name(current_label) == tool_name:
            resolved_labels.append(canonical_label)
            continue
        if normalize_tool_registry_name(current_label) == normalize_tool_registry_name(
            canonical_label
        ):
            resolved_labels.append(canonical_label)
            continue
        resolved_labels.append(current_label)

    if len(normalized_labels) > len(normalized_names):
        resolved_labels.extend(normalized_labels[len(normalized_names) :])
    return _normalize_governance_string_list(resolved_labels)


def _has_task_governance_values(governance: object) -> bool:
    if not isinstance(governance, dict):
        return False
    if isinstance(governance.get("profile"), str):
        return True
    if isinstance(governance.get("provider_source"), str):
        return True
    if isinstance(governance.get("allowed_tool_names"), (list, tuple)) and bool(
        governance.get("allowed_tool_names")
    ):
        return True
    if isinstance(governance.get("allowed_tool_labels"), (list, tuple)) and bool(
        governance.get("allowed_tool_labels")
    ):
        return True
    return False


def _has_session_governance_values(governance: object) -> bool:
    if not isinstance(governance, dict):
        return False
    if isinstance(governance.get("profiles"), (list, tuple)) and bool(
        governance.get("profiles")
    ):
        return True
    if isinstance(governance.get("provider_sources"), (list, tuple)) and bool(
        governance.get("provider_sources")
    ):
        return True
    if isinstance(governance.get("allowed_tool_names"), (list, tuple)) and bool(
        governance.get("allowed_tool_names")
    ):
        return True
    if isinstance(governance.get("allowed_tool_labels"), (list, tuple)) and bool(
        governance.get("allowed_tool_labels")
    ):
        return True
    return False


def _extract_task_governance_from_task_row(
    task: dict[str, object],
) -> dict[str, object] | None:
    raw_profile = task.get("tool_registry_profile")
    raw_provider_source = task.get("tool_registry_provider_source")
    profile = raw_profile if isinstance(raw_profile, str) else None
    provider_source = raw_provider_source if isinstance(raw_provider_source, str) else None
    allowed_tool_names = _parse_task_governance_json_list_blob(
        task.get("allowed_tool_names_json")
    )
    allowed_tool_labels = _parse_task_governance_json_list_blob(
        task.get("allowed_tool_labels_json")
    )
    normalized = _normalize_task_governance_dict(
        {
            "profile": profile,
            "provider_source": provider_source,
            "allowed_tool_names": allowed_tool_names,
            "allowed_tool_labels": allowed_tool_labels,
        }
    )
    if normalized is not None:
        return normalized
    trace_steps = _load_trace_steps_from_trace_json(task.get("trace_json"))
    if not trace_steps:
        return None
    return _extract_task_governance_from_trace_steps(trace_steps)


def _with_task_governance(task: dict[str, object]) -> dict[str, object]:
    governance = _extract_task_governance_from_task_row(task)
    return {
        **{
            key: value
            for key, value in task.items()
            if key
            not in {
                "tool_registry_profile",
                "tool_registry_provider_source",
                "allowed_tool_names_json",
                "allowed_tool_labels_json",
            }
        },
        "governance": governance,
    }


def _normalize_task_governance_dict(
    governance: object,
) -> dict[str, object] | None:
    if not isinstance(governance, dict):
        return None
    normalized_profile = (
        _normalize_governance_filter(governance.get("profile"))
        if isinstance(governance.get("profile"), str)
        else None
    )
    normalized_provider_source = (
        _normalize_governance_filter(governance.get("provider_source"))
        if isinstance(governance.get("provider_source"), str)
        else None
    )
    normalized = {
        "profile": normalized_profile,
        "provider_source": normalized_provider_source,
        "allowed_tool_names": _normalize_governance_string_list(
            governance.get("allowed_tool_names")
        ),
        "allowed_tool_labels": _normalize_governance_allowed_tool_labels(
            governance.get("allowed_tool_names"),
            governance.get("allowed_tool_labels"),
            profile=normalized_profile,
            provider_source=normalized_provider_source,
        ),
    }
    if not _has_task_governance_values(normalized):
        return None
    return normalized


def _normalize_session_governance_summary_dict(
    governance: object,
) -> dict[str, object] | None:
    if not isinstance(governance, dict):
        return None
    normalized_profiles = _normalize_governance_filter_list(governance.get("profiles"))
    normalized_provider_sources = _normalize_governance_filter_list(
        governance.get("provider_sources")
    )
    normalized = {
        "profiles": normalized_profiles,
        "provider_sources": normalized_provider_sources,
        "allowed_tool_names": _normalize_governance_summary_string_list(
            governance.get("allowed_tool_names")
        ),
        "allowed_tool_labels": _normalize_governance_summary_string_list(
            _normalize_governance_allowed_tool_labels(
                governance.get("allowed_tool_names"),
                governance.get("allowed_tool_labels"),
                profile=normalized_profiles[0] if len(normalized_profiles) == 1 else None,
                provider_source=(
                    normalized_provider_sources[0]
                    if len(normalized_provider_sources) == 1
                    else None
                ),
            )
        ),
    }
    if not _has_session_governance_values(normalized):
        return None
    return normalized


def _normalize_task_governance_payload(value: object) -> dict[str, object] | None:
    coerced = _coerce_payload_mapping_or_none(value)
    if coerced is None:
        return None
    normalized = _normalize_task_governance_dict(coerced)
    if normalized is None:
        return coerced
    compact: dict[str, object] = {}
    if isinstance(normalized.get("profile"), str):
        compact["profile"] = normalized["profile"]
    if isinstance(normalized.get("provider_source"), str):
        compact["provider_source"] = normalized["provider_source"]
    if isinstance(normalized.get("allowed_tool_names"), list) and normalized.get(
        "allowed_tool_names"
    ):
        compact["allowed_tool_names"] = list(normalized["allowed_tool_names"])
    if isinstance(normalized.get("allowed_tool_labels"), list) and normalized.get(
        "allowed_tool_labels"
    ):
        compact["allowed_tool_labels"] = list(normalized["allowed_tool_labels"])
    return compact


def _normalize_task_governance_payload_or_original(value: object) -> object:
    if isinstance(value, dict):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return _normalize_task_governance_payload(dumped)
    return value


def _normalize_task_governance_payload_for_response(
    value: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> object:
    normalized = _normalize_task_governance_payload(value)
    return _sanitize_task_governance_provider_source_values_for_export(
        normalized,
        provider_source_aliases=provider_source_aliases,
    )


def _normalize_session_governance_payload_for_response(
    value: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> object:
    normalized = _normalize_session_governance_payload_or_original(value)
    return _sanitize_session_governance_provider_source_values_for_export(
        normalized,
        provider_source_aliases=provider_source_aliases,
    )


def _sanitize_governance_provider_source_with_aliases(
    provider_source: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> str:
    if isinstance(provider_source, str):
        return (provider_source_aliases or {}).get(
            provider_source,
            _sanitize_tool_runtime_provider_source_name_for_artifact(provider_source),
        )
    return _sanitize_tool_runtime_provider_source_name_for_artifact(provider_source)


def _sanitize_task_governance_provider_source_values_for_export(
    value: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> object:
    governance = _coerce_payload_mapping_or_none(value)
    if governance is None:
        return value
    provider_source = governance.get("provider_source")
    if isinstance(provider_source, str) and provider_source.strip():
        safe_provider_source = _sanitize_governance_provider_source_with_aliases(
            provider_source,
            provider_source_aliases=provider_source_aliases,
        )
        if safe_provider_source != provider_source:
            sanitized = dict(governance)
            sanitized["provider_source"] = safe_provider_source
            return sanitized
    return value


def _sanitize_session_governance_provider_source_values_for_export(
    value: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> object:
    governance = _coerce_payload_mapping_or_none(value)
    if governance is None:
        return value
    provider_sources = governance.get("provider_sources")
    if isinstance(provider_sources, (list, tuple)):
        alias_by_source = provider_source_aliases or (
            build_safe_tool_registry_provider_source_alias_map(
                [
                    source
                    for source in provider_sources
                    if isinstance(source, str) and source.strip()
                ]
            )
        )
        safe_provider_sources = [
            alias_by_source.get(
                item,
                _sanitize_tool_runtime_provider_source_name_for_artifact(item),
            )
            if isinstance(item, str) and item.strip()
            else item
            for item in provider_sources
        ]
        if list(provider_sources) != safe_provider_sources:
            sanitized = dict(governance)
            sanitized["provider_sources"] = safe_provider_sources
            return sanitized
    return value


def build_session_export_provider_source_aliases(
    export_summary: object,
) -> dict[str, str]:
    summary = _coerce_payload_mapping_or_none(export_summary)
    if summary is None:
        return {}
    source_names: list[str] = []
    _append_governance_provider_source_alias_inputs(
        source_names,
        summary.get("governance"),
    )
    tasks = summary.get("tasks")
    if isinstance(tasks, list):
        for task in tasks:
            task_summary = _coerce_payload_mapping_or_none(task)
            if task_summary is None:
                continue
            _append_governance_provider_source_alias_inputs(
                source_names,
                task_summary.get("governance"),
            )
            for nested_key in ("task", "trace"):
                nested_summary = _coerce_payload_mapping_or_none(
                    task_summary.get(nested_key)
                )
                if nested_summary is None:
                    continue
                _append_governance_provider_source_alias_inputs(
                    source_names,
                    nested_summary.get("governance"),
                )
    return build_safe_tool_registry_provider_source_alias_map(source_names)


def sanitize_session_export_governance_provider_source_values(
    export_summary: object,
) -> object:
    summary = _coerce_payload_mapping_or_none(export_summary)
    if summary is None:
        return export_summary
    provider_source_aliases = build_session_export_provider_source_aliases(summary)
    if not provider_source_aliases:
        return export_summary

    sanitized = dict(summary)
    if "governance" in sanitized:
        sanitized["governance"] = (
            _sanitize_session_governance_provider_source_values_for_export(
                sanitized.get("governance"),
                provider_source_aliases=provider_source_aliases,
            )
        )
    tasks = sanitized.get("tasks")
    if isinstance(tasks, list):
        sanitized_tasks: list[object] = []
        for task in tasks:
            task_summary = _coerce_payload_mapping_or_none(task)
            if task_summary is None:
                sanitized_tasks.append(task)
                continue
            normalized_task = dict(task_summary)
            if "governance" in normalized_task:
                normalized_task["governance"] = (
                    _sanitize_task_governance_provider_source_values_for_export(
                        normalized_task.get("governance"),
                        provider_source_aliases=provider_source_aliases,
                    )
                )
            sanitized_tasks.append(normalized_task)
        sanitized["tasks"] = sanitized_tasks
    return sanitized


def _append_governance_provider_source_alias_inputs(
    source_names: list[str],
    governance: object,
) -> None:
    governance_payload = _coerce_payload_mapping_or_none(governance)
    if governance_payload is None:
        return
    provider_sources = governance_payload.get("provider_sources")
    if isinstance(provider_sources, (list, tuple)):
        source_names.extend(
            source
            for source in provider_sources
            if isinstance(source, str) and source.strip()
        )
    provider_source = governance_payload.get("provider_source")
    if isinstance(provider_source, str) and provider_source.strip():
        source_names.append(provider_source)


def _build_usage_dashboard_provider_source_aliases(
    *,
    session_rows: list[dict[str, object]],
    top_task_rows: list[dict[str, object]],
) -> dict[str, str]:
    source_names: list[str] = []
    for row in session_rows:
        _append_governance_provider_source_alias_inputs(
            source_names,
            row.get("governance"),
        )
    for row in top_task_rows:
        _append_governance_provider_source_alias_inputs(
            source_names,
            row.get("governance"),
        )
    return build_safe_tool_registry_provider_source_alias_map(source_names)


_PROVIDER_SOURCE_TRACE_META_KEYS = frozenset(
    {
        "provider_source",
        "provider_source_name",
        "tool_registry_provider_source",
    }
)
_PROVIDER_SOURCES_TRACE_META_KEYS = frozenset(
    {
        "provider_sources",
        "tool_registry_provider_sources",
    }
)


def _append_trace_provider_source_alias_inputs(
    source_names: list[str],
    value: object,
) -> None:
    value = _normalize_trace_json_compatible_value(value)
    if isinstance(value, dict):
        for key, item in value.items():
            safe_key = str(key)
            if safe_key in _PROVIDER_SOURCE_TRACE_META_KEYS:
                if isinstance(item, str) and item.strip():
                    source_names.append(item)
                continue
            if safe_key in _PROVIDER_SOURCES_TRACE_META_KEYS and isinstance(
                item, (list, tuple)
            ):
                source_names.extend(
                    source
                    for source in item
                    if isinstance(source, str) and source.strip()
                )
                continue
            _append_trace_provider_source_alias_inputs(source_names, item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _append_trace_provider_source_alias_inputs(source_names, item)


def _build_trace_steps_provider_source_aliases(
    trace_steps: list[TraceStep],
) -> dict[str, str]:
    source_names: list[str] = []
    for step in trace_steps:
        meta = getattr(step, "meta", None)
        if meta is None:
            continue
        meta_payload = (
            meta.model_dump(exclude_none=True)
            if hasattr(meta, "model_dump")
            else dict(meta)
            if isinstance(meta, dict)
            else None
        )
        if meta_payload is None:
            continue
        _append_trace_provider_source_alias_inputs(source_names, meta_payload)
    return build_safe_tool_registry_provider_source_alias_map(source_names)


def _sanitize_trace_provider_source_meta_values_for_export(
    value: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> object:
    if isinstance(value, dict):
        sanitized: dict[object, object] = {}
        for key, item in value.items():
            safe_key = str(key)
            if safe_key in _PROVIDER_SOURCE_TRACE_META_KEYS:
                if isinstance(item, str) and item.strip():
                    sanitized[key] = (
                        provider_source_aliases.get(
                            item,
                            _sanitize_tool_runtime_provider_source_name_for_artifact(
                                item
                            ),
                        )
                        if provider_source_aliases is not None
                        else _sanitize_tool_runtime_provider_source_name_for_artifact(
                            item
                        )
                    )
                else:
                    sanitized[key] = item
                continue
            if (
                safe_key in _PROVIDER_SOURCES_TRACE_META_KEYS
                and isinstance(item, (list, tuple))
            ):
                alias_by_source = provider_source_aliases or (
                    build_safe_tool_registry_provider_source_alias_map(
                        [
                            source
                            for source in item
                            if isinstance(source, str) and source.strip()
                        ]
                    )
                )
                sanitized[key] = [
                    alias_by_source.get(
                        source,
                        _sanitize_tool_runtime_provider_source_name_for_artifact(
                            source
                        ),
                    )
                    if isinstance(source, str) and source.strip()
                    else source
                    for source in item
                ]
                continue
            sanitized[key] = _sanitize_trace_provider_source_meta_values_for_export(
                item,
                provider_source_aliases=provider_source_aliases,
            )
        return sanitized
    if isinstance(value, list):
        return [
            _sanitize_trace_provider_source_meta_values_for_export(
                item,
                provider_source_aliases=provider_source_aliases,
            )
            for item in value
        ]
    if isinstance(value, tuple):
        return tuple(
            _sanitize_trace_provider_source_meta_values_for_export(
                item,
                provider_source_aliases=provider_source_aliases,
            )
            for item in value
        )
    return value


def _normalize_session_governance_payload_or_original(value: object) -> object:
    if isinstance(value, dict):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return _normalize_session_governance_summary_dict(dumped) or dict(dumped)
    return value


def ensure_session(prompt: str, user_id: str, session_id: str | None = None) -> str:
    current_time = _now_iso()
    resolved_session_id = session_id or str(uuid4())
    title = _build_session_title(prompt)

    with get_db_connection() as connection:
        existing = connection.execute(
            "SELECT id, user_id, title FROM sessions WHERE id = ?",
            (resolved_session_id,),
        ).fetchone()

        if existing is None:
            connection.execute(
                """
                INSERT INTO sessions(id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (resolved_session_id, user_id, title, current_time, current_time),
            )
        else:
            owner = existing["user_id"]
            if owner and owner != user_id:
                raise ValueError("session does not belong to current user")
            message_count_row = connection.execute(
                """
                SELECT COUNT(*) AS n
                FROM messages
                WHERE session_id = ? AND user_id = ?
                """,
                (resolved_session_id, user_id),
            ).fetchone()
            message_count = int(message_count_row["n"]) if message_count_row else 0
            should_autofill_title = (
                message_count == 0
                and _is_placeholder_session_title(existing["title"])
            )
            connection.execute(
                """
                UPDATE sessions
                SET
                    user_id = COALESCE(user_id, ?),
                    title = CASE
                        WHEN ? THEN ?
                        ELSE title
                    END,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    user_id,
                    should_autofill_title,
                    title,
                    current_time,
                    resolved_session_id,
                ),
            )
        connection.commit()

    return resolved_session_id


def create_task(
    session_id: str,
    prompt: str,
    user_id: str,
    task_id: str | None = None,
    status: str = "running",
) -> str:
    current_time = _now_iso()
    resolved_task_id = task_id or str(uuid4())

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO tasks(id, user_id, session_id, prompt, status, trace_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_task_id,
                user_id,
                session_id,
                prompt,
                status,
                None,
                current_time,
                current_time,
            ),
        )
        connection.commit()

    return resolved_task_id


def create_message(
    session_id: str,
    user_id: str,
    role: str,
    content: str,
    task_id: str | None = None,
) -> str:
    message_id = str(uuid4())
    current_time = _now_iso()

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO messages(id, user_id, session_id, task_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (message_id, user_id, session_id, task_id, role, content, current_time),
        )
        connection.execute(
            """
            UPDATE sessions
            SET updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (current_time, session_id, user_id),
        )
        connection.commit()

    return message_id


def update_task_status(task_id: str, status: str, user_id: str) -> None:
    current_time = _now_iso()

    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE tasks
            SET status = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (status, current_time, task_id, user_id),
        )
        connection.commit()


def mark_task_cancel_requested(
    *,
    task_id: str,
    user_id: str,
) -> int:
    current_time = _now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET status = ?,
                updated_at = ?,
                execution_owner_id = NULL,
                execution_heartbeat_at = NULL
            WHERE id = ? AND user_id = ?
              AND LOWER(status) IN ('pending', 'queued', 'running')
            """,
            ("cancelled", current_time, task_id, user_id),
        )
        connection.commit()
        return max(0, int(getattr(cursor, "rowcount", 0) or 0))


def mark_task_queued_waiting(
    *,
    task_id: str,
    user_id: str,
) -> int:
    current_time = _now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET status = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
              AND LOWER(status) IN ('pending', 'queued')
            """,
            ("queued", current_time, task_id, user_id),
        )
        connection.commit()
        return max(0, int(getattr(cursor, "rowcount", 0) or 0))


def get_task_execution_owner_id(settings: object | None = None) -> str:
    raw_owner_id = (
        getattr(settings, "task_execution_owner_id", None)
        if settings is not None
        else getattr(get_settings(), "task_execution_owner_id", None)
    )
    normalized = str(raw_owner_id or "").strip()
    return normalized or "default"


def get_task_execution_stale_after_sec(settings: object | None = None) -> float:
    raw_stale_after = (
        getattr(settings, "task_execution_stale_after_sec", None)
        if settings is not None
        else getattr(get_settings(), "task_execution_stale_after_sec", None)
    )
    try:
        stale_after = float(raw_stale_after or 0)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, stale_after)


def mark_task_running_started(
    *,
    task_id: str,
    user_id: str,
    execution_owner_id: str,
) -> int:
    current_time = _now_iso()
    owner_id = get_task_execution_owner_id(
        SimpleNamespace(task_execution_owner_id=execution_owner_id)
    )
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET
                status = ?,
                updated_at = ?,
                execution_owner_id = ?,
                execution_heartbeat_at = ?
            WHERE (
                LOWER(status) IN ('queued', 'pending')
                OR (
                    LOWER(status) = ?
                    AND (
                        execution_owner_id IS NULL
                        OR TRIM(execution_owner_id) = ''
                        OR execution_owner_id = ?
                    )
                )
              )
              AND id = ? AND user_id = ?
            """,
            (
                "running",
                current_time,
                owner_id,
                current_time,
                "running",
                owner_id,
                task_id,
                user_id,
            ),
        )
        connection.commit()
        return max(0, int(getattr(cursor, "rowcount", 0) or 0))


def touch_task_execution_heartbeat(
    *,
    task_id: str,
    user_id: str,
    execution_owner_id: str,
) -> int:
    current_time = _now_iso()
    owner_id = get_task_execution_owner_id(
        SimpleNamespace(task_execution_owner_id=execution_owner_id)
    )
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET
                updated_at = ?,
                execution_heartbeat_at = ?
            WHERE id = ?
              AND user_id = ?
              AND LOWER(status) = ?
              AND execution_owner_id = ?
            """,
            (current_time, current_time, task_id, user_id, "running", owner_id),
        )
        connection.commit()
        return max(0, int(getattr(cursor, "rowcount", 0) or 0))


def recover_orphaned_running_tasks_on_startup(
    *,
    execution_owner_id: str | None = None,
    execution_stale_after_sec: float | None = None,
) -> int:
    current_time = _now_iso()
    owner_id = get_task_execution_owner_id(
        SimpleNamespace(task_execution_owner_id=execution_owner_id)
    )
    stale_after_sec = (
        get_task_execution_stale_after_sec(
            SimpleNamespace(task_execution_stale_after_sec=execution_stale_after_sec)
        )
        if execution_stale_after_sec is not None
        else get_task_execution_stale_after_sec()
    )
    owner_clauses = [
        "execution_owner_id IS NULL",
        "TRIM(execution_owner_id) = ''",
        "execution_owner_id = ?",
    ]
    params: list[object] = ["failed", current_time, "running", owner_id]
    if stale_after_sec > 0:
        try:
            cutoff_time = datetime.fromisoformat(current_time) - timedelta(
                seconds=stale_after_sec
            )
        except ValueError:
            cutoff_time = datetime.now() - timedelta(seconds=stale_after_sec)
        owner_clauses.extend(
            [
                "execution_heartbeat_at IS NULL",
                "execution_heartbeat_at < ?",
            ]
        )
        params.append(cutoff_time.isoformat())
    owner_condition = "\n                OR ".join(owner_clauses)
    with get_db_connection() as connection:
        cursor = connection.execute(
            f"""
            UPDATE tasks
            SET
                status = ?,
                updated_at = ?,
                execution_owner_id = NULL,
                execution_heartbeat_at = NULL
            WHERE LOWER(status) = ?
              AND (
                {owner_condition}
              )
            """,
            tuple(params),
        )
        connection.commit()
        return max(0, int(getattr(cursor, "rowcount", 0) or 0))


def update_task_trace_steps(task_id: str, trace_steps: list[dict], user_id: str) -> None:
    """流式执行过程中写入部分 trace（不改变任务状态）。"""
    current_time = _now_iso()
    normalized_trace_steps = _normalize_trace_steps(trace_steps)
    (
        tool_registry_profile,
        tool_registry_provider_source,
        allowed_tool_names_json,
        allowed_tool_labels_json,
    ) = _serialize_task_governance_columns(normalized_trace_steps)

    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE tasks
            SET
                trace_json = ?,
                updated_at = ?,
                tool_registry_profile = ?,
                tool_registry_provider_source = ?,
                allowed_tool_names_json = ?,
                allowed_tool_labels_json = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                json.dumps(normalized_trace_steps, ensure_ascii=False),
                current_time,
                tool_registry_profile,
                tool_registry_provider_source,
                allowed_tool_names_json,
                allowed_tool_labels_json,
                task_id,
                user_id,
            ),
        )
        connection.commit()


def complete_task(
    task_id: str,
    trace_steps: list[dict],
    user_id: str,
    status: str = "completed",
    usage: dict[str, object] | None = None,
    execution_owner_id: str | None = None,
) -> int:
    current_time = _now_iso()
    normalized_trace_steps = _normalize_trace_steps(trace_steps)
    usage_blob = json.dumps(usage, ensure_ascii=False) if usage is not None else None
    owner_id = (
        get_task_execution_owner_id(
            SimpleNamespace(task_execution_owner_id=execution_owner_id)
        )
        if execution_owner_id is not None
        else None
    )
    (
        tool_registry_profile,
        tool_registry_provider_source,
        allowed_tool_names_json,
        allowed_tool_labels_json,
    ) = _serialize_task_governance_columns(normalized_trace_steps)
    status_guard = "LOWER(status) IN ('pending', 'queued', 'running')"
    guard_params: tuple[object, ...] = ()
    if owner_id is not None:
        status_guard = """
              (
                LOWER(status) IN ('pending', 'queued')
                OR (
                    LOWER(status) = ?
                    AND (
                        execution_owner_id IS NULL
                        OR TRIM(execution_owner_id) = ''
                        OR execution_owner_id = ?
                    )
                )
              )
        """
        guard_params = ("running", owner_id)

    with get_db_connection() as connection:
        cursor = connection.execute(
            f"""
            UPDATE tasks
            SET
                status = ?,
                trace_json = ?,
                usage_json = ?,
                updated_at = ?,
                tool_registry_profile = ?,
                tool_registry_provider_source = ?,
                allowed_tool_names_json = ?,
                allowed_tool_labels_json = ?,
                execution_owner_id = NULL,
                execution_heartbeat_at = NULL
            WHERE {status_guard}
              AND id = ? AND user_id = ?
            """,
            (
                status,
                json.dumps(normalized_trace_steps, ensure_ascii=False),
                usage_blob,
                current_time,
                tool_registry_profile,
                tool_registry_provider_source,
                allowed_tool_names_json,
                allowed_tool_labels_json,
                *guard_params,
                task_id,
                user_id,
            ),
        )
        connection.commit()
        return max(0, int(getattr(cursor, "rowcount", 0) or 0))


def create_session_record(title: str | None = None, user_id: str = "") -> dict:
    """Insert an empty session row (no messages yet)."""
    if not user_id.strip():
        raise ValueError("user_id is required")
    session_id = str(uuid4())
    current_time = _now_iso()
    raw = (title or "新会话").strip()
    resolved_title = raw[:120] if raw else "新会话"

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO sessions(id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, user_id, resolved_title, current_time, current_time),
        )
        connection.commit()

    row = get_session(session_id, user_id)
    if row is None:
        raise RuntimeError("failed to read session after insert")
    return row


def get_session(session_id: str, user_id: str) -> dict | None:
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM sessions
            WHERE id = ? AND user_id = ?
            """,
            (session_id, user_id),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def update_session_title(session_id: str, title: str, user_id: str) -> dict | None:
    """更新会话标题；title 为空则保持「未命名」式占位。"""
    raw = title.strip()
    resolved = raw[:120] if raw else "新会话"
    current_time = _now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE sessions
            SET title = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (resolved, current_time, session_id, user_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
    return get_session(session_id, user_id)


def delete_session(session_id: str, user_id: str) -> bool:
    """删除会话；关联 tasks / messages 由外键 ON DELETE CASCADE 清理。"""
    with get_db_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def count_sessions(user_id: str) -> int:
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS n FROM sessions WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return int(row["n"]) if row else 0


def _build_task_search_clause(
    query: str | None,
    params: list[object],
) -> str:
    normalized = (query or "").strip().lower()
    if not normalized:
        return ""
    like = f"%{normalized}%"
    params.extend((like, like, like))
    return """
        AND (
            LOWER(prompt) LIKE ?
            OR LOWER(id) LIKE ?
            OR LOWER(COALESCE(trace_json, '')) LIKE ?
        )
    """


def _build_task_governance_filter_clause(
    tool_registry_profile_filter: str | None,
    tool_registry_provider_source_filter: str | None,
    params: list[object],
) -> str:
    clauses: list[str] = []
    normalized_profile = _normalize_governance_filter(tool_registry_profile_filter)
    if normalized_profile:
        clauses.append("LOWER(COALESCE(tool_registry_profile, '')) = ?")
        params.append(normalized_profile)
    normalized_provider_source = _normalize_governance_provider_source_filter(
        tool_registry_provider_source_filter
    )
    if normalized_provider_source:
        clauses.append("LOWER(COALESCE(tool_registry_provider_source, '')) = ?")
        params.append(normalized_provider_source)
    if not clauses:
        return ""
    return "\n        AND (" + " AND ".join(clauses) + ")"


def count_tasks(
    user_id: str,
    session_id: str | None = None,
    query: str | None = None,
    tool_registry_profile_filter: str | None = None,
    tool_registry_provider_source_filter: str | None = None,
) -> int:
    with get_db_connection() as connection:
        params: list[object] = [user_id]
        session_clause = ""
        if session_id:
            session_clause = " AND session_id = ?"
            params.append(session_id)
        search_clause = _build_task_search_clause(query, params)
        governance_clause = _build_task_governance_filter_clause(
            tool_registry_profile_filter,
            tool_registry_provider_source_filter,
            params,
        )
        row = connection.execute(
            f"SELECT COUNT(*) AS n FROM tasks WHERE user_id = ?{session_clause}{search_clause}{governance_clause}",
            tuple(params),
        ).fetchone()
    return int(row["n"]) if row else 0


def list_sessions(user_id: str, limit: int = 20, offset: int = 0) -> list[dict]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        ).fetchall()

    return [dict(row) for row in rows]


def get_session_messages(session_id: str, user_id: str) -> list[dict]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, session_id, task_id, role, content, created_at
            FROM messages
            WHERE session_id = ? AND user_id = ?
            ORDER BY created_at ASC
            """,
            (session_id, user_id),
        ).fetchall()

    return [dict(row) for row in rows]


def get_task_messages(task_id: str, user_id: str) -> list[dict]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, session_id, task_id, role, content, created_at
            FROM messages
            WHERE task_id = ? AND user_id = ?
            ORDER BY created_at ASC
            """,
            (task_id, user_id),
        ).fetchall()

    return [dict(row) for row in rows]


def _resolve_task_failed_audit_insight(
    connection,
    *,
    task_id: str,
    user_id: str,
) -> dict[str, str] | None:
    row = connection.execute(
        """
        SELECT event_detail_json
        FROM audit_logs
        WHERE user_id = ?
          AND event_type = 'task_failed'
          AND event_detail_json IS NOT NULL
          AND (event_detail_json::jsonb ->> 'task_id') = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id, task_id),
    ).fetchone()
    if row is None:
        return None
    payload = _coerce_export_payload_block_to_dict(row)
    return _extract_task_failed_audit_insight_from_detail(
        payload.get("event_detail_json")
    )


def _extract_task_failed_audit_insight_from_detail(
    raw_detail: object,
) -> dict[str, str] | None:
    if not isinstance(raw_detail, str) or not raw_detail.strip():
        return None
    try:
        detail = json.loads(raw_detail)
    except Exception:
        return None
    if not isinstance(detail, dict):
        return None
    hint = (
        _normalize_task_failure_hint(detail.get("failure_hint"))
        or _normalize_task_failure_hint(detail.get("code"))
        or _normalize_task_failure_hint(detail.get("message"))
    )
    if not hint:
        return None
    return {
        "failure_hint": hint,
        "failure_source": "error_event",
    }


def _resolve_task_failed_audit_insights_for_tasks(
    connection,
    *,
    task_ids: list[str],
    user_id: str,
) -> dict[str, dict[str, str]]:
    normalized_task_ids = [
        task_id.strip()
        for task_id in task_ids
        if isinstance(task_id, str) and task_id.strip()
    ]
    if not normalized_task_ids:
        return {}
    task_conditions = " OR ".join(
        ["(event_detail_json::jsonb ->> 'task_id') = ?"] * len(normalized_task_ids)
    )
    rows = connection.execute(
        f"""
        SELECT event_detail_json
        FROM audit_logs
        WHERE user_id = ?
          AND event_type = 'task_failed'
          AND event_detail_json IS NOT NULL
          AND ({task_conditions})
        ORDER BY created_at DESC
        """,
        tuple([user_id, *normalized_task_ids]),
    ).fetchall()
    insights: dict[str, dict[str, str]] = {}
    for row in rows:
        payload = _coerce_export_payload_block_to_dict(row)
        raw_detail = payload.get("event_detail_json")
        if not isinstance(raw_detail, str) or not raw_detail.strip():
            continue
        try:
            detail = json.loads(raw_detail)
        except Exception:
            continue
        if not isinstance(detail, dict):
            continue
        detail_task_id = str(detail.get("task_id", "")).strip()
        if not detail_task_id or detail_task_id in insights:
            continue
        insight = _extract_task_failed_audit_insight_from_detail(raw_detail)
        if insight:
            insights[detail_task_id] = insight
    return insights


def get_task(task_id: str, user_id: str) -> dict | None:
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                session_id,
                prompt,
                status,
                trace_json,
                usage_json,
                tool_registry_profile,
                tool_registry_provider_source,
                allowed_tool_names_json,
                allowed_tool_labels_json,
                created_at,
                updated_at
            FROM tasks
            WHERE id = ? AND user_id = ?
            """,
            (task_id, user_id),
        ).fetchone()
        audit_failure = (
            _resolve_task_failed_audit_insight(
                connection,
                task_id=task_id,
                user_id=user_id,
            )
            if row is not None
            else None
        )

    if row is None:
        return None

    task = _with_task_governance(dict(row))
    if audit_failure:
        task.update(audit_failure)
    return task


def list_tasks(
    user_id: str,
    limit: int = 20,
    session_id: str | None = None,
    offset: int = 0,
    query: str | None = None,
    tool_registry_profile_filter: str | None = None,
    tool_registry_provider_source_filter: str | None = None,
) -> list[dict]:
    with get_db_connection() as connection:
        params: list[object] = [user_id]
        session_clause = ""
        if session_id:
            session_clause = " AND session_id = ?"
            params.append(session_id)
        search_clause = _build_task_search_clause(query, params)
        governance_clause = _build_task_governance_filter_clause(
            tool_registry_profile_filter,
            tool_registry_provider_source_filter,
            params,
        )
        params.extend((limit, offset))
        rows = connection.execute(
            f"""
                SELECT
                    id,
                    session_id,
                    prompt,
                    status,
                    trace_json,
                    usage_json,
                    tool_registry_profile,
                    tool_registry_provider_source,
                    allowed_tool_names_json,
                    allowed_tool_labels_json,
                    created_at,
                    updated_at
                FROM tasks
                WHERE user_id = ?{session_clause}{search_clause}{governance_clause}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """,
            tuple(params),
        ).fetchall()
        tasks = [_with_task_governance(dict(row)) for row in rows]
        failed_task_ids = [
            str(task.get("id", "")).strip()
            for task in tasks
            if normalize_task_status(str(task.get("status", ""))) == "failed"
        ]
        audit_failures = _resolve_task_failed_audit_insights_for_tasks(
            connection,
            task_ids=failed_task_ids,
            user_id=user_id,
        )

    for task in tasks:
        task_id = str(task.get("id", "")).strip()
        if task_id in audit_failures:
            task.update(audit_failures[task_id])
    return tasks


def get_session_tasks(session_id: str, user_id: str) -> list[dict]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                session_id,
                prompt,
                status,
                trace_json,
                usage_json,
                tool_registry_profile,
                tool_registry_provider_source,
                allowed_tool_names_json,
                allowed_tool_labels_json,
                created_at,
                updated_at
            FROM tasks
            WHERE user_id = ? AND session_id = ?
            ORDER BY created_at ASC
            """,
            (user_id, session_id),
        ).fetchall()

    return [_with_task_governance(dict(row)) for row in rows]


def get_task_trace_steps_from_task(task: dict) -> list[TraceStep]:
    task = _coerce_export_payload_block_to_dict(task)
    if not task.get("trace_json"):
        return []
    return _load_parsed_trace_steps_from_trace_json(task["trace_json"])


def get_task_usage_from_task(task: dict) -> dict[str, object] | None:
    task = _coerce_export_payload_block_to_dict(task)
    return _parse_usage_json_blob(task.get("usage_json"))


from app.services.module_export_utils import install_rebound_exports
from app.services import chat_persistence_trace_export as _chat_persistence_trace_export

install_rebound_exports(
    source_module=_chat_persistence_trace_export,
    target_namespace=globals(),
    export_names=_chat_persistence_trace_export._CHAT_PERSISTENCE_TRACE_EXPORT_EXPORTS,
)
from app.services import chat_persistence_usage as _chat_persistence_usage

install_rebound_exports(
    source_module=_chat_persistence_usage,
    target_namespace=globals(),
    export_names=_chat_persistence_usage._CHAT_PERSISTENCE_USAGE_EXPORTS,
)
