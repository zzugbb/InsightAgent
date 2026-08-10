from types import SimpleNamespace
from typing import Literal, NotRequired, TypedDict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.api.deps import get_current_user
from app.config import get_settings
from app.db import get_database_locator
from app.services.audit_service import safe_record_audit_event
from app.services.chat_persistence_service import get_session
from app.services.settings_service import StoredSettings, get_stored_settings, save_settings
from app.services.task_queue_service import get_task_queue_snapshot
from app.services.tool_runtime import (
    _sanitize_tool_runtime_provider_source_name_for_artifact,
    build_configured_tool_registry_provider_preflight_tool_details,
    build_safe_tool_registry_provider_source_alias_map,
    build_tool_registry_diagnostics_summary,
    build_tool_registry_provider_sources_from_settings_artifacts,
    get_available_tool_registry_profile_names,
    get_configured_tool_registry_provider,
    get_registered_tool_names,
    get_tool_display_name,
    get_tool_registry_profile_name_from_settings,
    get_tool_registry_provider_source_name_from_settings,
    get_tool_registry_provider_source_specs_from_settings,
    resolve_unique_tool_registry_provider_source_alias,
    sanitize_tool_registry_diagnostics_artifact_payload,
)


router = APIRouter()
_TOOL_REGISTRY_DISPLAY_ORDER = {
    "task_plan": 0,
    "task_retrieve": 1,
    "calc_eval": 2,
}


class ToolRegistryProfileOptionResponse(BaseModel):
    name: str
    enabled_tool_names: list[str]
    enabled_tool_labels: list[str]
    tool_details: list["ToolRegistryProviderToolDetailResponse"] = Field(
        default_factory=list
    )


class ToolRegistryProviderToolDetailResponse(BaseModel):
    name: str
    label: str
    kind: str
    semantic_kind: str | None = None
    execution_kind: str | None = None
    execution_summary: dict[str, object] | None = None
    execution_diagnostics: list[str] = Field(default_factory=list)
    semantic_family: str | None = None
    retryable_by_default: bool
    default_timeout_ms: int
    requires_user_context: bool
    supports_result_preview: bool
    effective_result_preview_keys: list[str] = Field(default_factory=list)
    effective_result_output_keys: list[str] = Field(default_factory=list)


class ToolRegistryDiagnosticsSummaryEntryResponse(BaseModel):
    kind: str
    target: str
    count: int
    values: list[str] = Field(default_factory=list)


class ToolRegistryDiagnosticsSummaryResponse(BaseModel):
    has_diagnostics: bool = False
    skipped_total: int = 0
    missing_total: int = 0
    total: int = 0
    entries: list[ToolRegistryDiagnosticsSummaryEntryResponse] = Field(default_factory=list)


class ToolRegistryProviderSourceOptionResponse(BaseModel):
    name: str
    base_profile: str
    enabled_tool_names: list[str]
    enabled_tool_labels: list[str]
    diagnostics_summary: ToolRegistryDiagnosticsSummaryResponse = Field(
        default_factory=ToolRegistryDiagnosticsSummaryResponse
    )
    tool_details: list[ToolRegistryProviderToolDetailResponse] = Field(
        default_factory=list
    )


class SettingsUpdateRequest(BaseModel):
    mode: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    base_url: str | None = None
    api_key: str | None = None
    tool_registry_profile: str | None = None
    tool_registry_provider_source: str | None = None

    @model_validator(mode="after")
    def validate_by_mode(self) -> "SettingsUpdateRequest":
        self.mode = self.mode.strip().lower()
        self.provider = self.provider.strip()
        self.model = self.model.strip()
        self.base_url = self.base_url.strip() if self.base_url else None
        self.api_key = self.api_key.strip() if self.api_key else None
        if self.mode not in {"mock", "remote"}:
            raise ValueError("mode must be either 'mock' or 'remote'")

        if self.mode == "mock":
            self.provider = "mock"
            self.model = "mock-gpt"
            self.base_url = None
            self.api_key = None

        if not self.model:
            raise ValueError("model is required")
        if not self.provider:
            raise ValueError("provider is required")

        return self


TaskQueuePressureState = Literal["idle", "active", "saturated", "scope_limited"]
TaskQueueWaitingPolicy = Literal["capacity_aware_oldest_eligible_fifo"]


