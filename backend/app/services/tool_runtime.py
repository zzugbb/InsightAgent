from __future__ import annotations

import json
import math
import re
import gzip
import inspect
import zlib
import codecs
from ast import Add, BinOp, Div, Expression, Mod, Mult, Pow, Sub, UAdd, USub, UnaryOp, parse
from collections import UserString
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Iterator, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, unquote, urlencode, urlparse
from urllib.request import Request, urlopen

from app.config import get_settings
from app.providers.base import ProviderUsage
from app.providers.response_utils import (
    coerce_provider_usage,
    extract_response_text,
    normalize_response_text,
)
from app.services.chroma_rag_service import (
    SHARED_RAG_SCOPE_USER_ID,
    is_shared_knowledge_base_id,
    normalize_knowledge_base_id,
    query_knowledge_base,
    sanitize_rag_collection_name,
    sanitize_rag_query_hits,
)


class MockToolExecutionError(RuntimeError):
    def __init__(self, message: str, *, fatal: bool):
        super().__init__(message)
        self.fatal = fatal


class _HttpJsonScalarFallbackOutput(dict[str, object]):
    pass


@dataclass(frozen=True)
class ToolInvocation:
    name: str
    tool_input: dict[str, object]


ToolRunner = Callable[..., dict[str, object]]
ToolRegistryLoader = Callable[[], dict[str, "ToolRegistration"]]
ToolRegistryLoaderFactory = Callable[[object | None], ToolRegistryLoader]
ToolRegistryProviderFactory = Callable[[object | None], "ToolRegistryProvider"]


class ToolRegistryProvider(Protocol):
    def load_tool_registry(self) -> dict[str, "ToolRegistration"]: ...


@dataclass(frozen=True)
class ToolRegistration:
    name: str
    kind: str
    label: str
    retryable_by_default: bool
    default_timeout_ms: int
    requires_user_context: bool
    supports_result_preview: bool
    runner: ToolRunner
    result_preview_keys: tuple[str, ...] = ()
    result_output_keys: tuple[str, ...] = ()
    runtime_semantic_kind: str | None = None
    execution_kind: str | None = None
    execution_summary: dict[str, object] | None = None
    execution_diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class StaticToolRegistryProvider:
    registry: dict[str, ToolRegistration]

    def load_tool_registry(self) -> dict[str, ToolRegistration]:
        return dict(self.registry)


@dataclass(frozen=True)
class DefaultToolRegistryProvider:
    def load_tool_registry(self) -> dict[str, ToolRegistration]:
        return get_default_tool_registry()


@dataclass(frozen=True)
class ConfiguredToolRegistryProvider:
    provider: ToolRegistryProvider | None = None
    loader: ToolRegistryLoader | None = None
    overrides: dict[str, ToolRegistration] | None = None
    disabled_tool_names: tuple[str, ...] = ()

    def load_tool_registry(self) -> dict[str, ToolRegistration]:
        if self.provider is not None:
            base_registry = dict(self.provider.load_tool_registry())
        elif self.loader is not None:
            base_registry = dict(self.loader())
        else:
            base_registry = DefaultToolRegistryProvider().load_tool_registry()
        return build_tool_registry(
            base_registry=base_registry,
            overrides=self.overrides,
            disabled_tool_names=self.disabled_tool_names,
        )


@dataclass(frozen=True)
class ToolRuntimeContext:
    name: str
    prompt: str
    user_id: str
    attempt: int
    registration: ToolRegistration
    retryable_by_default: bool
    default_timeout_ms: int
    requires_user_context: bool


@dataclass(frozen=True)
class ToolPlanArtifacts:
    tool_plan: list[dict[str, object]]
    allowed_tool_names: tuple[str, ...] = ()
    allowed_tool_labels: tuple[str, ...] = ()
    planning_prompt: str | None = None
    provider_usage: ProviderUsage | None = None
    planning_provider_attempted: bool = False
    planning_provider_used: bool = False


@dataclass(frozen=True)
class ToolRegistrySettingsConfig:
    overrides: dict[str, ToolRegistration]
    disabled_tool_names: tuple[str, ...] = ()


_TOOL_RUNTIME_PROVIDER_SOURCE_SENSITIVE_TOKEN_RE = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|client[_-]?secret|secret|token|password)"
    r"(?:\s*[:=][^\s,;/]+|[^\s,;/]*)?"
)
_TOOL_RUNTIME_PROVIDER_SOURCE_ARTIFACT_KEYS = frozenset(
    {
        "provider_source",
        "provider_source_name",
        "tool_registry_provider_source",
    }
)
_TOOL_RUNTIME_PROVIDER_SOURCES_ARTIFACT_KEYS = frozenset(
    {
        "provider_sources",
        "tool_registry_provider_sources",
    }
)


def _sanitize_tool_runtime_provider_source_name_for_artifact(
    provider_source_name: object,
) -> str:
    safe_value = _redact_tool_registry_diagnostic_value(
        str(provider_source_name).strip()
    )
    safe_value = _TOOL_RUNTIME_PROVIDER_SOURCE_SENSITIVE_TOKEN_RE.sub(
        "[redacted]",
        safe_value,
    )
    return safe_value or "default"


