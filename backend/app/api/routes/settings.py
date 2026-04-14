from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.db import get_sqlite_path
from app.services.settings_service import StoredSettings, get_stored_settings, save_settings


router = APIRouter()


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

        if not self.provider:
            raise ValueError("provider is required")

        if not self.model:
            raise ValueError("model is required")

        return self


class SettingsSummaryResponse(BaseModel):
    mode: str
    provider: str
    model: str
    api_key_configured: bool
    base_url_configured: bool
    sqlite_path: str


class SettingsValidateResponse(BaseModel):
    ok: bool
    mode: str
    provider: str
    model: str
    message: str
    error: str | None = None


@router.get("", response_model=SettingsSummaryResponse)
def get_settings_summary() -> SettingsSummaryResponse:
    settings = get_stored_settings()
    return SettingsSummaryResponse(
        mode=settings.mode,
        provider=settings.provider,
        model=settings.model,
        api_key_configured=bool(settings.api_key),
        base_url_configured=bool(settings.base_url),
        sqlite_path=str(get_sqlite_path()),
    )


@router.put("", response_model=SettingsSummaryResponse)
def update_settings(payload: SettingsUpdateRequest) -> SettingsSummaryResponse:
    existing = get_stored_settings()
    effective_api_key = payload.api_key or existing.api_key
    if payload.mode == "remote" and not effective_api_key:
        raise HTTPException(
            status_code=422,
            detail="api_key is required when mode is 'remote'",
        )

    settings = save_settings(
        StoredSettings(
            mode=payload.mode,
            provider=payload.provider,
            model=payload.model,
            base_url=payload.base_url,
            api_key=effective_api_key,
        )
    )
    return SettingsSummaryResponse(
        mode=settings.mode,
        provider=settings.provider,
        model=settings.model,
        api_key_configured=bool(settings.api_key),
        base_url_configured=bool(settings.base_url),
        sqlite_path=str(get_sqlite_path()),
    )


@router.post("/validate", response_model=SettingsValidateResponse)
def validate_settings(payload: SettingsUpdateRequest) -> SettingsValidateResponse:
    existing = get_stored_settings()
    effective_api_key = payload.api_key or existing.api_key
    if payload.mode == "remote" and not effective_api_key:
        return SettingsValidateResponse(
            ok=False,
            mode=payload.mode,
            provider=payload.provider,
            model=payload.model,
            message="remote mode preflight failed.",
            error="api_key is required when mode is 'remote'",
        )

    if payload.mode == "mock":
        return SettingsValidateResponse(
            ok=True,
            mode=payload.mode,
            provider=payload.provider,
            model=payload.model,
            message="mock mode is ready.",
        )

    if payload.base_url:
        parsed = urlparse(payload.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return SettingsValidateResponse(
                ok=False,
                mode=payload.mode,
                provider=payload.provider,
                model=payload.model,
                message="base_url is invalid.",
                error="base_url must be a valid http(s) URL",
            )

        try:
            request = Request(payload.base_url, method="HEAD")
            with urlopen(request, timeout=3) as response:
                status_code = int(getattr(response, "status", 0))
                if 200 <= status_code < 500:
                    return SettingsValidateResponse(
                        ok=True,
                        mode=payload.mode,
                        provider=payload.provider,
                        model=payload.model,
                        message="remote preflight succeeded.",
                    )
                return SettingsValidateResponse(
                    ok=False,
                    mode=payload.mode,
                    provider=payload.provider,
                    model=payload.model,
                        message="remote preflight failed.",
                        error=f"unexpected status: {status_code}",
                )
        except Exception as exc:
            # 某些网关/服务禁用 HEAD，回退 GET 以减少误判
            try:
                fallback = Request(payload.base_url, method="GET")
                with urlopen(fallback, timeout=3) as response:
                    status_code = int(getattr(response, "status", 0))
                    if 200 <= status_code < 500:
                        return SettingsValidateResponse(
                            ok=True,
                            mode=payload.mode,
                            provider=payload.provider,
                            model=payload.model,
                            message="remote preflight succeeded (GET fallback).",
                        )
                    return SettingsValidateResponse(
                        ok=False,
                        mode=payload.mode,
                        provider=payload.provider,
                        model=payload.model,
                        message="remote preflight failed.",
                        error=f"unexpected status: {status_code}",
                    )
            except Exception as fallback_exc:
                return SettingsValidateResponse(
                    ok=False,
                    mode=payload.mode,
                    provider=payload.provider,
                    model=payload.model,
                    message="remote preflight failed.",
                    error=f"{exc}; fallback_get={fallback_exc}",
                )

    return SettingsValidateResponse(
        ok=True,
        mode=payload.mode,
        provider=payload.provider,
        model=payload.model,
        message="remote mode payload is structurally valid.",
    )
