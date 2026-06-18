from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.api.deps import get_current_user
from app.config import get_settings
from app.db import get_database_locator
from app.services.audit_service import safe_record_audit_event
from app.services.settings_service import StoredSettings, get_stored_settings, save_settings
from app.services.tool_runtime import (
    build_tool_registry_provider_sources_from_settings,
    get_available_tool_registry_profile_names,
    get_configured_tool_registry_provider,
    get_registered_tool_names,
    get_tool_display_name,
    get_tool_registry_profile_name_from_settings,
    get_tool_registry_provider_source_name_from_settings,
    get_tool_registry_provider_source_specs_from_settings,
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


class ToolRegistryProviderSourceOptionResponse(BaseModel):
    name: str
    base_profile: str
    enabled_tool_names: list[str]
    enabled_tool_labels: list[str]


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


def _build_tool_registry_options_bundle(
    *,
    effective_settings: object,
) -> dict[str, object]:
    available_tool_registry_profiles = list(get_available_tool_registry_profile_names())
    available_tool_registry_profile_details: list[
        ToolRegistryProfileOptionResponse
    ] = []
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
        available_tool_registry_profile_details.append(
            ToolRegistryProfileOptionResponse(
                name=profile_name,
                enabled_tool_names=ordered_tool_names,
                enabled_tool_labels=[
                    get_tool_display_name(tool_name)
                    for tool_name in ordered_tool_names
                ],
            )
        )

    named_sources = build_tool_registry_provider_sources_from_settings(
        settings=effective_settings
    )
    normalized_source_specs = get_tool_registry_provider_source_specs_from_settings(
        settings=effective_settings
    )
    available_tool_registry_provider_sources = ["default"]
    available_tool_registry_provider_sources.extend(
        name for name in sorted(named_sources) if name and name != "default"
    )
    available_tool_registry_provider_source_details: list[
        ToolRegistryProviderSourceOptionResponse
    ] = []
    for source_name in available_tool_registry_provider_sources:
        if source_name == "default":
            preview_fields = _build_tool_registry_preview_fields(
                effective_settings=_clone_settings_with_updates(
                    settings=effective_settings,
                    tool_registry_provider_source="default",
                )
            )
            available_tool_registry_provider_source_details.append(
                ToolRegistryProviderSourceOptionResponse(
                    name="default",
                    base_profile="default",
                    enabled_tool_names=list(preview_fields["enabled_tool_names"]),
                    enabled_tool_labels=list(preview_fields["enabled_tool_labels"]),
                )
            )
            continue
        provider = named_sources.get(source_name)
        if provider is None:
            continue
        provider_registry = provider.load_tool_registry()
        enabled_tool_names = _order_tool_names_for_display(
            list(provider_registry.keys())
        )
        enabled_tool_labels = [
            provider_registry[tool_name].label for tool_name in enabled_tool_names
        ]
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
        available_tool_registry_provider_source_details.append(
            ToolRegistryProviderSourceOptionResponse(
                name=source_name,
                base_profile=base_profile,
                enabled_tool_names=enabled_tool_names,
                enabled_tool_labels=enabled_tool_labels,
            )
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
    return result.model_copy(
        update={
            **preview_fields,
            "available_tool_registry_profile_details": (
                option_bundle["available_tool_registry_profile_details"]
            ),
            "available_tool_registry_provider_source_details": (
                option_bundle["available_tool_registry_provider_source_details"]
            ),
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


def _build_settings_summary_response(
    *,
    settings: StoredSettings,
    runtime_settings: object | None = None,
    database_locator: str | None = None,
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
    return SettingsSummaryResponse(
        mode=settings.mode,
        provider=settings.provider,
        model=settings.model,
        base_url=settings.base_url,
        api_key_configured=bool(settings.api_key),
        base_url_configured=bool(settings.base_url),
        tool_registry_profile=str(preview_fields["tool_registry_profile"]),
        tool_registry_provider_source=str(preview_fields["tool_registry_provider_source"]),
        enabled_tool_names=list(preview_fields["enabled_tool_names"]),
        enabled_tool_labels=list(preview_fields["enabled_tool_labels"]),
        available_tool_registry_profiles=list(
            option_bundle["available_tool_registry_profiles"]
        ),
        available_tool_registry_profile_details=list(
            option_bundle["available_tool_registry_profile_details"]
        ),
        available_tool_registry_provider_sources=list(
            option_bundle["available_tool_registry_provider_sources"]
        ),
        available_tool_registry_provider_source_details=list(
            option_bundle["available_tool_registry_provider_source_details"]
        ),
        database_locator=database_locator or get_database_locator(),
    )


@router.get("", response_model=SettingsSummaryResponse)
def get_settings_summary(current_user: dict = Depends(get_current_user)) -> SettingsSummaryResponse:
    user_id = str(current_user["id"])
    settings = get_stored_settings(user_id)
    return _build_settings_summary_response(settings=settings)


@router.put("", response_model=SettingsSummaryResponse)
def update_settings(
    payload: SettingsUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> SettingsSummaryResponse:
    user_id = str(current_user["id"])
    existing = get_stored_settings(user_id)
    if payload.mode == "mock":
        effective_api_key = None
        effective_base_url = None
    else:
        effective_api_key = payload.api_key or existing.api_key
        effective_base_url = payload.base_url
    effective_tool_registry_profile, effective_tool_registry_provider_source = (
        _resolve_effective_tool_registry_selection(
            payload=payload,
            existing=existing,
        )
    )
    option_bundle = _build_tool_registry_options_bundle(
        effective_settings=get_settings()
    )
    available_tool_registry_profiles = option_bundle[
        "available_tool_registry_profiles"
    ]
    if effective_tool_registry_profile not in available_tool_registry_profiles:
        raise HTTPException(
            status_code=422,
            detail="tool_registry_profile is invalid",
        )
    available_tool_registry_provider_sources = option_bundle[
        "available_tool_registry_provider_sources"
    ]
    if effective_tool_registry_provider_source not in available_tool_registry_provider_sources:
        raise HTTPException(
            status_code=422,
            detail="tool_registry_provider_source is invalid",
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
    return _build_settings_summary_response(settings=settings)


@router.post("/validate", response_model=SettingsValidateResponse)
def validate_settings(
    payload: SettingsUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> SettingsValidateResponse:
    user_id = str(current_user["id"])
    existing = get_stored_settings(user_id)
    effective_api_key = payload.api_key or existing.api_key
    effective_base_url = payload.base_url
    effective_tool_registry_profile, effective_tool_registry_provider_source = (
        _resolve_effective_tool_registry_selection(
            payload=payload,
            existing=existing,
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
