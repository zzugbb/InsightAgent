from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

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

        if self.mode == "remote" and not self.api_key:
            raise ValueError("api_key is required when mode is 'remote'")

        return self


class SettingsSummaryResponse(BaseModel):
    mode: str
    provider: str
    model: str
    api_key_configured: bool
    base_url_configured: bool
    sqlite_path: str


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
    settings = save_settings(
        StoredSettings(
            mode=payload.mode,
            provider=payload.provider,
            model=payload.model,
            base_url=payload.base_url,
            api_key=payload.api_key,
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
