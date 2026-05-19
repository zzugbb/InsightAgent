from __future__ import annotations

import json
import re
from ast import Add, BinOp, Div, Expression, Mod, Mult, Pow, Sub, UAdd, USub, UnaryOp, parse
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Iterator, Protocol

from app.config import get_settings
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
class ToolRegistrySettingsConfig:
    overrides: dict[str, ToolRegistration]
    disabled_tool_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConfiguredToolRegistryProviderPreflightSummaryModel:
    provider_source_name: str
    tool_count: int
    tool_names: tuple[str, ...]
    service_action_count: int
    service_action_kinds: tuple[str, ...]
    trace_write_count: int
    audit_event_count: int
    has_diagnostics: bool
    diagnostics_total: int
    skipped_total: int
    missing_total: int

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_source_name": self.provider_source_name,
            "tool_count": self.tool_count,
            "tool_names": self.tool_names,
            "service_action_count": self.service_action_count,
            "service_action_kinds": self.service_action_kinds,
            "trace_write_count": self.trace_write_count,
            "audit_event_count": self.audit_event_count,
            "has_diagnostics": self.has_diagnostics,
            "diagnostics_total": self.diagnostics_total,
            "skipped_total": self.skipped_total,
            "missing_total": self.missing_total,
        }


@dataclass(frozen=True)
class ConfiguredToolRegistryProviderPreflightResultModel:
    provider: ToolRegistryProvider
    provider_source_name: str
    runtime_artifacts: dict[str, object]
    service_execution: dict[str, object]
    trace_write_count: int
    audit_event_count: int
    summary: ConfiguredToolRegistryProviderPreflightSummaryModel

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "provider_source_name": self.provider_source_name,
            "runtime_artifacts": self.runtime_artifacts,
            "service_execution": self.service_execution,
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
            "entries": self.entries,
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
            "trace_step": self.trace_step,
            "trace_event": self.trace_event,
            "audit_detail": self.audit_detail,
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
            "selected_source_diagnostics": self.selected_source_diagnostics,
            "source_diagnostics": self.source_diagnostics,
            "diagnostics_runtime": self.diagnostics_runtime.to_dict(),
            "audit_event": self.audit_event,
        }


_TOOL_REGISTRY_PROFILE_CONFIGS: dict[str, ToolRegistrySettingsConfig] = {
    "default": ToolRegistrySettingsConfig(
        overrides={},
        disabled_tool_names=(),
    ),
    "planning_only": ToolRegistrySettingsConfig(
        overrides={},
        disabled_tool_names=("calc_eval", "mock_retrieve"),
    ),
    "retrieval_only": ToolRegistrySettingsConfig(
        overrides={},
        disabled_tool_names=("calc_eval", "mock_plan"),
    ),
    "calculator_only": ToolRegistrySettingsConfig(
        overrides={},
        disabled_tool_names=("mock_plan", "mock_retrieve"),
    ),
}

_TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS = (
    "skipped_registry_sources",
    "missing_registry_sources",
    "skipped_registry_files",
    "missing_registry_files",
    "skipped_registry_dirs",
    "missing_registry_dirs",
)


def normalize_tool_spec(tool_spec: dict[str, object]) -> ToolInvocation:
    name = str(tool_spec.get("name", "")).strip()
    tool_input = tool_spec.get("input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    return ToolInvocation(name=name, tool_input=tool_input)


def _run_mock_plan(*, tool_input: dict[str, object], prompt: str, user_id: str) -> dict[str, object]:
    del tool_input, prompt, user_id
    return {
        "plan": "Split task into analysis -> retrieval -> synthesis.",
        "echo": True,
    }


def _run_mock_retrieve(
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
    "mock_plan": ToolRegistration(
        name="mock_plan",
        kind="mock_planner",
        label="Mock Planner",
        retryable_by_default=True,
        default_timeout_ms=3_000,
        requires_user_context=True,
        supports_result_preview=True,
        runner=_run_mock_plan,
    ),
    "mock_retrieve": ToolRegistration(
        name="mock_retrieve",
        kind="mock_retrieval",
        label="Mock Retrieval",
        retryable_by_default=True,
        default_timeout_ms=5_000,
        requires_user_context=True,
        supports_result_preview=True,
        runner=_run_mock_retrieve,
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
    ),
}


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
    normalized = name.strip().lower()
    if normalized == "default":
        return get_default_tool_registry
    return None


def resolve_named_tool_registry_provider_reference(
    name: str,
    *,
    named_providers: dict[str, ToolRegistryProvider] | None = None,
    named_sources: dict[str, ToolRegistryProvider] | None = None,
) -> ToolRegistryProvider | None:
    normalized = name.strip().lower()
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
    normalized = name.strip().lower()
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
    normalized = name.strip().lower()
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
    if not isinstance(raw_source_name, str):
        return "default"
    normalized = raw_source_name.strip().lower()
    return normalized or "default"


def get_tool_registry_profile_name_from_settings(*, settings: object | None = None) -> str:
    if settings is None:
        settings = get_settings()
    raw_profile_name = getattr(settings, "tool_registry_profile", None)
    if not isinstance(raw_profile_name, str):
        return "default"
    normalized = raw_profile_name.strip().lower()
    return normalized or "default"


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
) -> dict[str, ToolRegistration]:
    if not isinstance(extra_tool_specs, dict):
        return {}
    extra_tools_settings = type(
        "ToolRegistryExtraToolSettings",
        (),
        {"tool_registry_extra_tools_json": json.dumps(extra_tool_specs, ensure_ascii=False)},
    )()
    return build_tool_registry_extra_tools_from_settings(settings=extra_tools_settings)


def build_tool_registry_extra_tools_from_file(
    *,
    registry_file: str,
) -> dict[str, ToolRegistration]:
    payload = load_tool_registry_file_payload(registry_file=registry_file)
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("extra_tools"), dict):
        payload = payload["extra_tools"]
    return build_tool_registry_extra_tools_from_specs(extra_tool_specs=payload)


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
            if not isinstance(values, tuple):
                continue
            for value in values:
                if not isinstance(value, str) or value in merged[key]:
                    continue
                merged[key].append(value)
    return _normalize_tool_registry_file_diagnostics(merged)


