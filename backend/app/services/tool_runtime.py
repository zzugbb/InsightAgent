from __future__ import annotations

import json
import math
import re
import gzip
import zlib
import codecs
from ast import Add, BinOp, Div, Expression, Mod, Mult, Pow, Sub, UAdd, USub, UnaryOp, parse
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


@dataclass(frozen=True)
class ToolRegistryDiagnosticsRuntimeArtifactsModel:
    summary: ToolRegistryDiagnosticsSummaryModel
    trace_step: dict[str, object] | None
    trace_event: dict[str, object] | None
    audit_detail: dict[str, object] | None

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary.to_dict(),
            "trace_step": sanitize_tool_registry_diagnostics_artifact_payload(
                self.trace_step
            ),
            "trace_event": sanitize_tool_registry_diagnostics_artifact_payload(
                self.trace_event
            ),
            "audit_detail": sanitize_tool_registry_diagnostics_artifact_payload(
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
            "audit_event": sanitize_tool_registry_diagnostics_artifact_payload(
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
            payload["trace_step"] = sanitize_tool_registry_diagnostics_artifact_payload(
                self.trace_step
            )
        if self.trace_event is not None:
            payload["trace_event"] = sanitize_tool_registry_diagnostics_artifact_payload(
                self.trace_event
            )
        if self.persist_force:
            payload["persist_force"] = self.persist_force
        if self.kwargs is not None:
            payload["kwargs"] = sanitize_tool_registry_diagnostics_artifact_payload(
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
_HTTP_JSON_ALLOWED_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
_TOOL_TIMEOUT_MAX_MS = 2_147_483_647
_HTTP_JSON_ERROR_BODY_PREVIEW_MAX_LENGTH = 240
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
_TOOL_REGISTRY_DIAGNOSTIC_FIELD_PATH_RE = re.compile(
    r"\b(?:headers|query_params|json_body|result_fields)"
    r"(?:\.[A-Za-z0-9_\-\[\]]+)+"
)
_HTTP_JSON_URL_CONTROL_OR_SPACE_RE = re.compile(r"[\x00-\x20\x7f]")
_HTTP_JSON_QUERY_PARAM_NAME_UNSAFE_RE = re.compile(r"[\x00-\x20\x7f=&?#]")
_HTTP_JSON_HEADER_NAME_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_HTTP_JSON_HEADER_VALUE_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HTTP_JSON_SUPPORTED_CONTENT_ENCODINGS = ("identity", "gzip", "deflate")
_HTTP_JSON_RESPONSE_DIAGNOSTIC_HEADER_HINTS = (
    ("Retry-After", "retry-after"),
    ("X-RateLimit-Reset", "rate-limit-reset"),
    ("X-Request-ID", "request id"),
    ("Request-ID", "request id"),
    ("X-Correlation-ID", "correlation id"),
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
    name = str(tool_spec.get("name", "")).strip()
    tool_input = tool_spec.get("input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    return ToolInvocation(name=name, tool_input=tool_input)


def _normalize_planned_tool_names(raw_value: object) -> list[str]:
    if not isinstance(raw_value, (list, tuple)):
        return []
    normalized_names: list[str] = []
    seen_names: set[str] = set()
    for raw_name in raw_value:
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
    if isinstance(planned_tool_labels, (list, tuple)):
        for idx, raw_label in enumerate(planned_tool_labels):
            if idx >= len(planned_tool_names):
                break
            label = str(raw_label).strip()
            if label:
                label_by_name[planned_tool_names[idx]] = label
    if isinstance(planned_tool_kinds, (list, tuple)):
        for idx, raw_kind in enumerate(planned_tool_kinds):
            if idx >= len(planned_tool_names):
                break
            kind = _normalize_tool_semantic_kind(str(raw_kind).strip())
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
    if "planned_tool_names" in tool_input and isinstance(
        tool_input.get("planned_tool_names"), (list, tuple)
    ):
        planned_tool_labels = tool_input.get("planned_tool_labels")
        planned_tool_kinds = tool_input.get("planned_tool_kinds")
        steps = _build_task_plan_steps(
            planned_tool_names=planned_tool_names,
            planned_tool_labels=(
                planned_tool_labels
                if isinstance(planned_tool_labels, (list, tuple))
                else None
            ),
            planned_tool_kinds=(
                planned_tool_kinds
                if isinstance(planned_tool_kinds, (list, tuple))
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
    if not isinstance(raw_sources, str) or not raw_sources.strip():
        return {}
    try:
        source_specs = json.loads(raw_sources)
    except json.JSONDecodeError:
        return {}
    if not isinstance(source_specs, dict):
        return {}

    normalized_source_specs: dict[str, dict[str, object]] = {}
    for source_name, spec in source_specs.items():
        if not isinstance(source_name, str) or not isinstance(spec, dict):
            continue
        normalized_source_name = get_tool_registry_provider_source_name_from_settings(
            settings=SimpleNamespace(
                tool_registry_provider_source=source_name,
            )
        )
        if normalized_source_name == "default":
            continue
        normalized_source_specs[normalized_source_name] = spec
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
    if not isinstance(extra_tool_specs, dict):
        return {}
    extra_tools_settings = _clone_tool_execution_settings(
        settings=settings or SimpleNamespace(),
        tool_registry_extra_tools_json=json.dumps(
            extra_tool_specs,
            ensure_ascii=False,
        ),
        **(
            {"tool_registry_provider_source": provider_source_name}
            if provider_source_name
            else {}
        ),
    )
    return build_tool_registry_extra_tools_from_settings(settings=extra_tools_settings)


def _normalize_result_preview_keys(raw_value: object) -> tuple[str, ...]:
    if not isinstance(raw_value, (list, tuple)):
        return ()
    normalized_keys: list[str] = []
    seen_keys: set[str] = set()
    for raw_key in raw_value:
        key = str(raw_key).strip()
        if not key or key in seen_keys:
            continue
        normalized_keys.append(key)
        seen_keys.add(key)
    return tuple(normalized_keys)


def _normalize_result_output_keys(raw_value: object) -> tuple[str, ...]:
    return _normalize_result_preview_keys(raw_value)


def _is_sensitive_result_key(raw_value: object) -> bool:
    return _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(str(raw_value).strip()) is not None


def _normalize_safe_explicit_result_keys(
    raw_value: object,
    *,
    fallback_keys: tuple[str, ...],
) -> tuple[str, ...]:
    if not isinstance(raw_value, (list, tuple)):
        return fallback_keys
    normalized_keys = _normalize_result_preview_keys(raw_value)
    if not normalized_keys:
        return fallback_keys
    return tuple(key for key in normalized_keys if not _is_sensitive_result_key(key))


def _normalize_runtime_semantic_kind(raw_value: object) -> str | None:
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    return normalized or None


def _normalize_tool_execution_kind(raw_value: object) -> str | None:
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip().lower()
    return normalized or None


def _build_tool_execution_runtime_template_context(
    *,
    settings: object | None = None,
) -> dict[str, object]:
    if settings is None:
        return {}
    context: dict[str, object] = {}
    for attr_name, context_key in (
        ("mode", "settings_mode"),
        ("provider", "settings_provider"),
        ("model", "settings_model"),
        ("base_url", "settings_base_url"),
        ("api_key", "settings_api_key"),
        ("tool_registry_provider_source", "tool_registry_provider_source"),
        ("tool_registry_profile", "tool_registry_profile"),
    ):
        raw_value = getattr(settings, attr_name, None)
        if not isinstance(raw_value, str):
            continue
        normalized = raw_value.strip()
        if not normalized:
            continue
        context[context_key] = normalized
    return context


_SUPPORTED_TOOL_EXECUTION_RUNTIME_TEMPLATE_KEYS = frozenset(
    {
        "settings_mode",
        "settings_provider",
        "settings_model",
        "settings_base_url",
        "settings_api_key",
        "tool_registry_provider_source",
        "tool_registry_profile",
    }
)
_TOOL_EXECUTION_RUNTIME_TEMPLATE_RESERVED_PREFIXES = ("settings_", "tool_registry_")


_TOOL_EXECUTION_TEMPLATE_MISSING = object()


def _stringify_tool_execution_template_interpolation_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _clone_tool_execution_settings(
    *,
    settings: object,
    **updates: object,
) -> object:
    if isinstance(settings, dict):
        merged_values = dict(settings)
    elif hasattr(settings, "model_dump"):
        merged_values = dict(getattr(settings, "model_dump")())
    else:
        merged_values = dict(vars(settings))
    merged_values.update(updates)
    return SimpleNamespace(**merged_values)


def _render_tool_execution_template(
    value: object,
    *,
    context: dict[str, object],
) -> object:
    if isinstance(value, str):
        raw = value.strip()
        if "${" in value:
            missing_placeholder = False

            def replace_placeholder(match: re.Match[str]) -> str:
                nonlocal missing_placeholder
                lookup_key = match.group(1).strip()
                if not lookup_key or lookup_key not in context:
                    missing_placeholder = True
                    return ""
                return _stringify_tool_execution_template_interpolation_value(
                    context[lookup_key]
                )

            rendered_value = re.sub(r"\$\{([^{}]+)\}", replace_placeholder, value)
            if missing_placeholder:
                return _TOOL_EXECUTION_TEMPLATE_MISSING
            return rendered_value
        if raw.startswith("$") and len(raw) > 1:
            lookup_key = raw[1:]
            return (
                context[lookup_key]
                if lookup_key in context
                else _TOOL_EXECUTION_TEMPLATE_MISSING
            )
        return value
    if isinstance(value, dict):
        rendered_mapping: dict[str, object] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str) or not raw_key.strip():
                continue
            rendered_value = _render_tool_execution_template(
                raw_value,
                context=context,
            )
            if rendered_value is _TOOL_EXECUTION_TEMPLATE_MISSING or rendered_value is None:
                continue
            rendered_mapping[raw_key] = rendered_value
        return rendered_mapping
    if isinstance(value, (list, tuple)):
        rendered_items: list[object] = []
        for item in value:
            rendered_item = _render_tool_execution_template(item, context=context)
            if rendered_item is _TOOL_EXECUTION_TEMPLATE_MISSING:
                continue
            rendered_items.append(rendered_item)
        return rendered_items
    return value


def _iter_missing_tool_execution_template_variables(
    value: object,
    *,
    context: dict[str, object],
    path: str,
) -> tuple[tuple[str, str], ...]:
    if isinstance(value, str):
        missing: list[tuple[str, str]] = []
        raw = value.strip()
        if raw.startswith("$") and len(raw) > 1 and not raw.startswith("${"):
            lookup_key = raw[1:]
            if lookup_key not in context:
                missing.append((path, lookup_key))
        for match in re.finditer(r"\$\{([^{}]+)\}", value):
            lookup_key = match.group(1).strip()
            if lookup_key and lookup_key not in context:
                missing.append((path, lookup_key))
        return tuple(missing)
    if isinstance(value, dict):
        missing: list[tuple[str, str]] = []
        for raw_key, raw_item in value.items():
            if not isinstance(raw_key, str) or not raw_key.strip():
                continue
            child_path = f"{path}.{raw_key.strip()}" if path else raw_key.strip()
            missing.extend(
                _iter_missing_tool_execution_template_variables(
                    raw_item,
                    context=context,
                    path=child_path,
                )
            )
        return tuple(missing)
    if isinstance(value, (list, tuple)):
        missing: list[tuple[str, str]] = []
        for index, item in enumerate(value):
            missing.extend(
                _iter_missing_tool_execution_template_variables(
                    item,
                    context=context,
                    path=f"{path}[{index}]",
                )
            )
        return tuple(missing)
    return ()


def _render_required_tool_execution_template(
    value: object,
    *,
    context: dict[str, object],
    path: str,
) -> object:
    missing_references = _iter_missing_tool_execution_template_variables(
        value,
        context=context,
        path=path,
    )
    if missing_references:
        formatted_references = tuple(
            dict.fromkeys(
                f"{_format_safe_tool_execution_template_variable_name(variable_name)} "
                f"in {_format_safe_tool_execution_diagnostic_path(reference_path)}"
                for reference_path, variable_name in missing_references
            )
        )
        qualifier = "variable" if len(formatted_references) == 1 else "variables"
        joined_references = "; ".join(formatted_references)
        raise MockToolExecutionError(
            "HTTP JSON tool request template references missing runtime template "
            f"{qualifier} {joined_references}.",
            fatal=True,
        )
    return _render_tool_execution_template(value, context=context)


def _render_tool_execution_template_for_static_analysis(
    value: object,
    *,
    context: dict[str, object] | None,
    path: str,
) -> object:
    analysis_context = context or {}
    missing_references = _iter_missing_tool_execution_template_variables(
        value,
        context=analysis_context,
        path=path,
    )
    if missing_references:
        return _TOOL_EXECUTION_TEMPLATE_MISSING
    return _render_tool_execution_template(value, context=analysis_context)


def _resolve_tool_execution_template_value_for_static_validation(
    value: object,
    *,
    context: dict[str, object] | None,
    path: str,
) -> object:
    if not _iter_tool_execution_template_variable_references(value, path=path):
        return value
    rendered_value = _render_tool_execution_template_for_static_analysis(
        value,
        context=context,
        path=path,
    )
    if rendered_value is _TOOL_EXECUTION_TEMPLATE_MISSING:
        return value
    return rendered_value


def _iter_tool_execution_template_variable_references(
    value: object,
    *,
    path: str,
) -> tuple[tuple[str, str], ...]:
    if isinstance(value, str):
        references: list[tuple[str, str]] = []
        raw = value.strip()
        if raw.startswith("$") and len(raw) > 1 and not raw.startswith("${"):
            references.append((path, raw[1:]))
        references.extend(
            (path, match.group(1).strip())
            for match in re.finditer(r"\$\{([^{}]+)\}", value)
            if match.group(1).strip()
        )
        return tuple(references)
    if isinstance(value, dict):
        references: list[tuple[str, str]] = []
        for raw_key, raw_item in value.items():
            if not isinstance(raw_key, str) or not raw_key.strip():
                continue
            child_path = f"{path}.{raw_key.strip()}" if path else raw_key.strip()
            references.extend(
                _iter_tool_execution_template_variable_references(
                    raw_item,
                    path=child_path,
                )
            )
        return tuple(references)
    if isinstance(value, (list, tuple)):
        references: list[tuple[str, str]] = []
        for index, item in enumerate(value):
            references.extend(
                _iter_tool_execution_template_variable_references(
                    item,
                    path=f"{path}[{index}]",
                )
            )
        return tuple(references)
    return ()


def _collect_tool_execution_runtime_template_validation_errors(
    *,
    execution_spec: object,
) -> tuple[str, ...]:
    if not isinstance(execution_spec, dict):
        return ()
    execution_kind = _normalize_named_tool_registry_component_name(
        execution_spec.get("kind")
    )
    if execution_kind != "http_json":
        return ()
    references: list[tuple[str, str]] = []
    for field_name in ("url", "headers", "query_params", "json_body"):
        if field_name not in execution_spec:
            continue
        references.extend(
            _iter_tool_execution_template_variable_references(
                execution_spec.get(field_name),
                path=field_name,
            )
        )
    messages: list[str] = []
    for path, variable_name in references:
        if not variable_name.startswith(_TOOL_EXECUTION_RUNTIME_TEMPLATE_RESERVED_PREFIXES):
            continue
        if variable_name in _SUPPORTED_TOOL_EXECUTION_RUNTIME_TEMPLATE_KEYS:
            continue
        messages.append(
            "http_json execution references unsupported runtime template "
            "variable "
            f"{_format_safe_tool_execution_template_variable_name(variable_name)} "
            f"in {_format_safe_tool_execution_diagnostic_path(path)}"
        )
    return tuple(dict.fromkeys(messages))


def _normalize_tool_execution_http_method(raw_value: object) -> str:
    if not isinstance(raw_value, str):
        return "GET"
    normalized = raw_value.strip().upper()
    if normalized in _HTTP_JSON_ALLOWED_METHODS:
        return normalized
    return "GET"


def _describe_tool_execution_http_method_validation_error(
    raw_value: object,
) -> str | None:
    if not isinstance(raw_value, str):
        return (
            "http_json execution method must be one of "
            f"{', '.join(_HTTP_JSON_ALLOWED_METHODS)}"
        )
    normalized = raw_value.strip().upper()
    if normalized in _HTTP_JSON_ALLOWED_METHODS:
        return None
    return (
        "http_json execution method must be one of "
        f"{', '.join(_HTTP_JSON_ALLOWED_METHODS)}"
    )


def _is_supported_tool_timeout_ms(raw_value: object) -> bool:
    if isinstance(raw_value, bool):
        return False
    if isinstance(raw_value, int):
        return 0 < raw_value <= _TOOL_TIMEOUT_MAX_MS
    if isinstance(raw_value, float):
        return (
            math.isfinite(raw_value)
            and raw_value.is_integer()
            and 1 <= raw_value <= _TOOL_TIMEOUT_MAX_MS
        )
    return False


def _coerce_tool_execution_timeout_ms(
    raw_value: object,
    *,
    default_timeout_ms: int,
) -> int:
    if raw_value is None:
        return default_timeout_ms
    if _is_supported_tool_timeout_ms(raw_value):
        return int(raw_value)
    return default_timeout_ms


def _describe_tool_execution_timeout_ms_validation_error(
    raw_value: object,
) -> str | None:
    if _is_supported_tool_timeout_ms(raw_value):
        return None
    return "http_json execution timeout_ms must be a positive number of milliseconds"


def _coerce_tool_default_timeout_ms(
    raw_value: object,
    *,
    fallback_timeout_ms: int,
) -> int:
    if _is_supported_tool_timeout_ms(raw_value):
        coerced_timeout_ms = int(raw_value)
        return coerced_timeout_ms
    if isinstance(raw_value, str) and raw_value.strip():
        try:
            coerced_timeout_ms = int(raw_value.strip())
        except ValueError:
            return fallback_timeout_ms
        return (
            coerced_timeout_ms
            if _is_supported_tool_timeout_ms(coerced_timeout_ms)
            else fallback_timeout_ms
        )
    return fallback_timeout_ms


def _describe_tool_default_timeout_ms_validation_error(
    raw_value: object,
) -> str | None:
    if _is_supported_tool_timeout_ms(raw_value):
        return None
    if isinstance(raw_value, str) and raw_value.strip():
        try:
            if _is_supported_tool_timeout_ms(int(raw_value.strip())):
                return None
        except ValueError:
            pass
    return "tool default_timeout_ms must be a positive number of milliseconds"


def _normalize_tool_execution_http_headers(raw_value: object) -> dict[str, str]:
    if not isinstance(raw_value, dict):
        return {}
    headers: dict[str, str] = {}
    for raw_key, raw_item in raw_value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        if raw_item is None:
            continue
        headers[raw_key] = str(raw_item)
    return headers


def _normalize_tool_execution_http_query_params(
    raw_value: object,
) -> dict[str, object]:
    if not isinstance(raw_value, dict):
        return {}
    query_params: dict[str, object] = {}
    for raw_key, raw_item in raw_value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        if raw_item is None:
            continue
        if isinstance(raw_item, tuple):
            query_params[raw_key] = list(raw_item)
            continue
        query_params[raw_key] = raw_item
    return query_params


def _is_supported_tool_execution_http_url(raw_value: object) -> bool:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return False
    if _HTTP_JSON_URL_CONTROL_OR_SPACE_RE.search(raw_value):
        return False
    parsed_url = urlparse(raw_value.strip())
    try:
        parsed_url.port
    except ValueError:
        return False
    query_error = _describe_tool_execution_http_url_query_validation_error(
        parsed_url.query
    )
    path_error = _describe_tool_execution_http_url_path_validation_error(
        parsed_url.path
    )
    return (
        parsed_url.scheme in {"http", "https"}
        and bool(parsed_url.netloc)
        and parsed_url.username is None
        and parsed_url.password is None
        and not parsed_url.fragment
        and query_error is None
        and path_error is None
    )


def _describe_tool_execution_http_url_path_validation_error(
    raw_value: object,
) -> str | None:
    if not isinstance(raw_value, str) or not raw_value:
        return None
    decoded_path = unquote(raw_value)
    if _HTTP_JSON_HEADER_VALUE_CONTROL_RE.search(decoded_path):
        return "http_json execution url path must not contain encoded control characters"
    if any(segment in {".", ".."} for segment in decoded_path.split("/")):
        return "http_json execution url path must not include dot segments"
    return None


def _describe_tool_execution_http_url_query_validation_error(
    raw_value: object,
) -> str | None:
    if not isinstance(raw_value, str) or not raw_value:
        return None
    seen_query_param_names: set[str] = set()
    for query_param_name, _query_param_value in parse_qsl(
        raw_value,
        keep_blank_values=True,
    ):
        if not _is_supported_tool_execution_http_query_param_name(query_param_name):
            return (
                "http_json execution url query parameters must use safe query "
                "parameter names"
            )
        if _http_header_value_contains_control_character(_query_param_value):
            return (
                "http_json execution url query parameter values must not contain "
                "control characters"
            )
        if query_param_name in seen_query_param_names:
            return (
                "http_json execution url query must not define duplicate parameter "
                "names"
            )
        seen_query_param_names.add(query_param_name)
    return None


def _iter_tool_execution_http_url_query_param_names(
    raw_url: object,
) -> tuple[str, ...]:
    if not isinstance(raw_url, str) or not raw_url.strip():
        return ()
    parsed_url = urlparse(raw_url.strip())
    if not parsed_url.query:
        return ()
    return tuple(
        query_param_name
        for query_param_name, _query_param_value in parse_qsl(
            parsed_url.query,
            keep_blank_values=True,
        )
    )


def _describe_tool_execution_http_duplicate_query_param_validation_error(
    *,
    url: object,
    query_params: object,
) -> str | None:
    if not isinstance(query_params, dict) or not query_params:
        return None
    url_query_param_names = {
        query_param_name
        for query_param_name in _iter_tool_execution_http_url_query_param_names(url)
        if _is_supported_tool_execution_http_query_param_name(query_param_name)
    }
    if not url_query_param_names:
        return None
    for raw_key in query_params:
        if (
            isinstance(raw_key, str)
            and _is_supported_tool_execution_http_query_param_name(raw_key)
            and raw_key in url_query_param_names
        ):
            return (
                "http_json execution url query and query_params must not define "
                "duplicate parameter names"
            )
    return None


def _describe_tool_execution_http_url_validation_error(
    raw_value: object,
) -> str | None:
    if _is_supported_tool_execution_http_url(raw_value):
        return None
    if isinstance(raw_value, str) and raw_value.strip():
        if _HTTP_JSON_URL_CONTROL_OR_SPACE_RE.search(raw_value):
            return "http_json execution url must not contain control characters or spaces"
        parsed_url = urlparse(raw_value.strip())
        if (
            parsed_url.scheme in {"http", "https"}
            and parsed_url.netloc
            and (parsed_url.username is not None or parsed_url.password is not None)
        ):
            return "http_json execution url must not include credentials"
        try:
            parsed_url.port
        except ValueError:
            return (
                "http_json execution url must include a valid port when port is provided"
            )
        if (
            parsed_url.scheme in {"http", "https"}
            and parsed_url.netloc
            and parsed_url.fragment
        ):
            return "http_json execution url must not include fragments"
        if parsed_url.scheme in {"http", "https"} and parsed_url.netloc:
            path_error = _describe_tool_execution_http_url_path_validation_error(
                parsed_url.path
            )
            if path_error:
                return path_error
            query_error = _describe_tool_execution_http_url_query_validation_error(
                parsed_url.query
            )
            if query_error:
                return query_error
    return "http_json execution url must be an absolute http(s) URL"


def _format_safe_tool_execution_http_url_origin(parsed_url: object) -> str | None:
    scheme = getattr(parsed_url, "scheme", "")
    hostname = getattr(parsed_url, "hostname", None)
    if scheme not in {"http", "https"} or not isinstance(hostname, str) or not hostname:
        return None
    try:
        port = getattr(parsed_url, "port", None)
    except ValueError:
        return None
    if isinstance(port, int):
        return f"{scheme}://{hostname}:{port}"
    return f"{scheme}://{hostname}"


def _format_safe_tool_execution_http_url_path(parsed_url: object) -> str | None:
    path = getattr(parsed_url, "path", "")
    if not isinstance(path, str) or not path:
        return None
    path = unquote(path)
    safe_segments: list[str] = []
    redact_next_segment = False
    for segment in path.split("/"):
        if not segment:
            safe_segments.append(segment)
            continue
        if redact_next_segment:
            safe_segments.append("[redacted]")
            redact_next_segment = False
            continue
        if _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.fullmatch(segment):
            safe_segments.append("[redacted]")
            redact_next_segment = True
            continue
        redacted_segment = _redact_http_json_diagnostic_text(segment)
        safe_segments.append(redacted_segment)
    return "/".join(safe_segments)


def _format_safe_tool_execution_summary_field_name(raw_value: object) -> str:
    normalized = str(raw_value).strip()
    if not normalized:
        return ""
    if _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(normalized):
        return "[redacted]"
    return _HTTP_JSON_ERROR_BODY_SENSITIVE_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}[redacted]",
        normalized,
    )


def _format_safe_tool_execution_diagnostic_path(raw_value: object) -> str:
    raw_path = str(raw_value).strip()
    if not raw_path:
        return ""
    path_segments = raw_path.split(".")
    root_segment = path_segments[0]
    safe_segments: list[str] = []
    for index, segment in enumerate(path_segments):
        if not segment:
            continue
        if index == 0:
            safe_segments.append(segment)
            continue
        bracket_index = segment.find("[")
        if bracket_index == -1:
            field_name = segment
            suffix = ""
        else:
            field_name = segment[:bracket_index]
            suffix = segment[bracket_index:]
        if not field_name:
            safe_segments.append(segment)
            continue
        if (
            not (root_segment == "headers" and field_name.lower() == "authorization")
            and _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(field_name)
        ):
            safe_segments.append(f"[redacted]{suffix}")
            continue
        safe_segments.append(segment)
    return ".".join(safe_segments)


def _format_safe_tool_execution_template_variable_name(raw_value: object) -> str:
    normalized = str(raw_value).strip()
    if not normalized:
        return ""
    return _format_safe_tool_execution_summary_field_name(normalized)


def _format_safe_tool_execution_kind(raw_value: object) -> str:
    normalized = str(raw_value).strip()
    if not normalized:
        return ""
    return _format_safe_tool_execution_summary_field_name(normalized)


def _raise_http_json_rendered_url_validation_error(raw_value: object) -> None:
    validation_error = _describe_tool_execution_http_url_validation_error(raw_value)
    if validation_error is None:
        return
    message = validation_error.removeprefix("http_json execution ")
    raise MockToolExecutionError(
        f"HTTP JSON tool {message}.",
        fatal=True,
    )


def _raise_http_json_rendered_duplicate_query_param_validation_error(
    *,
    url: object,
    query_params: object,
) -> None:
    validation_error = (
        _describe_tool_execution_http_duplicate_query_param_validation_error(
            url=url,
            query_params=query_params,
        )
    )
    if validation_error is None:
        return
    message = validation_error.removeprefix("http_json execution ")
    raise MockToolExecutionError(
        f"HTTP JSON tool {message}.",
        fatal=True,
    )


def _is_supported_tool_execution_http_scalar_value(raw_value: object) -> bool:
    if raw_value is None:
        return False
    if isinstance(raw_value, bool):
        return True
    if isinstance(raw_value, int):
        return True
    if isinstance(raw_value, float):
        return math.isfinite(raw_value)
    return isinstance(raw_value, str)


def _is_supported_tool_execution_http_query_value(raw_value: object) -> bool:
    if _is_supported_tool_execution_http_scalar_value(raw_value):
        return True
    if isinstance(raw_value, (list, tuple)):
        return all(
            _is_supported_tool_execution_http_scalar_value(item)
            for item in raw_value
        )
    return False


def _is_supported_tool_execution_http_query_param_name(raw_value: object) -> bool:
    if not isinstance(raw_value, str) or raw_value != raw_value.strip():
        return False
    return bool(raw_value) and not _HTTP_JSON_QUERY_PARAM_NAME_UNSAFE_RE.search(
        raw_value
    )


def _is_supported_tool_execution_http_header_name(raw_value: object) -> bool:
    if not isinstance(raw_value, str) or raw_value != raw_value.strip():
        return False
    return bool(_HTTP_JSON_HEADER_NAME_RE.fullmatch(raw_value))


def _http_header_value_contains_line_break(raw_value: object) -> bool:
    return isinstance(raw_value, str) and ("\r" in raw_value or "\n" in raw_value)


def _http_header_value_contains_control_character(raw_value: object) -> bool:
    return isinstance(raw_value, str) and bool(
        _HTTP_JSON_HEADER_VALUE_CONTROL_RE.search(raw_value)
    )


def _http_headers_contain_duplicate_names(headers: object) -> bool:
    if not isinstance(headers, dict):
        return False
    seen_header_names: set[str] = set()
    for raw_key in headers:
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        normalized_key = raw_key.strip().lower()
        if normalized_key in seen_header_names:
            return True
        seen_header_names.add(normalized_key)
    return False


def _get_tool_execution_http_header_value(
    headers: object,
    header_name: str,
) -> object | None:
    if not isinstance(headers, dict):
        return None
    normalized_header_name = header_name.strip().lower()
    for raw_key, raw_value in headers.items():
        if (
            isinstance(raw_key, str)
            and raw_key.strip().lower() == normalized_header_name
        ):
            return raw_value
    return None


def _is_supported_http_json_media_type(raw_value: object) -> bool:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return False
    media_type = _split_http_json_header_parameters(raw_value)[0].strip().lower()
    return media_type == "application/json" or media_type.endswith("+json")


def _get_http_json_media_type_parameter_values(
    raw_value: object,
    parameter_name: str,
) -> tuple[str, ...]:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return ()
    parameter_values: list[str] = []
    for raw_part in _split_http_json_header_parameters(raw_value)[1:]:
        raw_name, separator, raw_parameter_value = raw_part.partition("=")
        if raw_name.strip().lower() != parameter_name:
            continue
        if separator != "=":
            parameter_values.append("")
            continue
        parameter_value = raw_parameter_value.strip().strip("\"'")
        parameter_values.append(parameter_value if parameter_value else "")
    return tuple(parameter_values)


def _http_json_header_value_has_balanced_quoted_parameters(raw_value: object) -> bool:
    if not isinstance(raw_value, str):
        return True
    quote_char: str | None = None
    escaped = False
    for char in raw_value:
        if escaped:
            escaped = False
            continue
        if quote_char is not None:
            if char == "\\":
                escaped = True
            elif char == quote_char:
                quote_char = None
            continue
        if char in ("'", '"'):
            quote_char = char
    return quote_char is None


def _is_supported_http_json_accept_header(raw_value: object) -> bool:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return False
    for item in _split_http_json_header_values(raw_value):
        raw_parts = _split_http_json_header_parameters(item)
        if not raw_parts:
            continue
        media_type = raw_parts[0].strip().lower()
        json_compatible = (
            media_type in {"application/json", "application/*", "*/*"}
            or media_type.endswith("+json")
        )
        q_values: list[float] = []
        for raw_part in raw_parts[1:]:
            parameter_name, separator, parameter_value = raw_part.partition("=")
            if parameter_name.strip().lower() != "q":
                continue
            if separator != "=":
                q_values.append(0.0)
                continue
            try:
                q_values.append(float(parameter_value.strip().strip("\"'")))
            except ValueError:
                q_values.append(0.0)
        if not q_values:
            q_values = [1.0]
        if any(
            not math.isfinite(q_value) or q_value <= 0 or q_value > 1
            for q_value in q_values
        ):
            if json_compatible:
                return False
            continue
        if json_compatible:
            return True
    return False


def _format_http_json_request_content_type_validation_error(
    raw_value: object,
) -> str:
    safe_content_type = _format_http_json_error_body_preview(raw_value)
    return (
        "http_json execution headers.Content-Type must be application/json or "
        "a +json media type when json_body is defined: "
        f"{safe_content_type}"
    )


def _format_http_json_request_content_type_charset_validation_error(
    raw_value: object,
) -> str:
    safe_content_type = _format_http_json_error_body_preview(raw_value)
    return (
        "http_json execution headers.Content-Type charset must be utf-8 when "
        "json_body is defined: "
        f"{safe_content_type}"
    )


def _format_http_json_request_header_quote_validation_error(
    *,
    header_name: str,
    raw_value: object,
) -> str:
    safe_value = _format_http_json_error_body_preview(raw_value)
    return (
        f"http_json execution headers.{header_name} must use balanced quoted "
        f"parameters: {safe_value}"
    )


def _describe_http_json_request_content_type_validation_errors(
    *,
    headers: object,
) -> tuple[str, ...]:
    raw_content_type = _get_tool_execution_http_header_value(headers, "Content-Type")
    if raw_content_type is None:
        return ()
    if _iter_tool_execution_template_variable_references(
        raw_content_type,
        path="headers.Content-Type",
    ):
        return ()
    if isinstance(
        raw_content_type, str
    ) and not _http_json_header_value_has_balanced_quoted_parameters(raw_content_type):
        return (
            _format_http_json_request_header_quote_validation_error(
                header_name="Content-Type",
                raw_value=raw_content_type,
            ),
        )
    if not (
        isinstance(raw_content_type, str)
        and _is_supported_http_json_media_type(raw_content_type)
    ):
        return (_format_http_json_request_content_type_validation_error(raw_content_type),)
    charset_values = _get_http_json_media_type_parameter_values(
        raw_content_type,
        "charset",
    )
    normalized_charsets = {
        charset.lower().replace("_", "-")
        for charset in charset_values
    }
    if normalized_charsets and not normalized_charsets <= {"utf-8", "utf8"}:
        return (
            _format_http_json_request_content_type_charset_validation_error(
                raw_content_type
            ),
        )
    return ()


def _raise_http_json_rendered_request_content_type_validation_error(
    *,
    headers: object,
) -> None:
    validation_errors = _describe_http_json_request_content_type_validation_errors(
        headers=headers
    )
    if not validation_errors:
        return
    message = validation_errors[0].removeprefix("http_json execution ")
    raise MockToolExecutionError(
        f"HTTP JSON tool {message}.",
        fatal=True,
    )


def _ensure_http_json_request_content_type_header(
    headers: dict[str, str],
) -> None:
    if _get_tool_execution_http_header_value(headers, "Content-Type") is None:
        headers["Content-Type"] = "application/json"


def _format_http_json_request_accept_validation_error(raw_value: object) -> str:
    safe_accept = _format_http_json_error_body_preview(raw_value)
    return (
        "http_json execution headers.Accept must allow application/json or "
        "a +json media type: "
        f"{safe_accept}"
    )


def _describe_http_json_request_accept_validation_errors(
    *,
    headers: object,
) -> tuple[str, ...]:
    raw_accept = _get_tool_execution_http_header_value(headers, "Accept")
    if raw_accept is None:
        return ()
    if _iter_tool_execution_template_variable_references(
        raw_accept,
        path="headers.Accept",
    ):
        return ()
    if isinstance(
        raw_accept, str
    ) and not _http_json_header_value_has_balanced_quoted_parameters(raw_accept):
        return (
            _format_http_json_request_header_quote_validation_error(
                header_name="Accept",
                raw_value=raw_accept,
            ),
        )
    if isinstance(raw_accept, str) and _is_supported_http_json_accept_header(
        raw_accept
    ):
        return ()
    return (_format_http_json_request_accept_validation_error(raw_accept),)


def _raise_http_json_rendered_request_accept_validation_error(
    *,
    headers: object,
) -> None:
    validation_errors = _describe_http_json_request_accept_validation_errors(
        headers=headers
    )
    if not validation_errors:
        return
    message = validation_errors[0].removeprefix("http_json execution ")
    raise MockToolExecutionError(
        f"HTTP JSON tool {message}.",
        fatal=True,
    )


def _ensure_http_json_request_accept_header(headers: dict[str, str]) -> None:
    if _get_tool_execution_http_header_value(headers, "Accept") is None:
        headers["Accept"] = "application/json"


def _describe_tool_execution_http_value_validation_errors(
    *,
    field_name: str,
    raw_mapping: object,
) -> tuple[str, ...]:
    if not isinstance(raw_mapping, dict):
        return ()
    validation_errors: list[str] = []
    if field_name == "headers" and _http_headers_contain_duplicate_names(
        raw_mapping
    ):
        validation_errors.append(
            "http_json execution headers must not include duplicate HTTP header names"
        )
    for raw_key, raw_item in raw_mapping.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        normalized_key = raw_key.strip()
        safe_path = _format_safe_tool_execution_diagnostic_path(
            f"{field_name}.{normalized_key}"
        )
        if field_name == "headers":
            if not _is_supported_tool_execution_http_header_name(raw_key):
                validation_errors.append(
                    "http_json execution headers must use valid HTTP header names"
                )
                continue
            if not _is_supported_tool_execution_http_scalar_value(raw_item):
                validation_errors.append(
                    f"http_json execution {safe_path} must be a "
                    "string, number, or boolean"
                )
                continue
            if _http_header_value_contains_line_break(raw_item):
                validation_errors.append(
                    f"http_json execution {safe_path} must not contain CR or LF"
                )
                continue
            if _http_header_value_contains_control_character(raw_item):
                validation_errors.append(
                    f"http_json execution {safe_path} must not contain control characters"
                )
            continue
        if field_name == "query_params":
            if not _is_supported_tool_execution_http_query_param_name(raw_key):
                validation_errors.append(
                    f"http_json execution {safe_path} must use safe query parameter names"
                )
                continue
            if not _is_supported_tool_execution_http_query_value(raw_item):
                validation_errors.append(
                    f"http_json execution {safe_path} must be a "
                    "string, number, boolean, or list of those values"
                )
    return tuple(validation_errors)


def _format_tool_execution_json_body_child_path(path: str, raw_key: str) -> str:
    normalized_key = raw_key.strip()
    if re.fullmatch(r"[A-Za-z_][0-9A-Za-z_]*", normalized_key):
        return _format_safe_tool_execution_diagnostic_path(f"{path}.{normalized_key}")
    return f"{path}.<field>"


def _describe_tool_execution_json_body_validation_errors(
    raw_value: object,
    *,
    path: str = "json_body",
) -> tuple[str, ...]:
    if raw_value is None:
        return ()
    if isinstance(raw_value, bool):
        return ()
    if isinstance(raw_value, int):
        return ()
    if isinstance(raw_value, float):
        if math.isfinite(raw_value):
            return ()
        return (f"http_json execution {path} must be valid JSON",)
    if isinstance(raw_value, str):
        return ()
    if isinstance(raw_value, dict):
        validation_errors: list[str] = []
        for raw_key, raw_item in raw_value.items():
            if not isinstance(raw_key, str) or not raw_key.strip():
                if path != "json_body":
                    validation_errors.append(
                        f"http_json execution {path} must use non-empty string object field names"
                    )
                continue
            validation_errors.extend(
                _describe_tool_execution_json_body_validation_errors(
                    raw_item,
                    path=_format_tool_execution_json_body_child_path(path, raw_key),
                )
            )
        return tuple(validation_errors)
    if isinstance(raw_value, (list, tuple)):
        validation_errors = []
        for index, raw_item in enumerate(raw_value):
            validation_errors.extend(
                _describe_tool_execution_json_body_validation_errors(
                    raw_item,
                    path=f"{path}[{index}]",
                )
            )
        return tuple(validation_errors)
    return (f"http_json execution {path} must be valid JSON",)


def _raise_http_json_rendered_value_validation_error(
    *,
    field_name: str,
    raw_mapping: object,
) -> None:
    validation_errors = _describe_tool_execution_http_value_validation_errors(
        field_name=field_name,
        raw_mapping=raw_mapping,
    )
    if not validation_errors:
        return
    message = validation_errors[0].removeprefix("http_json execution ")
    raise MockToolExecutionError(
        f"HTTP JSON tool {message}.",
        fatal=True,
    )


def _raise_http_json_rendered_json_body_validation_error(raw_value: object) -> None:
    validation_errors = _describe_tool_execution_json_body_validation_errors(raw_value)
    if not validation_errors:
        return
    message = validation_errors[0].removeprefix("http_json execution ")
    raise MockToolExecutionError(
        f"HTTP JSON tool {message}.",
        fatal=True,
    )


def _is_supported_tool_execution_response_path_segment(segment: str) -> bool:
    if not segment:
        return False
    index = 0
    if segment[index] != "[":
        while index < len(segment) and segment[index] not in "[]":
            index += 1
    while index < len(segment):
        if segment[index] != "[":
            return False
        closing_index = segment.find("]", index + 1)
        if closing_index == -1:
            return False
        raw_index = segment[index + 1 : closing_index]
        if not raw_index.isdigit():
            return False
        index = closing_index + 1
    return True


def _is_supported_tool_execution_response_path(raw_value: object) -> bool:
    if not isinstance(raw_value, str):
        return False
    normalized = raw_value.strip()
    if normalized == "$":
        return True
    if normalized.startswith("$"):
        normalized = normalized[1:]
    if normalized.startswith("."):
        normalized = normalized[1:]
    if not normalized:
        return False
    segments = normalized.split(".")
    return all(
        _is_supported_tool_execution_response_path_segment(segment)
        for segment in segments
    )


def _normalize_tool_execution_response_path(raw_value: object) -> list[object]:
    if not isinstance(raw_value, str):
        return []
    normalized = raw_value.strip()
    if normalized.startswith("$"):
        normalized = normalized[1:]
    if normalized.startswith("."):
        normalized = normalized[1:]
    if not normalized:
        return []
    parts: list[object] = []
    for segment in normalized.split("."):
        if not segment:
            continue
        token_match = re.finditer(r"([^\[\]]+)|\[(\d+)\]", segment)
        for match in token_match:
            key = match.group(1)
            index = match.group(2)
            if key:
                parts.append(key)
            elif index is not None:
                parts.append(int(index))
    return parts


def _extract_tool_execution_response_value(
    payload: object,
    *,
    path: object,
) -> object:
    path_tokens = _normalize_tool_execution_response_path(path)
    if not path_tokens:
        return payload
    current = payload
    for token in path_tokens:
        if isinstance(token, int):
            if not isinstance(current, (list, tuple)) or token >= len(current):
                return _TOOL_EXECUTION_TEMPLATE_MISSING
            current = current[token]
            continue
        if not isinstance(current, dict) or token not in current:
            return _TOOL_EXECUTION_TEMPLATE_MISSING
        current = current[token]
    return current


def _normalize_nonnegative_int_count_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        if value >= 0:
            return value
        return None
    if isinstance(value, float):
        if value >= 0 and value.is_integer():
            return int(value)
        return None
    if isinstance(value, str):
        normalized_value = value.strip()
        if normalized_value.isdigit():
            return int(normalized_value)
        if "." in normalized_value:
            whole_part, fractional_part = normalized_value.split(".", 1)
            if (
                whole_part.isdigit()
                and fractional_part
                and all(char == "0" for char in fractional_part)
            ):
                return int(whole_part)
    return None


def _normalize_http_json_output_shape(output: dict[str, object]) -> dict[str, object]:
    normalized_output = dict(output)
    if "request_id" in normalized_output:
        safe_request_id = _get_safe_http_json_request_id_display_value(
            normalized_output.get("request_id")
        )
        if safe_request_id is None:
            normalized_output.pop("request_id", None)
        else:
            normalized_output["request_id"] = safe_request_id
    documents_total = _normalize_nonnegative_int_count_value(
        normalized_output.get("documents_total")
    )
    if documents_total is not None:
        normalized_output["documents_total"] = documents_total
    else:
        for alias_name in ("documents", "items"):
            alias_value = normalized_output.get(alias_name)
            if isinstance(alias_value, (list, tuple)):
                normalized_output["documents_total"] = len(alias_value)
                break
    hit_count = _normalize_nonnegative_int_count_value(
        normalized_output.get("hit_count")
    )
    if hit_count is not None:
        normalized_output["hit_count"] = hit_count
    else:
        for alias_name in ("hits", "results", "matches"):
            alias_value = normalized_output.get(alias_name)
            if isinstance(alias_value, (list, tuple)):
                normalized_output["hit_count"] = len(alias_value)
                break
    return normalized_output


def _redact_http_json_sensitive_payload_value(raw_value: object) -> object:
    if isinstance(raw_value, dict):
        redacted: dict[str, object] = {}
        for key, value in raw_value.items():
            normalized_key = str(key)
            if _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.search(normalized_key):
                redacted[normalized_key] = "[redacted]"
                continue
            redacted[normalized_key] = _redact_http_json_sensitive_payload_value(value)
        return redacted
    if isinstance(raw_value, list):
        return [_redact_http_json_sensitive_payload_value(item) for item in raw_value]
    if isinstance(raw_value, tuple):
        return tuple(_redact_http_json_sensitive_payload_value(item) for item in raw_value)
    if isinstance(raw_value, str):
        return _HTTP_JSON_ERROR_BODY_SENSITIVE_ASSIGNMENT_RE.sub(
            lambda match: f"{match.group(1)}[redacted]",
            raw_value,
        )
    return raw_value


def _normalize_http_json_safe_output_shape(output: dict[str, object]) -> dict[str, object]:
    normalized_output = _normalize_http_json_output_shape(output)
    redacted_output = _redact_http_json_sensitive_payload_value(normalized_output)
    if isinstance(redacted_output, dict):
        return redacted_output
    return normalized_output


def _normalize_tool_result_projection_output(
    output: dict[str, object],
    *,
    registration: ToolRegistration | None,
) -> dict[str, object]:
    if registration is not None and registration.execution_kind == "http_json":
        return _normalize_http_json_safe_output_shape(output)
    return output


def _redact_http_json_diagnostic_text(raw_value: str) -> str:
    return _HTTP_JSON_ERROR_BODY_SENSITIVE_ASSIGNMENT_RE.sub(
        "[redacted]",
        raw_value,
    )


def _redact_tool_registry_diagnostic_value(raw_value: object) -> str:
    text = _redact_http_json_diagnostic_text(str(raw_value).strip())
    if not text:
        return ""

    def redact_path(match: re.Match[str]) -> str:
        safe_path = _format_safe_tool_execution_diagnostic_path(match.group(0))
        if "[redacted]" in safe_path:
            return "[redacted]"
        return safe_path

    return _TOOL_REGISTRY_DIAGNOSTIC_FIELD_PATH_RE.sub(redact_path, text)


def _redact_http_json_error_body_value(raw_value: object) -> object:
    if isinstance(raw_value, dict):
        redacted: dict[str, object] = {}
        for key, value in raw_value.items():
            safe_key = _format_safe_tool_execution_summary_field_name(key)
            if safe_key == "[redacted]":
                redacted[safe_key] = "[redacted]"
                continue
            redacted[safe_key] = _redact_http_json_error_body_value(value)
        return redacted
    if isinstance(raw_value, list):
        return [_redact_http_json_error_body_value(item) for item in raw_value]
    if isinstance(raw_value, tuple):
        return tuple(_redact_http_json_error_body_value(item) for item in raw_value)
    if isinstance(raw_value, str):
        return _redact_http_json_diagnostic_text(raw_value)
    return raw_value


def _coerce_http_json_error_body_preview_text(raw_body: object) -> str:
    if isinstance(raw_body, bytes):
        raw_text = raw_body.decode("utf-8", errors="replace")
    else:
        raw_text = str(raw_body)
    try:
        parsed_body = json.loads(raw_text)
    except (TypeError, ValueError):
        return _redact_http_json_diagnostic_text(raw_text)
    redacted_body = _redact_http_json_error_body_value(parsed_body)
    return json.dumps(redacted_body, ensure_ascii=False, separators=(",", ":"))


def _format_http_json_error_body_preview(raw_body: object) -> str:
    normalized = _coerce_http_json_error_body_preview_text(raw_body)
    normalized = " ".join(normalized.strip().split())
    if len(normalized) <= _HTTP_JSON_ERROR_BODY_PREVIEW_MAX_LENGTH:
        return normalized
    return f"{normalized[:_HTTP_JSON_ERROR_BODY_PREVIEW_MAX_LENGTH]}..."


def _coerce_http_json_body_preview_bytes(raw_body: object) -> bytes | None:
    if isinstance(raw_body, bytes):
        return raw_body
    if isinstance(raw_body, bytearray):
        return bytes(raw_body)
    if isinstance(raw_body, memoryview):
        return raw_body.tobytes()
    return None


def _format_http_json_response_body_preview(
    raw_body: object,
    *,
    content_type: object = None,
) -> str:
    raw_bytes = _coerce_http_json_body_preview_bytes(raw_body)
    if raw_bytes is None:
        return _format_http_json_error_body_preview(raw_body)
    charset = _get_http_json_response_charset(content_type)
    try:
        codecs.lookup(charset)
        raw_text = raw_bytes.decode(charset)
    except (LookupError, UnicodeError):
        return _format_http_json_error_body_preview(raw_bytes)
    return _format_http_json_error_body_preview(raw_text)


def _append_http_json_response_header_diagnostic_hints(
    message: str,
    response: object,
) -> str:
    header_hints = _format_http_json_response_header_diagnostic_hints(response)
    if not header_hints:
        return message
    return f"{message}; headers: {header_hints}"


def _format_http_json_http_error(exc: HTTPError) -> str:
    message = f"HTTP JSON tool failed: HTTP {exc.code}"
    reason = _format_http_json_error_body_preview(
        getattr(exc, "reason", "") or ""
    )
    if reason:
        message = f"{message} {reason}"
    message = _append_http_json_response_header_diagnostic_hints(message, exc)
    content_type = _get_http_json_response_content_type(exc)
    try:
        body = _read_http_json_response_body_bytes(exc)
        body = _decode_http_json_response_body_for_content_encoding(
            raw_body=body,
            content_encoding=_get_http_json_response_content_encoding(exc),
            content_type=content_type,
        )
        body_preview = _format_http_json_response_body_preview(
            body,
            content_type=content_type,
        )
    except (OSError, TypeError) as exc:
        body_preview = _format_http_json_error_body_preview(exc)
    except ValueError as exc:
        body_preview = _format_http_json_error_body_preview(exc)
    if body_preview:
        message = f"{message}; body: {body_preview}"
    return message


def _coerce_http_json_response_status_code(raw_value: object) -> int | None:
    if isinstance(raw_value, bool):
        return None
    if isinstance(raw_value, int):
        return raw_value
    if isinstance(raw_value, float):
        if math.isfinite(raw_value) and raw_value.is_integer():
            return int(raw_value)
        return None
    if isinstance(raw_value, bytes):
        raw_value = raw_value.decode("utf-8", errors="replace")
    if isinstance(raw_value, bytearray):
        raw_value = bytes(raw_value).decode("utf-8", errors="replace")
    if isinstance(raw_value, memoryview):
        raw_value = raw_value.tobytes().decode("utf-8", errors="replace")
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        match = re.match(r"^(\d{3})(?:\b|$)", normalized)
        if match:
            return int(match.group(1))
    return None


def _http_json_response_status_value_is_present(raw_value: object) -> bool:
    if raw_value is None:
        return False
    if isinstance(raw_value, str):
        return bool(raw_value.strip())
    if isinstance(raw_value, (bytes, bytearray)):
        return bool(bytes(raw_value).strip())
    if isinstance(raw_value, memoryview):
        return bool(raw_value.tobytes().strip())
    return True


def _format_http_json_invalid_status_response(
    *,
    raw_status: object,
    raw_body: object,
    content_type: object = None,
    response: object | None = None,
) -> str:
    status_preview = _format_http_json_error_body_preview(raw_status)
    message = "HTTP JSON tool failed: invalid HTTP response status"
    if status_preview:
        message = f"{message}: {status_preview}"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(message, response)
    body_preview = _format_http_json_response_body_preview(
        raw_body,
        content_type=content_type,
    )
    if body_preview:
        message = f"{message}; body: {body_preview}"
    return message


def _get_http_json_adapter_attr(adapter: object, attr_name: str) -> object | None:
    try:
        return getattr(adapter, attr_name, None)
    except Exception:
        return None


def _call_http_json_adapter_method(
    method: object,
    *args: object,
    **kwargs: object,
) -> object | None:
    if not callable(method):
        return None
    try:
        return method(*args, **kwargs)
    except Exception:
        return None


def _call_http_json_getheader_adapter(
    getheader: object,
    header_name: str,
) -> object | None:
    raw_value = _call_http_json_adapter_method(getheader, header_name, None)
    if raw_value is not None:
        return raw_value
    return _call_http_json_adapter_method(getheader, header_name)


def _get_http_json_response_status_code(
    response: object,
) -> tuple[int | None, object | None]:
    for attr_name in ("status", "code", "status_code"):
        raw_status = _get_http_json_adapter_attr(response, attr_name)
        if not _http_json_response_status_value_is_present(raw_status):
            continue
        status_code = _coerce_http_json_response_status_code(raw_status)
        if status_code is None or not 100 <= status_code <= 599:
            return None, raw_status
        return status_code, None
    getcode = _get_http_json_adapter_attr(response, "getcode")
    if callable(getcode):
        raw_status = _call_http_json_adapter_method(getcode)
        if not _http_json_response_status_value_is_present(raw_status):
            return None, None
        status_code = _coerce_http_json_response_status_code(raw_status)
        if status_code is None or not 100 <= status_code <= 599:
            return None, raw_status
        return status_code, None
    return None, None


def _coerce_http_json_response_text(raw_value: object) -> str | None:
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        return normalized or None
    if isinstance(raw_value, bytes):
        normalized = raw_value.decode("utf-8", errors="replace").strip()
        return normalized or None
    if isinstance(raw_value, bytearray):
        normalized = bytes(raw_value).decode("utf-8", errors="replace").strip()
        return normalized or None
    if isinstance(raw_value, memoryview):
        normalized = raw_value.tobytes().decode("utf-8", errors="replace").strip()
        return normalized or None
    return None


def _get_http_json_response_reason(response: object) -> object:
    for attr_name in ("reason", "msg"):
        reason = _coerce_http_json_response_text(
            _get_http_json_adapter_attr(response, attr_name)
        )
        if reason is not None:
            return reason
    return ""


def _get_http_json_response_url(response: object) -> str | None:
    geturl = _get_http_json_adapter_attr(response, "geturl")
    if callable(geturl):
        raw_value = _call_http_json_adapter_method(geturl)
        response_url = _coerce_http_json_response_text(raw_value)
        if response_url is not None:
            return response_url
    response_url = _coerce_http_json_response_text(
        _get_http_json_adapter_attr(response, "url")
    )
    if response_url is not None:
        return response_url
    return None


_HTTP_JSON_UNRESERVED_URL_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)


def _normalize_http_json_unreserved_percent_encoding(value: str) -> str:
    def replace_match(match: re.Match[str]) -> str:
        encoded_value = match.group(0)
        decoded_char = chr(int(encoded_value[1:], 16))
        if decoded_char in _HTTP_JSON_UNRESERVED_URL_CHARS:
            return decoded_char
        return encoded_value.upper()

    return re.sub(r"%[0-9A-Fa-f]{2}", replace_match, value)


def _normalize_http_json_query_for_drift_check(
    raw_query: str,
) -> tuple[tuple[str, str], ...] | None:
    try:
        query_pairs = parse_qsl(raw_query, keep_blank_values=True)
    except ValueError:
        return None
    return tuple(sorted(query_pairs))


def _normalize_http_json_url_for_drift_check(
    raw_url: str,
) -> tuple[str, str, str, str, tuple[tuple[str, str], ...]] | None:
    parsed = urlparse(raw_url)
    hostname = parsed.hostname
    if not parsed.scheme or hostname is None:
        return None
    try:
        port = parsed.port
    except ValueError:
        return None
    scheme = parsed.scheme.lower()
    normalized_host = hostname.lower()
    default_port = (
        (scheme == "http" and port == 80)
        or (scheme == "https" and port == 443)
    )
    normalized_authority = (
        normalized_host
        if port is None or default_port
        else f"{normalized_host}:{port}"
    )
    normalized_query = _normalize_http_json_query_for_drift_check(parsed.query)
    if normalized_query is None:
        return None
    return (
        scheme,
        normalized_authority,
        _normalize_http_json_unreserved_percent_encoding(parsed.path or "/"),
        _normalize_http_json_unreserved_percent_encoding(parsed.params),
        normalized_query,
    )


def _http_json_response_url_matches_request_url(
    *,
    response_url: str,
    request_url: str,
) -> bool:
    if response_url == request_url:
        return True
    normalized_response_url = _normalize_http_json_url_for_drift_check(response_url)
    normalized_request_url = _normalize_http_json_url_for_drift_check(request_url)
    return (
        normalized_response_url is not None
        and normalized_request_url is not None
        and normalized_response_url == normalized_request_url
    )


def _format_http_json_redirected_response_url_error(
    response: object | None = None,
) -> str:
    message = "HTTP JSON tool failed: redirected response url does not match request url"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(
            message,
            response,
        )
    return message


def _format_http_json_unexpected_status_response(
    *,
    status_code: int,
    reason: object,
    raw_body: bytes,
    content_type: object = None,
    response: object | None = None,
) -> str:
    message = f"HTTP JSON tool failed: HTTP {status_code}"
    reason_preview = _format_http_json_error_body_preview(reason or "")
    if reason_preview:
        message = f"{message} {reason_preview}"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(message, response)
    body_preview = _format_http_json_response_body_preview(
        raw_body,
        content_type=content_type,
    )
    if body_preview:
        message = f"{message}; body: {body_preview}"
    return message


def _format_http_json_unexpected_status_response_body_decode_error(
    *,
    status_code: int,
    reason: object,
    error: Exception,
    response: object | None = None,
) -> str:
    message = f"HTTP JSON tool failed: HTTP {status_code}"
    reason_preview = _format_http_json_error_body_preview(reason or "")
    if reason_preview:
        message = f"{message} {reason_preview}"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(message, response)
    body_preview = _format_http_json_error_body_preview(error)
    if body_preview:
        message = f"{message}; body: {body_preview}"
    return message


def _format_http_json_empty_response(
    *,
    status_code: int | None,
    reason: object,
    response: object | None = None,
) -> str:
    message = "HTTP JSON tool failed: empty JSON response"
    if status_code is not None:
        message = f"{message}: HTTP {status_code}"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(
            message,
            response,
        )
    reason_preview = _format_http_json_error_body_preview(reason or "")
    if reason_preview:
        message = f"{message} {reason_preview}"
    return message


def _coerce_http_json_response_body_bytes(raw_body: object) -> bytes:
    if isinstance(raw_body, bytes):
        return raw_body
    if isinstance(raw_body, bytearray):
        return bytes(raw_body)
    if isinstance(raw_body, memoryview):
        return raw_body.tobytes()
    if isinstance(raw_body, str):
        return raw_body.encode("utf-8")
    raise TypeError("response body must be bytes or text")


def _read_http_json_response_body_bytes(response: object) -> bytes:
    read = _get_http_json_adapter_attr(response, "read")
    if not callable(read):
        raise TypeError("response body reader is unavailable")
    try:
        return _coerce_http_json_response_body_bytes(read())
    except TypeError:
        raise
    except Exception as exc:
        raise TypeError(f"response read failed: {exc}") from exc


def _format_http_json_invalid_json_response(
    *,
    raw_body: bytes,
    error: json.JSONDecodeError | UnicodeDecodeError,
    charset: str = "utf-8",
    content_type: object = None,
    response: object | None = None,
) -> str:
    error_message = (
        error.msg
        if isinstance(error, json.JSONDecodeError)
        else f"invalid {_format_http_json_error_body_preview(charset)} response body: {error.reason}"
    )
    message = f"HTTP JSON tool failed: invalid JSON response: {error_message}"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(
            message,
            response,
        )
    body_preview = _format_http_json_response_body_preview(
        raw_body,
        content_type=content_type,
    )
    if body_preview:
        message = f"{message}; body: {body_preview}"
    return message


def _format_http_json_invalid_charset_response(
    *,
    charset: str,
    raw_body: bytes,
    response: object | None = None,
) -> str:
    safe_charset = _format_http_json_error_body_preview(charset)
    message = f"HTTP JSON tool failed: invalid JSON response charset: {safe_charset}"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(
            message,
            response,
        )
    body_preview = _format_http_json_error_body_preview(raw_body)
    if body_preview:
        message = f"{message}; body: {body_preview}"
    return message


def _coerce_http_json_header_text(raw_value: object) -> str | None:
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        return normalized or None
    if isinstance(raw_value, bytes):
        normalized = raw_value.decode("utf-8", errors="replace").strip()
        return normalized or None
    if isinstance(raw_value, bytearray):
        normalized = bytes(raw_value).decode("utf-8", errors="replace").strip()
        return normalized or None
    if isinstance(raw_value, memoryview):
        normalized = raw_value.tobytes().decode("utf-8", errors="replace").strip()
        return normalized or None
    if isinstance(raw_value, (list, tuple)):
        values = [
            header_value
            for item in raw_value
            if (header_value := _coerce_http_json_header_text(item)) is not None
        ]
        return ", ".join(values) if values else None
    return None


def _coerce_http_json_header_name_text(raw_value: object) -> str | None:
    header_name = _coerce_http_json_response_text(raw_value)
    return header_name.lower() if header_name is not None else None


def _get_http_json_header_items(headers: object) -> object:
    for method_name in ("items", "raw_items", "multi_items"):
        items = _get_http_json_adapter_attr(headers, method_name)
        if callable(items):
            header_items = _call_http_json_adapter_method(items)
            if header_items is not None:
                return header_items
    if isinstance(headers, (list, tuple)):
        return headers
    return ()


def _get_http_json_header_value_from_method(
    *,
    headers: object,
    method_name: str,
    header_name: str,
) -> str | None:
    method = _get_http_json_adapter_attr(headers, method_name)
    if not callable(method):
        return None
    for candidate_name in (
        header_name,
        header_name.lower(),
        header_name.upper(),
        header_name.encode("ascii"),
        header_name.lower().encode("ascii"),
        header_name.upper().encode("ascii"),
    ):
        raw_value = _call_http_json_adapter_method(
            method,
            candidate_name,
            None,
        )
        header_value = _coerce_http_json_header_text(raw_value)
        if header_value is not None:
            return header_value
        raw_value = _call_http_json_adapter_method(
            method,
            candidate_name,
        )
        header_value = _coerce_http_json_header_text(raw_value)
        if header_value is not None:
            return header_value
    return None


def _get_http_json_header_text_from_mapping(
    headers: object,
    header_name: str,
) -> str | None:
    normalized_header_name = header_name.strip().lower()
    header_values: list[str] = []
    header_items = _get_http_json_header_items(headers)
    for raw_item in header_items:
        try:
            raw_key, raw_value = raw_item
        except (TypeError, ValueError):
            continue
        if _coerce_http_json_header_name_text(raw_key) == normalized_header_name:
            header_value = _coerce_http_json_header_text(raw_value)
            if header_value is not None:
                header_values.append(header_value)
    if header_values:
        return ", ".join(header_values)
    for method_name in ("get_all", "getheaders", "get"):
        header_value = _get_http_json_header_value_from_method(
            headers=headers,
            method_name=method_name,
            header_name=header_name,
        )
        if header_value is not None:
            return header_value
    return None


def _get_http_json_response_header_text(
    response: object,
    header_name: str,
) -> str | None:
    getheader = _get_http_json_adapter_attr(response, "getheader")
    if callable(getheader):
        raw_value = _call_http_json_getheader_adapter(getheader, header_name)
        header_value = _coerce_http_json_header_text(raw_value)
        if header_value is not None:
            return header_value
    for attr_name in ("headers", "hdrs"):
        headers = _get_http_json_adapter_attr(response, attr_name)
        if headers is None:
            continue
        header_value = _get_http_json_header_text_from_mapping(headers, header_name)
        if header_value is not None:
            return header_value
    info = _get_http_json_adapter_attr(response, "info")
    if callable(info):
        info_headers = _call_http_json_adapter_method(info)
        header_value = _get_http_json_header_text_from_mapping(
            info_headers,
            header_name,
        )
        if header_value is not None:
            return header_value
    return None


def _format_http_json_response_header_diagnostic_hints(response: object) -> str:
    hint_parts: list[str] = []
    seen_labels: set[str] = set()
    for header_name, label in _HTTP_JSON_RESPONSE_DIAGNOSTIC_HEADER_HINTS:
        if label in seen_labels:
            continue
        header_value = _get_http_json_response_header_text(response, header_name)
        if header_value is None:
            continue
        if label == "request id" and not _is_safe_http_json_request_id_value(header_value):
            continue
        safe_header_value = _format_http_json_error_body_preview(header_value)
        if not safe_header_value:
            continue
        hint_parts.append(f"{label}: {safe_header_value}")
        seen_labels.add(label)
    return "; ".join(hint_parts)


def _get_http_json_response_request_id(response: object) -> str | None:
    for header_name in _HTTP_JSON_RESPONSE_REQUEST_ID_HEADER_NAMES:
        header_value = _get_http_json_response_header_text(response, header_name)
        if header_value is None:
            continue
        normalized = header_value.strip()
        if not normalized:
            continue
        if not _is_safe_http_json_request_id_value(normalized):
            continue
        return normalized
    return None


def _is_safe_http_json_request_id_value(value: str) -> bool:
    normalized = value.strip()
    if not normalized:
        return False
    if len(normalized) > 128:
        return False
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in normalized):
        return False
    safe_value = _format_http_json_error_body_preview(normalized)
    return safe_value == normalized


def _get_safe_http_json_request_id_display_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not _is_safe_http_json_request_id_value(normalized):
        return None
    return normalized


def _attach_http_json_response_request_id(
    output: dict[str, object],
    request_id: str | None,
) -> dict[str, object]:
    safe_existing_request_id = _get_safe_http_json_request_id_display_value(
        output.get("request_id")
    )
    if safe_existing_request_id is not None:
        output["request_id"] = safe_existing_request_id
        return output
    if "request_id" in output:
        output.pop("request_id", None)
    if not request_id:
        return output
    output["request_id"] = request_id
    return output


def _get_http_json_response_content_type(response: object) -> str | None:
    return _get_http_json_response_header_text(response, "Content-Type")


def _get_http_json_response_content_encoding(response: object) -> str | None:
    return _get_http_json_response_header_text(response, "Content-Encoding")


def _split_http_json_header_value(
    raw_value: str,
    *,
    separator: str,
) -> tuple[str, ...]:
    values: list[str] = []
    current_value: list[str] = []
    quote_char: str | None = None
    escaped = False
    for char in raw_value:
        if escaped:
            current_value.append(char)
            escaped = False
            continue
        if quote_char is not None:
            current_value.append(char)
            if char == "\\":
                escaped = True
            elif char == quote_char:
                quote_char = None
            continue
        if char in ("'", '"'):
            quote_char = char
            current_value.append(char)
            continue
        if char == separator:
            normalized_value = "".join(current_value).strip()
            if normalized_value:
                values.append(normalized_value)
            current_value = []
            continue
        current_value.append(char)
    normalized_value = "".join(current_value).strip()
    if normalized_value:
        values.append(normalized_value)
    return tuple(values)


def _split_http_json_header_values(raw_value: str) -> tuple[str, ...]:
    return _split_http_json_header_value(raw_value, separator=",")


def _split_http_json_header_parameters(raw_value: str) -> tuple[str, ...]:
    return _split_http_json_header_value(raw_value, separator=";")


def _get_http_json_response_charset(raw_content_type: object) -> str:
    if not isinstance(raw_content_type, str) or ";" not in raw_content_type:
        return "utf-8"
    charset_values: list[str] = []
    for content_type_value in _split_http_json_header_values(raw_content_type):
        for raw_parameter in _split_http_json_header_parameters(content_type_value)[1:]:
            raw_name, separator, raw_value = raw_parameter.partition("=")
            if raw_name.strip().lower() != "charset":
                continue
            if not separator:
                charset_values.append("")
                continue
            normalized_value = raw_value.strip().strip("\"'")
            charset_values.append(normalized_value if normalized_value else "")
    if not charset_values:
        return "utf-8"
    normalized_charset_values = {
        charset_value.lower().replace("_", "-")
        for charset_value in charset_values
    }
    if len(normalized_charset_values) > 1:
        safe_values = ", ".join(charset_values[:3])
        if len(charset_values) > 3:
            safe_values = f"{safe_values}, ..."
        return f"ambiguous response charset: {safe_values}"
    return charset_values[0]


def _decode_http_json_response_text(
    *,
    raw_body: bytes,
    content_type: object,
    response: object | None = None,
) -> str:
    charset = _get_http_json_response_charset(content_type)
    try:
        codecs.lookup(charset)
    except LookupError as exc:
        raise MockToolExecutionError(
            _format_http_json_invalid_charset_response(
                charset=charset,
                raw_body=raw_body,
                response=response,
            ),
            fatal=False,
        ) from exc
    try:
        return raw_body.decode(charset)
    except UnicodeDecodeError as exc:
        raise MockToolExecutionError(
            _format_http_json_invalid_json_response(
                raw_body=raw_body,
                error=exc,
                charset=charset,
                content_type=content_type,
                response=response,
            ),
            fatal=False,
        ) from exc


def _normalize_http_json_content_encodings(raw_value: object) -> tuple[str, ...]:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return ()
    encodings = [
        item.strip().lower()
        for item in raw_value.split(",")
        if item.strip()
    ]
    return tuple(encodings)


def _decompress_http_json_deflate_body(raw_body: bytes) -> bytes:
    try:
        return zlib.decompress(raw_body)
    except zlib.error as wrapped_exc:
        try:
            return zlib.decompress(raw_body, -zlib.MAX_WBITS)
        except zlib.error as raw_exc:
            raise raw_exc from wrapped_exc


def _decode_http_json_response_body_for_content_encoding(
    *,
    raw_body: bytes,
    content_encoding: object,
    content_type: object = None,
) -> bytes:
    decoded_body = raw_body
    normalized_encodings = _normalize_http_json_content_encodings(content_encoding)
    if not normalized_encodings:
        return decoded_body
    for normalized_encoding in reversed(normalized_encodings):
        if normalized_encoding == "identity":
            continue
        if normalized_encoding == "gzip":
            try:
                decoded_body = gzip.decompress(decoded_body)
            except (OSError, EOFError, zlib.error) as exc:
                body_preview = _format_http_json_response_body_preview(
                    decoded_body,
                    content_type=content_type,
                )
                message = "invalid gzip response body"
                if body_preview:
                    message = f"{message}; body: {body_preview}"
                raise ValueError(message) from exc
            continue
        if normalized_encoding == "deflate":
            try:
                decoded_body = _decompress_http_json_deflate_body(decoded_body)
            except zlib.error as exc:
                body_preview = _format_http_json_response_body_preview(
                    decoded_body,
                    content_type=content_type,
                )
                message = "invalid deflate response body"
                if body_preview:
                    message = f"{message}; body: {body_preview}"
                raise ValueError(message) from exc
            continue
        safe_encoding = _format_http_json_error_body_preview(
            ",".join(normalized_encodings)
        )
        body_preview = _format_http_json_response_body_preview(
            decoded_body,
            content_type=content_type,
        )
        message = f"unsupported response content-encoding: {safe_encoding}"
        if body_preview:
            message = f"{message}; body: {body_preview}"
        raise ValueError(message)
    return decoded_body


def _is_supported_http_json_response_content_type(raw_value: object) -> bool:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return True
    if not _http_json_header_value_has_balanced_quoted_parameters(raw_value):
        return False
    content_type_values = _split_http_json_header_values(raw_value)
    if not content_type_values:
        return False
    for content_type_value in content_type_values:
        media_type = content_type_value.split(";", 1)[0].strip().lower()
        if not (media_type == "application/json" or media_type.endswith("+json")):
            return False
    return True


def _format_http_json_invalid_content_type_response(
    *,
    content_type: str,
    raw_body: bytes,
    response: object | None = None,
) -> str:
    safe_content_type = _format_http_json_error_body_preview(content_type)
    message = (
        "HTTP JSON tool failed: invalid JSON response content-type: "
        f"{safe_content_type}"
    )
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(
            message,
            response,
        )
    body_preview = _format_http_json_response_body_preview(
        raw_body,
        content_type=content_type,
    )
    if body_preview:
        message = f"{message}; body: {body_preview}"
    return message


def _format_http_json_transport_error(
    exc: BaseException,
    response: object | None = None,
) -> str:
    raw_reason = getattr(exc, "reason", None)
    reason = raw_reason if raw_reason is not None else exc
    reason_preview = _format_http_json_error_body_preview(reason)
    if reason_preview:
        message = f"HTTP JSON tool failed: transport error: {reason_preview}"
    else:
        message = "HTTP JSON tool failed: transport error"
    if response is not None:
        message = _append_http_json_response_header_diagnostic_hints(
            message,
            response,
        )
    return message


def _format_http_json_mapping_path_for_error(raw_path: object) -> str:
    safe_path = _format_safe_tool_execution_diagnostic_path(str(raw_path).strip())
    return _format_http_json_error_body_preview(safe_path)


def _format_http_json_mapping_payload_shape_key_for_error(raw_key: object) -> str:
    safe_key = _format_safe_tool_execution_summary_field_name(raw_key)
    if not safe_key:
        return ""
    safe_key = _format_http_json_error_body_preview(safe_key)
    if len(safe_key) <= _HTTP_JSON_MAPPING_PAYLOAD_SHAPE_KEY_MAX_LENGTH:
        return safe_key
    return f"{safe_key[:_HTTP_JSON_MAPPING_PAYLOAD_SHAPE_KEY_MAX_LENGTH]}..."


def _format_http_json_mapping_payload_shape_keys_for_error(payload: dict) -> str:
    safe_keys: list[str] = []
    seen_keys: set[str] = set()
    for raw_key in payload.keys():
        safe_key = _format_http_json_mapping_payload_shape_key_for_error(raw_key)
        if not safe_key or safe_key in seen_keys:
            continue
        seen_keys.add(safe_key)
        safe_keys.append(safe_key)
    if not safe_keys:
        return "none"
    visible_keys = safe_keys[:_HTTP_JSON_MAPPING_PAYLOAD_SHAPE_KEY_MAX_ITEMS]
    hidden_count = len(safe_keys) - len(visible_keys)
    if hidden_count > 0:
        visible_keys.append(f"and {hidden_count} more")
    return ", ".join(visible_keys)


def _format_http_json_mapping_payload_shape_for_error(payload: object) -> str:
    if isinstance(payload, dict):
        keys = _format_http_json_mapping_payload_shape_keys_for_error(payload)
        return f"available response keys: {keys}"
    if isinstance(payload, list):
        message = f"response payload is a list with {len(payload)} items"
        if payload and isinstance(payload[0], dict):
            keys = _format_http_json_mapping_payload_shape_keys_for_error(payload[0])
            message = f"{message}; first item keys: {keys}"
        return message
    if payload is None:
        return "response payload is null"
    if isinstance(payload, bool):
        return "response payload is a boolean"
    if isinstance(payload, (int, float)):
        return "response payload is a number"
    if isinstance(payload, str):
        return "response payload is a string"
    return "response payload has an unsupported shape"


def _format_http_json_result_field_mapping_error(
    *,
    field_name: str,
    raw_path: object,
) -> str:
    safe_field_name = _format_safe_tool_execution_summary_field_name(field_name)
    safe_path = _format_http_json_mapping_path_for_error(raw_path)
    return f"{safe_field_name} -> {safe_path}"


def _format_http_json_missing_result_field_mappings(
    missing_result_fields: list[str],
) -> str:
    visible_mappings = missing_result_fields[
        :_HTTP_JSON_RESULT_FIELD_MAPPING_ERROR_MAX_ITEMS
    ]
    hidden_count = len(missing_result_fields) - len(visible_mappings)
    if hidden_count > 0:
        visible_mappings.append(f"and {hidden_count} more")
    return "; ".join(visible_mappings)


def _build_http_json_tool_runner(
    *,
    execution_spec: dict[str, object],
    default_timeout_ms: int,
    template_context: dict[str, object] | None = None,
) -> ToolRunner:
    method = _normalize_tool_execution_http_method(
        execution_spec.get("method", "POST" if execution_spec.get("json_body") else "GET")
    )
    headers = _normalize_tool_execution_http_headers(execution_spec.get("headers"))
    raw_query_params = execution_spec.get("query_params")
    raw_json_body = execution_spec.get("json_body")
    raw_response_path = execution_spec.get("response_path")
    raw_result_fields = execution_spec.get("result_fields")
    timeout_ms = _coerce_tool_execution_timeout_ms(
        execution_spec.get("timeout_ms"),
        default_timeout_ms=default_timeout_ms,
    )

    def runner(*, tool_input: dict[str, object], prompt: str, user_id: str) -> dict[str, object]:
        raw_url = execution_spec.get("url")
        if not isinstance(raw_url, str) or not raw_url.strip():
            raise MockToolExecutionError(
                "HTTP JSON tool requires a non-empty url.",
                fatal=True,
            )
        context = {
            **(template_context or {}),
            **tool_input,
            "prompt": prompt,
            "user_id": user_id,
        }
        rendered_url = _render_required_tool_execution_template(
            raw_url,
            context=context,
            path="url",
        )
        if not isinstance(rendered_url, str) or not rendered_url.strip():
            raise MockToolExecutionError(
                "HTTP JSON tool could not resolve a valid url.",
                fatal=True,
            )
        _raise_http_json_rendered_url_validation_error(rendered_url)
        rendered_headers_value = _render_required_tool_execution_template(
            headers,
            context=context,
            path="headers",
        )
        _raise_http_json_rendered_value_validation_error(
            field_name="headers",
            raw_mapping=rendered_headers_value,
        )
        rendered_headers = _normalize_tool_execution_http_headers(
            rendered_headers_value
        )
        rendered_query_params_value = _render_required_tool_execution_template(
            raw_query_params,
            context=context,
            path="query_params",
        )
        _raise_http_json_rendered_value_validation_error(
            field_name="query_params",
            raw_mapping=rendered_query_params_value,
        )
        rendered_query_params = _normalize_tool_execution_http_query_params(
            rendered_query_params_value
        )
        _raise_http_json_rendered_duplicate_query_param_validation_error(
            url=rendered_url,
            query_params=rendered_query_params,
        )
        _raise_http_json_rendered_request_accept_validation_error(
            headers=rendered_headers
        )
        query_string = urlencode(rendered_query_params, doseq=True)
        full_url = rendered_url.strip()
        if query_string:
            separator = "&" if "?" in full_url else "?"
            full_url = f"{full_url}{separator}{query_string}"
        request_data: bytes | None = None
        if raw_json_body is not None and method != "GET":
            rendered_json_body = _render_required_tool_execution_template(
                raw_json_body,
                context=context,
                path="json_body",
            )
            if not isinstance(rendered_json_body, dict):
                raise MockToolExecutionError(
                    "HTTP JSON tool json_body must resolve to an object.",
                    fatal=True,
                )
            _raise_http_json_rendered_request_content_type_validation_error(
                headers=rendered_headers
            )
            _raise_http_json_rendered_json_body_validation_error(rendered_json_body)
            try:
                request_data = json.dumps(
                    rendered_json_body,
                    ensure_ascii=False,
                    allow_nan=False,
                ).encode("utf-8")
            except (TypeError, ValueError) as exc:
                raise MockToolExecutionError(
                    "HTTP JSON tool json_body must be valid JSON.",
                    fatal=True,
            ) from exc
            _ensure_http_json_request_content_type_header(rendered_headers)
        _ensure_http_json_request_accept_header(rendered_headers)
        request = Request(
            full_url,
            data=request_data,
            headers=rendered_headers,
            method=method,
        )
        response_request_id: str | None = None
        try:
            with urlopen(
                request,
                timeout=max(0.1, timeout_ms / 1000),
            ) as response:
                response_content_encoding = _get_http_json_response_content_encoding(
                    response
                )
                response_status_code, invalid_response_status = (
                    _get_http_json_response_status_code(response)
                )
                response_reason = _get_http_json_response_reason(response)
                response_content_type = _get_http_json_response_content_type(response)
                response_url = _get_http_json_response_url(response)
                response_request_id = _get_http_json_response_request_id(response)
                if (
                    invalid_response_status is None
                    and (
                        response_status_code is None
                        or 200 <= response_status_code <= 299
                    )
                    and response_url is not None
                    and not _http_json_response_url_matches_request_url(
                        response_url=response_url,
                        request_url=full_url,
                    )
                ):
                    raise MockToolExecutionError(
                        _format_http_json_redirected_response_url_error(response),
                        fatal=False,
                    )
                try:
                    response_body = _read_http_json_response_body_bytes(response)
                except TypeError as exc:
                    if invalid_response_status is not None:
                        raise MockToolExecutionError(
                            _format_http_json_invalid_status_response(
                                raw_status=invalid_response_status,
                                raw_body=exc,
                                content_type=response_content_type,
                                response=response,
                            ),
                            fatal=False,
                        ) from exc
                    if (
                        response_status_code is not None
                        and not 200 <= response_status_code <= 299
                    ):
                        raise MockToolExecutionError(
                            _format_http_json_unexpected_status_response_body_decode_error(
                                status_code=response_status_code,
                                reason=response_reason,
                                error=exc,
                                response=response,
                            ),
                            fatal=False,
                        ) from exc
                    raise MockToolExecutionError(
                        _format_http_json_transport_error(exc, response=response),
                        fatal=False,
                    ) from exc
                if invalid_response_status is not None:
                    raise MockToolExecutionError(
                        _format_http_json_invalid_status_response(
                            raw_status=invalid_response_status,
                            raw_body=response_body,
                            content_type=response_content_type,
                            response=response,
                        ),
                        fatal=False,
                    )
                try:
                    response_body = _decode_http_json_response_body_for_content_encoding(
                        raw_body=response_body,
                        content_encoding=response_content_encoding,
                        content_type=response_content_type,
                    )
                except ValueError as exc:
                    if (
                        response_status_code is not None
                        and not 200 <= response_status_code <= 299
                    ):
                        raise MockToolExecutionError(
                            _format_http_json_unexpected_status_response_body_decode_error(
                                status_code=response_status_code,
                                reason=response_reason,
                                error=exc,
                                response=response,
                            ),
                            fatal=False,
                        ) from exc
                    message = f"HTTP JSON tool failed: {exc}"
                    message = _append_http_json_response_header_diagnostic_hints(
                        message,
                        response,
                    )
                    raise MockToolExecutionError(
                        message,
                        fatal=False,
                    ) from exc
                if (
                    response_status_code is not None
                    and not 200 <= response_status_code <= 299
                ):
                    raise MockToolExecutionError(
                        _format_http_json_unexpected_status_response(
                            status_code=response_status_code,
                            reason=response_reason,
                            raw_body=response_body,
                            content_type=response_content_type,
                            response=response,
                        ),
                        fatal=False,
                    )
                if (
                    response_content_type
                    and not _is_supported_http_json_response_content_type(
                        response_content_type
                    )
                ):
                    raise MockToolExecutionError(
                        _format_http_json_invalid_content_type_response(
                            content_type=response_content_type,
                            raw_body=response_body,
                            response=response,
                        ),
                        fatal=False,
                    )
                if not response_body.strip():
                    raise MockToolExecutionError(
                        _format_http_json_empty_response(
                            status_code=response_status_code,
                            reason=response_reason,
                            response=response,
                        ),
                        fatal=False,
                    )
                try:
                    response_text = _decode_http_json_response_text(
                        raw_body=response_body,
                        content_type=response_content_type,
                        response=response,
                    )
                    response_payload = json.loads(response_text)
                except json.JSONDecodeError as exc:
                    raise MockToolExecutionError(
                        _format_http_json_invalid_json_response(
                            raw_body=response_body,
                            error=exc,
                            content_type=response_content_type,
                            response=response,
                        ),
                        fatal=False,
                    ) from exc
        except HTTPError as exc:
            raise MockToolExecutionError(
                _format_http_json_http_error(exc),
                fatal=False,
            ) from exc
        except (URLError, OSError, TypeError, ValueError) as exc:
            raise MockToolExecutionError(
                _format_http_json_transport_error(exc),
                fatal=False,
            ) from exc
        except Exception as exc:
            if isinstance(exc, MockToolExecutionError):
                raise
            raise MockToolExecutionError(
                _format_http_json_transport_error(exc),
                fatal=False,
            ) from exc

        scoped_payload = _extract_tool_execution_response_value(
            response_payload,
            path=raw_response_path,
        )
        if scoped_payload is _TOOL_EXECUTION_TEMPLATE_MISSING:
            if isinstance(raw_response_path, str) and raw_response_path.strip():
                safe_response_path = _format_http_json_mapping_path_for_error(
                    raw_response_path
                )
                payload_shape = _format_http_json_mapping_payload_shape_for_error(
                    response_payload
                )
                message = (
                    "HTTP JSON tool response_path could not resolve any payload at "
                    f"{safe_response_path}; {payload_shape}."
                )
                message = _append_http_json_response_header_diagnostic_hints(
                    message,
                    response,
                )
                raise MockToolExecutionError(
                    message,
                    fatal=True,
                )
            scoped_payload = response_payload
        if isinstance(raw_result_fields, dict):
            mapped_output: dict[str, object] = {}
            missing_result_fields: list[str] = []
            for raw_key, raw_path in raw_result_fields.items():
                if not isinstance(raw_key, str) or not raw_key.strip():
                    continue
                normalized_key = raw_key.strip()
                mapped_value = _extract_tool_execution_response_value(
                    scoped_payload,
                    path=raw_path,
                )
                if mapped_value is _TOOL_EXECUTION_TEMPLATE_MISSING:
                    missing_result_fields.append(
                        _format_http_json_result_field_mapping_error(
                            field_name=normalized_key,
                            raw_path=raw_path,
                        )
                    )
                    continue
                mapped_output[normalized_key] = mapped_value
            if missing_result_fields and not mapped_output:
                formatted_mappings = _format_http_json_missing_result_field_mappings(
                    missing_result_fields
                )
                payload_shape = _format_http_json_mapping_payload_shape_for_error(
                    scoped_payload
                )
                message = (
                    "HTTP JSON tool result_fields could not resolve any configured "
                    f"mapping: {formatted_mappings}; {payload_shape}."
                )
                message = _append_http_json_response_header_diagnostic_hints(
                    message,
                    response,
                )
                raise MockToolExecutionError(
                    message,
                    fatal=True,
                )
            _attach_http_json_response_request_id(
                mapped_output,
                response_request_id,
            )
            return _normalize_http_json_safe_output_shape(mapped_output)
        if isinstance(scoped_payload, dict):
            output = dict(scoped_payload)
            _attach_http_json_response_request_id(output, response_request_id)
            return _normalize_http_json_safe_output_shape(output)
        output = {
            "value": _redact_http_json_sensitive_payload_value(scoped_payload),
        }
        _attach_http_json_response_request_id(output, response_request_id)
        return output

    return runner


def _build_invalid_tool_execution_runner(
    *,
    message: str,
) -> ToolRunner:
    def runner(*, tool_input: dict[str, object], prompt: str, user_id: str) -> dict[str, object]:
        del tool_input, prompt, user_id
        raise MockToolExecutionError(message, fatal=True)

    return runner


def _build_tool_runner_from_execution_spec(
    *,
    execution_spec: object,
    fallback_runner: ToolRunner,
    default_timeout_ms: int,
    template_context: dict[str, object] | None = None,
) -> ToolRunner:
    if execution_spec is None:
        return fallback_runner
    validation_errors = _describe_tool_execution_spec_validation_errors(
        execution_spec,
        template_context=template_context,
    )
    if validation_errors:
        return _build_invalid_tool_execution_runner(
            message=f"{validation_errors[0][:1].upper()}{validation_errors[0][1:]}",
        )
    execution_kind = _normalize_named_tool_registry_component_name(
        execution_spec.get("kind")
    )
    if execution_kind == "http_json":
        return _build_http_json_tool_runner(
            execution_spec=execution_spec,
            default_timeout_ms=default_timeout_ms,
            template_context=template_context,
        )
    if execution_kind is None:
        return _build_invalid_tool_execution_runner(
            message="Invalid tool execution spec: execution.kind is required.",
        )
    return _build_invalid_tool_execution_runner(
        message=(
            "Unsupported tool execution kind: "
            f"{_format_safe_tool_execution_kind(execution_kind)}"
        ),
    )


def _resolve_tool_execution_kind_from_spec(execution_spec: object) -> str | None:
    if not isinstance(execution_spec, dict):
        return None
    return _normalize_tool_execution_kind(execution_spec.get("kind"))


def _build_tool_execution_summary_from_spec(
    execution_spec: object,
    *,
    template_context: dict[str, object] | None = None,
) -> dict[str, object] | None:
    if not isinstance(execution_spec, dict):
        return None
    execution_kind = _normalize_tool_execution_kind(execution_spec.get("kind"))
    if execution_kind != "http_json":
        return None

    summary: dict[str, object] = {
        "method": _normalize_tool_execution_http_method(
            execution_spec.get(
                "method",
                "POST" if execution_spec.get("json_body") is not None else "GET",
            )
        )
    }
    raw_url = execution_spec.get("url")
    summary_url: object = raw_url
    if _iter_tool_execution_template_variable_references(raw_url, path="url"):
        rendered_url = _render_tool_execution_template_for_static_analysis(
            raw_url,
            context=template_context,
            path="url",
        )
        if rendered_url is not _TOOL_EXECUTION_TEMPLATE_MISSING:
            summary_url = rendered_url
        elif not _is_supported_tool_execution_http_url(raw_url):
            summary_url = None
    if isinstance(summary_url, str) and summary_url.strip():
        parsed_url = urlparse(summary_url.strip())
        safe_origin = _format_safe_tool_execution_http_url_origin(parsed_url)
        if safe_origin:
            summary["url_origin"] = safe_origin
        safe_path = _format_safe_tool_execution_http_url_path(parsed_url)
        if safe_path:
            summary["url_path"] = safe_path
    raw_headers = execution_spec.get("headers")
    if isinstance(raw_headers, dict) and raw_headers:
        summary["header_count"] = len(
            [
                raw_key
                for raw_key in raw_headers
                if isinstance(raw_key, str) and raw_key.strip()
            ]
        )
    raw_query_params = execution_spec.get("query_params")
    if isinstance(raw_query_params, dict) and raw_query_params:
        summary["query_param_count"] = len(
            [
                raw_key
                for raw_key in raw_query_params
                if isinstance(raw_key, str) and raw_key.strip()
            ]
        )
    raw_json_body = execution_spec.get("json_body")
    if isinstance(raw_json_body, dict) and raw_json_body:
        summary["json_body_field_count"] = len(
            [
                raw_key
                for raw_key in raw_json_body
                if isinstance(raw_key, str) and raw_key.strip()
            ]
        )
    raw_response_path = execution_spec.get("response_path")
    if isinstance(raw_response_path, str) and raw_response_path.strip():
        summary["response_path"] = _format_http_json_mapping_path_for_error(
            raw_response_path
        )
    raw_result_fields = execution_spec.get("result_fields")
    if isinstance(raw_result_fields, dict) and raw_result_fields:
        result_field_names = tuple(
            _format_safe_tool_execution_summary_field_name(raw_key)
            for raw_key in raw_result_fields
            if isinstance(raw_key, str) and raw_key.strip()
        )
        if result_field_names:
            summary["result_field_names"] = list(result_field_names)
    return summary


def _format_safe_tool_execution_summary_url_path(raw_value: object) -> str:
    raw_path = str(raw_value).strip()
    if not raw_path:
        return ""
    path = unquote(raw_path)
    safe_segments: list[str] = []
    redact_next_segment = False
    for segment in path.split("/"):
        if not segment:
            safe_segments.append(segment)
            continue
        if redact_next_segment:
            safe_segments.append("[redacted]")
            redact_next_segment = False
            continue
        if _HTTP_JSON_ERROR_BODY_SENSITIVE_KEY_RE.fullmatch(segment):
            safe_segments.append("[redacted]")
            redact_next_segment = True
            continue
        safe_segments.append(_redact_http_json_diagnostic_text(segment))
    return "/".join(safe_segments)


def _sanitize_tool_execution_summary_value(key: str, value: object) -> object:
    normalized_key = key.strip()
    if normalized_key == "url_path" and isinstance(value, str):
        return _format_safe_tool_execution_summary_url_path(value)
    if normalized_key == "response_path" and isinstance(value, str):
        return _format_http_json_mapping_path_for_error(value)
    if normalized_key == "result_field_names" and isinstance(value, (list, tuple)):
        return [
            safe_field_name
            for safe_field_name in (
                _format_safe_tool_execution_summary_field_name(item)
                for item in value
            )
            if safe_field_name
        ]
    if isinstance(value, str):
        return _redact_tool_registry_diagnostic_value(value)
    return value


def sanitize_tool_execution_summary(
    execution_summary: object,
) -> dict[str, object] | None:
    if not isinstance(execution_summary, dict) or not execution_summary:
        return None
    sanitized_summary: dict[str, object] = {}
    for raw_key, raw_value in execution_summary.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        safe_value = _sanitize_tool_execution_summary_value(raw_key, raw_value)
        if safe_value in ("", [], ()):
            continue
        sanitized_summary[raw_key.strip()] = safe_value
    return sanitized_summary or None


def sanitize_tool_execution_diagnostics(diagnostics: object) -> tuple[str, ...]:
    if not isinstance(diagnostics, (list, tuple)):
        return ()
    safe_diagnostics = tuple(
        safe_diagnostic
        for safe_diagnostic in (
            _redact_tool_registry_diagnostic_value(diagnostic)
            for diagnostic in diagnostics
            if isinstance(diagnostic, str)
        )
        if safe_diagnostic
    )
    return tuple(dict.fromkeys(safe_diagnostics))


def _describe_tool_execution_spec_validation_error(
    execution_spec: object,
    *,
    template_context: dict[str, object] | None = None,
) -> str | None:
    validation_errors = _describe_tool_execution_spec_validation_errors(
        execution_spec,
        template_context=template_context,
    )
    return validation_errors[0] if validation_errors else None


def _describe_tool_execution_spec_validation_errors(
    execution_spec: object,
    *,
    template_context: dict[str, object] | None = None,
) -> tuple[str, ...]:
    if execution_spec is None:
        return ()
    if not isinstance(execution_spec, dict):
        return ("invalid tool execution spec: expected an object",)
    execution_kind = _normalize_named_tool_registry_component_name(
        execution_spec.get("kind")
    )
    if execution_kind is None:
        return ("invalid tool execution spec: execution.kind is required",)
    if execution_kind != "http_json":
        return (
            "unsupported tool execution kind "
            f"{_format_safe_tool_execution_kind(execution_kind)}",
        )
    raw_url = execution_spec.get("url")
    if not isinstance(raw_url, str) or not raw_url.strip():
        return ("http_json execution requires a non-empty url",)
    validation_errors: list[str] = []
    url_for_validation: object | None = raw_url
    if _iter_tool_execution_template_variable_references(raw_url, path="url"):
        rendered_url = _render_tool_execution_template_for_static_analysis(
            raw_url,
            context=template_context,
            path="url",
        )
        url_for_validation = (
            None
            if rendered_url is _TOOL_EXECUTION_TEMPLATE_MISSING
            else rendered_url
        )
    if url_for_validation is not None:
        url_error = _describe_tool_execution_http_url_validation_error(url_for_validation)
        if url_error:
            validation_errors.append(url_error)
    normalized_method: str | None = None
    if "method" in execution_spec:
        method_error = _describe_tool_execution_http_method_validation_error(
            execution_spec.get("method")
        )
        if method_error:
            validation_errors.append(method_error)
        else:
            normalized_method = _normalize_tool_execution_http_method(
                execution_spec.get("method")
            )
    if "timeout_ms" in execution_spec:
        timeout_error = _describe_tool_execution_timeout_ms_validation_error(
            execution_spec.get("timeout_ms")
        )
        if timeout_error:
            validation_errors.append(timeout_error)
    raw_headers = execution_spec.get("headers")
    if raw_headers is not None and not isinstance(raw_headers, dict):
        validation_errors.append("http_json execution headers must be an object")
    raw_query_params = execution_spec.get("query_params")
    if raw_query_params is not None and not isinstance(raw_query_params, dict):
        validation_errors.append("http_json execution query_params must be an object")
    raw_json_body = execution_spec.get("json_body")
    if raw_json_body is not None and not isinstance(raw_json_body, dict):
        validation_errors.append("http_json execution json_body must be an object")
    headers_for_validation = _resolve_tool_execution_template_value_for_static_validation(
        raw_headers,
        context=template_context,
        path="headers",
    )
    query_params_for_validation = _resolve_tool_execution_template_value_for_static_validation(
        raw_query_params,
        context=template_context,
        path="query_params",
    )
    json_body_for_validation = _resolve_tool_execution_template_value_for_static_validation(
        raw_json_body,
        context=template_context,
        path="json_body",
    )
    if normalized_method == "GET" and raw_json_body is not None:
        validation_errors.append(
            "http_json execution GET method must not define json_body; "
            "use query_params or a body-capable method"
        )
    effective_method = (
        normalized_method
        if normalized_method is not None
        else ("POST" if raw_json_body is not None else "GET")
    )
    if raw_json_body is not None and effective_method != "GET":
        validation_errors.extend(
            _describe_http_json_request_content_type_validation_errors(
                headers=headers_for_validation,
            )
        )
    validation_errors.extend(
        _describe_http_json_request_accept_validation_errors(
            headers=headers_for_validation,
        )
    )
    duplicate_query_param_error = (
        _describe_tool_execution_http_duplicate_query_param_validation_error(
            url=url_for_validation,
            query_params=query_params_for_validation,
        )
    )
    if duplicate_query_param_error:
        validation_errors.append(duplicate_query_param_error)
    raw_response_path = execution_spec.get("response_path")
    if raw_response_path is not None and not isinstance(raw_response_path, str):
        validation_errors.append("http_json execution response_path must be a string")
    if isinstance(raw_response_path, str) and not raw_response_path.strip():
        validation_errors.append(
            "http_json execution response_path must be a non-empty string when provided"
        )
    if isinstance(raw_response_path, str) and raw_response_path.strip():
        if not _is_supported_tool_execution_response_path(raw_response_path):
            validation_errors.append(
                "http_json execution response_path must use dot fields and "
                "numeric indexes"
            )
    raw_result_fields = execution_spec.get("result_fields")
    if raw_result_fields is not None and not isinstance(raw_result_fields, dict):
        validation_errors.append("http_json execution result_fields must be an object")
    for field_name, raw_mapping in (
        ("headers", raw_headers),
        ("query_params", raw_query_params),
        ("json_body", raw_json_body),
    ):
        if not isinstance(raw_mapping, dict):
            continue
        has_valid_field_name = False
        has_blank_field_name = False
        for raw_key in raw_mapping:
            if isinstance(raw_key, str) and raw_key.strip():
                has_valid_field_name = True
                continue
            has_blank_field_name = True
        if has_blank_field_name:
            validation_errors.append(
                f"http_json execution {field_name} must not include blank field names"
            )
        if raw_mapping and not has_valid_field_name:
            validation_errors.append(
                f"http_json execution {field_name} must include at least one "
                "non-empty field name when provided"
            )
    validation_errors.extend(
        _describe_tool_execution_http_value_validation_errors(
            field_name="headers",
            raw_mapping=headers_for_validation,
        )
    )
    validation_errors.extend(
        _describe_tool_execution_http_value_validation_errors(
            field_name="query_params",
            raw_mapping=query_params_for_validation,
        )
    )
    validation_errors.extend(
        _describe_tool_execution_json_body_validation_errors(json_body_for_validation)
    )
    if isinstance(raw_result_fields, dict):
        if not raw_result_fields:
            validation_errors.append(
                "http_json execution result_fields must include at least one "
                "field mapping"
            )
        has_valid_result_field_name = False
        has_blank_result_field_name = False
        for raw_key, raw_path in raw_result_fields.items():
            if not isinstance(raw_key, str) or not raw_key.strip():
                has_blank_result_field_name = True
                continue
            has_valid_result_field_name = True
            safe_result_field_path = _format_safe_tool_execution_diagnostic_path(
                f"result_fields.{raw_key.strip()}"
            )
            if isinstance(raw_path, str) and raw_path.strip():
                if not _is_supported_tool_execution_response_path(raw_path):
                    validation_errors.append(
                        f"http_json execution {safe_result_field_path} must use dot "
                        "fields and numeric indexes"
                    )
                continue
            validation_errors.append(
                f"http_json execution {safe_result_field_path} must be a non-empty "
                "string path"
            )
        if has_blank_result_field_name and has_valid_result_field_name:
            validation_errors.append(
                "http_json execution result_fields must not include blank field names"
            )
        if raw_result_fields and not has_valid_result_field_name:
            validation_errors.append(
                "http_json execution result_fields must include at least one "
                "non-empty field name"
            )
    validation_errors.extend(
        _collect_tool_execution_runtime_template_validation_errors(
            execution_spec=execution_spec,
        )
    )
    return tuple(dict.fromkeys(validation_errors))


def _build_invalid_tool_execution_diagnostics(
    *,
    messages: object,
) -> dict[str, tuple[str, ...]]:
    if not isinstance(messages, (list, tuple)):
        return _empty_tool_registry_file_diagnostics()
    normalized_messages = tuple(
        str(message).strip()
        for message in messages
        if str(message).strip()
    )
    if not normalized_messages:
        return _empty_tool_registry_file_diagnostics()
    diagnostics = _empty_tool_registry_file_diagnostics()
    diagnostics["invalid_tool_executions"] = tuple(dict.fromkeys(normalized_messages))
    return diagnostics


def _group_invalid_tool_execution_messages_by_tool(
    messages: object,
) -> dict[str, tuple[str, ...]]:
    if not isinstance(messages, (list, tuple)):
        return {}
    grouped_messages: dict[str, list[str]] = {}
    for raw_message in messages:
        message = str(raw_message).strip()
        if not message:
            continue
        tool_name, separator, detail = message.partition(":")
        if not separator:
            continue
        normalized_tool_name = normalize_tool_registry_name(tool_name)
        normalized_detail = _redact_tool_registry_diagnostic_value(detail)
        if not normalized_tool_name or not normalized_detail:
            continue
        grouped_messages.setdefault(normalized_tool_name, [])
        if normalized_detail not in grouped_messages[normalized_tool_name]:
            grouped_messages[normalized_tool_name].append(normalized_detail)
    return {
        tool_name: tuple(messages)
        for tool_name, messages in grouped_messages.items()
    }


def _collect_invalid_tool_execution_messages_from_extra_tool_specs(
    *,
    extra_tool_specs: object,
    settings: object | None = None,
) -> tuple[str, ...]:
    if not isinstance(extra_tool_specs, dict):
        return ()
    runtime_template_context = _build_tool_execution_runtime_template_context(
        settings=settings,
    )
    messages: list[str] = []
    for tool_name, spec in extra_tool_specs.items():
        if not isinstance(tool_name, str) or not isinstance(spec, dict):
            continue
        validation_errors: list[str] = []
        if "default_timeout_ms" in spec:
            timeout_error = _describe_tool_default_timeout_ms_validation_error(
                spec.get("default_timeout_ms")
            )
            if timeout_error:
                validation_errors.append(timeout_error)
        if "execution" in spec:
            validation_errors.extend(
                _describe_tool_execution_spec_validation_errors(
                    spec.get("execution"),
                    template_context=runtime_template_context,
                )
            )
        if not validation_errors:
            continue
        normalized_tool_name = normalize_tool_registry_name(tool_name) or tool_name.strip()
        messages.extend(
            f"{normalized_tool_name}: {validation_error}"
            for validation_error in validation_errors
        )
    return tuple(dict.fromkeys(messages))


def _collect_invalid_tool_execution_messages_from_override_specs(
    *,
    override_specs: object,
    base_registry: dict[str, ToolRegistration],
    settings: object | None = None,
) -> tuple[str, ...]:
    if not isinstance(override_specs, dict):
        return ()
    runtime_template_context = _build_tool_execution_runtime_template_context(
        settings=settings,
    )
    messages: list[str] = []
    for tool_name, spec in override_specs.items():
        if not isinstance(tool_name, str) or not isinstance(spec, dict):
            continue
        normalized_tool_name = normalize_tool_registry_name(tool_name)
        if not normalized_tool_name or normalized_tool_name not in base_registry:
            continue
        validation_errors: list[str] = []
        if "default_timeout_ms" in spec:
            timeout_error = _describe_tool_default_timeout_ms_validation_error(
                spec.get("default_timeout_ms")
            )
            if timeout_error:
                validation_errors.append(timeout_error)
        if "execution" in spec:
            validation_errors.extend(
                _describe_tool_execution_spec_validation_errors(
                    spec.get("execution"),
                    template_context=runtime_template_context,
                )
            )
        if not validation_errors:
            continue
        messages.extend(
            f"{normalized_tool_name}: {validation_error}"
            for validation_error in validation_errors
        )
    return tuple(dict.fromkeys(messages))


def build_tool_registry_settings_execution_diagnostics(
    *,
    settings: object | None = None,
    base_provider: ToolRegistryProvider | None = None,
) -> dict[str, tuple[str, ...]]:
    if settings is None:
        settings = get_settings()
    raw_extra_tools = getattr(settings, "tool_registry_extra_tools_json", None)
    extra_tool_specs: object = None
    if isinstance(raw_extra_tools, str) and raw_extra_tools.strip():
        try:
            parsed_extra_tool_specs = json.loads(raw_extra_tools)
        except json.JSONDecodeError:
            parsed_extra_tool_specs = None
        if isinstance(parsed_extra_tool_specs, dict):
            extra_tool_specs = parsed_extra_tool_specs

    extra_tool_messages = _collect_invalid_tool_execution_messages_from_extra_tool_specs(
        extra_tool_specs=extra_tool_specs,
        settings=settings,
    )

    known_registrations = (
        dict(base_provider.load_tool_registry())
        if base_provider is not None
        else get_default_tool_registry()
    )
    extra_tools = build_tool_registry_extra_tools_from_specs(
        extra_tool_specs=extra_tool_specs,
        settings=settings,
    )
    known_registrations = build_tool_registry(
        base_registry=known_registrations,
        overrides=extra_tools or None,
    )

    raw_overrides = getattr(settings, "tool_registry_overrides_json", None)
    override_specs: object = None
    if isinstance(raw_overrides, str) and raw_overrides.strip():
        try:
            parsed_override_specs = json.loads(raw_overrides)
        except json.JSONDecodeError:
            parsed_override_specs = None
        if isinstance(parsed_override_specs, dict):
            override_specs = parsed_override_specs

    override_messages = _collect_invalid_tool_execution_messages_from_override_specs(
        override_specs=override_specs,
        base_registry=known_registrations,
        settings=settings,
    )
    return _build_invalid_tool_execution_diagnostics(
        messages=(*extra_tool_messages, *override_messages),
    )


def build_tool_registry_extra_tools_from_file(
    *,
    registry_file: str,
    settings: object | None = None,
) -> dict[str, ToolRegistration]:
    payload = load_tool_registry_file_payload(registry_file=registry_file)
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("extra_tools"), dict):
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
    payload = load_tool_registry_file_payload(registry_file=str(resolved_path))
    if not isinstance(payload, dict):
        return {}

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
                settings=settings,
            )
        )
        return build_tool_registry_extra_tools_from_specs(
            extra_tool_specs=payload,
            settings=settings,
        )

    profile_name = get_tool_registry_profile_name_from_settings(
        settings=SimpleNamespace(
            tool_registry_profile=payload.get("profile", "default"),
        )
    )
    profile_config = build_tool_registry_profile_settings_config(profile_name=profile_name)
    disabled_tool_names = set(normalize_tool_registry_names(profile_config.disabled_tool_names))
    raw_disabled_tool_names = payload.get("disabled_tool_names")
    if isinstance(raw_disabled_tool_names, (list, tuple)):
        disabled_tool_names.update(normalize_tool_registry_names(raw_disabled_tool_names))

    composed_base_registry: dict[str, ToolRegistration] | None = None
    raw_registry_sources = payload.get("registry_sources")
    if isinstance(raw_registry_sources, (list, tuple)):
        composed_base_registry = {}
        named_sources = build_tool_registry_provider_sources_from_settings(
            settings=settings,
            named_providers={},
        )
        for child_registry_source in raw_registry_sources:
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
            if normalized_source_name in _visited_sources:
                _diagnostics["skipped_registry_sources"].append(normalized_source_name)
                continue
            source_provider = named_sources.get(normalized_source_name)
            if source_provider is None:
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
    if isinstance(raw_registry_files, (list, tuple)):
        if composed_base_registry is None:
            composed_base_registry = {}
        for child_registry_file in raw_registry_files:
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
                settings=settings,
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
    if isinstance(raw_registry_dirs, (list, tuple)):
        if composed_base_registry is None:
            composed_base_registry = {}
        for child_registry_dir in raw_registry_dirs:
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
                    settings=settings,
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
    if not isinstance(extra_tool_specs, dict):
        extra_tool_specs = payload
    _diagnostics["invalid_tool_executions"].extend(
        _collect_invalid_tool_execution_messages_from_extra_tool_specs(
            extra_tool_specs=extra_tool_specs,
            settings=settings,
        )
    )
    extra_tools = build_tool_registry_extra_tools_from_specs(
        extra_tool_specs=extra_tool_specs,
        settings=settings,
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
            settings=settings,
        )
    )
    source_overrides, disabled_tool_names = _build_registry_overrides_from_specs(
        override_specs=payload.get("overrides"),
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


def build_tool_registry_loaders_from_settings_artifacts(
    *,
    settings: object | None = None,
) -> dict[str, object]:
    if settings is None:
        settings = get_settings()
    raw_loaders = getattr(settings, "tool_registry_loaders_json", None)
    if not isinstance(raw_loaders, str) or not raw_loaders.strip():
        return {
            "loaders": {},
            "loader_diagnostics": {},
        }
    try:
        loader_specs = json.loads(raw_loaders)
    except json.JSONDecodeError:
        return {
            "loaders": {},
            "loader_diagnostics": {},
        }
    if not isinstance(loader_specs, dict):
        return {
            "loaders": {},
            "loader_diagnostics": {},
        }

    loaders: dict[str, ToolRegistryLoader] = {}
    loader_diagnostics: dict[str, dict[str, tuple[str, ...]]] = {}
    for loader_name, spec in loader_specs.items():
        if not isinstance(loader_name, str) or not isinstance(spec, dict):
            continue
        normalized_loader_name = _normalize_named_tool_registry_component_name(
            loader_name
        )
        if normalized_loader_name is None:
            continue
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
                    settings=settings,
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
                    settings=settings,
                )
            ),
        )
        loader = build_tool_registry_loader_adapter(
            spec=spec,
            settings=settings,
            named_loaders=loaders,
        )
        if loader is None:
            continue
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
    if not isinstance(raw_factories, str) or not raw_factories.strip():
        return {
            "loader_factories": {},
            "loader_factory_diagnostics": {},
        }
    try:
        factory_specs = json.loads(raw_factories)
    except json.JSONDecodeError:
        return {
            "loader_factories": {},
            "loader_factory_diagnostics": {},
        }
    if not isinstance(factory_specs, dict):
        return {
            "loader_factories": {},
            "loader_factory_diagnostics": {},
        }

    factories: dict[str, ToolRegistryLoaderFactory] = {}
    factory_diagnostics: dict[str, dict[str, tuple[str, ...]]] = {}
    for factory_name, spec in factory_specs.items():
        if not isinstance(factory_name, str) or not isinstance(spec, dict):
            continue
        normalized_factory_name = _normalize_named_tool_registry_component_name(
            factory_name
        )
        if normalized_factory_name is None:
            continue
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
                continue
            factories[normalized_factory_name] = (
                lambda settings=None, loader=loader: loader
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
            continue
        target_normalized = _normalize_named_tool_registry_component_name(target_name)
        if target_normalized in _TOOL_REGISTRY_PROFILE_CONFIGS:
            resolved = _annotate_loader_factory_profile(
                resolved,
                profile_name=target_normalized,
            )
        factories[normalized_factory_name] = resolved
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
    if not isinstance(raw_factories, str) or not raw_factories.strip():
        return {
            "provider_factories": {},
            "provider_factory_diagnostics": {},
        }
    try:
        factory_specs = json.loads(raw_factories)
    except json.JSONDecodeError:
        return {
            "provider_factories": {},
            "provider_factory_diagnostics": {},
        }
    if not isinstance(factory_specs, dict):
        return {
            "provider_factories": {},
            "provider_factory_diagnostics": {},
        }

    factories: dict[str, ToolRegistryProviderFactory] = {}
    factory_diagnostics: dict[str, dict[str, tuple[str, ...]]] = {}
    for factory_name, spec in factory_specs.items():
        if not isinstance(factory_name, str) or not isinstance(spec, dict):
            continue
        normalized_factory_name = _normalize_named_tool_registry_component_name(
            factory_name
        )
        if normalized_factory_name is None:
            continue
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
                continue
            factories[normalized_factory_name] = (
                lambda settings=None, provider=provider: provider
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
            continue
        target_normalized = _normalize_named_tool_registry_component_name(target_name)
        if target_normalized in _TOOL_REGISTRY_PROFILE_CONFIGS:
            resolved = _annotate_provider_factory_profile(
                resolved,
                profile_name=target_normalized,
            )
        factories[normalized_factory_name] = resolved
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
    spec: dict[str, object],
    settings: object | None = None,
    named_loaders: dict[str, ToolRegistryLoader] | None = None,
) -> ToolRegistryLoader | None:
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
    if isinstance(raw_disabled_tool_names, (list, tuple)):
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
        base_provider = provider_factory(settings)
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
    if isinstance(raw_disabled_tool_names, (list, tuple)):
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
    return build_tool_registry_provider(
        provider=base_provider,
        loader=base_loader,
        overrides=build_tool_registry(
            base_registry=profile_config.overrides,
            overrides=build_tool_registry(
                base_registry=source_overrides,
                overrides=extra_tools or None,
            )
            or None,
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
    raw_providers = getattr(settings, "tool_registry_providers_json", None)
    if not isinstance(raw_providers, str) or not raw_providers.strip():
        return {
            "providers": {},
            "provider_diagnostics": {},
        }
    try:
        provider_specs = json.loads(raw_providers)
    except json.JSONDecodeError:
        return {
            "providers": {},
            "provider_diagnostics": {},
        }
    if not isinstance(provider_specs, dict):
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
    for provider_name, spec in provider_specs.items():
        if not isinstance(provider_name, str) or not isinstance(spec, dict):
            continue
        normalized_provider_name = _normalize_named_tool_registry_component_name(
            provider_name
        )
        if normalized_provider_name is None:
            continue
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
                    settings=settings,
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
                    settings=settings,
                )
            ),
        )
        provider = build_tool_registry_provider_adapter(
            spec=spec,
            settings=settings,
            named_loaders=named_loaders,
            named_providers=providers,
        )
        if provider is None:
            continue
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
    if not isinstance(raw_sources, str) or not raw_sources.strip():
        return {
            "sources": {},
            "source_diagnostics": {},
        }
    try:
        source_specs = json.loads(raw_sources)
    except json.JSONDecodeError:
        return {
            "sources": {},
            "source_diagnostics": {},
        }
    if not isinstance(source_specs, dict):
        return {
            "sources": {},
            "source_diagnostics": {},
        }

    loader_artifacts: dict[str, object] | None = None
    provider_artifacts: dict[str, object] | None = None
    loader_factory_artifacts: dict[str, object] | None = None
    provider_factory_artifacts: dict[str, object] | None = None
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
    sources: dict[str, ToolRegistryProvider] = {}
    source_diagnostics: dict[str, dict[str, tuple[str, ...]]] = {}
    for source_name, spec in source_specs.items():
        if not isinstance(source_name, str) or not isinstance(spec, dict):
            continue
        normalized_source_name = get_tool_registry_provider_source_name_from_settings(
            settings=SimpleNamespace(
                tool_registry_provider_source=source_name,
            )
        )
        adapter_keys = {
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
        if any(key in spec for key in adapter_keys):
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
                        settings=settings,
                        provider_source_name=normalized_source_name,
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
                        settings=settings,
                    )
                ),
                settings_execution_diagnostics,
            )
            provider = build_tool_registry_provider_adapter(
                spec=spec,
                settings=settings,
                provider_source_name=normalized_source_name,
                named_loaders=named_loaders,
                named_providers=named_providers,
                named_sources=sources,
            )
            if provider is None:
                source_diagnostics[normalized_source_name] = diagnostics
                continue
            sources[normalized_source_name] = provider
            source_diagnostics[normalized_source_name] = diagnostics
            continue

        extra_tools = build_tool_registry_extra_tools_from_specs(
            extra_tool_specs=spec,
            settings=settings,
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
                    settings=settings,
                )
            ),
            settings_execution_diagnostics,
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
    if not isinstance(raw_extra_tools, str) or not raw_extra_tools.strip():
        return {}
    try:
        extra_tool_specs = json.loads(raw_extra_tools)
    except json.JSONDecodeError:
        return {}
    if not isinstance(extra_tool_specs, dict):
        return {}

    runtime_template_context = _build_tool_execution_runtime_template_context(
        settings=settings,
    )
    extra_tools: dict[str, ToolRegistration] = {}
    for name, spec in extra_tool_specs.items():
        if not isinstance(name, str) or not isinstance(spec, dict):
            continue
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
    if not isinstance(raw_overrides, str) or not raw_overrides.strip():
        return ToolRegistrySettingsConfig(
            overrides=dict(extra_tools),
            disabled_tool_names=normalize_tool_registry_names(profile_config.disabled_tool_names),
        )
    try:
        override_specs = json.loads(raw_overrides)
    except json.JSONDecodeError:
        return ToolRegistrySettingsConfig(
            overrides=dict(extra_tools),
            disabled_tool_names=normalize_tool_registry_names(profile_config.disabled_tool_names),
        )
    if not isinstance(override_specs, dict):
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
        trace_step=sanitize_tool_registry_diagnostics_artifact_payload(
            service_action.get("trace_step")
        )
        if isinstance(service_action.get("trace_step"), dict)
        else None,
        trace_event=sanitize_tool_registry_diagnostics_artifact_payload(
            service_action.get("trace_event")
        )
        if isinstance(service_action.get("trace_event"), dict)
        else None,
        persist_force=bool(service_action.get("persist_force")),
        kwargs=sanitize_tool_registry_diagnostics_artifact_payload(
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
            trace_step=sanitize_tool_registry_diagnostics_artifact_payload(
                diagnostics_runtime_payload.get("trace_step")
            )
            if isinstance(diagnostics_runtime_payload.get("trace_step"), dict)
            else None,
            trace_event=sanitize_tool_registry_diagnostics_artifact_payload(
                diagnostics_runtime_payload.get("trace_event")
            )
            if isinstance(diagnostics_runtime_payload.get("trace_event"), dict)
            else None,
            audit_detail=sanitize_tool_registry_diagnostics_artifact_payload(
                diagnostics_runtime_payload.get("audit_detail")
            )
            if isinstance(diagnostics_runtime_payload.get("audit_detail"), dict)
            else None,
        ),
        audit_event=sanitize_tool_registry_diagnostics_artifact_payload(
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
            trace_steps.append(trace_step)
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


def build_tool_registry_provider(
    *,
    provider: ToolRegistryProvider | None = None,
    loader: ToolRegistryLoader | None = None,
    overrides: dict[str, ToolRegistration] | None = None,
    disabled_tool_names: tuple[str, ...] = (),
) -> ToolRegistryProvider:
    if provider is not None and not overrides and not disabled_tool_names:
        return provider
    if provider is None and loader is None and not overrides and not disabled_tool_names:
        return get_default_tool_registry_provider()
    return ConfiguredToolRegistryProvider(
        provider=provider,
        loader=loader,
        overrides=overrides,
        disabled_tool_names=disabled_tool_names,
    )


def build_tool_registry(
    *,
    base_registry: dict[str, ToolRegistration] | None = None,
    overrides: dict[str, ToolRegistration] | None = None,
    disabled_tool_names: tuple[str, ...] | None = None,
) -> dict[str, ToolRegistration]:
    registry = get_default_tool_registry() if base_registry is None else dict(base_registry)
    if overrides:
        registry.update(overrides)
    if disabled_tool_names:
        for name in normalize_tool_registry_names(disabled_tool_names):
            registry.pop(name, None)
    return registry


def get_registered_tool_names(
    *,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> tuple[str, ...]:
    provider_stack = resolve_tool_registry_provider(
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    return tuple(sorted(provider_stack.load_tool_registry()))


def resolve_tool_registry_provider(
    *,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> ToolRegistryProvider:
    if registry is not None:
        return StaticToolRegistryProvider(registry=dict(registry))
    return build_tool_registry_provider(
        provider=registry_provider,
        loader=registry_loader,
    )


def resolve_tool_registration(
    name: str,
    *,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> ToolRegistration | None:
    provider_stack = resolve_tool_registry_provider(
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    lookup_name = normalize_tool_registry_name(name)
    return provider_stack.load_tool_registry().get(lookup_name)


def ensure_tool_registration(
    name: str,
    *,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> ToolRegistration:
    registration = resolve_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if registration is None:
        raise MockToolExecutionError(f"Unknown tool: {name}", fatal=True)
    return registration


def maybe_raise_tool_execution_error(*, name: str, prompt: str, attempt: int) -> None:
    del name
    normalized = prompt.strip().lower()

    if "[tool-fatal]" in normalized or "[mock-tool-fatal]" in normalized:
        raise MockToolExecutionError(
            "Tool fatal error: planner contract validation failed.",
            fatal=True,
        )

    if ("[tool-error]" in normalized or "[mock-tool-error]" in normalized) and attempt == 0:
        raise MockToolExecutionError(
            "Tool transient error: plan source unavailable on first attempt.",
            fatal=False,
        )


def maybe_raise_mock_tool_execution_error(*, name: str, prompt: str, attempt: int) -> None:
    maybe_raise_tool_execution_error(
        name=name,
        prompt=prompt,
        attempt=attempt,
    )


def build_tool_runtime_context(
    *,
    name: str,
    prompt: str,
    user_id: str,
    attempt: int,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> ToolRuntimeContext:
    registration = ensure_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    canonical_name = registration.name
    requires_user_context = tool_requires_user_context(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    effective_user_id = user_id if requires_user_context else ""
    return ToolRuntimeContext(
        name=canonical_name,
        prompt=prompt,
        user_id=effective_user_id,
        attempt=attempt,
        registration=registration,
        retryable_by_default=is_tool_retryable_by_default(
            canonical_name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        default_timeout_ms=get_tool_default_timeout_ms(
            canonical_name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        requires_user_context=requires_user_context,
    )


def _normalize_tool_input_for_registration(
    *,
    name: str,
    tool_input: dict[str, object],
    registration: ToolRegistration,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    if get_tool_semantic_kind(name=name, registration=registration) != "task_planner":
        return tool_input
    if not isinstance(tool_input.get("planned_tool_names"), (list, tuple)):
        return tool_input
    raw_planned_tool_names = _normalize_planned_tool_names(tool_input.get("planned_tool_names"))
    if not raw_planned_tool_names:
        return tool_input

    existing_labels = tool_input.get("planned_tool_labels")
    planned_tool_names: list[str] = []
    planned_tool_labels: list[str] = []
    planned_tool_kinds: list[str] = []
    for idx, planned_tool_name in enumerate(raw_planned_tool_names):
        planned_registration = resolve_tool_registration(
            planned_tool_name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        semantic_kind = get_tool_semantic_kind(
            name=planned_tool_name,
            registration=planned_registration,
        )
        if semantic_kind == "task_planner":
            continue
        planned_tool_names.append(planned_tool_name)
        label = ""
        if isinstance(existing_labels, (list, tuple)) and idx < len(existing_labels):
            label = str(existing_labels[idx]).strip()
        if not label:
            label = get_tool_display_name_from_registration(
                name=planned_tool_name,
                registration=planned_registration,
            )
        planned_tool_labels.append(label)
        planned_tool_kinds.append(semantic_kind or "")

    normalized_input = dict(tool_input)
    normalized_input["planned_tool_names"] = list(planned_tool_names)
    normalized_input["planned_tool_labels"] = planned_tool_labels
    normalized_input["planned_tool_kinds"] = planned_tool_kinds
    return normalized_input


def build_tool_runtime_input(
    *,
    name: str,
    tool_input: dict[str, object],
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if resolved_registration is None:
        return dict(tool_input)
    return _normalize_tool_input_for_registration(
        name=canonical_name,
        tool_input=dict(tool_input),
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )


def build_tool_visible_input(
    *,
    name: str,
    tool_input: dict[str, object],
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    normalized_tool_input = build_tool_runtime_input(
        name=canonical_name,
        tool_input=tool_input,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if (
        resolved_registration is not None
        and _normalize_tool_execution_kind(resolved_registration.execution_kind) == "http_json"
    ):
        safe_tool_input = _redact_http_json_sensitive_payload_value(normalized_tool_input)
        if isinstance(safe_tool_input, dict):
            return safe_tool_input
    return normalized_tool_input


def _with_action_step_tool_input(
    action_step: dict[str, object],
    *,
    tool_input: dict[str, object],
) -> dict[str, object]:
    meta = action_step.get("meta")
    if not isinstance(meta, dict):
        return action_step
    tool_meta = meta.get("tool")
    if not isinstance(tool_meta, dict):
        return action_step
    return {
        **action_step,
        "meta": {
            **meta,
            "tool": {
                **tool_meta,
                "input": tool_input,
            },
        },
    }


def build_tool_result_preview(
    *,
    name: str,
    output: dict[str, object],
    registry: dict[str, ToolRegistration] | None = None,
    registration: ToolRegistration | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object] | None:
    resolved_registration = registration or resolve_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if resolved_registration is None:
        return output
    if not resolved_registration.supports_result_preview:
        return None
    normalized_output = _normalize_tool_result_projection_output(
        output,
        registration=resolved_registration,
    )
    result_preview_keys = get_tool_effective_result_preview_keys(
        name=name,
        registration=resolved_registration,
    )
    semantic_kind = get_tool_semantic_kind(
        name=name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if result_preview_keys:
        preview = {
            key: normalized_output[key]
            for key in result_preview_keys
            if key in normalized_output
        }
        if semantic_kind == "task_planner":
            normalized_steps = _normalize_tool_result_plan_steps(preview.get("steps"))
            if normalized_steps:
                preview["steps"] = normalized_steps
        return preview
    if semantic_kind == "task_planner":
        task_planner_output = dict(normalized_output)
        normalized_steps = _normalize_tool_result_plan_steps(
            task_planner_output.get("steps")
        )
        if normalized_steps:
            task_planner_output["steps"] = normalized_steps
        return task_planner_output
    return normalized_output


def build_tool_result_output(
    *,
    name: str,
    output: dict[str, object],
    registry: dict[str, ToolRegistration] | None = None,
    registration: ToolRegistration | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    resolved_registration = registration or resolve_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if resolved_registration is None:
        return output
    normalized_source_output = _normalize_tool_result_projection_output(
        output,
        registration=resolved_registration,
    )
    result_output_keys = get_tool_effective_result_output_keys(
        name=name,
        registration=resolved_registration,
    )
    semantic_kind = get_tool_semantic_kind(
        name=name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if not result_output_keys:
        if semantic_kind == "task_planner":
            normalized_output = dict(normalized_source_output)
            normalized_steps = _normalize_tool_result_plan_steps(
                normalized_output.get("steps")
            )
            if normalized_steps:
                normalized_output["steps"] = normalized_steps
            return normalized_output
        return normalized_source_output
    normalized_output = {
        key: normalized_source_output[key]
        for key in result_output_keys
        if key in normalized_source_output
    }
    if semantic_kind == "task_planner":
        normalized_steps = _normalize_tool_result_plan_steps(normalized_output.get("steps"))
        if normalized_steps:
            normalized_output["steps"] = normalized_steps
    return normalized_output


def _normalize_tool_result_plan_steps(raw_steps: object) -> list[str]:
    if not isinstance(raw_steps, (list, tuple)):
        return []
    normalized_steps: list[str] = []
    for raw_step in raw_steps:
        if not isinstance(raw_step, str):
            continue
        step = raw_step.strip()
        if step:
            normalized_steps.append(step)
    return normalized_steps


def _summarize_generic_tool_result_payload(payload: dict[str, object]) -> str | None:
    parts: list[str] = []
    for key, value in payload.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        safe_key = _format_safe_tool_execution_summary_field_name(normalized_key)
        if safe_key == "[redacted]":
            continue
        if isinstance(value, bool):
            parts.append(f"{safe_key}={'true' if value else 'false'}")
            continue
        if isinstance(value, (int, float)):
            parts.append(f"{safe_key}={value}")
            continue
        if isinstance(value, str):
            normalized_value = value.strip()
            if normalized_value:
                safe_value = _HTTP_JSON_ERROR_BODY_SENSITIVE_ASSIGNMENT_RE.sub(
                    lambda match: f"{match.group(1)}[redacted]",
                    normalized_value,
                )
                parts.append(f"{safe_key}={safe_value}")
            continue
    if not parts:
        return None
    return ", ".join(parts[:3])


def build_tool_result_summary(
    *,
    name: str,
    output: dict[str, object],
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> str | None:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if resolved_registration is None:
        return None
    effective_result_output_keys = get_tool_effective_result_output_keys(
        name=canonical_name,
        registration=resolved_registration,
    )
    if not effective_result_output_keys:
        return None
    outward_output = build_tool_result_output(
        name=canonical_name,
        output=output,
        registry=registry,
        registration=resolved_registration,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    resolved_display_name = display_name or get_tool_observation_display_name_from_registration(
        name=canonical_name,
        registration=resolved_registration,
    )
    runtime_semantic_kind = _get_tool_runtime_trace_semantic_kind(
        name=canonical_name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    semantic_family = get_tool_semantic_kind(
        name=canonical_name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )

    plan = outward_output.get("plan")
    if isinstance(plan, str) and plan.strip():
        return f"Planned steps - {plan.strip()}."
    steps = _normalize_tool_result_plan_steps(outward_output.get("steps"))
    if steps:
        return f"Planned steps - {' -> '.join(steps)}."

    expression = outward_output.get("expression")
    result = outward_output.get("result")
    request_id = _get_safe_http_json_request_id_display_value(
        outward_output.get("request_id")
    )
    if isinstance(expression, str) and expression.strip() and result is not None:
        if isinstance(request_id, str) and request_id.strip():
            return (
                f"Calculated {expression.strip()} = {result} "
                f"(request id {request_id.strip()})."
            )
        return f"Calculated {expression.strip()} = {result}."
    if (
        semantic_family == "local_calculator"
        or (
            result is not None
            and semantic_family is None
            and runtime_semantic_kind is None
            and (
                _label_implies_real_calc_summary(tool_name)
                or _label_implies_real_calc_summary(display_name)
            )
        )
    ) and result is not None:
        if isinstance(request_id, str) and request_id.strip():
            return f"Calculated result = {result} (request id {request_id.strip()})."
        return f"Calculated result = {result}."

    hit_count = _normalize_nonnegative_int_count_value(outward_output.get("hit_count"))
    knowledge_base_id = outward_output.get("knowledge_base_id")
    if hit_count is not None:
        hit_label = "hit" if hit_count == 1 else "hits"
        if (
            runtime_semantic_kind == "knowledge_retrieval"
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

    documents_total = _normalize_nonnegative_int_count_value(
        outward_output.get("documents_total")
    )
    if documents_total is not None:
        document_label = "document" if documents_total == 1 else "documents"
        if isinstance(request_id, str) and request_id.strip():
            return (
                f"Retrieved {documents_total} {document_label} "
                f"(request id {request_id.strip()})."
            )
        return f"Retrieved {documents_total} {document_label}."

    generic_payload_summary = _summarize_generic_tool_result_payload(outward_output)
    if generic_payload_summary:
        return f"{resolved_display_name} output - {generic_payload_summary}."
    return None


def build_tool_runtime_semantics_meta(
    *,
    name: str,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if resolved_registration is None:
        return {}
    semantic_kind = _get_tool_runtime_trace_semantic_kind(
        name=canonical_name,
        registration=resolved_registration,
    )
    semantic_family = get_tool_semantic_kind(
        name=canonical_name,
        registration=resolved_registration,
    )
    effective_result_preview_keys = get_tool_effective_result_preview_keys(
        name=canonical_name,
        registration=resolved_registration,
    )
    effective_result_output_keys = get_tool_effective_result_output_keys(
        name=canonical_name,
        registration=resolved_registration,
    )
    meta: dict[str, object] = {
        "kind": resolved_registration.kind,
        "semantic_kind": semantic_kind,
        "supports_result_preview": resolved_registration.supports_result_preview,
        "effective_result_preview_keys": list(effective_result_preview_keys),
    }
    execution_kind = _normalize_tool_execution_kind(resolved_registration.execution_kind)
    if execution_kind is not None:
        meta["execution_kind"] = execution_kind
    execution_summary = sanitize_tool_execution_summary(
        resolved_registration.execution_summary,
    )
    if execution_summary is not None:
        meta["execution_summary"] = execution_summary
    execution_diagnostics = sanitize_tool_execution_diagnostics(
        resolved_registration.execution_diagnostics,
    )
    if execution_diagnostics:
        meta["execution_diagnostics"] = list(execution_diagnostics)
    if semantic_family and semantic_family != semantic_kind:
        meta["semantic_family"] = semantic_family
    if effective_result_output_keys:
        meta["effective_result_output_keys"] = list(effective_result_output_keys)
    return meta


def tool_requires_user_context(
    name: str,
    *,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> bool:
    registration = resolve_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if registration is None:
        return True
    return registration.requires_user_context


def is_tool_retryable_by_default(
    name: str,
    *,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> bool:
    registration = resolve_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if registration is None:
        return True
    return registration.retryable_by_default


def get_tool_default_timeout_ms(
    name: str,
    *,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> int:
    registration = resolve_tool_registration(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if registration is None:
        return 3_000
    return registration.default_timeout_ms


def compute_tool_retry_decision(*, ctx: ToolRuntimeContext, exc: MockToolExecutionError) -> bool:
    max_retry = 1 if ctx.retryable_by_default else 0
    return (not exc.fatal) and ctx.attempt < max_retry


def build_tool_end_payload(
    *,
    name: str,
    task_id: str,
    step_id: str,
    output: dict[str, object],
    retry_count: int,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    outward_output = build_tool_result_output(
        name=canonical_name,
        output=output,
        registry=registry,
        registration=resolved_registration,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    payload = {
        "task_id": task_id,
        "step_id": step_id,
        "status": "done",
        "latency_ms": max(
            1,
            (
                resolved_registration.default_timeout_ms
                if resolved_registration is not None
                else get_tool_default_timeout_ms(canonical_name)
            )
            // 250,
        ),
        "output_preview": build_tool_result_preview(
            name=canonical_name,
            output=outward_output,
            registry=registry,
            registration=resolved_registration,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        **build_tool_runtime_semantics_meta(
            name=canonical_name,
            registration=resolved_registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "retry_count": retry_count,
    }
    effective_result_output_keys = get_tool_effective_result_output_keys(
        name=canonical_name,
        registration=resolved_registration,
    )
    if effective_result_output_keys:
        payload["output"] = outward_output
        result_summary = build_tool_result_summary(
            name=canonical_name,
            output=output,
            registry=registry,
            registration=resolved_registration,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        if result_summary:
            payload["result_summary"] = result_summary
    return payload


def build_tool_success_meta(
    *,
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object],
    retry_count: int,
    last_error: str | None,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    safe_last_error = (
        _normalize_tool_error_message_for_registration(
            last_error,
            registration=resolved_registration,
        )
        if isinstance(last_error, str)
        else last_error
    )
    normalized_tool_input = build_tool_visible_input(
        name=canonical_name,
        tool_input=tool_input,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    outward_output = build_tool_result_output(
        name=canonical_name,
        output=output,
        registry=registry,
        registration=resolved_registration,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    result_summary = build_tool_result_summary(
        name=canonical_name,
        output=output,
        display_name=display_name,
        registry=registry,
        registration=resolved_registration,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    return {
        "tool": {
            "name": canonical_name,
            "label": display_name
            or get_tool_execution_display_name_from_registration(
                name=canonical_name,
                registration=resolved_registration,
            ),
            "input": normalized_tool_input,
            "output": outward_output,
            "output_preview": build_tool_result_preview(
                name=canonical_name,
                output=outward_output,
                registry=registry,
                registration=resolved_registration,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
            "status": "done",
            "retry_count": retry_count,
            "error": safe_last_error,
            **({"result_summary": result_summary} if result_summary else {}),
            **build_tool_runtime_semantics_meta(
                name=canonical_name,
                registration=resolved_registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        },
    }


def _normalize_tool_error_message_for_registration(
    error_message: str,
    *,
    registration: ToolRegistration | None,
) -> str:
    if (
        registration is not None
        and _normalize_tool_execution_kind(registration.execution_kind) == "http_json"
    ):
        return _redact_http_json_diagnostic_text(error_message)
    return error_message


def build_tool_error_meta(
    *,
    name: str,
    tool_input: dict[str, object],
    retry_count: int,
    error_message: str,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    safe_error_message = _normalize_tool_error_message_for_registration(
        error_message,
        registration=resolved_registration,
    )
    normalized_tool_input = build_tool_visible_input(
        name=canonical_name,
        tool_input=tool_input,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    return {
        "tool": {
            "name": canonical_name,
            "label": display_name
            or get_tool_execution_display_name_from_registration(
                name=canonical_name,
                registration=resolved_registration,
            ),
            "input": normalized_tool_input,
            "status": "error",
            "retry_count": retry_count,
            "error": safe_error_message,
            **build_tool_runtime_semantics_meta(
                name=canonical_name,
                registration=resolved_registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        },
    }


def build_tool_start_payload(
    *,
    task_id: str,
    step_id: str,
    name: str,
    tool_input: dict[str, object],
    retry_count: int,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    normalized_tool_input = build_tool_visible_input(
        name=canonical_name,
        tool_input=tool_input,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    return {
        "task_id": task_id,
        "step_id": step_id,
        "name": canonical_name,
        "display_name": display_name
        or get_tool_execution_display_name_from_registration(
            name=canonical_name,
            registration=resolved_registration,
        ),
        "input": normalized_tool_input,
        **build_tool_runtime_semantics_meta(
            name=canonical_name,
            registration=resolved_registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "retry_count": retry_count,
    }


def build_tool_error_payload(
    *,
    name: str | None = None,
    task_id: str,
    step_id: str,
    error_message: str,
    retry_count: int,
    latency_ms: int = 12,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    semantic_meta: dict[str, object] = {}
    normalized_name = (
        normalize_tool_registry_name(name) if isinstance(name, str) and name.strip() else None
    )
    if normalized_name is not None:
        resolved_registration = registration or resolve_tool_registration(
            normalized_name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        error_message = _normalize_tool_error_message_for_registration(
            error_message,
            registration=resolved_registration,
        )
        semantic_meta = build_tool_runtime_semantics_meta(
            name=normalized_name,
            registration=resolved_registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
    else:
        error_message = _normalize_tool_error_message_for_registration(
            error_message,
            registration=registration,
        )
    return {
        "task_id": task_id,
        "step_id": step_id,
        "status": "error",
        "latency_ms": latency_ms,
        "output_preview": {"error": error_message},
        **semantic_meta,
        "retry_count": retry_count,
        "error": error_message,
    }


def build_tool_phase(attempt: int) -> str:
    return "tool_running" if attempt == 0 else "tool_retry"


def build_tool_execution_policy(ctx: ToolRuntimeContext) -> dict[str, object]:
    return {
        "max_retry": 1 if ctx.retryable_by_default else 0,
        "latency_ms": max(1, ctx.default_timeout_ms // 250),
        "effective_user_id": ctx.user_id,
    }


def build_action_step_initial_meta(
    *,
    name: str,
    tool_input: dict[str, object],
    model: str,
    label: str,
    token_count: int,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    normalized_tool_input = build_tool_visible_input(
        name=canonical_name,
        tool_input=tool_input,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    return {
        "model": model,
        "step_type": "tool_call",
        "label": label,
        "retryCount": 0,
        "tokens": token_count,
        "cost_estimate": None,
        "tool": {
            "name": canonical_name,
            "label": display_name
            or get_tool_execution_display_name_from_registration(
                name=canonical_name,
                registration=resolved_registration,
            ),
            "input": normalized_tool_input,
            "status": "running",
            "retry_count": 0,
            **build_tool_runtime_semantics_meta(
                name=canonical_name,
                registration=resolved_registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        },
    }


def build_action_step_initial_step(
    *,
    step_id: str,
    seq: int,
    name: str,
    meta: dict[str, object],
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    tool_meta = meta.get("tool") if isinstance(meta.get("tool"), dict) else None
    display_name = (
        str(tool_meta.get("label")).strip()
        if isinstance(tool_meta, dict) and isinstance(tool_meta.get("label"), str)
        else get_tool_execution_display_name_from_registration(
            name=name,
            registration=registration
            or resolve_tool_registration(
                name,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        )
    )
    return {
        "id": step_id,
        "seq": seq,
        "type": "action",
        "content": f"Tool running: {display_name}",
        "meta": meta,
    }


def build_tool_step_success_update(
    *,
    action_step: dict[str, object],
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object],
    retry_count: int,
    token_count: int,
    last_error: str | None,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    tool_meta = action_step.get("meta") if isinstance(action_step, dict) else None
    tool_obj = (
        tool_meta.get("tool")
        if isinstance(tool_meta, dict) and isinstance(tool_meta.get("tool"), dict)
        else None
    )
    resolved_display_name = display_name or (
        str(tool_obj.get("label")).strip()
        if isinstance(tool_obj, dict) and isinstance(tool_obj.get("label"), str)
        else get_tool_execution_display_name_from_registration(
            name=name,
            registration=registration
            or resolve_tool_registration(
                name,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        )
    )
    return {
        **action_step,
        "content": f"Tool done: {resolved_display_name}",
        "meta": {
            **dict(action_step.get("meta", {})),
            "step_type": "tool_call",
            "retryCount": retry_count,
            "tokens": token_count,
            **build_tool_success_meta(
                name=name,
                tool_input=tool_input,
                output=output,
                retry_count=retry_count,
                last_error=last_error,
                display_name=resolved_display_name,
                registration=registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        },
    }


def build_tool_step_error_update(
    *,
    action_step: dict[str, object],
    name: str,
    tool_input: dict[str, object],
    retry_count: int,
    token_count: int,
    error_message: str,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    tool_meta = action_step.get("meta") if isinstance(action_step, dict) else None
    tool_obj = (
        tool_meta.get("tool")
        if isinstance(tool_meta, dict) and isinstance(tool_meta.get("tool"), dict)
        else None
    )
    resolved_display_name = display_name or (
        str(tool_obj.get("label")).strip()
        if isinstance(tool_obj, dict) and isinstance(tool_obj.get("label"), str)
        else get_tool_execution_display_name_from_registration(
            name=name,
            registration=registration
            or resolve_tool_registration(
                name,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        )
    )
    sanitized_action_step = sanitize_tool_registry_diagnostics_artifact_payload(
        action_step
    )
    assert isinstance(sanitized_action_step, dict)
    sanitized_meta = sanitize_tool_registry_diagnostics_artifact_payload(
        dict(sanitized_action_step.get("meta", {}))
    )
    assert isinstance(sanitized_meta, dict)
    return {
        **sanitized_action_step,
        "content": f"Tool error: {resolved_display_name}",
        "meta": {
            **sanitized_meta,
            "step_type": "tool_call",
            "retryCount": retry_count,
            "tokens": token_count,
            **build_tool_error_meta(
                name=name,
                tool_input=tool_input,
                retry_count=retry_count,
                error_message=error_message,
                display_name=resolved_display_name,
                registration=registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        },
    }


def build_tool_attempt_start_events(
    *,
    task_id: str,
    step_id: str,
    name: str,
    tool_input: dict[str, object],
    attempt: int,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, dict[str, object]]:
    return {
        "tool_start": build_tool_start_payload(
            task_id=task_id,
            step_id=step_id,
            name=name,
            tool_input=tool_input,
            retry_count=attempt,
            display_name=display_name,
            registration=registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "state": {
            "task_id": task_id,
            "phase": build_tool_phase(attempt),
        },
    }


def build_tool_attempt_bundle(
    *,
    task_id: str,
    step_id: str,
    name: str,
    tool_input: dict[str, object],
    prompt: str,
    user_id: str,
    attempt: int,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    runtime_ctx = build_tool_runtime_context(
        name=name,
        prompt=prompt,
        user_id=user_id,
        attempt=attempt,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    return {
        "normalized_tool_input": build_tool_runtime_input(
            name=runtime_ctx.name,
            tool_input=tool_input,
            registration=runtime_ctx.registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "start_events": build_tool_attempt_start_events(
            task_id=task_id,
            step_id=step_id,
            name=runtime_ctx.name,
            tool_input=tool_input,
            attempt=attempt,
            display_name=get_tool_execution_display_name_from_registration(
                name=runtime_ctx.registration.name,
                registration=runtime_ctx.registration,
            ),
            registration=runtime_ctx.registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "runtime_ctx": runtime_ctx,
        "runtime_policy": build_tool_execution_policy(runtime_ctx),
    }


def build_tool_attempt_execution(
    *,
    task_id: str,
    iteration_ctx: dict[str, object],
    action_step: dict[str, object],
    attempt_bundle: dict[str, object],
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object] | None,
    exc: MockToolExecutionError | None,
    token_count: int,
    last_error: str | None,
    model: str,
    rag_step_id: str,
    rag_token_count: int,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    return build_tool_plan_item_execution(
        task_id=task_id,
        iteration_ctx=iteration_ctx,
        action_step=action_step,
        runtime_ctx=attempt_bundle["runtime_ctx"],
        name=attempt_bundle["runtime_ctx"].name,
        tool_input=tool_input,
        output=output,
        exc=exc,
        token_count=token_count,
        last_error=last_error,
        model=model,
        rag_step_id=rag_step_id,
        rag_token_count=rag_token_count,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )


def build_tool_attempt_loop_result(
    *,
    attempt_execution: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_attempt_loop_result_payload(
        {
            "tool_end_event": attempt_execution["tool_end_event"],
            "error_event": attempt_execution["error_event"],
            "retryable": attempt_execution["retryable"],
            "next_action_step": attempt_execution["next_action_step"],
            "last_error": attempt_execution["last_error"],
            "plan_item_result": attempt_execution["plan_item_result"],
            "postprocess": attempt_execution["postprocess"],
            "success_effects": attempt_execution["success_effects"],
            "terminal_effects": attempt_execution["terminal_effects"],
        }
    )


def _sanitize_tool_plan_attempt_loop_result_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = dict(payload)
    for key in (
        "tool_end_event",
        "error_event",
        "next_action_step",
        "last_error",
        "plan_item_result",
        "terminal_effects",
    ):
        if key in sanitized:
            sanitized[key] = sanitize_tool_registry_diagnostics_artifact_payload(
                sanitized[key]
            )
    return sanitized


def _sanitize_tool_plan_retry_loop_result_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = dict(payload)
    for key in ("trace_event", "terminal_effects"):
        if key in sanitized:
            sanitized[key] = sanitize_tool_registry_diagnostics_artifact_payload(
                sanitized[key]
            )
    return sanitized


def _sanitize_tool_plan_loop_terminal_result_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = dict(payload)
    if "terminal_effects" in sanitized:
        sanitized["terminal_effects"] = sanitize_tool_registry_diagnostics_artifact_payload(
            sanitized["terminal_effects"]
        )
    return sanitized


def build_tool_attempt_loop_terminal_result(
    *,
    loop_result: dict[str, object],
) -> dict[str, object]:
    sanitized_loop_result = _sanitize_tool_plan_attempt_loop_result_payload(loop_result)
    terminal_effects = sanitized_loop_result["terminal_effects"]
    return _sanitize_tool_plan_loop_terminal_result_payload(
        {
            "should_return": terminal_effects is not None,
            "terminal_effects": terminal_effects,
        }
    )


def build_tool_plan_item_retry_loop_result(
    *,
    loop_result: dict[str, object],
) -> dict[str, object]:
    sanitized_loop_result = _sanitize_tool_plan_attempt_loop_result_payload(loop_result)
    success_effects = sanitized_loop_result["success_effects"]
    terminal_effects = sanitized_loop_result["terminal_effects"]
    trace_event = (
        success_effects["trace"]
        if success_effects is not None
        else terminal_effects["trace"]
        if terminal_effects is not None
        else None
    )
    return _sanitize_tool_plan_retry_loop_result_payload(
        {
            "outcome": "success" if success_effects is not None else "terminal_failure",
            "trace_event": trace_event,
            "success_effects": success_effects,
            "terminal_effects": terminal_effects,
        }
    )


def build_tool_plan_item_retry_loop_execution_result(
    *,
    loop_result: dict[str, object],
) -> dict[str, object]:
    sanitized_loop_result = _sanitize_tool_plan_attempt_loop_result_payload(loop_result)
    retry_loop_result = build_tool_plan_item_retry_loop_result(
        loop_result=sanitized_loop_result,
    )
    loop_terminal_result = build_tool_attempt_loop_terminal_result(
        loop_result=sanitized_loop_result,
    )
    return _sanitize_tool_plan_retry_loop_result_payload(
        {
            "outcome": retry_loop_result["outcome"],
            "trace_event": retry_loop_result["trace_event"],
            "success_effects": retry_loop_result["success_effects"],
            "terminal_effects": retry_loop_result["terminal_effects"],
            "should_return": loop_terminal_result["should_return"],
            "loop_result": sanitized_loop_result,
            "retry_loop_result": retry_loop_result,
            "loop_terminal_result": loop_terminal_result,
        }
    )


def execute_tool_plan_item_retry_loop(
    *,
    task_id: str,
    iteration_ctx: dict[str, object],
    initial_action_step: dict[str, object],
    tool_name: str,
    tool_input: dict[str, object],
    prompt: str,
    user_id: str,
    model: str,
    estimate_token_count: Callable[[str], int],
    make_step_id: Callable[[], str],
    raise_if_should_abort: Callable[[], None],
    run_tool_fn: ToolRunner | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> Iterator[dict[str, object]]:
    step_id = str(iteration_ctx["step_id"])
    action_step = dict(initial_action_step)
    attempt = 0
    last_error: str | None = None
    if run_tool_fn is None:
        def default_runner(
            *,
            name: str,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
            attempt: int,
        ) -> dict[str, object]:
            return run_tool(
                name=name,
                tool_input=tool_input,
                prompt=prompt,
                user_id=user_id,
                attempt=attempt,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            )

        runner = default_runner
    else:
        runner = run_tool_fn

    while True:
        raise_if_should_abort()
        attempt_bundle = build_tool_attempt_bundle(
            task_id=task_id,
            step_id=step_id,
            name=tool_name,
            tool_input=tool_input,
            prompt=prompt,
            user_id=user_id,
            attempt=attempt,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        normalized_tool_input = attempt_bundle["normalized_tool_input"]
        action_step = _with_action_step_tool_input(
            action_step,
            tool_input=normalized_tool_input,
        )
        start_events = attempt_bundle["start_events"]
        yield {
            "kind": "event",
            "event": "tool_start",
            "data": start_events["tool_start"],
        }
        yield {
            "kind": "event",
            "event": "state",
            "data": start_events["state"],
        }

        try:
            raise_if_should_abort()
            runtime_policy = attempt_bundle["runtime_policy"]
            output = runner(
                name=tool_name,
                tool_input=normalized_tool_input,
                prompt=prompt,
                user_id=str(runtime_policy["effective_user_id"]),
                attempt=attempt,
            )
            plan_item_execution = build_tool_attempt_execution(
                task_id=task_id,
                iteration_ctx=iteration_ctx,
                action_step=action_step,
                attempt_bundle=attempt_bundle,
                name=tool_name,
                tool_input=normalized_tool_input,
                output=output,
                exc=None,
                token_count=estimate_token_count(
                    f"{tool_name} {json.dumps(output, ensure_ascii=False)}"
                ),
                last_error=last_error,
                model=model,
                rag_step_id=make_step_id(),
                rag_token_count=estimate_token_count(
                    "\n".join(str(x) for x in output.get("chunks", []))
                )
                if isinstance(output, dict)
                else 0,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            )
            loop_result = build_tool_attempt_loop_result(
                attempt_execution=plan_item_execution,
            )
            action_step = loop_result["next_action_step"]
            yield {
                "kind": "event",
                "event": "tool_end",
                "data": loop_result["tool_end_event"],
            }
            yield {
                "kind": "result",
                "result": build_tool_plan_item_retry_loop_execution_result(
                    loop_result=loop_result,
                ),
            }
            return

        except MockToolExecutionError as exc:
            plan_item_execution = build_tool_attempt_execution(
                task_id=task_id,
                iteration_ctx=iteration_ctx,
                action_step=action_step,
                attempt_bundle=attempt_bundle,
                name=tool_name,
                tool_input=normalized_tool_input,
                output=None,
                exc=exc,
                token_count=estimate_token_count(str(exc)),
                last_error=None,
                model=model,
                rag_step_id=make_step_id(),
                rag_token_count=0,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            )
            loop_result = build_tool_attempt_loop_result(
                attempt_execution=plan_item_execution,
            )
            action_step = loop_result["next_action_step"]
            yield {
                "kind": "event",
                "event": "tool_end",
                "data": loop_result["tool_end_event"],
            }
            error_event = loop_result["error_event"]
            if error_event is not None:
                yield {
                    "kind": "event",
                    "event": "error",
                    "data": error_event,
                }
            if bool(loop_result["retryable"]):
                attempt += 1
                last_error = str(loop_result["last_error"])
                continue

            yield {
                "kind": "result",
                "result": build_tool_plan_item_retry_loop_execution_result(
                    loop_result=loop_result,
                ),
            }
            return


def execute_tool_plan_item_service_execution(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
    iteration_ctx: dict[str, object],
    initial_action_step: dict[str, object],
    tool_name: str,
    tool_input: dict[str, object],
    prompt: str,
    user_id: str,
    model: str,
    estimate_token_count: Callable[[str], int],
    make_step_id: Callable[[], str],
    raise_if_should_abort: Callable[[], None],
    run_tool_fn: ToolRunner | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> Iterator[dict[str, object]]:
    for item in execute_tool_plan_item_retry_loop(
        task_id=task_id,
        iteration_ctx=iteration_ctx,
        initial_action_step=initial_action_step,
        tool_name=tool_name,
        tool_input=tool_input,
        prompt=prompt,
        user_id=user_id,
        model=model,
        estimate_token_count=estimate_token_count,
        make_step_id=make_step_id,
        raise_if_should_abort=raise_if_should_abort,
        run_tool_fn=run_tool_fn,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    ):
        if item["kind"] == "event":
            yield item
            continue
        loop_execution_result = item["result"]
        service_execution = build_tool_plan_item_service_execution(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
            loop_execution_result=loop_execution_result,
        )
        service_execution["loop_execution_result"] = (
            sanitize_tool_registry_diagnostics_artifact_payload(
                loop_execution_result
            )
        )
        yield {
            "kind": "result",
            "result": service_execution,
        }
        return


def execute_tool_plan_item_service_actions(
    *,
    service_actions: list[dict[str, object]],
    trace_steps: list[dict[str, object]],
    tool_observations: list[str],
    seq_cursor: int,
    persist_trace_fn: Callable[..., None],
    complete_task_fn: Callable[..., None],
    record_failure_event_fn: Callable[..., None],
) -> Iterator[dict[str, object]]:
    current_seq_cursor = int(seq_cursor)
    for raw_service_action in service_actions:
        service_action = sanitize_tool_registry_diagnostics_artifact_payload(
            raw_service_action
        )
        if not isinstance(service_action, dict):
            continue
        kind = str(service_action["kind"])
        if kind == "trace_write":
            trace_steps.append(service_action["trace_step"])
            yield {
                "kind": "event",
                "event": "trace",
                "data": service_action["trace_event"],
            }
            persist_trace_fn(force=bool(service_action["persist_force"]))
            continue
        if kind == "continue":
            tool_observations.extend(service_action["tool_observations"])
            current_seq_cursor += int(service_action["seq_increment"])
            continue
        if kind == "complete_task":
            complete_task_fn(**service_action["kwargs"])
            continue
        if kind == "record_failure_event":
            record_failure_event_fn(**service_action["kwargs"])
            continue
        if kind == "emit_state":
            yield {
                "kind": "event",
                "event": str(service_action["event"]),
                "data": service_action["data"],
            }
            continue
        if kind == "return":
            yield {
                "kind": "result",
                "result": {
                    "seq_cursor": current_seq_cursor,
                    "should_return": True,
                },
            }
            return
        raise AssertionError(f"unsupported tool service action: {kind}")

    yield {
        "kind": "result",
        "result": {
            "seq_cursor": current_seq_cursor,
            "should_return": False,
        },
    }


def build_tool_attempt_success_events(
    *,
    task_id: str,
    step_id: str,
    name: str,
    output: dict[str, object],
    retry_count: int,
    registration: ToolRegistration | None = None,
) -> dict[str, dict[str, object]]:
    return {
        "tool_end": build_tool_end_payload(
            name=name,
            task_id=task_id,
            step_id=step_id,
            output=output,
            retry_count=retry_count,
            registration=registration,
        )
    }


def build_tool_attempt_error_events(
    *,
    name: str,
    task_id: str,
    step_id: str,
    error_message: str,
    retry_count: int,
    latency_ms: int = 12,
    registration: ToolRegistration | None = None,
) -> dict[str, dict[str, object]]:
    return {
        "tool_end": build_tool_error_payload(
            name=name,
            task_id=task_id,
            step_id=step_id,
            error_message=error_message,
            retry_count=retry_count,
            latency_ms=latency_ms,
            registration=registration,
        )
    }


def build_tool_attempt_success_transition(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object],
    retry_count: int,
    token_count: int,
    last_error: str | None,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    return {
        "action_step": build_tool_step_success_update(
            action_step=action_step,
            name=name,
            tool_input=tool_input,
            output=output,
            retry_count=retry_count,
            token_count=token_count,
            last_error=last_error,
            display_name=display_name,
            registration=registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "events": build_tool_attempt_success_events(
            task_id=task_id,
            step_id=step_id,
            name=name,
            output=output,
            retry_count=retry_count,
            registration=registration,
        ),
    }


def build_tool_attempt_error_transition(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    runtime_ctx: ToolRuntimeContext,
    name: str,
    tool_input: dict[str, object],
    exc: MockToolExecutionError,
    token_count: int,
    display_name: str | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    error_message = str(exc)
    safe_error_message = _normalize_tool_error_message_for_registration(
        error_message,
        registration=runtime_ctx.registration,
    )
    retry_count = runtime_ctx.attempt + 1
    retryable = compute_tool_retry_decision(ctx=runtime_ctx, exc=exc)
    return {
        "action_step": build_tool_step_error_update(
            action_step=action_step,
            name=name,
            tool_input=tool_input,
            retry_count=retry_count,
            token_count=token_count,
            error_message=safe_error_message,
            display_name=display_name,
            registration=runtime_ctx.registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "events": {
            **build_tool_attempt_error_events(
                name=name,
                task_id=task_id,
                step_id=step_id,
                error_message=safe_error_message,
                retry_count=retry_count,
                latency_ms=max(1, runtime_ctx.default_timeout_ms // 250),
                registration=runtime_ctx.registration,
            ),
            "error": {
                "task_id": task_id,
                "message": safe_error_message,
                "code": "tool_execution_error",
                "fatal": not retryable,
                "retryable": retryable,
                "retryCount": retry_count,
                "step_id": step_id,
            },
        },
        "retryable": retryable,
        "error_message": safe_error_message,
        "retry_count": retry_count,
    }


def _parse_tool_json_mapping_string(value: str) -> dict[str, object] | None:
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


def _coerce_tool_output_preview_mapping(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    return _parse_tool_json_mapping_string(value)


def _coerce_tool_output_mapping(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    return _parse_tool_json_mapping_string(value)


def build_tool_step_output(action_step: dict[str, object]) -> dict[str, object] | None:
    tool_obj = get_action_step_tool_meta(action_step)
    output = tool_obj.get("output") if isinstance(tool_obj, dict) else None
    if isinstance(output, dict):
        return output
    safe_output = _resolve_step_tool_safe_output(tool_obj)
    if isinstance(safe_output, dict):
        return safe_output
    preview_output = tool_obj.get("output_preview") if isinstance(tool_obj, dict) else None
    return _coerce_tool_output_preview_mapping(preview_output)


def get_action_step_tool_meta(action_step: dict[str, object]) -> dict[str, object] | None:
    tool_meta = action_step.get("meta") if isinstance(action_step, dict) else None
    tool_obj = (
        tool_meta.get("tool")
        if isinstance(tool_meta, dict) and isinstance(tool_meta.get("tool"), dict)
        else None
    )
    return tool_obj if isinstance(tool_obj, dict) else None


def _resolve_step_tool_safe_output(
    step_tool_meta: dict[str, object] | None,
) -> object | None:
    if not isinstance(step_tool_meta, dict):
        return None
    output_keys = step_tool_meta.get("effective_result_output_keys")
    if not isinstance(output_keys, (list, tuple)):
        return None
    normalized_keys = [
        key.strip()
        for key in output_keys
        if isinstance(key, str) and key.strip()
    ]
    if not normalized_keys:
        return None
    output = step_tool_meta.get("output")
    output_mapping = _coerce_tool_output_mapping(output)
    if not isinstance(output_mapping, dict):
        return output
    if _step_tool_meta_uses_http_json_execution(step_tool_meta):
        output_mapping = _normalize_http_json_safe_output_shape(output_mapping)
    return {
        key: output_mapping[key]
        for key in normalized_keys
        if key in output_mapping
    }


def _step_tool_meta_uses_http_json_execution(
    step_tool_meta: dict[str, object] | None,
) -> bool:
    if not isinstance(step_tool_meta, dict):
        return False
    return _normalize_tool_execution_kind(step_tool_meta.get("execution_kind")) == "http_json"


def _build_tool_result_summary_from_step_meta_semantics(
    *,
    output: dict[str, object],
    step_tool_meta: dict[str, object] | None,
) -> str | None:
    if not isinstance(output, dict):
        return None
    if _step_tool_meta_uses_http_json_execution(step_tool_meta):
        output = _normalize_http_json_safe_output_shape(output)
    meta_label = (
        str(step_tool_meta.get("label")).strip()
        if isinstance(step_tool_meta, dict)
        and isinstance(step_tool_meta.get("label"), str)
        else ""
    )
    meta_name = (
        str(step_tool_meta.get("name")).strip()
        if isinstance(step_tool_meta, dict)
        and isinstance(step_tool_meta.get("name"), str)
        else ""
    )
    structural_tool_kind = (
        str(step_tool_meta.get("kind")).strip()
        if isinstance(step_tool_meta, dict)
        and isinstance(step_tool_meta.get("kind"), str)
        else ""
    )
    explicit_semantic_kind = (
        str(step_tool_meta.get("semantic_kind")).strip()
        if isinstance(step_tool_meta, dict)
        and isinstance(step_tool_meta.get("semantic_kind"), str)
        else ""
    )
    explicit_semantic_family = (
        str(step_tool_meta.get("semantic_family")).strip()
        if isinstance(step_tool_meta, dict)
        and isinstance(step_tool_meta.get("semantic_family"), str)
        else ""
    )
    label_implies_local_retrieval = (
        _label_implies_local_knowledge_retrieval(meta_label)
        or _label_implies_local_knowledge_retrieval(meta_name)
    )
    label_implies_real_retrieval = (
        _label_implies_real_retrieval_summary(meta_label)
        or _label_implies_real_retrieval_summary(meta_name)
    )
    label_implies_real_calc = (
        _label_implies_real_calc_summary(meta_label)
        or _label_implies_real_calc_summary(meta_name)
    )
    runtime_semantic_kind = _normalize_tool_semantic_kind(
        explicit_semantic_kind or None
    )
    explicit_runtime_semantic_family = _normalize_tool_semantic_kind(
        explicit_semantic_family or None
    )
    structural_semantic_family = _normalize_tool_semantic_kind(
        structural_tool_kind or None
    )
    semantic_family = explicit_runtime_semantic_family
    if semantic_family is None and structural_semantic_family in {
        "knowledge_retrieval",
        "local_calculator",
        "task_planner",
    } and normalize_tool_registry_name(meta_name) not in _REGISTERED_TOOLS:
        semantic_family = structural_semantic_family
    has_runtime_semantic_hint = semantic_family is not None
    if (
        not has_runtime_semantic_hint
        and not label_implies_local_retrieval
        and not label_implies_real_retrieval
        and not label_implies_real_calc
    ):
        return None
    allow_local_knowledge_base_summary = (
        runtime_semantic_kind == "knowledge_retrieval"
        or (
            runtime_semantic_kind is None
            and (
                explicit_runtime_semantic_family == "knowledge_retrieval"
                or label_implies_local_retrieval
            )
        )
    )

    plan = output.get("plan")
    if isinstance(plan, str) and plan.strip():
        return f"Planned steps - {plan.strip()}."
    steps = _normalize_tool_result_plan_steps(output.get("steps"))
    if steps:
        return f"Planned steps - {' -> '.join(steps)}."

    expression = output.get("expression")
    result = output.get("result")
    request_id = _get_safe_http_json_request_id_display_value(
        output.get("request_id")
    )
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

    hit_count = _normalize_nonnegative_int_count_value(output.get("hit_count"))
    knowledge_base_id = output.get("knowledge_base_id")
    if hit_count is not None:
        hit_label = "hit" if hit_count == 1 else "hits"
        if (
            allow_local_knowledge_base_summary
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
        if semantic_family == "knowledge_retrieval":
            if isinstance(request_id, str) and request_id.strip():
                return f"Retrieved {hit_count} {hit_label} (request id {request_id.strip()})."
            return f"Retrieved {hit_count} {hit_label}."
        if isinstance(request_id, str) and request_id.strip():
            return f"Retrieved {hit_count} {hit_label} (request id {request_id.strip()})."
        return f"Retrieved {hit_count} {hit_label}."

    documents_total = _normalize_nonnegative_int_count_value(
        output.get("documents_total")
    )
    if documents_total is not None:
        document_label = "document" if documents_total == 1 else "documents"
        if isinstance(request_id, str) and request_id.strip():
            return (
                f"Retrieved {documents_total} {document_label} "
                f"(request id {request_id.strip()})."
            )
        return f"Retrieved {documents_total} {document_label}."
    return None


def build_tool_observation_entry(
    *,
    name: str,
    output: dict[str, object] | None,
    display_name: str | None = None,
    step_tool_meta: dict[str, object] | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> str:
    canonical_name = normalize_tool_registry_name(name)
    resolved_registration = registration or resolve_tool_registration(
        canonical_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    meta_display_name = (
        str(step_tool_meta.get("label")).strip()
        if isinstance(step_tool_meta, dict) and isinstance(step_tool_meta.get("label"), str)
        else ""
    )
    resolved_display_name = (
        display_name
        or meta_display_name
        or get_tool_observation_display_name_from_registration(
            name=canonical_name,
            registration=resolved_registration,
        )
    )
    meta_result_summary = (
        str(step_tool_meta.get("result_summary")).strip()
        if isinstance(step_tool_meta, dict)
        and isinstance(step_tool_meta.get("result_summary"), str)
        else ""
    )
    if meta_result_summary:
        return f"{resolved_display_name}: {meta_result_summary}"
    meta_safe_output = _resolve_step_tool_safe_output(step_tool_meta)
    if isinstance(meta_safe_output, dict) and not isinstance(output, dict):
        result_summary = build_tool_result_summary(
            name=canonical_name,
            output=meta_safe_output,
            display_name=resolved_display_name,
            registration=resolved_registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        if result_summary is None:
            result_summary = _build_tool_result_summary_from_step_meta_semantics(
                output=meta_safe_output,
                step_tool_meta=step_tool_meta,
            )
        if result_summary:
            return f"{resolved_display_name}: {result_summary}"
    if meta_safe_output is not None and not isinstance(output, dict):
        return (
            f"{resolved_display_name}: "
            f"{json.dumps(meta_safe_output, ensure_ascii=False)}"
        )
    meta_preview_output = (
        step_tool_meta.get("output_preview")
        if isinstance(step_tool_meta, dict)
        else None
    )
    meta_preview_mapping = _coerce_tool_output_preview_mapping(meta_preview_output)
    if isinstance(meta_preview_mapping, dict) and not isinstance(output, dict):
        if _step_tool_meta_uses_http_json_execution(step_tool_meta):
            meta_preview_mapping = _normalize_http_json_safe_output_shape(
                meta_preview_mapping
            )
        result_summary = build_tool_result_summary(
            name=canonical_name,
            output=meta_preview_mapping,
            display_name=resolved_display_name,
            registration=resolved_registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        if result_summary is None:
            result_summary = _build_tool_result_summary_from_step_meta_semantics(
                output=meta_preview_mapping,
                step_tool_meta=step_tool_meta,
            )
        if result_summary:
            return f"{resolved_display_name}: {result_summary}"
    if meta_preview_output is not None and not isinstance(output, dict):
        if isinstance(meta_preview_mapping, dict) and _step_tool_meta_uses_http_json_execution(
            step_tool_meta
        ):
            return (
                f"{resolved_display_name}: "
                f"{json.dumps(meta_preview_mapping, ensure_ascii=False)}"
            )
        return (
            f"{resolved_display_name}: "
            f"{json.dumps(meta_preview_output, ensure_ascii=False)}"
        )
    if isinstance(output, dict):
        result_summary = build_tool_result_summary(
            name=canonical_name,
            output=output,
            display_name=resolved_display_name,
            registration=resolved_registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        if result_summary is None:
            result_summary = _build_tool_result_summary_from_step_meta_semantics(
                output=output,
                step_tool_meta=step_tool_meta,
            )
        if result_summary:
            return f"{resolved_display_name}: {result_summary}"
        meta_safe_output = _resolve_step_tool_safe_output(step_tool_meta)
        if meta_safe_output is not None:
            return (
                f"{resolved_display_name}: "
                f"{json.dumps(meta_safe_output, ensure_ascii=False)}"
            )
        if meta_preview_output is not None:
            return (
                f"{resolved_display_name}: "
                f"{json.dumps(meta_preview_output, ensure_ascii=False)}"
            )
    observation_output = output
    if isinstance(output, dict):
        effective_result_output_keys = get_tool_effective_result_output_keys(
            name=canonical_name,
            registration=resolved_registration,
        )
        observation_output = build_tool_result_output(
            name=canonical_name,
            output=output,
            registry=registry,
            registration=resolved_registration,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        if not effective_result_output_keys:
            preview_output = build_tool_result_preview(
                name=canonical_name,
                output=observation_output,
                registry=registry,
                registration=resolved_registration,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            )
            if preview_output is not None:
                observation_output = preview_output
        if (
            isinstance(observation_output, dict)
            and _step_tool_meta_uses_http_json_execution(step_tool_meta)
        ):
            observation_output = _normalize_http_json_safe_output_shape(
                observation_output
            )
    return (
        f"{resolved_display_name}: "
        f"{json.dumps(observation_output, ensure_ascii=False)}"
    )


def build_tool_trace_event(
    *,
    task_id: str,
    step_id: str,
    step: dict[str, object],
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "step_id": step_id,
        "step": step,
    }


def build_tool_terminal_failure_transition(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    error_message: str,
    retry_count: int,
) -> dict[str, object]:
    return _sanitize_tool_terminal_failure_payload(
        {
            "trace": build_tool_trace_event(
                task_id=task_id,
                step_id=step_id,
                step=action_step,
            ),
            "audit_detail": {
                "step_id": step_id,
                "retry_count": retry_count,
            },
            "state": {
                "task_id": task_id,
                "phase": "error",
            },
            "status": "failed",
            "error_message": error_message,
        }
    )


def _sanitize_tool_terminal_failure_payload(
    payload: dict[str, object] | None,
) -> dict[str, object] | None:
    if payload is None:
        return None
    sanitized = sanitize_tool_registry_diagnostics_artifact_payload(payload)
    assert isinstance(sanitized, dict)
    return sanitized


def _sanitize_tool_plan_item_result_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = dict(payload)
    for key in ("action_step", "last_error", "terminal_failure"):
        if key in sanitized:
            sanitized[key] = sanitize_tool_registry_diagnostics_artifact_payload(
                sanitized[key]
            )
    return sanitized


def build_tool_rag_step(
    *,
    step_id: str,
    seq: int,
    model: str,
    chunks: list[str],
    knowledge_base_id: str | None,
    token_count: int,
    content: str | None = None,
) -> dict[str, object]:
    rag_meta: dict[str, object] = {
        "chunks": chunks,
    }
    if isinstance(knowledge_base_id, str) and knowledge_base_id:
        rag_meta["knowledge_base_id"] = knowledge_base_id
    return {
        "id": step_id,
        "seq": seq,
        "type": "thought",
        "content": content
        or "Knowledge Retrieval returned snippets from the selected knowledge base.",
        "meta": {
            "model": model,
            "step_type": "rag_retrieval",
            "tokens": token_count,
            "cost_estimate": None,
            "rag": rag_meta,
        },
    }


def _build_tool_rag_followup_content(
    *,
    display_name: str | None,
    runtime_semantic_kind: str | None,
    semantic_family: str | None,
) -> str:
    normalized_display_name = (
        str(display_name).strip() if isinstance(display_name, str) else ""
    )
    normalized_runtime_semantic_kind = _normalize_tool_semantic_kind(
        runtime_semantic_kind
    )
    normalized_semantic_family = _normalize_tool_semantic_kind(semantic_family)
    if (
        normalized_runtime_semantic_kind != "knowledge_retrieval"
        and normalized_semantic_family == "knowledge_retrieval"
    ):
        if normalized_display_name:
            return f"{normalized_display_name} returned snippets."
        return "Knowledge Retrieval returned snippets."
    if normalized_display_name and normalized_display_name != "Knowledge Retrieval":
        return f"{normalized_display_name} returned snippets from the selected knowledge base."
    return "Knowledge Retrieval returned snippets from the selected knowledge base."


_TOOL_RAG_DOCUMENT_TEXT_FIELDS = (
    "snippet",
    "content",
    "text",
    "excerpt",
    "summary",
    "description",
    "body",
    "chunk",
    "page_content",
    "document_text",
)
_TOOL_RAG_DOCUMENT_CONTAINER_FIELDS = (
    "metadata",
    "document",
    "payload",
    "chunk",
    "node",
    "data",
    "record",
    "item",
)
_TOOL_RAG_DOCUMENT_LIST_FIELDS = ("documents", "items", "results", "hits", "matches")


def _extract_tool_rag_chunk_from_document_mapping(
    raw_document: dict,
    *,
    depth: int = 0,
    visited: set[int] | None = None,
) -> str | None:
    if depth > 4:
        return None
    if visited is None:
        visited = set()
    document_id = id(raw_document)
    if document_id in visited:
        return None
    visited.add(document_id)
    for field_name in _TOOL_RAG_DOCUMENT_TEXT_FIELDS:
        raw_value = raw_document.get(field_name)
        if not isinstance(raw_value, str):
            continue
        normalized_chunk = raw_value.strip()
        if normalized_chunk:
            return normalized_chunk
    for field_name in _TOOL_RAG_DOCUMENT_TEXT_FIELDS:
        nested_document = raw_document.get(field_name)
        if not isinstance(nested_document, dict):
            continue
        nested_chunk = _extract_tool_rag_chunk_from_document_mapping(
            nested_document,
            depth=depth + 1,
            visited=visited,
        )
        if nested_chunk:
            return nested_chunk
    for container_name in _TOOL_RAG_DOCUMENT_CONTAINER_FIELDS:
        nested_document = raw_document.get(container_name)
        if not isinstance(nested_document, dict):
            continue
        nested_chunk = _extract_tool_rag_chunk_from_document_mapping(
            nested_document,
            depth=depth + 1,
            visited=visited,
        )
        if nested_chunk:
            return nested_chunk
    return None


def _extract_tool_rag_chunks_from_document_list(raw_documents: object) -> list[str]:
    if not isinstance(raw_documents, (list, tuple)):
        return []
    extracted_chunks: list[str] = []
    for raw_document in raw_documents:
        if isinstance(raw_document, str):
            normalized_chunk = raw_document.strip()
            if normalized_chunk:
                extracted_chunks.append(normalized_chunk)
            continue
        if not isinstance(raw_document, dict):
            continue
        normalized_chunk = _extract_tool_rag_chunk_from_document_mapping(raw_document)
        if normalized_chunk:
            extracted_chunks.append(normalized_chunk)
    return extracted_chunks


def _extract_tool_rag_chunks_from_output(output: dict[str, object]) -> list[str]:
    raw_chunks = output.get("chunks")
    if isinstance(raw_chunks, (list, tuple)):
        return [
            chunk.strip()
            for chunk in raw_chunks
            if isinstance(chunk, str) and chunk.strip()
        ]

    for list_field_name in _TOOL_RAG_DOCUMENT_LIST_FIELDS:
        extracted_chunks = _extract_tool_rag_chunks_from_document_list(
            output.get(list_field_name)
        )
        if extracted_chunks:
            return extracted_chunks
    return []


def build_tool_prompt_with_observations(
    *,
    prompt: str,
    tool_observations: list[str],
) -> str:
    if not tool_observations:
        return prompt
    return f"{prompt}\n\nTool observations:\n" + "\n".join(tool_observations)


def build_tool_attempt_result(
    *,
    outcome: str,
    action_step: dict[str, object],
    events: dict[str, dict[str, object]],
    retryable: bool,
    error_message: str | None,
    retry_count: int,
) -> dict[str, object]:
    result = {
        "outcome": outcome,
        "action_step": action_step,
        "events": events,
        "retryable": retryable,
        "error_message": error_message,
        "retry_count": retry_count,
    }
    if outcome == "success" and error_message is None:
        return result
    return _sanitize_tool_attempt_error_result_payload(result)


def _sanitize_tool_attempt_error_result_payload(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = dict(payload)
    for key in ("action_step", "events", "error_message"):
        if key in sanitized:
            sanitized[key] = sanitize_tool_registry_diagnostics_artifact_payload(
                sanitized[key]
            )
    return sanitized


def build_tool_attempt_outcome(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    runtime_ctx: ToolRuntimeContext,
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object] | None,
    exc: MockToolExecutionError | None,
    token_count: int,
    last_error: str | None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    display_name = get_tool_execution_display_name_from_registration(
        name=runtime_ctx.registration.name,
        registration=runtime_ctx.registration,
    )
    if exc is None:
        assert output is not None
        success_transition = build_tool_attempt_success_transition(
            task_id=task_id,
            step_id=step_id,
            action_step=action_step,
            name=name,
            tool_input=tool_input,
            output=output,
            retry_count=runtime_ctx.attempt,
            token_count=token_count,
            last_error=last_error,
            display_name=display_name,
            registration=runtime_ctx.registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        return build_tool_attempt_result(
            outcome="success",
            action_step=success_transition["action_step"],
            events=success_transition["events"],
            retryable=False,
            error_message=None,
            retry_count=runtime_ctx.attempt,
        )

    error_transition = build_tool_attempt_error_transition(
        task_id=task_id,
        step_id=step_id,
        action_step=action_step,
        runtime_ctx=runtime_ctx,
        name=name,
        tool_input=tool_input,
        exc=exc,
        token_count=token_count,
        display_name=display_name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    return build_tool_attempt_result(
        outcome="error",
        action_step=error_transition["action_step"],
        events=error_transition["events"],
        retryable=bool(error_transition["retryable"]),
        error_message=str(error_transition["error_message"]),
        retry_count=int(error_transition["retry_count"]),
    )


def build_tool_iteration_context(
    *,
    step_id: str,
    seq: int,
    name: str,
    tool_input: dict[str, object],
    model: str,
    label: str,
    token_count: int,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    canonical_name = normalize_tool_registry_name(name)
    return {
        "step_id": step_id,
        "action_step": build_action_step_initial_step(
            step_id=step_id,
            seq=seq,
            name=canonical_name,
            meta=build_action_step_initial_meta(
                name=canonical_name,
                tool_input=tool_input,
                model=model,
                label=label,
                token_count=token_count,
                display_name=display_name,
                registration=registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
        ),
    }


def build_tool_iteration_success_artifacts(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    name: str,
    display_name: str | None = None,
    registration: ToolRegistration | None = None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    output = build_tool_step_output(action_step)
    step_tool_meta = get_action_step_tool_meta(action_step)
    canonical_name = normalize_tool_registry_name(name)
    return {
        "trace": build_tool_trace_event(
            task_id=task_id,
            step_id=step_id,
            step=action_step,
        ),
        "observation": build_tool_observation_entry(
            name=canonical_name,
            output=output,
            display_name=display_name,
            step_tool_meta=step_tool_meta,
            registration=registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        "output": output,
    }


def build_tool_rag_followup(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    tool_name: str,
    tool_kind: str | None = None,
    tool_semantic_family: str | None = None,
    display_name: str | None = None,
    output: dict[str, object] | None,
    token_count: int,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object] | None:
    if not isinstance(output, dict):
        return None
    runtime_semantic_kind = _normalize_tool_semantic_kind(tool_kind)
    if runtime_semantic_kind is None:
        runtime_semantic_kind = _get_tool_runtime_trace_semantic_kind(
            name=tool_name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
    semantic_family = _normalize_tool_semantic_kind(tool_semantic_family)
    if semantic_family is None:
        semantic_family = get_tool_semantic_kind(
            name=tool_name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
    semantic_kind = runtime_semantic_kind
    if semantic_kind != "knowledge_retrieval":
        semantic_kind = semantic_family
    if semantic_kind != "knowledge_retrieval":
        return None
    chunks = _extract_tool_rag_chunks_from_output(output)
    if not chunks:
        return None
    kb = output.get("knowledge_base_id")
    step = build_tool_rag_step(
        step_id=step_id,
        seq=seq,
        model=model,
        chunks=chunks,
        knowledge_base_id=str(kb) if kb else None,
        token_count=token_count,
        content=_build_tool_rag_followup_content(
            display_name=display_name,
            runtime_semantic_kind=runtime_semantic_kind,
            semantic_family=semantic_family,
        ),
    )
    return {
        "step": step,
        "trace": build_tool_trace_event(
            task_id=task_id,
            step_id=step_id,
            step=step,
        ),
    }


def build_tool_iteration_execution(
    *,
    task_id: str,
    step_id: str,
    iteration_ctx: dict[str, object],
    action_step: dict[str, object],
    runtime_ctx: ToolRuntimeContext,
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object] | None,
    exc: MockToolExecutionError | None,
    token_count: int,
    last_error: str | None,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    normalized_output = (
        normalize_tool_output_for_registration(
            output=output,
            registration=runtime_ctx.registration,
        )
        if isinstance(output, dict)
        else output
    )
    execution_display_name = get_tool_execution_display_name_from_registration(
        name=runtime_ctx.registration.name,
        registration=runtime_ctx.registration,
    )
    start_events = build_tool_attempt_start_events(
        task_id=task_id,
        step_id=step_id,
        name=name,
        tool_input=tool_input,
        attempt=runtime_ctx.attempt,
        display_name=execution_display_name,
        registration=runtime_ctx.registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    outcome = build_tool_attempt_outcome(
        task_id=task_id,
        step_id=step_id,
        action_step=dict(action_step),
        runtime_ctx=runtime_ctx,
        name=name,
        tool_input=tool_input,
        output=normalized_output,
        exc=exc,
        token_count=token_count,
        last_error=last_error,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    if outcome["outcome"] == "success":
        observation_display_name = get_tool_observation_display_name_from_registration(
            name=runtime_ctx.registration.name,
            registration=runtime_ctx.registration,
        )
        return {
            "start_events": start_events,
            "outcome": outcome,
            "success_artifacts": build_tool_iteration_success_artifacts(
                task_id=task_id,
                step_id=step_id,
                action_step=outcome["action_step"],
                name=name,
                display_name=observation_display_name,
                registration=runtime_ctx.registration,
                registry=registry,
                registry_provider=registry_provider,
                registry_loader=registry_loader,
            ),
            "rag_source_output": normalized_output if isinstance(normalized_output, dict) else None,
            "terminal_failure": None,
        }

    terminal_failure = None
    if not bool(outcome["retryable"]):
        terminal_failure = build_tool_terminal_failure_transition(
            task_id=task_id,
            step_id=step_id,
            action_step=outcome["action_step"],
            error_message=str(outcome["error_message"]),
            retry_count=int(outcome["retry_count"]),
        )
    return {
        "start_events": start_events,
        "outcome": outcome,
        "success_artifacts": None,
        "terminal_failure": terminal_failure,
    }


def build_tool_plan_item_success_bundle(
    *,
    success_artifacts: dict[str, object],
    rag_followup: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "trace": success_artifacts["trace"],
        "observation": success_artifacts["observation"],
        "output": success_artifacts["output"],
        "rag_followup": rag_followup,
    }


def build_tool_plan_item_result(
    *,
    outcome: str,
    action_step: dict[str, object],
    last_error: str | None,
    success_bundle: dict[str, object] | None,
    terminal_failure: dict[str, object] | None,
) -> dict[str, object]:
    return _sanitize_tool_plan_item_result_payload(
        {
            "outcome": outcome,
            "action_step": action_step,
            "last_error": last_error,
            "success_bundle": success_bundle,
            "terminal_failure": terminal_failure,
        }
    )


def build_tool_plan_item_execution_result(
    *,
    iteration_execution: dict[str, object],
    rag_followup: dict[str, object] | None,
) -> dict[str, object]:
    success_artifacts = iteration_execution.get("success_artifacts")
    terminal_failure = iteration_execution.get("terminal_failure")
    outcome = iteration_execution["outcome"]
    action_step = outcome["action_step"]
    error_message = outcome.get("error_message")

    if success_artifacts is not None:
        return build_tool_plan_item_result(
            outcome="success",
            action_step=action_step,
            last_error=error_message,
            success_bundle=build_tool_plan_item_success_bundle(
                success_artifacts=success_artifacts,
                rag_followup=rag_followup,
            ),
            terminal_failure=None,
        )

    return build_tool_plan_item_result(
        outcome="terminal_failure",
        action_step=action_step,
        last_error=error_message,
        success_bundle=None,
        terminal_failure=terminal_failure,
    )


def build_tool_plan_item_execution(
    *,
    task_id: str,
    iteration_ctx: dict[str, object],
    action_step: dict[str, object],
    runtime_ctx: ToolRuntimeContext,
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object] | None,
    exc: MockToolExecutionError | None,
    token_count: int,
    last_error: str | None,
    model: str,
    rag_step_id: str,
    rag_token_count: int,
    registry: dict[str, ToolRegistration] | None = None,
    registry_provider: ToolRegistryProvider | None = None,
    registry_loader: ToolRegistryLoader | None = None,
) -> dict[str, object]:
    iteration_execution = build_tool_iteration_execution(
        task_id=task_id,
        step_id=str(iteration_ctx["step_id"]),
        iteration_ctx=iteration_ctx,
        action_step=action_step,
        runtime_ctx=runtime_ctx,
        name=name,
        tool_input=tool_input,
        output=output,
        exc=exc,
        token_count=token_count,
        last_error=last_error,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    success_artifacts = iteration_execution.get("success_artifacts")
    rag_followup = None
    if success_artifacts is not None:
        success_output = iteration_execution.get("rag_source_output")
        if not isinstance(success_output, dict):
            success_output = success_artifacts["output"]
        rag_followup = build_tool_rag_followup(
            task_id=task_id,
            step_id=rag_step_id,
            seq=int(action_step.get("seq", 0)) + 1,
            model=model,
            tool_name=name,
            tool_kind=_get_tool_runtime_trace_semantic_kind(
                name=runtime_ctx.registration.name,
                registration=runtime_ctx.registration,
            ),
            tool_semantic_family=get_tool_semantic_kind(
                name=runtime_ctx.registration.name,
                registration=runtime_ctx.registration,
            ),
            display_name=get_tool_display_name_from_registration(
                name=runtime_ctx.registration.name,
                registration=runtime_ctx.registration,
            ),
            output=success_output if isinstance(success_output, dict) else None,
            token_count=rag_token_count,
        )
    plan_item_result = build_tool_plan_item_execution_result(
        iteration_execution=iteration_execution,
        rag_followup=rag_followup,
    )
    attempt_outcome = iteration_execution["outcome"]
    postprocess = None
    success_effects = None
    terminal_effects = None
    if plan_item_result["success_bundle"] is not None:
        postprocess = build_tool_plan_item_postprocess(
            plan_item_result=plan_item_result,
        )
        success_effects = build_tool_plan_item_success_effects(
            action_step=plan_item_result["action_step"],
            postprocess=postprocess,
        )
    elif plan_item_result["terminal_failure"] is not None:
        terminal_effects = build_tool_plan_item_terminal_effects(
            action_step=plan_item_result["action_step"],
            terminal_failure=plan_item_result["terminal_failure"],
        )
    return {
        "start_events": iteration_execution["start_events"],
        "iteration_execution": iteration_execution,
        "tool_end_event": attempt_outcome["events"]["tool_end"],
        "error_event": attempt_outcome["events"].get("error"),
        "retryable": bool(attempt_outcome["retryable"]),
        "postprocess": postprocess,
        "success_effects": success_effects,
        "terminal_effects": terminal_effects,
        "plan_item_result": plan_item_result,
        "next_action_step": plan_item_result["action_step"],
        "last_error": plan_item_result["last_error"],
        "terminal_failure": plan_item_result["terminal_failure"],
    }


def build_tool_plan_item_postprocess(
    *,
    plan_item_result: dict[str, object],
) -> dict[str, object]:
    success_bundle = plan_item_result["success_bundle"]
    assert success_bundle is not None
    return {
        "trace": success_bundle["trace"],
        "observation": success_bundle["observation"],
        "output": success_bundle["output"],
        "rag_followup": success_bundle["rag_followup"],
    }


def _sanitize_tool_plan_item_payload_dict(
    payload: dict[str, object],
) -> dict[str, object]:
    sanitized = sanitize_tool_registry_diagnostics_artifact_payload(payload)
    assert isinstance(sanitized, dict)
    return sanitized


def _sanitize_tool_plan_item_payload_list(
    payload: list[dict[str, object]],
) -> list[dict[str, object]]:
    sanitized = sanitize_tool_registry_diagnostics_artifact_payload(payload)
    assert isinstance(sanitized, list)
    return sanitized


def build_tool_plan_item_success_effects(
    *,
    action_step: dict[str, object],
    postprocess: dict[str, object],
) -> dict[str, object]:
    return {
        "trace_step": action_step,
        "trace": postprocess["trace"],
        "observation": postprocess["observation"],
        "output": postprocess["output"],
        "rag_followup": postprocess["rag_followup"],
    }


def build_tool_plan_item_terminal_effects(
    *,
    action_step: dict[str, object],
    terminal_failure: dict[str, object],
) -> dict[str, object]:
    return {
        "trace_step": action_step,
        "trace": terminal_failure["trace"],
        "status": terminal_failure["status"],
        "error_message": terminal_failure["error_message"],
        "audit_detail": terminal_failure["audit_detail"],
        "state": terminal_failure["state"],
    }


def build_tool_plan_item_stream_effects(
    *,
    loop_execution_result: dict[str, object],
) -> dict[str, object]:
    success_effects = loop_execution_result["success_effects"]
    terminal_effects = loop_execution_result["terminal_effects"]

    if success_effects is not None:
        trace_steps = [success_effects["trace_step"]]
        trace_events = [loop_execution_result["trace_event"]]
        rag_followup = success_effects["rag_followup"]
        if rag_followup is not None:
            trace_steps.append(rag_followup["step"])
            trace_events.append(rag_followup["trace"])
        return _sanitize_tool_plan_item_payload_dict(
            {
                "trace_steps": trace_steps,
                "trace_events": trace_events,
                "observation": success_effects["observation"],
                "tool_observations": [success_effects["observation"]],
                "terminal_effects": None,
                "seq_increment": 1 if rag_followup is not None else 0,
                "should_return": False,
            }
        )

    assert terminal_effects is not None
    return _sanitize_tool_plan_item_payload_dict(
        {
            "trace_steps": [terminal_effects["trace_step"]],
            "trace_events": [terminal_effects["trace"]],
            "observation": None,
            "tool_observations": [],
            "terminal_effects": terminal_effects,
            "seq_increment": 0,
            "should_return": bool(loop_execution_result["should_return"]),
        }
    )


def build_tool_plan_item_terminal_return_effects(
    *,
    terminal_effects: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "task_status": terminal_effects["status"],
            "state_event": terminal_effects["state"],
            "failure_event": {
                "event_type": "task_failed",
                "code": "tool_execution_error",
                "message": terminal_effects["error_message"],
                "detail": terminal_effects["audit_detail"],
            },
        }
    )


def build_tool_plan_item_continue_update(
    *,
    stream_effects: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "tool_observations": list(stream_effects["tool_observations"]),
            "seq_increment": int(stream_effects["seq_increment"]),
        }
    )


def build_tool_plan_item_continue_action(
    *,
    continue_update: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "tool_observations": list(continue_update["tool_observations"]),
            "seq_increment": int(continue_update["seq_increment"]),
        }
    )


def build_tool_plan_item_next_action(
    *,
    continue_update: dict[str, object],
    terminal_return_effects: dict[str, object] | None,
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "kind": "return" if terminal_return_effects is not None else "continue",
            "continue_update": continue_update,
            "terminal_return_effects": terminal_return_effects,
        }
    )


def build_tool_plan_item_return_action(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
    user_id: str,
    terminal_return_effects: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "complete_task_kwargs": {
                "task_id": task_id,
                "trace_steps": trace_steps,
                "user_id": user_id,
                "status": str(terminal_return_effects["task_status"]),
            },
            "failure_event_kwargs": terminal_return_effects["failure_event"],
            "state_event": terminal_return_effects["state_event"],
        }
    )


def build_tool_plan_item_trace_write_action(
    *,
    trace_write: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "trace_step": trace_write["step"],
            "trace_event": trace_write["event"],
            "persist_force": bool(trace_write["force_persist"]),
        }
    )


def build_tool_plan_item_next_action_execution(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
    user_id: str,
    next_action: dict[str, object],
) -> dict[str, object]:
    continue_action = build_tool_plan_item_continue_action(
        continue_update=next_action["continue_update"],
    )
    if str(next_action["kind"]) == "return":
        terminal_return_effects = next_action["terminal_return_effects"]
        assert terminal_return_effects is not None
        return _sanitize_tool_plan_item_payload_dict(
            {
                "kind": "return",
                "continue_update": next_action["continue_update"],
                "continue_action": continue_action,
                "return_action": build_tool_plan_item_return_action(
                    task_id=task_id,
                    trace_steps=trace_steps,
                    user_id=user_id,
                    terminal_return_effects=terminal_return_effects,
                ),
            }
        )
    return _sanitize_tool_plan_item_payload_dict(
        {
            "kind": "continue",
            "continue_update": next_action["continue_update"],
            "continue_action": continue_action,
            "return_action": None,
        }
    )


def build_tool_plan_item_service_actions(
    *,
    service_execution: dict[str, object],
) -> list[dict[str, object]]:
    actions = [
        build_tool_plan_item_trace_write_service_action(
            trace_write_action=trace_write_action,
        )
        for trace_write_action in service_execution["trace_write_actions"]
    ]
    next_action_execution = service_execution["next_action_execution"]
    if str(next_action_execution["kind"]) == "return":
        return_action = next_action_execution["return_action"]
        assert return_action is not None
        return _sanitize_tool_plan_item_payload_list(
            [
                *actions,
                *build_tool_plan_item_return_service_actions(
                    return_action=return_action,
                ),
            ]
        )

    continue_action = next_action_execution["continue_action"]
    return _sanitize_tool_plan_item_payload_list(
        [
            *actions,
            build_tool_plan_item_continue_service_action(
                continue_action=continue_action,
            ),
        ]
    )


def build_tool_plan_item_trace_write_service_action(
    *,
    trace_write_action: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "kind": "trace_write",
            "trace_step": trace_write_action["trace_step"],
            "trace_event": trace_write_action["trace_event"],
            "persist_force": bool(trace_write_action["persist_force"]),
        }
    )


def build_tool_plan_item_continue_service_action(
    *,
    continue_action: dict[str, object],
) -> dict[str, object]:
    return _sanitize_tool_plan_item_payload_dict(
        {
            "kind": "continue",
            "tool_observations": list(continue_action["tool_observations"]),
            "seq_increment": int(continue_action["seq_increment"]),
        }
    )


def build_tool_plan_item_return_service_actions(
    *,
    return_action: dict[str, object],
) -> list[dict[str, object]]:
    return _sanitize_tool_plan_item_payload_list(
        [
            {
                "kind": "complete_task",
                "kwargs": return_action["complete_task_kwargs"],
            },
            {
                "kind": "record_failure_event",
                "kwargs": return_action["failure_event_kwargs"],
            },
            {
                "kind": "emit_state",
                "event": "state",
                "data": return_action["state_event"],
            },
            {
                "kind": "return",
            },
        ]
    )


def build_tool_plan_item_service_effects_execution(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
    user_id: str,
    service_effects: dict[str, object],
) -> dict[str, object]:
    service_execution = {
        "trace_write_actions": list(service_effects["trace_write_actions"]),
        "next_action_execution": build_tool_plan_item_next_action_execution(
            task_id=task_id,
            trace_steps=trace_steps,
            user_id=user_id,
            next_action=service_effects["next_action"],
        ),
    }
    service_execution["service_actions"] = build_tool_plan_item_service_actions(
        service_execution=service_execution,
    )
    sanitized_service_execution = sanitize_tool_registry_diagnostics_artifact_payload(
        service_execution
    )
    assert isinstance(sanitized_service_execution, dict)
    return sanitized_service_execution


def build_tool_plan_item_service_execution(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
    user_id: str,
    loop_execution_result: dict[str, object],
) -> dict[str, object]:
    service_effects = build_tool_plan_item_service_effects(
        loop_execution_result=loop_execution_result,
    )
    return build_tool_plan_item_service_effects_execution(
        task_id=task_id,
        trace_steps=trace_steps,
        user_id=user_id,
        service_effects=service_effects,
    )


def build_tool_plan_item_service_effects(
    *,
    loop_execution_result: dict[str, object],
) -> dict[str, object]:
    stream_effects = build_tool_plan_item_stream_effects(
        loop_execution_result=loop_execution_result,
    )
    continue_update = build_tool_plan_item_continue_update(
        stream_effects=stream_effects,
    )
    terminal_effects = stream_effects["terminal_effects"]
    terminal_return_effects = (
        build_tool_plan_item_terminal_return_effects(
            terminal_effects=terminal_effects,
        )
        if terminal_effects is not None
        else None
    )
    should_return = bool(stream_effects["should_return"])
    next_action = build_tool_plan_item_next_action(
        continue_update=continue_update,
        terminal_return_effects=terminal_return_effects,
    )
    trace_writes = [
        {
            "step": trace_step,
            "event": trace_event,
            "force_persist": should_return,
        }
        for trace_step, trace_event in zip(
            stream_effects["trace_steps"],
            stream_effects["trace_events"],
        )
    ]
    trace_write_actions = [
        build_tool_plan_item_trace_write_action(trace_write=trace_write)
        for trace_write in trace_writes
    ]
    service_effects = {
        "trace_steps": stream_effects["trace_steps"],
        "trace_events": stream_effects["trace_events"],
        "trace_writes": trace_writes,
        "trace_write_actions": trace_write_actions,
        "continue_update": continue_update,
        "next_action": next_action,
        "tool_observations": continue_update["tool_observations"],
        "seq_increment": continue_update["seq_increment"],
        "should_return": should_return,
        "terminal_return_effects": terminal_return_effects,
    }
    sanitized_service_effects = sanitize_tool_registry_diagnostics_artifact_payload(
        service_effects
    )
    assert isinstance(sanitized_service_effects, dict)
    return sanitized_service_effects


def _extract_calc_expression(prompt: str) -> str | None:
    tagged = re.search(r"\[calc:(.+?)\]", prompt, flags=re.IGNORECASE)
    if tagged:
        expr = tagged.group(1).strip()
        return expr or None

    plain = re.search(r"(?:计算|calc)\s*[:：]?\s*([0-9+\-*/().%\s]{3,})", prompt)
    if plain:
        expr = plain.group(1).strip()
        return expr or None

    return None


def _safe_eval_expression(expr: str) -> float:
    tree = parse(expr, mode="eval")

    def _eval(node: object) -> float:
        if isinstance(node, Expression):
            return _eval(node.body)
        if isinstance(node, BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, Add):
                return left + right
            if isinstance(node.op, Sub):
                return left - right
            if isinstance(node.op, Mult):
                return left * right
            if isinstance(node.op, Div):
                return left / right
            if isinstance(node.op, Mod):
                return left % right
            if isinstance(node.op, Pow):
                return left**right
            raise ValueError("unsupported binary operator")
        if isinstance(node, UnaryOp):
            value = _eval(node.operand)
            if isinstance(node.op, UAdd):
                return value
            if isinstance(node.op, USub):
                return -value
            raise ValueError("unsupported unary operator")
        if isinstance(node, int | float):
            return float(node)
        if hasattr(node, "value") and isinstance(getattr(node, "value"), (int, float)):
            return float(getattr(node, "value"))
        raise ValueError("unsupported expression node")

    return _eval(tree)


def _extract_knowledge_base_id(prompt: str) -> str | None:
    tagged = re.search(r"\[kb:([a-zA-Z0-9_-]{1,64})\]", prompt)
    if not tagged:
        return None
    value = tagged.group(1).strip()
    return value or None


def _build_rule_based_tool_plan(
    prompt: str,
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> list[dict[str, object]]:
    normalized = prompt.strip().lower()
    settings = get_settings()
    knowledge_base_id = (
        _extract_knowledge_base_id(prompt) or settings.rag_default_knowledge_base_id
    )
    primary_planner_name = _get_enabled_planning_primary_tool_name(
        registry_provider=registry_provider,
    )
    retrieval_tool_name = _get_first_enabled_planning_tool_name_for_kind(
        "knowledge_retrieval",
        registry_provider=registry_provider,
    )
    calculator_tool_name = _get_first_enabled_planning_tool_name_for_kind(
        "local_calculator",
        registry_provider=registry_provider,
    )
    plan: list[dict[str, object]] = []
    if primary_planner_name is not None:
        plan.append(
            {
                "name": primary_planner_name,
                "input": {
                    "prompt_preview": prompt.strip()[:120],
                },
            }
        )

    if (
        retrieval_tool_name is not None
        and (
            "rag" in normalized
            or "知识" in normalized
            or "检索" in normalized
            or "context" in normalized
            or "[multi-tool]" in normalized
            or "[mock-multi-tool]" in normalized
        )
    ):
        plan.append(
            {
                "name": retrieval_tool_name,
                "input": {
                    "query": prompt.strip()[:80] or "default query",
                    "top_k": settings.rag_default_top_k,
                    "knowledge_base_id": knowledge_base_id,
                },
            }
        )

    calc_expr = _extract_calc_expression(prompt)
    if calc_expr and calculator_tool_name is not None:
        plan.append(
            {
                "name": calculator_tool_name,
                "input": {
                    "expression": calc_expr,
                },
            }
        )

    return plan


def _build_provider_tool_plan_prompt(
    prompt: str,
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> str:
    allowed_tool_names = _get_enabled_planning_optional_tool_names(
        registry_provider=registry_provider,
    )
    allowed_tool_names_text = ", ".join(allowed_tool_names) if allowed_tool_names else "none"
    allowed_tool_labels = [
        get_tool_display_name(name, registry_provider=registry_provider)
        for name in allowed_tool_names
    ]
    allowed_tool_labels_text = ", ".join(allowed_tool_labels) if allowed_tool_labels else "none"
    input_lines: list[str] = []
    for tool_name in allowed_tool_names:
        registration = resolve_tool_registration(
            tool_name,
            registry_provider=registry_provider,
        )
        if registration is None:
            continue
        semantic_kind = get_tool_semantic_kind(
            name=tool_name,
            registration=registration,
        )
        if semantic_kind == "knowledge_retrieval":
            input_lines.append(
                f"For {tool_name} input, include query, optional top_k, optional knowledge_base_id.\n"
            )
            continue
        if semantic_kind == "local_calculator":
            input_lines.append(
                f"For {tool_name} input, include expression.\n"
            )
    return (
        "You are the Task Planner for InsightAgent.\n"
        "Return JSON only with shape {\"tools\": [...]}.\n"
        f"Allowed tool names: {allowed_tool_names_text}.\n"
        f"Allowed tool labels: {allowed_tool_labels_text}.\n"
        "Do not include planner tools in the JSON; planner is added automatically.\n"
        + "".join(input_lines)
        + "If no extra tools are needed, return {\"tools\": []}.\n"
        + f"User request:\n{prompt.strip() or 'empty prompt'}"
    )


def _extract_provider_tool_plan_items_from_payload(
    payload: object,
) -> list[object] | None:
    if isinstance(payload, tuple):
        return list(payload)
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return None
    tools = payload.get("tools", payload.get("plan"))
    if isinstance(tools, tuple):
        return list(tools)
    if isinstance(tools, list):
        return tools
    raw_name = payload.get("name", payload.get("tool"))
    if isinstance(raw_name, str) and raw_name.strip():
        return [payload]
    return None


def _extract_provider_tool_plan_items(provider_content: object) -> list[object] | None:
    direct_items = _extract_provider_tool_plan_items_from_payload(provider_content)
    if direct_items is not None:
        return direct_items
    if not isinstance(provider_content, str):
        return None
    raw = provider_content.strip()
    if not raw:
        return None
    candidates = [raw]
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", raw, flags=re.DOTALL | re.IGNORECASE)
    candidates.extend(item.strip() for item in fenced if item.strip())

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        items = _extract_provider_tool_plan_items_from_payload(payload)
        if items is not None:
            return items
    return None


def _extract_provider_response_content(response: object) -> object:
    if isinstance(response, dict):
        if any(key in response for key in ("tools", "plan", "name", "tool")):
            return response
        if "content" in response:
            content = response.get("content")
            normalized_text = normalize_response_text(content)
            if normalized_text:
                return normalized_text
            return content
        output_text = response.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text
        text = response.get("text")
        if isinstance(text, str) and text.strip():
            return text
        normalized_text = extract_response_text(response)
        if normalized_text:
            return normalized_text
        return response
    content = getattr(response, "content", response)
    normalized_text = normalize_response_text(content)
    if normalized_text:
        return normalized_text
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text
    normalized_text = extract_response_text(response)
    if normalized_text:
        return normalized_text
    return content


def _normalize_provider_tool_plan_item(
    raw_item: object,
    *,
    registry_provider: ToolRegistryProvider | None = None,
) -> tuple[str, dict[str, object]] | None:
    if isinstance(raw_item, str):
        tool_name = _resolve_provider_tool_name(
            raw_item,
            registry_provider=registry_provider,
        )
        if not tool_name:
            return None
        return tool_name, {}
    if not isinstance(raw_item, dict):
        return None
    raw_name = raw_item.get("name", raw_item.get("tool", ""))
    tool_name = _resolve_provider_tool_name(
        raw_name,
        registry_provider=registry_provider,
    )
    if not tool_name:
        return None
    tool_input = raw_item.get("input")
    if not isinstance(tool_input, dict):
        tool_input = raw_item.get("arguments")
    if not isinstance(tool_input, dict):
        tool_input = raw_item.get("args")
    if not isinstance(tool_input, dict):
        tool_input = {
            key: value
            for key, value in raw_item.items()
            if key not in {"name", "tool", "input", "arguments", "args"}
        }
    if not isinstance(tool_input, dict):
        tool_input = {}
    return tool_name, dict(tool_input)


def _normalize_provider_tool_plan(
    raw_items: list[object],
    *,
    prompt: str,
    registry_provider: ToolRegistryProvider | None = None,
) -> list[dict[str, object]] | None:
    settings = get_settings()
    prompt_preview = prompt.strip()[:120]
    default_query = prompt.strip()[:80] or "default query"
    default_kb_id = (
        _extract_knowledge_base_id(prompt) or settings.rag_default_knowledge_base_id
    )
    fallback_calc_expression = _extract_calc_expression(prompt)
    primary_planner_name = _get_enabled_planning_primary_tool_name(
        registry_provider=registry_provider,
    )
    enabled_optional_tool_names = set(
        _get_enabled_planning_optional_tool_names(
            registry_provider=registry_provider,
        )
    )
    normalized_plan: list[dict[str, object]] = []
    seen_names: set[str] = set()
    saw_planner_tool = False
    if primary_planner_name is not None:
        normalized_plan.append(
            {
                "name": primary_planner_name,
                "input": {
                    "prompt_preview": prompt_preview,
                },
            }
        )
        seen_names.add(primary_planner_name)

    for raw_item in raw_items:
        normalized_item = _normalize_provider_tool_plan_item(
            raw_item,
            registry_provider=registry_provider,
        )
        if normalized_item is None:
            continue
        tool_name, tool_input = normalized_item
        if tool_name in seen_names or tool_name not in enabled_optional_tool_names:
            continue
        registration = resolve_tool_registration(
            tool_name,
            registry_provider=registry_provider,
        )
        tool_kind = (
            get_tool_semantic_kind(
                name=tool_name,
                registration=registration,
            )
            if registration is not None
            else None
        )
        if tool_kind == "task_planner":
            saw_planner_tool = True
            continue
        if tool_kind == "knowledge_retrieval":
            top_k = tool_input.get("top_k")
            if isinstance(top_k, bool):
                top_k = None
            if not isinstance(top_k, int) or top_k <= 0:
                top_k = settings.rag_default_top_k
            query = str(tool_input.get("query") or default_query)
            knowledge_base_id = str(
                tool_input.get("knowledge_base_id") or default_kb_id
            )
            normalized_plan.append(
                {
                    "name": tool_name,
                    "input": {
                        "query": query,
                        "top_k": top_k,
                        "knowledge_base_id": knowledge_base_id,
                    },
                }
            )
            seen_names.add(tool_name)
            continue
        if tool_kind == "local_calculator":
            expression = tool_input.get("expression")
            if not isinstance(expression, str) or not expression.strip():
                expression = fallback_calc_expression
            if not isinstance(expression, str) or not expression.strip():
                continue
            try:
                _safe_eval_expression(expression)
            except Exception:  # noqa: BLE001
                continue
            normalized_plan.append(
                {
                    "name": tool_name,
                    "input": {
                        "expression": expression,
                    },
                }
            )
            seen_names.add(tool_name)

    if not raw_items:
        return normalized_plan
    if primary_planner_name is not None and len(normalized_plan) == 1:
        if saw_planner_tool:
            return normalized_plan
        return None
    if primary_planner_name is None and not normalized_plan:
        return None
    return normalized_plan


def _build_provider_tool_plan(
    prompt: str,
    *,
    provider: object,
    registry_provider: ToolRegistryProvider | None = None,
) -> ToolPlanArtifacts | None:
    provider_name = str(getattr(provider, "provider", "")).strip().lower()
    generate = getattr(provider, "generate", None)
    if provider_name == "mock" or not callable(generate):
        return None
    planning_prompt = _build_provider_tool_plan_prompt(
        prompt,
        registry_provider=registry_provider,
    )
    response = generate(planning_prompt)
    raw_usage = (
        response.get("usage")
        if isinstance(response, dict)
        else getattr(response, "usage", None)
    )
    provider_usage = coerce_provider_usage(raw_usage)
    if provider_usage is None and isinstance(raw_usage, dict):
        provider_usage = ProviderUsage()
    if provider_usage is None:
        get_last_usage = getattr(provider, "get_last_usage", None)
        if callable(get_last_usage):
            provider_usage = coerce_provider_usage(get_last_usage())
    content = _extract_provider_response_content(response)
    if content is None:
        return ToolPlanArtifacts(
            tool_plan=[],
            planning_prompt=planning_prompt,
            provider_usage=provider_usage,
            planning_provider_attempted=True,
            planning_provider_used=False,
        )
    items = _extract_provider_tool_plan_items(content)
    if items is None:
        return ToolPlanArtifacts(
            tool_plan=[],
            planning_prompt=planning_prompt,
            provider_usage=provider_usage,
            planning_provider_attempted=True,
            planning_provider_used=False,
        )
    normalized_plan = _normalize_provider_tool_plan(
        items,
        prompt=prompt,
        registry_provider=registry_provider,
    )
    return ToolPlanArtifacts(
        tool_plan=normalized_plan or [],
        planning_prompt=planning_prompt,
        provider_usage=provider_usage,
        planning_provider_attempted=True,
        planning_provider_used=normalized_plan is not None,
    )


def build_tool_plan_artifacts(
    prompt: str,
    *,
    provider: object | None = None,
    registry_provider: ToolRegistryProvider | None = None,
) -> ToolPlanArtifacts:
    allowed_tool_names = get_enabled_planning_tool_names(
        registry_provider=registry_provider,
    )
    allowed_tool_labels = get_enabled_planning_tool_labels(
        registry_provider=registry_provider,
    )
    fallback_plan = _annotate_task_plan_tool_input(
        _build_rule_based_tool_plan(
            prompt,
            registry_provider=registry_provider,
        ),
        registry_provider=registry_provider,
    )
    if provider is None:
        return ToolPlanArtifacts(
            tool_plan=fallback_plan,
            allowed_tool_names=allowed_tool_names,
            allowed_tool_labels=allowed_tool_labels,
        )
    try:
        provider_plan = _build_provider_tool_plan(
            prompt,
            provider=provider,
            registry_provider=registry_provider,
        )
    except Exception:  # noqa: BLE001
        provider_plan = None
    if provider_plan is None:
        return ToolPlanArtifacts(
            tool_plan=fallback_plan,
            allowed_tool_names=allowed_tool_names,
            allowed_tool_labels=allowed_tool_labels,
        )
    if provider_plan.planning_provider_used:
        return replace(
            provider_plan,
            tool_plan=_annotate_task_plan_tool_input(
                provider_plan.tool_plan,
                registry_provider=registry_provider,
            ),
            allowed_tool_names=allowed_tool_names,
            allowed_tool_labels=allowed_tool_labels,
        )
    return ToolPlanArtifacts(
        tool_plan=fallback_plan,
        allowed_tool_names=allowed_tool_names,
        allowed_tool_labels=allowed_tool_labels,
        planning_prompt=provider_plan.planning_prompt,
        provider_usage=provider_plan.provider_usage,
        planning_provider_attempted=provider_plan.planning_provider_attempted,
        planning_provider_used=False,
    )


def build_tool_plan(
    prompt: str,
    *,
    provider: object | None = None,
    registry_provider: ToolRegistryProvider | None = None,
) -> list[dict[str, object]]:
    return build_tool_plan_artifacts(
        prompt,
        provider=provider,
        registry_provider=registry_provider,
    ).tool_plan


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
            return label
    return _humanize_tool_display_name(normalize_tool_registry_name(name))


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


def _normalize_tool_semantic_kind(kind: str | None) -> str | None:
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
            return _normalize_tool_semantic_kind(default_registration.kind)
        return _normalize_tool_semantic_kind(registration.kind)
    if default_registration is not None:
        return _normalize_tool_semantic_kind(default_registration.kind)
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
        return resolved_registration.result_output_keys
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
    should_infer_output_keys = explicit_runtime_semantic_kind is not None or (
        semantic_kind is not None and raw_kind is not None and raw_kind != semantic_kind
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
        semantic_family = get_tool_semantic_kind(
            name=normalized_name,
            registration=resolved_registration,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        )
        output_keys = _augment_http_json_local_calculator_output_keys(
            output_keys=output_keys,
            registration=resolved_registration,
            semantic_kind=semantic_kind,
            semantic_family=semantic_family,
        )
        return output_keys
    semantic_family = get_tool_semantic_kind(
        name=normalized_name,
        registration=resolved_registration,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
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
        return resolved_registration.result_preview_keys
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
    normalized_semantic_kind = _normalize_tool_semantic_kind(semantic_kind)
    normalized_semantic_family = _normalize_tool_semantic_kind(semantic_family)
    if (
        normalized_execution_kind != "http_json"
        or normalized_semantic_kind != "local_calculator"
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
        semantic_kind = get_tool_runtime_semantic_kind(
            name=tool_name,
            registration=registration,
        )
        semantic_family = get_tool_semantic_kind(
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
        label = registration.label.strip() or get_tool_display_name_from_registration(
            name=tool_name,
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
    normalized_output = dict(output)
    if _normalize_tool_execution_kind(registration.execution_kind) == "http_json":
        normalized_output = _normalize_http_json_safe_output_shape(normalized_output)
    normalized_name = normalize_tool_registry_name(registration.name)
    default_registration = _REGISTERED_TOOLS.get(normalized_name)
    explicit_runtime_tool_kind = _normalize_runtime_semantic_kind(
        registration.runtime_semantic_kind
    )
    desired_tool_kind = explicit_runtime_tool_kind or registration.kind
    if (
        default_registration is not None
        and registration.runner is default_registration.runner
        and registration.kind == default_registration.kind
        and desired_tool_kind == registration.kind
    ):
        return normalized_output

    current_kind = normalized_output.get("tool_kind")
    current_kind_text = str(current_kind).strip() if current_kind is not None else ""
    if not current_kind_text:
        normalized_output["tool_kind"] = desired_tool_kind
        return normalized_output
    if current_kind_text == desired_tool_kind:
        return normalized_output

    template_registration = _find_builtin_registration_by_runner(registration.runner)
    if (
        template_registration is not None
        and current_kind_text == template_registration.kind
        and desired_tool_kind != template_registration.kind
    ):
        normalized_output["tool_kind"] = desired_tool_kind
    elif (
        default_registration is not None
        and current_kind_text == default_registration.kind
        and desired_tool_kind != default_registration.kind
    ):
        normalized_output["tool_kind"] = desired_tool_kind
    elif (
        current_kind_text == registration.kind
        and desired_tool_kind != registration.kind
    ):
        normalized_output["tool_kind"] = desired_tool_kind
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
