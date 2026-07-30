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
from app.services.chroma_rag_service import query_knowledge_base


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

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_source_name": self.provider_source_name,
            "tool_count": self.tool_count,
            "tool_names": self.tool_names,
            "tool_details": self.tool_details,
            "service_action_count": self.service_action_count,
            "service_action_kinds": self.service_action_kinds,
            "trace_write_count": self.trace_write_count,
            "audit_event_count": self.audit_event_count,
            "has_diagnostics": self.has_diagnostics,
            "diagnostics_total": self.diagnostics_total,
            "skipped_total": self.skipped_total,
            "missing_total": self.missing_total,
            "diagnostics_summary": self.diagnostics_summary,
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
        return {
            "provider": self.provider,
            "provider_source_name": self.provider_source_name,
            "runtime_artifacts": self.runtime_artifacts.to_dict(),
            "service_execution": self.service_execution.to_dict(),
            "trace_write_count": self.trace_write_count,
            "audit_event_count": self.audit_event_count,
            "summary": self.summary.to_dict(),
        }


@dataclass(frozen=True)
class ToolRegistryDiagnosticsSummaryModel:
    has_diagnostics: bool
    skipped_total: int
    missing_total: int
    total: int
    entries: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "has_diagnostics": self.has_diagnostics,
            "skipped_total": self.skipped_total,
            "missing_total": self.missing_total,
            "total": self.total,
            "entries": sanitize_tool_registry_diagnostics_summary_entries(
                self.entries
            ),
        }


def _sanitize_tool_runtime_trace_artifact_payload(payload: object) -> object:
    sanitized = sanitize_tool_registry_diagnostics_artifact_payload(payload)
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

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary.to_dict(),
            "trace_step": _sanitize_tool_runtime_trace_artifact_payload(
                self.trace_step
            ),
            "trace_event": _sanitize_tool_runtime_trace_artifact_payload(
                self.trace_event
            ),
            "audit_detail": _sanitize_tool_runtime_trace_artifact_payload(
                self.audit_detail
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

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "provider_source_name": self.provider_source_name,
            "provider_sources": self.provider_sources,
            "selected_source_diagnostics": sanitize_tool_registry_file_diagnostics(
                self.selected_source_diagnostics
            ),
            "source_diagnostics": sanitize_tool_registry_source_diagnostics(
                self.source_diagnostics
            ),
            "diagnostics_runtime": self.diagnostics_runtime.to_dict(),
            "audit_event": _sanitize_tool_runtime_trace_artifact_payload(
                self.audit_event
            ),
        }


@dataclass(frozen=True)
class ConfiguredToolRegistryProviderRuntimeServiceActionModel:
    kind: str
    trace_step: dict[str, object] | None = None
    trace_event: dict[str, object] | None = None
    persist_force: bool = False
    kwargs: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "kind": self.kind,
        }
        if self.trace_step is not None:
            payload["trace_step"] = _sanitize_tool_runtime_trace_artifact_payload(
                self.trace_step
            )
        if self.trace_event is not None:
            payload["trace_event"] = _sanitize_tool_runtime_trace_artifact_payload(
                self.trace_event
            )
        if self.persist_force:
            payload["persist_force"] = self.persist_force
        if self.kwargs is not None:
            payload["kwargs"] = _sanitize_tool_runtime_trace_artifact_payload(
                self.kwargs
            )
        return payload


@dataclass(frozen=True)
class ConfiguredToolRegistryProviderRuntimeServiceActionsModel:
    actions: tuple[ConfiguredToolRegistryProviderRuntimeServiceActionModel, ...]

    def to_dict(self) -> list[dict[str, object]]:
        return [action.to_dict() for action in self.actions]


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

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "provider_source_name": self.provider_source_name,
            "runtime_artifacts": self.runtime_artifacts.to_dict(),
            "service_actions": [action.to_dict() for action in self.service_actions],
        }