def _build_tool_registry_from_file_registry(
    *,
    registry_file: str,
    settings: object | None = None,
    _visited_files: set[str],
    _visited_dirs: set[str],
    _visited_sources: set[str],
    _diagnostics: dict[str, list[str]],
) -> dict[str, ToolRegistration]:
    resolved_path = _resolve_tool_registry_file_path(registry_file=registry_file)
    if resolved_path is None:
        return {}
    resolved_path_key = str(resolved_path)
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
        return build_tool_registry_extra_tools_from_specs(extra_tool_specs=payload)

    profile_name = str(payload.get("profile", "default")).strip().lower() or "default"
    profile_config = build_tool_registry_profile_settings_config(profile_name=profile_name)
    disabled_tool_names = set(profile_config.disabled_tool_names)
    raw_disabled_tool_names = payload.get("disabled_tool_names")
    if isinstance(raw_disabled_tool_names, list):
        disabled_tool_names.update(
            str(name).strip() for name in raw_disabled_tool_names if str(name).strip()
        )

    composed_base_registry: dict[str, ToolRegistration] | None = None
    raw_registry_sources = payload.get("registry_sources")
    if isinstance(raw_registry_sources, list):
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
            normalized_source_name = child_registry_source.strip().lower()
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
    if isinstance(raw_registry_files, list):
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
    if isinstance(raw_registry_dirs, list):
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
    extra_tools = build_tool_registry_extra_tools_from_specs(
        extra_tool_specs=extra_tool_specs
    )

    base_registry = build_tool_registry(
        base_registry=(
            composed_base_registry
            if composed_base_registry is not None
            else get_default_tool_registry()
        ),
        overrides=extra_tools or None,
    )
    source_overrides, disabled_tool_names = _build_registry_overrides_from_specs(
        override_specs=payload.get("overrides"),
        base_registry=base_registry,
        disabled_tool_names=disabled_tool_names,
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
) -> dict[str, object]:
    diagnostics: dict[str, list[str]] = {
        "skipped_registry_sources": [],
        "missing_registry_sources": [],
        "skipped_registry_files": [],
        "missing_registry_files": [],
        "skipped_registry_dirs": [],
        "missing_registry_dirs": [],
    }
    registry = _build_tool_registry_from_file_registry(
        registry_file=registry_file,
        settings=settings,
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
) -> dict[str, object]:
    artifacts = build_tool_registry_from_file_artifacts(
        registry_file=registry_file,
        settings=settings,
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
) -> dict[str, object]:
    artifacts = build_tool_registry_loader_from_file_artifacts(
        registry_file=registry_file,
        settings=settings,
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
) -> dict[str, ToolRegistration]:
    artifacts = build_tool_registry_from_file_artifacts(
        registry_file=registry_file,
        settings=settings,
    )
    return dict(artifacts["registry"])


def build_tool_registry_loader_from_file(
    *,
    registry_file: str,
    settings: object | None = None,
) -> ToolRegistryLoader | None:
    artifacts = build_tool_registry_loader_from_file_artifacts(
        registry_file=registry_file,
        settings=settings,
    )
    return artifacts["loader"]


def build_tool_registry_provider_from_file(
    *,
    registry_file: str,
    settings: object | None = None,
) -> ToolRegistryProvider | None:
    artifacts = build_tool_registry_provider_from_file_artifacts(
        registry_file=registry_file,
        settings=settings,
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
        normalized_loader_name = loader_name.strip().lower()
        diagnostics = _empty_tool_registry_file_diagnostics()
        registry_file = spec.get("registry_file")
        loader_reference = spec.get("loader")
        if isinstance(registry_file, str) and registry_file.strip():
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                build_tool_registry_loader_from_file_artifacts(
                    registry_file=registry_file,
                    settings=settings,
                )["diagnostics"],
            )
        elif (
            isinstance(loader_reference, str)
            and loader_reference.strip().lower() in loader_diagnostics
        ):
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                loader_diagnostics[loader_reference.strip().lower()],
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


def build_tool_registry_loader_factories_from_settings(
    *,
    settings: object | None = None,
) -> dict[str, ToolRegistryLoaderFactory]:
    if settings is None:
        settings = get_settings()
    raw_factories = getattr(settings, "tool_registry_loader_factories_json", None)
    if not isinstance(raw_factories, str) or not raw_factories.strip():
        return {}
    try:
        factory_specs = json.loads(raw_factories)
    except json.JSONDecodeError:
        return {}
    if not isinstance(factory_specs, dict):
        return {}

    factories: dict[str, ToolRegistryLoaderFactory] = {}
    for factory_name, spec in factory_specs.items():
        if not isinstance(factory_name, str) or not isinstance(spec, dict):
            continue
        registry_file = spec.get("registry_file")
        if isinstance(registry_file, str) and registry_file.strip():
            loader = build_tool_registry_loader_from_file(
                registry_file=registry_file,
                settings=settings,
            )
            if loader is None:
                continue
            factories[factory_name.strip().lower()] = (
                lambda settings=None, loader=loader: loader
            )
            continue
        target_name = spec.get("factory")
        if not isinstance(target_name, str) or not target_name.strip():
            continue
        resolved = resolve_named_tool_registry_loader_factory(
            target_name,
            named_loader_factories=factories,
        )
        if resolved is None:
            continue
        target_normalized = target_name.strip().lower()
        if target_normalized in _TOOL_REGISTRY_PROFILE_CONFIGS:
            resolved = _annotate_loader_factory_profile(
                resolved,
                profile_name=target_normalized,
            )
        factories[factory_name.strip().lower()] = resolved
    return factories