class TaskQueueDiagnosticsSummary(TypedDict):
    max_concurrent: int
    active_count: int
    waiting_count: int
    available_slots: int
    has_waiting_tasks: bool
    saturated: bool
    pressure_state: TaskQueuePressureState
    max_concurrent_per_user: int
    max_concurrent_per_session: int
    poll_interval_sec: float
    per_user_limit_enabled: bool
    per_session_limit_enabled: bool
    fairness_limits_enabled: bool
    waiting_policy: TaskQueueWaitingPolicy
    capacity_aware_fifo_enabled: bool
    current_user_active_count: NotRequired[int]
    current_user_waiting_count: NotRequired[int]
    current_user_available_slots: NotRequired[int]
    current_user_limit_reached: NotRequired[bool]
    current_session_active_count: NotRequired[int]
    current_session_waiting_count: NotRequired[int]
    current_session_available_slots: NotRequired[int]
    current_session_limit_reached: NotRequired[bool]


class SettingsSummaryResponse(BaseModel):
    mode: str
    provider: str
    model: str
    base_url: str | None = None
    api_key_configured: bool
    base_url_configured: bool
    tool_registry_profile: str
    tool_registry_provider_source: str
    enabled_tool_names: list[str]
    enabled_tool_labels: list[str]
    available_tool_registry_profiles: list[str]
    available_tool_registry_profile_details: list[ToolRegistryProfileOptionResponse]
    available_tool_registry_provider_sources: list[str]
    available_tool_registry_provider_source_details: list[ToolRegistryProviderSourceOptionResponse]
    task_queue_diagnostics: TaskQueueDiagnosticsSummary
    database_locator: str


class SettingsValidateResponse(BaseModel):
    ok: bool
    mode: str
    provider: str
    model: str
    message: str
    error: str | None = None
    error_code: str | None = None
    tool_registry_profile: str | None = None
    tool_registry_provider_source: str | None = None
    enabled_tool_names: list[str] = Field(default_factory=list)
    enabled_tool_labels: list[str] = Field(default_factory=list)
    available_tool_registry_profile_details: list[ToolRegistryProfileOptionResponse] = Field(
        default_factory=list
    )
    available_tool_registry_provider_source_details: list[
        ToolRegistryProviderSourceOptionResponse
    ] = Field(default_factory=list)


def _build_tool_registry_preview_fields(*, effective_settings: object) -> dict[str, object]:
    registry_provider = get_configured_tool_registry_provider(settings=effective_settings)
    enabled_tool_names = list(
        get_registered_tool_names(registry_provider=registry_provider)
    )
    enabled_tool_labels = [
        get_tool_display_name(name, registry_provider=registry_provider)
        for name in enabled_tool_names
    ]
    return {
        "tool_registry_profile": get_tool_registry_profile_name_from_settings(
            settings=effective_settings
        ),
        "tool_registry_provider_source": get_tool_registry_provider_source_name_from_settings(
            settings=effective_settings
        ),
        "enabled_tool_names": enabled_tool_names,
        "enabled_tool_labels": enabled_tool_labels,
    }


def _order_tool_names_for_display(names: list[str]) -> list[str]:
    return sorted(
        names,
        key=lambda name: (_TOOL_REGISTRY_DISPLAY_ORDER.get(name, 999), name),
    )