@dataclass(frozen=True)
class ConfiguredToolRegistryProviderServiceExecutionResultModel:
    provider: ToolRegistryProvider
    provider_source_name: str
    runtime_artifacts: ConfiguredToolRegistryProviderRuntimeArtifactsModel
    trace_write_count: int
    audit_event_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "provider_source_name": self.provider_source_name,
            "runtime_artifacts": self.runtime_artifacts.to_dict(),
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
    try:
        result = query_knowledge_base(
            user_id=user_id,
            knowledge_base_id=kb_id,
            query_text=query or prompt,
            top_k=top_k,
        )
    except Exception as exc:  # noqa: BLE001
        raise MockToolExecutionError(
            f"RAG query failed: {exc}",
            fatal=False,
        ) from exc
    chunks = [
        str(x.get("content", "")).strip()
        for x in result.get("hits", [])
        if isinstance(x, dict)
    ]
    clean_chunks = [x for x in chunks if x]
    return {
        "chunks": clean_chunks,
        "hits": result.get("hits", []),
        "hit_count": int(result.get("hit_count", 0) or 0),
        "knowledge_base_id": str(result.get("knowledge_base_id", kb_id)),
        "collection": result.get("collection"),
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

def build_tool_registry_extra_tools_from_file(
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


def _resolve_tool_registry_file_path(
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


def _resolve_tool_registry_dir_path(
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


def load_tool_registry_file_payload(
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


def _normalize_tool_registry_file_diagnostics(
    diagnostics: dict[str, list[str]],
) -> dict[str, tuple[str, ...]]:
    return {
        key: tuple(value)
        for key, value in diagnostics.items()
    }


def _empty_tool_registry_file_diagnostics() -> dict[str, tuple[str, ...]]:
    return {key: () for key in _TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS}


def _has_tool_registry_file_diagnostics(
    diagnostics: Mapping[str, tuple[str, ...]] | None,
) -> bool:
    if not isinstance(diagnostics, Mapping):
        return False
    for key in _TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS:
        values = diagnostics.get(key, ())
        if isinstance(values, (list, tuple)) and values:
            return True
    return False


def _merge_tool_registry_file_diagnostics(
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


def sanitize_tool_registry_file_diagnostics(
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


def sanitize_tool_registry_source_diagnostics(
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


def sanitize_tool_registry_diagnostics_summary_entries(
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


def sanitize_tool_registry_diagnostics_artifact_payload(payload: object) -> object:
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


def _filter_tool_registry_json_object_setting_for_visited_registry_files(
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


def _clone_tool_registry_settings_without_visited_registry_file_components(
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


def _expand_skipped_registry_file_component_names(
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


def _build_tool_registry_from_file_registry(
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


def build_tool_registry_from_file_artifacts(
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


def build_tool_registry_loader_from_file_artifacts(
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


def build_tool_registry_provider_from_file_artifacts(
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


def build_tool_registry_from_file(
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


def build_tool_registry_loader_from_file(
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


def build_tool_registry_provider_from_file(
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


def _build_tool_registry_loader_factory_adapter(
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


def _build_tool_registry_provider_factory_adapter(
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


def build_tool_registry_loaders_from_settings_artifacts(
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


def build_tool_registry_loader_factories_from_settings_artifacts(
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


def build_tool_registry_loader_factories_from_settings(
    *,
    settings: object | None = None,
) -> dict[str, ToolRegistryLoaderFactory]:
    artifacts = build_tool_registry_loader_factories_from_settings_artifacts(
        settings=settings
    )
    return artifacts["loader_factories"]


def build_tool_registry_provider_factories_from_settings_artifacts(
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


def build_tool_registry_provider_factories_from_settings(
    *,
    settings: object | None = None,
) -> dict[str, ToolRegistryProviderFactory]:
    artifacts = build_tool_registry_provider_factories_from_settings_artifacts(
        settings=settings
    )
    return artifacts["provider_factories"]


def build_tool_registry_loader_adapter(
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


def build_tool_registry_loaders_from_settings(
    *,
    settings: object | None = None,
) -> dict[str, ToolRegistryLoader]:
    artifacts = build_tool_registry_loaders_from_settings_artifacts(settings=settings)
    return artifacts["loaders"]


def build_tool_registry_provider_adapter(
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


def build_tool_registry_providers_from_settings(
    *,
    settings: object | None = None,
) -> dict[str, ToolRegistryProvider]:
    artifacts = build_tool_registry_providers_from_settings_artifacts(settings=settings)
    return artifacts["providers"]


def build_tool_registry_providers_from_settings_artifacts(
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


def build_tool_registry_provider_sources_from_settings(
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


def build_tool_registry_provider_sources_from_settings_artifacts(
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


def build_tool_registry_extra_tools_from_settings(
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


def _build_registry_overrides_from_specs(
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


def build_tool_registry_settings_config(
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


def build_tool_registry_overrides_from_settings(
    *,
    settings: object | None = None,
) -> dict[str, ToolRegistration]:
    return build_tool_registry_settings_config(settings=settings).overrides


def get_disabled_tool_names_from_settings(*, settings: object | None = None) -> tuple[str, ...]:
    return build_tool_registry_settings_config(settings=settings).disabled_tool_names


def get_configured_tool_registry_provider(*, settings: object | None = None) -> ToolRegistryProvider:
    artifacts = get_configured_tool_registry_provider_artifacts(settings=settings)
    return artifacts["provider"]


def get_configured_tool_registry_provider_artifacts(
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


def build_tool_registry_diagnostics_summary_model(
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


def build_tool_registry_diagnostics_summary(
    *,
    diagnostics: dict[str, tuple[str, ...]],
) -> dict[str, object]:
    return build_tool_registry_diagnostics_summary_model(
        diagnostics=diagnostics,
    ).to_dict()


def _humanize_tool_registry_diagnostics_target(target: object) -> str:
    normalized = str(target).strip().lower() if target is not None else ""
    if not normalized:
        return "diagnostics"
    return normalized.replace("_", " ")


def build_tool_registry_diagnostics_display_lines(
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


def build_tool_registry_diagnostics_runtime_artifacts_model(
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


def build_tool_registry_diagnostics_runtime_artifacts(
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


def build_tool_registry_diagnostics_audit_event(
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


def build_tool_registry_diagnostics_audit_service_action(
    *,
    audit_event: dict[str, object],
) -> dict[str, object]:
    return build_tool_registry_diagnostics_audit_service_action_model(
        audit_event=audit_event,
    ).to_dict()


def build_tool_registry_diagnostics_audit_service_action_model(
    *,
    audit_event: dict[str, object],
) -> ConfiguredToolRegistryProviderRuntimeServiceActionModel:
    return ConfiguredToolRegistryProviderRuntimeServiceActionModel(
        kind="record_audit_event",
        kwargs=audit_event,
    )


def build_tool_registry_diagnostics_trace_service_action(
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


def build_tool_registry_diagnostics_trace_service_action_model(
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


def build_configured_tool_registry_provider_runtime_service_actions(
    *,
    runtime_artifacts: dict[str, object],
) -> list[dict[str, object]]:
    return build_configured_tool_registry_provider_runtime_service_actions_model(
        runtime_artifacts=runtime_artifacts,
    ).to_dict()


def build_configured_tool_registry_provider_runtime_service_actions_model(
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


def build_configured_tool_registry_provider_runtime_service_actions_outputs_from_models(
    *,
    service_actions: ConfiguredToolRegistryProviderRuntimeServiceActionsModel,
) -> tuple[
    ConfiguredToolRegistryProviderRuntimeServiceActionsModel,
    list[dict[str, object]],
]:
    return service_actions, service_actions.to_dict()


def build_configured_tool_registry_provider_runtime_service_actions_outputs_from_runtime_artifacts_model(
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


def build_configured_tool_registry_provider_runtime_service_actions_outputs_from_dicts(
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


def build_configured_tool_registry_provider_runtime_service_actions_outputs(
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


def build_configured_tool_registry_provider_runtime_service_actions_model_from_runtime_artifacts_model(
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


def build_configured_tool_registry_provider_runtime_service_action_model_from_dict(
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


def build_configured_tool_registry_provider_runtime_service_actions_model_from_dicts(
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


def build_configured_tool_registry_provider_runtime_artifacts_model_from_dict(
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


def build_configured_tool_registry_provider_service_execution_model_from_dict(
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


def execute_configured_tool_registry_provider_runtime_service_actions(
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


def build_configured_tool_registry_provider_runtime_service_actions_result_model(
    *,
    trace_write_count: int,
    audit_event_count: int,
) -> ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel:
    return ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel(
        trace_write_count=int(trace_write_count),
        audit_event_count=int(audit_event_count),
    )


def build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_models(
    *,
    execution_result: ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel,
) -> tuple[
    ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel,
    dict[str, object],
]:
    return execution_result, execution_result.to_dict()


def build_configured_tool_registry_provider_runtime_service_actions_result_outputs_from_dict(
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


def build_configured_tool_registry_provider_runtime_service_actions_result_model_from_dict(
    *,
    execution_result: dict[str, object],
) -> ConfiguredToolRegistryProviderRuntimeServiceActionsResultModel:
    return build_configured_tool_registry_provider_runtime_service_actions_result_model(
        trace_write_count=int(execution_result.get("trace_write_count", 0)),
        audit_event_count=int(execution_result.get("audit_event_count", 0)),
    )


def execute_configured_tool_registry_provider_runtime_service_actions_result_model(
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


def execute_configured_tool_registry_provider_runtime_service_actions_outputs_from_models(
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


def execute_configured_tool_registry_provider_runtime_service_actions_result_model_from_models(
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


def execute_configured_tool_registry_provider_runtime_service_actions_model(
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


def execute_configured_tool_registry_provider_runtime_service_actions_outputs(
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


def build_configured_tool_registry_provider_service_execution_model(
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


def build_configured_tool_registry_provider_service_execution(
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


def build_configured_tool_registry_provider_service_execution_result_model(
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


def build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model(
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


def build_configured_tool_registry_provider_service_execution_result_model_from_models(
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


def build_configured_tool_registry_provider_service_execution_outputs_from_models(
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


def build_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
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


def execute_configured_tool_registry_provider_service_execution_outputs_from_models(
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


def build_configured_tool_registry_provider_service_execution_outputs(
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


def execute_configured_tool_registry_provider_service_execution(
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


def execute_configured_tool_registry_provider_service_execution_outputs_from_service_execution_model(
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


def execute_configured_tool_registry_provider_service_execution_outputs(
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


def execute_configured_tool_registry_provider_service_execution_model(
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


def build_configured_tool_registry_provider_preflight_summary_model(
    *,
    preflight_result: dict[str, object],
) -> ConfiguredToolRegistryProviderPreflightSummaryModel:
    return build_configured_tool_registry_provider_preflight_summary_model_from_dict(
        preflight_result=preflight_result,
    )


def build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
    *,
    preflight_result: dict[str, object],
) -> ConfiguredToolRegistryProviderServiceExecutionModel:
    return build_configured_tool_registry_provider_service_execution_model_from_dict(
        service_execution=build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict(
            preflight_result=preflight_result,
        )
    )


def build_configured_tool_registry_provider_preflight_service_execution_payload_from_dict(
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


def _merge_configured_tool_registry_provider_preflight_service_execution_payload(
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


def build_configured_tool_registry_provider_preflight_service_execution_result_model_from_dict(
    *,
    preflight_result: dict[str, object],
) -> ConfiguredToolRegistryProviderServiceExecutionResultModel:
    return build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model(
        service_execution=build_configured_tool_registry_provider_preflight_service_execution_model_from_dict(
            preflight_result=preflight_result,
        ),
        preflight_result=preflight_result,
    )


def build_configured_tool_registry_provider_preflight_service_execution_result_model_from_service_execution_model(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    preflight_result: dict[str, object],
) -> ConfiguredToolRegistryProviderServiceExecutionResultModel:
    return build_configured_tool_registry_provider_service_execution_result_model_from_service_execution_model(
        service_execution=service_execution,
        execution_result=preflight_result,
    )


def build_configured_tool_registry_provider_preflight_execution_models_from_dict(
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


def build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_payload(
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


def build_configured_tool_registry_provider_preflight_execution_models_from_service_execution_model(
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


def build_configured_tool_registry_provider_preflight_models_from_service_execution_payload(
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


def build_configured_tool_registry_provider_preflight_models_from_service_execution_model(
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


def build_configured_tool_registry_provider_preflight_models_from_dict(
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

def build_configured_tool_registry_provider_preflight_models_from_models(
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


def build_configured_tool_registry_provider_preflight_summary_model_from_dict(
    *,
    preflight_result: dict[str, object],
) -> ConfiguredToolRegistryProviderPreflightSummaryModel:
    return build_configured_tool_registry_provider_preflight_summary_model_from_result_model(
        preflight_result=build_configured_tool_registry_provider_preflight_result_model_from_dict(
            preflight_result=preflight_result,
        ),
    )


def build_configured_tool_registry_provider_preflight_summary_model_from_result_model(
    *,
    preflight_result: ConfiguredToolRegistryProviderPreflightResultModel,
) -> ConfiguredToolRegistryProviderPreflightSummaryModel:
    return preflight_result.summary


def build_configured_tool_registry_provider_preflight_summary_model_from_models(
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


def build_configured_tool_registry_provider_preflight_summary_model_from_parts(
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


def build_configured_tool_registry_provider_preflight_summary(
    *,
    preflight_result: dict[str, object],
) -> dict[str, object]:
    return build_configured_tool_registry_provider_preflight_summary_model(
        preflight_result=preflight_result,
    ).to_dict()


def build_configured_tool_registry_provider_preflight_outputs_from_resolved_models(
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


def build_configured_tool_registry_provider_preflight_outputs_from_models(
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


def build_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
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


def build_configured_tool_registry_provider_preflight_outputs(
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


def build_configured_tool_registry_provider_preflight_outputs_from_service_execution_payload(
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


def build_configured_tool_registry_provider_preflight_outputs_from_dict(
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


def build_configured_tool_registry_provider_preflight_models(
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


def build_configured_tool_registry_provider_preflight_dicts(
    *,
    preflight_result: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    result_model = build_configured_tool_registry_provider_preflight_result_model_from_dict(
        preflight_result=preflight_result,
    )
    return result_model.summary.to_dict(), result_model.to_dict()


def build_configured_tool_registry_provider_preflight_result_model(
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


def build_configured_tool_registry_provider_preflight_result_model_from_service_execution_model(
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


def build_configured_tool_registry_provider_preflight_result_model_from_models(
    *,
    service_execution: ConfiguredToolRegistryProviderServiceExecutionModel,
    execution_result: ConfiguredToolRegistryProviderServiceExecutionResultModel,
) -> ConfiguredToolRegistryProviderPreflightResultModel:
    _, _, _, result_model, _, _ = build_configured_tool_registry_provider_preflight_outputs_from_models(
        service_execution=service_execution,
        execution_result=execution_result,
    )
    return result_model


def build_configured_tool_registry_provider_preflight_result_model_from_dict(
    *,
    preflight_result: dict[str, object],
) -> ConfiguredToolRegistryProviderPreflightResultModel:
    _, _, _, result_model, _, _ = build_configured_tool_registry_provider_preflight_outputs_from_dict(
        preflight_result=preflight_result,
    )
    return result_model


def build_configured_tool_registry_provider_preflight_result(
    *,
    service_execution: dict[str, object],
    execution_result: dict[str, object],
) -> dict[str, object]:
    return build_configured_tool_registry_provider_preflight_result_model(
        service_execution=service_execution,
        execution_result=execution_result,
    ).to_dict()


def execute_configured_tool_registry_provider_preflight_models_from_service_execution_model(
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


def execute_configured_tool_registry_provider_preflight_outputs_from_service_execution_model(
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


def execute_configured_tool_registry_provider_preflight_outputs(
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


def execute_configured_tool_registry_provider_preflight_summary_model(
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


def execute_configured_tool_registry_provider_preflight_summary(
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


def execute_configured_tool_registry_provider_preflight_dicts(
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


def execute_configured_tool_registry_provider_preflight_models(
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


def execute_configured_tool_registry_provider_preflight(
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


def execute_configured_tool_registry_provider_preflight_model(
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


def build_configured_tool_registry_provider_runtime_artifacts_model(
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


def build_configured_tool_registry_provider_runtime_artifacts(
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