def build_tool_registry_provider_factories_from_settings(
    *,
    settings: object | None = None,
) -> dict[str, ToolRegistryProviderFactory]:
    if settings is None:
        settings = get_settings()
    raw_factories = getattr(settings, "tool_registry_provider_factories_json", None)
    if not isinstance(raw_factories, str) or not raw_factories.strip():
        return {}
    try:
        factory_specs = json.loads(raw_factories)
    except json.JSONDecodeError:
        return {}
    if not isinstance(factory_specs, dict):
        return {}

    factories: dict[str, ToolRegistryProviderFactory] = {}
    for factory_name, spec in factory_specs.items():
        if not isinstance(factory_name, str) or not isinstance(spec, dict):
            continue
        registry_file = spec.get("registry_file")
        if isinstance(registry_file, str) and registry_file.strip():
            provider = build_tool_registry_provider_from_file(
                registry_file=registry_file,
                settings=settings,
            )
            if provider is None:
                continue
            factories[factory_name.strip().lower()] = (
                lambda settings=None, provider=provider: provider
            )
            continue
        target_name = spec.get("factory")
        if not isinstance(target_name, str) or not target_name.strip():
            continue
        resolved = resolve_named_tool_registry_provider_factory(
            target_name,
            named_provider_factories=factories,
        )
        if resolved is None:
            continue
        target_normalized = target_name.strip().lower()
        if target_normalized in _TOOL_REGISTRY_PROFILE_CONFIGS:
            resolved = _annotate_provider_factory_profile(
                resolved,
                profile_name=target_normalized,
            )
        factories[factory_name.strip().lower()] = resolved
    return factories


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
        normalized_loader_factory_name = loader_factory_name.strip().lower()
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
            implicit_profile_name = str(profile_name_hint).strip().lower() or "default"
    elif isinstance(loader_name, str) and loader_name.strip():
        base_loader = resolve_named_tool_registry_loader(loader_name)
        if base_loader is None and named_loaders is not None:
            base_loader = named_loaders.get(loader_name.strip().lower())
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

    profile_name = str(spec.get("profile", implicit_profile_name)).strip().lower() or "default"
    profile_config = build_tool_registry_profile_settings_config(profile_name=profile_name)
    disabled_tool_names = set(profile_config.disabled_tool_names)
    raw_disabled_tool_names = spec.get("disabled_tool_names")
    if isinstance(raw_disabled_tool_names, list):
        disabled_tool_names.update(
            str(name).strip()
            for name in raw_disabled_tool_names
            if str(name).strip()
        )

    extra_tools = build_tool_registry_extra_tools_from_specs(
        extra_tool_specs=spec.get("extra_tools"),
    )
    base_registry = build_tool_registry(
        base_registry=known_base_registry if known_base_registry is not None else base_loader(),
        overrides=extra_tools or None,
    )
    source_overrides, disabled_tool_names = _build_registry_overrides_from_specs(
        override_specs=spec.get("overrides"),
        base_registry=base_registry,
        disabled_tool_names=disabled_tool_names,
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
    named_loaders: dict[str, ToolRegistryLoader] | None = None,
    named_providers: dict[str, ToolRegistryProvider] | None = None,
    named_sources: dict[str, ToolRegistryProvider] | None = None,
) -> ToolRegistryProvider | None:
    provider_factory_name = spec.get("provider_factory")
    provider_name = spec.get("provider")
    loader_name = spec.get("loader")
    registry_file = spec.get("registry_file")
    base_provider: ToolRegistryProvider | None = None
    base_loader: ToolRegistryLoader | None = None
    known_base_registry: dict[str, ToolRegistration] | None = None

    if isinstance(provider_factory_name, str) and provider_factory_name.strip():
        normalized_provider_factory_name = provider_factory_name.strip().lower()
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
    elif isinstance(provider_name, str) and provider_name.strip():
        base_provider = resolve_named_tool_registry_provider_reference(
            provider_name,
            named_providers=named_providers,
            named_sources=named_sources,
        )
        if base_provider is None:
            return None
        known_base_registry = dict(base_provider.load_tool_registry())
    elif isinstance(loader_name, str) and loader_name.strip():
        base_loader = resolve_named_tool_registry_loader(loader_name)
        if base_loader is None and named_loaders is not None:
            base_loader = named_loaders.get(loader_name.strip().lower())
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

    profile_name = str(spec.get("profile", "default")).strip().lower() or "default"
    profile_config = build_tool_registry_profile_settings_config(profile_name=profile_name)
    disabled_tool_names = set(profile_config.disabled_tool_names)
    raw_disabled_tool_names = spec.get("disabled_tool_names")
    if isinstance(raw_disabled_tool_names, list):
        disabled_tool_names.update(
            str(name).strip()
            for name in raw_disabled_tool_names
            if str(name).strip()
        )

    extra_tools = build_tool_registry_extra_tools_from_specs(
        extra_tool_specs=spec.get("extra_tools"),
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
    providers: dict[str, ToolRegistryProvider] = {}
    provider_diagnostics: dict[str, dict[str, tuple[str, ...]]] = {}
    for provider_name, spec in provider_specs.items():
        if not isinstance(provider_name, str) or not isinstance(spec, dict):
            continue
        normalized_provider_name = provider_name.strip().lower()
        diagnostics = _empty_tool_registry_file_diagnostics()
        registry_file = spec.get("registry_file")
        provider_reference = spec.get("provider")
        loader_reference = spec.get("loader")
        if isinstance(registry_file, str) and registry_file.strip():
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                build_tool_registry_provider_from_file_artifacts(
                    registry_file=registry_file,
                    settings=settings,
                )["diagnostics"],
            )
        elif (
            isinstance(provider_reference, str)
            and provider_reference.strip().lower() in provider_diagnostics
        ):
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                provider_diagnostics[provider_reference.strip().lower()],
            )
        elif (
            isinstance(loader_reference, str)
            and loader_reference.strip().lower() in loader_diagnostics
        ):
            diagnostics = _merge_tool_registry_file_diagnostics(
                diagnostics,
                loader_diagnostics[loader_reference.strip().lower()],
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
    if named_loaders is None:
        loader_artifacts = build_tool_registry_loaders_from_settings_artifacts(
            settings=settings
        )
        named_loaders = loader_artifacts["loaders"]
    loader_diagnostics = (
        loader_artifacts["loader_diagnostics"] if loader_artifacts is not None else {}
    )
    if named_providers is None:
        provider_artifacts = build_tool_registry_providers_from_settings_artifacts(
            settings=settings
        )
        named_providers = provider_artifacts["providers"]
    provider_diagnostics = (
        provider_artifacts["provider_diagnostics"] if provider_artifacts is not None else {}
    )
    sources: dict[str, ToolRegistryProvider] = {}
    source_diagnostics: dict[str, dict[str, tuple[str, ...]]] = {}
    for source_name, spec in source_specs.items():
        if not isinstance(source_name, str) or not isinstance(spec, dict):
            continue
        normalized_source_name = source_name.strip().lower()
        adapter_keys = {
            "provider_factory",
            "provider",
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
            provider_reference = spec.get("provider")
            loader_reference = spec.get("loader")
            if isinstance(registry_file, str) and registry_file.strip():
                diagnostics = _merge_tool_registry_file_diagnostics(
                    diagnostics,
                    build_tool_registry_provider_from_file_artifacts(
                        registry_file=registry_file,
                        settings=settings,
                    )["diagnostics"],
                )
            elif (
                isinstance(provider_reference, str)
                and provider_reference.strip().lower() in provider_diagnostics
            ):
                diagnostics = _merge_tool_registry_file_diagnostics(
                    diagnostics,
                    provider_diagnostics[provider_reference.strip().lower()],
                )
            elif (
                isinstance(loader_reference, str)
                and loader_reference.strip().lower() in loader_diagnostics
            ):
                diagnostics = _merge_tool_registry_file_diagnostics(
                    diagnostics,
                    loader_diagnostics[loader_reference.strip().lower()],
                )
            provider = build_tool_registry_provider_adapter(
                spec=spec,
                settings=settings,
                named_loaders=named_loaders,
                named_providers=named_providers,
                named_sources=sources,
            )
            if provider is None:
                continue
            sources[normalized_source_name] = provider
            source_diagnostics[normalized_source_name] = diagnostics
            continue

        extra_tools = build_tool_registry_extra_tools_from_specs(extra_tool_specs=spec)
        if not extra_tools:
            continue
        sources[normalized_source_name] = StaticToolRegistryProvider(registry=extra_tools)
        source_diagnostics[normalized_source_name] = _empty_tool_registry_file_diagnostics()
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

    extra_tools: dict[str, ToolRegistration] = {}
    for name, spec in extra_tool_specs.items():
        if not isinstance(name, str) or not isinstance(spec, dict):
            continue
        if name in _REGISTERED_TOOLS:
            continue
        template_name = spec.get("template")
        if not isinstance(template_name, str):
            continue
        template_registration = _REGISTERED_TOOLS.get(template_name)
        if template_registration is None:
            continue
        extra_tools[name] = replace(
            template_registration,
            name=name,
            kind=str(spec.get("kind", template_registration.kind)),
            label=str(spec.get("label", template_registration.label)),
            retryable_by_default=bool(
                spec.get("retryable_by_default", template_registration.retryable_by_default)
            ),
            default_timeout_ms=int(
                spec.get("default_timeout_ms", template_registration.default_timeout_ms)
            ),
            requires_user_context=bool(
                spec.get("requires_user_context", template_registration.requires_user_context)
            ),
            supports_result_preview=bool(
                spec.get("supports_result_preview", template_registration.supports_result_preview)
            ),
        )
    return extra_tools


def _build_registry_overrides_from_specs(
    *,
    override_specs: object,
    base_registry: dict[str, ToolRegistration],
    disabled_tool_names: set[str],
) -> tuple[dict[str, ToolRegistration], set[str]]:
    if not isinstance(override_specs, dict):
        return {}, disabled_tool_names

    overrides: dict[str, ToolRegistration] = {}
    for name, spec in override_specs.items():
        if not isinstance(name, str) or not isinstance(spec, dict):
            continue
        base_registration = base_registry.get(name)
        if base_registration is None:
            continue
        if spec.get("enabled") is False:
            disabled_tool_names.add(name)
        elif spec.get("enabled") is True:
            disabled_tool_names.discard(name)
        metadata_keys = {
            "kind",
            "label",
            "retryable_by_default",
            "default_timeout_ms",
            "requires_user_context",
            "supports_result_preview",
        }
        if not any(key in spec for key in metadata_keys):
            continue
        overrides[name] = replace(
            base_registration,
            kind=str(spec.get("kind", base_registration.kind)),
            label=str(spec.get("label", base_registration.label)),
            retryable_by_default=bool(
                spec.get("retryable_by_default", base_registration.retryable_by_default)
            ),
            default_timeout_ms=int(
                spec.get("default_timeout_ms", base_registration.default_timeout_ms)
            ),
            requires_user_context=bool(
                spec.get("requires_user_context", base_registration.requires_user_context)
            ),
            supports_result_preview=bool(
                spec.get("supports_result_preview", base_registration.supports_result_preview)
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
            disabled_tool_names=profile_config.disabled_tool_names,
        )
    try:
        override_specs = json.loads(raw_overrides)
    except json.JSONDecodeError:
        return ToolRegistrySettingsConfig(
            overrides=dict(extra_tools),
            disabled_tool_names=profile_config.disabled_tool_names,
        )
    if not isinstance(override_specs, dict):
        return ToolRegistrySettingsConfig(
            overrides=dict(extra_tools),
            disabled_tool_names=profile_config.disabled_tool_names,
        )

    overrides: dict[str, ToolRegistration] = dict(extra_tools)
    disabled_tool_names = set(profile_config.disabled_tool_names)
    source_overrides, disabled_tool_names = _build_registry_overrides_from_specs(
        override_specs=override_specs,
        base_registry=known_registrations,
        disabled_tool_names=disabled_tool_names,
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
        "selected_source_diagnostics": source_artifacts["source_diagnostics"].get(
            provider_source_name,
            _empty_tool_registry_file_diagnostics(),
        ),
        "source_diagnostics": source_artifacts["source_diagnostics"],
    }


def build_tool_registry_diagnostics_summary_model(
    *,
    diagnostics: dict[str, tuple[str, ...]],
) -> ToolRegistryDiagnosticsSummaryModel:
    entries: list[dict[str, object]] = []
    skipped_total = 0
    missing_total = 0
    for key in _TOOL_REGISTRY_FILE_DIAGNOSTIC_KEYS:
        values = diagnostics.get(key, ())
        if not isinstance(values, tuple) or not values:
            continue
        kind, target = key.split("_", 1)
        entry = {
            "kind": kind,
            "target": target,
            "count": len(values),
            "values": values,
        }
        entries.append(entry)
        if kind == "skipped":
            skipped_total += len(values)
        elif kind == "missing":
            missing_total += len(values)
    return ToolRegistryDiagnosticsSummaryModel(
        has_diagnostics=bool(entries),
        skipped_total=skipped_total,
        missing_total=missing_total,
        total=skipped_total + missing_total,
        entries=tuple(entries),
    )


def build_tool_registry_diagnostics_summary(
    *,
    diagnostics: dict[str, tuple[str, ...]],
) -> dict[str, object]:
    return build_tool_registry_diagnostics_summary_model(
        diagnostics=diagnostics,
    ).to_dict()


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
        "content": (
            "Tool registry diagnostics: "
            f"source={provider_source_name} "
            f"skipped={int(summary.skipped_total)} "
            f"missing={int(summary.missing_total)}"
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
    return {
        "kind": "record_audit_event",
        "kwargs": audit_event,
    }


def build_tool_registry_diagnostics_trace_service_action(
    *,
    trace_step: dict[str, object],
    trace_event: dict[str, object],
    persist_force: bool = True,
) -> dict[str, object]:
    return {
        "kind": "internal_trace_write",
        "trace_step": trace_step,
        "trace_event": trace_event,
        "persist_force": bool(persist_force),
    }


def build_configured_tool_registry_provider_runtime_service_actions(
    *,
    runtime_artifacts: dict[str, object],
) -> list[dict[str, object]]:
    service_actions: list[dict[str, object]] = []
    diagnostics_runtime = runtime_artifacts.get("diagnostics_runtime")
    if isinstance(diagnostics_runtime, dict):
        trace_step = diagnostics_runtime.get("trace_step")
        trace_event = diagnostics_runtime.get("trace_event")
        if isinstance(trace_step, dict) and isinstance(trace_event, dict):
            service_actions.append(
                build_tool_registry_diagnostics_trace_service_action(
                    trace_step=trace_step,
                    trace_event=trace_event,
                )
            )
    audit_event = runtime_artifacts.get("audit_event")
    if isinstance(audit_event, dict):
        service_actions.append(
            build_tool_registry_diagnostics_audit_service_action(
                audit_event=audit_event,
            )
        )
    return service_actions


def execute_configured_tool_registry_provider_runtime_service_actions(
    *,
    service_actions: list[dict[str, object]],
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
) -> dict[str, object]:
    trace_write_count = 0
    audit_event_count = 0
    for service_action in service_actions:
        kind = str(service_action.get("kind"))
        if kind == "internal_trace_write":
            trace_step = service_action.get("trace_step")
            if not isinstance(trace_step, dict):
                continue
            trace_steps.append(trace_step)
            persist_trace_fn(force=bool(service_action.get("persist_force")))
            trace_write_count += 1
            continue
        if kind != "record_audit_event":
            continue
        kwargs = service_action.get("kwargs")
        if not isinstance(kwargs, dict):
            continue
        record_audit_event_fn(**kwargs)
        audit_event_count += 1
    return {
        "trace_write_count": trace_write_count,
        "audit_event_count": audit_event_count,
    }


def build_configured_tool_registry_provider_service_execution(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    settings: object | None = None,
) -> dict[str, object]:
    runtime_artifacts = build_configured_tool_registry_provider_runtime_artifacts(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        settings=settings,
    )
    return {
        "provider": runtime_artifacts["provider"],
        "provider_source_name": runtime_artifacts["provider_source_name"],
        "runtime_artifacts": runtime_artifacts,
        "service_actions": build_configured_tool_registry_provider_runtime_service_actions(
            runtime_artifacts=runtime_artifacts,
        ),
    }


def execute_configured_tool_registry_provider_service_execution(
    *,
    service_execution: dict[str, object],
    trace_steps: list[dict[str, object]],
    persist_trace_fn: Callable[..., None],
    record_audit_event_fn: Callable[..., None],
) -> dict[str, object]:
    execution_result = execute_configured_tool_registry_provider_runtime_service_actions(
        service_actions=list(service_execution["service_actions"]),
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
    )
    return {
        "provider": service_execution["provider"],
        "provider_source_name": service_execution["provider_source_name"],
        "runtime_artifacts": service_execution["runtime_artifacts"],
        **execution_result,
    }


def build_configured_tool_registry_provider_preflight_summary_model(
    *,
    preflight_result: dict[str, object],
) -> ConfiguredToolRegistryProviderPreflightSummaryModel:
    runtime_artifacts = preflight_result.get("runtime_artifacts")
    has_diagnostics = False
    diagnostics_total = 0
    skipped_total = 0
    missing_total = 0
    if isinstance(runtime_artifacts, dict):
        diagnostics_runtime = runtime_artifacts.get("diagnostics_runtime")
        if isinstance(diagnostics_runtime, dict):
            summary = diagnostics_runtime.get("summary")
            if isinstance(summary, dict):
                has_diagnostics = bool(summary.get("has_diagnostics"))
                diagnostics_total = int(summary.get("total", 0) or 0)
                skipped_total = int(summary.get("skipped_total", 0) or 0)
                missing_total = int(summary.get("missing_total", 0) or 0)
    provider = preflight_result.get("provider")
    tool_count = 0
    tool_names: tuple[str, ...] = ()
    if hasattr(provider, "load_tool_registry") and callable(
        getattr(provider, "load_tool_registry", None)
    ):
        tool_registry = provider.load_tool_registry()
        tool_count = len(tool_registry)
        tool_names = tuple(sorted(tool_registry))
    service_execution = preflight_result.get("service_execution")
    service_action_count = 0
    service_action_kinds: tuple[str, ...] = ()
    if isinstance(service_execution, dict):
        service_actions = service_execution.get("service_actions")
        if isinstance(service_actions, list):
            service_action_count = len(service_actions)
            service_action_kinds = tuple(
                str(item.get("kind")) for item in service_actions if isinstance(item, dict)
            )
    return ConfiguredToolRegistryProviderPreflightSummaryModel(
        provider_source_name=str(preflight_result["provider_source_name"]),
        tool_count=tool_count,
        tool_names=tool_names,
        service_action_count=service_action_count,
        service_action_kinds=service_action_kinds,
        trace_write_count=int(preflight_result["trace_write_count"]),
        audit_event_count=int(preflight_result["audit_event_count"]),
        has_diagnostics=has_diagnostics,
        diagnostics_total=diagnostics_total,
        skipped_total=skipped_total,
        missing_total=missing_total,
    )


def build_configured_tool_registry_provider_preflight_summary(
    *,
    preflight_result: dict[str, object],
) -> dict[str, object]:
    return build_configured_tool_registry_provider_preflight_summary_model(
        preflight_result=preflight_result,
    ).to_dict()


def build_configured_tool_registry_provider_preflight_result_model(
    *,
    service_execution: dict[str, object],
    execution_result: dict[str, object],
) -> ConfiguredToolRegistryProviderPreflightResultModel:
    preflight_result_payload = {
        **execution_result,
        "service_execution": service_execution,
    }
    summary = build_configured_tool_registry_provider_preflight_summary_model(
        preflight_result=preflight_result_payload,
    )
    return ConfiguredToolRegistryProviderPreflightResultModel(
        provider=execution_result["provider"],
        provider_source_name=str(execution_result["provider_source_name"]),
        runtime_artifacts=execution_result["runtime_artifacts"],
        service_execution=service_execution,
        trace_write_count=int(execution_result["trace_write_count"]),
        audit_event_count=int(execution_result["audit_event_count"]),
        summary=summary,
    )


def build_configured_tool_registry_provider_preflight_result(
    *,
    service_execution: dict[str, object],
    execution_result: dict[str, object],
) -> dict[str, object]:
    return build_configured_tool_registry_provider_preflight_result_model(
        service_execution=service_execution,
        execution_result=execution_result,
    ).to_dict()


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
    service_execution = build_configured_tool_registry_provider_service_execution(
        task_id=task_id,
        step_id=step_id,
        seq=seq,
        model=model,
        settings=settings,
    )
    execution_result = execute_configured_tool_registry_provider_service_execution(
        service_execution=service_execution,
        trace_steps=trace_steps,
        persist_trace_fn=persist_trace_fn,
        record_audit_event_fn=record_audit_event_fn,
    )
    return build_configured_tool_registry_provider_preflight_result(
        service_execution=service_execution,
        execution_result=execution_result,
    )


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
        for name in disabled_tool_names:
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
    return provider_stack.load_tool_registry().get(name)


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
        raise MockToolExecutionError(f"Unknown mock tool: {name}", fatal=True)
    return registration


def maybe_raise_mock_tool_execution_error(*, name: str, prompt: str, attempt: int) -> None:
    del name
    normalized = prompt.strip().lower()

    if "[mock-tool-fatal]" in normalized:
        raise MockToolExecutionError(
            "Mock tool fatal error: planner contract validation failed.",
            fatal=True,
        )

    if "[mock-tool-error]" in normalized and attempt == 0:
        raise MockToolExecutionError(
            "Mock tool transient error: plan source unavailable on first attempt.",
            fatal=False,
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
    requires_user_context = tool_requires_user_context(
        name,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    effective_user_id = user_id if requires_user_context else ""
    return ToolRuntimeContext(
        name=name,
        prompt=prompt,
        user_id=effective_user_id,
        attempt=attempt,
        registration=registration,
        retryable_by_default=is_tool_retryable_by_default(
            name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        default_timeout_ms=get_tool_default_timeout_ms(
            name,
            registry=registry,
            registry_provider=registry_provider,
            registry_loader=registry_loader,
        ),
        requires_user_context=requires_user_context,
    )


def build_tool_result_preview(
    *,
    name: str,
    output: dict[str, object],
    registry: dict[str, ToolRegistration] | None = None,
) -> dict[str, object] | None:
    registration = resolve_tool_registration(name, registry=registry)
    if registration is None:
        return output
    if not registration.supports_result_preview:
        return None
    return output


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
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "step_id": step_id,
        "status": "done",
        "latency_ms": max(1, get_tool_default_timeout_ms(name) // 250),
        "output_preview": build_tool_result_preview(name=name, output=output),
        "retry_count": retry_count,
    }


def build_tool_success_meta(
    *,
    name: str,
    tool_input: dict[str, object],
    output: dict[str, object],
    retry_count: int,
    last_error: str | None,
) -> dict[str, object]:
    return {
        "tool": {
            "name": name,
            "input": tool_input,
            "output": output,
            "status": "done",
            "retry_count": retry_count,
            "error": last_error,
        },
    }


def build_tool_error_meta(
    *,
    name: str,
    tool_input: dict[str, object],
    retry_count: int,
    error_message: str,
) -> dict[str, object]:
    return {
        "tool": {
            "name": name,
            "input": tool_input,
            "status": "error",
            "retry_count": retry_count,
            "error": error_message,
        },
    }


def build_tool_start_payload(
    *,
    task_id: str,
    step_id: str,
    name: str,
    tool_input: dict[str, object],
    retry_count: int,
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "step_id": step_id,
        "name": name,
        "input": tool_input,
        "retry_count": retry_count,
    }


def build_tool_error_payload(
    *,
    task_id: str,
    step_id: str,
    error_message: str,
    retry_count: int,
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "step_id": step_id,
        "status": "error",
        "latency_ms": 12,
        "output_preview": {"error": error_message},
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
) -> dict[str, object]:
    return {
        "model": model,
        "step_type": "tool_call",
        "label": label,
        "retryCount": 0,
        "tokens": token_count,
        "cost_estimate": None,
        "tool": {
            "name": name,
            "input": tool_input,
            "status": "running",
            "retry_count": 0,
        },
    }


def build_action_step_initial_step(
    *,
    step_id: str,
    seq: int,
    name: str,
    meta: dict[str, object],
) -> dict[str, object]:
    return {
        "id": step_id,
        "seq": seq,
        "type": "action",
        "content": f"Tool running: {name}",
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
) -> dict[str, object]:
    return {
        **action_step,
        "content": f"Tool done: {name}",
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
) -> dict[str, object]:
    return {
        **action_step,
        "content": f"Tool error: {name}",
        "meta": {
            **dict(action_step.get("meta", {})),
            "step_type": "tool_call",
            "retryCount": retry_count,
            "tokens": token_count,
            **build_tool_error_meta(
                name=name,
                tool_input=tool_input,
                retry_count=retry_count,
                error_message=error_message,
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
) -> dict[str, dict[str, object]]:
    return {
        "tool_start": build_tool_start_payload(
            task_id=task_id,
            step_id=step_id,
            name=name,
            tool_input=tool_input,
            retry_count=attempt,
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
        "start_events": build_tool_attempt_start_events(
            task_id=task_id,
            step_id=step_id,
            name=name,
            tool_input=tool_input,
            attempt=attempt,
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
) -> dict[str, object]:
    return build_tool_plan_item_execution(
        task_id=task_id,
        iteration_ctx=iteration_ctx,
        action_step=action_step,
        runtime_ctx=attempt_bundle["runtime_ctx"],
        name=name,
        tool_input=tool_input,
        output=output,
        exc=exc,
        token_count=token_count,
        last_error=last_error,
        model=model,
        rag_step_id=rag_step_id,
        rag_token_count=rag_token_count,
    )


def build_tool_attempt_loop_result(
    *,
    attempt_execution: dict[str, object],
) -> dict[str, object]:
    return {
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


def build_tool_attempt_loop_terminal_result(
    *,
    loop_result: dict[str, object],
) -> dict[str, object]:
    terminal_effects = loop_result["terminal_effects"]
    return {
        "should_return": terminal_effects is not None,
        "terminal_effects": terminal_effects,
    }


def build_tool_plan_item_retry_loop_result(
    *,
    loop_result: dict[str, object],
) -> dict[str, object]:
    success_effects = loop_result["success_effects"]
    terminal_effects = loop_result["terminal_effects"]
    trace_event = (
        success_effects["trace"]
        if success_effects is not None
        else terminal_effects["trace"]
        if terminal_effects is not None
        else None
    )
    return {
        "outcome": "success" if success_effects is not None else "terminal_failure",
        "trace_event": trace_event,
        "success_effects": success_effects,
        "terminal_effects": terminal_effects,
    }


def build_tool_plan_item_retry_loop_execution_result(
    *,
    loop_result: dict[str, object],
) -> dict[str, object]:
    retry_loop_result = build_tool_plan_item_retry_loop_result(
        loop_result=loop_result,
    )
    loop_terminal_result = build_tool_attempt_loop_terminal_result(
        loop_result=loop_result,
    )
    return {
        "outcome": retry_loop_result["outcome"],
        "trace_event": retry_loop_result["trace_event"],
        "success_effects": retry_loop_result["success_effects"],
        "terminal_effects": retry_loop_result["terminal_effects"],
        "should_return": loop_terminal_result["should_return"],
        "loop_result": loop_result,
        "retry_loop_result": retry_loop_result,
        "loop_terminal_result": loop_terminal_result,
    }


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
                tool_input=tool_input,
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
                tool_input=tool_input,
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
                tool_input=tool_input,
                output=None,
                exc=exc,
                token_count=estimate_token_count(str(exc)),
                last_error=None,
                model=model,
                rag_step_id=make_step_id(),
                rag_token_count=0,
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
        service_execution["loop_execution_result"] = loop_execution_result
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
    for service_action in service_actions:
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
) -> dict[str, dict[str, object]]:
    return {
        "tool_end": build_tool_end_payload(
            name=name,
            task_id=task_id,
            step_id=step_id,
            output=output,
            retry_count=retry_count,
        )
    }


def build_tool_attempt_error_events(
    *,
    task_id: str,
    step_id: str,
    error_message: str,
    retry_count: int,
) -> dict[str, dict[str, object]]:
    return {
        "tool_end": build_tool_error_payload(
            task_id=task_id,
            step_id=step_id,
            error_message=error_message,
            retry_count=retry_count,
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
        ),
        "events": build_tool_attempt_success_events(
            task_id=task_id,
            step_id=step_id,
            name=name,
            output=output,
            retry_count=retry_count,
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
) -> dict[str, object]:
    error_message = str(exc)
    retry_count = runtime_ctx.attempt + 1
    retryable = compute_tool_retry_decision(ctx=runtime_ctx, exc=exc)
    return {
        "action_step": build_tool_step_error_update(
            action_step=action_step,
            name=name,
            tool_input=tool_input,
            retry_count=retry_count,
            token_count=token_count,
            error_message=error_message,
        ),
        "events": {
            **build_tool_attempt_error_events(
                task_id=task_id,
                step_id=step_id,
                error_message=error_message,
                retry_count=retry_count,
            ),
            "error": {
                "task_id": task_id,
                "message": error_message,
                "code": "tool_execution_error",
                "fatal": not retryable,
                "retryable": retryable,
                "retryCount": retry_count,
                "step_id": step_id,
            },
        },
        "retryable": retryable,
        "error_message": error_message,
        "retry_count": retry_count,
    }


def build_tool_step_output(action_step: dict[str, object]) -> dict[str, object] | None:
    tool_meta = action_step.get("meta") if isinstance(action_step, dict) else None
    tool_obj = (
        tool_meta.get("tool")
        if isinstance(tool_meta, dict) and isinstance(tool_meta.get("tool"), dict)
        else None
    )
    output = tool_obj.get("output") if isinstance(tool_obj, dict) else None
    return output if isinstance(output, dict) else None


def build_tool_observation_entry(*, name: str, output: dict[str, object] | None) -> str:
    return f"{name}: {json.dumps(output, ensure_ascii=False)}"


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
    return {
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


def build_tool_rag_step(
    *,
    step_id: str,
    seq: int,
    model: str,
    chunks: list[str],
    knowledge_base_id: str,
    token_count: int,
) -> dict[str, object]:
    return {
        "id": step_id,
        "seq": seq,
        "type": "thought",
        "content": "Retrieved snippets from mock knowledge base.",
        "meta": {
            "model": model,
            "step_type": "rag_retrieval",
            "tokens": token_count,
            "cost_estimate": None,
            "rag": {
                "chunks": chunks,
                "knowledge_base_id": knowledge_base_id,
            },
        },
    }


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
    return {
        "outcome": outcome,
        "action_step": action_step,
        "events": events,
        "retryable": retryable,
        "error_message": error_message,
        "retry_count": retry_count,
    }


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
) -> dict[str, object]:
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
) -> dict[str, object]:
    return {
        "step_id": step_id,
        "action_step": build_action_step_initial_step(
            step_id=step_id,
            seq=seq,
            name=name,
            meta=build_action_step_initial_meta(
                name=name,
                tool_input=tool_input,
                model=model,
                label=label,
                token_count=token_count,
            ),
        ),
    }


def build_tool_iteration_success_artifacts(
    *,
    task_id: str,
    step_id: str,
    action_step: dict[str, object],
    name: str,
) -> dict[str, object]:
    output = build_tool_step_output(action_step)
    return {
        "trace": build_tool_trace_event(
            task_id=task_id,
            step_id=step_id,
            step=action_step,
        ),
        "observation": build_tool_observation_entry(name=name, output=output),
        "output": output,
    }


def build_tool_rag_followup(
    *,
    task_id: str,
    step_id: str,
    seq: int,
    model: str,
    tool_name: str,
    output: dict[str, object] | None,
    token_count: int,
) -> dict[str, object] | None:
    if tool_name != "mock_retrieve" or not isinstance(output, dict):
        return None
    chunks = output.get("chunks")
    if not isinstance(chunks, list):
        return None
    kb = output.get("knowledge_base_id")
    step = build_tool_rag_step(
        step_id=step_id,
        seq=seq,
        model=model,
        chunks=[str(x) for x in chunks],
        knowledge_base_id=str(kb) if kb else get_settings().rag_default_knowledge_base_id,
        token_count=token_count,
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
) -> dict[str, object]:
    start_events = build_tool_attempt_start_events(
        task_id=task_id,
        step_id=step_id,
        name=name,
        tool_input=tool_input,
        attempt=runtime_ctx.attempt,
    )
    outcome = build_tool_attempt_outcome(
        task_id=task_id,
        step_id=step_id,
        action_step=dict(action_step),
        runtime_ctx=runtime_ctx,
        name=name,
        tool_input=tool_input,
        output=output,
        exc=exc,
        token_count=token_count,
        last_error=last_error,
    )
    if outcome["outcome"] == "success":
        return {
            "start_events": start_events,
            "outcome": outcome,
            "success_artifacts": build_tool_iteration_success_artifacts(
                task_id=task_id,
                step_id=step_id,
                action_step=outcome["action_step"],
                name=name,
            ),
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
    return {
        "outcome": outcome,
        "action_step": action_step,
        "last_error": last_error,
        "success_bundle": success_bundle,
        "terminal_failure": terminal_failure,
    }


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
    )
    success_artifacts = iteration_execution.get("success_artifacts")
    rag_followup = None
    if success_artifacts is not None:
        success_output = success_artifacts["output"]
        rag_followup = build_tool_rag_followup(
            task_id=task_id,
            step_id=rag_step_id,
            seq=int(action_step.get("seq", 0)) + 1,
            model=model,
            tool_name=name,
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
        return {
            "trace_steps": trace_steps,
            "trace_events": trace_events,
            "observation": success_effects["observation"],
            "tool_observations": [success_effects["observation"]],
            "terminal_effects": None,
            "seq_increment": 1 if rag_followup is not None else 0,
            "should_return": False,
        }

    assert terminal_effects is not None
    return {
        "trace_steps": [terminal_effects["trace_step"]],
        "trace_events": [terminal_effects["trace"]],
        "observation": None,
        "tool_observations": [],
        "terminal_effects": terminal_effects,
        "seq_increment": 0,
        "should_return": bool(loop_execution_result["should_return"]),
    }


def build_tool_plan_item_terminal_return_effects(
    *,
    terminal_effects: dict[str, object],
) -> dict[str, object]:
    return {
        "task_status": terminal_effects["status"],
        "state_event": terminal_effects["state"],
        "failure_event": {
            "event_type": "task_failed",
            "code": "tool_execution_error",
            "message": terminal_effects["error_message"],
            "detail": terminal_effects["audit_detail"],
        },
    }


def build_tool_plan_item_continue_update(
    *,
    stream_effects: dict[str, object],
) -> dict[str, object]:
    return {
        "tool_observations": list(stream_effects["tool_observations"]),
        "seq_increment": int(stream_effects["seq_increment"]),
    }


def build_tool_plan_item_continue_action(
    *,
    continue_update: dict[str, object],
) -> dict[str, object]:
    return {
        "tool_observations": list(continue_update["tool_observations"]),
        "seq_increment": int(continue_update["seq_increment"]),
    }


def build_tool_plan_item_next_action(
    *,
    continue_update: dict[str, object],
    terminal_return_effects: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "kind": "return" if terminal_return_effects is not None else "continue",
        "continue_update": continue_update,
        "terminal_return_effects": terminal_return_effects,
    }


def build_tool_plan_item_return_action(
    *,
    task_id: str,
    trace_steps: list[dict[str, object]],
    user_id: str,
    terminal_return_effects: dict[str, object],
) -> dict[str, object]:
    return {
        "complete_task_kwargs": {
            "task_id": task_id,
            "trace_steps": trace_steps,
            "user_id": user_id,
            "status": str(terminal_return_effects["task_status"]),
        },
        "failure_event_kwargs": terminal_return_effects["failure_event"],
        "state_event": terminal_return_effects["state_event"],
    }


def build_tool_plan_item_trace_write_action(
    *,
    trace_write: dict[str, object],
) -> dict[str, object]:
    return {
        "trace_step": trace_write["step"],
        "trace_event": trace_write["event"],
        "persist_force": bool(trace_write["force_persist"]),
    }


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
        return {
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
    return {
        "kind": "continue",
        "continue_update": next_action["continue_update"],
        "continue_action": continue_action,
        "return_action": None,
    }


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
        return [
            *actions,
            *build_tool_plan_item_return_service_actions(
                return_action=return_action,
            ),
        ]

    continue_action = next_action_execution["continue_action"]
    return [
        *actions,
        build_tool_plan_item_continue_service_action(
            continue_action=continue_action,
        ),
    ]


def build_tool_plan_item_trace_write_service_action(
    *,
    trace_write_action: dict[str, object],
) -> dict[str, object]:
    return {
        "kind": "trace_write",
        "trace_step": trace_write_action["trace_step"],
        "trace_event": trace_write_action["trace_event"],
        "persist_force": bool(trace_write_action["persist_force"]),
    }


def build_tool_plan_item_continue_service_action(
    *,
    continue_action: dict[str, object],
) -> dict[str, object]:
    return {
        "kind": "continue",
        "tool_observations": list(continue_action["tool_observations"]),
        "seq_increment": int(continue_action["seq_increment"]),
    }


def build_tool_plan_item_return_service_actions(
    *,
    return_action: dict[str, object],
) -> list[dict[str, object]]:
    return [
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
    return service_execution


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
    return {
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


def build_tool_plan(prompt: str) -> list[dict[str, object]]:
    normalized = prompt.strip().lower()
    settings = get_settings()
    knowledge_base_id = (
        _extract_knowledge_base_id(prompt) or settings.rag_default_knowledge_base_id
    )
    plan: list[dict[str, object]] = [
        {
            "name": "mock_plan",
            "input": {
                "prompt_preview": prompt.strip()[:120],
            },
        }
    ]

    if (
        "rag" in normalized
        or "知识" in normalized
        or "检索" in normalized
        or "context" in normalized
        or "[mock-multi-tool]" in normalized
    ):
        plan.append(
            {
                "name": "mock_retrieve",
                "input": {
                    "query": prompt.strip()[:80] or "default query",
                    "top_k": settings.rag_default_top_k,
                    "knowledge_base_id": knowledge_base_id,
                },
            }
        )

    calc_expr = _extract_calc_expression(prompt)
    if calc_expr:
        plan.append(
            {
                "name": "calc_eval",
                "input": {
                    "expression": calc_expr,
                },
            }
        )

    return plan


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
    maybe_raise_mock_tool_execution_error(name=name, prompt=prompt, attempt=attempt)
    ctx = build_tool_runtime_context(
        name=name,
        prompt=prompt,
        user_id=user_id,
        attempt=attempt,
        registry=registry,
        registry_provider=registry_provider,
        registry_loader=registry_loader,
    )
    return ctx.registration.runner(
        tool_input=tool_input,
        prompt=ctx.prompt,
        user_id=ctx.user_id,
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