def _clone_settings_with_updates(
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


def _resolve_effective_remote_connection_settings(
    *,
    payload: SettingsUpdateRequest,
    existing: StoredSettings,
) -> tuple[str | None, str | None]:
    return (
        payload.api_key or existing.api_key,
        payload.base_url or existing.base_url,
    )


def _build_tool_registry_options_bundle(
    *,
    effective_settings: object,
) -> dict[str, object]:
    available_tool_registry_profiles = list(get_available_tool_registry_profile_names())
    available_tool_registry_profile_details: list[dict[str, object]] = []
    for profile_name in available_tool_registry_profiles:
        preview_fields = _build_tool_registry_preview_fields(
            effective_settings=_clone_settings_with_updates(
                settings=effective_settings,
                tool_registry_profile=profile_name,
                tool_registry_provider_source="default",
            )
        )
        ordered_tool_names = _order_tool_names_for_display(
            list(preview_fields["enabled_tool_names"])
        )
        preview_label_by_tool_name = dict(
            zip(
                list(preview_fields["enabled_tool_names"]),
                list(preview_fields["enabled_tool_labels"]),
                strict=False,
            )
        )
        available_tool_registry_profile_details.append(
            {
                "name": profile_name,
                "enabled_tool_names": ordered_tool_names,
                "enabled_tool_labels": [
                    str(
                        preview_label_by_tool_name.get(
                            tool_name,
                            get_tool_display_name(tool_name),
                        )
                    )
                    for tool_name in ordered_tool_names
                ],
                "tool_details": list(
                    build_configured_tool_registry_provider_preflight_tool_details(
                        provider=get_configured_tool_registry_provider(
                            settings=_clone_settings_with_updates(
                                settings=effective_settings,
                                tool_registry_profile=profile_name,
                                tool_registry_provider_source="default",
                            )
                        )
                    )
                ),
            }
        )

    source_artifacts = build_tool_registry_provider_sources_from_settings_artifacts(
        settings=effective_settings
    )
    named_sources = source_artifacts["sources"]
    source_diagnostics = source_artifacts["source_diagnostics"]
    normalized_source_specs = get_tool_registry_provider_source_specs_from_settings(
        settings=effective_settings
    )
    available_tool_registry_provider_sources = ["default"]
    available_tool_registry_provider_sources.extend(
        name
        for name in sorted({*named_sources.keys(), *normalized_source_specs.keys()})
        if name and name != "default"
    )
    available_tool_registry_provider_source_details: list[dict[str, object]] = []
    for source_name in available_tool_registry_provider_sources:
        if source_name == "default":
            preview_fields = _build_tool_registry_preview_fields(
                effective_settings=_clone_settings_with_updates(
                    settings=effective_settings,
                    tool_registry_provider_source="default",
                )
            )
            available_tool_registry_provider_source_details.append(
                {
                    "name": "default",
                    "base_profile": "default",
                    "enabled_tool_names": list(preview_fields["enabled_tool_names"]),
                    "enabled_tool_labels": list(preview_fields["enabled_tool_labels"]),
                    "diagnostics_summary": build_tool_registry_diagnostics_summary(
                        diagnostics={}
                    ),
                    "tool_details": list(
                        build_configured_tool_registry_provider_preflight_tool_details(
                            provider=get_configured_tool_registry_provider(
                                settings=_clone_settings_with_updates(
                                    settings=effective_settings,
                                    tool_registry_provider_source="default",
                                )
                            ),
                            diagnostics={},
                        )
                    ),
                }
            )
            continue
        provider = named_sources.get(source_name)
        source_spec = normalized_source_specs.get(source_name, {})
        base_profile = get_tool_registry_profile_name_from_settings(
            settings=_clone_settings_with_updates(
                settings=effective_settings,
                tool_registry_profile=(
                    source_spec.get("profile", "default")
                    if isinstance(source_spec, dict)
                    else "default"
                ),
            )
        )
        enabled_tool_names: list[str] = []
        enabled_tool_labels: list[str] = []
        tool_details: list[dict[str, object]] = []
        if provider is not None:
            provider_registry = provider.load_tool_registry()
            enabled_tool_names = _order_tool_names_for_display(
                list(provider_registry.keys())
            )
            enabled_tool_labels = [
                get_tool_display_name(tool_name, registry_provider=provider)
                for tool_name in enabled_tool_names
            ]
            tool_details = list(
                build_configured_tool_registry_provider_preflight_tool_details(
                    provider=provider,
                    diagnostics=source_diagnostics.get(source_name, {}),
                )
            )
        available_tool_registry_provider_source_details.append(
            {
                "name": source_name,
                "base_profile": base_profile,
                "enabled_tool_names": enabled_tool_names,
                "enabled_tool_labels": enabled_tool_labels,
                "diagnostics_summary": build_tool_registry_diagnostics_summary(
                    diagnostics=source_diagnostics.get(source_name, {})
                ),
                "tool_details": tool_details,
            }
        )
    return {
        "available_tool_registry_profiles": available_tool_registry_profiles,
        "available_tool_registry_profile_details": (
            available_tool_registry_profile_details
        ),
        "available_tool_registry_provider_sources": (
            available_tool_registry_provider_sources
        ),
        "available_tool_registry_provider_source_details": (
            available_tool_registry_provider_source_details
        ),
    }


def _sanitize_provider_source_option_names_for_response(
    *,
    source_names: list[object],
    source_details: list[object],
) -> tuple[list[str], list[object]]:
    safe_name_by_raw = build_safe_tool_registry_provider_source_alias_map(
        [str(source_name) for source_name in source_names]
    )
    safe_source_names: list[str] = []
    seen_safe_names: set[str] = set()
    for source_name in source_names:
        raw_name = str(source_name)
        safe_name = safe_name_by_raw.get(
            raw_name,
            _sanitize_tool_runtime_provider_source_name_for_artifact(raw_name),
        )
        if safe_name in seen_safe_names:
            continue
        seen_safe_names.add(safe_name)
        safe_source_names.append(safe_name)

    safe_details: list[object] = []
    seen_detail_names: set[str] = set()
    for detail in source_details:
        if isinstance(detail, BaseModel):
            detail_payload = detail.model_dump()
        elif isinstance(detail, dict):
            detail_payload = dict(detail)
        else:
            safe_details.append(detail)
            continue

        raw_name = str(detail_payload.get("name", "default"))
        safe_name = safe_name_by_raw.get(
            raw_name,
            _sanitize_tool_runtime_provider_source_name_for_artifact(raw_name),
        )
        if safe_name in seen_detail_names:
            continue
        seen_detail_names.add(safe_name)
        detail_payload["name"] = safe_name
        safe_details.append(detail_payload)
    return safe_source_names, safe_details


def _apply_tool_registry_preview_to_validate_response(
    *,
    result: SettingsValidateResponse,
    effective_settings: object,
) -> SettingsValidateResponse:
    preview_fields = _build_tool_registry_preview_fields(
        effective_settings=effective_settings
    )
    option_bundle = _build_tool_registry_options_bundle(
        effective_settings=effective_settings
    )
    source_names = list(option_bundle["available_tool_registry_provider_sources"])
    alias_by_source = build_safe_tool_registry_provider_source_alias_map(
        [str(source_name) for source_name in source_names]
    )
    _, safe_provider_source_details = (
        _sanitize_provider_source_option_names_for_response(
            source_names=source_names,
            source_details=list(
                option_bundle["available_tool_registry_provider_source_details"]
            ),
        )
    )
    raw_provider_source = str(preview_fields["tool_registry_provider_source"])
    return SettingsValidateResponse(
        **{
            **result.model_dump(),
            **{
                **preview_fields,
                "tool_registry_provider_source": alias_by_source.get(
                    raw_provider_source,
                    _sanitize_tool_runtime_provider_source_name_for_artifact(
                        raw_provider_source
                    ),
                ),
            },
            "available_tool_registry_profile_details": option_bundle[
                "available_tool_registry_profile_details"
            ],
            "available_tool_registry_provider_source_details": safe_provider_source_details,
        }
    )


def _build_preflight_response(
    *,
    status_code: int,
    mode: str,
    provider: str,
    model: str,
    success_message: str,
) -> SettingsValidateResponse:
    if status_code in {401, 403}:
        return SettingsValidateResponse(
            ok=False,
            mode=mode,
            provider=provider,
            model=model,
            message="remote preflight failed.",
            error=f"HTTP {status_code}: unauthorized, please verify api_key and base_url",
            error_code="remote_api_key_unauthorized",
        )
    if 200 <= status_code < 500:
        return SettingsValidateResponse(
            ok=True,
            mode=mode,
            provider=provider,
            model=model,
            message=success_message,
        )
    return SettingsValidateResponse(
        ok=False,
        mode=mode,
        provider=provider,
        model=model,
        message="remote preflight failed.",
        error=f"unexpected status: {status_code}",
        error_code="remote_base_url_unexpected_status",
    )


def _sanitize_settings_validate_response_error(
    result: SettingsValidateResponse,
) -> SettingsValidateResponse:
    if not isinstance(result.error, str):
        return result
    safe_error = sanitize_tool_registry_diagnostics_artifact_payload(result.error)
    if not isinstance(safe_error, str) or safe_error == result.error:
        return result
    return result.model_copy(update={"error": safe_error})


def _merge_runtime_settings_for_summary(
    *,
    settings: StoredSettings,
    runtime_settings: object | None = None,
) -> object:
    base_settings = get_settings() if runtime_settings is None else runtime_settings
    if isinstance(base_settings, dict):
        merged_values = dict(base_settings)
    elif hasattr(base_settings, "model_dump"):
        merged_values = dict(getattr(base_settings, "model_dump")())
    else:
        merged_values = dict(vars(base_settings))
    merged_values.update(
        {
            "mode": settings.mode,
            "provider": settings.provider,
            "model": settings.model,
            "model_name": settings.model,
            "base_url": settings.base_url,
            "api_key": settings.api_key,
            "tool_registry_profile": settings.tool_registry_profile
            or merged_values.get("tool_registry_profile"),
            "tool_registry_provider_source": settings.tool_registry_provider_source
            or merged_values.get("tool_registry_provider_source"),
        }
    )
    return SimpleNamespace(**merged_values)


def _build_task_queue_diagnostics(
    *,
    runtime_settings: object,
    current_user_id: str | None = None,
    current_session_id: str | None = None,
) -> TaskQueueDiagnosticsSummary:
    max_concurrent = max(
        1,
        int(getattr(runtime_settings, "task_queue_max_concurrent", 1) or 1),
    )
    max_concurrent_per_user = max(
        0,
        int(getattr(runtime_settings, "task_queue_max_concurrent_per_user", 0) or 0),
    )
    max_concurrent_per_session = max(
        0,
        int(
            getattr(runtime_settings, "task_queue_max_concurrent_per_session", 0)
            or 0
        ),
    )
    poll_interval_sec = float(
        getattr(runtime_settings, "task_queue_poll_interval_sec", 0.25) or 0.25
    )
    per_user_limit_enabled = max_concurrent_per_user > 0
    per_session_limit_enabled = max_concurrent_per_session > 0
    queue_snapshot = get_task_queue_snapshot(
        max_concurrent=max_concurrent,
        user_id=current_user_id,
        session_id=current_session_id,
    )
    active_count = max(0, int(queue_snapshot.get("active_count", 0) or 0))
    waiting_count = max(0, int(queue_snapshot.get("waiting_count", 0) or 0))
    available_slots = max(0, max_concurrent - active_count)
    has_waiting_tasks = waiting_count > 0
    saturated = available_slots <= 0
    if has_waiting_tasks and available_slots > 0:
        pressure_state: TaskQueuePressureState = "scope_limited"
    elif has_waiting_tasks or saturated:
        pressure_state = "saturated"
    elif active_count > 0:
        pressure_state = "active"
    else:
        pressure_state = "idle"
    diagnostics: TaskQueueDiagnosticsSummary = {
        "max_concurrent": max_concurrent,
        "active_count": active_count,
        "waiting_count": waiting_count,
        "available_slots": available_slots,
        "has_waiting_tasks": has_waiting_tasks,
        "saturated": saturated,
        "pressure_state": pressure_state,
        "max_concurrent_per_user": max_concurrent_per_user,
        "max_concurrent_per_session": max_concurrent_per_session,
        "poll_interval_sec": poll_interval_sec,
        "per_user_limit_enabled": per_user_limit_enabled,
        "per_session_limit_enabled": per_session_limit_enabled,
        "fairness_limits_enabled": (
            per_user_limit_enabled or per_session_limit_enabled
        ),
        "waiting_policy": "capacity_aware_oldest_eligible_fifo",
        "capacity_aware_fifo_enabled": True,
    }
    if current_user_id:
        current_user_active_count = max(
            0,
            int(queue_snapshot.get("active_count_for_user", 0) or 0),
        )
        current_user_waiting_count = max(
            0,
            int(queue_snapshot.get("waiting_count_for_user", 0) or 0),
        )
        diagnostics.update(
            {
                "current_user_active_count": current_user_active_count,
                "current_user_waiting_count": current_user_waiting_count,
                "current_user_available_slots": min(
                    available_slots,
                    max(0, max_concurrent_per_user - current_user_active_count)
                    if max_concurrent_per_user > 0
                    else available_slots,
                ),
                "current_user_limit_reached": (
                    max_concurrent_per_user > 0
                    and current_user_active_count >= max_concurrent_per_user
                ),
            }
        )
    if current_session_id:
        current_session_active_count = max(
            0,
            int(queue_snapshot.get("active_count_for_session", 0) or 0),
        )
        current_session_waiting_count = max(
            0,
            int(queue_snapshot.get("waiting_count_for_session", 0) or 0),
        )
        diagnostics.update(
            {
                "current_session_active_count": current_session_active_count,
                "current_session_waiting_count": current_session_waiting_count,
                "current_session_available_slots": min(
                    available_slots,
                    max(0, max_concurrent_per_session - current_session_active_count)
                    if max_concurrent_per_session > 0
                    else available_slots,
                ),
                "current_session_limit_reached": (
                    max_concurrent_per_session > 0
                    and current_session_active_count >= max_concurrent_per_session
                ),
            }
        )
    return diagnostics


def _resolve_effective_tool_registry_selection(
    *,
    payload: SettingsUpdateRequest,
    existing: StoredSettings,
    runtime_settings: object | None = None,
) -> tuple[str, str]:
    default_settings = get_settings() if runtime_settings is None else runtime_settings
    requested_profile = payload.tool_registry_profile
    requested_provider_source = payload.tool_registry_provider_source
    if isinstance(requested_profile, str) and not requested_profile.strip():
        requested_profile = None
    if isinstance(requested_provider_source, str) and not requested_provider_source.strip():
        requested_provider_source = None
    effective_settings = SimpleNamespace(
        tool_registry_profile=(
            requested_profile
            or existing.tool_registry_profile
            or getattr(default_settings, "tool_registry_profile", None)
        ),
        tool_registry_provider_source=(
            requested_provider_source
            or existing.tool_registry_provider_source
            or getattr(default_settings, "tool_registry_provider_source", None)
        ),
    )
    return (
        get_tool_registry_profile_name_from_settings(settings=effective_settings),
        get_tool_registry_provider_source_name_from_settings(
            settings=effective_settings
        ),
    )


def _validate_tool_registry_selection(
    *,
    effective_settings: object,
    tool_registry_profile: str,
    tool_registry_provider_source: str,
) -> None:
    option_bundle = _build_tool_registry_options_bundle(
        effective_settings=effective_settings
    )
    available_tool_registry_profiles = option_bundle[
        "available_tool_registry_profiles"
    ]
    if tool_registry_profile not in available_tool_registry_profiles:
        raise HTTPException(
            status_code=422,
            detail="tool_registry_profile is invalid",
        )
    available_tool_registry_provider_sources = option_bundle[
        "available_tool_registry_provider_sources"
    ]
    if tool_registry_provider_source not in available_tool_registry_provider_sources:
        raise HTTPException(
            status_code=422,
            detail="tool_registry_provider_source is invalid",
        )


def _resolve_tool_registry_provider_source_request_alias(
    *,
    effective_settings: object,
    tool_registry_provider_source: str,
) -> str:
    return resolve_unique_tool_registry_provider_source_alias(
        settings=effective_settings,
        tool_registry_provider_source=tool_registry_provider_source,
    )


def _build_settings_summary_response(
    *,
    settings: StoredSettings,
    runtime_settings: object | None = None,
    database_locator: str | None = None,
    current_user_id: str | None = None,
    current_session_id: str | None = None,
) -> SettingsSummaryResponse:
    effective_settings = _merge_runtime_settings_for_summary(
        settings=settings,
        runtime_settings=runtime_settings,
    )
    preview_fields = _build_tool_registry_preview_fields(
        effective_settings=effective_settings
    )
    option_bundle = _build_tool_registry_options_bundle(
        effective_settings=effective_settings
    )
    source_names = list(option_bundle["available_tool_registry_provider_sources"])
    alias_by_source = build_safe_tool_registry_provider_source_alias_map(
        [str(source_name) for source_name in source_names]
    )
    safe_provider_sources, safe_provider_source_details = (
        _sanitize_provider_source_option_names_for_response(
            source_names=source_names,
            source_details=list(
                option_bundle["available_tool_registry_provider_source_details"]
            ),
        )
    )
    raw_provider_source = str(preview_fields["tool_registry_provider_source"])
    return SettingsSummaryResponse(
        mode=settings.mode,
        provider=settings.provider,
        model=settings.model,
        base_url=settings.base_url,
        api_key_configured=bool(settings.api_key),
        base_url_configured=bool(settings.base_url),
        tool_registry_profile=str(preview_fields["tool_registry_profile"]),
        tool_registry_provider_source=alias_by_source.get(
            raw_provider_source,
            _sanitize_tool_runtime_provider_source_name_for_artifact(
                raw_provider_source
            ),
        ),
        enabled_tool_names=list(preview_fields["enabled_tool_names"]),
        enabled_tool_labels=list(preview_fields["enabled_tool_labels"]),
        available_tool_registry_profiles=list(
            option_bundle["available_tool_registry_profiles"]
        ),
        available_tool_registry_profile_details=list(
            option_bundle["available_tool_registry_profile_details"]
        ),
        available_tool_registry_provider_sources=safe_provider_sources,
        available_tool_registry_provider_source_details=safe_provider_source_details,
        task_queue_diagnostics=_build_task_queue_diagnostics(
            runtime_settings=effective_settings,
            current_user_id=current_user_id,
            current_session_id=current_session_id,
        ),
        database_locator=database_locator or get_database_locator(),
    )


def _resolve_current_session_id_for_task_queue_diagnostics(
    *,
    session_id: str | None,
    user_id: str,
) -> str | None:
    normalized_session_id = session_id.strip() if session_id else ""
    if not normalized_session_id:
        return None
    if get_session(normalized_session_id, user_id) is None:
        return None
    return normalized_session_id


@router.get("", response_model=SettingsSummaryResponse)
def get_settings_summary(
    session_id: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> SettingsSummaryResponse:
    user_id = str(current_user["id"])
    settings = get_stored_settings(user_id)
    return _build_settings_summary_response(
        settings=settings,
        current_user_id=user_id,
        current_session_id=_resolve_current_session_id_for_task_queue_diagnostics(
            session_id=session_id,
            user_id=user_id,
        ),
    )


@router.put("", response_model=SettingsSummaryResponse)
def update_settings(
    payload: SettingsUpdateRequest,
    session_id: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> SettingsSummaryResponse:
    user_id = str(current_user["id"])
    existing = get_stored_settings(user_id)
    if payload.mode == "mock":
        effective_api_key = None
        effective_base_url = None
    else:
        effective_api_key, effective_base_url = (
            _resolve_effective_remote_connection_settings(
                payload=payload,
                existing=existing,
            )
        )
    runtime_settings = get_settings()
    effective_tool_registry_profile, effective_tool_registry_provider_source = (
        _resolve_effective_tool_registry_selection(
            payload=payload,
            existing=existing,
            runtime_settings=runtime_settings,
        )
    )
    if (
        isinstance(payload.tool_registry_provider_source, str)
        and payload.tool_registry_provider_source.strip()
    ):
        effective_tool_registry_provider_source = (
            _resolve_tool_registry_provider_source_request_alias(
                effective_settings=runtime_settings,
                tool_registry_provider_source=effective_tool_registry_provider_source,
            )
        )
    _validate_tool_registry_selection(
        effective_settings=runtime_settings,
        tool_registry_profile=effective_tool_registry_profile,
        tool_registry_provider_source=effective_tool_registry_provider_source,
    )
    if payload.mode == "remote" and not effective_api_key:
        raise HTTPException(
            status_code=422,
            detail="api_key is required when mode is 'remote'",
        )
    if payload.mode == "remote" and not effective_base_url:
        raise HTTPException(
            status_code=422,
            detail="base_url is required when mode is 'remote'",
        )

    settings = save_settings(
        user_id,
        StoredSettings(
            mode=payload.mode,
            provider=payload.provider,
            model=payload.model,
            base_url=effective_base_url,
            api_key=effective_api_key,
            tool_registry_profile=effective_tool_registry_profile,
            tool_registry_provider_source=effective_tool_registry_provider_source,
        )
    )
    safe_record_audit_event(
        user_id=user_id,
        event_type="settings_update",
        detail={
            "mode": settings.mode,
            "provider": settings.provider,
            "model": settings.model,
            "base_url_configured": bool(settings.base_url),
            "api_key_configured": bool(settings.api_key),
            "tool_registry_profile": settings.tool_registry_profile,
            "tool_registry_provider_source": settings.tool_registry_provider_source,
        },
    )
    return _build_settings_summary_response(
        settings=settings,
        current_user_id=user_id,
        current_session_id=_resolve_current_session_id_for_task_queue_diagnostics(
            session_id=session_id,
            user_id=user_id,
        ),
    )


@router.post("/validate", response_model=SettingsValidateResponse)
def validate_settings(
    payload: SettingsUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> SettingsValidateResponse:
    user_id = str(current_user["id"])
    existing = get_stored_settings(user_id)
    if payload.mode == "mock":
        effective_api_key = None
        effective_base_url = None
    else:
        effective_api_key, effective_base_url = (
            _resolve_effective_remote_connection_settings(
                payload=payload,
                existing=existing,
            )
        )
    runtime_settings = get_settings()
    effective_tool_registry_profile, effective_tool_registry_provider_source = (
        _resolve_effective_tool_registry_selection(
            payload=payload,
            existing=existing,
            runtime_settings=runtime_settings,
        )
    )
    if (
        isinstance(payload.tool_registry_provider_source, str)
        and payload.tool_registry_provider_source.strip()
    ):
        effective_tool_registry_provider_source = (
            _resolve_tool_registry_provider_source_request_alias(
                effective_settings=runtime_settings,
                tool_registry_provider_source=effective_tool_registry_provider_source,
            )
        )
    effective_runtime_settings = _merge_runtime_settings_for_summary(
        settings=StoredSettings(
            mode=payload.mode,
            provider=payload.provider,
            model=payload.model,
            base_url=effective_base_url,
            api_key=effective_api_key,
            tool_registry_profile=effective_tool_registry_profile,
            tool_registry_provider_source=effective_tool_registry_provider_source,
        )
    )

    def _audit_validate(result: SettingsValidateResponse) -> SettingsValidateResponse:
        result = _sanitize_settings_validate_response_error(result)
        safe_record_audit_event(
            user_id=user_id,
            event_type="settings_validate",
            detail={
                "ok": result.ok,
                "mode": payload.mode,
                "provider": payload.provider,
                "model": payload.model,
                "error_code": result.error_code,
                "base_url_configured": bool(effective_base_url),
                "api_key_configured": bool(effective_api_key),
                "tool_registry_profile": effective_tool_registry_profile,
                "tool_registry_provider_source": effective_tool_registry_provider_source,
            },
        )
        return result

    try:
        _validate_tool_registry_selection(
            effective_settings=runtime_settings,
            tool_registry_profile=effective_tool_registry_profile,
            tool_registry_provider_source=effective_tool_registry_provider_source,
        )
    except HTTPException as exc:
        return _audit_validate(
            _apply_tool_registry_preview_to_validate_response(
                result=SettingsValidateResponse(
                    ok=False,
                    mode=payload.mode,
                    provider=payload.provider,
                    model=payload.model,
                    message="tool registry selection is invalid.",
                    error=str(exc.detail),
                    error_code="tool_registry_selection_invalid",
                ),
                effective_settings=effective_runtime_settings,
            )
        )

    if payload.mode == "remote" and not effective_api_key:
        return _audit_validate(
            _apply_tool_registry_preview_to_validate_response(
                result=SettingsValidateResponse(
                    ok=False,
                    mode=payload.mode,
                    provider=payload.provider,
                    model=payload.model,
                    message="remote mode preflight failed.",
                    error="api_key is required when mode is 'remote'",
                    error_code="remote_api_key_required",
                ),
                effective_settings=effective_runtime_settings,
            )
        )
    if payload.mode == "remote" and not effective_base_url:
        return _audit_validate(
            _apply_tool_registry_preview_to_validate_response(
                result=SettingsValidateResponse(
                    ok=False,
                    mode=payload.mode,
                    provider=payload.provider,
                    model=payload.model,
                    message="remote mode preflight failed.",
                    error="base_url is required when mode is 'remote'",
                    error_code="remote_base_url_required",
                ),
                effective_settings=effective_runtime_settings,
            )
        )

    if payload.mode == "mock":
        return _audit_validate(
            _apply_tool_registry_preview_to_validate_response(
                result=SettingsValidateResponse(
                    ok=True,
                    mode=payload.mode,
                    provider=payload.provider,
                    model=payload.model,
                    message="mock mode is ready.",
                ),
                effective_settings=effective_runtime_settings,
            )
        )

    if effective_base_url:
        parsed = urlparse(effective_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return _audit_validate(
                _apply_tool_registry_preview_to_validate_response(
                    result=SettingsValidateResponse(
                        ok=False,
                        mode=payload.mode,
                        provider=payload.provider,
                        model=payload.model,
                        message="base_url is invalid.",
                        error="base_url must be a valid http(s) URL",
                        error_code="remote_base_url_invalid",
                    ),
                    effective_settings=effective_runtime_settings,
                )
            )

        headers: dict[str, str] = {}
        if effective_api_key:
            headers["Authorization"] = f"Bearer {effective_api_key}"
        head_error: Exception | None = None

        try:
            request = Request(effective_base_url, method="HEAD", headers=headers)
            try:
                with urlopen(request, timeout=3) as response:
                    status_code = int(getattr(response, "status", 0))
            except HTTPError as exc:
                status_code = int(exc.code)
            head_result = _build_preflight_response(
                status_code=status_code,
                mode=payload.mode,
                provider=payload.provider,
                model=payload.model,
                success_message="remote preflight succeeded.",
            )
            if head_result.ok or head_result.error_code == "remote_api_key_unauthorized":
                return _audit_validate(
                    _apply_tool_registry_preview_to_validate_response(
                        result=head_result,
                        effective_settings=effective_runtime_settings,
                    )
                )
        except URLError as exc:
            head_error = exc
        except Exception as exc:  # noqa: BLE001
            head_error = exc

        # 某些网关/服务禁用 HEAD，回退 GET 以减少误判
        try:
            fallback = Request(effective_base_url, method="GET", headers=headers)
            try:
                with urlopen(fallback, timeout=3) as response:
                    status_code = int(getattr(response, "status", 0))
            except HTTPError as exc:
                status_code = int(exc.code)
            return _audit_validate(
                _apply_tool_registry_preview_to_validate_response(
                    result=_build_preflight_response(
                        status_code=status_code,
                        mode=payload.mode,
                        provider=payload.provider,
                        model=payload.model,
                        success_message="remote preflight succeeded (GET fallback).",
                    ),
                    effective_settings=effective_runtime_settings,
                )
            )
        except Exception as fallback_exc:  # noqa: BLE001
            base_error = head_error if head_error is not None else "head request failed"
            return _audit_validate(
                _apply_tool_registry_preview_to_validate_response(
                    result=SettingsValidateResponse(
                        ok=False,
                        mode=payload.mode,
                        provider=payload.provider,
                        model=payload.model,
                        message="remote preflight failed.",
                        error=f"{base_error}; fallback_get={fallback_exc}",
                        error_code="remote_preflight_network_error",
                    ),
                    effective_settings=effective_runtime_settings,
                )
            )

    return _audit_validate(
        _apply_tool_registry_preview_to_validate_response(
            result=SettingsValidateResponse(
                ok=True,
                mode=payload.mode,
                provider=payload.provider,
                model=payload.model,
                message="remote mode is ready.",
            ),
            effective_settings=effective_runtime_settings,
        )
    )
