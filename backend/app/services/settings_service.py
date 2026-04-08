from pydantic import BaseModel

from app.config import get_settings
from app.db import get_db_connection


class StoredSettings(BaseModel):
    mode: str
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None


def _default_settings() -> StoredSettings:
    settings = get_settings()
    return StoredSettings(
        mode=settings.mode,
        provider=settings.provider,
        model=settings.model_name,
        base_url=settings.base_url,
        api_key=settings.api_key,
    )


def get_stored_settings() -> StoredSettings:
    defaults = _default_settings()
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT mode, provider, model, base_url, api_key
            FROM app_settings
            WHERE id = 1
            """
        ).fetchone()

    if row is None:
        return defaults

    return StoredSettings(
        mode=row["mode"],
        provider=row["provider"],
        model=row["model"],
        base_url=row["base_url"],
        api_key=row["api_key"],
    )


def save_settings(settings: StoredSettings) -> StoredSettings:
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO app_settings(id, mode, provider, model, base_url, api_key)
            VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                mode = excluded.mode,
                provider = excluded.provider,
                model = excluded.model,
                base_url = excluded.base_url,
                api_key = excluded.api_key
            """,
            (
                settings.mode,
                settings.provider,
                settings.model,
                settings.base_url,
                settings.api_key,
            ),
        )
        connection.commit()
    return settings