def _sanitize_tool_runtime_provider_source_fields_for_artifact(
    payload: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> object:
    if isinstance(payload, dict):
        sanitized: dict[object, object] = {}
        for key, value in payload.items():
            safe_key = str(key)
            if safe_key in _TOOL_RUNTIME_PROVIDER_SOURCE_ARTIFACT_KEYS:
                sanitized[key] = _sanitize_tool_runtime_provider_source_name_with_aliases(
                    value,
                    provider_source_aliases=provider_source_aliases,
                )
                continue
            if (
                safe_key in _TOOL_RUNTIME_PROVIDER_SOURCES_ARTIFACT_KEYS
                and isinstance(value, (list, tuple))
            ):
                alias_by_source = provider_source_aliases or {}
                local_alias_by_source = build_safe_tool_registry_provider_source_alias_map(
                    [
                        source_name
                        for source_name in value
                        if isinstance(source_name, str) and source_name.strip()
                        and source_name not in alias_by_source
                    ]
                )
                sanitized[key] = [
                    alias_by_source.get(
                        source_name,
                        local_alias_by_source.get(
                            source_name,
                            _sanitize_tool_runtime_provider_source_name_for_artifact(
                                source_name
                            ),
                        ),
                    )
                    if isinstance(source_name, str) and source_name.strip()
                    else source_name
                    for source_name in value
                ]
                continue
            sanitized[key] = _sanitize_tool_runtime_provider_source_fields_for_artifact(
                value,
                provider_source_aliases=provider_source_aliases,
            )
        return sanitized
    if isinstance(payload, tuple):
        return tuple(
            _sanitize_tool_runtime_provider_source_fields_for_artifact(
                value,
                provider_source_aliases=provider_source_aliases,
            )
            for value in payload
        )
    if isinstance(payload, list):
        return [
            _sanitize_tool_runtime_provider_source_fields_for_artifact(
                value,
                provider_source_aliases=provider_source_aliases,
            )
            for value in payload
        ]
    return payload


def _sanitize_tool_runtime_provider_sources_for_artifact(
    provider_sources: dict[str, ToolRegistryProvider],
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> dict[str, ToolRegistryProvider]:
    sanitized: dict[str, ToolRegistryProvider] = {}
    alias_by_source = provider_source_aliases or (
        build_safe_tool_registry_provider_source_alias_map(list(provider_sources.keys()))
    )
    for source_name, provider in provider_sources.items():
        safe_source_name = alias_by_source.get(
            source_name,
            _sanitize_tool_runtime_provider_source_name_for_artifact(source_name),
        )
        if safe_source_name in sanitized:
            continue
        sanitized[safe_source_name] = provider
    return sanitized


def _iter_tool_runtime_provider_source_diagnostic_values(diagnostics: object):
    if not isinstance(diagnostics, dict):
        return
    for key, values in diagnostics.items():
        if not str(key).endswith("_registry_sources"):
            continue
        if not isinstance(values, (list, tuple)):
            continue
        for value in values:
            if isinstance(value, str) and value.strip():
                yield value


def _iter_tool_runtime_provider_source_artifact_values(payload: object):
    if isinstance(payload, dict):
        for key, value in payload.items():
            safe_key = str(key)
            if (
                safe_key in _TOOL_RUNTIME_PROVIDER_SOURCE_ARTIFACT_KEYS
                and isinstance(value, str)
                and value.strip()
            ):
                yield value
            elif (
                safe_key in _TOOL_RUNTIME_PROVIDER_SOURCES_ARTIFACT_KEYS
                and isinstance(value, (list, tuple))
            ):
                for source_name in value:
                    if isinstance(source_name, str) and source_name.strip():
                        yield source_name
            elif (
                safe_key == "values"
                and str(payload.get("target")) == "registry_sources"
                and isinstance(value, (list, tuple))
            ):
                for source_name in value:
                    if isinstance(source_name, str) and source_name.strip():
                        yield source_name
            yield from _iter_tool_runtime_provider_source_artifact_values(value)
        return
    if isinstance(payload, (list, tuple)):
        for value in payload:
            yield from _iter_tool_runtime_provider_source_artifact_values(value)
        return
    if hasattr(payload, "entries"):
        yield from _iter_tool_runtime_provider_source_artifact_values(
            getattr(payload, "entries")
        )
    if hasattr(payload, "summary"):
        yield from _iter_tool_runtime_provider_source_artifact_values(
            getattr(payload, "summary")
        )
    if hasattr(payload, "trace_step"):
        yield from _iter_tool_runtime_provider_source_artifact_values(
            getattr(payload, "trace_step")
        )
    if hasattr(payload, "trace_event"):
        yield from _iter_tool_runtime_provider_source_artifact_values(
            getattr(payload, "trace_event")
        )
    if hasattr(payload, "audit_detail"):
        yield from _iter_tool_runtime_provider_source_artifact_values(
            getattr(payload, "audit_detail")
        )
    if hasattr(payload, "kwargs"):
        yield from _iter_tool_runtime_provider_source_artifact_values(
            getattr(payload, "kwargs")
        )


def _build_tool_runtime_artifact_provider_source_aliases(
    *,
    provider_source_name: object,
    provider_sources: object,
    selected_source_diagnostics: object,
    source_diagnostics: object,
    diagnostics_runtime: object = None,
    audit_event: object = None,
    service_actions: object = None,
) -> dict[str, str]:
    source_names: list[object] = []
    if isinstance(provider_sources, dict):
        source_names.extend(provider_sources.keys())
    if str(provider_source_name).strip():
        source_names.append(provider_source_name)
    if isinstance(source_diagnostics, dict):
        source_names.extend(source_diagnostics.keys())
        for diagnostics in source_diagnostics.values():
            source_names.extend(
                _iter_tool_runtime_provider_source_diagnostic_values(diagnostics)
            )
    source_names.extend(
        _iter_tool_runtime_provider_source_diagnostic_values(
            selected_source_diagnostics
        )
    )
    source_names.extend(
        _iter_tool_runtime_provider_source_artifact_values(diagnostics_runtime)
    )
    source_names.extend(_iter_tool_runtime_provider_source_artifact_values(audit_event))
    source_names.extend(
        _iter_tool_runtime_provider_source_artifact_values(service_actions)
    )
    return build_safe_tool_registry_provider_source_alias_map(source_names)


def _sanitize_tool_runtime_provider_source_name_with_aliases(
    provider_source_name: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> str:
    return (provider_source_aliases or {}).get(
        str(provider_source_name),
        _sanitize_tool_runtime_provider_source_name_for_artifact(provider_source_name),
    )


def _sanitize_tool_runtime_provider_source_name_with_runtime_alias(
    provider_source_name: object,
    *,
    runtime_artifacts: ConfiguredToolRegistryProviderRuntimeArtifactsModel,
    provider_source_aliases: dict[str, str] | None = None,
) -> str:
    safe_provider_source_name = _sanitize_tool_runtime_provider_source_name_with_aliases(
        provider_source_name,
        provider_source_aliases=provider_source_aliases,
    )
    safe_runtime_provider_source_name = (
        _sanitize_tool_runtime_provider_source_name_with_aliases(
            runtime_artifacts.provider_source_name,
            provider_source_aliases=provider_source_aliases,
        )
    )
    fallback_provider_source_name = (
        _sanitize_tool_runtime_provider_source_name_for_artifact(provider_source_name)
    )
    if (
        safe_provider_source_name == fallback_provider_source_name
        and safe_runtime_provider_source_name.startswith(
            f"{fallback_provider_source_name}#"
        )
    ):
        return safe_runtime_provider_source_name
    return safe_provider_source_name


def _sanitize_tool_runtime_diagnostics_summary_for_artifact(
    diagnostics_summary: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> dict[str, object]:
    if not isinstance(diagnostics_summary, dict):
        return {}
    artifact_payload = sanitize_tool_registry_diagnostics_artifact_payload(
        diagnostics_summary
    )
    sanitized_payload = _sanitize_tool_runtime_provider_source_fields_for_artifact(
        artifact_payload,
        provider_source_aliases=provider_source_aliases,
    )
    if not isinstance(sanitized_payload, dict):
        return {}
    entries = diagnostics_summary.get("entries")
    if not isinstance(entries, (list, tuple)):
        return sanitized_payload
    safe_entries: list[dict[str, object]] = []
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            continue
        safe_entry: dict[str, object] = {}
        values: object = None
        for key, value in raw_entry.items():
            if key == "values" and isinstance(value, (list, tuple)):
                values = value
                continue
            safe_entry[key] = _sanitize_tool_runtime_provider_source_fields_for_artifact(
                sanitize_tool_registry_diagnostics_artifact_payload(value),
                provider_source_aliases=provider_source_aliases,
            )
        if isinstance(values, (list, tuple)):
            alias_by_value = (
                build_safe_tool_registry_provider_source_alias_map(values)
                if str(safe_entry.get("target")) == "registry_sources"
                else {}
            )
            deduped_safe_values: list[str] = []
            for value in values:
                value_key = str(value)
                safe_value = (
                    (
                        provider_source_aliases.get(value_key)
                        if provider_source_aliases is not None
                        else None
                    )
                    or alias_by_value.get(value_key)
                    or _sanitize_tool_runtime_provider_source_name_for_artifact(value)
                )
                if not safe_value or safe_value in deduped_safe_values:
                    continue
                deduped_safe_values.append(safe_value)
            safe_entry["values"] = tuple(deduped_safe_values)
            safe_entry["count"] = len(deduped_safe_values)
        safe_entries.append(safe_entry)
    sanitized_payload["entries"] = tuple(safe_entries)
    return sanitized_payload


@dataclass(frozen=True)
class ConfiguredToolRegistryProviderPreflightSummaryModel:
    provider_source_name: str
    tool_count: int
    tool_names: tuple[str, ...]
    tool_details: tuple[dict[str, object], ...]
    service_action_count: int
    service_action_kinds: tuple[str, ...]
    trace_write_count: int
    audit_event_count: int
    has_diagnostics: bool
    diagnostics_total: int
    skipped_total: int
    missing_total: int
    diagnostics_summary: dict[str, object]

    def to_dict(
        self,
        *,
        provider_source_aliases: dict[str, str] | None = None,
    ) -> dict[str, object]:
        return {
            "provider_source_name": _sanitize_tool_runtime_provider_source_name_with_aliases(
                self.provider_source_name,
                provider_source_aliases=provider_source_aliases,
            ),
            "tool_count": self.tool_count,
            "tool_names": self.tool_names,
            "tool_details": _sanitize_tool_runtime_trace_artifact_payload(
                self.tool_details,
                provider_source_aliases=provider_source_aliases,
            ),
            "service_action_count": self.service_action_count,
            "service_action_kinds": self.service_action_kinds,
            "trace_write_count": self.trace_write_count,
            "audit_event_count": self.audit_event_count,
            "has_diagnostics": self.has_diagnostics,
            "diagnostics_total": self.diagnostics_total,
            "skipped_total": self.skipped_total,
            "missing_total": self.missing_total,
            "diagnostics_summary": _sanitize_tool_runtime_diagnostics_summary_for_artifact(
                self.diagnostics_summary,
                provider_source_aliases=provider_source_aliases,
            ),
        }


@dataclass(frozen=True)
class ConfiguredToolRegistryProviderPreflightResultModel:
    provider: ToolRegistryProvider
    provider_source_name: str
    runtime_artifacts: ConfiguredToolRegistryProviderRuntimeArtifactsModel
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel
    trace_write_count: int
    audit_event_count: int
    summary: ConfiguredToolRegistryProviderPreflightSummaryModel

    def to_dict(self) -> dict[str, object]:
        provider_source_aliases = _build_tool_runtime_artifact_provider_source_aliases(
            provider_source_name=self.provider_source_name,
            provider_sources=self.runtime_artifacts.provider_sources,
            selected_source_diagnostics=self.runtime_artifacts.selected_source_diagnostics,
            source_diagnostics=self.runtime_artifacts.source_diagnostics,
            diagnostics_runtime=self.runtime_artifacts.diagnostics_runtime,
            audit_event=self.runtime_artifacts.audit_event,
            service_actions=self.service_execution.service_actions,
        )
        return {
            "provider": self.provider,
            "provider_source_name": _sanitize_tool_runtime_provider_source_name_with_aliases(
                self.provider_source_name,
                provider_source_aliases=provider_source_aliases,
            ),
            "runtime_artifacts": self.runtime_artifacts.to_dict(
                provider_source_aliases=provider_source_aliases,
            ),
            "service_execution": self.service_execution.to_dict(
                provider_source_aliases=provider_source_aliases,
            ),
            "trace_write_count": self.trace_write_count,
            "audit_event_count": self.audit_event_count,
            "summary": self.summary.to_dict(
                provider_source_aliases=provider_source_aliases,
            ),
        }


@dataclass(frozen=True)
class ToolRegistryDiagnosticsSummaryModel:
    has_diagnostics: bool
    skipped_total: int
    missing_total: int
    total: int
    entries: tuple[dict[str, object], ...]

    def to_dict(
        self,
        *,
        provider_source_aliases: dict[str, str] | None = None,
    ) -> dict[str, object]:
        return _sanitize_tool_runtime_diagnostics_summary_for_artifact(
            {
                "has_diagnostics": self.has_diagnostics,
                "skipped_total": self.skipped_total,
                "missing_total": self.missing_total,
                "total": self.total,
                "entries": self.entries,
            },
            provider_source_aliases=provider_source_aliases,
        )


def _sanitize_tool_runtime_trace_artifact_payload(
    payload: object,
    *,
    provider_source_aliases: dict[str, str] | None = None,
) -> object:
    sanitized = sanitize_tool_registry_diagnostics_artifact_payload(payload)
    sanitized = _sanitize_tool_runtime_provider_source_fields_for_artifact(
        sanitized,
        provider_source_aliases=provider_source_aliases,
    )
    return _sanitize_tool_runtime_trace_artifact_http_json_payload(sanitized)


def _sanitize_tool_runtime_trace_artifact_http_json_payload(payload: object) -> object:
    if isinstance(payload, dict):
        if get_action_step_tool_meta(payload) is not None:
            return _sanitize_tool_trace_event_step(payload)

        sanitized: dict[str, object] = {}
        for key, value in payload.items():
            if key in {"trace_step", "step"} and isinstance(value, dict):
                sanitized[key] = _sanitize_tool_trace_event_step(value)
            elif key in {"trace_event", "trace"} and isinstance(value, dict):
                sanitized[key] = _sanitize_tool_trace_event_payload(value)
            else:
                sanitized[key] = _sanitize_tool_runtime_trace_artifact_http_json_payload(
                    value
                )
        return sanitized
    if isinstance(payload, list):
        return [
            _sanitize_tool_runtime_trace_artifact_http_json_payload(value)
            for value in payload
        ]
    if isinstance(payload, tuple):
        return tuple(
            _sanitize_tool_runtime_trace_artifact_http_json_payload(value)
            for value in payload
        )
    return payload


@dataclass(frozen=True)
class ToolRegistryDiagnosticsRuntimeArtifactsModel:
    summary: ToolRegistryDiagnosticsSummaryModel
    trace_step: dict[str, object] | None
    trace_event: dict[str, object] | None
    audit_detail: dict[str, object] | None

    def to_dict(
        self,
        *,
        provider_source_aliases: dict[str, str] | None = None,
    ) -> dict[str, object]:
        return {
            "summary": self.summary.to_dict(
                provider_source_aliases=provider_source_aliases,
            ),
            "trace_step": _sanitize_tool_runtime_trace_artifact_payload(
                self.trace_step,
                provider_source_aliases=provider_source_aliases,
            ),
            "trace_event": _sanitize_tool_runtime_trace_artifact_payload(
                self.trace_event,
                provider_source_aliases=provider_source_aliases,
            ),
            "audit_detail": _sanitize_tool_runtime_trace_artifact_payload(
                self.audit_detail,
                provider_source_aliases=provider_source_aliases,
            ),
        }


@dataclass(frozen=True)
class ConfiguredToolRegistryProviderRuntimeArtifactsModel:
    provider: ToolRegistryProvider
    provider_source_name: str
    provider_sources: dict[str, ToolRegistryProvider]
    selected_source_diagnostics: dict[str, tuple[str, ...]]
    source_diagnostics: dict[str, dict[str, tuple[str, ...]]]
    diagnostics_runtime: ToolRegistryDiagnosticsRuntimeArtifactsModel
    audit_event: dict[str, object] | None

    def to_dict(
        self,
        *,
        provider_source_aliases: dict[str, str] | None = None,
    ) -> dict[str, object]:
        if provider_source_aliases is None:
            provider_source_aliases = _build_tool_runtime_artifact_provider_source_aliases(
                provider_source_name=self.provider_source_name,
                provider_sources=self.provider_sources,
                selected_source_diagnostics=self.selected_source_diagnostics,
                source_diagnostics=self.source_diagnostics,
                diagnostics_runtime=self.diagnostics_runtime,
                audit_event=self.audit_event,
            )
        return {
            "provider": self.provider,
            "provider_source_name": provider_source_aliases.get(
                str(self.provider_source_name),
                _sanitize_tool_runtime_provider_source_name_for_artifact(
                    self.provider_source_name
                ),
            ),
            "provider_sources": _sanitize_tool_runtime_provider_sources_for_artifact(
                self.provider_sources,
                provider_source_aliases=provider_source_aliases,
            ),
            "selected_source_diagnostics": _impl__sanitize_tool_registry_file_diagnostics_with_provider_source_aliases(
                self.selected_source_diagnostics,
                provider_source_aliases=provider_source_aliases,
            ),
            "source_diagnostics": _impl__sanitize_tool_registry_source_diagnostics_with_provider_source_aliases(
                self.source_diagnostics,
                provider_source_aliases=provider_source_aliases,
            ),
            "diagnostics_runtime": self.diagnostics_runtime.to_dict(
                provider_source_aliases=provider_source_aliases,
            ),
            "audit_event": _sanitize_tool_runtime_trace_artifact_payload(
                self.audit_event,
                provider_source_aliases=provider_source_aliases,
            ),
        }


@dataclass(frozen=True)
class ConfiguredToolRegistryProviderRuntimeServiceActionModel:
    kind: str
    trace_step: dict[str, object] | None = None
    trace_event: dict[str, object] | None = None
    persist_force: bool = False
    kwargs: dict[str, object] | None = None

    def to_dict(
        self,
        *,
        provider_source_aliases: dict[str, str] | None = None,
    ) -> dict[str, object]:
        if provider_source_aliases is None:
            provider_source_aliases = _build_tool_runtime_artifact_provider_source_aliases(
                provider_source_name="",
                provider_sources={},
                selected_source_diagnostics={},
                source_diagnostics={},
                service_actions=(self,),
            )
        payload: dict[str, object] = {
            "kind": self.kind,
        }
        if self.trace_step is not None:
            payload["trace_step"] = _sanitize_tool_runtime_trace_artifact_payload(
                self.trace_step,
                provider_source_aliases=provider_source_aliases,
            )
        if self.trace_event is not None:
            payload["trace_event"] = _sanitize_tool_runtime_trace_artifact_payload(
                self.trace_event,
                provider_source_aliases=provider_source_aliases,
            )
        if self.persist_force:
            payload["persist_force"] = self.persist_force
        if self.kwargs is not None:
            payload["kwargs"] = _sanitize_tool_runtime_trace_artifact_payload(
                self.kwargs,
                provider_source_aliases=provider_source_aliases,
            )
        return payload


@dataclass(frozen=True)
class ConfiguredToolRegistryProviderRuntimeServiceActionsModel:
    actions: tuple[ConfiguredToolRegistryProviderRuntimeServiceActionModel, ...]

    def to_dict(
        self,
        *,
        provider_source_aliases: dict[str, str] | None = None,
    ) -> list[dict[str, object]]:
        if provider_source_aliases is None:
            provider_source_aliases = _build_tool_runtime_artifact_provider_source_aliases(
                provider_source_name="",
                provider_sources={},
                selected_source_diagnostics={},
                source_diagnostics={},
                service_actions=self.actions,
            )
        return [
            action.to_dict(provider_source_aliases=provider_source_aliases)
            for action in self.actions
        ]


@dataclass(frozen=True)
class ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel:
    trace_write_count: int
    audit_event_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "trace_write_count": self.trace_write_count,
            "audit_event_count": self.audit_event_count,
        }


@dataclass(frozen=True)
class ConfiguredToolRegistryProviderServiceExecutionModel:
    provider: ToolRegistryProvider
    provider_source_name: str
    runtime_artifacts: ConfiguredToolRegistryProviderRuntimeArtifactsModel
    service_actions: tuple[ConfiguredToolRegistryProviderRuntimeServiceActionModel, ...]

    def to_dict(
        self,
        *,
        provider_source_aliases: dict[str, str] | None = None,
    ) -> dict[str, object]:
        if provider_source_aliases is None:
            provider_source_aliases = _build_tool_runtime_artifact_provider_source_aliases(
                provider_source_name=self.provider_source_name,
                provider_sources=self.runtime_artifacts.provider_sources,
                selected_source_diagnostics=self.runtime_artifacts.selected_source_diagnostics,
                source_diagnostics=self.runtime_artifacts.source_diagnostics,
                diagnostics_runtime=self.runtime_artifacts.diagnostics_runtime,
                audit_event=self.runtime_artifacts.audit_event,
                service_actions=self.service_actions,
            )
        return {
            "provider": self.provider,
            "provider_source_name": _sanitize_tool_runtime_provider_source_name_with_runtime_alias(
                self.provider_source_name,
                runtime_artifacts=self.runtime_artifacts,
                provider_source_aliases=provider_source_aliases,
            ),
            "runtime_artifacts": self.runtime_artifacts.to_dict(
                provider_source_aliases=provider_source_aliases,
            ),
            "service_actions": [
                action.to_dict(provider_source_aliases=provider_source_aliases)
                for action in self.service_actions
            ],
        }


@dataclass(frozen=True)
class ConfiguredToolRegistryProviderServiceExecutionResultModel:
    provider: ToolRegistryProvider
    provider_source_name: str
    runtime_artifacts: ConfiguredToolRegistryProviderRuntimeArtifactsModel
    trace_write_count: int
    audit_event_count: int

    def to_dict(
        self,
        *,
        provider_source_aliases: dict[str, str] | None = None,
    ) -> dict[str, object]:
        if provider_source_aliases is None:
            provider_source_aliases = _build_tool_runtime_artifact_provider_source_aliases(
                provider_source_name=self.provider_source_name,
                provider_sources=self.runtime_artifacts.provider_sources,
                selected_source_diagnostics=self.runtime_artifacts.selected_source_diagnostics,
                source_diagnostics=self.runtime_artifacts.source_diagnostics,
                diagnostics_runtime=self.runtime_artifacts.diagnostics_runtime,
                audit_event=self.runtime_artifacts.audit_event,
            )
        return {
            "provider": self.provider,
            "provider_source_name": _sanitize_tool_runtime_provider_source_name_with_runtime_alias(
                self.provider_source_name,
                runtime_artifacts=self.runtime_artifacts,
                provider_source_aliases=provider_source_aliases,
            ),
            "runtime_artifacts": self.runtime_artifacts.to_dict(
                provider_source_aliases=provider_source_aliases,
            ),
            "trace_write_count": self.trace_write_count,
            "audit_event_count": self.audit_event_count,
        }


_TOOL_REGISTRY_PROFILE_CONFIGS: dict[str, ToolRegistrySettingsConfig] = {
    "default": ToolRegistrySettingsConfig(
        overrides={},
        disabled_tool_names=(),
    ),
    "planning_only": ToolRegistrySettingsConfig(
        overrides={},
        disabled_tool_names=("calc_eval", "task_retrieve"),
    ),
    "retrieval_only": ToolRegistrySettingsConfig(
        overrides={},
        disabled_tool_names=("calc_eval", "task_plan"),
    ),
    "calculator_only": ToolRegistrySettingsConfig(
        overrides={},
        disabled_tool_names=("task_plan", "task_retrieve"),
    ),
}

_TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS = (
    "skipped_registry_sources",
    "missing_registry_sources",
    "skipped_registry_files",
    "missing_registry_files",
    "skipped_registry_dirs",
    "missing_registry_dirs",
    "invalid_tool_executions",
)
_TOOL_REGISTRY_LOADER_ADAPTER_KEYS = {
    "loader_factory",
    "loader",
    "registry_file",
    "profile",
    "disabled_tool_names",
    "overrides",
    "extra_tools",
}
_TOOL_REGISTRY_PROVIDER_ADAPTER_KEYS = {
    "provider_factory",
    "provider",
    "loader_factory",
    "loader",
    "registry_file",
    "profile",
    "disabled_tool_names",
    "overrides",
    "extra_tools",
}
_TOOL_REGISTRY_FACTORY_ADAPTER_KEYS = {
    "factory",
    "registry_file",
    "profile",
    "disabled_tool_names",
    "overrides",
    "extra_tools",
}
_HTTP_JSON_ALLOWED_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
_TOOL_TIMEOUT_MAX_MS = 2_147_483_647
_HTTP_JSON_ERROR_BODY_PREVIEW_MAX_LENGTH = 240
_HTTP_JSON_RESPONSE_BODY_READ_CHUNK_SIZE = 64 * 1024
_HTTP_JSON_RESULT_FIELD_MAPPING_ERROR_MAX_ITEMS = 5
_HTTP_JSON_MAPPING_PAYLOAD_SHAPE_KEY_MAX_ITEMS = 5
_HTTP_JSON_MAPPING_PAYLOAD_SHAPE_KEY_MAX_LENGTH = 48
_HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE = re.compile(
    r"(authorization|api[_-]?key|credential|password|secret|token)",
    re.IGNORECASE,
)
_HTTP_JSON_ERROR_BODY_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"((?:\"|')?\b(?:authorization|api[_-]?key|credential|password|secret|token)"
    r"\b(?:\"|')?\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;<>}]+)",
    re.IGNORECASE,
)
_HTTP_JSON_BARE_BEARER_TOKEN_RE = re.compile(r"\bbearer\s+\S+", re.IGNORECASE)
_HTTP_JSON_URL_TEXT_RE = re.compile(r"https?://[^\s<>\"'{}\[\]]+")
_TOOL_EXECUTION_ROOT_TEMPLATE_REFERENCE_RE = re.compile(
    r"^\$([A-Za-z_][0-9A-Za-z_]*)$"
)
_TOOL_REGISTRY_DIAGNOSTIC_FIELD_PATH_RE = re.compile(
    r"\b(?:headers|query_params|json_body|response_path|result_fields)"
    r"(?:\.[A-Za-z0-9_\-\[\]]+)+"
)
_TOOL_REGISTRY_DIAGNOSTIC_BRACKET_FIELD_PATH_RE = re.compile(
    r"\b(?:headers|query_params|json_body|response_path|result_fields)"
    r"(?:(?:\.[A-Za-z0-9_\-]+(?:\[\d+\])*)|"
    r"(?:\[(?:\"[^\"]*\"|'[^']*'|\d+)\]))+"
)
_TOOL_REGISTRY_DIAGNOSTIC_MAPPING_PATH_RE = re.compile(
    r"\b(?P<context>response_path|result_fields(?:\.[A-Za-z0-9_\-\[\]]+)*)"
    r"(?P<separator>\s*[:=]\s*)"
    r"(?P<path>\$(?:\.[A-Za-z0-9_\-\[\]]+)+)"
)
_TOOL_REGISTRY_DIAGNOSTIC_BRACKET_MAPPING_PATH_RE = re.compile(
    r"\b(?P<context>response_path|result_fields(?:\.[A-Za-z0-9_\-\[\]]+)*)"
    r"(?P<separator>\s*[:=]\s*)"
    r"(?P<path>\$(?:(?:\.[A-Za-z0-9_\-]+(?:\[\d+\])*)|"
    r"(?:\[(?:\"[^\"]*\"|'[^']*'|\d+)\]))+)"
)
_TOOL_REGISTRY_DIAGNOSTIC_JSONPATH_DOT_SEGMENT_RE = re.compile(
    r"(?P<prefix>\.)(?P<field>[A-Za-z0-9_\-]+)(?=(?:\.|\[|$))"
)
_TOOL_REGISTRY_DIAGNOSTIC_JSONPATH_BRACKET_SEGMENT_RE = re.compile(
    r"\[(?P<quote>['\"])(?P<field>[^'\"]*)(?P=quote)\]"
)
_HTTP_JSON_URL_CONTROL_OR_SPACE_RE = re.compile(r"[\x00-\x20\x7f]")
_HTTP_JSON_QUERY_PARAM_NAME_UNSAFE_RE = re.compile(r"[\x00-\x20\x7f=&?#]")
_HTTP_JSON_HEADER_NAME_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_HTTP_JSON_HEADER_VALUE_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HTTP_JSON_SUPPORTED_CONTENT_ENCODINGS = ("identity", "gzip", "deflate")
_HTTP_JSON_RESPONSE_DIAGNOSTIC_HEADER_HINTS = (
    ("Retry-After", "retry-after"),
    ("X-RateLimit-Reset", "rate-limit-reset"),
    ("RateLimit-Reset", "rate-limit-reset"),
    ("X-RateLimit-Remaining", "rate-limit-remaining"),
    ("RateLimit-Remaining", "rate-limit-remaining"),
    ("X-RateLimit-Limit", "rate-limit-limit"),
    ("RateLimit-Limit", "rate-limit-limit"),
    ("X-Request-ID", "request id"),
    ("Request-ID", "request id"),
    ("X-Correlation-ID", "correlation id"),
    ("Traceparent", "traceparent"),
    ("X-Trace-ID", "trace id"),
    ("X-Amzn-RequestId", "request id"),
    ("X-Amzn-Trace-Id", "trace id"),
    ("CF-Ray", "request id"),
)
_HTTP_JSON_RESPONSE_REQUEST_ID_HEADER_NAMES = (
    "X-Request-ID",
    "Request-ID",
    "X-Amzn-RequestId",
    "CF-Ray",
)


def normalize_tool_spec(tool_spec: dict[str, object]) -> ToolInvocation:
    tool_spec = _coerce_tool_registry_spec_payload(tool_spec)
    if not isinstance(tool_spec, Mapping):
        tool_spec = {}
    name = str(_coerce_tool_execution_string_like_value(tool_spec.get("name", ""))).strip()
    tool_input = _coerce_tool_registry_spec_payload(tool_spec.get("input"))
    if not isinstance(tool_input, Mapping):
        tool_input = {}
    return ToolInvocation(name=name, tool_input=dict(tool_input))


def _is_non_text_sequence(raw_value: object) -> bool:
    return isinstance(raw_value, Sequence) and not isinstance(
        raw_value,
        (str, bytes, bytearray, memoryview),
    )


def _normalize_planned_tool_names(raw_value: object) -> list[str]:
    if not _is_non_text_sequence(raw_value):
        return []
    normalized_names: list[str] = []
    seen_names: set[str] = set()
    for raw_name in raw_value:
        raw_name = _coerce_tool_execution_string_like_value(raw_name)
        canonical_name = normalize_tool_registry_name(str(raw_name).strip())
        if not canonical_name or canonical_name == "task_plan" or canonical_name in seen_names:
            continue
        normalized_names.append(canonical_name)
        seen_names.add(canonical_name)
    return normalized_names


def _build_task_plan_steps(
    *,
    planned_tool_names: list[str],
    planned_tool_labels: list[str] | None = None,
    planned_tool_kinds: list[str] | None = None,
) -> list[str]:
    steps = ["Analyze request"]
    label_by_name: dict[str, str] = {}
    kind_by_name: dict[str, str] = {}
    if _is_non_text_sequence(planned_tool_labels):
        for idx, raw_label in enumerate(planned_tool_labels):
            if idx >= len(planned_tool_names):
                break
            raw_label = _coerce_tool_execution_string_like_value(raw_label)
            label = str(raw_label).strip()
            if label:
                label_by_name[planned_tool_names[idx]] = label
    if _is_non_text_sequence(planned_tool_kinds):
        for idx, raw_kind in enumerate(planned_tool_kinds):
            if idx >= len(planned_tool_names):
                break
            raw_kind = _coerce_tool_execution_string_like_value(raw_kind)
            kind = _normalize_tool_semantic_kind(raw_kind)
            if kind:
                kind_by_name[planned_tool_names[idx]] = kind

    for tool_name in planned_tool_names:
        semantic_kind = kind_by_name.get(tool_name)
        if semantic_kind == "knowledge_retrieval" or tool_name == "task_retrieve":
            step = "Retrieve supporting context"
        elif semantic_kind == "local_calculator" or tool_name == "calc_eval":
            step = "Evaluate calculation"
        else:
            display_name = label_by_name.get(tool_name) or tool_name
            step = f"Run {display_name}"
        if step not in steps:
            steps.append(step)

    steps.append("Synthesize final answer")
    return steps


def _run_task_plan(*, tool_input: dict[str, object], prompt: str, user_id: str) -> dict[str, object]:
    del user_id
    prompt_preview = str(tool_input.get("prompt_preview", "")).strip() or prompt.strip()[:120]
    planned_tool_names = _normalize_planned_tool_names(tool_input.get("planned_tool_names"))
    if "planned_tool_names" in tool_input and _is_non_text_sequence(
        tool_input.get("planned_tool_names")
    ):
        planned_tool_labels = tool_input.get("planned_tool_labels")
        planned_tool_kinds = tool_input.get("planned_tool_kinds")
        steps = _build_task_plan_steps(
            planned_tool_names=planned_tool_names,
            planned_tool_labels=(
                planned_tool_labels
                if _is_non_text_sequence(planned_tool_labels)
                else None
            ),
            planned_tool_kinds=(
                planned_tool_kinds
                if _is_non_text_sequence(planned_tool_kinds)
                else None
            ),
        )
    else:
        steps = ["Analyze request"]
        normalized = prompt.lower()
        if (
            "rag" in normalized
            or "知识" in normalized
            or "检索" in normalized
            or "context" in normalized
            or "[multi-tool]" in normalized
            or "[mock-multi-tool]" in normalized
        ):
            steps.append("Retrieve supporting context")
        if _extract_calc_expression(prompt):
            steps.append("Evaluate calculation")
        steps.append("Synthesize final answer")
    return {
        "plan": " -> ".join(steps),
        "steps": steps,
        "prompt_preview": prompt_preview,
        "echo": True,
    }


def _run_task_retrieve(
    *,
    tool_input: dict[str, object],
    prompt: str,
    user_id: str,
) -> dict[str, object]:
    query = str(tool_input.get("query", ""))
    top_k_raw = tool_input.get("top_k")
    top_k = top_k_raw if isinstance(top_k_raw, int) else 4
    kb_raw = tool_input.get("knowledge_base_id")
    kb_id = str(kb_raw or get_settings().rag_default_knowledge_base_id)
    owner_user_id = (
        SHARED_RAG_SCOPE_USER_ID if is_shared_knowledge_base_id(kb_id) else user_id
    )
    try:
        result = query_knowledge_base(
            user_id=owner_user_id,
            knowledge_base_id=kb_id,
            query_text=query or prompt,
            top_k=top_k,
        )
    except Exception as exc:  # noqa: BLE001
        raise MockToolExecutionError(
            f"RAG query failed: {exc}",
            fatal=False,
        ) from exc
    safe_hits = sanitize_rag_query_hits(result.get("hits"))
    chunks = [
        str(x.get("content", "")).strip()
        for x in safe_hits
        if isinstance(x, dict)
    ]
    clean_chunks = [x for x in chunks if x]
    raw_kb_id = str(result.get("knowledge_base_id", kb_id))
    return {
        "chunks": clean_chunks,
        "hits": safe_hits,
        "hit_count": int(result.get("hit_count", 0) or 0),
        "knowledge_base_id": normalize_knowledge_base_id(raw_kb_id),
        "collection": sanitize_rag_collection_name(result.get("collection")),
    }


def _run_calc_eval(*, tool_input: dict[str, object], prompt: str, user_id: str) -> dict[str, object]:
    del prompt, user_id
    expression = str(tool_input.get("expression", "")).strip()
    if not expression:
        raise MockToolExecutionError(
            "Calculator tool requires a non-empty expression.",
            fatal=False,
        )
    try:
        value = _safe_eval_expression(expression)
    except Exception as exc:
        raise MockToolExecutionError(
            f"Calculator parse/eval failed: {exc}",
            fatal=False,
        ) from exc
    return {
        "expression": expression,
        "result": value,
        "tool_kind": "local_calculator",
    }


_REGISTERED_TOOLS = {
    "task_plan": ToolRegistration(
        name="task_plan",
        kind="task_planner",
        label="Task Planner",
        retryable_by_default=True,
        default_timeout_ms=3_000,
        requires_user_context=True,
        supports_result_preview=True,
        runner=_run_task_plan,
        result_preview_keys=("plan", "steps"),
    ),
    "task_retrieve": ToolRegistration(
        name="task_retrieve",
        kind="knowledge_retrieval",
        label="Knowledge Retrieval",
        retryable_by_default=True,
        default_timeout_ms=5_000,
        requires_user_context=True,
        supports_result_preview=True,
        runner=_run_task_retrieve,
        result_preview_keys=("hit_count", "knowledge_base_id"),
    ),
    "calc_eval": ToolRegistration(
        name="calc_eval",
        kind="local_calculator",
        label="Calculator",
        retryable_by_default=True,
        default_timeout_ms=3_000,
        requires_user_context=True,
        supports_result_preview=True,
        runner=_run_calc_eval,
        result_preview_keys=("expression", "result"),
    ),
}

_TOOL_NAME_ALIASES: dict[str, str] = {
    "mock_plan": "task_plan",
    "mock_retrieve": "task_retrieve",
}


def normalize_tool_registry_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        return normalized
    normalized = re.sub(r"\s*\[[^\[\]]+\]\s*$", "", normalized)
    return _TOOL_NAME_ALIASES.get(normalized, normalized)


def normalize_tool_registry_names(names: tuple[str, ...] | list[str] | set[str]) -> tuple[str, ...]:
    normalized_names: list[str] = []
    for name in names:
        normalized_name = normalize_tool_registry_name(str(name))
        if normalized_name and normalized_name not in normalized_names:
            normalized_names.append(normalized_name)
    return tuple(normalized_names)


def _normalize_named_tool_registry_component_name(name: object | None) -> str | None:
    if isinstance(name, UserString):
        name = str(name)
    if not isinstance(name, str):
        return None
    normalized = name.strip().lower()
    return normalized or None


def _normalize_tool_lookup_text(name: object | None) -> str | None:
    if not isinstance(name, str):
        return None
    normalized = re.sub(r"\s*\[[^\[\]]+\]\s*$", "", name.strip())
    normalized = " ".join(normalized.lower().split())
    return normalized or None


def _resolve_provider_tool_name(
    raw_name: object,
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> str | None:
    canonical_name = normalize_tool_registry_name(str(raw_name).strip())
    if canonical_name and resolve_tool_registration(
        canonical_name,
        registry_provider=registry_provider,
    ) is not None:
        return canonical_name
    lookup_text = _normalize_tool_lookup_text(raw_name)
    if lookup_text is None:
        return canonical_name or None
    registry = resolve_tool_registry_provider(
        registry_provider=registry_provider,
    ).load_tool_registry()
    for tool_name, registration in registry.items():
        candidate_names = {
            _normalize_tool_lookup_text(tool_name),
            _normalize_tool_lookup_text(registration.label),
            _normalize_tool_lookup_text(
                get_tool_display_name(tool_name, registry_provider=registry_provider)
            ),
        }
        if lookup_text in candidate_names:
            return tool_name
    return canonical_name or None


def get_tool_display_name(
    name: str,
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> str:
    registration = resolve_tool_registration(name=name, registry_provider=registry_provider)
    return get_tool_display_name_from_registration(name=name, registration=registration)


def build_tool_plan_summary(
    tool_plan: list[dict[str, object]],
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> str:
    if not tool_plan:
        return "Planned tools: none"
    names = []
    for item in tool_plan:
        tool_name = str(item.get("name", "")).strip()
        if not tool_name:
            continue
        registration = resolve_tool_registration(
            tool_name,
            registry_provider=registry_provider,
        )
        if (
            get_tool_semantic_kind(
                name=tool_name,
                registration=registration,
            )
            == "task_planner"
        ):
            continue
        names.append(get_tool_display_name(tool_name, registry_provider=registry_provider))
    if not names:
        return "Planned tools: none"
    return "Planned tools: " + ", ".join(names)


def _annotate_task_plan_tool_input(
    tool_plan: list[dict[str, object]],
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> list[dict[str, object]]:
    if not tool_plan:
        return tool_plan
    planned_tool_names: list[str] = []
    planned_tool_labels: list[str] = []
    planned_tool_kinds: list[str] = []
    planned_tool_execution_kinds: list[str] = []
    for item in tool_plan:
        tool_name = normalize_tool_registry_name(str(item.get("name", "")).strip())
        if not tool_name:
            continue
        registration = resolve_tool_registration(
            name=tool_name,
            registry_provider=registry_provider,
        )
        semantic_kind = (
            get_tool_semantic_kind(
                name=tool_name,
                registration=registration,
            )
            if registration is not None
            else None
        )
        if semantic_kind == "task_planner":
            continue
        planned_tool_names.append(tool_name)
        planned_tool_labels.append(
            get_tool_display_name(tool_name, registry_provider=registry_provider)
        )
        planned_tool_kinds.append(semantic_kind or "")
        planned_tool_execution_kinds.append(
            _normalize_tool_execution_kind(registration.execution_kind) or ""
            if registration is not None
            else ""
        )

    annotated_plan: list[dict[str, object]] = []
    task_plan_annotated = False
    for item in tool_plan:
        if task_plan_annotated:
            annotated_plan.append(item)
            continue
        tool_name = normalize_tool_registry_name(str(item.get("name", "")).strip())
        registration = resolve_tool_registration(
            name=tool_name,
            registry_provider=registry_provider,
        )
        semantic_kind = (
            get_tool_semantic_kind(
                name=tool_name,
                registration=registration,
            )
            if registration is not None
            else None
        )
        if semantic_kind != "task_planner":
            annotated_plan.append(item)
            continue
        tool_input = item.get("input")
        if not isinstance(tool_input, dict):
            tool_input = {}
        annotated_input = dict(tool_input)
        annotated_input["planned_tool_names"] = list(planned_tool_names)
        annotated_input["planned_tool_labels"] = list(planned_tool_labels)
        annotated_input["planned_tool_kinds"] = list(planned_tool_kinds)
        annotated_input["planned_tool_execution_kinds"] = list(
            planned_tool_execution_kinds
        )
        annotated_plan.append(
            {
                **item,
                "input": annotated_input,
            }
        )
        task_plan_annotated = True
    return annotated_plan


def _is_tool_enabled_for_planning(
    name: str,
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> bool:
    return (
        resolve_tool_registration(
            name=name,
            registry_provider=registry_provider,
        )
        is not None
    )


def _get_enabled_planning_optional_tool_names(
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> tuple[str, ...]:
    registry = resolve_tool_registry_provider(
        registry_provider=registry_provider,
    ).load_tool_registry()
    optional_names = []
    for name, registration in registry.items():
        if (
            get_tool_semantic_kind(
                name=name,
                registration=registration,
            )
            == "task_planner"
        ):
            continue
        optional_names.append(name)
    optional_names.sort(
        key=lambda name: (
            1 if normalize_tool_registry_name(name) in _REGISTERED_TOOLS else 0,
        )
    )
    return tuple(optional_names)


def _get_enabled_planning_primary_tool_name(
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> str | None:
    registry = resolve_tool_registry_provider(
        registry_provider=registry_provider,
    ).load_tool_registry()
    candidate_names = list(registry)
    candidate_names.sort(
        key=lambda name: (
            1 if normalize_tool_registry_name(name) in _REGISTERED_TOOLS else 0,
        )
    )
    for name in candidate_names:
        registration = registry.get(name)
        if registration is None:
            continue
        if (
            get_tool_semantic_kind(
                name=name,
                registration=registration,
            )
            == "task_planner"
        ):
            return name
    return None


def _get_first_enabled_planning_tool_name_for_kind(
    kind: str,
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> str | None:
    for name in _get_enabled_planning_optional_tool_names(
        registry_provider=registry_provider,
    ):
        registration = resolve_tool_registration(
            name,
            registry_provider=registry_provider,
        )
        if registration is None:
            continue
        if (
            get_tool_semantic_kind(
                name=name,
                registration=registration,
            )
            == kind
        ):
            return name
    return None


def get_enabled_planning_tool_names(
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> tuple[str, ...]:
    names: list[str] = []
    primary_planner_name = _get_enabled_planning_primary_tool_name(
        registry_provider=registry_provider,
    )
    if primary_planner_name:
        names.append(primary_planner_name)
    names.extend(
        _get_enabled_planning_optional_tool_names(
            registry_provider=registry_provider,
        )
    )
    return tuple(names)


def get_enabled_planning_tool_labels(
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> tuple[str, ...]:
    return tuple(
        get_tool_display_name(name, registry_provider=registry_provider)
        for name in get_enabled_planning_tool_names(
            registry_provider=registry_provider,
        )
    )


def load_tool_registry(
    *,
    provider: ToolRegistryProvider | None = None,
    loader: ToolRegistryLoader | None = None,
    overrides: dict[str, ToolRegistration] | None = None,
) -> dict[str, ToolRegistration]:
    return build_tool_registry_provider(
        provider=provider,
        loader=loader,
        overrides=overrides,
    ).load_tool_registry()


def get_default_tool_registry() -> dict[str, ToolRegistration]:
    return dict(_REGISTERED_TOOLS)


def get_default_tool_registry_provider() -> ToolRegistryProvider:
    return DefaultToolRegistryProvider()


def build_profile_tool_registry_provider(*, profile_name: str) -> ToolRegistryProvider:
    profile_config = build_tool_registry_profile_settings_config(profile_name=profile_name)
    return build_tool_registry_provider(
        overrides=profile_config.overrides or None,
        disabled_tool_names=profile_config.disabled_tool_names,
    )


def build_profile_tool_registry_loader(*, profile_name: str) -> ToolRegistryLoader:
    profile_config = build_tool_registry_profile_settings_config(profile_name=profile_name)
    registry = build_tool_registry(
        overrides=profile_config.overrides or None,
        disabled_tool_names=profile_config.disabled_tool_names,
    )
    return lambda: dict(registry)


def _annotate_loader_factory_profile(
    factory: ToolRegistryLoaderFactory,
    *,
    profile_name: str,
) -> ToolRegistryLoaderFactory:
    setattr(factory, "_tool_registry_profile_name", profile_name)
    return factory


def _annotate_provider_factory_profile(
    factory: ToolRegistryProviderFactory,
    *,
    profile_name: str,
) -> ToolRegistryProviderFactory:
    setattr(factory, "_tool_registry_profile_name", profile_name)
    return factory


def resolve_named_tool_registry_loader(name: str) -> ToolRegistryLoader | None:
    normalized = _normalize_named_tool_registry_component_name(name)
    if normalized is None:
        return None
    if normalized == "default":
        return get_default_tool_registry
    return None


def resolve_named_tool_registry_provider_reference(
    name: str,
    *,
    named_providers: dict[str, ToolRegistryProvider] | None = None,
    named_sources: dict[str, ToolRegistryProvider] | None = None,
) -> ToolRegistryProvider | None:
    normalized = _normalize_named_tool_registry_component_name(name)
    if normalized is None:
        return None
    if normalized == "default":
        return get_default_tool_registry_provider()
    if named_providers and normalized in named_providers:
        return named_providers[normalized]
    if named_sources and normalized in named_sources:
        return named_sources[normalized]
    normalized_source = get_tool_registry_provider_source_name_from_settings(
        settings=SimpleNamespace(tool_registry_provider_source=name)
    )
    if named_sources and normalized_source in named_sources:
        return named_sources[normalized_source]
    return None

def resolve_named_tool_registry_loader_factory(
    name: str,
    *,
    named_loader_factories: dict[str, ToolRegistryLoaderFactory] | None = None,
) -> ToolRegistryLoaderFactory | None:
    normalized = _normalize_named_tool_registry_component_name(name)
    if normalized is None:
        return None
    if named_loader_factories and normalized in named_loader_factories:
        return named_loader_factories[normalized]
    if normalized == "default":
        return lambda settings=None: get_default_tool_registry
    if normalized in _TOOL_REGISTRY_PROFILE_CONFIGS:
        return _annotate_loader_factory_profile(
            lambda settings=None: build_profile_tool_registry_loader(
                profile_name=normalized
            ),
            profile_name=normalized,
        )
    return None


def resolve_named_tool_registry_provider_factory(
    name: str,
    *,
    named_provider_factories: dict[str, ToolRegistryProviderFactory] | None = None,
) -> ToolRegistryProviderFactory | None:
    normalized = _normalize_named_tool_registry_component_name(name)
    if normalized is None:
        return None
    if named_provider_factories and normalized in named_provider_factories:
        return named_provider_factories[normalized]
    if normalized == "default":
        return lambda settings=None: get_default_tool_registry_provider()
    if normalized in _TOOL_REGISTRY_PROFILE_CONFIGS:
        return _annotate_provider_factory_profile(
            lambda settings=None: build_profile_tool_registry_provider(
                profile_name=normalized
            ),
            profile_name=normalized,
        )
    return None


def get_tool_registry_provider_source_name_from_settings(
    *,
    settings: object | None = None,
) -> str:
    if settings is None:
        settings = get_settings()
    raw_source_name = getattr(settings, "tool_registry_provider_source", None)
    normalized = _normalize_named_tool_registry_component_name(raw_source_name)
    return normalized or "default"


def get_tool_registry_provider_source_specs_from_settings(
    *,
    settings: object | None = None,
) -> dict[str, dict[str, object]]:
    if settings is None:
        settings = get_settings()
    raw_sources = getattr(settings, "tool_registry_provider_sources_json", None)
    source_specs = _parse_tool_registry_json_object_setting(raw_sources)
    if source_specs is None:
        return {}

    normalized_source_specs: dict[str, dict[str, object]] = {}
    for source_name, spec in source_specs.items():
        spec = _coerce_tool_registry_spec_payload(spec)
        if not isinstance(source_name, str) or not isinstance(spec, Mapping):
            continue
        normalized_source_name = get_tool_registry_provider_source_name_from_settings(
            settings=SimpleNamespace(
                tool_registry_provider_source=source_name,
            )
        )
        if normalized_source_name == "default":
            continue
        normalized_source_specs[normalized_source_name] = dict(spec)
    return normalized_source_specs


def get_tool_registry_profile_name_from_settings(*, settings: object | None = None) -> str:
    if settings is None:
        settings = get_settings()
    raw_profile_name = getattr(settings, "tool_registry_profile", None)
    normalized = _normalize_named_tool_registry_component_name(raw_profile_name)
    return normalized or "default"


def get_available_tool_registry_profile_names() -> tuple[str, ...]:
    return tuple(_TOOL_REGISTRY_PROFILE_CONFIGS.keys())


def get_available_tool_registry_provider_source_names(
    *,
    settings: object | None = None,
) -> tuple[str, ...]:
    named_sources = build_tool_registry_provider_sources_from_settings(settings=settings)
    names = ["default"]
    names.extend(
        name for name in sorted(named_sources) if name and name != "default"
    )
    return tuple(names)


def build_tool_registry_profile_settings_config(
    *,
    profile_name: str,
) -> ToolRegistrySettingsConfig:
    return _TOOL_REGISTRY_PROFILE_CONFIGS.get(
        profile_name,
        _TOOL_REGISTRY_PROFILE_CONFIGS["default"],
    )


def build_tool_registry_extra_tools_from_specs(
    *,
    extra_tool_specs: object,
    settings: object | None = None,
    provider_source_name: str | None = None,
) -> dict[str, ToolRegistration]:
    extra_tool_specs = _coerce_tool_registry_spec_payload(extra_tool_specs)
    if not isinstance(extra_tool_specs, dict):
        return {}
    try:
        extra_tools_json = json.dumps(extra_tool_specs, ensure_ascii=False)
    except TypeError:
        return {}
    extra_tools_settings = _clone_tool_execution_settings(
        settings=settings or SimpleNamespace(),
        tool_registry_extra_tools_json=extra_tools_json,
        **(
            {"tool_registry_provider_source": provider_source_name}
            if provider_source_name
            else {}
        ),
    )
    return build_tool_registry_extra_tools_from_settings(settings=extra_tools_settings)


def _clone_tool_registry_provider_source_scoped_settings(
    *,
    settings: object | None,
    provider_source_name: str | None,
    profile_name: str | None = None,
) -> object:
    overrides: dict[str, object] = {}
    if provider_source_name:
        overrides["tool_registry_provider_source"] = provider_source_name
    if profile_name:
        overrides["tool_registry_profile"] = profile_name
    if not overrides:
        return settings or SimpleNamespace()
    return _clone_tool_execution_settings(
        settings=settings or SimpleNamespace(),
        **overrides,
    )


def _coerce_tool_registry_spec_payload(raw_value: object) -> object:
    try:
        return _coerce_http_json_json_compatible_body(raw_value)
    except TypeError:
        return raw_value


def _parse_tool_registry_json_object_setting(raw_value: object) -> dict[str, object] | None:
    raw_value = _coerce_tool_execution_string_like_value(raw_value)
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    try:
        parsed_value = json.loads(raw_value)
    except json.JSONDecodeError:
        return None
    parsed_value = _coerce_tool_registry_spec_payload(parsed_value)
    if not isinstance(parsed_value, Mapping):
        return None
    return dict(parsed_value)


def _merge_inline_tool_registry_extra_tool_specs(
    spec: dict[str, object],
    *,
    adapter_keys: set[str],
) -> dict[str, object]:
    if not any(key in spec for key in adapter_keys):
        return spec
    inline_extra_tool_specs = {
        key: value for key, value in spec.items() if key not in adapter_keys
    }
    if not inline_extra_tool_specs:
        return spec
    merged_spec = dict(spec)
    configured_extra_tools = _coerce_tool_registry_spec_payload(
        merged_spec.get("extra_tools")
    )
    if isinstance(configured_extra_tools, Mapping):
        merged_spec["extra_tools"] = {
            **inline_extra_tool_specs,
            **dict(configured_extra_tools),
        }
    else:
        merged_spec["extra_tools"] = inline_extra_tool_specs
    return merged_spec


def _order_tool_registry_provider_source_specs(
    source_specs: Mapping[object, object],
) -> list[tuple[object, object]]:
    source_items_by_name: dict[str, tuple[object, object]] = {}
    for source_name, spec in source_specs.items():
        normalized_source_name = get_tool_registry_provider_source_name_from_settings(
            settings=SimpleNamespace(
                tool_registry_provider_source=source_name,
            )
        )
        source_items_by_name[normalized_source_name] = (source_name, spec)

    ordered: list[tuple[object, object]] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(normalized_source_name: str) -> None:
        if normalized_source_name in visited:
            return
        if normalized_source_name in visiting:
            return
        item = source_items_by_name.get(normalized_source_name)
        if item is None:
            return
        visiting.add(normalized_source_name)
        _source_name, spec = item
        spec = _coerce_tool_registry_spec_payload(spec)
        if isinstance(spec, Mapping):
            provider_reference = get_tool_registry_provider_source_name_from_settings(
                settings=SimpleNamespace(
                    tool_registry_provider_source=spec.get("provider"),
                )
            )
            if (
                provider_reference is not None
                and provider_reference in source_items_by_name
            ):
                visit(provider_reference)
        visiting.discard(normalized_source_name)
        visited.add(normalized_source_name)
        ordered.append(item)

    for source_name in source_items_by_name:
        visit(source_name)
    return ordered


def _find_tool_registry_provider_source_reference_cycle_edges(
    source_specs: Mapping[object, object],
) -> dict[str, str]:
    source_references: dict[str, str] = {}
    source_names: set[str] = set()
    for source_name, spec in source_specs.items():
        normalized_source_name = get_tool_registry_provider_source_name_from_settings(
            settings=SimpleNamespace(
                tool_registry_provider_source=source_name,
            )
        )
        source_names.add(normalized_source_name)
        spec = _coerce_tool_registry_spec_payload(spec)
        if not isinstance(spec, Mapping):
            continue
        provider_reference = get_tool_registry_provider_source_name_from_settings(
            settings=SimpleNamespace(
                tool_registry_provider_source=spec.get("provider"),
            )
        )
        source_references[normalized_source_name] = provider_reference

    source_references = {
        source_name: reference_name
        for source_name, reference_name in source_references.items()
        if reference_name in source_names
    }
    cycle_edges: dict[str, str] = {}
    for source_name in source_references:
        path: list[str] = []
        path_indexes: dict[str, int] = {}
        current_name = source_name
        while current_name in source_references:
            if current_name in path_indexes:
                for cycle_name in path[path_indexes[current_name] :]:
                    cycle_edges[cycle_name] = source_references[cycle_name]
                break
            if current_name in cycle_edges:
                break
            path_indexes[current_name] = len(path)
            path.append(current_name)
            current_name = source_references[current_name]
    return cycle_edges


def _order_tool_registry_provider_specs(
    provider_specs: Mapping[object, object],
) -> list[tuple[object, object]]:
    provider_items_by_name: dict[str, tuple[object, object]] = {}
    for provider_name, spec in provider_specs.items():
        normalized_provider_name = _normalize_named_tool_registry_component_name(
            provider_name
        )
        if normalized_provider_name is None:
            continue
        provider_items_by_name[normalized_provider_name] = (provider_name, spec)

    ordered: list[tuple[object, object]] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(normalized_provider_name: str) -> None:
        if normalized_provider_name in visited:
            return
        if normalized_provider_name in visiting:
            return
        item = provider_items_by_name.get(normalized_provider_name)
        if item is None:
            return
        visiting.add(normalized_provider_name)
        _provider_name, spec = item
        spec = _coerce_tool_registry_spec_payload(spec)
        if isinstance(spec, Mapping):
            provider_reference = _normalize_named_tool_registry_component_name(
                spec.get("provider")
            )
            if (
                provider_reference is not None
                and provider_reference in provider_items_by_name
            ):
                visit(provider_reference)
        visiting.discard(normalized_provider_name)
        visited.add(normalized_provider_name)
        ordered.append(item)

    for provider_name in provider_items_by_name:
        visit(provider_name)
    return ordered


def _order_tool_registry_loader_specs(
    loader_specs: Mapping[object, object],
) -> list[tuple[object, object]]:
    loader_items_by_name: dict[str, tuple[object, object]] = {}
    for loader_name, spec in loader_specs.items():
        normalized_loader_name = _normalize_named_tool_registry_component_name(
            loader_name
        )
        if normalized_loader_name is None:
            continue
        loader_items_by_name[normalized_loader_name] = (loader_name, spec)

    ordered: list[tuple[object, object]] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(normalized_loader_name: str) -> None:
        if normalized_loader_name in visited:
            return
        if normalized_loader_name in visiting:
            return
        item = loader_items_by_name.get(normalized_loader_name)
        if item is None:
            return
        visiting.add(normalized_loader_name)
        _loader_name, spec = item
        spec = _coerce_tool_registry_spec_payload(spec)
        if isinstance(spec, Mapping):
            loader_reference = _normalize_named_tool_registry_component_name(
                spec.get("loader")
            )
            if (
                loader_reference is not None
                and loader_reference in loader_items_by_name
            ):
                visit(loader_reference)
        visiting.discard(normalized_loader_name)
        visited.add(normalized_loader_name)
        ordered.append(item)

    for loader_name in loader_items_by_name:
        visit(loader_name)
    return ordered


def _order_tool_registry_factory_specs(
    factory_specs: Mapping[object, object],
) -> list[tuple[object, object]]:
    factory_items_by_name: dict[str, tuple[object, object]] = {}
    for factory_name, spec in factory_specs.items():
        normalized_factory_name = _normalize_named_tool_registry_component_name(
            factory_name
        )
        if normalized_factory_name is None:
            continue
        factory_items_by_name[normalized_factory_name] = (factory_name, spec)

    ordered: list[tuple[object, object]] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(normalized_factory_name: str) -> None:
        if normalized_factory_name in visited:
            return
        if normalized_factory_name in visiting:
            return
        item = factory_items_by_name.get(normalized_factory_name)
        if item is None:
            return
        visiting.add(normalized_factory_name)
        _factory_name, spec = item
        spec = _coerce_tool_registry_spec_payload(spec)
        if isinstance(spec, Mapping):
            factory_reference = _normalize_named_tool_registry_component_name(
                spec.get("factory")
            )
            if (
                factory_reference is not None
                and factory_reference in factory_items_by_name
            ):
                visit(factory_reference)
        visiting.discard(normalized_factory_name)
        visited.add(normalized_factory_name)
        ordered.append(item)

    for factory_name in factory_items_by_name:
        visit(factory_name)
    return ordered


from app.services.tool_runtime_http_json import (
    _normalize_result_preview_keys,
    _normalize_result_output_keys,
    _is_sensitive_result_key,
    _normalize_safe_explicit_result_keys,
    _normalize_runtime_semantic_kind,
    _normalize_tool_execution_kind,
    _build_tool_execution_runtime_template_context,
    _stringify_tool_execution_template_interpolation_value,
    _clone_tool_execution_settings,
    _render_tool_execution_template,
    _iter_missing_tool_execution_template_variables,
    _render_required_tool_execution_template,
    _render_tool_execution_template_for_static_analysis,
    _is_tool_execution_mapping_path_template,
    _iter_tool_execution_mapping_path_template_variable_references,
    _iter_missing_tool_execution_mapping_path_template_variables,
    _render_required_tool_execution_mapping_path_template,
    _render_tool_execution_mapping_path_template_for_static_analysis,
    _coerce_http_json_mapping_path_value,
    _coerce_http_json_mapping_field_name,
    _coerce_tool_execution_string_like_value,
    _iter_http_json_mapping_field_names,
    _resolve_tool_execution_mapping_path_for_static_validation,
    _resolve_tool_execution_template_value_for_static_validation,
    _coerce_tool_execution_value_for_static_validation,
    _iter_tool_execution_template_variable_references,
    _is_tool_execution_root_template_reference,
    _collect_tool_execution_runtime_template_validation_errors,
    _normalize_tool_execution_http_method,
    _describe_tool_execution_http_method_validation_error,
    _is_supported_tool_timeout_ms,
    _coerce_tool_execution_timeout_ms,
    _describe_tool_execution_timeout_ms_validation_error,
    _coerce_tool_default_timeout_ms,
    _describe_tool_default_timeout_ms_validation_error,
    _normalize_tool_execution_http_headers,
    _normalize_tool_execution_http_query_params,
    _is_supported_tool_execution_http_url,
    _describe_tool_execution_http_url_path_validation_error,
    _describe_tool_execution_http_url_query_validation_error,
    _iter_tool_execution_http_url_query_param_names,
    _describe_tool_execution_http_duplicate_query_param_validation_error,
    _describe_tool_execution_http_url_validation_error,
    _format_safe_tool_execution_http_url_origin,
    _format_safe_tool_execution_http_url_path,
    _format_safe_tool_execution_summary_field_name,
    _format_safe_tool_execution_diagnostic_path,
    _format_safe_tool_execution_template_variable_name,
    _format_safe_tool_execution_kind,
    _raise_http_json_rendered_url_validation_error,
    _raise_http_json_rendered_method_validation_error,
    _raise_http_json_rendered_timeout_ms_validation_error,
    _raise_http_json_rendered_duplicate_query_param_validation_error,
    _is_supported_tool_execution_http_scalar_value,
    _is_supported_tool_execution_http_query_value,
    _is_supported_tool_execution_http_query_param_name,
    _is_supported_tool_execution_http_header_name,
    _http_header_value_contains_line_break,
    _http_header_value_contains_control_character,
    _http_headers_contain_duplicate_names,
    _get_tool_execution_http_header_value,
    _is_supported_http_json_media_type,
    _get_http_json_media_type_parameter_values,
    _http_json_header_value_has_balanced_quoted_parameters,
    _is_supported_http_json_accept_header,
    _format_http_json_request_content_type_validation_error,
    _format_http_json_request_content_type_charset_validation_error,
    _format_http_json_request_header_quote_validation_error,
    _describe_http_json_request_content_type_validation_errors,
    _raise_http_json_rendered_request_content_type_validation_error,
    _ensure_http_json_request_content_type_header,
    _format_http_json_request_accept_validation_error,
    _describe_http_json_request_accept_validation_errors,
    _raise_http_json_rendered_request_accept_validation_error,
    _ensure_http_json_request_accept_header,
    _describe_tool_execution_http_value_validation_errors,
    _format_tool_execution_json_body_child_path,
    _describe_tool_execution_json_body_validation_errors,
    _raise_http_json_rendered_value_validation_error,
    _raise_http_json_rendered_json_body_validation_error,
    _raise_http_json_rendered_response_path_validation_error,
    _render_http_json_response_path,
    _raise_http_json_rendered_result_field_validation_error,
    _render_http_json_result_fields,
    _is_supported_tool_execution_response_path_segment,
    _is_supported_tool_execution_response_path,
    _normalize_tool_execution_response_path,
    _extract_tool_execution_response_value,
    _normalize_nonnegative_int_count_value,
    _flatten_http_json_retrieval_sequence,
    _extract_http_json_retrieval_list_from_container,
    _extract_http_json_retrieval_count_from_container,
    _extract_http_json_retrieval_count_from_nested_containers,
    _extract_http_json_retrieval_count_alias_from_mapping,
    _HTTP_JSON_RETRIEVAL_COUNT_ALIAS_FIELDS,
    _http_json_output_implies_retrieval_count,
    _http_json_output_implies_calculator_result,
    _get_safe_http_json_request_id_alias,
    _normalize_http_json_output_shape,
    _redact_http_json_sensitive_payload_text,
    _format_safe_http_json_payload_key,
    _redact_http_json_sensitive_payload_value,
    _normalize_http_json_safe_output_shape,
    _normalize_tool_result_projection_output,
    _redact_http_json_diagnostic_text,
    _format_safe_http_json_url_query,
    _format_safe_http_json_url_fragment,
    _format_safe_http_json_url_text,
    _redact_http_json_url_text,
    _redact_tool_registry_diagnostic_mapping_paths,
    _redact_tool_registry_diagnostic_bracket_field_paths,
    _format_safe_tool_execution_bracket_jsonpath,
    _redact_tool_registry_diagnostic_bracket_mapping_paths,
    _redact_tool_registry_diagnostic_value,
    _redact_http_json_raw_fallback_value,
    _redact_http_json_error_body_value,
    _coerce_http_json_error_body_preview_text,
    _format_http_json_error_body_preview,
    _coerce_http_json_body_preview_bytes,
    _format_http_json_response_body_preview,
    _append_http_json_response_header_diagnostic_hints,
    _format_http_json_http_error,
    _coerce_http_json_response_status_code,
    _http_json_response_status_value_is_present,
    _format_http_json_invalid_status_response,
    _get_http_json_adapter_attr,
    _call_http_json_adapter_method,
    _call_http_json_getheader_adapter,
    _get_http_json_response_status_code,
    _coerce_http_json_response_text,
    _get_http_json_response_reason,
    _get_http_json_response_url,
    _normalize_http_json_unreserved_percent_encoding,
    _normalize_http_json_query_for_drift_check,
    _normalize_http_json_url_for_drift_check,
    _http_json_response_url_matches_request_url,
    _format_http_json_redirected_response_url_error,
    _format_http_json_unexpected_status_response,
    _format_http_json_unexpected_status_response_body_decode_error,
    _format_http_json_empty_response,
    _coerce_http_json_response_body_bytes,
    _HttpJsonJsonBodyDumpMethodUnavailable,
    _HttpJsonJsonBodyDumpJsonMethodUnavailable,
    _HttpJsonResponseBodyAttrUnavailable,
    _is_http_json_parsed_body_attr,
    _read_http_json_response_body_attr,
    _coerce_http_json_json_compatible_body,
    _coerce_http_json_json_compatible_mapping_key,
    _call_http_json_json_body_dump_method,
    _http_json_callable_accepts_call,
    _call_http_json_json_body_dump_json_method,
    _coerce_http_json_json_body_dump_json_compatible,
    _read_http_json_json_body_dump_json_bytes,
    _coerce_http_json_response_json_body_bytes,
    _HttpJsonResponseBodyInitialReadTypeError,
    _read_http_json_response_body_chunked,
    _HttpJsonResponseBodyInitialIteratorTypeError,
    _HttpJsonResponseBodyIteratorUnavailable,
    _read_http_json_response_body_chunks,
    _read_http_json_response_body_iterator,
    _read_http_json_response_body_bytes,
    _close_http_json_response,
    _format_http_json_invalid_json_response,
    _format_http_json_invalid_charset_response,
    _coerce_http_json_header_text,
    _coerce_http_json_header_name_text,
    _get_http_json_header_items,
    _get_http_json_header_value_from_method,
    _get_http_json_header_text_from_mapping,
    _get_http_json_response_header_text,
    _format_http_json_response_header_diagnostic_hints,
    _get_http_json_response_request_id,
    _is_safe_http_json_request_id_value,
    _get_safe_http_json_request_id_display_value,
    _attach_http_json_response_request_id,
    _get_http_json_response_content_type,
    _get_http_json_response_content_encoding,
    _split_http_json_header_value,
    _split_http_json_header_values,
    _split_http_json_header_parameters,
    _get_http_json_response_charset,
    _decode_http_json_response_text,
    _normalize_http_json_content_encodings,
    _decompress_http_json_deflate_body,
    _decode_http_json_response_body_for_content_encoding,
    _is_supported_http_json_response_content_type,
    _format_http_json_invalid_content_type_response,
    _format_http_json_transport_error,
    _format_http_json_mapping_path_for_error,
    _format_http_json_mapping_payload_shape_key_for_error,
    _format_http_json_mapping_payload_shape_keys_for_error,
    _format_http_json_mapping_payload_shape_for_error,
    _format_http_json_result_field_mapping_error,
    _format_http_json_missing_result_field_mappings,
    _build_http_json_tool_runner,
    _build_invalid_tool_execution_runner,
    _build_tool_runner_from_execution_spec,
    _resolve_tool_execution_kind_from_spec,
    _build_tool_execution_summary_from_spec,
    _resolve_tool_execution_summary_value,
    _resolve_tool_execution_string_like_summary_value,
    _format_safe_tool_execution_summary_url_path,
    _sanitize_tool_execution_summary_value,
    sanitize_tool_execution_summary,
    sanitize_tool_execution_diagnostics,
    _describe_tool_execution_spec_validation_error,
    _describe_tool_execution_spec_validation_errors,
    _build_invalid_tool_execution_diagnostics,
    _group_invalid_tool_execution_messages_by_tool,
    _collect_invalid_tool_execution_messages_from_extra_tool_specs,
    _collect_invalid_tool_execution_messages_from_override_specs,
    build_tool_registry_settings_execution_diagnostics,
)

from app.services.tool_runtime_registry import (
    build_tool_registry_extra_tools_from_file,
    _resolve_tool_registry_file_path,
    _resolve_tool_registry_dir_path,
    load_tool_registry_file_payload,
    _normalize_tool_registry_file_diagnostics,
    _empty_tool_registry_file_diagnostics,
    _has_tool_registry_file_diagnostics,
    _merge_tool_registry_file_diagnostics,
    _impl__sanitize_tool_registry_file_diagnostics_with_provider_source_aliases,
    _impl__sanitize_tool_registry_source_diagnostics_with_provider_source_aliases,
    sanitize_tool_registry_file_diagnostics,
    sanitize_tool_registry_source_diagnostics,
    sanitize_tool_registry_diagnostics_summary_entries,
    sanitize_tool_registry_diagnostics_artifact_payload,
    _filter_tool_registry_json_object_setting_for_visited_registry_files,
    _clone_tool_registry_settings_without_visited_registry_file_components,
    _expand_skipped_registry_file_component_names,
    _build_tool_registry_from_file_registry,
    build_tool_registry_from_file_artifacts,
    build_tool_registry_loader_from_file_artifacts,
    build_tool_registry_provider_from_file_artifacts,
    build_tool_registry_from_file,
    build_tool_registry_loader_from_file,
    build_tool_registry_provider_from_file,
    _build_tool_registry_loader_factory_adapter,
    _build_tool_registry_provider_factory_adapter,
    build_tool_registry_loaders_from_settings_artifacts,
    build_tool_registry_loader_factories_from_settings_artifacts,
    build_tool_registry_loader_factories_from_settings,
    build_tool_registry_provider_factories_from_settings_artifacts,
    build_tool_registry_provider_factories_from_settings,
    build_tool_registry_loader_adapter,
    build_tool_registry_loaders_from_settings,
    build_tool_registry_provider_adapter,
    build_tool_registry_providers_from_settings,
    build_tool_registry_providers_from_settings_artifacts,
    build_tool_registry_provider_sources_from_settings,
    build_tool_registry_provider_sources_from_settings_artifacts,
    build_safe_tool_registry_provider_source_alias_map,
    resolve_unique_tool_registry_provider_source_alias,
    build_tool_registry_extra_tools_from_settings,
    _build_registry_overrides_from_specs,
    build_tool_registry_settings_config,
    build_tool_registry_overrides_from_settings,
    get_disabled_tool_names_from_settings,
    get_configured_tool_registry_provider,
    get_configured_tool_registry_provider_artifacts,
    build_tool_registry_diagnostics_summary_model,
    build_tool_registry_diagnostics_summary,
    _humanize_tool_registry_diagnostics_target,
    build_tool_registry_diagnostics_display_lines,
    build_tool_registry_diagnostics_runtime_artifacts_model,
    build_tool_registry_diagnostics_runtime_artifacts,
    build_tool_registry_diagnostics_audit_event,
    build_tool_registry_diagnostics_audit_service_action,
    build_tool_registry_diagnostics_audit_service_action_model,
    build_tool_registry_diagnostics_trace_service_action,
    build_tool_registry_diagnostics_trace_service_action_model,
    build_configured_tool_registry_provider_runtime_service_actions,
    build_configured_tool_registry_provider_runtime_service_actions_model,
    build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models,
    build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model,
    build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts,
    build_configured_tool_registry_provider_runtime_service_actions_outputs,
    build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model,
    build_configured_tool_registry_provider_runtime_service_action_model_from_dict,
    build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts,
    build_configured_tool_registry_provider_runtime_artifacts_model_from_dict,
    build_configured_tool_registry_provider_service_execution_model_from_dict,
    execute_configured_tool_registry_provider_runtime_service_actions,
    build_configured_tool_registry_provider_runtime_service_actions_result_model,
    build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models,
    build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict,
    build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict,
    execute_configured_tool_registry_provider_runtime_service_actions_result_model,
    execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models,
    execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models,
    execute_configured_tool_registry_provider_runtime_service_actions_model,
    execute_configured_tool_registry_provider_runtime_service_actions_outputs,
    build_configured_tool_registry_provider_service_execution_model,
    build_configured_tool_registry_provider_service_execution,
    build_configured_tool_registry_provider_service_execution_result_model,
    build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model,
    build_configured_tool_registry_provider_service_execution_result_model_from_models,
    build_configured_tool_registry_provider_service_execution_outputs_from_models,
    build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model,
    execute_configured_tool_registry_provider_service_execution_outputs_from_models,
    build_configured_tool_registry_provider_service_execution_outputs,
    execute_configured_tool_registry_provider_service_execution,
    execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model,
    execute_configured_tool_registry_provider_service_execution_outputs,
    execute_configured_tool_registry_provider_service_execution_model,
    build_configured_tool_registry_provider_preflight_summary_model,
    build_configured_tool_registry_provider_preflight_service_execution_model_from_dict,
    build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict,
    _merge_configured_tool_registry_provider_preflight_service_execution_payload,
    build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict,
    build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model,
    build_configured_tool_registry_provider_preflight_execution_models_from_dict,
    build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload,
    build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model,
    build_configured_tool_registry_provider_preflight_models_from_service_execution_payload,
    build_configured_tool_registry_provider_preflight_models_from_service_execution_model,
    build_configured_tool_registry_provider_preflight_models_from_dict,
    build_configured_tool_registry_provider_preflight_models_from_models,
    build_configured_tool_registry_provider_preflight_summary_model_from_dict,
    build_configured_tool_registry_provider_preflight_summary_model_from_result_model,
    build_configured_tool_registry_provider_preflight_summary_model_from_models,
    build_configured_tool_registry_provider_preflight_summary_model_from_parts,
    build_configured_tool_registry_provider_preflight_summary,
    build_configured_tool_registry_provider_preflight_outputs_from_resolved_models,
    build_configured_tool_registry_provider_preflight_outputs_from_models,
    build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model,
    build_configured_tool_registry_provider_preflight_outputs,
    build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload,
    build_configured_tool_registry_provider_preflight_outputs_from_dict,
    build_configured_tool_registry_provider_preflight_models,
    build_configured_tool_registry_provider_preflight_dicts,
    build_configured_tool_registry_provider_preflight_result_model,
    build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model,
    build_configured_tool_registry_provider_preflight_result_model_from_models,
    build_configured_tool_registry_provider_preflight_result_model_from_dict,
    build_configured_tool_registry_provider_preflight_result,
    execute_configured_tool_registry_provider_preflight_models_from_service_execution_model,
    execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model,
    execute_configured_tool_registry_provider_preflight_outputs,
    execute_configured_tool_registry_provider_preflight_summary_model,
    execute_configured_tool_registry_provider_preflight_summary,
    execute_configured_tool_registry_provider_preflight_dicts,
    execute_configured_tool_registry_provider_preflight_models,
    execute_configured_tool_registry_provider_preflight,
    execute_configured_tool_registry_provider_preflight_model,
    build_configured_tool_registry_provider_runtime_artifacts_model,
    build_configured_tool_registry_provider_runtime_artifacts,
)

from app.services.tool_runtime_execution import (
    _build_tool_result_summary_from_step_meta_semantics,
    _build_tool_rag_followup_content,
    _coerce_tool_output_mapping,
    _coerce_tool_output_preview_mapping,
    _extract_tool_rag_chunk_from_document_mapping,
    _extract_tool_rag_chunks_from_document_list,
    _extract_tool_rag_chunks_from_output,
    _normalize_tool_error_message_for_registration,
    _normalize_tool_input_for_registration,
    _normalize_tool_result_plan_steps,
    _parse_tool_json_mapping_string,
    _redact_tool_rag_chunk_text,
    _resolve_step_tool_safe_output,
    _sanitize_tool_attempt_error_result_payload,
    _sanitize_tool_plan_attempt_loop_result_payload,
    _sanitize_tool_plan_item_payload_dict,
    _sanitize_tool_plan_item_payload_list,
    _sanitize_tool_plan_item_result_payload,
    _sanitize_tool_plan_loop_effects_payload,
    _sanitize_tool_plan_loop_postprocess_payload,
    _sanitize_tool_plan_loop_terminal_result_payload,
    _sanitize_tool_plan_retry_loop_result_payload,
    _sanitize_tool_plan_success_bundle_payload,
    _sanitize_tool_plan_success_bundle_rag_followup_payload,
    _sanitize_tool_plan_rag_followup_payload,
    _sanitize_tool_terminal_failure_payload,
    _sanitize_tool_trace_event_payload,
    _sanitize_tool_trace_event_step,
    _step_tool_meta_uses_http_json_execution,
    _summarize_generic_tool_result_payload,
    _with_action_step_tool_input,
    build_action_step_initial_meta,
    build_action_step_initial_step,
    build_configured_tool_registry_provider_runtime_artifacts,
    build_configured_tool_registry_provider_runtime_artifacts_model,
    build_tool_attempt_bundle,
    build_tool_attempt_error_events,
    build_tool_attempt_error_transition,
    build_tool_attempt_execution,
    build_tool_attempt_loop_result,
    build_tool_attempt_loop_terminal_result,
    build_tool_attempt_outcome,
    build_tool_attempt_result,
    build_tool_attempt_start_events,
    build_tool_attempt_success_events,
    build_tool_attempt_success_transition,
    build_tool_end_payload,
    build_tool_error_meta,
    build_tool_error_payload,
    build_tool_execution_policy,
    build_tool_observation_entry,
    build_tool_phase,
    build_tool_iteration_context,
    build_tool_iteration_execution,
    build_tool_iteration_success_artifacts,
    build_tool_plan_item_continue_action,
    build_tool_plan_item_continue_service_action,
    build_tool_plan_item_continue_update,
    build_tool_plan_item_next_action,
    build_tool_plan_item_next_action_execution,
    build_tool_plan_item_execution,
    build_tool_plan_item_execution_result,
    build_tool_plan_item_postprocess,
    build_tool_plan_item_result,
    build_tool_plan_item_retry_loop_execution_result,
    build_tool_plan_item_retry_loop_result,
    build_tool_plan_item_return_action,
    build_tool_plan_item_return_service_actions,
    build_tool_plan_item_service_actions,
    build_tool_plan_item_service_effects,
    build_tool_plan_item_service_effects_execution,
    build_tool_plan_item_service_execution,
    build_tool_plan_item_stream_effects,
    build_tool_plan_item_success_bundle,
    build_tool_plan_item_success_effects,
    build_tool_plan_item_terminal_effects,
    build_tool_plan_item_terminal_return_effects,
    build_tool_plan_item_trace_write_action,
    build_tool_plan_item_trace_write_service_action,
    build_tool_prompt_with_observations,
    build_tool_rag_followup,
    build_tool_rag_step,
    build_tool_registry,
    build_tool_registry_provider,
    build_tool_result_output,
    build_tool_result_preview,
    build_tool_result_summary,
    build_tool_runtime_context,
    build_tool_runtime_input,
    build_tool_runtime_semantics_meta,
    build_tool_start_payload,
    build_tool_step_error_update,
    build_tool_step_output,
    build_tool_step_success_update,
    build_tool_success_meta,
    build_tool_terminal_failure_transition,
    build_tool_trace_event,
    build_tool_visible_input,
    compute_tool_retry_decision,
    ensure_tool_registration,
    execute_tool_plan_item_retry_loop,
    execute_tool_plan_item_service_actions,
    execute_tool_plan_item_service_execution,
    get_action_step_tool_meta,
    get_tool_default_timeout_ms,
    get_registered_tool_names,
    is_tool_retryable_by_default,
    maybe_raise_mock_tool_execution_error,
    maybe_raise_tool_execution_error,
    resolve_tool_registration,
    resolve_tool_registry_provider,
    tool_requires_user_context,
)

from app.services.tool_runtime_planning import (
    _build_provider_tool_plan,
    _build_provider_tool_plan_prompt,
    _build_rule_based_tool_plan,
    _coerce_provider_tool_plan_input_mapping,
    _coerce_provider_tool_plan_payload,
    _extract_calc_expression,
    _extract_knowledge_base_id,
    _extract_provider_response_content,
    _extract_provider_tool_plan_items,
    _extract_provider_tool_plan_items_from_payload,
    _normalize_provider_tool_plan,
    _normalize_provider_tool_plan_item,
    _safe_eval_expression,
    build_tool_plan,
    build_tool_plan_artifacts,
)

from app.services.module_export_utils import install_rebound_exports
from app.services import tool_runtime_display as _tool_runtime_display

install_rebound_exports(
    source_module=_tool_runtime_display,
    target_namespace=globals(),
    export_names=_tool_runtime_display._TOOL_RUNTIME_DISPLAY_EXPORTS,
)
