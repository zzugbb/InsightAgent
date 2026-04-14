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


def _now_iso() -> str:
    return datetime.now().isoformat()


def _default_settings() -> StoredSettings:
    settings = get_settings()
    return StoredSettings(
        mode=settings.mode,
        provider=settings.provider,
        model=settings.model_name,
        base_url=settings.base_url,
        api_key=settings.api_key,
    )


def get_stored_settings(user_id: str) -> StoredSettings:
    defaults = _default_settings()
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT mode, provider, model, base_url, api_key_enc
            FROM user_settings
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return defaults

    return StoredSettings(
        mode=row["mode"],
        provider=row["provider"],
        model=row["model"],
        base_url=row["base_url"],
        api_key=decrypt_secret(row["api_key_enc"]),
    )


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
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                mode = excluded.mode,
                provider = excluded.provider,
                model = excluded.model,
                base_url = excluded.base_url,
                api_key_enc = excluded.api_key_enc,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                settings.mode,
                settings.provider,
                settings.model,
                settings.base_url,
                encrypted_api_key,
                now,
                now,
            ),
        )
        connection.commit()
    return settings
