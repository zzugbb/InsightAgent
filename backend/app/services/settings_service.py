from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.config import get_settings
from app.db import get_db_connection
from app.security import decrypt_secret, encrypt_secret


class StoredSettings(BaseModel):
    mode: str
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None
    tool_registry_profile: str | None = None
    tool_registry_provider_source: str | None = None
    tool_registry_overrides_json: str | None = None
    tool_registry_extra_tools_json: str | None = None
    tool_registry_loaders_json: str | None = None
    tool_registry_loader_factories_json: str | None = None
    tool_registry_providers_json: str | None = None
    tool_registry_provider_factories_json: str | None = None
    tool_registry_provider_sources_json: str | None = None


def _now_iso() -> str:
    return datetime.now().isoformat()


def _normalize_optional_str(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_default_runtime_mode(
    *,
    mode: object,
    provider: object,
    model: object,
    base_url: object,
    api_key: object,
) -> tuple[str, str, str, str | None, str | None]:
    normalized_mode = _normalize_optional_str(mode) or "mock"
    normalized_mode = normalized_mode.lower()
    normalized_provider = _normalize_optional_str(provider) or "mock"
    normalized_model = _normalize_optional_str(model) or "mock-gpt"
    normalized_base_url = _normalize_optional_str(base_url)
    normalized_api_key = _normalize_optional_str(api_key)

    if normalized_mode != "mock":
        return (
            normalized_mode,
            normalized_provider,
            normalized_model,
            normalized_base_url,
            normalized_api_key,
        )

    remote_ready = (
        normalized_provider != "mock"
        and normalized_model != "mock-gpt"
        and normalized_api_key is not None
    )
    if remote_ready:
        return (
            "remote",
            normalized_provider,
            normalized_model,
            normalized_base_url,
            normalized_api_key,
        )

    return ("mock", "mock", "mock-gpt", None, None)


def _build_stored_settings_update_from_row(row: object) -> dict[str, object]:
    values = {
        "mode": getattr(row, "__getitem__", None) and row["mode"],
        "provider": getattr(row, "__getitem__", None) and row["provider"],
        "model": getattr(row, "__getitem__", None) and row["model"],
        "tool_registry_profile": getattr(row, "__getitem__", None)
        and row["tool_registry_profile"],
        "tool_registry_provider_source": getattr(row, "__getitem__", None)
        and row["tool_registry_provider_source"],
    }
    normalized_base_url = _normalize_optional_str(
        getattr(row, "__getitem__", None) and row["base_url"]
    )
    if normalized_base_url is not None:
        values["base_url"] = normalized_base_url
    decrypted_api_key = decrypt_secret(
        getattr(row, "__getitem__", None) and row["api_key_enc"]
    )
    normalized_api_key = _normalize_optional_str(decrypted_api_key)
    if normalized_api_key is not None:
        values["api_key"] = normalized_api_key
    return values


def _default_settings() -> StoredSettings:
    settings = get_settings()
    mode, provider, model, base_url, api_key = _normalize_default_runtime_mode(
        mode=getattr(settings, "mode", None),
        provider=getattr(settings, "provider", None),
        model=getattr(settings, "model_name", None),
        base_url=getattr(settings, "base_url", None),
        api_key=getattr(settings, "api_key", None),
    )
    return StoredSettings(
        mode=mode,
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
        tool_registry_profile=settings.tool_registry_profile,
        tool_registry_provider_source=settings.tool_registry_provider_source,
        tool_registry_overrides_json=settings.tool_registry_overrides_json,
        tool_registry_extra_tools_json=settings.tool_registry_extra_tools_json,
        tool_registry_loaders_json=settings.tool_registry_loaders_json,
        tool_registry_loader_factories_json=settings.tool_registry_loader_factories_json,
        tool_registry_providers_json=settings.tool_registry_providers_json,
        tool_registry_provider_factories_json=settings.tool_registry_provider_factories_json,
        tool_registry_provider_sources_json=settings.tool_registry_provider_sources_json,
    )


def get_stored_settings(user_id: str) -> StoredSettings:
    defaults = _default_settings()
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT mode, provider, model, base_url, api_key_enc,
                   tool_registry_profile, tool_registry_provider_source
            FROM user_settings
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return defaults

    return defaults.model_copy(update=_build_stored_settings_update_from_row(row))


def save_settings(user_id: str, settings: StoredSettings) -> StoredSettings:
    now = _now_iso()
    encrypted_api_key = encrypt_secret(settings.api_key)
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO user_settings(
                user_id,
                mode,
                provider,
                model,
                base_url,
                api_key_enc,
                tool_registry_profile,
                tool_registry_provider_source,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                mode = excluded.mode,
                provider = excluded.provider,
                model = excluded.model,
                base_url = excluded.base_url,
                api_key_enc = excluded.api_key_enc,
                tool_registry_profile = excluded.tool_registry_profile,
                tool_registry_provider_source = excluded.tool_registry_provider_source,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                settings.mode,
                settings.provider,
                settings.model,
                settings.base_url,
                encrypted_api_key,
                settings.tool_registry_profile,
                settings.tool_registry_provider_source,
                now,
                now,
            ),
        )
        connection.commit()
    return settings
