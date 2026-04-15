from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.api.deps import get_current_user
from app.db import get_database_locator
from app.services.audit_service import record_audit_event
from app.services.settings_service import StoredSettings, get_stored_settings, save_settings


router = APIRouter()


def _safe_record_audit_event(
    *,
    user_id: str | None,
    event_type: str,
    detail: dict[str, object] | None = None,
) -> None:
    try:
        record_audit_event(user_id=user_id, event_type=event_type, detail=detail)
    except Exception:
        # 审计日志采用 best-effort，不影响设置保存主流程
        return


class SettingsUpdateRequest(BaseModel):
    mode: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    base_url: str | None = None
    api_key: str | None = None

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
    database_locator: str


class SettingsValidateResponse(BaseModel):
    ok: bool
    mode: str
    provider: str
    model: str
    message: str
    error: str | None = None
    error_code: str | None = None


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


@router.get("", response_model=SettingsSummaryResponse)
def get_settings_summary(current_user: dict = Depends(get_current_user)) -> SettingsSummaryResponse:
    user_id = str(current_user["id"])
    settings = get_stored_settings(user_id)
    return SettingsSummaryResponse(
        mode=settings.mode,
        provider=settings.provider,
        model=settings.model,
        base_url=settings.base_url,
        api_key_configured=bool(settings.api_key),
        base_url_configured=bool(settings.base_url),
        database_locator=get_database_locator(),
    )


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
        )
    )
    _safe_record_audit_event(
        user_id=user_id,
        event_type="settings_update",
        detail={
            "mode": settings.mode,
            "provider": settings.provider,
            "model": settings.model,
            "base_url_configured": bool(settings.base_url),
            "api_key_configured": bool(settings.api_key),
        },
    )
    return SettingsSummaryResponse(
        mode=settings.mode,
        provider=settings.provider,
        model=settings.model,
        base_url=settings.base_url,
        api_key_configured=bool(settings.api_key),
        base_url_configured=bool(settings.base_url),
        database_locator=get_database_locator(),
    )


@router.post("/validate", response_model=SettingsValidateResponse)
def validate_settings(
    payload: SettingsUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> SettingsValidateResponse:
    user_id = str(current_user["id"])
    existing = get_stored_settings(user_id)
    effective_api_key = payload.api_key or existing.api_key
    effective_base_url = payload.base_url
    if payload.mode == "remote" and not effective_api_key:
        return SettingsValidateResponse(
            ok=False,
            mode=payload.mode,
            provider=payload.provider,
            model=payload.model,
            message="remote mode preflight failed.",
            error="api_key is required when mode is 'remote'",
            error_code="remote_api_key_required",
        )
    if payload.mode == "remote" and not effective_base_url:
        return SettingsValidateResponse(
            ok=False,
            mode=payload.mode,
            provider=payload.provider,
            model=payload.model,
            message="remote mode preflight failed.",
            error="base_url is required when mode is 'remote'",
            error_code="remote_base_url_required",
        )

    if payload.mode == "mock":
        return SettingsValidateResponse(
            ok=True,
            mode=payload.mode,
            provider=payload.provider,
            model=payload.model,
            message="mock mode is ready.",
        )

    if effective_base_url:
        parsed = urlparse(effective_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return SettingsValidateResponse(
                ok=False,
                mode=payload.mode,
                provider=payload.provider,
                model=payload.model,
                message="base_url is invalid.",
                error="base_url must be a valid http(s) URL",
                error_code="remote_base_url_invalid",
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
                return head_result
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
            return _build_preflight_response(
                status_code=status_code,
                mode=payload.mode,
                provider=payload.provider,
                model=payload.model,
                success_message="remote preflight succeeded (GET fallback).",
            )
        except Exception as fallback_exc:  # noqa: BLE001
            base_error = head_error if head_error is not None else "head request failed"
            return SettingsValidateResponse(
                ok=False,
                mode=payload.mode,
                provider=payload.provider,
                model=payload.model,
                message="remote preflight failed.",
                error=f"{base_error}; fallback_get={fallback_exc}",
                error_code="remote_preflight_network_error",
            )

    return SettingsValidateResponse(
        ok=True,
        mode=payload.mode,
        provider=payload.provider,
        model=payload.model,
        message="remote mode is ready.",
    )
